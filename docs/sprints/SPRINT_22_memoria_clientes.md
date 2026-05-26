# Sprint 22 — Memoria de clientes

> Estado: ✅ cerrado · suite pytest **174/174** verde

## Requisitos

De las notas de reunión 2026-05-20: prioridad #2 — *"memoria clientes para guardad los datos"*. La idea: cada cliente tiene datos recurrentes (CBU, alias, condiciones de pago, contacto secundario, preferencias) y un historial de interacciones que sirve para no perder contexto entre conversaciones.

Respeta la decisión arquitectónica [[decision-todo-por-obra]]: aunque la "memoria" es transversal al cliente, la vista principal sigue siendo `/obra/:id`. Esta pantalla se ofrece como **profundización transversal** cuando hace falta.

## Cómo se hizo

### T1 — Rama
Branch `sprint-22-memoria-clientes` desde `sprint-21-contabilidad-blanco-negro`.

### T2 — Modelos

[backend/app/models.py](../../backend/app/models.py):

**`Cliente`** suma 6 columnas:
- `cbu` (String 30)
- `alias_bancario` (String 50)
- `condiciones_pago` (String 200) — ej. "30 días fecha factura"
- `contacto_secundario` (String 200)
- `preferencias` (Text)
- `last_interaction_at` (DateTime, indexed) — actualizado cuando se crea una nota

**`ClienteNota`** (tabla nueva):
```python
id, is_demo, cliente_id (FK CASCADE), autor_id (FK User),
texto: Text, importante: bool, created_at
```

`cliente_notas` agregada a `_DEMO_TABLES` en [security.py](../../backend/app/security.py).

Migración Alembic [c5e7f9a1b3d4](../../backend/alembic/versions/c5e7f9a1b3d4_sprint_22_memoria_cliente.py).

### T3 — Endpoints

[backend/app/routers/clientes.py](../../backend/app/routers/clientes.py) suma:

- `GET /api/clientes/{cid}/detalle` → `ClienteDetalleOut`:
  - Campos del cliente (incluye campos memoria).
  - `obras`: lista con ingresos cobrados/pendientes y saldo por obra.
  - `resumen_financiero`: agregados de todas las obras del cliente (cobrado, por cobrar, contratos, obras_en_curso/finalizadas).
  - `interacciones`: últimas 50 notas (renombrado para no chocar con `Cliente.notas` que es string libre del modelo viejo).
- `GET /api/clientes/{cid}/notas` — lista de notas.
- `POST /api/clientes/{cid}/notas` — crea nota. Actualiza `last_interaction_at`. Setea `autor_id` desde el user logueado.
- `DELETE /api/clientes/notas/{nid}` — borra (solo admin).

CRUD existente (`POST/PUT /api/clientes`) sigue funcionando y ahora acepta los campos nuevos.

### T4 — Frontend

**Modal de edición** [`Clientes.jsx`](../../frontend/src/pages/Clientes.jsx) suma sección **"Datos recurrentes (memoria)"** con inputs para CBU, alias bancario, condiciones de pago, contacto secundario y preferencias.

**Card de cliente**: click en la card lleva a `/clientes/:id` (no abre modal). Botón ✏️ pequeño abre el modal para edición rápida.

**Nueva página** [`ClienteDetalle.jsx`](../../frontend/src/pages/ClienteDetalle.jsx) en `/clientes/:id`:

- Header con nombre + razón social + última interacción.
- 4 BigStats: Contratos totales · Cobrado · Por cobrar · Obras (en curso / total).
- 3 tabs:
  - **Datos**: contacto, datos recurrentes (CBU/alias/condiciones), preferencias, notas internas.
  - **Obras**: tabla con código, nombre, estado, contrato, cobrado, por cobrar, saldo + link a `/obra/:id`.
  - **Notas**: form para anotar (con flag "importante"), lista con timestamp/autor, borrar.

[`ObraDetail.jsx`](../../frontend/src/pages/ObraDetail.jsx) ahora linkea el nombre del cliente a `/clientes/:id`.

## Cómo se usa

### Cargar la "memoria" de un cliente
1. `/clientes` → click ✏️ en la card → modal.
2. Scroll hasta sección **"Datos recurrentes"**.
3. Cargar CBU, alias, condiciones de pago, contacto secundario, preferencias.
4. Guardar.

### Ver el dossier completo de un cliente
1. `/clientes` → click en card → `/clientes/:id`.
2. **Datos** ve todo el perfil con datos bancarios y preferencias.
3. **Obras** ve todas sus obras con cobrado/pendiente.
4. **Notas** ve el historial de interacciones.

### Anotar una llamada / reunión
1. `/clientes/:id` → tab **Notas** → escribir texto → opcional ⭐ importante → Anotar.
2. Queda guardado con fecha/autor.
3. `last_interaction_at` del cliente se actualiza automáticamente.

### Desde una obra
- `/obra/IDS` → header → click en el nombre del cliente → va a su detalle.

## Tests

[backend/tests/test_clientes_memoria.py](../../backend/tests/test_clientes_memoria.py) — 14 casos:
- Crear y leer cliente con campos memoria.
- `GET /detalle` con estructura completa.
- Resumen financiero agrega cobrado/pendiente correctamente de varias obras + movimientos.
- Crear nota (normal y con flag importante).
- Crear nota actualiza `last_interaction_at`.
- Listado de notas en orden descendente (con tiebreaker por id).
- Validaciones: `cliente_id` del body debe coincidir con el path; 404 si cliente no existe.
- Borrar nota; solo admin puede borrar (403 supervisor).
- 404 si cliente del detalle no existe.

Suite total: **174/174 verde**.

## Deuda pendiente

- **Autocompletado al cargar movimientos**: tener CBU/alias guardado no auto-rellena el medio de pago todavía. Próximo refinamiento.
- **Búsqueda en notas**: si crecen mucho, agregar `?q=texto`. Hoy se muestran las últimas 50.
- **Edición de nota**: hoy solo se crea y se borra. Si se necesita editar, agregar PATCH.
- **Notificaciones por importancia**: las notas con `importante=true` no disparan nada todavía. Cuando se quiera, conectar con el bot.
- **El campo `notas` viejo del Cliente (string libre) sigue ahí** — se muestra en el tab Datos como "Notas internas". Coexiste con la nueva tabla `cliente_notas` (renombrada a `interacciones` en el output del detalle).
