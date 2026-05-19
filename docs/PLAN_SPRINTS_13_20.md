# Plan — Sprints 13 a 20

Plan vigente. Reemplaza a [PLAN_SPRINTS_9_13.md](PLAN_SPRINTS_9_13.md), que queda como histórico.

Base: notas de reunión 2026-05-19. Premisa central sigue igual:
**toda la carga de datos operativa va por bot (ahora Telegram)**. La web es panel de consulta, confirmación y configuración.

## Estado de lo ya cerrado

| # | Sprint | Resuelve | Estado |
|---|---|---|---|
| 9 | Stock multi-ubicación | `StockMaterial(ubicacion_tipo)` — depósito · en obra · comprado-no-retirado | ✅ |
| 10 | Presupuestos de materiales | `Presupuesto` / `PresupuestoItem` por obra, botón en `/materiales` | ✅ |
| 11 | Bot de Telegram (texto) | Webhook + `/vincular`, ruteo al agente. Reemplaza WhatsApp "por ahora" | ✅ |
| 12 | Perfil demo dual | `is_demo` en 15 tablas raíz + scoping automático via listener + `scope_demo()` manual en routers | ✅ |

## Plan adelante

| # | Sprint | Resuelve | Tamaño |
|---|---|---|---|
| 13 | UI cleanup + permisos granulares | Sacar puntos en títulos · tabla check de accesos por sección + obras visibles (caso arquitecta) | M |
| 14 | Materiales: estados pedido/retirar/retirado + alertas | Estado `pedido` con fecha → aviso 1 día antes · `retirado` con foto factura + forma de pago + blanco/negro | M |
| 15 | Proveedores extendido | Detalle facturado vs presupuestado · listar por fecha · ocultar +1 año · tipos de materiales que vende | S |
| 16 | Recetas por etapa de obra | "Tapial 10m = 140 ladrillos/m + X cemento + X hierro + X reboque" — alimenta presupuestos (S10) | M |
| 17 | Requerimientos por obra | Sección nueva: mensaje al bot ante imprevisto → queda anotado en `/obras/:id/requerimientos` | S |
| 18 | OCR de tickets con Claude Vision | Inbound media de Telegram → Claude Vision → propuesta `MovimientoMaterial` + `Comprobante` para confirmar | M |
| 19 | Contabilidad blanco/negro por obra | Ingreso/egreso · cobrado/por cobrar · efectivo/cheque/transferencia · IIBB 3% / IVA 21% / gastos banco · "lo que tenés − lo que se debe" | L |
| 20 | Deploy producción + dominio + handoff a Tomi | Cerrar deploy en Easy Panel, dominio, doc operativa para Tomi | S |

## Orden de ejecución

**S20 → S13 → S17 → S14 → S15 → S16 → S18 → S19**

- **S20 primero**: Tomi necesita acceso real para que sus notas tengan validación contra el sistema en producción.
- **S13 después**: sin permisos granulares la arquitecta no puede entrar acotada.
- **S17 → S14 → S15**: quitan fricción en el día a día (requerimientos por bot, refinar stock, proveedores).
- **S16 → S18**: aceleran carga pero no bloquean.
- **S19 último**: es el más pesado y conviene tener los datos limpios antes.

## Convenciones

- 1 sprint = una rama `sprint-N-<slug>`, mergeada a `dev` vía PR.
- Commits en español, con `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` trailer.
- Cada sprint deja un `docs/sprints/SPRINT_N_*.md` con: requisitos, cómo se hizo, cómo se usa, tests, deuda pendiente.
- Migraciones Alembic incrementales (no se regenera la base).
- `pytest` debe quedar 100% verde al final de cada sprint.

## Detalle por sprint

### S13 — UI cleanup + permisos granulares

**Backend — modelos:**
```python
class PermisoUsuario(Base):
    id, user_id, seccion, allowed: bool
    # seccion ∈ {'obras','materiales','proveedores','finanzas','equipo','stock','presupuestos',...}

class PermisoUsuarioObra(Base):
    id, user_id, obra_id, allowed: bool
    # whitelist explícita: si user tiene filas → solo esas obras; si no tiene → todas (default admin)
```

**Backend — guard:**
- Dependency `require_section(seccion: str)` en routers protegidos.
- Filtro automático en queries de obras por la whitelist del usuario.

**Frontend:**
- `/equipo/:id/permisos` — grilla de checkboxes (secciones × allow) + multiselect de obras.
- Ocultar items del sidebar según permisos del user logueado.

**UI cleanup:**
- Sacar puntos finales en `<h1>` / `<h2>` de todas las páginas (regex sobre `frontend/src/pages/*.jsx`).

