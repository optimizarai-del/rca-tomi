# Sprint 20 — Deploy producción + dominio + handoff a Tomi

> Estado: 🟡 en curso · objetivo: dejar `rca.<dominio>` corriendo en VPS con Tomi como dueño operativo.

## Requisitos

Notas de reunión 2026-05-19:

- "Deployar y pasar link del dominio a Tomi" — última pieza para que Tomi pruebe en producción real.

## Alcance del sprint

1. **Infra**
   - VPS con Easy Panel ya configurado.
   - Proyecto Supabase creado y connection string a mano.
   - Dominio o subdominio apuntando a la IP del VPS (registro `A`).
2. **App**
   - Stack `docker-compose.yml` ya armado (sprint anterior). Falta solo apretar deploy con las env vars reales.
   - DB inicial: correr `alembic upgrade head` (lo hace el backend al arrancar) + decidir si seedeamos demo o no.
3. **Bots**
   - Configurar Telegram en producción (token + webhook + chat_ids autorizados).
4. **Handoff**
   - Crear usuario `admin` real para Tomi.
   - Doc operativa simple para Tomi (cómo loguearse, cómo invitar a la arquitecta, cómo vincular Telegram, qué hacer si algo se rompe).

## Cómo se hace

### T1 — Preparar Supabase

1. https://supabase.com → New project.
2. Region: la más cercana a tu VPS (típicamente `sa-east-1` São Paulo para AR).
3. Anotar `Project Ref` y guardar la `Database password` en un manager (1Password / Bitwarden).
4. Ir a *Settings → Database → Connection pooling* → copiar el **Session pooler** connection string.
5. Reemplazar el prefijo `postgresql://` por `postgresql+psycopg://` (lo necesita SQLAlchemy + psycopg).

### T2 — Crear servicio en Easy Panel

Ya cubierto en [DEPLOY_EASYPANEL.md](../../DEPLOY_EASYPANEL.md) pasos 2–4. Branch a deployar: **`dev`** (es la que tiene todo mergeado).

### T3 — Env vars productivas

Variables críticas (las no listadas se dejan en default):

```env
DATABASE_URL=postgresql+psycopg://postgres.PROJREF:PASS@aws-0-REGION.pooler.supabase.com:5432/postgres
SECRET_KEY=<generar con: python -c "import secrets; print(secrets.token_urlsafe(48))">
ANTHROPIC_API_KEY=sk-ant-api03-...
AGENT_MODEL=claude-sonnet-4-5
CORS_ORIGINS=https://rca.tudominio.com
VITE_API_URL=
SENTRY_DSN=<opcional, ver T6>
```

### T4 — Primer deploy + seed

1. Deploy en Easy Panel.
2. Verificar `Uvicorn running on http://0.0.0.0:8010` en logs.
3. Crear el usuario admin de Tomi. Desde la **Console** del container backend:

   ```bash
   python -c "
   from app.database import SessionLocal
   from app.models import User
   from app.security import hash_password
   db = SessionLocal()
   u = User(
       email='tomi@rca.com',
       hashed_password=hash_password('CAMBIAR-ESTA-PASS'),
       nombre='Tomi',
       rol='admin',
       is_demo=False,
   )
   db.add(u); db.commit()
   print('user creado:', u.id)
   "
   ```

   ⚠️ Cambiar la pass apenas Tomi entre la primera vez (cuando exista esa funcionalidad — hoy hay que editar la DB).

4. **NO** correr `python -m scripts.reset_db` en producción — eso dropea todo. La DB real arranca vacía y se va cargando por bot.

### T5 — Dominio + SSL

1. DNS: registro `A` de `rca.tudominio.com` → IP del VPS.
2. Easy Panel → servicio compose → *Domains* → **+ Add Domain** → servicio `frontend`, puerto 80.
3. SSL automático Let's Encrypt (1-2 min).
4. Test:
   - `https://rca.tudominio.com` → login.
   - `https://rca.tudominio.com/health` → JSON con `status: ok`.
   - `https://rca.tudominio.com/api/docs` → Swagger.

### T6 — Telegram en producción

1. [@BotFather](https://t.me/BotFather) → `/newbot` → guardar el token.
2. Env vars en Easy Panel:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_WEBHOOK_SECRET=<generar random largo>
   TELEGRAM_AUTHORIZED_CHAT_IDS=<chat_id de Tomi>,<chat_id de la arquitecta>
   ```
   (Para conseguir el `chat_id` de alguien: que le escriba a [@userinfobot](https://t.me/userinfobot) y reenvíe el número.)
3. Redeploy.
4. Registrar webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
        -d "url=https://rca.tudominio.com/api/telegram/webhook" \
        -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
   ```
5. Test desde Telegram: mandarle `/start` al bot. Después `/vincular tomi@rca.com`.

### T7 — Sentry (opcional, recomendado)

1. https://sentry.io → New project → Python (FastAPI).
2. Copiar DSN.
3. Env var: `SENTRY_DSN=https://...@sentry.io/...`.
4. Redeploy. Cualquier excepción del backend va a llegar a Sentry.

### T8 — Doc operativa para Tomi

Crear `docs/HANDOFF_TOMI.md` con:

- URL del sistema + credenciales iniciales.
- Cómo se vincula Telegram (`/vincular <email>`).
- Cómo invitar a alguien al sistema (crear user en `/equipo`).
- Qué hacer si "no funciona" (logs en Easy Panel, contactar a Gero, etc.).
- Glosario de slash-commands del bot (`/stock`, `/presupuesto`, `/req`, etc.).

## Checklist de cierre

- [ ] Supabase proyecto creado y `DATABASE_URL` armada.
- [ ] Deploy en Easy Panel funcionando, health check OK.
- [ ] DNS + SSL del dominio configurado.
- [ ] Usuario admin de Tomi creado en DB.
- [ ] Telegram bot creado, webhook registrado, `TELEGRAM_AUTHORIZED_CHAT_IDS` con chat_id de Tomi.
- [ ] `/vincular` testeado de punta a punta con Tomi.
- [ ] (Opcional) Sentry conectado.
- [ ] `docs/HANDOFF_TOMI.md` escrito.
- [ ] Link + credenciales pasadas a Tomi por canal privado.

## Deuda pendiente / fuera de scope

- **Cambio de password desde la UI**: hoy hay que editar la DB. Se cubre con el panel de usuarios del Sprint 13.
- **Auto-deploy en push**: configurar webhook GitHub → Easy Panel deploy. No bloquea, se hace cuando estabilice.
- **WhatsApp**: queda en `log_only`. Se reactiva si lo piden explícitamente.
