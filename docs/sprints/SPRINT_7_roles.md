# Sprint 7 — Roles y permisos completos + tabla Socio

> Estado: ✅ cerrado · suite pytest **49/49** verde

## Requisitos

Desde el seed nuevo del Sprint A+B, todos los usuarios reales eran `super_admin`. La plataforma tenía los 5 roles definidos en el enum (`super_admin`, `admin_finanzas`, `admin`, `supervisor`, `usuario_bot`) pero solo dos checks granulares en `security.py`: `require_admin` y `require_finanzas`. El roadmap pedía:

> *Reactivar jerarquía de roles más allá de super_admin.*
> *Matriz de permisos por endpoint en código + tests.*
> *Tabla Socio propia (hoy se usa User con rol admin_finanzas como proxy para aportes).*

**Objetivo:** que los 5 roles tengan scope distinto, sin que el agente IA o el sidebar muestren cosas que el usuario no debería ver. Y separar la entidad "Socio" (con CUIT, participación, datos fiscales) del concepto "User" (cuenta con login).

## Cómo se hizo

### T1 — Tabla `Socio` propia

En `backend/app/models.py`:

```python
class Socio(Base):
    __tablename__ = "socios"
    id, nombre, apellido, cuit, email, telefono,
    participacion_pct (Numeric 5,2),
    activo (Boolean),
    notas,
    user_id (FK opcional a users — vínculo si el socio tiene cuenta),
    created_at, updated_at
```

`AporteSocio.socio_id` cambió de `FK users.id` → `FK socios.id`. El vínculo `User ←→ Socio` queda opcional: un socio puede no tener cuenta de login (típico para inversionistas externos), y un user puede no ser socio.

**Migración Alembic**: como SQLite con `batch` requiere nombres en las constraints para dropearlas (y la FK original no los tenía), se hizo un reset completo regenerando la migración inicial. Resultado: una sola revisión `9e8a83189515 initial schema (sprint 0..7)` que captura las 21 tablas finales.

### T2 — Seed actualizado

`backend/app/seed.py`:
- Crea 2 socios: **Tomás Martínez** (50%) y **Lucía Fernández** (50%), cada uno vinculado a su user correspondiente.
- El aporte demo de SP ahora apunta a `socio_entity_a.id` (la tabla nueva), no a `socio_a.id` (User).

### T3 — Matriz de permisos

`backend/app/security.py` — 4 conjuntos claros:

| Constante | Roles | Para qué |
|---|---|---|
| `ADMIN_ROLES` | super_admin, admin, admin_finanzas | Crear/editar recursos, invitar usuarios |
| `FINANZAS_ROLES` | super_admin, admin_finanzas | Datos fiscales sensibles (descalce, comprobantes confidenciales) |
| `SUPERVISOR_ROLES` | super_admin, admin, admin_finanzas, supervisor | Cargar movimientos básicos, reportar avance, ver obras asignadas |
| `WEB_BLOCKED_ROLES` | usuario_bot | NUNCA acceden vía web |

Tres dependency-helpers:
- `require_admin(user)` — ADMIN_ROLES
- `require_finanzas(user)` — FINANZAS_ROLES
- `require_supervisor(user)` — SUPERVISOR_ROLES
- `require_role(*roles)` — factory genérica para casos puntuales

**Cambio crítico** en `get_current_user`:
```python
if user.role in WEB_BLOCKED_ROLES:
    raise HTTPException(403, "Este rol solo opera vía WhatsApp")
```

Esto significa que un `usuario_bot` puede tener JWT (para el flujo de WhatsApp), pero apenas intenta llamar a cualquier endpoint protegido por `get_current_user`, devuelve 403. El webhook `/api/whatsapp/inbound` valida con `WHATSAPP_WEBHOOK_TOKEN` (token compartido), no con JWT, así que sigue funcionando.

**Corrección de permiso encontrado por el test**: el endpoint `GET /api/movimientos/descalce-fiscal` usaba `require_admin` pero debía ser `require_finanzas`. El descalce expone créditos fiscales de IVA — es info sensible que un PM (`admin`) no necesita ver. Cambio aplicado.

### T4 — Router CRUD `/api/socios`

`backend/app/routers/socios.py` con:
- `GET /api/socios?activos_solo=true` — listar (cualquier user autenticado).
- `POST /api/socios` — crear (admin only, valida CUIT único).
- `GET /api/socios/{id}` — detalle.
- `PUT /api/socios/{id}` — editar (admin only).
- `DELETE /api/socios/{id}` — borrar (admin only, bloquea si tiene aportes; marcalo inactivo en su lugar).

Schemas Pydantic `SocioIn` / `SocioOut` agregados en `schemas.py`.

Router de aportes (`backend/app/routers/aportes.py`) ahora valida que el socio existe en la tabla `socios` (no en `users`) y que está activo.

### T5 — Tests de matriz

`backend/tests/test_roles.py` con **12 tests** cubriendo:

