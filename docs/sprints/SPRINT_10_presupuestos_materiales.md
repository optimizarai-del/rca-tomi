# Sprint 10 — Presupuestos de materiales por obra

> Estado: ✅ cerrado · suite pytest **77/77** verde

## Requisitos

Petición de la reunión 2026-05-13: *"en la sección materiales, agregar un button que sea para crear presupuesto, pedidos o nuevos computos con el detalle que necesita cada obra"*.

Después de aclarar con el equipo, se simplificó a **un único concepto**: el **presupuesto de materiales por obra**, que en la práctica representa lo mismo que cómputo y orden de compra para los flujos típicos. Es:

- Una lista nombrada de `(material, cantidad, precio estimado)` para una obra.
- Estados: `borrador` → `aprobado` → `cerrado`.
- Se carga por WhatsApp; se aprueba/visualiza en la web.

## Cómo se hizo

### T1 — Modelos `Presupuesto` y `PresupuestoItem`

[backend/app/models.py](../../backend/app/models.py): enum `EstadoPresupuesto` (`borrador`/`aprobado`/`cerrado`) + dos tablas:

```python
class Presupuesto:
    id, obra_id (FK), nombre, estado, total_estimado,
    notas, created_at, aprobado_at, created_by_id

class PresupuestoItem:
    id, presupuesto_id (FK CASCADE), material_id (FK),
    cantidad, precio_unitario_estimado, subtotal
```

`total_estimado` es **cache** que se recalcula automáticamente al crear/agregar items. La fórmula: `sum(items.subtotal)` donde `subtotal = cantidad * precio_unitario_estimado`.

Misma migración Alembic [030c8e2c167e](../../backend/alembic/versions/030c8e2c167e_sprint_9_10_stock_multi_ubicacion_y_.py) del Sprint 9.

### T2 — Servicio `app/presupuestos_svc.py` + endpoints

[backend/app/presupuestos_svc.py](../../backend/app/presupuestos_svc.py) centraliza:

| Función | Reglas que valida |
|---|---|
| `crear_presupuesto(obra_id, nombre, items, ...)` | obra existe; nombre no vacío; cantidades > 0; resuelve precio del Material si no se pasa |
| `agregar_item(presupuesto_id, material_id, cantidad, precio?)` | solo si está en `borrador` |
| `aprobar_presupuesto(presupuesto_id)` | solo desde `borrador`; no permite aprobar vacío |
| `serialize(p, db)` | dict con nombres resueltos (obra, materiales) |

Router [backend/app/routers/presupuestos.py](../../backend/app/routers/presupuestos.py):

```
GET    /api/presupuestos/?obra_id=&estado=     → listar (filtros opcionales)
GET    /api/presupuestos/{id}                  → detalle
POST   /api/presupuestos/                      → (admin) crear con items
POST   /api/presupuestos/{id}/items            → (admin) agregar item
POST   /api/presupuestos/{id}/aprobar          → (admin) marcar aprobado
DELETE /api/presupuestos/{id}                  → (admin) borrar (rechaza si está aprobado)
```

### T3 — Tools del agente

[backend/app/agent/tools.py](../../backend/app/agent/tools.py) sumó 3 tools:

| Tool | Tipo | Notas |
|---|---|---|
| `consultar_presupuestos` | LECTURA | filtra por obra y/o estado |
| `crear_presupuesto` | ESCRITURA | acepta items con `{material, cantidad, precio?}`, resuelve material por nombre |
| `aprobar_presupuesto` | ESCRITURA | requiere `presupuesto_id` |

Las 2 de escritura están en `REQUIRES_CONFIRMATION_TOOLS`. El JSON schema acepta `items` como array, así que la conversación natural funciona: *"Creá un presupuesto para IDS llamado 'cimientos' con 100 cemento y 200 ladrillos"* — el LLM mapea a la estructura.

### T4 — UI

[frontend/src/pages/Presupuestos.jsx](../../frontend/src/pages/Presupuestos.jsx): página nueva con:

