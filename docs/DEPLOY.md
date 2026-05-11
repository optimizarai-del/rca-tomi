# 🚀 Deploy a producción

Guía paso a paso para llevar RCA. a producción real. Stack recomendado:

- **Backend** — Railway (Python) o Fly.io.
- **DB** — Supabase Postgres o Railway Postgres o RDS.
- **Frontend** — Vercel.
- **Monitoreo** — Sentry (opcional).

Todo lo que sigue está pensado para hacerlo desde cero, una vez. Tiempo estimado: 60–90 min.

## 0 · Antes de empezar

Hace falta tener cuentas creadas en:
- [GitHub](https://github.com) (con el repo subido)
- [Vercel](https://vercel.com)
- [Railway](https://railway.app) o [Fly.io](https://fly.io)
- [Supabase](https://supabase.com) (opcional si vas a usar Postgres de Railway)
- [Sentry](https://sentry.io) (opcional)
- [Anthropic](https://console.anthropic.com) con saldo (para que el agente IA funcione)
- [Twilio](https://www.twilio.com) o [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp) (opcional, si querés WhatsApp real)

## 1 · Postgres en Supabase

1. Entrar a https://supabase.com → New project → región más cercana, password fuerte.
2. Esperar 2 minutos a que se aprovisione.
3. Settings → Database → **Connection string** → copiar la modalidad **URI** (psql). Algo así:
   ```
   postgresql://postgres.xxxxxxxxxxxxxxxx:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
4. Agregar el sufijo `+psycopg`:
   ```
   postgresql+psycopg://postgres.xxxx:[PASSWORD]@...
   ```
5. Aplicar las migraciones desde tu máquina:
   ```bash
   cd backend
   DATABASE_URL="postgresql+psycopg://..." .venv/bin/python -m alembic upgrade head
   DATABASE_URL="postgresql+psycopg://..." .venv/bin/python -m app.seed   # opcional, datos demo
   ```
6. Verificá en Supabase → Table Editor que aparecieron las 20 tablas.

> **Tip:** Supabase también ofrece **Storage** — útil más adelante para subir fotos de tickets, comprobantes, etc.

## 2 · Backend en Railway

1. https://railway.app → New Project → Deploy from GitHub repo.
2. Elegir el repo `rca-tomi` y la rama (`main` o `dev`).
3. Railway detecta el Dockerfile en `backend/`. Setear el directorio raíz a `backend/` si pide.
4. **Variables de entorno** (Settings → Variables):
   ```
   DATABASE_URL=postgresql+psycopg://...        ← la de Supabase
   SECRET_KEY=<string random largo>             ← generá con: python -c "import secrets; print(secrets.token_urlsafe(64))"
   CORS_ORIGINS=https://app.tu-dominio.com      ← url del frontend
   ANTHROPIC_API_KEY=sk-ant-api03-...
   AGENT_MODEL=claude-sonnet-4-5
   WHATSAPP_WEBHOOK_TOKEN=<string random>
   WHATSAPP_PROVIDER=log_only                   ← cambiar a twilio o cloud_api cuando tengas
   SENTRY_DSN=https://xxxx@oxxxx.ingest.sentry.io/xxxx   ← opcional
   PORT=8010
   ```
5. Deploy. Railway corre el `CMD` del Dockerfile: `alembic upgrade head && uvicorn`.
6. Settings → Networking → **Generate Domain**. Anotá la URL pública.
7. Verificar: `curl https://tu-backend.up.railway.app/health` → `{"status":"ok"}`.

## 3 · Frontend en Vercel

1. https://vercel.com → New Project → Import Git Repository.
2. Elegir el repo. **Root Directory:** `frontend`.
3. Framework Preset: Vite. Build Command: `npm run build`. Output: `dist`.
4. **Environment Variables:**
   ```
   VITE_API_URL=https://tu-backend.up.railway.app
   VITE_SENTRY_DSN=...                ← opcional
   ```
5. Deploy. Vercel asigna `tu-proyecto.vercel.app`.
6. **Volver a Railway** y actualizar `CORS_ORIGINS` con la URL real de Vercel. Redeploy backend.

## 4 · Sentry (opcional)

1. https://sentry.io → New Project → **Platform: FastAPI** (para backend).
2. Copiar el DSN, pegar en Railway → variable `SENTRY_DSN`.
3. Redeploy.
4. Para frontend: New Project → React → pegar el DSN en Vercel como `VITE_SENTRY_DSN`. Redeploy.
5. Para probar que captura errores, levantar manualmente una excepción en una ruta o usar `Sentry.captureMessage("test")`.

## 5 · Backups automáticos

### Opción A — Cron en Railway

Si Railway permite scheduled jobs (depende del plan):
```
schedule: "0 3 * * *"
command: bash scripts/backup_db.sh
env:
  BACKUP_DIR: /tmp/backups
```
Después subir `/tmp/backups/*.dump` a S3/Supabase Storage con otro paso del cron.

### Opción B — GitHub Actions con secrets

Crear `.github/workflows/backup.yml`:
```yaml
name: Daily DB backup
on:
  schedule: [{ cron: "0 3 * * *" }]
  workflow_dispatch: {}
jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get install -y postgresql-client
      - run: bash backend/scripts/backup_db.sh
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          BACKUP_DIR: ./backups
      - uses: actions/upload-artifact@v4
        with:
          name: db-backup-${{ github.run_id }}
          path: backups/*.dump
          retention-days: 30
```
Agregar `DATABASE_URL` en GitHub → Settings → Secrets and variables → Actions.

### Opción C — Supabase nativo

Supabase tiene backups automáticos diarios con retención 7 días en plan Pro. Si estás en plan free, hacé Opción B.

## 6 · WhatsApp real (opcional)

### Con Twilio

1. https://www.twilio.com/console → comprar número con WhatsApp habilitado.
2. Copiar Account SID + Auth Token + From.
3. Variables en Railway:
   ```
   WHATSAPP_PROVIDER=twilio
   TWILIO_ACCOUNT_SID=ACxxxx
   TWILIO_AUTH_TOKEN=xxxx
   TWILIO_FROM=whatsapp:+14155238886
   ```
4. Configurar el webhook en Twilio Console → Messaging → Try it out → WhatsApp Sandbox:
   - When a message comes in: `https://tu-backend.up.railway.app/api/whatsapp/inbound`
5. Probar enviando `/saldo` al número de Twilio desde tu WhatsApp.

### Con Meta Cloud API

1. Crear app en https://developers.facebook.com.
2. Activar WhatsApp Business → obtener Phone ID y Token.
3. Variables:
   ```
   WHATSAPP_PROVIDER=cloud_api
   CLOUD_API_PHONE_ID=123456789012345
   CLOUD_API_TOKEN=EAAxxxxxx
   ```
4. Configurar webhook en Meta → tu endpoint `/api/whatsapp/inbound`.

## 7 · Notificaciones automáticas — cron

Las notifs del Sprint 4 (cheques venciendo, eventos críticos, etc) se disparan con `POST /api/notifications/check`. Idealmente correr cada 15 minutos:

```yaml
# .github/workflows/notifications-cron.yml
name: Notifications check
on:
  schedule: [{ cron: "*/15 * * * *" }]
  workflow_dispatch: {}
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - run: |
          TOKEN=$(curl -s -X POST https://tu-backend/api/auth/login \
            -H "Content-Type: application/json" \
            -d "{\"email\":\"${{secrets.NOTIF_EMAIL}}\",\"password\":\"${{secrets.NOTIF_PASS}}\"}" | jq -r .access_token)
          curl -s -X POST "https://tu-backend/api/notifications/check?cheques_dias=7&eventos_horas=2" \
            -H "Authorization: Bearer $TOKEN"
```

Los lunes a las 8am UTC, agregá un job adicional con `semanal_force=true` para mandar el resumen semanal.

## 8 · Checklist final pre-producción

- [ ] Pytest CI en verde para la rama `main`.
- [ ] `SECRET_KEY` único y random (NO el de dev).
- [ ] `CORS_ORIGINS` solo incluye tu dominio real.
- [ ] `DATABASE_URL` apunta a Postgres (no SQLite).
- [ ] HTTPS funciona en backend y frontend (Vercel y Railway lo dan automático).
- [ ] Backup automático configurado y probado restoreando en una DB de staging.
- [ ] Sentry recibe el primer error de prueba.
- [ ] Si usás WhatsApp real, mandaste y recibiste un mensaje desde producción.

## 9 · Cómo restaurar un backup

### SQLite
```bash
gunzip -k rca_20260511_202731.sqlite.gz
cp rca_20260511_202731.sqlite backend/fielddata.db
```

### Postgres
```bash
pg_restore --clean --if-exists --no-owner --no-privileges \
    --dbname="$DATABASE_URL" rca_20260511_030000.dump
```

## 10 · Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| 502 en el backend al deploy | Falta `DATABASE_URL` o está mal el formato | Revisar Railway → Variables, debe empezar con `postgresql+psycopg://` |
| CORS error en el browser | `CORS_ORIGINS` no incluye la URL del frontend | Editar en Railway → Redeploy |
| Pytest CI falla en `alembic upgrade head` | Hay migraciones huérfanas o conflictos | Localmente: `alembic history`, ajustar |
| Frontend muestra "Error de conexión con el agente" | `ANTHROPIC_API_KEY` falta o sin saldo | console.anthropic.com → Billing |
| WhatsApp no responde nada | Provider en `log_only` (default) o credenciales mal | Revisar `outbound_messages` en DB para ver qué pasó |
