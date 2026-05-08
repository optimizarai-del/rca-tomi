# Sprint 0 — Setup inicial

> Commit: `4763a24 chore(setup): scripts one-shot + docs para correr el proyecto en otra PC`
> Estado: ✅ cerrado

## Requisitos

El proyecto venía con un base funcional de la plataforma RCA pero sin scripts de bootstrap. Para correr el repo en otra PC había que ir paso a paso instalando Python, Node, dependencias, ejecutando seed manualmente y editando configs. Eso introducía fricción y errores.

**Objetivo:** que cualquier persona pudiera clonar el repo y dejarlo corriendo en menos de 5 minutos con un solo comando.

## Cómo se hizo

### Decisiones de puerto

Se cambiaron los puertos por choque con otra plataforma local (OPTIMIZAR):
- Backend: `8000` → `8010`
- Frontend: `5173` → `5175`

### Scripts one-shot

- **`setup.bat`** (Windows) y **`setup.sh`** (Mac/Linux) — bootstrap completo:
  1. Verifica que Python 3.11+ y Node 20+ están en PATH.
  2. Crea `.venv` en `backend/` y corre `pip install -r requirements.txt`.
  3. Copia `.env.example` → `.env` si no existe.
  4. Ejecuta el seed (`python -m app.seed`) para tener datos demo.
  5. Corre `npm install` en `frontend/`.

- **`start-backend.bat`** y **`start-frontend.bat`** — launchers diarios:
  - Validan que `.venv` y `node_modules` existen (sino abortan con mensaje claro).
  - Levantan los servidores en los puertos correctos.

### `.env.example` con todas las variables

Se documentaron las vars necesarias:
- `DATABASE_URL` (default SQLite, opcionalmente PG vía Docker)
- `SECRET_KEY` (JWT)
- `CORS_ORIGINS`
- `ANTHROPIC_API_KEY` (necesaria para el agente IA — Sprint 1)
- `WHATSAPP_WEBHOOK_TOKEN`
- `RELOAD` opcional (apagado por bug de OneDrive)

### Documentación

- **`SETUP.md`** en la raíz: guía paso a paso de PC nueva con troubleshooting.

## Cómo se usa

```bash
# 1. Clonar y entrar
git clone <repo> rca && cd rca

# 2. Ejecutar setup una sola vez
setup.bat            # Windows
./setup.sh           # Mac/Linux

# 3. Editar la API key
# abrir backend/.env y pegar ANTHROPIC_API_KEY=sk-ant-api03-...

# 4. Levantar los dos servidores (en terminales separadas)
start-backend.bat    # → http://localhost:8010
start-frontend.bat   # → http://localhost:5175

# 5. Login demo
# email: admin@rca.com  (o admin@demo.com en el seed viejo)
# pass:  demo1234
```

URLs útiles después de levantar:
- App: http://localhost:5175
- Swagger del backend: http://localhost:8010/docs
- Health: http://localhost:8010/health → `{"status":"ok","brand":"RCA.","version":"0.4.0"}`

### Reset de la DB

```bash
cd backend
.venv/Scripts/python.exe -m scripts.reset_db    # Windows
.venv/bin/python -m scripts.reset_db             # Mac/Linux
```

Esto hace drop all + recreate + seed. Útil cuando el modelo cambia (sin Alembic todavía).

## Tests realizados

Smoke manual:
- Clonar repo limpio, correr `setup.bat`, levantar ambos servers, login demo, navegar páginas.
- Verificar `.env` generado con vars correctas.
- Verificar que `python -m app.seed` no falla si la DB ya existe (chequea por presencia de usuarios).

## Estado y deuda

✅ **Resuelto:** setup en 1 comando funciona en Windows/Mac/Linux.

⚠️ **Notas:**
- El seed actual no es idempotente perfecto: si la DB ya tiene datos, sale sin tocar nada. Para reset completo hay que usar `scripts/reset_db.py`.
- El reload de uvicorn está apagado por default por bug conocido en OneDrive (los reload daban errores intermitentes). Para activar: `RELOAD=1` en `.env`.
- En Windows, las consolas que abren los `.bat` tienen problemas de encoding con emojis (workaround: `PYTHONIOENCODING=utf-8`).
