# 📖 Guía completa del proyecto — RCA. Plataforma

> Documento orientado a entender **qué es el proyecto, cómo está organizado y por qué cada sección existe**.
> Para el plan de tareas por sprint, ver [PLAN_ACCION.md](PLAN_ACCION.md).

---

## 🎯 ¿Qué es esto?

**RCA. — Plataforma de gestión integral de obras de construcción**, con dos capas:

1. **Capa financiera "seria"** (corazón del producto) — sigue el doc *"Modelo de gestión de gastos de obra v1.0"*: clientes, régimen fiscal, etapas, movimientos en tabla única (ingresos/egresos), aportes de socios, comprobantes AFIP con CAE, retenciones, flujo de caja, descalce fiscal.
2. **Capa lúdica/operativa** (overlay opcional) — cuadrillas con XP/nivel, frentes, órdenes (quests), feed de eventos. Conservada del modelo viejo "videojuego". **No contamina** los reportes financieros.

Ambas capas operadas por un **Operario IA conversacional** (Claude Sonnet 4.5 con tool-use) accesible vía chat web flotante (y a futuro por WhatsApp).

**Branding:** *Diseño · Construcción · Servicio*. Estética minimalista estilo Apple keynote, paleta tierra-noche (navy + olive + bone).

---

## 🏗️ Arquitectura general

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React 18 + Vite + Tailwind)                  │
│  http://localhost:5175                                  │
│  - Páginas: WorldMap, ObraDetail, Finanzas, etc         │
│  - Chat IA flotante (AgentChat)                         │
│  - JWT en localStorage, axios interceptor               │
└────────────────────┬────────────────────────────────────┘
                     │ REST + Bearer JWT
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Backend (FastAPI + SQLAlchemy)                         │
│  http://localhost:8010                                  │
│  - 18 routers                                           │
│  - Agente IA con loop tool-use                          │
│  - SQLite (default) / Postgres opcional                 │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴───────────┐
        ▼                        ▼
   ┌──────────┐           ┌──────────────┐
   │ SQLite   │           │ Anthropic API │
   │ fielddata│           │ Claude Sonnet │
   └──────────┘           └──────────────┘
