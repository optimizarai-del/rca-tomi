# Plan — Sprints 9 a 13

Plan de evolución a partir de notas de reunión del 2026-05-13. Premisa central:
**TODA la carga de datos operativa va por mensajes al bot de WhatsApp**.
La web es panel de consulta y confirmación, no de carga directa.

## Visión global

| # | Sprint | Resuelve | Estado |
|---|---|---|---|
| 9 | Stock multi-ubicación | Romper `stock` plano → `StockMaterial(ubicacion_tipo, cantidad)` con 3 tipos: `deposito_propio` · `en_obra` · `comprado_no_retirado` | 🟡 en curso |
| 10 | Presupuestos de materiales | Tabla `Presupuesto`/`PresupuestoItem` por obra. Botón en `/materiales` para ver el presupuesto activo de una obra | 🟡 en curso |
| 11 | Cotizaciones de proveedores | Tabla `Cotizacion`, comparativa, recalcular presupuesto con mejor cotización | ⏳ siguiente |
| 12 | Mano de obra por especialidad | `TarifaEspecialidad` + `RegistroManoObra`. Slash `/horas`. Costo obra = materiales + mano de obra | ⏳ |
| 13 | Foto de ticket con Claude Vision | Inbound media WhatsApp → Claude Vision → propuesta MovimientoMaterial + Comprobante para confirmar | ⏳ |

## Decisiones tomadas en la reunión

1. **Mano de obra**: se trackea **por especialidad** (albañil, electricista, plomero, ayudante, pintor), no por persona individual. Una cuadrilla tiene una especialidad principal (campo ya existe en `Cuadrilla.especialidad`).
2. **Botón en /materiales**: presupuesto de materiales **por obra** — UN solo flujo, no tres. Se carga por bot, se visualiza/aprueba en la web.
3. **OCR del ticket**: Claude Vision (ya hay key Anthropic).
4. **Comprado-no-retirado**: el flujo es:
   - WhatsApp: "compré 10 bolsas de cemento a Holcim" → estado `comprado_no_retirado` (la mercadería sigue en el proveedor).
   - WhatsApp: "retiré 10 bolsas de cemento de Holcim a obra IDS" → cambia a `en_obra(IDS)`.

## Convenciones

- 1 sprint = commits dedicados (rama `sprint-N`).
- Commits en español, con `Co-Authored-By` trailer.
- Cada sprint deja un `docs/sprints/SPRINT_N_*.md` con: requisitos, cómo se hizo, cómo se usa, tests, deuda pendiente.
- Migraciones Alembic incrementales (no se regenera la base).
- `pytest` debe quedar 100% verde al final de cada sprint.

## Sprint 9 — Stock multi-ubicación (en curso)

**Modelos:**
```python
class StockMaterial(Base):
    id, material_id, ubicacion_tipo, ubicacion_ref, cantidad, updated_at

# ubicacion_tipo ∈ {'deposito_propio', 'en_obra', 'comprado_no_retirado'}
# ubicacion_ref → para 'en_obra': obra_id; para 'comprado_no_retirado': proveedor_id; para 'deposito_propio': null
```
Migración inicial: copia `Material.stock` actual a `StockMaterial(deposito_propio, cantidad=stock)`.

**Tools del agente (write + confirmación):**
- `cargar_compra_pendiente_retiro(material, proveedor, cantidad)`
- `retirar_de_proveedor(material, proveedor, cantidad, destino: 'deposito' | obra_id)`
- `consumir_en_obra(material, obra, cantidad)`
- `transferir_stock(material, origen, destino, cantidad)`

**Tool read:** `consultar_stock(material?)` → breakdown por ubicación.

**Slash:** `/stock [material]`.

**UI:** `/materiales` con 4 columnas: Depósito · En obras · Pendiente retiro · Total.

## Sprint 10 — Presupuesto de materiales por obra (en curso)

**Modelos:**
```python
class Presupuesto(Base):
    id, obra_id, nombre, estado: ('borrador' | 'aprobado' | 'cerrado'),
    total_estimado, created_at, created_by_id

class PresupuestoItem(Base):
    id, presupuesto_id, material_id, cantidad, precio_unitario_estimado, subtotal
```

**Tools (write + confirmación):**
- `crear_presupuesto(obra, items)` → crea presupuesto borrador con items.
- `agregar_item_presupuesto(presupuesto_id, material, cantidad)`
- `aprobar_presupuesto(presupuesto_id)`

**Tool read:** `consultar_presupuestos(obra?)`.

**UI:** botón **"Presupuesto materiales"** en `/materiales` que abre vista por obra: tabla con items + total. Botón "Marcar aprobado" (acción web mínima).

## Sprints 11-13 — detalle por confirmar

Cada uno se detallará al arrancar. Foco actual: cerrar 9 y 10 con tests verdes y UI funcional.