- 3 big numbers: total presupuestos · borradores · suma de aprobados.
- Filtros: por obra (dropdown) + por estado (pills).
- Layout 2 columnas: lista de presupuestos a la izquierda, detalle expandido a la derecha.
- En el detalle: tabla de items con `(material, cantidad, precio, subtotal)` + total destacado + botones **Aprobar** y **Borrar** (solo si está en borrador).
- Si no hay presupuestos, muestra un placeholder con el prompt sugerido para el bot:
  > `"crea presupuesto para obra IDS llamado 'cimientos' con 100 cemento y 200 ladrillos"`

[frontend/src/components/Layout/Sidebar.jsx](../../frontend/src/components/Layout/Sidebar.jsx): nuevo item **Presupuestos** bajo Recursos (visible con `isAdmin`).

[frontend/src/pages/Materiales.jsx](../../frontend/src/pages/Materiales.jsx): botón **"Presupuesto materiales"** en el header que navega a `/presupuestos`.

[frontend/src/App.jsx](../../frontend/src/App.jsx): ruta `/presupuestos` con `requireAdmin`.

### T5 — Tests

[backend/tests/test_presupuestos.py](../../backend/tests/test_presupuestos.py) con **12 tests**:

- Servicio (7): cálculo de total, validaciones, transiciones.
- Endpoints REST (2): crear + listar + aprobar end-to-end; borrar aprobado rechazado.
- Tools del agente (3): resolución de referencias, aprobación, filtrado por obra.

## Cómo se usa

### Flujo típico vía WhatsApp

```
👤 "Crear presupuesto para obra IDS llamado 'fundaciones enero' con 100 bolsas cemento, 5 toneladas hierro, 2000 ladrillos"
🤖 [crear_presupuesto] → AgentAction pendiente con preview de los items y el total
👤 [✅ Confirmar]
🤖 "Listo. Presupuesto #5 en borrador. Total estimado: $625.000"

👤 "Aprobá el presupuesto 5"
🤖 [aprobar_presupuesto] → confirmar
👤 ✅
🤖 "Aprobado. Quedó cerrado para edición."
```

### Web

Sidebar → Recursos → **Presupuestos**: ver lista, abrir detalle, aprobar/borrar.

O desde Materiales: botón **"Presupuesto materiales"** en la esquina superior.

### Precio por defecto

Si en el item no se pasa `precio`, el servicio toma `Material.precio_unitario` actual. Cuando se aprueba, el precio queda **congelado en el item** (`precio_unitario_estimado`), así que cambios futuros en `Material.precio_unitario` no afectan presupuestos ya aprobados.

## Tests realizados

- ✅ `pytest` → 77/77 passed (incluye 12 nuevos del Sprint 10).
- ✅ Endpoint POST /api/presupuestos crea con items y devuelve el total correcto.
- ✅ POST /aprobar setea `aprobado_at` y bloquea agregar items adicionales.

## Estado y deuda

✅ **Cerrado:** modelo + migración + servicio + endpoints + tools + UI + tests.

⚠️ **Deuda menor:**
- No hay UI para editar items existentes ni cambiar precios en un borrador. Solo se pueden agregar nuevos items via tool/endpoint, no editar.
- No hay vinculación automática `Presupuesto → MovimientoObra` cuando se aprueba. Es decisión pendiente: cuando se aprueba, ¿debería crear automáticamente un movimiento esperado de egreso? El equipo aún no lo definió.
- No hay vista de **diferencia** entre presupuesto aprobado y stock comprado/consumido real para esa obra. Sería un overlay tipo: *de las 100 bolsas presupuestadas, ya retiraste 80, te faltan 20*. Quedaría para Sprint 11+.

📌 **Cómo se conecta:**
- **Sprint 9** (stock) usa los mismos materiales. Cuando esté el Sprint 11 (cotizaciones), se va a recalcular automáticamente el `total_estimado` con la mejor cotización vigente por material.
- **Sprint 8** (auth + roles) — la creación/aprobación requiere `require_admin`.
- El sidebar item "Presupuestos" hereda gating del sprint 7 (`isAdmin`).
