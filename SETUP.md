# 🚀 Setup en otra PC

Guía mínima para clonar el repo y dejarlo corriendo en una PC nueva.

## Requisitos

| Tool | Versión | Cómo instalar |
|------|---------|---------------|
| **Python** | 3.11+ | https://www.python.org/downloads/ (marcá "Add to PATH") |
| **Node.js** | 20+ | https://nodejs.org/ |
| **Git** | cualquiera | https://git-scm.com/ |
| **Anthropic API Key** | — | https://console.anthropic.com/settings/keys |

Verificá que estén en PATH:
```bash
python --version    # → Python 3.11.x o más
node --version      # → v20.x o más
npm --version
```

---

## 🪟 Windows (1 comando)

```cmd
git clone https://github.com/optimizarai-del/ciudad.git rca
cd rca
git checkout feat/sprint1-agente-ia
setup.bat
```

`setup.bat` hace: venv + pip install + seed DB + npm install + crea archivos `.env`.

Después editá `backend\.env` y pegá tu `ANTHROPIC_API_KEY`. Listo:

```cmd
start-backend.bat
start-frontend.bat
```

Abrí http://localhost:5175 → login `admin@demo.com` / `demo1234`.

---

## 🍎 Mac / 🐧 Linux

```bash
git clone https://github.com/optimizarai-del/ciudad.git rca
cd rca
git checkout feat/sprint1-agente-ia
chmod +x setup.sh
./setup.sh
```

Editá `backend/.env` con tu API key. Después en dos terminales:

```bash
# Terminal 1 — backend
cd backend
.venv/bin/python run.py

# Terminal 2 — frontend
cd frontend
npm run dev -- --port 5175 --strictPort
```

---

## 🔑 Variables de entorno

### `backend/.env` (obligatorio editar `ANTHROPIC_API_KEY`)

```env
DATABASE_URL=sqlite:///./fielddata.db
SECRET_KEY=cambialo-por-un-string-largo-random
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5175,http://localhost:5173,http://localhost:5174

# Webhook WhatsApp (opcional, para integración con n8n)
WHATSAPP_WEBHOOK_TOKEN=set-shared-token-with-n8n

# Agente Operario IA (REQUERIDO para el chat IA)
ANTHROPIC_API_KEY=sk-ant-api03-...
AGENT_MODEL=claude-sonnet-4-5

# Opcional: hot-reload de uvicorn (problemas conocidos en OneDrive/Windows)
# RELOAD=1
# Opcional: cambiar puerto del backend
# PORT=8010
```

### `frontend/.env` (opcional, default ya correcto)

```env
VITE_API_URL=http://localhost:8010
```

---

## 🌐 Puertos por default

| Servicio | URL |
|----------|-----|
| Backend (FastAPI) | http://localhost:8010 |
| Swagger docs | http://localhost:8010/docs |
| Frontend (Vite) | http://localhost:5175 |

Si tenés esos puertos ocupados, exportá `PORT=otro` antes del backend y ajustá `VITE_API_URL` + `CORS_ORIGINS`.

---

## 🧪 Verificación rápida

1. http://localhost:8010/health → `{"status":"ok","brand":"RCA."}`
2. http://localhost:5175 → pantalla de login
3. Login con `admin@demo.com` / `demo1234`
4. Click en el botón **"Operario IA"** abajo a la derecha
5. Pregunta: *"¿Cómo va todo en general?"* → debe contestar con datos reales

Si el chat dice **"falta ANTHROPIC_API_KEY"**, completá la key en `backend/.env` y reiniciá el backend (Ctrl+C en la consola, después correr de nuevo).

---

## 🔄 Resetear datos demo

```bash
cd backend
rm fielddata.db                # Linux/Mac
del fielddata.db               # Windows
.venv/bin/python -m app.seed   # Linux/Mac
.venv\Scripts\python.exe -m app.seed   # Windows
```

---

## 🩺 Troubleshooting

**Backend no levanta** → verificá `python --version` ≥ 3.11 y que el `.venv` exista. Si no, reejecutá `setup.bat` / `setup.sh`.

**Frontend no levanta** → `cd frontend && npm install`. Borrá `node_modules` si quedó corrupto.

**Puerto ocupado** → Windows: `netstat -ano | findstr :8010` para ver qué proceso. Linux/Mac: `lsof -i :8010`.

**El agente IA no responde** → revisá `backend/.env`:
- ¿`ANTHROPIC_API_KEY` está completa? (empieza con `sk-ant-api03-`)
- ¿Tu cuenta de Anthropic tiene saldo? https://console.anthropic.com/settings/billing
- Si el modelo `claude-sonnet-4-5` no está disponible en tu cuenta, probá `AGENT_MODEL=claude-haiku-4-5-20251001`.

**CORS error en el navegador** → asegurate que `CORS_ORIGINS` en `backend/.env` incluya el puerto donde corre el frontend (default 5175).

**Hot-reload del backend rompe (típico en OneDrive)** → el reload está apagado por default. Si lo querés activar: `RELOAD=1` en `.env`. Si se cuelga, sacalo.
