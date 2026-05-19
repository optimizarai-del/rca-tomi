# Sprint 11 — Bot de Telegram (texto)

> Estado: ✅ cerrado (Sprint 11a) · suite pytest **90/90** verde

## Requisitos

Decisión de la reunión 2026-05-13/17: **reemplazar WhatsApp por Telegram** como canal del bot, "por ahora". Razones:

- Telegram tiene Bot API **gratis y abierta** (Twilio cobra, Meta Cloud API requiere business approval).
- Token vía [@BotFather](https://t.me/BotFather), 5 minutos de setup.
- API uniforme para texto, audio e imágenes (esto último habilita el Sprint 11b — OCR de tickets con Claude Vision).

La premisa central no cambia: **toda la carga operativa va por bot**. La web es para visualización y confirmación.

## Cómo se hizo

### T1 — Rama

Branch `sprint-11-telegram-bot` desde `sprint-9-10-stock-presupuesto`.

### T2 — Modelo: User extendido

[backend/app/models.py](../../backend/app/models.py) — 4 campos nuevos en `User`:

```python
telegram_chat_id = Column(String, unique=True, index=True)
telegram_username = Column(String)
telegram_vinculacion_code = Column(String)       # generado por admin
telegram_vinculacion_exp = Column(DateTime)      # TTL 15 minutos
```

Migración Alembic [6706465fbb3c](../../backend/alembic/versions/6706465fbb3c_sprint_11_telegram_bot_fields_on_user.py).

### T3 — Configuración

`.env` y `.env.example` ([backend/.env.example](../../backend/.env.example)) suman 3 variables:

```bash
TELEGRAM_BOT_TOKEN=          # de @BotFather
TELEGRAM_AUTHORIZED_CHAT_IDS= # whitelist CSV; vacío = nadie autorizado
TELEGRAM_WEBHOOK_SECRET=     # secret_token validado en cada webhook
```

### T4 — Adaptador `telegram_sender.py`

[backend/app/messaging/telegram_sender.py](../../backend/app/messaging/telegram_sender.py): paralelo a `whatsapp_sender.py`.

Funciones:
- `send_telegram(db, chat_id, mensaje, ...)` — envía y persiste en `outbound_messages` (canal=`telegram`).
- `get_file_url(file_id)` — devuelve URL temporal para descargar archivos (preparado para Sprint 11b).
- `authorized_chat_ids()` — set de chat_ids autorizados leído de env.

Comportamiento:
- Si `TELEGRAM_BOT_TOKEN` está vacío → mensajes quedan como `log_only` (no rompe).
- Soporta `dedupe=True` con `context_key` (idempotencia para notificaciones automáticas).

### T5 + T6 — Router del webhook + ruteo

[backend/app/routers/telegram.py](../../backend/app/routers/telegram.py): endpoint `POST /api/telegram/webhook`.

Pipeline:

1. Validar header `X-Telegram-Bot-Api-Secret-Token` contra `TELEGRAM_WEBHOOK_SECRET`. Si falla → 200 con `ok=false` (Telegram no debe reintentar).
2. Sacar `chat_id` + texto del payload.
3. **Comandos especiales (sin whitelist):** `/start` y `/vincular <código>` siempre se procesan, son el único onboarding.
4. **Whitelist (policy b):** si `chat_id` NO está en `TELEGRAM_AUTHORIZED_CHAT_IDS` → ignorar silencioso, no responder.
   - Importante: lista vacía = nadie autorizado (seguridad por defecto).
5. **User binding:** si el chat está en whitelist pero el chat_id no está asociado a ningún User → mensaje de guía.
6. **Slash commands** (`/saldo`, `/stock`, `/cheques`, etc.) → `handle_slash()` del módulo existente.
7. **Texto libre** → `agent_chat()` del orchestrator. Si la respuesta del agente trae `pending_actions`, se anexan al mensaje pidiendo confirmación en la web.

Todo el ruteo **reusa** `slash_commands.py` y `orchestrator.py` sin modificarlos.

### T7 — Polling para desarrollo local

[backend/scripts/telegram_polling.py](../../backend/scripts/telegram_polling.py): alternativa al webhook cuando no hay URL pública.

```bash
cd backend
./.venv/Scripts/python.exe scripts/telegram_polling.py
```

- Hace `deleteWebhook` al arrancar (polling y webhook son excluyentes).
- Long-poll de 25s con `getUpdates`.
- Procesa cada update con `_handle_update()` del router (mismo flujo que el webhook).
- Maneja `SIGINT`/`SIGTERM` para shutdown limpio.

### T8 — Registro de webhook en producción

[backend/scripts/telegram_set_webhook.py](../../backend/scripts/telegram_set_webhook.py):

```bash
# Registrar contra dominio público
python scripts/telegram_set_webhook.py https://api.tu-dominio.com

# Volver a polling
python scripts/telegram_set_webhook.py --delete

# Ver estado actual
python scripts/telegram_set_webhook.py --info
```

Configura `secret_token=$TELEGRAM_WEBHOOK_SECRET`, así Telegram lo manda en cada llamada y el webhook lo valida.

### T9 — Vinculación User ↔ chat

**Endpoints en [backend/app/routers/users.py](../../backend/app/routers/users.py):**

- `POST /api/users/{uid}/telegram/generate-code` (admin) → genera código de 6 dígitos, TTL 15 min.
- `DELETE /api/users/{uid}/telegram` (admin) → desvincula.

**Flujo:**

1. Admin entra a `/equipo`, clickea **"Vincular TG"** al lado del usuario.
2. Modal muestra el código (ej: `847215`) y la instrucción: *"Pedile a Tomi que abra el bot y mande: `/vincular 847215`"*.
3. Tomi abre el bot, manda `/vincular 847215`.
4. El webhook valida código + TTL, asocia `chat_id` + `username` al User y consume el código.
5. Tomi recibe confirmación: *"✅ Listo, Tomi! Tu cuenta está vinculada."*.

**UI:** [frontend/src/pages/Equipo.jsx](../../frontend/src/pages/Equipo.jsx) muestra chip "Telegram @user" cuando está vinculado + botón Vincular/Desvincular.

### T10 — Tests

[backend/tests/test_telegram.py](../../backend/tests/test_telegram.py) con **13 tests**:

| Categoría | Tests |
|---|---|
| Adaptador | log_only fallback, dedupe, llamada real (httpx mockeado), parseo CSV whitelist |
| Webhook | rechaza secret inválido, acepta secret correcto, whitelist policy b (silencio) |
| Vinculación | admin genera código + user lo usa, código expirado falla, código inexistente falla, /start sin código da ayuda |
| Slash | `/saldo` desde Telegram funciona |
| Desvinculación | admin desvincula y limpia campos |

**Suite total:** 90/90 verde (77 anteriores + 13 nuevos).

## Cómo se usa

### Setup inicial (una vez)

1. Crear bot en [@BotFather](https://t.me/BotFather) → copiar el token.
2. Pegar token en `backend/.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=8832312701:AAFSFh6km7ZsKXZSc_8RpzB4wbOnQ_B2LIw
   TELEGRAM_AUTHORIZED_CHAT_IDS=1222571438
   TELEGRAM_WEBHOOK_SECRET=cualquier-string-aleatorio
   ```
3. Aplicar migración: `alembic upgrade head`.

### Desarrollo local (sin URL pública)

```bash
# Terminal 1: backend
./start-backend.bat

# Terminal 2: polling
cd backend && ./.venv/Scripts/python.exe scripts/telegram_polling.py
```

### Producción (con URL pública)

```bash
# Una vez después del deploy
python scripts/telegram_set_webhook.py https://api.tu-dominio.com
```

### Onboarding de Tomi

1. Tomi abre el bot en Telegram, manda `/start`.
2. El bot responde con instrucciones + el `chat_id` de Tomi.
3. Admin entra a la web → Equipo → busca a Tomi → **"Vincular TG"** → copia el código.
4. Le pasa el código a Tomi (verbal/WhatsApp).
5. Tomi manda `/vincular <código>` al bot.
6. Listo, Tomi puede usar todos los comandos y el agente IA.

### Comandos disponibles

Los mismos del Sprint 4 (`/saldo`, `/cheques`, `/aportes`, `/avance`, `/gasto`, `/stock`, `/help`). Texto libre lo procesa el agente IA con confirmación humana en la web.

## Decisiones tomadas

| Decisión | Por qué |
|---|---|
| Telegram como provider | Gratis, sin approval, API uniforme texto+imágenes |
| Whitelist por chat_id | Más simple y más seguro que API key compartida |
| Policy b (ignorar silencioso) | Si un bot público recibe spam, no responder evita revelar que el bot existe |
| `/vincular <código>` en vez de auto-detect por phone | El chat_id es estable y único; el phone no siempre coincide |
| Código de 6 dígitos numéricos, TTL 15 min | Suficientemente fuerte para un canal con whitelist activa |
| Whitelist vacía = nadie autorizado | Default seguro (no exponer el bot por accidente) |

## Estado y deuda

✅ **Cerrado:** adaptador, webhook, polling, vinculación, UI, tests.

⚠️ **Deuda menor:**
- El bot todavía NO procesa imágenes. Eso queda para **Sprint 11b — OCR de tickets con Claude Vision**.
- Las notificaciones automáticas (cheques a vencer, etc.) siguen usando `whatsapp_sender`. Hay que decidir si las pasamos a Telegram o las dejamos en ambos canales según preferencia del user.
- No hay "deep link" auto-vinculación (`https://t.me/bot?start=código`). Hoy el admin pasa el código manualmente. Es una mejora menor para Sprint 11c.

📌 **Cómo se conecta:**
- **Sprint 2** (agente IA): el orchestrator se reutiliza tal cual. Tools de escritura siguen requiriendo confirmación humana en la web.
- **Sprint 4** (WhatsApp): coexisten. El adaptador `whatsapp_sender.py` sigue funcionando. Se puede migrar gradualmente.
- **Sprint 7** (roles): la whitelist es independiente del rol. Un `supervisor` con chat_id en la whitelist tiene los mismos permisos que tendría desde la web.
- **Sprint 9/10** (stock/presupuestos): las 8 tools nuevas funcionan idénticamente desde Telegram. Tomi puede mandar *"cargá 100 bolsas de cemento compradas a Holcim"* y el agente lo procesa.