| Caso | Verifica |
|---|---|
| `usuario_bot_no_accede_a_endpoints_web` | Para 5 endpoints distintos, status=403 con mensaje "whatsapp" |
| `supervisor_lee_obras` | GET /api/obras = 200 |
| `supervisor_no_crea_obra` | POST /api/obras = 403 |
| `supervisor_no_accede_descalce_fiscal` | GET descalce = 403 |
| `admin_pm_crea_obra` | POST /api/obras = 201 |
| `admin_pm_no_accede_descalce_fiscal` | GET descalce = 403 (admin NO está en FINANZAS_ROLES) |
| `admin_finanzas_accede_descalce` | GET descalce = 200 |
| `admin_finanzas_crea_obra` | POST /api/obras = 201 (también está en ADMIN_ROLES) |
| `super_admin_accede_a_todo` | 6 endpoints distintos = 200 |
| `crud_socios` | Ciclo completo CREATE → CUIT duplicado rechaza → READ → LIST → UPDATE → DELETE |
| `supervisor_lee_socios_pero_no_crea` | GET = 200, POST = 403 |
| `borrar_socio_con_aportes_rechaza` | DELETE con aportes vinculados = 400 |

**Suite total: 49/49** (36 anteriores + 13 nuevos del Sprint 7).

### T6 — UI página `/socios`

`frontend/src/pages/Socios.jsx` con el mismo patrón de `Clientes.jsx`:
- 3 big numbers: socios activos, participación total (verde si suma 100%, marrón si no), sin asignar.
- Pills filtro: Activos / Todos.
- Cards con datos del socio (nombre, CUIT, email, teléfono, % participación, link a User).
- Modal de edición/creación con todos los campos + soft-delete vía toggle "activo".
- Botón hard-delete que el backend rechaza si hay aportes vinculados.

Sidebar: nuevo item **Socios** bajo Finanzas (sólo visible con `hasFinanzas=true`). Ícono `Briefcase` para diferenciarlo de Cuadrillas (que usa `Users`).

Ruta en `App.jsx`: `<Route path="/socios" element={<P requireFinanzas><Socios/></P>}>`.

### Bug fix colateral

Sentry lazy import del Sprint 8 rompía Vite porque hacía análisis estático del `import('@sentry/react')` aunque no estuviera instalado. Fix: usar `const pkg = '@sentry/' + 'react'; import(pkg)` — Vite no puede resolver imports con variable runtime, así que no intenta cargar el módulo en dev. Cuando `@sentry/react` esté instalado de verdad (producción con DSN), el browser lo carga en runtime.

## Cómo se usa

### Para un admin

1. **Ver/gestionar socios** → Sidebar → Finanzas → Socios.
2. **Crear socio**: botón "Nuevo socio", llenar nombre + CUIT + participación. Opcionalmente vincular a un User existente.
3. **Crear aporte**: ahora el dropdown de "Socio" en `/aportes` muestra socios reales (con CUIT y nombre completo), no users.
4. **Desactivar socio sin perder historial**: editar → desmarcar "Socio activo" → guardar. Sigue apareciendo en aportes históricos pero no en el dropdown.

### Para configurar permisos

En cualquier endpoint nuevo:
```python
from app.security import require_finanzas, require_supervisor, require_role
from app import models

# Endpoint solo finanzas
@router.get("/secreto", dependencies=[Depends(require_finanzas)])

# Endpoint que necesita supervisor o superior
@router.post("/cargar", dependencies=[Depends(require_supervisor)])

# Endpoint que requiere rol específico (factory)
@router.delete("/peligroso",
    dependencies=[Depends(require_role(models.UserRole.super_admin))])
```

### Para invitar a alguien con rol específico

Hoy se puede via API:
```bash
curl -X POST http://localhost:8010/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan", "last_name": "Pérez",
    "email": "juan@empresa.com", "password": "xxx",
    "role": "supervisor", "phone": "+5491100000099"
  }'
```

La UI dedicada para invitar con rol elegible (`/equipo` con dropdown de rol) queda como deuda menor para un sprint futuro.

## Tests realizados

- ✅ `alembic upgrade head` aplica limpio sobre DB vacía.
- ✅ `reset_db.py` ejecuta sin errores y genera 2 socios + 1 aporte del seed.
- ✅ `pytest` → **49/49 passed** (12 nuevos + 37 que ya pasaban).
- ✅ Test visual: `/socios` carga con los 2 socios del seed, big numbers correctos (100% participación), sidebar muestra "Socios" activo.

## Estado y deuda

✅ **Cerrado:** modelo Socio + matriz de permisos + UI + tests.

⚠️ **Deuda menor que quedó:**
- La UI de `/equipo` (lista de Users) no tiene aún dropdown para cambiar rol ni botón "invitar" con selector — sólo se hace por API. Bajo impacto, hay 1 endpoint que ya funciona.
- El `socio.user_id` permite vincular pero no hay UI para crear ambas entidades en un solo paso. Es 2-step manual hoy.
- El supervisor ve TODAS las obras hoy. La lógica "ver solo obras asignadas" del roadmap requiere otra tabla `obras_asignadas (user_id, obra_id)` + filtrado en queries. Queda para Sprint 7.1 si se requiere.

📌 **Cómo se conecta con otros sprints:**
- El agente IA del **Sprint 2** ya respeta los permisos por rol (cada tool chequea `user.role in ADMIN_ROLES` cuando aplica).
- Los **slash commands del Sprint 4** funcionan para cualquier rol con teléfono cargado. Cuando se reactive el supervisor, el comando `/gasto` ya respeta que solo crea movimientos `A_REVISAR` (no `CONFIRMADO`).
- La página `/socios` sigue el mismo patrón visual y de gating (`requireFinanzas`) que **Sprint 3** introdujo.
