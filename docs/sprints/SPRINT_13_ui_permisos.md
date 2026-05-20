# Sprint 13 — UI cleanup + permisos granulares

> Estado: ✅ cerrado · suite pytest **103/103** verde

## Requisitos

Notas de reunión 2026-05-19:

1. **Sacar puntos** de los títulos de las secciones (UI cleanup masivo).
2. **Panel de acceso a X secciones a los usuarios.** Tabla check para dar accesos a X secciones de la página y poder elegir X obras para mostrar (caso "arquitecta": solo ve 2 obras y solo unas pocas secciones).

## Cómo se hizo

### T1 — Rama

Branch `sprint-13-ui-permisos` desde `dev`.

### T2 — Modelos

[backend/app/models.py](../../backend/app/models.py):

```python
SECCIONES = (
    "obras", "ordenes", "feed",
    "cuadrillas", "materiales", "presupuestos", "proveedores",
    "finanzas", "movimientos", "aportes", "comprobantes", "clientes", "socios",
    "equipo", "mensajes",
)

class PermisoUsuario(Base):
    # blacklist por seccion: si no hay fila, la seccion es accesible
    user_id, seccion, allowed: bool

class PermisoUsuarioObra(Base):
    # whitelist de obras: si no hay filas, ve todas
    user_id, obra_id
```

Migración Alembic [8a1b3c2d5e0f](../../backend/alembic/versions/8a1b3c2d5e0f_sprint_13_permisos_granulares.py).

### T3 — Guards en `security.py`

[backend/app/security.py](../../backend/app/security.py) suma 4 helpers:

- `user_section_allowed(db, user, seccion) -> bool` — admin siempre `True`; otro rol consulta `PermisoUsuario`.
- `user_visible_obra_ids(db, user) -> list[int] | None` — admin siempre `None` (ve todas); otro rol consulta `PermisoUsuarioObra` (None si no tiene filas, lista si tiene).
- `scope_obras(query, model_obra, db, user)` — aplica filter por whitelist o no-op para admin.
- `require_section(seccion)` — dependency factory para gatear endpoints.

**Decisión clave:** los roles administrativos (`super_admin`, `admin`, `admin_finanzas`) tienen **bypass** anti-lockout. La idea es que el sistema de permisos extra **sumara** restricciones a roles operativos (`supervisor`, `usuario_bot`) sin riesgo de dejar a un admin sin acceso.

### T4 — Aplicar scope a `/api/obras`

[backend/app/routers/obras.py](../../backend/app/routers/obras.py): `list_obras` y `get_obra` ahora aplican `scope_obras` además del `scope_demo` existente. Una supervisora con whitelist `[obra_id=7]` solo ve la obra 7.

### T5 — Endpoints de permisos

[backend/app/routers/users.py](../../backend/app/routers/users.py):

- `GET /api/users/me/permisos` → cualquier user logueado consulta sus propios permisos (el frontend lo usa para armar el sidebar).
- `GET /api/users/{uid}/permisos` (admin) → permisos de un user específico.
- `PUT /api/users/{uid}/permisos` (admin) → setea secciones permitidas y obras visibles.

**Importante:** `/me/permisos` se declara ANTES que `/{uid}/permisos` para que FastAPI no intente parsear `"me"` como `int`.

Payload PUT:
```json
{
  "secciones_permitidas": ["obras", "feed"],
  "obras_visibles_ids": [7, 12]   // null = ve todas
}
```

### T6 — Página `/equipo/:uid/permisos` (frontend)

[frontend/src/pages/EquipoPermisos.jsx](../../frontend/src/pages/EquipoPermisos.jsx):

- Grilla de checkboxes agrupada por categoría (General · Recursos · Finanzas · Administración).
- Multi-select de obras con flag "Ver todas las obras" (whitelist).
- Botón Guardar con confirmación visual.

Botón "Permisos" agregado en [Equipo.jsx](../../frontend/src/pages/Equipo.jsx) al lado de "Vincular TG".

### T7 — Sidebar dinámico

[AuthContext.jsx](../../frontend/src/context/AuthContext.jsx) ahora carga `permisos` del user al loguearse via `/api/users/me/permisos` y expone `sectionAllowed(seccion)`.

[Sidebar.jsx](../../frontend/src/components/Layout/Sidebar.jsx) usa `show(seccion, requiereRol)` para combinar el chequeo de rol existente (`isAdmin` / `hasFinanzas`) con el de permisos granulares. Los headers de sección (Recursos, Finanzas, Administración) se ocultan si TODAS las entradas hijas están bloqueadas.

### T8 — UI cleanup: sacar puntos de títulos

Script Python en backend hizo regex sobre `frontend/src/pages/*.jsx`:

- `<h1 className="hero-title ...">Texto.</h1>` → `<h1 ...>Texto</h1>`
- `<h2 className="hero-title ...">Texto.</h2>` → `<h2 ...>Texto</h2>`

Casos con expresión ternaria (`{isNew ? 'Nuevo X.' : 'Editar X.'}`) corregidos a mano en [Clientes.jsx](../../frontend/src/pages/Clientes.jsx) y [Socios.jsx](../../frontend/src/pages/Socios.jsx).

15 archivos modificados.

## Cómo se usa

### Como admin: asignar permisos a una usuaria nueva (caso arquitecta)

1. Invitar al usuario desde `/equipo` (rol `supervisor`).
2. Clickear el botón **Permisos** en la fila.
3. Destildar las secciones que NO debe ver (ej. todo lo de Finanzas + Administración).
4. Destildar **"Ver todas las obras"** y tildar solo las obras que sí debe ver.
5. **Guardar cambios**.
6. La usuaria, al loguearse, ve solo esas secciones en el sidebar y solo esas obras en `/world`.

### Como dev: gatear un endpoint nuevo por sección

```python
from app.security import require_section

@router.get("/api/algo", dependencies=[Depends(require_section("finanzas"))])
def listar_algo():
    ...
```

Si el user no tiene permiso → 403.

## Tests

[backend/tests/test_permisos.py](../../backend/tests/test_permisos.py) — 13 casos:

- estado inicial (sin filas) → todas las secciones permitidas, ve todas las obras.
- bloquear secciones específicas, ver bloqueadas en respuesta.
- 400 ante sección u obra inexistente en el PUT.
- bypass de admin (filas `allowed=False` ignoradas).
- whitelist de obras: supervisor con 1 fila ve solo esa obra, admin ignora la fila.
- `scope_obras` filtra la query correctamente.
- `GET /api/obras` respeta la whitelist end-to-end.
- `/me/permisos` funciona para cualquier rol.
- non-admin no puede editar permisos de otros (403).

Suite total: **103/103 verde**.

## Deuda pendiente

- **Scope de obras en otros endpoints**: por ahora solo `list_obras` y `get_obra` aplican `scope_obras`. Endpoints derivados (movimientos, comprobantes, eventos por obra) heredan el filtro porque ya filtran por `obra_id`, pero un user con whitelist puede acceder directo a `/api/movimientos/123` si conoce el id. Mitigación parcial: el backend ya tiene `require_admin` en endpoints sensibles. Cierre completo: extender `scope_obras` a esos routers en S14/S15.
- **Endpoint `set_section_permission`** atómico: hoy se manda toda la lista. Si dos admins editan en paralelo, gana el último. Suficiente para el MVP.
- **Audit log**: no se registra quién cambió qué permiso. Si se necesita, agregar tabla `PermisoLog` en próximo sprint.
- **Bot Telegram**: no respeta `PermisoUsuarioObra` todavía. Cuando se implemente el slash `/req` (S17) habrá que aplicar el scope ahí también.