```

**Stack:**
- Backend: FastAPI 0.110 + SQLAlchemy 2.0 + SQLite + Pydantic 2.6 + JWT/bcrypt + Anthropic SDK
- Frontend: React 18 + Vite 5.4 + Tailwind 3 + React Router 6 + Lucide + Axios
- WhatsApp: Webhook `/api/whatsapp/inbound` listo para n8n (parser keyword, será reemplazado por agente IA)

---

## 📁 Estructura del repo y el porqué de cada sección

### Raíz

| Archivo / carpeta | Para qué sirve |
|---|---|
| [README.md](../README.md) | Doc principal con concepto, stack, login demo, roadmap |
| [ROADMAP.md](ROADMAP.md) | **Plan vivo**. Acá se decide qué viene. Es la fuente de verdad de los sprints |
| [SETUP.md](../SETUP.md) | Cómo levantar el proyecto en una PC nueva (Win/Mac/Linux), `.env`, troubleshooting |
| [QUICK_START.md](QUICK_START.md) | Versión "30 segundos" para correrlo |
| [GUIA_ONBOARDING.md](GUIA_ONBOARDING.md) | Tour paso a paso de la UI para usuarios nuevos |
| [ESTRUCTURA_PLATAFORMA.md](ESTRUCTURA_PLATAFORMA.md) | Documentación técnica completa: modelos, paleta, componentes, rutas, flujos |
| [TEMPLATE_PLATAFORMA.md](TEMPLATE_PLATAFORMA.md) | Spec original del modelo financiero (lo que se implementó en Sprint A+B) |
| [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) | Checklist QA |
| [PLAN_ACCION.md](PLAN_ACCION.md) | Plan detallado por sprint (este documento es el complemento) |
| [GUIA_PROYECTO.md](GUIA_PROYECTO.md) | Este archivo |
| [setup.sh](../setup.sh) / [setup.bat](../setup.bat) | Bootstrap one-shot: venv + pip + npm + seed + `.env` |
| [start-backend.bat](../start-backend.bat) / [start-frontend.bat](../start-frontend.bat) | Launchers Windows; validan venv/node_modules |

---

### `backend/`

```
backend/
├── run.py                      # Entry point uvicorn
├── requirements.txt
├── docker-compose.yml          # Postgres opcional (puerto 5433)
├── .env.example                # Vars: DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY...
├── scripts/reset_db.py         # Drop all + recreate + seed
└── app/
    ├── main.py                 # FastAPI app + CORS + registro de routers
    ├── database.py             # Engine + SessionLocal + Base
    ├── security.py             # JWT, bcrypt, ADMIN_ROLES, get_current_user
    ├── models.py               # 18 modelos SQLAlchemy + enums + eventos
    ├── schemas.py              # Pydantic in/out
    ├── seed.py                 # Datos demo realistas
    ├── routers/
    │   ├── auth.py             # /api/auth/login, register, me
    │   ├── users.py            # /api/users CRUD
    │   ├── regimenes_fiscales.py  # RI / MT / EX
    │   ├── clientes.py         # CRUD clientes
    │   ├── obras.py            # CRUD obras + /dashboard/{oid} + frentes
    │   ├── etapas.py           # CRUD etapas con cascada R5
    │   ├── movimientos.py      # ★ TABLA CENTRAL — saldo, flujo-caja, cheques, descalce
    │   ├── aportes.py          # Aportes + R2 (ingreso espejo) + devolución
    │   ├── comprobantes.py     # AFIP (FC_A/B/C, NC, ND, Recibo, Remito) con validación
    │   ├── cuadrillas.py       # capa lúdica
    │   ├── materiales.py       # inventario + alertas stock bajo
    │   ├── proveedores.py
    │   ├── ordenes.py          # quests con XP
    │   ├── eventos.py          # feed
    │   ├── dashboard.py        # /api/dashboard/hud — big numbers globales
    │   ├── whatsapp.py         # webhook /api/whatsapp/inbound (parser keyword)
    │   └── agent.py            # /api/agent/chat, /reset, /actions
    └── agent/
        ├── orchestrator.py     # Loop tool-use con Claude
        └── tools.py            # 16 tools de solo lectura + schemas Anthropic
