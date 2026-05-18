# 🚀 Deploy en Easy Panel

Guía para levantar RCA en un VPS con [Easy Panel](https://easypanel.io). El stack queda como:

```
            ┌─────────────────────────────────┐
            │  Internet  →  Easy Panel proxy   │
            │            (SSL automático)      │
            └────────────────┬─────────────────┘
                             ▼
                ┌─────────────────────────┐
                │  frontend (nginx :80)   │  ← dominio público
                │   - sirve la SPA        │
                │   - proxy /api → backend│
                └────────────┬────────────┘
                             ▼
                ┌─────────────────────────┐
                │  backend (FastAPI :8010)│  ← interno, no expuesto
                │   - agente IA           │
                │   - bots WhatsApp/TG    │
                └────────────┬────────────┘
                             ▼
                ┌─────────────────────────┐
                │   db (Postgres 16)      │  ← volumen persistente
                └─────────────────────────┘
```

**Un solo dominio** sirve todo. El nginx del frontend hace `proxy_pass /api → backend:8010` interno — no hay CORS que configurar, no se exponen puertos del backend a internet.

---

## 1. Prerequisitos

- Una VPS con Easy Panel ya instalado.
- Un dominio o subdominio apuntando a tu VPS (ej. `rca.tudominio.com`).
- Una **API key de Anthropic** (https://console.anthropic.com/settings/keys).
- (Opcional) Bot tokens de WhatsApp/Telegram si vas a usar esas integraciones.

---

## 2. Crear el proyecto en Easy Panel

1. Entrá al panel.
2. **+ Create Project** → ponele un nombre, ej. `rca`.
3. Dentro del proyecto: **+ Create Service** → **Compose**.
4. En "Source":
   - Tipo: **GitHub**
   - Repository: `optimizarai-del/rca-tomi`
   - Branch: `sprint-11-telegram-bot` (o la rama que querramos desplegar).
   - Build Path: `/` (raíz, donde está el `docker-compose.yml`).

---

## 3. Cargar las variables de entorno

En el servicio Compose, **Environment** → pegá lo siguiente y completá los valores marcados:

```env
# ── DB ───────────────────────────────────────────────────────────
POSTGRES_USER=rca
POSTGRES_PASSWORD=PONÉ-UNA-PASS-LARGA-RANDOM-AQUI
POSTGRES_DB=rca
DATABASE_URL=postgresql+psycopg://rca:PONÉ-UNA-PASS-LARGA-RANDOM-AQUI@db:5432/rca

# ── Auth ─────────────────────────────────────────────────────────
SECRET_KEY=GENERA-UN-STRING-LARGO-RANDOM-DE-48-CHARS-O-MÁS
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── CORS / Frontend ──────────────────────────────────────────────
CORS_ORIGINS=*
VITE_API_URL=
FRONTEND_PORT=8080

# ── Agente IA (REQUERIDO) ────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-api03-TU-KEY-AQUI
AGENT_MODEL=claude-sonnet-4-5

# ── WhatsApp (opcional) ──────────────────────────────────────────
WHATSAPP_PROVIDER=log_only
WHATSAPP_WEBHOOK_TOKEN=cambia-este-token-secreto

# ── Telegram (opcional) ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_AUTHORIZED_CHAT_IDS=
TELEGRAM_WEBHOOK_SECRET=

# ── Sentry (opcional) ────────────────────────────────────────────
SENTRY_ENV=production
SENTRY_TRACES_RATE=0.1
```

> **Tip:** generar el `SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"` desde cualquier terminal con Python instalado.

---

## 4. Configurar el dominio

1. En el servicio Compose, después del primer deploy, andá a **Domains**.
2. **+ Add Domain** → apuntá al servicio **`frontend`** en el puerto **`80`** (interno del container).
3. Easy Panel maneja SSL automático con Let's Encrypt. Esperá 1-2 minutos.
4. Verificá que en tu DNS, el dominio apunte a la IP del VPS (registro `A`).

> **Importante:** NO expongas el servicio `backend` a internet. Solo el `frontend`. El frontend nginx ya proxea `/api/*` al backend interno.

---

## 5. Deploy

Tocá **Deploy** en Easy Panel. La primera vez va a:

1. Clonar el repo.
2. Construir imágenes (`frontend` ~3 min, `backend` ~2 min).
3. Levantar `db`.
4. Backend corre `alembic upgrade head` automáticamente y arranca uvicorn.
5. Frontend nginx queda listo.

Mirá los **Logs** del servicio compose para ver el progreso. Cuando el backend imprime `Uvicorn running on http://0.0.0.0:8010`, estás listo.

---

## 6. Cargar datos demo (opcional, solo primera vez)

Si querés arrancar con las obras demo (IDS Colegio Domingo Savio + Casa San Pedro):

En Easy Panel → servicio compose → **Console** del contenedor `rca_backend`:

```bash
python -m scripts.reset_db
```

⚠️ Esto **DROPea todas las tablas** y vuelve a poblar. Solo hacelo cuando la DB está vacía. Después se logea con:

```
admin@rca.com / demo1234
```

---

## 7. Probar

1. Abrí `https://rca.tudominio.com` → pantalla de login.
2. Logueate.
3. Abrí el **Operario IA** (botón flotante abajo derecha).
4. Pregunta: *"resumen del estado financiero global"*.
5. El agente debería contestar con datos reales.

Checks:
- `https://rca.tudominio.com/healthz` → `ok` (nginx)
- `https://rca.tudominio.com/health` → `{"status":"ok","brand":"RCA.","version":"..."}` (proxy al backend)
- `https://rca.tudominio.com/api/docs` → Swagger del FastAPI

---

## 8. Backups

Easy Panel tiene backup integrado para volúmenes Docker. En el servicio compose → **Backups** → schedule diario del volumen `rca_pgdata`.

Para restaurar manualmente desde la consola del contenedor:

```bash
# Dump
pg_dump -U rca -d rca > /tmp/rca-$(date +%F).sql

# Restore (en otro server / mismo volumen vacío)
psql -U rca -d rca < /tmp/rca-2026-05-17.sql
```

---

## 9. Configurar bots (opcional)

### Telegram

1. Crear bot con [@BotFather](https://t.me/BotFather): `/newbot` → copiar token.
2. Setear en Easy Panel:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_WEBHOOK_SECRET=un-string-random-tuyo
   ```
3. Redeploy.
4. Registrar el webhook desde tu máquina:
   ```bash
   curl -X POST "https://api.telegram.org/bot$TOKEN/setWebhook" \
        -d "url=https://rca.tudominio.com/api/telegram/webhook" \
        -d "secret_token=tu-secret-de-arriba"
   ```
5. En Telegram, mandale `/vincular <email>` al bot para asociar tu cuenta.

### WhatsApp (Twilio o Cloud API)

Ver `backend/.env.example` para las vars específicas. Luego configurar el webhook del proveedor apuntando a:

```
https://rca.tudominio.com/api/whatsapp/inbound
```

con el `WHATSAPP_WEBHOOK_TOKEN` que pusiste en las vars.

---

## 10. Troubleshooting

| Síntoma | Solución |
|---------|----------|
| Frontend abre pero `/api/*` da 502 | El backend no arrancó. Mirá logs del container `rca_backend` — suele ser Alembic con DB no lista (esperá 30s más) o `ANTHROPIC_API_KEY` faltante. |
| Login da CORS error | Estás llamando al backend desde otro dominio. Configurá `CORS_ORIGINS` con tu dominio explícito en vez de `*`. |
| El agente IA dice "no configurado" | Falta `ANTHROPIC_API_KEY` o quedó vacío en las env vars del compose. Redeploy después de setearlo. |
| Alembic falla con "FATAL: database does not exist" | El servicio `db` todavía no está listo. Easy Panel debería respetar el `depends_on healthy` — esperá y rehacé deploy. |
| Cambié variables pero no se aplican | El backend necesita restart del container. Tocá **Restart** en el servicio compose, no rebuild. |
| Quiero exponer el backend en otro subdominio | Edita `docker-compose.yml`, descomentá `ports: 8010:8010` en `backend`, y agregá un Domain en Easy Panel apuntando al servicio backend. |

---

## 11. Actualizar el deploy

Cada vez que pushees a la rama configurada:

1. Easy Panel → servicio compose → **Deploy** (o configurá auto-deploy desde GitHub webhook).
2. Esperá build + restart.
3. Alembic corre migraciones nuevas automáticamente.

Para volver a una versión anterior:

1. Cambiá la branch o tag en la config del servicio.
2. Deploy.
3. (Si la migración no es reversible, restaurá desde backup primero.)

---

## 📋 Resumen de qué expone Easy Panel a internet

| Servicio | Puerto interno | Puerto en VPS | Dominio público |
|----------|---------------|---------------|------------------|
| `frontend` | 80 | proxy de Easy Panel | ✅ `rca.tudominio.com` |
| `backend` | 8010 | — | ❌ (solo accesible vía `/api/*` del frontend) |
| `db` | 5432 | — | ❌ (solo accesible desde backend) |

Eso es todo. Si algo no anda, pasame el log del container y lo debugeamos.
