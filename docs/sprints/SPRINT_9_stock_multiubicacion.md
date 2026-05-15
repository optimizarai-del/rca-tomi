# Sprint 9 — Stock multi-ubicación

> Estado: ✅ cerrado · suite pytest **77/77** verde

## Requisitos

Hasta el Sprint 8, `Material.stock` era un único número plano: "cuántas unidades hay en algún lugar". En la reunión del 2026-05-13 se identificó que la operación real necesita **separar el stock por ubicación física**:

| Ubicación | Significado |
|---|---|
| `deposito_propio` | Mercadería en el depósito de RCA, todavía sin asignar a obra |
| `en_obra` | Ya retirada del depósito y entregada a una obra específica |
| `comprado_no_retirado` | Pago/factura emitida, pero la mercadería sigue en el proveedor |

Sin esta separación, no se podía responder preguntas operativas básicas:
- *¿Cuánto cemento tengo en obra IDS hoy?*
- *¿Qué facturé/pagué a Holcim que todavía no fue a buscar nadie?*

Además, la premisa de la reunión: **toda la carga operativa va por mensajes al bot de WhatsApp**. La web es para visualización y confirmación.

## Cómo se hizo

### T1 — Modelo `StockMaterial` + migración Alembic

[backend/app/models.py](../../backend/app/models.py): nuevo enum `UbicacionStockTipo` y tabla `StockMaterial`:

```python
class StockMaterial(Base):
    id, material_id, ubicacion_tipo, ubicacion_ref, cantidad, updated_at
```

- `ubicacion_ref` apunta a obra_id, proveedor_id o `null` según `ubicacion_tipo`.
- `Material.stock` se mantiene como **cache** de `(deposito + en_obra)` — no rompe queries existentes ni `t_alertas_stock_bajo`.

Migración Alembic [030c8e2c167e](../../backend/alembic/versions/030c8e2c167e_sprint_9_10_stock_multi_ubicacion_y_.py) incluye **data-migration**: copia el `Material.stock` actual a una fila `(deposito_propio, ref=null, cantidad=stock)`.

### T2 — Servicio `app/stock.py` + endpoints `/api/stock`

[backend/app/stock.py](../../backend/app/stock.py) centraliza la lógica para que endpoints REST y tools del agente compartan la misma validación:

| Función | Descripción |
|---|---|
| `cargar_compra_pendiente` | Crea una fila `comprado_no_retirado` |
| `retirar_de_proveedor` | Resta de `comprado_no_retirado`, suma a `deposito_propio` o `en_obra` |
| `consumir_en_obra` | Resta de `en_obra` (la cuadrilla usó el material) |
| `transferir_stock` | Mueve entre depósito ↔ obras o entre obras |
| `breakdown_por_material` | Devuelve el desglose con nombres resueltos (obra/proveedor) |

Reglas que valida:
- Cantidades positivas (>0).
- No permite que una ubicación quede negativa.
- Validación de FKs (material, obra, proveedor existen).
- Cada operación deja un `MovimientoMaterial` para auditoría.
- Después de cada movimiento, recalcula `Material.stock = sum(deposito + en_obra)` (no cuenta pendientes).

Router [backend/app/routers/stock.py](../../backend/app/routers/stock.py) expone:

```
GET    /api/stock/                        → lista todos los materiales con breakdown
GET    /api/stock/{material_id}           → detalle de un material
POST   /api/stock/compra-pendiente        → (admin) cargar_compra_pendiente
POST   /api/stock/retiro-proveedor        → (admin) retirar_de_proveedor
POST   /api/stock/consumo-obra            → consumir_en_obra
POST   /api/stock/transferir              → (admin) transferir_stock
```

### T3 — Tools del agente

[backend/app/agent/tools.py](../../backend/app/agent/tools.py) sumó 5 tools (1 lectura + 4 escritura):

| Tool | Tipo | Descripción |
|---|---|---|
| `consultar_stock` | LECTURA | Desglose de uno o todos los materiales |
| `cargar_compra_pendiente_retiro` | ESCRITURA | "compré 10 bolsas cemento a Holcim" → estado comprado_no_retirado |
| `retirar_de_proveedor` | ESCRITURA | "retiré 10 bolsas cemento de Holcim a IDS" |
| `consumir_en_obra` | ESCRITURA | "consumimos 5 bolsas en IDS" |
| `transferir_stock` | ESCRITURA | "mové 20 ladrillos de IDS a SP" |

Las 4 de escritura se sumaron a `REQUIRES_CONFIRMATION_TOOLS`, así que el orchestrator persiste un `AgentAction` pendiente y la ejecución real solo ocurre cuando el admin clickea **Confirmar** en la UI (o vía magic link de WhatsApp).

Helpers nuevos:
- `_material_by_ref(ref, db)` — resuelve por id o nombre parcial (`ilike '%'`).
- `_proveedor_by_ref(ref, db)` — análogo para proveedor.