```

#### Modelos clave (en [backend/app/models.py](../backend/app/models.py))

- **`User`** — auth + xp + onboarding_step.
- **`RegimenFiscal`** — RI, Monotributo, Exento. Define IVA default, si aplica IIBB/Ganancias.
- **`Cliente`** — CUIT, razón social, régimen fiscal.
- **`Obra`** — núcleo del modelo. Tiene `cliente_id`, `regimen_fiscal_id`, `tipo_facturacion` (TOTAL_BLANCO/NEGRO/MIXTA/SIN_DEFINIR), `monto_contrato`. **Reemplaza** el viejo campo `presupuesto_consumido`.
- **`EtapaObra`** — divide la obra en etapas (Anticipo, Etapa 1, Final) con monto contractual y estado (PENDIENTE→EN_EJECUCION→EJECUTADA→FACTURADA→COBRADA).
- **`MovimientoObra`** — ★ **tabla central**. Cada fila es un INGRESO o EGRESO. Saldo = SUM(INGRESO) - SUM(EGRESO), sin filtrar por estado (R1).
- **`AporteSocio`** — préstamos internos con obligación de devolución.
- **`Comprobante`** — datos AFIP (FC_A/B/C, NC, ND, Recibo X, Remito) con CAE.
- **`RetencionSufrida`** — Ganancias, IIBB, IVA, SUSS.
- **`NotaObra`** — observaciones libres por obra o por movimiento.
- **Capa lúdica:** `Frente`, `Cuadrilla`, `Material`, `MovimientoMaterial`, `Proveedor`, `OrdenTrabajo`, `Evento`.
- **Agente IA:** `AgentSession` (historial), `AgentAction` (audit log).

#### Reglas de negocio implementadas (R1–R5)

- **R1** — saldo NO se filtra por estado. `CONFIRMADO` y `A_REVISAR` cuentan igual.
- **R2** — alta de aporte crea movimiento espejo INGRESO automáticamente (ver [aportes.py:46](../backend/app/routers/aportes.py#L46)).
- **R3** — cheques propios "salen" en `fecha_vto_cheque`, no en fecha de emisión (ver `flujo_proyectado` en [movimientos.py:140](../backend/app/routers/movimientos.py#L140)).
- **R4** — descalce fiscal: egresos con factura > ingresos con factura, por obra (ver [movimientos.py:224](../backend/app/routers/movimientos.py#L224)).
- **R5** — etapa pasada a COBRADA con aportes pendientes deja nota automática.

#### Agente IA (`backend/app/agent/`)

- [orchestrator.py](../backend/app/agent/orchestrator.py) — loop tool-use, max 8 iteraciones, historial truncado a 30 mensajes, sesión persistente por user.
- [tools.py](../backend/app/agent/tools.py) — 16 tools de **solo lectura** registradas:
  - `dashboard_hud` — big numbers globales
  - `listar_obras` / `obtener_obra` — obras con cliente, saldo, etapas
  - `listar_clientes` / `listar_etapas`
  - `listar_movimientos` — con filtros por tipo, categoría, estado
  - `saldo_obra` / `flujo_caja_obra` — financiero por obra
  - `aportes_pendientes` / `cheques_a_vencer` — alertas
  - `descalce_fiscal` — solo admin/finanzas
  - `alertas_stock_bajo` / `listar_proveedores` / `listar_cuadrillas`
  - `eventos_recientes` — feed
  - `listar_usuarios` — solo admin

#### Endpoints REST principales

| Router | Prefix | Endpoints clave |
|--------|--------|-----------|
| `auth` | `/api/auth` | `POST /login`, `POST /register`, `GET /me` |
| `users` | `/api/users` | CRUD |
| `regimenes_fiscales` | `/api/regimenes-fiscales` | RI / MT / EX |
| `clientes` | `/api/clientes` | CRUD |
| `obras` | `/api/obras` | CRUD + `/{id}/dashboard` |
| `etapas` | `/api/etapas` | CRUD con cascada R5 |
| `movimientos` | `/api/movimientos` | CRUD + `/obra/{id}/saldo` + `/flujo-caja` + `/flujo-proyectado` + `/cheques-a-vencer` + `/descalce-fiscal` |
| `aportes` | `/api/aportes` | CRUD + `/{id}/devolucion` |
| `comprobantes` | `/api/comprobantes` | CRUD AFIP |
| `cuadrillas` `materiales` `proveedores` `ordenes` `eventos` | `/api/...` | CRUD capa lúdica |
| `dashboard` | `/api/dashboard` | `GET /hud` |
| `whatsapp` | `/api/whatsapp` | webhook |
| `agent` | `/api/agent` | `POST /chat`, `POST /reset`, `GET /actions` |

**Docs interactivas:** http://localhost:8010/docs (Swagger UI)

---

### `frontend/`

```
frontend/
├── package.json                # React 18, Vite 5, Tailwind 3, lucide-react, axios
├── vite.config.js              # puerto default 5175 (no 5173 por choque con OPTIMIZAR)
├── tailwind.config.js          # paleta RCA (navy/olive/leather/bone) + tokens
└── src/
    ├── main.jsx                # mount React
    ├── App.jsx                 # Routes + ProtectedRoute
    ├── index.css               # Tailwind + utilities .hero-title, .card, .btn-*, .glass
    ├── components/
    │   ├── HUD.jsx             # Top nav glass con big numbers (saldo, cheques, alertas)
    │   ├── Logo.jsx            # "RCA." con punto bloque oliva
    │   ├── AgentChat.jsx       # Chat flotante del Operario IA
    │   └── Layout/
    │       ├── Layout.jsx      # HUD + Sidebar + main
    │       ├── Sidebar.jsx     # Nav lateral por rol
    │       └── ProtectedRoute.jsx
    ├── context/
    │   └── AuthContext.jsx     # user, login, logout, isAdmin, hasFinanzas
    ├── utils/
    │   └── api.js              # axios + interceptor JWT
    └── pages/
        ├── Login.jsx           # hero bicolor + form
        ├── Register.jsx        # primer usuario auto-rol super_admin
        ├── WorldMap.jsx        # grilla de obras con health-dot + filtros + modal nueva obra
        ├── ObraDetail.jsx      # micro-mundo: hero + progress + frentes + órdenes + actividad
        ├── Cuadrillas.jsx      # CRUD equipos RPG
        ├── Materiales.jsx      # inventario filtrable + alertas stock
        ├── Proveedores.jsx     # red con rating
        ├── Ordenes.jsx         # quest log global
        ├── Feed.jsx            # cronología de eventos
        ├── Finanzas.jsx        # 4 big numbers + alertas + breakdown por categoría/obra
        └── Equipo.jsx          # gestión usuarios