### S14 — Estados de pedido/retirar/retirado en materiales

**Modelo:**
```python
class StockMaterial(Base):  # ya existe
    # nuevo: estado_pedido: ('comprado_no_retirado'|'pedido_retirar'|'retirado'|'en_obra'|'deposito_propio')
    # nuevo: fecha_retirar: Date (nullable)  — si estado='pedido_retirar'
    # nuevo: retirado_at: DateTime (nullable)
    # nuevo: comprobante_id: FK Comprobante (nullable) — foto factura
    # nuevo: forma_pago: ('efectivo'|'cheque'|'transferencia'|'tarjeta') (nullable)
    # nuevo: en_negro: bool (default False)
```

**Tools del agente:**
- `pedir_retiro(material, proveedor, cantidad, fecha)` → estado `pedido_retirar` + alerta.
- `marcar_retirado(stock_id, forma_pago, en_negro, foto_factura_id)`.

**Alertas:**
- Job nocturno que para cada `stock_pedido_retirar` con `fecha_retirar = hoy + 1` manda mensaje por Telegram.

### S15 — Proveedores extendido

**Modelo:**
```python
class ProveedorMaterial(Base):
    id, proveedor_id, material_id  # tipos que vende
```

**Endpoints:**
- `GET /api/proveedores/:id/materiales?desde=&hasta=` — listado con `facturado | presupuestado`, paginado.
- Default: filtrar items con fecha > -1 año (param `incluir_antiguos=true` para verlos).

### S16 — Recetas por etapa de obra

**Modelo:**
```python
class Receta(Base):
    id, nombre, unidad: ('metro_lineal'|'metro_cuadrado'|'metro_cubico'|'unidad')

class RecetaItem(Base):
    id, receta_id, material_id, cantidad_por_unidad
```

**Flujo:**
- Crear receta "Tapial" con items: 140 ladrillos/m, X kg cemento/m, X kg hierro/m, X kg reboque/m.
- Tool del agente `cotizar_etapa(receta, cantidad_unidades, obra)` → crea `Presupuesto` borrador con items multiplicados.

### S17 — Requerimientos por obra

**Modelo:**
```python
class Requerimiento(Base):
    id, obra_id, created_by_id, mensaje, estado: ('abierto'|'resuelto'), created_at, resuelto_at
```

**Bot:**
- Slash `/req <obra> <mensaje>` → crea requerimiento.
- Notificación a usuarios con permiso sobre esa obra.

**Web:**
- `/obras/:id/requerimientos` — lista, marcar resuelto.

### S18 — OCR de tickets con Claude Vision

Plan ya esbozado en S13 original. Habilitado por Sprint 11b: ya tenemos `get_file_url(file_id)` en `telegram_sender.py`.

**Flujo:**
1. Usuario manda foto de ticket al bot.
2. Backend descarga via `get_file_url`.
3. Claude Vision extrae: proveedor, fecha, items (material + cantidad + precio), total, IVA.
4. Bot responde con propuesta: *"¿Confirmás esto como compra a {proveedor} por ${total}?"*.
5. Usuario `/ok` → crea `Comprobante` + `MovimientoMaterial` en estado `comprado_no_retirado`.

### S19 — Contabilidad blanco/negro por obra

**Modelo:**
```python
class MovimientoFinanciero(Base):  # generalización de MovimientoObra
    id, obra_id, tipo: ('ingreso'|'egreso'),
    legalidad: ('blanco'|'negro'),
    monto: Decimal,
    estado: ('cobrado'|'pagado'|'pendiente'),
    medio_pago: ('efectivo'|'cheque'|'transferencia'|'tarjeta') | null,
    fecha_operacion: Date,
    fecha_cobro_pago: Date | null,
    comprobante_id: FK Comprobante | null,
    iva_pct: Decimal | null,  # 21 por default en blanco
    iibb_pct: Decimal | null, # 3 por default en blanco
    gastos_banco: Decimal default 0,
    notas: Text
```

**Vistas:**
- `/obras/:id/finanzas` con tabs: Blanco / Negro / Consolidado.
- "Lo que tenés": suma de cobrado − pagado, por obra.
- "Lo que se debe": pendiente (por cobrar + por pagar).
- Cálculo de impuestos: `monto_neto = monto - (monto * iva_pct) - (monto * iibb_pct) - gastos_banco`.

### S20 — Deploy producción + dominio + handoff a Tomi

Ver [docs/sprints/SPRINT_20_deploy_handoff.md](sprints/SPRINT_20_deploy_handoff.md).
