# Sprint 17 — Requerimientos por obra

> Estado: ✅ cerrado · suite pytest **115/115** verde

## Requisitos

Nota de reunión 2026-05-19:

> "Por cada obra, agregar una sección llamada Requerimientos en la que si pasa algo imprevisto podés mandar un mensaje y que anote: *hacer tapial de 10 metros - 140 ladrillos, 10 cementos, 20 hierro, reboque X*."

Es decir: carga rápida de imprevistos/pedidos contra una obra, sin formulario largo. El bot manda `/req <obra> <texto>` y queda anotado.

## Cómo se hizo

### T1 — Rama

Branch `sprint-17-requerimientos` desde `sprint-13-ui-permisos` (necesita `scope_obras` para respetar la whitelist).

### T2 — Modelo

[backend/app/models.py](../../backend/app/models.py):

```python
class RequerimientoEstado(str, Enum):
    abierto = "abierto"
    resuelto = "resuelto"

class Requerimiento(Base):
    id, is_demo, obra_id, mensaje, estado, canal,
    created_by_id, resuelto_by_id, created_at, resuelto_at
```

`is_demo` para que el listener del Sprint 12 filtre automáticamente. Agregada a `_DEMO_TABLES` en [security.py](../../backend/app/security.py).

`requerimientos` agregado al catálogo `SECCIONES` para que se pueda permisar como cualquier otra sección del Sprint 13.

Migración Alembic [9b2c4d5e6f70](../../backend/alembic/versions/9b2c4d5e6f70_sprint_17_requerimientos.py).

### T3 — Endpoints

[backend/app/routers/requerimientos.py](../../backend/app/routers/requerimientos.py):

- `GET /api/obras/{oid}/requerimientos?estado=` — lista por obra. Valida acceso vía `scope_obras`.
- `GET /api/requerimientos?estado=&obra_id=` — lista global, filtrada por whitelist del user.
- `POST /api/requerimientos` — crea (canal=`web`).
- `PATCH /api/requerimientos/{rid}/resolver`
- `PATCH /api/requerimientos/{rid}/reabrir`
- `DELETE /api/requerimientos/{rid}`

Cada endpoint aplica `_filter_by_obras` para que un user con whitelist solo vea y actúe sobre requerimientos de sus obras.

### T4 — Slash `/req`

[backend/app/slash_commands.py](../../backend/app/slash_commands.py):

```
/req <obra> <mensaje>
```

Ejemplo:
```
/req IDS falta cemento, mando 5 bolsas mañana
```

Crea el requerimiento con `canal=whatsapp` (heredado de la convención del slash) y `created_by=user`. +3 XP al user.

### T5 — Frontend

Nueva pestaña **Requerimientos** en [ObraDetail.jsx](../../frontend/src/pages/ObraDetail.jsx):

- 3 BigStats: Abiertos · Resueltos · Total.
- Form inline para anotar uno nuevo (caja de texto + botón "Anotar").
- Filtro chips: todos / abierto / resuelto.
- Lista con punto de estado (leather=abierto, olive=resuelto), mensaje, fecha, canal, autor.
- Acciones por fila: **Resolver** / **Reabrir** / **Eliminar**.
- Hint visible: "También se puede mandar por Telegram con `/req {codigo} <mensaje>`".

El catálogo del [EquipoPermisos.jsx](../../frontend/src/pages/EquipoPermisos.jsx) ahora lista `requerimientos` en el grupo "General" — los admins pueden bloquear esa sección a un usuario.

## Cómo se usa

### Desde Telegram (caso del día)

```
/req IDS Tapial 10m: 140 ladrillos, 10 cementos, 20 hierro, reboque
```

El bot responde con `#id` del requerimiento y queda visible en la web.

### Desde la web

`/obra/:id` → tab **Requerimientos** → escribir mensaje → **Anotar**.

### Marcar resuelto

Botón **Resolver** en cada fila. Vuelve a aparecer con el ícono "olive" y la fecha de resolución.

## Tests

[backend/tests/test_requerimientos.py](../../backend/tests/test_requerimientos.py) — 12 casos:

- CRUD básico (crear, listar, filtrar por estado).
- 404 cuando la obra no existe.
- 422 cuando el mensaje está vacío.
- Resolver/reabrir (con `resuelto_by_id` y `resuelto_at`).
- Eliminar.
- Supervisor con whitelist solo ve sus obras (no las ajenas, 404 al pedirlas).
- Slash `/req` end-to-end (crea fila, valida args, integración con `/help`).

Suite total: **115/115 verde**.

## Deuda pendiente

- **Notificación a usuarios con permiso sobre la obra**: el plan original mencionaba notificar por Telegram a quienes tengan acceso a esa obra cuando se crea un requerimiento. Se difiere — necesita decidir si va por bot push (requiere Telegram activado) o también por mail.
- **Adjuntos**: no se aceptan fotos por ahora. Cuando se integre OCR de tickets (S18) habrá infra para esto.
- **Edición del mensaje**: hoy solo se puede eliminar y rehacer. Si se vuelve molesto, agregar PATCH del campo `mensaje`.
- **Priorización / etiquetas**: todo entra como "abierto" liso. Si emerge necesidad de urgencia/categoría, se puede agregar después.
