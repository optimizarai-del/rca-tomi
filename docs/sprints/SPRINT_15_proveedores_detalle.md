# Sprint 15 — Proveedores extendido

> Estado: ✅ cerrado · suite pytest **144/144** verde

## Requisitos

Notas de reunión 2026-05-19:

> PROVEEDORES
> - Detalle de materiales si es facturado o presupuestado.
> - Listar materiales por fecha.
> - Los que tengan +1 año los elimine (no borrar pero si no mostrar en pantalla).
> - Mostrar qué tipos de materiales vende el proveedor.

## Cómo se hizo

### T1 — Rama

Branch `sprint-15-proveedores` desde `sprint-14-stock-retiros`.

### T2 — Sin modelo nuevo

Se aprovecha el campo existente `Material.proveedor_id` (1:N) — no hace falta una tabla N:M `ProveedorMaterial`. Los "tipos que vende" se derivan con `SELECT Material WHERE proveedor_id = X`.

Para el historial:
- **Facturado** = `RetiroMaterial` (Sprint 14) con `proveedor_id = X`.
- **Presupuestado** = `PresupuestoItem` (Sprint 10) cuyo `material.proveedor_id = X`.

### T3 — Schemas

[backend/app/schemas.py](../../backend/app/schemas.py) suma:

```python
class ProveedorMaterialOut:
    material_id, nombre, categoria, unidad, precio_unitario,
    stock_actual, pendiente_retiro

class ProveedorHistorialItem:
    fecha, tipo: 'facturado'|'presupuestado',
    material_id, material_nombre, unidad, cantidad,
    precio_unitario, subtotal, en_negro, forma_pago,
    obra_destino_nombre, presupuesto_nombre, presupuesto_estado,
    ref_id

class ProveedorDetalleOut(ProveedorOut):
    materiales_vendidos: List[ProveedorMaterialOut]
    ultima_actividad: Optional[date]
```

### T4 — Endpoints

[backend/app/routers/proveedores.py](../../backend/app/routers/proveedores.py):

**Listado con filtro de inactivos:**
```
GET /api/proveedores?activos_meses=12&incluir_inactivos=false
```
- Default `activos_meses=12`: oculta los que no tuvieron actividad (retiros ni items de presupuesto) en los últimos 12 meses.
- Proveedores sin actividad alguna (recién creados, sin uso) → **se muestran** igual.
- `incluir_inactivos=true` o `activos_meses=0` desactivan el filtro.

**Tipos que vende:**
```
GET /api/proveedores/:id/materiales
```
Lista cada material con `precio_unitario`, `stock_actual` y `pendiente_retiro` específicos de este proveedor.

**Detalle completo:**
```
GET /api/proveedores/:id/detalle
```
Proveedor + materiales que vende + última actividad.

**Historial:**
```
GET /api/proveedores/:id/historial?desde=&hasta=&incluir_antiguos=false
```
Items facturados (retiros efectivos) y presupuestados, ordenados por fecha desc.
Default: oculta items con fecha > 1 año.

⚠️ Las rutas con paths fijos (`/{pid}/detalle`, `/{pid}/materiales`, `/{pid}/historial`) van **después** de `POST ""` pero el orden de declaración respeta que ningún path fijo choque con `/{pid}` por sí solo.

### T5 — Frontend

[frontend/src/pages/Proveedores.jsx](../../frontend/src/pages/Proveedores.jsx):

- **Card de proveedor** ahora es clickeable: expande detalle inline.
- **Checkbox "Ver inactivos (+1 año)"** en el header para alternar el filtro.
- Detalle con 2 tabs:
  - **Vende** — lista de materiales con categoría, precio, pendiente de retiro en ese proveedor.
  - **Historial** — items facturados (chip "blanco"/"negro") y presupuestados (chip estado), con fecha, cantidad, subtotal. Checkbox para incluir items de hace +1 año.

Iconografía:
- 🧾 `Receipt` (olive) = facturado
- 📄 `FileText` (navy/60) = presupuestado

## Cómo se usa

### Tomi quiere saber qué le compró a Holcim este año

1. `/proveedores` → click en el card de Holcim.
2. Tab **Historial** → ya filtrado a los últimos 12 meses.
3. Cada fila muestra fecha, material, cantidad, subtotal, blanco/negro.
4. Tildar "Incluir items de hace más de 1 año" para ver histórico completo.

### Tomi quiere ver qué vende cada proveedor

1. `/proveedores` → click en el card → tab **Vende**.
2. Lista de materiales asociados a ese proveedor.
3. Si hay mercadería pendiente de retiro en ese proveedor, aparece un chip warn con la cantidad.

### El listado se está llenando de proveedores viejos

- Por default `/proveedores` solo muestra los activos (12 meses).
- Tildar "Ver inactivos (+1 año)" para gestionarlos.

## Tests

[backend/tests/test_proveedores_detalle.py](../../backend/tests/test_proveedores_detalle.py) — 11 casos:

- Listado sin actividad → todos visibles (por la regla "sin actividad alguna → mostrar").
- Listado con actividad vieja (+1 año en uno, reciente en otro) → solo el reciente.
- `incluir_inactivos=true` → ambos.
- Materiales que vende (con segundo material agregado).
- Pendiente de retiro en ese proveedor sumado en la respuesta.
- Historial mezcla facturado + presupuestado.
- Historial default oculta items > 1 año, `incluir_antiguos=true` los muestra.
- Orden del historial: fecha desc.
- Detalle completo (proveedor + materiales + última_actividad).
- 404s.

Suite total: **144/144 verde**.

## Deuda pendiente

- **N:M proveedor-material**: hoy un material tiene un único proveedor. Cuando se quiera comparar cotizaciones de mismos materiales entre varios proveedores (Sprint 11 original), hay que migrar a tabla `ProveedorMaterial(proveedor_id, material_id, precio_actual, fecha_cotizacion)`. Lo dejamos para ese sprint.
- **Filtro por categoría / búsqueda**: el listado de `/proveedores` no tiene búsqueda. Aceptable hasta 20-30 proveedores; después se agrega.
- **Historial con paginación**: hoy se trae todo el rango. Si crece mucho la DB se vuelve lento. Workaround actual: el frontend ya muestra solo los primeros 30 con "…y N más". Próximo sprint puede agregar `limit/offset` server-side.
- **Edición desde detalle**: hoy no se puede editar precio_unitario del material desde la vista del proveedor. Se hace desde `/materiales`. Si pasa a ser un workflow común, agregar inline edit.
