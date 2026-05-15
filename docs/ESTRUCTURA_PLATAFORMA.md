# 🏗️ RCA. — Documentación Técnica Completa

> **Diseño · Construcción · Servicio**
> Plataforma minimalista (estilo Apple) para gestión integral de obras de construcción.

---

## 📑 Índice

1. [Visión general](#-visión-general)
2. [Stack tecnológico](#-stack-tecnológico)
3. [Estructura de carpetas](#-estructura-de-carpetas)
4. [Sistema de diseño visual](#-sistema-de-diseño-visual)
5. [Backend — API & modelos](#-backend--api--modelos)
6. [Frontend — Páginas & componentes](#-frontend--páginas--componentes)
7. [Autenticación & roles](#-autenticación--roles)
8. [Flujos de usuario](#-flujos-de-usuario)
9. [Scripts & comandos](#-scripts--comandos)

---

## 🌐 Visión general

**RCA.** es una plataforma full-stack diseñada para que empresas constructoras gestionen:

- 🏢 **Obras** — cada una un "micro-mundo" con su propio estado, frentes y stats
- 👷 **Cuadrillas** — equipos con especialidad, eficiencia y nivel
- 📦 **Materiales** — inventario por categoría con alertas de stock
- 🚚 **Proveedores** — red evaluada con rating y plazos
- 📋 **Órdenes** — quests asignadas a cuadrillas con XP reward
- 💰 **Finanzas** — presupuestos consumidos vs comprometidos
- 📢 **Eventos** — actividad en tiempo real (web + WhatsApp bot)
- 👥 **Usuarios** — 4 roles con permisos diferenciados

**Filosofía de diseño:** mínimo visual, máximo significado. Tipografía generosa, paleta tierra-noche, transiciones suaves estilo Apple keynote.

---

## 🧩 Stack tecnológico

### Backend
| Tech | Versión | Propósito |
|------|---------|-----------|
| **FastAPI** | 0.110 | Framework web async |
| **SQLAlchemy** | 2.0 | ORM |
| **SQLite** | — | Base de datos (`fielddata.db`) |
| **Pydantic** | 2.6 | Validación de schemas |
| **Uvicorn** | 0.27 | ASGI server |
| **python-jose** | 3.3 | JWT auth |
| **passlib + bcrypt** | — | Hash de passwords |

### Frontend
| Tech | Versión | Propósito |
|------|---------|-----------|
| **React** | 18 | UI library |
| **Vite** | 5.4 | Bundler + HMR |
| **Tailwind CSS** | 3 | Utility-first styling |
| **React Router** | 6 | Routing client-side |
| **Lucide React** | — | Iconos SVG |
| **Axios** | — | HTTP client |
| **Inter font** | — | Tipografía (fallback SF Pro) |

---

## 📁 Estructura de carpetas

```
RCA/
├── start-backend.bat              # Launcher Windows (backend)
├── start-frontend.bat             # Launcher Windows (frontend)
├── README.md
├── GUIA_ONBOARDING.md             # Onboarding paso a paso
├── TESTING_CHECKLIST.md           # Checklist QA
├── QUICK_START.md                 # Quick reference
├── ESTRUCTURA_PLATAFORMA.md       # Este archivo
│
├── backend/
│   ├── run.py                     # Entry point (uvicorn)
│   ├── requirements.txt
│   ├── fielddata.db               # SQLite (auto-creada)
│   └── app/
│       ├── main.py                # FastAPI app + CORS
│       ├── database.py            # Engine + SessionLocal
│       ├── models.py              # 11 modelos SQLAlchemy
│       ├── schemas.py             # Pydantic schemas
│       ├── security.py            # JWT + password hash
│       ├── seed.py                # Datos iniciales
│       └── routers/
│           ├── auth.py            # /auth/* (login, register)
│           ├── users.py           # /api/users
│           ├── obras.py           # /api/obras + /api/obras/{id}/frentes
│           ├── cuadrillas.py      # /api/cuadrillas
│           ├── materiales.py      # /api/materiales + movimientos
│           ├── proveedores.py     # /api/proveedores
│           ├── ordenes.py         # /api/ordenes
│           ├── eventos.py         # /api/eventos (feed)
│           ├── gastos.py          # /api/gastos (finanzas)
│           ├── dashboard.py       # /api/dashboard/hud
│           └── whatsapp.py        # /api/whatsapp (bot integration)
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js         # Paleta RCA + tokens
    ├── postcss.config.js
    └── src/
        ├── main.jsx               # Mount React
        ├── App.jsx                # Router + rutas protegidas
        ├── index.css              # Tailwind + utilidades custom
        │
        ├── components/
        │   ├── HUD.jsx            # Top nav glass
        │   ├── Logo.jsx           # Logo RCA. tipográfico
        │   └── Layout/
        │       ├── Layout.jsx     # Wrapper con HUD + Sidebar
        │       ├── Sidebar.jsx    # Nav lateral con secciones
        │       └── ProtectedRoute.jsx  # Guard auth + roles
        │
        ├── context/
        │   └── AuthContext.jsx    # Estado global (user, login, logout)
        │
        ├── utils/
        │   └── api.js             # Axios con interceptor JWT
        │
        └── pages/
            ├── Login.jsx          # Hero bicolor + form
            ├── Register.jsx       # Auto-rol admin si es primero
            ├── WorldMap.jsx       # Dashboard de obras
            ├── ObraDetail.jsx     # Detalle por obra
            ├── Cuadrillas.jsx     # CRUD equipos
            ├── Materiales.jsx     # Inventario filtrable
            ├── Proveedores.jsx    # Red de aliados
            ├── Ordenes.jsx        # Vista global
            ├── Feed.jsx           # Activity timeline
            ├── Finanzas.jsx       # Big numbers + breakdown
            └── Equipo.jsx         # Gestión usuarios
```

---

## 🎨 Sistema de diseño visual

### Paleta cromática RCA

| Color | Hex | CMYK | Uso |
|-------|-----|------|-----|
| **Azul noche** | `#1E2B5E` | C100 M90 Y0 K75 | Texto principal, primary |
| **Verde militar** | `#3D4F1E` | C58 M30 Y80 K20 | Success, success-dark |
| **Verde oliva** | `#8A9A5B` | C45 M20 Y65 K5 | Accent, eyebrows |
| **Marrón cuero** | `#6B4C30` | C30 M55 Y75 K35 | Warnings |
| **Marrón arena** | `#A8845F` | C20 M42 Y62 K10 | Warn secondary |
| **Tostado** | `#C4B99A` | C15 M18 Y38 K5 | Borders, muted |
| **Hueso** | `#EEEAE3` | C5 M4 Y8 K0 | Bone — surfaces |

### Escala extendida (Tailwind)
```js
navy: { 50, 100, 200, 300, 400, 500 (DEFAULT), 600, 700, 800, 900 }
olive: { 50, 100, 200, 300, 400, 500 (DEFAULT), 600, 700, 800, 900 }
bone: { 50, 100, 200, 300, 400 }
military, leather, sand, tan: solo DEFAULT
```

### Tipografía
```css
Display: 'Inter' + SF Pro Display fallback
Body:    'Inter' + system fonts
Weights: 200, 300, 400, 500, 600, 700, 800, 900
```

**Tracking:**
- `tightest` = -0.04em (heroes)
- `tighter` = -0.025em (h2-h3)
- `tight` = body normal
- `[0.18em]–[0.22em]` = uppercase eyebrows

### Componentes utility (en `index.css`)

#### Hero (estilo Apple keynote)
```css
.hero-eyebrow  → 12px uppercase tracking-[0.22em] olive-700 font-semibold
.hero-title    → font-display bold tracking-[-0.04em] leading-[1.02]
.hero-sub      → text-lg muted font-light leading-relaxed
```

**Patrón estándar de página:**
```jsx
<header className="mb-12">
  <div className="hero-eyebrow">Sección</div>
  <h1 className="hero-title text-5xl md:text-6xl mb-3">Título.</h1>
  <p className="hero-sub">Descripción ligera.</p>
</header>
```

#### Cards
```css
.card        → bg-white rounded-3xl border-border/70
.card-flat   → bg-white rounded-3xl (sin border)
.card-hover  → transition + hover:shadow-card + -translate-y-0.5
```

#### Botones (Apple pill)
```css
.btn          → rounded-full px-5 py-2.5 text-[13px] tracking-tight
.btn-lg       → px-7 py-3.5 text-[15px]
.btn-primary  → bg-navy text-bone hover:navy-700 active:scale-[0.97]
.btn-secondary → bg-bone-200/80 text-navy
.btn-ghost    → bg-transparent text-navy
.btn-accent   → bg-olive text-white
.btn-danger   → bg-danger/10 text-danger
.btn-link     → text-olive-700 underline-style
```

#### Inputs
```css
.input  → rounded-2xl bg-bone-100/70 px-4 py-3 + focus ring navy/5
.label  → 11px uppercase tracking-wide muted
```

#### Chips (pills informativos)
```css
.chip-navy    → bg-navy/10 text-navy
.chip-olive   → bg-olive/15 text-olive-700
.chip-leather → bg-leather/10 text-leather
.chip-warn    → bg-warn/15 text-leather
.chip-danger  → bg-danger/10 text-danger
.chip-muted   → bg-bone-200/70 text-muted
```

#### Glass (top nav)
```css
.glass → bg-white/70 backdrop-blur-2xl backdrop-saturate-150
```

### Sombras
```js
soft       : 1px 2px + 4px 12px navy/4%   → cards reposo
card       : 3px 6px + 8px 24px navy/6%   → cards hover
lift       : 4px 8px + 16px 40px navy/8%  → modals
inner-soft : inset 1px 2px navy/4%        → inputs press
```

### Animaciones
```js
fade-in   : 0.5s ease-out
slide-up  : 0.6s cubic-bezier(0.16, 1, 0.3, 1)  → hero entrance
scale-in  : 0.4s cubic-bezier(0.16, 1, 0.3, 1)
```

---

## 🔌 Backend — API & modelos

### Modelos de dominio (11)

```
┌─────────────┐       ┌──────────┐
│    User     │───┬───│ Cuadrilla│
└─────────────┘   │   └────┬─────┘
                  │        │
                  │        ▼
                  │   ┌─────────┐
                  │   │ Frente  │◀──┐
                  │   └────┬────┘   │
                  │        │        │
                  │        ▼        │
┌─────────────┐   │   ┌─────────┐   │
│   Obra      │───┴───│ Evento  │   │
└──────┬──────┘       └─────────┘   │
       │                            │
       ├──────────────────┐         │
       ▼                  ▼         │
┌─────────────┐    ┌─────────────┐  │
│OrdenTrabajo │    │   Gasto     │──┘
└─────────────┘    └─────────────┘
                          │
┌─────────────┐           │
│  Material   │───────────┤
│             │    ┌──────┴──────┐
│ Movimiento  │    │ Proveedor   │
└─────────────┘    └─────────────┘
```

### Tabla de modelos

| Modelo | Propósito | Relaciones |
|--------|-----------|------------|
| **User** | Usuarios + auth | role enum (4 valores) |
| **Obra** | Proyecto principal (micro-mundo) | → Frente, Evento, Orden |
| **Frente** | Sub-mapa dentro de obra (cimientos, terminaciones) | ← Obra, Cuadrilla |
| **Cuadrilla** | Equipo con stats RPG (eficiencia, XP) | ← capataz (User) |
| **Material** | Inventario por categoría | → Movimiento, ← Proveedor |
| **MovimientoMaterial** | Ingreso/consumo | ← Material, Obra, User |
| **Proveedor** | Red evaluada (rating 0-5) | → Material |
| **OrdenTrabajo** | Quest con XP reward | ← Obra, Frente, Cuadrilla |
| **Evento** | Activity log | ← Obra, Frente, User |
| **Gasto** | Egreso financiero | ← Obra, Proveedor |

### Enums clave

```python
UserRole      = admin_finanzas | admin | supervisor | usuario_bot
UserStatus    = active | pending | rejected
ObraStatus    = planificacion | en_obra | pausada | finalizada
ObraSalud     = optimo (verde) | atencion (amarillo) | critico (rojo)
FrenteEstado  = pendiente | en_progreso | bloqueado | completado
TaskStatus    = pendiente | en_progreso | completada | bloqueada
EventoTipo    = avance | material_llegada | incidente | inspeccion | foto | hito | otro
CanalCarga    = whatsapp | web | automatico
```

### Endpoints REST

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `auth` | `/auth` | `POST /login`, `POST /register`, `GET /me` |
| `users` | `/api/users` | GET / POST / PATCH / DELETE |
| `obras` | `/api/obras` | CRUD + `/{id}/frentes` |
| `cuadrillas` | `/api/cuadrillas` | CRUD |
| `materiales` | `/api/materiales` | CRUD + `/{id}/movimientos` |
| `proveedores` | `/api/proveedores` | CRUD |
| `ordenes` | `/api/ordenes` | CRUD + `/{id}/complete` |
| `eventos` | `/api/eventos` | GET (limit) + POST |
| `gastos` | `/api/gastos` | CRUD |
| `dashboard` | `/api/dashboard` | `GET /hud` (stats agregados) |
| `whatsapp` | `/api/whatsapp` | webhook bot |

**Docs interactivas:** http://localhost:8000/docs (Swagger UI)

---

## 💻 Frontend — Páginas & componentes

### Mapa de rutas

| Path | Componente | Acceso | Layout |
|------|-----------|--------|--------|
| `/login` | Login | público | sin layout |
| `/register` | Register | público | sin layout |
| `/world` | WorldMap | autenticado | fullWidth |
| `/obra/:id` | ObraDetail | autenticado | fullWidth |
| `/ordenes` | Ordenes | autenticado | normal |
| `/feed` | Feed | autenticado | normal |
| `/cuadrillas` | Cuadrillas | admin | normal |
| `/materiales` | Materiales | admin | normal |
| `/proveedores` | Proveedores | admin | normal |
| `/finanzas` | Finanzas | admin_finanzas | normal |
| `/equipo` | Equipo | admin | normal |

### Componentes globales

#### `<Layout fullWidth?>` ([Layout.jsx](../frontend/src/components/Layout/Layout.jsx))
Wrapper estándar:
- `<HUD />` arriba sticky
- `<Sidebar />` izquierda 60w
- `<main>` con padding `px-10 py-12` (o sin padding si fullWidth)

#### `<HUD />` ([HUD.jsx](../frontend/src/components/HUD.jsx))
Top nav 48px con:
- Logo clickeable → `/world`
- Stats live: Disponible | Obras | Equipo | Productividad (auto-refresh 30s)
- Alertas críticas (link a feed)
- Search (placeholder), WhatsApp bot, Avatar+nombre, Logout
- Glass effect: `bg-white/70 backdrop-blur-2xl saturate-150`

#### `<Sidebar />` ([Sidebar.jsx](../frontend/src/components/Layout/Sidebar.jsx))
Nav lateral con secciones según rol:
- **General:** Obras, Órdenes, Actividad
- **Recursos** (admin): Cuadrillas, Materiales, Proveedores
- **Finanzas** (admin_finanzas): Presupuestos
- **Administración** (admin): Usuarios

Active state: pill navy + shadow-soft. Iconos `strokeWidth=1.8`.

#### `<Logo size variant tagline color />` ([Logo.jsx](../frontend/src/components/Logo.jsx))
Logo tipográfico "RCA." con punto bloque oliva.
- Sizes: `xs | sm | md | lg | xl`
- Colors: `navy | bone | white`
- Variants: con o sin tagline "Diseño · Construcción · Servicio"

#### `<ProtectedRoute requireAdmin requireFinanzas />`
Guard que:
1. Redirige a `/login` si no hay user
2. Bloquea ruta si rol insuficiente

### Páginas (resumen visual)

#### 🔐 Login ([Login.jsx](../frontend/src/pages/Login.jsx))
- **Layout:** 2 columnas grid `[1.1fr_1fr]`
- **Izq:** Hero navy con blobs ambient (olive/leather), título 6-7xl bicolor
- **Der:** Form minimalista con campos rounded-2xl
- **Eyebrow:** "Diseño · Construcción · Servicio" tracking-[0.22em]
- **Demo box:** credenciales `admin@demo.com / demo1234`

#### 📝 Register ([Register.jsx](../frontend/src/pages/Register.jsx))
- Card centrada `p-10` con shadow-card
- Form 2 columnas (nombre/apellido) + email + WhatsApp + password
- Auto-rol `admin_finanzas` para primer usuario

#### 🌍 WorldMap ([WorldMap.jsx](../frontend/src/pages/WorldMap.jsx))
- **Hero:** "Tus obras / en un solo lugar." (6-7xl bicolor)
- **Filtros pill:** Todas | En obra | Planificación | Finalizadas (con conteos)
- **Grid de obras:** cards con código, nombre, ciudad, progress bar, salud-dot
- **Empty state:** ícono grande + CTA crear primera obra

#### 🏢 ObraDetail ([ObraDetail.jsx](../frontend/src/pages/ObraDetail.jsx))
Página rica con secciones apilables:
1. **Hero header:** código + estado + nombre 5-6xl + ubicación + cliente + descripción
2. **Status pill** (verde/amarillo/rojo)
3. **Mega progress** (3xl % + bar 2px navy)
4. **Frentes de trabajo** (tabla + modal nuevo)
5. **Órdenes de trabajo** (lista + modal)
6. **Actividad** (mini feed) + reportar evento

#### 📋 Ordenes ([Ordenes.jsx](../frontend/src/pages/Ordenes.jsx))
- Hero "Órdenes." + subtítulo
- Filtro dropdown por obra
- Card con resumen 3-buckets (pendientes / en_progreso / completadas)
- Tabla detallada de órdenes

#### 👷 Cuadrillas ([Cuadrillas.jsx](../frontend/src/pages/Cuadrillas.jsx))
- Hero "Cuadrillas." + CTA "Nueva cuadrilla"
- Grid 1/2/3 columnas responsive
- Cada card: nombre, especialidad, miembros + stats RPG (nivel, eficiencia)

#### 📦 Materiales ([Materiales.jsx](../frontend/src/pages/Materiales.jsx))
- Hero "Materiales." + CTA "Nuevo material"
- Filtros pill por categoría
- Grid agrupado por categoría
- Alertas si stock < stock_minimo

#### 🚚 Proveedores ([Proveedores.jsx](../frontend/src/pages/Proveedores.jsx))
- Hero "Proveedores." + CTA
- Grid de cards con rating estrellas, plazo entrega, flag moroso

#### 💰 Finanzas ([Finanzas.jsx](../frontend/src/pages/Finanzas.jsx))
- Hero "Presupuestos."
- **3 big numbers** estilo Apple: Total | Consumido | Disponible (`text-5xl`)
- **2 breakdowns:** por categoría + por obra (bar charts)

#### 👥 Equipo ([Equipo.jsx](../frontend/src/pages/Equipo.jsx))
- Hero "Usuarios." + CTA invitar
- Tabla con avatar circular navy + datos + select de rol

#### 📢 Feed ([Feed.jsx](../frontend/src/pages/Feed.jsx))
- Hero "Actividad."
- Timeline cronológica con icons:
  - ◆ avance · ◇ material · ! incidente · ◉ inspección · ◫ foto · ★ hito
- Eventos críticos en bg-danger/5

---

## 🔐 Autenticación & roles

### Flow JWT
```
1. POST /auth/login { email, password }
   → { access_token, user }
2. localStorage.setItem('rca_token', token)
3. Axios interceptor: Authorization: Bearer ${token}
4. Backend valida en cada request via dependencies
```

### Matriz de permisos

| Recurso | admin | admin_finanzas | supervisor | usuario_bot |
|---------|:-----:|:--------------:|:----------:|:-----------:|
| Ver obras | ✓ | ✓ | ✓ (asignadas) | ✗ |
| Crear obra | ✓ | ✓ | ✗ | ✗ |
| Cuadrillas | ✓ | ✗ | ver | ✗ |
| Materiales | ✓ | ✗ | ver | ✗ |
| Proveedores | ✓ | ✗ | ✗ | ✗ |
| Finanzas | ✓ | ✓ | ✗ | ✗ |
| Usuarios | ✓ | ✗ | ✗ | ✗ |
| Órdenes | ✓ | ver | ✓ | solo asignadas (WhatsApp) |
| Feed | ✓ | ✓ | ✓ | post via WhatsApp |

### Helpers en `AuthContext`
```js
const { user, login, logout, isAdmin, hasFinanzas } = useAuth()
```

---

## 🚦 Flujos de usuario

### Onboarding nuevo cliente
```
1. POST /register → 1er usuario es admin_finanzas
2. Login automático
3. Redirect /world (vacío)
4. CTA "Crear primera obra"
5. Modal con form: nombre, código, dirección, presupuesto, fechas
6. Redirect /obra/:id
7. Crear frentes → asignar cuadrilla
8. Crear órdenes → asignar capataz
9. Capataz recibe en WhatsApp (si telefono cuadrilla)
```

### Reporte de avance vía WhatsApp
```
1. Capataz envía foto + texto al bot
2. POST /api/whatsapp/webhook
3. Backend crea Evento(tipo=foto, canal=whatsapp)
4. Si keyword "incidente" → es_critico=true
5. Frontend HUD muestra alerta roja
6. Admin click → /feed → ve evento
```

### Cierre de orden
```
1. PATCH /api/ordenes/{id} { status: completada }
2. Backend setea completada_at
3. Crea Evento(tipo=avance, titulo="Orden completada")
4. User.xp += orden.xp_reward
5. Si todas órdenes del frente completas → Frente.estado=completado
6. Recalcula Obra.progreso
```

---

## 🛠️ Scripts & comandos

### Iniciar desarrollo

```powershell
# Opción 1: Launchers (Windows)
# Doble-clic en:
.\start-backend.bat
.\start-frontend.bat

# Opción 2: Manual
# Terminal 1
cd backend
python run.py            # → http://localhost:8000

# Terminal 2
cd frontend
npm run dev              # → http://localhost:5173
```

### Comandos frontend
```bash
npm install              # Instala deps
npm run dev              # Vite dev server
npm run build            # Build prod
npm run preview          # Preview build
npm run lint             # ESLint
```

### Comandos backend
```bash
pip install -r requirements.txt   # Instala deps
python run.py                     # Uvicorn dev (reload)
python -m app.seed                # Carga datos de demo
```

### Reset de base de datos
```bash
cd backend
del fielddata.db                  # Windows
# o: rm fielddata.db              # Linux/Mac
python run.py                     # Recrea schema vacío
python -m app.seed                # Re-pobla con demo data
```

---

## 📐 Convenciones de código

### Tailwind: usá los tokens
```jsx
// ✅ Bien
<div className="bg-navy text-bone rounded-3xl">
<h1 className="hero-title text-5xl md:text-6xl">

// ❌ Mal
<div className="bg-[#1E2B5E] text-[#EEEAE3] rounded-[24px]">
<h1 style={{ fontSize: '48px', fontWeight: 700 }}>
```

### Patrones de página
1. `<div className="max-w-Nxl mx-auto animate-fade-in">` wrapper
2. `<header className="mb-12">` con eyebrow + h1 + sub
3. Acciones primarias arriba derecha del header
4. Filtros en barra pill rounded-full bajo header
5. Contenido en `card` con `divide-y` o `grid`
6. Modales: backdrop blur + card centered max-w-md

### Patrones de modal
```jsx
{open && (
  <div className="fixed inset-0 bg-navy/30 backdrop-blur-sm z-50 grid place-items-center p-6"
       onClick={() => setOpen(false)}>
    <div className="card p-8 max-w-md w-full shadow-lift" onClick={e=>e.stopPropagation()}>
      <h2 className="hero-title text-2xl mb-6">Título</h2>
      {/* form */}
    </div>
  </div>
)}
```

---

## 🎯 Resumen de modificaciones visuales aplicadas

### Antes → Después

| Elemento | Antes | Después |
|----------|-------|---------|
| **Top nav** | `h-14 bg-white/85` | `h-12 glass (white/70 + saturate-150)` |
| **Sidebar** | `w-56 rounded-lg` | `w-60 rounded-xl + shadow-soft active` |
| **Hero titles** | `text-4xl md:text-5xl` | `text-5xl md:text-6xl` (con punto final) |
| **Eyebrow** | inline class | `.hero-eyebrow` reusable |
| **Cards** | `rounded-2xl` | `rounded-3xl` (más generoso) |
| **Inputs** | `rounded-xl` | `rounded-2xl` + ring-4 navy/5 |
| **Buttons** | `text-sm` | `text-[13px] tracking-tight` + active scale |
| **Layout padding** | `px-8 py-8` | `px-10 py-12` (más respiración) |
| **Login hero** | `text-5xl xl:text-6xl` | `text-6xl xl:text-7xl` + ambient blobs |
| **Section labels** | tracking-[0.15em] | tracking-[0.18em] |

### Nuevas utilidades CSS
- `.hero-eyebrow` — eyebrow uppercase olive
- `.hero-title` — display bold tracking ultra-tight
- `.hero-sub` — subtítulo light
- `.glass` — backdrop-blur + saturate
- `.btn-lg` — botón grande
- `.btn-link` — link estilizado
- `.card-flat` — card sin border

### Páginas tocadas
✓ Login · ✓ Register · ✓ WorldMap · ✓ Cuadrillas · ✓ Equipo · ✓ Proveedores · ✓ Materiales · ✓ Ordenes · ✓ Finanzas · ✓ Feed · ✓ ObraDetail (sin cambios mayores) · ✓ HUD · ✓ Sidebar · ✓ Layout · ✓ index.css · ✓ tailwind.config.js

---

## 📞 URLs de referencia

| Recurso | URL |
|---------|-----|
| App principal | http://localhost:5173 |
| API backend | http://localhost:8000 |
| **Swagger docs** | **http://localhost:8000/docs** |
| ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

**Credenciales demo:** `admin@demo.com` / `demo1234`

---

> **RCA.** — Una plataforma. Tres pilares. Diseño · Construcción · Servicio.