```

#### Rutas y permisos

| Path | Página | Acceso |
|---|---|---|
| `/login` `/register` | público | — |
| `/world` | WorldMap | autenticado |
| `/obra/:id` | ObraDetail | autenticado |
| `/ordenes` `/feed` | — | autenticado |
| `/cuadrillas` `/materiales` `/proveedores` `/equipo` | — | admin |
| `/finanzas` | Finanzas | admin_finanzas |

#### Sistema de diseño (Apple minimalist)

**Paleta RCA:**
- Navy `#1E2B5E` — texto principal, primary
- Olive `#8A9A5B` — accent, eyebrows
- Military `#3D4F1E` — success-dark
- Leather `#6B4C30` — warnings
- Sand `#A8845F` — warn secondary
- Tan `#C4B99A` — borders, muted
- Bone `#EEEAE3` — surfaces

**Tipografía:** Inter (fallback SF Pro Display). Tracking ultra-tight para heroes (-0.04em).

**Utilidades reusables (en `index.css`):**
- `.hero-eyebrow` — uppercase tracking-[0.22em] olive-700
- `.hero-title` — display bold tracking-tight
- `.hero-sub` — subtítulo light muted
- `.card` `.card-hover` `.card-flat` — radius 3xl
- `.btn-primary` `.btn-secondary` `.btn-ghost` `.btn-accent` `.btn-danger` `.btn-link` — pill shape
- `.input` — radius 2xl con focus ring navy/5
- `.chip-navy` `.chip-olive` `.chip-warn` etc — pills informativos
- `.glass` — backdrop-blur 2xl + saturate 150

---

## 🔐 Autenticación y roles

### Flow JWT
```
1. POST /api/auth/login { email, password }
   → { access_token, user }
2. localStorage.setItem('rca_token', token)
3. Axios interceptor: Authorization: Bearer ${token}
4. Backend valida en cada request via dependencies (security.py)
```

### Matriz de permisos (objetivo Sprint 7)

| Recurso | super_admin | admin_finanzas | admin | supervisor | usuario_bot |
|---------|:-----------:|:--------------:|:-----:|:----------:|:-----------:|
| Ver obras | ✓ | ✓ | ✓ | ✓ (asignadas) | ✗ |
| Crear obra | ✓ | ✓ | ✓ | ✗ | ✗ |
| Cuadrillas | ✓ | — | ✓ | ver | ✗ |
| Materiales | ✓ | — | ✓ | ver | ✗ |
| Proveedores | ✓ | — | ✓ | ✗ | ✗ |
| Finanzas | ✓ | ✓ | — | ✗ | ✗ |
| Usuarios | ✓ | — | ✓ | ✗ | ✗ |
| Órdenes | ✓ | ver | ✓ | ✓ | solo asignadas |
| Feed | ✓ | ✓ | ✓ | ✓ | post via WhatsApp |

> **Estado actual:** `super_admin` único activo. La jerarquía está modelada pero gateada hasta Sprint 7.

### Helpers en `AuthContext`
```js
const { user, login, logout, isAdmin, hasFinanzas } = useAuth()
```

---

## 🚀 Cómo correrlo

```bash
# Una vez (Windows)
setup.bat            # crea venv, instala deps, hace seed, genera .env
# editar backend/.env y poner ANTHROPIC_API_KEY

# Cada vez
start-backend.bat    # → http://localhost:8010
start-frontend.bat   # → http://localhost:5175

# Login demo
admin@rca.com / demo1234   # super_admin (seed nuevo)
```

