# 🏗️ Construction Tycoon

Plataforma de gestión de obras con UX tipo videojuego. Cada obra es un **micro-mundo** con su propio dashboard, frentes, cuadrillas (personajes con XP/nivel), órdenes (quests) y eventos en tiempo real. Integración con WhatsApp Bot para carga de datos desde el campo.

## 🎮 Concepto

- **HUD superior fijo** con recursos globales (presupuesto, materiales, obreros, productividad, alertas, XP)
- **Mapa de Obras** = grilla de cards animadas con barra de progreso, salud (verde/amarillo/rojo), y stats
- **Click en obra → Micro-mundo:** dashboard con frentes (sub-mapas), feed de eventos, quest log, stats grandes
- **Cuadrillas como personajes RPG:** avatar, especialidad, nivel, XP, eficiencia
- **Órdenes de trabajo = quests:** dan XP al usuario y a la cuadrilla cuando se completan
- **Bot WhatsApp:** capataz reporta desde el campo → se registra evento → otorga XP

## Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite + JWT/bcrypt (basado en blueprint Larrañaga)
- **Frontend:** React 18 + Vite + Tailwind + lucide-react (dark mode)
- **WhatsApp:** Webhook `/api/whatsapp/inbound` listo para n8n

## 📂 Estructura

```
backend/
├── app/
│   ├── main.py, database.py, security.py
│   ├── models.py     # User, Obra, Frente, Cuadrilla, Material, Proveedor, OrdenTrabajo, Evento, Gasto
│   ├── schemas.py    # Pydantic
│   ├── seed.py       # Datos demo (5 obras, 5 cuadrillas, 10 materiales, etc.)
│   └── routers/      # auth, users, obras, cuadrillas, materiales, proveedores,
│                     # ordenes, eventos, gastos, dashboard, whatsapp
frontend/
└── src/
    ├── components/HUD.jsx           # Barra superior con recursos globales
    ├── components/Layout/Sidebar.jsx
    └── pages/
        ├── WorldMap.jsx     # Grilla de obras-mundos
        ├── ObraDetail.jsx   # Micro-mundo con tabs (resumen, frentes, quest log, eventos)
        ├── Cuadrillas.jsx   # Equipos como personajes RPG
        ├── Materiales.jsx   # Inventario con alertas
        ├── Proveedores.jsx  # Aliados con rating
        ├── Ordenes.jsx      # Quest log global
        ├── Feed.jsx         # Stream de eventos cross-obra
        ├── Finanzas.jsx     # Presupuestos + gastos por obra/categoría
        └── Equipo.jsx       # Usuarios con XP/nivel
```

## 🚀 Cómo correrlo

### Pre-requisitos
- **Python 3.11+** instalado y en PATH
- **Node.js 20+** instalado y en PATH

### Backend
```powershell
cd C:\Users\Usuario\Desktop\RCA\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# (Opcional) Cargar datos demo
python -m app.seed

# Levantar API
python run.py
```
→ http://localhost:8000 · docs: http://localhost:8000/docs

### Frontend
```powershell
cd C:\Users\Usuario\Desktop\RCA\frontend
npm install
npm run dev
```
→ http://localhost:5173

## 👤 Login demo (después de correr seed)

```
admin@demo.com / demo1234
```

## 🎯 Datos del seed

- **5 Obras:** Torre Aurora 🏙️ (78%), Country Las Lomas 🏘️, Galpón Industrial 🏭, Local Comercial 🏪, Casa Quincho 🏡
- **5 Cuadrillas:** Los Maestros 🧱, Volt Power ⚡, Aqua Plomers 🚿, Color Squad 🎨, Iron Crew ⚙️
- **4 Proveedores** con rating
- **10 Materiales** con stock y alertas
- **Eventos** críticos y normales
- **Órdenes** con XP rewards (10 a 50 XP cada una)

## 🤖 Integración WhatsApp (n8n)

Endpoint `POST /api/whatsapp/inbound`:
```json
{
  "phone": "+5491100000001",
  "text": "Llegó hormigón Torre Aurora 30m3",
  "token": "<WHATSAPP_WEBHOOK_TOKEN>",
  "foto_url": "https://..."
}
```

El backend:
1. Identifica usuario por `phone`
2. Detecta tipo de evento (avance/material/incidente/inspección/hito)
3. Detecta obra mencionada
4. Detecta criticidad (palabras como "urgente", "accidente")
5. Crea evento + suma 5 XP al usuario
6. Devuelve mensaje confirmación con XP total

## 🎨 Roles

- `admin_finanzas` — todo + finanzas
- `admin` — Project Manager (todo excepto $)
- `supervisor` — jefe de obra/capataz con web
- `usuario_bot` — solo carga por WhatsApp

## 🔮 Roadmap (siguientes features)

- [ ] **Achievements/Logros** desbloqueables (primera obra completada, 1000 XP, etc.)
- [ ] **Vision IA** en webhook: análisis de fotos de obra (cascos, avance)
- [ ] **NLP avanzado** con Claude/OpenAI para extraer múltiples eventos de un mensaje
- [ ] **Mapa geo real** con Mapbox/Leaflet (cada obra como pin)
- [ ] **Mini-mapa por obra** mostrando layout de frentes
- [ ] **Sound effects** opcionales (ding al completar quest)
- [ ] **Dashboard de cuadrillas** con ranking semanal por XP
- [ ] **Auto-asignación IA** de cuadrilla óptima a una orden nueva
- [ ] **Resumen semanal** automático por WhatsApp con stats del juego