### T4 — Slash command `/stock`

[backend/app/slash_commands.py](../../backend/app/slash_commands.py): nuevo handler `_cmd_stock`.

```
/stock                    → top 15 materiales con cantidad disponible + flag de stock crítico
/stock cemento            → desglose detallado de Cemento (por ubicación)
/stock 1                  → por id
```

### T5 — UI `/materiales` con 4 columnas

[frontend/src/pages/Materiales.jsx](../../frontend/src/pages/Materiales.jsx) ahora consume `GET /api/stock/` (en vez de `GET /api/materiales/`) y muestra:

| Columna | Significado |
|---|---|
| Material | Ícono + nombre + chip "Bajo stock" si total ≤ mínimo |
| Depósito | Suma de cantidades en depósito propio |
| En obras | Suma de cantidades en `en_obra` |
| Pendiente retiro | Suma de `comprado_no_retirado` (marrón/leather si > 0) |
| Total disp. | Sum(depósito + en obras) — el del cache `Material.stock` |

Al click en una fila se despliega el detalle por ubicación (obra IDS: 20 · obra SP: 5 · Holcim: 100 pendientes).

Se removieron los botones "+ Ingreso" / "+ Consumo" — la carga va por bot. Sí queda el botón "Nuevo material" para alta inicial (admin) y un botón nuevo **"Presupuesto materiales"** que navega a `/presupuestos` (Sprint 10).

### T6 — Tests

[backend/tests/test_stock.py](../../backend/tests/test_stock.py) con **16 tests**:

- Servicio (10): operaciones individuales, validaciones, auditoría.
- REST (2): smoke test de `GET /api/stock/`, flujo `compra → retiro`.
- Tools del agente (4): resolución de nombres parciales, errores correctos.

`pytest` total del proyecto: **77/77** verde (49 anteriores + 16 nuevos del Sprint 9 + 12 del Sprint 10).

## Cómo se usa

### Carga típica vía WhatsApp (premisa)

```
👤 "Compré 100 bolsas de cemento a Holcim"
🤖 [tool cargar_compra_pendiente_retiro] → persiste AgentAction pendiente
🤖 "¿Confirmás cargar compra pendiente: Cemento Holcim · 100 bolsas · prov Holcim SA?"
👤 [click ✅ Confirmar]
🤖 "✅ Listo. Pendiente de retiro: 100 bolsas en Holcim"
```

Luego:
```
👤 "Retirá 50 bolsas de cemento de Holcim a la obra IDS"
🤖 [retirar_de_proveedor con destino_tipo=en_obra]
🤖 "¿Confirmás retiro de 50 bolsas cemento → IDS?"
👤 ✅
```

Y al final:
```
👤 "Usamos 30 bolsas de cemento en IDS"
🤖 [consumir_en_obra]
🤖 "¿Confirmás consumo 30 bolsas cemento en IDS?"
👤 ✅
🤖 "Stock disponible: 70 bolsas (20 en IDS, 50 en otras obras/depósito)"
```

### Consulta rápida por WhatsApp

```
/stock cemento
```
Devuelve:
```
📦 *Cemento Holcim* (bolsa)
  Total disponible: 70 · pendiente retiro: 50
  • Obra IDS: 20
  • Depósito propio: 50
  • Holcim SA (comprado no retirado): 50
```

### Web

Sidebar → Recursos → **Materiales**: tabla con las 4 columnas, click en fila para desplegar el detalle por ubicación.

## Tests realizados

- ✅ `alembic upgrade head` aplicó limpio sobre DB con 4 materiales existentes → se copiaron a `stock_material` como `deposito_propio`.
- ✅ `pytest` → 77/77 passed.
- ✅ Import del módulo: `from app.main import app` resuelve sin warnings.
- ✅ Smoke endpoint `GET /api/stock/` devuelve breakdown completo.

## Estado y deuda

✅ **Cerrado:** modelo + migración + servicio + endpoints + tools + slash + UI + tests.

⚠️ **Deuda menor:**
- Sin UI para revertir un consumo o transferencia (hoy hay que crear el movimiento inverso vía bot).
- El detalle expandido en `/materiales` no muestra el `MovimientoMaterial` que originó cada fila (auditoría visible). Se accede al log vía consulta del agente.
- No hay alerta automática cuando una compra lleva > N días pendiente de retiro. Se puede sumar en Sprint 12+ con notifications.py.

📌 **Cómo se conecta:**
- **Sprint 10** (presupuestos) usa los precios de `Material.precio_unitario` para estimar.
- **Sprint 13** (foto de ticket) creará automáticamente movimientos `cargar_compra_pendiente_retiro` después del OCR.
- El sidebar item "Materiales" hereda permisos del Sprint 7 (`isAdmin`).