URLs útiles:
- **App**: http://localhost:5175
- **Swagger**: http://localhost:8010/docs
- **Health**: http://localhost:8010/health → `{"status":"ok","brand":"RCA.","version":"0.4.0"}`

### Variables de entorno (`backend/.env`)

```env
DATABASE_URL=sqlite:///./fielddata.db
SECRET_KEY=cambialo-por-un-string-largo-random
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5175,http://localhost:5173,http://localhost:5174
WHATSAPP_WEBHOOK_TOKEN=set-shared-token-with-n8n
ANTHROPIC_API_KEY=sk-ant-api03-...
AGENT_MODEL=claude-sonnet-4-5
# RELOAD=1   # opcional, reload uvicorn (rompe en OneDrive)
# PORT=8010  # opcional
```

### Reset de base de datos

```bash
cd backend
python scripts/reset_db.py    # drop all + recreate + seed
```

---

## 🌱 Datos del seed

- **3 regímenes fiscales:** RI, Monotributo, Exento
- **4 usuarios:** admin (super_admin), socio_a, socio_b, kevin (capataz/supervisor)
- **3 clientes:** Colegio Domingo Savio (público RI), Constructora San Pedro SA (privado RI), Familia García (particular)
- **2 obras:**
  - **IDS — Domingo Savio** TOTAL_BLANCO, $12.5M, 4 etapas
  - **SP — San Pedro** MIXTA, $8.2M, 3 etapas
- **Movimientos:** anticipos cobrados, MO semanal, materiales con factura A, subcontrato pagado con cheque a vencer
- **1 aporte** de socio + ingreso espejo automático
- **Capa lúdica:** 2 cuadrillas (Los Maestros, Volt Power), frentes en cada obra, materiales y proveedores demo

---

## 🤖 Operario IA (centro de mando)

Botón flotante "Operario IA" abajo a la derecha en cualquier página autenticada.

**Sprint 1 (actual) — solo lectura:** dashboard global, listar/detalle de obras, órdenes, cuadrillas, materiales (con alertas de stock bajo), proveedores, eventos recientes, finanzas por obra, usuarios. Permisos por rol del usuario logueado. Audit log en tabla `agent_actions`. Historial persistente por usuario en `agent_sessions`.

**Próximos sprints:** escritura con confirmación humana (crear órdenes, registrar gastos/materiales, cerrar órdenes), reemplazo del parser de WhatsApp por el mismo agente, Vision IA para tickets/fotos, resumen semanal proactivo.

**Endpoints:** `POST /api/agent/chat`, `POST /api/agent/reset`, `GET /api/agent/actions`.

---

## 📞 ¿Por dónde seguimos?

El roadmap recomienda explícitamente **Sprint 2 — Operario IA con escritura**:

> *"El cuello de botella más grande hoy es que el agente solo lee — desbloquea el valor real de la plataforma."*

Plan detallado en [PLAN_ACCION.md](PLAN_ACCION.md).

---

## 🧠 Decisiones técnicas tomadas (extraídas del roadmap)

| Decisión | Razón |
|----------|-------|
| Mantener SQLAlchemy (no migrar a Prisma) | Backend Python ya funciona; cambiar ORM duplica trabajo sin beneficio claro |
| Integer PKs (no UUID del doc) | Sin breaking change en relaciones existentes; UUIDs se pueden agregar como campos públicos después |
| Eventos SQLAlchemy (no triggers PG) | Portable a SQLite, testeable, no atado a un motor |
| SQLite por default + PG opcional vía Docker | Onboarding de PC nueva sin Docker; producción con PG con 1 línea de cambio |
| Capa lúdica conservada | Diferencia visual del producto, no afecta finanzas |
| Reset total de DB (no migración de datos viejos) | Datos de prueba; el costo de migrar no se justifica |
| `super_admin` único hasta tener flujo claro de roles | Evita gating prematuro mientras itera la UI |
| Claude Sonnet 4.5 default, configurable vía `AGENT_MODEL` | Costo razonable, soporte tool-use sólido; user puede cambiar a 4.6 / Haiku |
