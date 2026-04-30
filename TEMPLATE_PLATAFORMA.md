# 🧬 Template — Plataforma minimalista estilo Apple

> **Cómo usar este documento:**
> Pegale este archivo entero a Claude al inicio de un proyecto nuevo y decile:
> *"Quiero replicar esta estructura para [TU PROYECTO]. La marca es [NOMBRE], el rubro es [INDUSTRIA], y la paleta es [COLORES]. Usá este template como base."*
>
> Claude generará: backend FastAPI + frontend React/Vite/Tailwind con diseño minimalista Apple, autenticación JWT, sistema de roles, dashboard con HUD, sidebar y todas las páginas CRUD listas.

---

## 📑 Índice

1. [Variables a personalizar](#-variables-a-personalizar)
2. [Stack tecnológico fijo](#-stack-tecnológico-fijo)
3. [Estructura de carpetas](#-estructura-de-carpetas)
4. [Sistema de diseño (copy-paste)](#-sistema-de-diseño-copy-paste)
5. [Backend — Boilerplate completo](#-backend--boilerplate-completo)
6. [Frontend — Boilerplate completo](#-frontend--boilerplate-completo)
7. [Patrones de página reutilizables](#-patrones-de-página-reutilizables)
8. [Launchers Windows](#-launchers-windows)
9. [Prompt-checklist final para Claude](#-prompt-checklist-final-para-claude)

---

## 🎯 Variables a personalizar

Antes de pasarle esto a Claude, definí estas 8 variables. Reemplazá `{{ }}` con tus valores:

```yaml
# Marca
BRAND_NAME: "{{NombreMarca}}"          # ej: "RCA."
BRAND_TAGLINE: "{{Pilar1 · Pilar2 · Pilar3}}"  # ej: "Diseño · Construcción · Servicio"
INDUSTRY: "{{Rubro}}"                  # ej: "construcción", "logística", "salud"

# Paleta (7 colores siempre)
COLOR_PRIMARY: "#______"     # color oscuro principal (ej navy #1E2B5E)
COLOR_PRIMARY_DARK: "#______" # variante más oscura
COLOR_ACCENT: "#______"      # color destacado (ej verde oliva #8A9A5B)
COLOR_ACCENT_DARK: "#______" # variante más oscura
COLOR_WARN: "#______"        # warning (ej marrón cuero #6B4C30)
COLOR_NEUTRAL: "#______"     # crema/hueso (ej #EEEAE3)
COLOR_BG: "#______"          # fondo (ej #FAFAF8)

# Dominio (los modelos principales)
ENTITIES:
  - "{{Entidad1}}"   # ej: Obra, Producto, Paciente
  - "{{Entidad2}}"   # ej: Cuadrilla, Vendedor, Doctor
  - "{{Entidad3}}"   # etc
```

---

## 🧰 Stack tecnológico fijo

> Estos NO cambian — son los pilares del template.

### Backend
- **FastAPI** 0.110 + **Uvicorn** 0.27
- **SQLAlchemy** 2.0 + **SQLite** (dev) / Postgres (prod)
- **Pydantic** 2.6 (schemas)
- **python-jose** + **passlib[bcrypt]** (JWT auth)
- **python-multipart** + **python-dotenv**

### Frontend
- **React 18** + **Vite 5**
- **Tailwind CSS 3** + **PostCSS** + **Autoprefixer**
- **React Router 6**
- **Lucide React** (iconos)
- **Axios** (HTTP)
- **Inter** (Google Fonts, weights 200-900)

---

## 📁 Estructura de carpetas

```
{{PROYECTO}}/
├── start-backend.bat              # Launcher (doble-clic)
├── start-frontend.bat
├── README.md
├── QUICK_START.md
├── GUIA_ONBOARDING.md
│
├── backend/
│   ├── run.py                     # uvicorn entry
│   ├── requirements.txt
│   ├── .env                       # SECRET_KEY, CORS_ORIGINS, DATABASE_URL
│   └── app/
│       ├── __init__.py
│       ├── main.py                # FastAPI + CORS + routers
│       ├── database.py            # engine + SessionLocal + Base
│       ├── models.py              # SQLAlchemy models
│       ├── schemas.py             # Pydantic schemas
│       ├── security.py            # hash + JWT
│       ├── seed.py                # datos demo
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── users.py
│           ├── dashboard.py       # /api/dashboard/hud
│           └── {{entity}}.py      # 1 router por entidad
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js         # paleta + tokens
    ├── postcss.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx                # rutas
        ├── index.css              # Tailwind + .hero-* + .btn-* etc
        │
        ├── components/
        │   ├── HUD.jsx            # top nav glass
        │   ├── Logo.jsx
        │   └── Layout/
        │       ├── Layout.jsx
        │       ├── Sidebar.jsx
        │       └── ProtectedRoute.jsx
        │
        ├── context/
        │   └── AuthContext.jsx
        │
        ├── utils/
        │   └── api.js             # axios + interceptor JWT
        │
        └── pages/
            ├── Login.jsx
            ├── Register.jsx
            ├── Dashboard.jsx       # equiv a /world
            └── {{Entity}}.jsx
```

---

## 🎨 Sistema de diseño (copy-paste)

### `tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Primario (escala completa generada de COLOR_PRIMARY)
        primary: {
          DEFAULT: '{{COLOR_PRIMARY}}',
          50: '#____', 100: '#____', 200: '#____', 300: '#____', 400: '#____',
          500: '{{COLOR_PRIMARY}}', 600: '{{COLOR_PRIMARY_DARK}}',
          700: '#____', 800: '#____', 900: '#____',
        },
        accent: {
          DEFAULT: '{{COLOR_ACCENT}}',
          50: '#____', 100: '#____', 200: '#____', 300: '#____', 400: '#____',
          500: '{{COLOR_ACCENT}}', 600: '{{COLOR_ACCENT_DARK}}',
          700: '#____', 800: '#____', 900: '#____',
        },
        warn: '{{COLOR_WARN}}',
        neutral: {
          DEFAULT: '{{COLOR_NEUTRAL}}',
          50: '#FAFAF8', 100: '#F5F2EC', 200: '#EEEAE3',
          300: '#E5E0D6', 400: '#D4CCBC',
        },
        // Aliases semánticos
        bg: '{{COLOR_BG}}',
        surface: '#FFFFFF',
        surface2: '#F5F2EC',
        border: '#E5E0D6',
        text: '{{COLOR_PRIMARY}}',
        muted: '#6B7280',
        success: '{{COLOR_ACCENT_DARK}}',
        danger: '#B33A3A',
      },
      fontFamily: {
        display: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Helvetica', 'sans-serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.025em',
      },
      boxShadow: {
        'soft': '0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.04)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.06), 0 8px 24px rgba(0, 0, 0, 0.06)',
        'lift': '0 4px 8px rgba(0, 0, 0, 0.08), 0 16px 40px rgba(0, 0, 0, 0.08)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: {
          '0%': { transform: 'translateY(24px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.96)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
```

### `index.css` (utilidades core)

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700;800;900&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

* { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

html, body, #root { height: 100%; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  font-feature-settings: "ss01", "cv11";
  font-weight: 400;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #E0DBD0; border-radius: 8px; }

@layer base {
  h1, h2, h3, h4 { letter-spacing: -0.03em; }
  h1 { font-weight: 700; }
}

@layer components {
  /* Cards */
  .card { @apply bg-white rounded-3xl border border-border/70; }
  .card-flat { @apply bg-white rounded-3xl; }
  .card-hover {
    @apply transition-all duration-500 ease-out hover:shadow-card hover:-translate-y-0.5;
  }

  /* Buttons (Apple pill) */
  .btn {
    @apply inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full
           font-medium text-[13px] tracking-tight
           transition-all duration-200 ease-out;
  }
  .btn-lg { @apply px-7 py-3.5 text-[15px]; }
  .btn-primary  { @apply btn bg-primary text-neutral hover:bg-primary-700 active:scale-[0.97]; }
  .btn-secondary{ @apply btn bg-neutral-200/80 text-primary hover:bg-neutral-300; }
  .btn-ghost    { @apply btn bg-transparent text-primary hover:bg-neutral-200/70; }
  .btn-accent   { @apply btn bg-accent text-white hover:bg-accent-600; }
  .btn-danger   { @apply btn bg-danger/10 text-danger hover:bg-danger/15; }
  .btn-link     { @apply inline-flex items-center gap-1 text-[13px] font-medium text-accent-700 hover:text-accent-600; }

  /* Inputs */
  .input {
    @apply w-full bg-neutral-100/70 border border-transparent rounded-2xl px-4 py-3
           text-primary text-sm placeholder:text-muted/60
           focus:outline-none focus:border-primary/40 focus:bg-white
           focus:ring-4 focus:ring-primary/5 transition;
  }
  .label { @apply block text-[11px] font-medium text-muted mb-2 tracking-wide uppercase; }

  /* Sidebar section */
  .section-label {
    @apply text-[10px] uppercase tracking-[0.18em] text-muted/70 px-3 mt-7 mb-2 font-semibold;
  }

  /* Chips */
  .chip { @apply inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium tracking-tight; }
  .chip-primary { @apply chip bg-primary/10 text-primary; }
  .chip-accent  { @apply chip bg-accent/15 text-accent-700; }
  .chip-warn    { @apply chip bg-warn/15 text-warn; }
  .chip-danger  { @apply chip bg-danger/10 text-danger; }
  .chip-muted   { @apply chip bg-neutral-200/70 text-muted; }

  /* Hero (Apple keynote style) */
  .hero-eyebrow { @apply text-[12px] uppercase tracking-[0.22em] text-accent-700 font-semibold mb-4; }
  .hero-title   { @apply font-display font-bold tracking-[-0.04em] leading-[1.02]; }
  .hero-sub     { @apply text-muted text-lg md:text-xl leading-relaxed font-light; }

  /* Stats */
  .stat-label { @apply text-[11px] uppercase tracking-[0.14em] text-muted font-medium; }
  .stat-value { @apply font-display font-semibold tracking-[-0.03em] text-primary; }

  /* Glass (top nav) */
  .glass { @apply bg-white/70 backdrop-blur-2xl backdrop-saturate-150; }
}

/* Ambient gradient utility */
.bg-grain {
  background-image:
    radial-gradient(at 0% 0%, rgba(var(--accent-rgb), 0.05) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(var(--primary-rgb), 0.04) 0px, transparent 50%);
}

*:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; border-radius: 6px; }
html { scroll-behavior: smooth; }
```

> **Reglas de Tailwind crítico:**
> - Las opacidades válidas son `/5 /10 /15 /20 /25 /30 ... /95`. **NO uses `/8` ni `/72`** — rompen el build.

---

## 🔌 Backend — Boilerplate completo

### `backend/requirements.txt`

```
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
pydantic==2.6.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
python-dotenv==1.0.1
email-validator==2.3.0
httpx==0.27.0
```

### `backend/run.py`

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

### `backend/app/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
```

### `backend/app/main.py`

```python
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, users, dashboard  # + tus entidades

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="{{BRAND_NAME}} — {{BRAND_TAGLINE}}", version="0.1.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [auth, users, dashboard]:
    app.include_router(r.router)

@app.get("/health")
def health():
    return {"status": "ok", "brand": "{{BRAND_NAME}}"}
```

### `backend/app/security.py`

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 semana

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_pw(p): return pwd_context.hash(p)
def verify_pw(plain, hashed): return pwd_context.verify(plain, hashed)

def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2), db: Session = Depends(...)):
    from app.models import User
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload.get("sub"))
    except JWTError:
        raise cred_exc
    user = db.query(User).filter(User.id == uid).first()
    if not user: raise cred_exc
    return user
```

### Patrón de modelo (`models.py`)

```python
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Boolean
from app.database import Base

class UserRole(str, Enum):
    admin = "admin"
    operativo = "operativo"
    viewer = "viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.viewer)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Patrón de router CRUD (`routers/{{entity}}.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.security import get_current_user
from app import models, schemas

router = APIRouter(prefix="/api/{{entities}}", tags=["{{entities}}"])

@router.get("/", response_model=List[schemas.{{Entity}}Out])
def listar(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.{{Entity}}).all()

@router.post("/", response_model=schemas.{{Entity}}Out)
def crear(data: schemas.{{Entity}}Create, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = models.{{Entity}}(**data.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/{id}", response_model=schemas.{{Entity}}Out)
def detalle(id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = db.query(models.{{Entity}}).filter_by(id=id).first()
    if not obj: raise HTTPException(404, "No encontrado")
    return obj

@router.patch("/{id}", response_model=schemas.{{Entity}}Out)
def editar(id: int, data: schemas.{{Entity}}Update, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = db.query(models.{{Entity}}).filter_by(id=id).first()
    if not obj: raise HTTPException(404, "No encontrado")
    for k, v in data.dict(exclude_unset=True).items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

@router.delete("/{id}")
def eliminar(id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    obj = db.query(models.{{Entity}}).filter_by(id=id).first()
    if not obj: raise HTTPException(404, "No encontrado")
    db.delete(obj); db.commit()
    return {"ok": True}
```

---

## 💻 Frontend — Boilerplate completo

### `package.json`

```json
{
  "name": "{{proyecto}}-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "axios": "^1.6.7",
    "lucide-react": "^0.330.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "vite": "^5.4.0"
  }
}
```

### `src/utils/api.js`

```js
import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('app_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) {
    localStorage.removeItem('app_token')
    window.location.href = '/login'
  }
  return Promise.reject(err)
})

export default api
```

### `src/context/AuthContext.jsx`

```jsx
import { createContext, useContext, useEffect, useState } from 'react'
import api from '../utils/api'

const AuthContext = createContext()
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('app_token')
    if (token) api.get('/auth/me').then(r => setUser(r.data)).finally(()=>setLoading(false))
    else setLoading(false)
  }, [])

  const login = async (email, password) => {
    const r = await api.post('/auth/login', { email, password })
    localStorage.setItem('app_token', r.data.access_token)
    setUser(r.data.user)
  }

  const logout = () => {
    localStorage.removeItem('app_token')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{
      user, login, logout, loading,
      isAdmin: user?.role === 'admin',
    }}>
      {children}
    </AuthContext.Provider>
  )
}
```

### `src/components/HUD.jsx` (top nav glass)

```jsx
import { useNavigate } from 'react-router-dom'
import { LogOut, Search, Bell } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'

export default function HUD() {
  const { user, logout } = useAuth()
  const nav = useNavigate()

  return (
    <header className="sticky top-0 z-40 glass border-b border-border/60">
      <div className="px-6 h-12 flex items-center gap-8">
        <button onClick={() => nav('/')} className="flex items-center hover:opacity-70 transition">
          <Logo size="sm" />
        </button>

        <div className="ml-auto flex items-center gap-1">
          <IconBtn><Search size={15}/></IconBtn>
          <IconBtn><Bell size={15}/></IconBtn>
          <div className="w-px h-5 bg-border mx-2"/>
          <button className="flex items-center gap-2 pr-3 pl-1 py-1 rounded-full hover:bg-neutral-200/70 transition">
            <div className="w-7 h-7 rounded-full bg-primary text-neutral grid place-items-center text-[11px] font-semibold">
              {user?.name?.[0]?.toUpperCase()}
            </div>
            <span className="text-[13px] font-medium hidden md:inline tracking-tight">{user?.name}</span>
          </button>
          <IconBtn onClick={logout}><LogOut size={15}/></IconBtn>
        </div>
      </div>
    </header>
  )
}

function IconBtn({ children, ...props }) {
  return (
    <button {...props}
      className="p-2 rounded-full text-muted hover:bg-neutral-200/70 hover:text-primary transition">
      {children}
    </button>
  )
}
```

### `src/components/Layout/Sidebar.jsx`

```jsx
import { NavLink } from 'react-router-dom'
import { LayoutGrid, Users, Settings } from 'lucide-react'

const link = ({ isActive }) =>
  `flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium tracking-tight transition-all duration-200 ${
    isActive ? 'bg-primary text-neutral shadow-soft' : 'text-primary/65 hover:bg-neutral-200/60 hover:text-primary'
  }`

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-border/60 bg-white/30 backdrop-blur-sm
                      min-h-[calc(100vh-3rem)] py-5 px-3 flex flex-col">
      <div className="section-label !mt-0">General</div>
      <NavLink to="/" className={link}><LayoutGrid size={15} strokeWidth={1.8}/> Dashboard</NavLink>
      <NavLink to="/usuarios" className={link}><Users size={15} strokeWidth={1.8}/> Usuarios</NavLink>
      <NavLink to="/configuracion" className={link}><Settings size={15} strokeWidth={1.8}/> Configuración</NavLink>

      <div className="mt-auto pt-6 px-3">
        <div className="text-[10px] tracking-[0.18em] uppercase text-muted/60 font-semibold">{{BRAND_NAME}}</div>
        <div className="text-[10px] text-muted/50 mt-1 tracking-wide">{{BRAND_TAGLINE}}</div>
      </div>
    </aside>
  )
}
```

### `src/components/Logo.jsx`

```jsx
export default function Logo({ size = 'md', tagline = false, color = 'primary', className = '' }) {
  const sizes = {
    sm: { txt: 'text-xl', dot: 'w-2 h-2 ml-0.5', tag: 'text-[9px]' },
    md: { txt: 'text-2xl', dot: 'w-2.5 h-2.5 ml-0.5', tag: 'text-[10px]' },
    lg: { txt: 'text-5xl', dot: 'w-4 h-4 ml-1', tag: 'text-xs' },
    xl: { txt: 'text-7xl', dot: 'w-6 h-6 ml-1.5', tag: 'text-sm' },
  }
  const s = sizes[size]
  const colors = { primary: 'text-primary', neutral: 'text-neutral', white: 'text-white' }

  return (
    <div className={`inline-flex flex-col leading-none ${className}`}>
      <div className={`flex items-end font-display font-bold tracking-[-0.04em] ${colors[color]} ${s.txt}`}>
        <span>{{INITIALS}}</span>  {/* ej: "RCA" */}
        <span className={`${s.dot} bg-accent rounded-[2px] mb-[0.15em]`} aria-hidden />
      </div>
      {tagline && (
        <div className={`${s.tag} font-medium tracking-[0.18em] uppercase mt-1.5
                        ${color === 'primary' ? 'text-accent-700' : 'text-accent-200'}`}>
          {{BRAND_TAGLINE}}
        </div>
      )}
    </div>
  )
}
```

### `src/components/Layout/Layout.jsx`

```jsx
import HUD from '../HUD'
import Sidebar from './Sidebar'

export default function Layout({ children, fullWidth = false }) {
  return (
    <div className="min-h-screen bg-bg">
      <HUD />
      <div className="flex">
        <Sidebar />
        <main className={`flex-1 ${fullWidth ? '' : 'px-10 py-12'} overflow-x-hidden`}>
          {children}
        </main>
      </div>
    </div>
  )
}
```

### `src/components/Layout/ProtectedRoute.jsx`

```jsx
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ children, requireAdmin }) {
  const { user, loading, isAdmin } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />
  return children
}
```

---

## 🧱 Patrones de página reutilizables

### 1. Página CRUD estándar (template)

```jsx
import { useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import api from '../utils/api'

export default function {{Entity}}Page() {
  const [list, setList] = useState([])
  const [open, setOpen] = useState(false)

  const load = () => api.get('/api/{{entities}}').then(r => setList(r.data))
  useEffect(() => { load() }, [])

  const eliminar = async (id) => {
    if (confirm('¿Eliminar?')) { await api.delete(`/api/{{entities}}/${id}`); load() }
  }

  return (
    <div className="max-w-6xl mx-auto animate-fade-in">
      <header className="mb-12">
        <div className="hero-eyebrow">{{Sección}}</div>
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="hero-title text-5xl md:text-6xl mb-3">{{Título}}.</h1>
            <p className="hero-sub">{{Descripción ligera.}}</p>
          </div>
          <button onClick={()=>setOpen(true)} className="btn-primary">
            <Plus size={14}/> Nuevo {{singular}}
          </button>
        </div>
      </header>

      {list.length === 0 ? (
        <div className="card text-center py-20">
          <div className="text-5xl mb-3 opacity-30">○</div>
          <p className="text-muted">Aún no hay {{entities}}.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {list.map(item => (
            <div key={item.id} className="card p-6 card-hover">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="font-bold text-lg tracking-tight">{item.nombre}</div>
                  <div className="text-xs uppercase tracking-wider text-muted mt-1">{item.tipo}</div>
                </div>
                <button onClick={()=>eliminar(item.id)}
                  className="text-muted/60 hover:text-danger transition">
                  <Trash2 size={14}/>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {open && <Modal onClose={()=>setOpen(false)} onSaved={load}/>}
    </div>
  )
}

function Modal({ onClose, onSaved }) {
  return (
    <div className="fixed inset-0 bg-primary/30 backdrop-blur-sm z-50 grid place-items-center p-6"
         onClick={onClose}>
      <div className="card p-8 max-w-md w-full shadow-lift animate-scale-in"
           onClick={e=>e.stopPropagation()}>
        <h2 className="hero-title text-2xl mb-6">Nuevo</h2>
        {/* form fields */}
      </div>
    </div>
  )
}
```

### 2. Login bicolor estilo Apple

```jsx
<div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr] bg-bg">
  {/* Izq — keynote */}
  <div className="hidden lg:flex flex-col justify-between p-14 xl:p-20 bg-primary text-neutral relative overflow-hidden">
    <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-accent/20 blur-3xl"/>
    <div className="absolute -bottom-40 -right-20 w-[420px] h-[420px] rounded-full bg-warn/15 blur-3xl"/>

    <Logo size="md" color="neutral" />

    <div className="relative z-10 max-w-lg animate-slide-up">
      <div className="text-[12px] uppercase tracking-[0.22em] text-accent-300 font-semibold mb-5">
        {{BRAND_TAGLINE}}
      </div>
      <h1 className="hero-title text-6xl xl:text-7xl mb-6">
        {{Eslogan línea 1}}<br/>
        <span className="text-accent-300">{{Eslogan línea 2}}.</span>
      </h1>
      <p className="text-neutral/70 text-lg leading-relaxed font-light max-w-md">
        {{Subtítulo descriptivo}}
      </p>
    </div>

    <div className="text-neutral/40 text-[11px] tracking-[0.15em] uppercase">
      © {{BRAND_NAME}}
    </div>
  </div>

  {/* Der — form */}
  <div className="flex flex-col justify-center px-6 py-12 lg:px-20">
    <div className="w-full max-w-sm mx-auto animate-fade-in">
      <h2 className="font-display text-4xl font-bold tracking-[-0.035em] text-primary mb-3">
        Iniciar sesión
      </h2>
      <p className="text-muted text-[15px] font-light mb-10">Bienvenido de vuelta.</p>

      <form className="space-y-5">
        <div><label className="label">Email</label><input className="input" type="email"/></div>
        <div><label className="label">Contraseña</label><input className="input" type="password"/></div>
        <button className="btn-primary btn-lg w-full">Continuar</button>
      </form>
    </div>
  </div>
</div>
```

### 3. Big numbers (Apple keynote dashboard)

```jsx
<section className="grid md:grid-cols-3 gap-6 mb-10">
  <div className="card p-8">
    <div className="stat-label">Total comprometido</div>
    <div className="hero-title text-4xl md:text-5xl mt-2 text-primary">$1.2M</div>
  </div>
  <div className="card p-8">
    <div className="stat-label">Consumido</div>
    <div className="hero-title text-4xl md:text-5xl mt-2 text-warn">$840k</div>
    <div className="chip-warn mt-2">70% del presupuesto</div>
  </div>
  <div className="card p-8">
    <div className="stat-label">Disponible</div>
    <div className="hero-title text-4xl md:text-5xl mt-2 text-accent-700">$360k</div>
  </div>
</section>
```

---

## 🎬 Launchers Windows

### `start-backend.bat`

```bat
@echo off
title {{BRAND_NAME}} Backend
cd /d "%~dp0backend"
echo ============================
echo   {{BRAND_NAME}} - Backend (FastAPI)
echo   http://localhost:8000
echo ============================
python run.py
pause
```

### `start-frontend.bat`

```bat
@echo off
title {{BRAND_NAME}} Frontend
cd /d "%~dp0frontend"
echo ============================
echo   {{BRAND_NAME}} - Frontend (Vite)
echo   http://localhost:5173
echo ============================
call npm run dev
pause
```

---

## 🤖 Prompt-checklist final para Claude

> Copiá y pegá esto al final de tu mensaje:

```
Por favor armá la plataforma siguiendo este template, con estos requisitos:

1. ESTRUCTURA
   - Crear las 2 carpetas backend/ y frontend/
   - Crear los 2 launchers .bat en raíz
   - Crear .env de backend con SECRET_KEY, CORS_ORIGINS, DATABASE_URL

2. BACKEND
   - FastAPI + SQLAlchemy + SQLite
   - Modelos: User + las entidades que te pasé
   - Auth JWT con /auth/login y /auth/register
   - Un router CRUD por entidad usando el patrón estándar
   - Endpoint /api/dashboard/hud con stats agregados
   - Seed con 1 usuario admin@demo.com / demo1234 + datos demo

3. FRONTEND
   - React 18 + Vite + Tailwind 3 + Inter font
   - tailwind.config.js con paleta exacta del template (sustituyendo
     COLOR_PRIMARY/ACCENT/etc por los míos)
   - index.css con todas las utilidades del template (.hero-*, .btn-*,
     .card, .chip-*, .glass, etc)
   - HUD glass + Sidebar + Layout + Logo + ProtectedRoute
   - Páginas: Login bicolor + Register + Dashboard + 1 página por entidad
   - Cada página de entidad sigue el patrón CRUD estándar

4. DISEÑO (REGLAS DURAS)
   - Hero pattern en todas las páginas: eyebrow + título 5-6xl con punto
     final + hero-sub
   - Cards rounded-3xl, botones rounded-full pill
   - Inputs rounded-2xl con focus ring primary/5
   - Top nav glass 48px (h-12)
   - Sidebar w-60 con pill activa
   - Layout padding px-10 py-12
   - Animaciones fade-in en wrappers, scale-in en modales
   - SOLO usar opacidades válidas Tailwind (/5 /10 /15 .../95). NO /8, NO /72.

5. DOCS
   - Generar QUICK_START.md, GUIA_ONBOARDING.md y README.md

Datos del proyecto:

BRAND_NAME: {{}}
BRAND_TAGLINE: {{}}
INDUSTRY: {{}}
COLOR_PRIMARY: {{#}}
COLOR_PRIMARY_DARK: {{#}}
COLOR_ACCENT: {{#}}
COLOR_ACCENT_DARK: {{#}}
COLOR_WARN: {{#}}
COLOR_NEUTRAL: {{#}}
COLOR_BG: {{#}}
ENTIDADES (modelos principales): {{}}
ROLES de usuario: {{}}

Empezá creando todo. Al terminar, arrancá ambos servidores en background
y dame las URLs.
```

---

## 📋 Checklist QA al replicar

Marca conforme valides en el proyecto nuevo:

- [ ] `npm run dev` arranca sin errores Tailwind
- [ ] `python run.py` arranca uvicorn en :8000
- [ ] http://localhost:5173 carga (no white screen)
- [ ] Login funciona con credenciales demo
- [ ] HUD glass effect visible (backdrop-blur)
- [ ] Sidebar con pills activas navy/primary
- [ ] Hero titles 5-6xl con punto final
- [ ] Cards rounded-3xl con hover lift
- [ ] Botones pill con tracking-tight + active scale
- [ ] Inputs con focus ring primary/5
- [ ] Modales con backdrop-blur + animate-scale-in
- [ ] Logo tipográfico con punto accent
- [ ] Animaciones fade-in / slide-up funcionan
- [ ] Tipografía Inter cargada (verificar en Network tab)
- [ ] CRUD de cada entidad funciona end-to-end
- [ ] Persistencia OK (recargar = datos siguen)
- [ ] Logout limpia token y redirige a /login
- [ ] Roles bloquean rutas correctamente

---

## 💡 Tips finales

- **Si Claude se cuelga generando todo:** pedile que lo haga en 3 fases
  (1. backend completo, 2. frontend base, 3. páginas CRUD una por una).
- **Para variar el feel:** la única diferencia visual real entre proyectos
  son los 7 colores. La estructura tipográfica y de espaciado debe quedar
  igual para mantener el "ADN Apple".
- **Para deploy:** Vercel para frontend, Railway/Fly.io para backend +
  Postgres. Cambia `DATABASE_URL` en .env y nada más.
- **Mobile:** todas las páginas son responsive por default — el sidebar
  se oculta < 768px (agregar drawer mobile si lo necesitás).

---

> **Este template = ADN reutilizable.**
> Cambiando 7 colores y 3-5 modelos podés tener una plataforma profesional
> con look Apple en 1-2 horas con Claude.
