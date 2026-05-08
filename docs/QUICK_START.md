# 🚀 Quick Start — RCA Platform

## En 30 segundos

```bash
# 1. Abrí explorer: C:\Users\Usuario\Desktop\RCA
# 2. Doble-clic: start-backend.bat
# 3. Doble-clic: start-frontend.bat
# 4. Abra: http://localhost:5173
# 5. Login: admin@demo.com / demo1234
# Done! 🎉
```

---

## URLs clave

| Servicio | URL |
|----------|-----|
| **App** | http://localhost:5173 |
| **API** | http://localhost:8000 |
| **Docs** | http://localhost:8000/docs |

---

## Credenciales demo

**Email:** `admin@demo.com`  
**Contraseña:** `demo1234`

→ Acceso admin full

---

## Estructura del proyecto

```
RCA/
├── frontend/              # React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/         # Obras, Órdenes, Cuadrillas, etc
│   │   ├── components/    # Layout, HUD, Sidebar, Logo
│   │   ├── context/       # Auth, estado global
│   │   ├── utils/         # API client, helpers
│   │   └── index.css      # Tailwind + custom utilities
│   ├── tailwind.config.js # Paleta RCA (navy, olive, etc)
│   └── vite.config.js     # Bundler config
│
├── backend/               # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py        # Entry point
│   │   ├── models.py      # DB schemas
│   │   ├── routes/        # API endpoints
│   │   └── database.py    # SQLAlchemy setup
│   ├── run.py             # python run.py → inicia servidor
│   └── requirements.txt    # pip install -r requirements.txt
│
├── start-backend.bat      # Launcher (Windows)
├── start-frontend.bat     # Launcher (Windows)
├── GUIA_ONBOARDING.md     # Guía completa (paso a paso)
├── TESTING_CHECKLIST.md   # Validación de features
└── README.md
```

---

## Comandos útiles

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Dev server (Vite HMR — hot reload)
npm run dev

# Build para producción
npm run build

# Preview de build
npm run preview

# Lint (ESLint)
npm run lint
```

### Backend

```bash
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Dev server (FastAPI + Uvicorn + hot reload)
python run.py

# Swagger docs
# → Abrá http://localhost:8000/docs

# Resetear BD (cuidado!)
# rm fielddata.db && python -c "from app.main import app; ..."
```

---

## Stack tech

### Frontend
- **React 18** — UI framework
- **Vite** — ultra-fast bundler
- **Tailwind CSS** — utility-first styling
- **Lucide Icons** — SVG icons
- **React Router** — client-side routing
- **Axios** — HTTP client

### Backend
- **FastAPI** — async web framework
- **SQLAlchemy** — ORM
- **SQLite** — lightweight DB
- **Uvicorn** — ASGI server
- **Pydantic** — data validation

### Paleta RCA (Tailwind)
```
Navy:      #1E2B5E (primary)
Olive:     #8A9A5B (accent)
Military:  #3D4F1E
Leather:   #6B4C30 (warnings)
Sand:      #A8845F
Tan:       #C4B99A
Bone:      #EEEAE3 (surfaces)
```

---

## Diseño: Apple minimalist

✨ **Features:**
- Top nav glass effect (backdrop-blur + saturate)
- Hero titles 5-6xl con tight tracking
- Cards rounded-3xl sin borders duros
- Buttons pill-shaped con tracking-tight
- Inputs rounded-2xl con focus ring
- Eyebrows uppercase olive-700
- Shadows soft, card, lift
- Smooth transitions 200-500ms

📐 **Tipografía:**
- Display: Inter (SF Pro Display alternative)
- Body: Inter 400
- Headings: 700 bold, tracking-[-0.04em]

---

## Páginas principales

| Ruta | Descripción |
|------|-------------|
| `/` | Login (si no autenticado) |
| `/world` | Dashboard — todas las obras |
| `/ordenes` | Órdenes globales |
| `/cuadrillas` | Equipos de trabajo |
| `/materiales` | Inventario |
| `/proveedores` | Red de aliados |
| `/finanzas` | Presupuestos |
| `/equipo` | Gestión usuarios (admin) |
| `/feed` | Actividad en tiempo real |
| `/obra/:id` | Detalle de obra (map view) |

---

## Testing rápido

### 1. Crear obra
1. Ir a `/world`
2. Click "Nueva obra" (si existe botón)
3. Form: Nombre, Presupuesto, Descripción
4. Submit

### 2. Crear orden
1. Entra a la obra
2. Tab "Órdenes"
3. Click "Nueva orden"
4. Form: Descripción, Status
5. Submit

### 3. Completar orden
1. Ir a `/ordenes`
2. Buscar la orden que creaste
3. Cambiar status a "completada"
4. Verifica que aparezca en `/feed`

### 4. Verificar sincronización
1. Abrí 2 navegadores: uno en `/ordenes`, otro en `/feed`
2. Completa orden en primer navegador
3. El segundo deberá reflejar el cambio (si hay real-time)

---

## Troubleshooting rápido

### Backend no arranca
```bash
# Checkea que Python esté instalado
python --version

# Instala dependencias
pip install -r requirements.txt

# Prueba direktamente
cd backend && python run.py
```

### Frontend no carga
```bash
# Checkea Node
node --version && npm --version

# Instala dependencias
cd frontend && npm install

# Prueba dev
npm run dev
```

### Datos no persisten
→ SQLite DB está en `backend/fielddata.db`  
→ Si necesitas resetear: elimina el archivo y reinicia backend

### CORS errors
→ Backend tiene CORS habilitado en `app/main.py`  
→ Si da error, verifica que Frontend apunte a `http://localhost:8000` en `src/utils/api.js`

---

## DevTools & Debug

### F12 en navegador
- **Console:** Errores JS, logs
- **Network:** Requests a `/api/*` en backend
- **Elements:** Inspecciona componentes React
- **Performance:** Mide carga de página

### Backend Swagger
- **URL:** http://localhost:8000/docs
- Testea endpoints REST directamente
- "Try it out" → Execute
- Ver request/response en vivo

### Logs en consola
```
Backend:   INFO:     ... (Uvicorn logs)
Frontend:  vite:hmr (Vite update notifications)
```

---

## Próximos pasos (después de testear)

- [ ] Agregar data real (obras, equipos)
- [ ] Customizar roles/permisos
- [ ] Integrar con WhatsApp bot (WebHook)
- [ ] Upload de fotos/documentos
- [ ] Reportes en PDF
- [ ] Dark mode (optional)
- [ ] Mobile app (React Native)
- [ ] Deploy a producción (Vercel + Railway)

---

## Links útiles

- **Tailwind docs:** https://tailwindcss.com
- **FastAPI docs:** https://fastapi.tiangolo.com
- **React docs:** https://react.dev
- **Lucide icons:** https://lucide.dev

---

¡Listo! Cualquier duda, revisá la `GUIA_ONBOARDING.md` completa. 🚀
