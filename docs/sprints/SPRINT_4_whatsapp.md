# Sprint 4 — WhatsApp bidireccional + magic links

> Commit: `2ef3571 feat(whatsapp): Sprint 4 — bidireccional con slash commands, notifs y magic links`
> Estado: ✅ cerrado

## Requisitos

El proyecto venía con un webhook `/api/whatsapp/inbound` muy básico desde el inicio: parser keyword-based que detectaba palabras como *"llegó"*, *"incidente"*, *"avance"* y creaba un Evento. Funcional pero limitado.

Para que la plataforma sirviera de verdad a los capataces (que están en obra, no frente a la PC), necesitábamos:
- **Salir de la app** (notificar al admin, al capataz, al socio) por WhatsApp.
- **Entrar a la app** con comandos útiles (`/saldo`, `/gasto IDS 5000 nafta`).
- **Aprobar acciones del agente IA desde el celu** sin tener que abrir la web ni loguearse.

**Objetivo:** WhatsApp bidireccional — la plataforma manda y recibe mensajes — con notificaciones automáticas para alertas críticas (cheques venciendo, eventos críticos, resumen semanal) y magic links firmados para aprobaciones rápidas.

## Cómo se hizo

### Restricciones del entorno

- No tenemos cuenta Twilio ni WhatsApp Cloud API activas → todo el código se construyó con un provider `log_only` por default que persiste los mensajes en DB pero no los envía. Cambiar a producción real es 1 variable de `.env`.
- El agente IA (Sprint 2) sigue bloqueado por falta de saldo Anthropic → el webhook usa primero el parser de slash commands (que NO requiere LLM) y cae al keyword parser viejo si el mensaje no es slash.

### T0 — Tabla `outbound_messages` + env vars

`backend/app/models.py`:

- Enum `OutboundMessageStatus`: `log_only`, `pending`, `sent`, `failed`.
- Tabla `OutboundMessage` con: canal, destinatario, mensaje, foto_url, provider, status, provider_message_id, error, **context_key** (idempotencia), notification_type, obra_id, user_id, related_action_id, sent_at, created_at.

`.env.example` + `.env`:
```env
WHATSAPP_PROVIDER=log_only          # log_only | twilio | cloud_api

# Twilio (opcional)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=whatsapp:+14155238886

# Meta Cloud API (opcional)
CLOUD_API_PHONE_ID=...
CLOUD_API_TOKEN=...
```

### T1 — Adaptador saliente con 3 backends

`backend/app/whatsapp_sender.py`:

```python
def send_whatsapp(db, destinatario, mensaje, *, foto_url=None,
                  notification_type="manual", obra_id=None, user_id=None,
                  related_action_id=None, context_key=None, dedupe=False) -> OutboundMessage
```

Lógica:
1. `normalize_phone()` — saca prefijo `whatsapp:`, espacios, guiones; agrega `+` si falta.
2. Si `dedupe=True` y hay otro mensaje con el mismo `(destinatario, context_key)` en estado válido, **no envía** (devuelve `None`).
3. Persiste un `OutboundMessage` con status=pending.
4. Según `WHATSAPP_PROVIDER`:
   - `log_only` → marca `log_only` y termina.
   - `twilio` → POST a Twilio Messages API con auth basic.
   - `cloud_api` → POST a Meta WhatsApp Cloud API v18.0 con bearer.
5. Si falla, marca `failed` con el error guardado.

### T2 + T3 — Webhook inbound + slash commands

`backend/app/slash_commands.py`:

```
/help                                  - lista comandos
/saldo [obra]                          - global o por obra
/cheques [dias]                        - cheques a vencer (default 30)
/aportes                               - aportes pendientes
/avance <obra> <%>                     - actualiza progreso
/gasto <obra> <monto> <concepto>       - registra EGRESO (estado A_REVISAR)
```

Cada handler devuelve `{ok, reply, ...extra}`. El parser usa `shlex` para split.

`backend/app/routers/whatsapp.py` refactoreado:

```python
@router.post("/inbound")
def inbound(payload):
    # 1. Validar token compartido
    # 2. Identificar user por phone
    # 3. Si text empieza con "/" → handle_slash()
    # 4. Si no → keyword parser viejo (crea Evento)
    # 5. send_whatsapp() de la respuesta al user (vía adapter)
    # 6. devolver {ok, reply, mode, ...}
```

Cuando llegue saldo Anthropic, el branch (4) reemplaza el keyword parser por una llamada al `orchestrator.chat()` con `canal=whatsapp` y los slash commands quedan como atajo rápido sin gasto de tokens.

### T4 — Notificaciones automáticas idempotentes

`backend/app/notifications.py`:

4 checks independientes, cada uno con su propio `context_key` para dedupar:

| Check | Trigger | context_key |
|---|---|---|
| `cheques_venciendo` | Cheques propios con vto en próx N días | `cheque_venciendo:movimiento={id}:vto={fecha}` |
| `eventos_criticos` | Eventos `es_critico=True` recientes | `evento_critico:evento={id}` |
| `resumen_semanal` | Solo lunes (o `force=True`) | `semanal:{year}-W{iso_week}` |
| `asignacion_orden` | Órdenes con cuadrilla.capataz_id | `asignacion_orden:{id}` |

Función `run_all(db, *, types=None, ...)` que corre todos o un subset.

`backend/app/routers/notifications.py`:
- `POST /api/notifications/check?cheques_dias=7&semanal_force=false&...` — corre checks (admin only).
- `GET /api/notifications/outbound?notification_type=&status=&limit=` — log de mensajes salientes.

### T5 — Magic links firmados

`backend/app/approval.py`:

```python
def make_approval_token(action_id, user_id, ttl_hours=24) -> str
def verify_approval_token(token, action_id) -> Optional[dict]
def approval_url(base_url, action_id, token, confirm: bool) -> str
```

JWT con `aud=approve`, `sub=action_id`, `confirmer=user_id`, `exp=now+ttl`. Reusa `SECRET_KEY` del .env pero con audience distinto para no mezclar tokens de login con tokens de aprobación.

`backend/app/routers/approval.py`:

`GET /api/approve/{action_id}?token=...&confirm=true|false` — endpoint **público** (sin login). Valida JWT, llama a `orchestrator.confirm_action()`, devuelve un HTML simple con UX de aprobación (verde/rojo según resultado).

### T6 — Tool `enviar_whatsapp` deja de ser stub

En `backend/app/agent/tools.py`, el handler `t_enviar_whatsapp` que en Sprint 2 era un stub ahora invoca el adapter real:

```python
msg = send_whatsapp(
    db, telefono, mensaje,
    notification_type="agente_ia",
    obra_id=obra_id,
    user_id=user.id,
)
return {"ok": ..., "outbound_id": msg.id, "provider": msg.provider, "status": msg.status.value}
```

Con provider en `log_only` el flujo queda registrado sin spam de mensajes reales.

### T7 — Página `/mensajes` UI

`frontend/src/pages/Mensajes.jsx`:

- 4 big numbers: total, log only, enviados, fallidos.
- Filtros por tipo (Manual / Agente IA / Slash command / Cheque venciendo / Evento crítico / Resumen semanal / Asignación orden) y por estado.
- Botón **"Correr notificaciones"** que dispara `POST /api/notifications/check` con `semanal_force=true&eventos_horas=999&cheques_dias=30`.
- Banner verde al volver con resumen de la corrida (X enviados, Y deduplicados, breakdown por tipo).
- Tabla con: fecha, destinatario, tipo, mensaje (preview multilínea), provider, estado (chip + ícono).

Item nuevo en sidebar (sección Administración): **Mensajes**.

## Cómo se usa

### Recibir un mensaje y responder (modo `log_only`)

Simulando que llega un mensaje del capataz Kevin (phone `+5491100000004`):

```bash
curl -s -X POST http://localhost:8010/api/whatsapp/inbound \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+5491100000004",
    "text": "/gasto SP 9999 grava para hormigon",
    "token": "set-shared-token-with-n8n"
  }'
```

Response:
```json
{
  "ok": true,
  "reply": "💸 Gasto registrado en SP\ngrava para hormigon · $10k\nEstado: A_REVISAR (cargá la factura cuando puedas)\nSaldo obra: $1.73M\n+5 XP (total: 10)",
  "movimiento_id": 14,
  "saldo_obra": 1730001.0,
  "mode": "slash"
}
```

Lo que pasa internamente:
1. Token validado.
2. Phone identifica a Kevin (User #4).
3. Texto empieza con `/` → `handle_slash()` parsea `/gasto SP 9999 grava para hormigon`.
4. Se crea un `MovimientoObra` (EGRESO, GASTO_DIRECTO_OBRA, EFECTIVO, A_REVISAR, canal=whatsapp).
5. `send_whatsapp()` registra la respuesta en `outbound_messages` con `notification_type=slash_response` (status=log_only).
6. Kevin gana 5 XP.

Si configurás `WHATSAPP_PROVIDER=twilio` con credenciales válidas, el paso 5 envía el mensaje real al WhatsApp del capataz.

### Disparar notificaciones automáticas

Desde la UI: ir a `/mensajes` → click "Correr notificaciones".

Desde HTTP:
```bash
curl -X POST "http://localhost:8010/api/notifications/check?semanal_force=true" \
  -H "Authorization: Bearer $TOKEN"
```

Response típica primera vez:
```json
{
  "checks_run": 4,
  "total_sent": 9,
  "total_skipped_dedupe": 0,
  "details": [
    {"type": "cheques_venciendo", "cheques_encontrados": 1, "sent": 3, ...},
    {"type": "eventos_criticos", "eventos_encontrados": 1, "sent": 3, ...},
    {"type": "resumen_semanal", "sent": 3, ...},
    {"type": "asignacion_orden", "ordenes_encontradas": 0, "sent": 0, ...}
  ]
}
```

Re-ejecutar inmediatamente:
```json
{ "total_sent": 0, "total_skipped_dedupe": 9, ... }
```

Idempotente. Pensado para correrse desde un cron job cada 15 minutos sin spam.

### Aprobar una acción del agente desde WhatsApp

Flujo end-to-end (cuando hay saldo Anthropic + provider real):

1. El agente IA decide hacer una acción sensible (ej: registrar movimiento de $500k).
2. Se persiste un `AgentAction` con `status=pending`.
3. Se genera un magic link:
   ```python
   token = make_approval_token(action_id=42, user_id=admin.id)
   url = approval_url("https://app.rca.com", 42, token, confirm=True)
   send_whatsapp(db, admin.phone, f"Revisá y confirmá: {url}", notification_type="approval")
   ```
4. Admin recibe el WhatsApp con el link.
5. Click → abre el browser en `https://app.rca.com/api/approve/42?token=...&confirm=true`.
6. Backend valida el JWT, ejecuta `orchestrator.confirm_action()`, devuelve un HTML verde "✅ Acción confirmada" o rojo "🚫 Cancelada".

### Configuración para producción real

Cuando tengas Twilio:
```env
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_FROM=whatsapp:+14155238886
```

Cuando tengas Meta Cloud API:
```env
WHATSAPP_PROVIDER=cloud_api
CLOUD_API_PHONE_ID=123456789012345
CLOUD_API_TOKEN=EAAxxxxxxxxxxxxxxxx
```

Reiniciar el backend. **No hace falta tocar código.** Los `outbound_messages` previos en `log_only` se mantienen como historial; los nuevos saldrán por el provider real.

## Tests realizados (suite E2E completa)

Cada flujo del sprint fue validado independientemente:

- **T1** Adapter — 6 casos: normalize_phone (varios formatos), log_only persiste, foto_url, dedupe, provider desconocido devuelve failed con mensaje claro, twilio sin credenciales devuelve failed listando qué falta.
- **T2+T3** Slash commands — 12 casos directos + 4 vía HTTP curl al webhook (incluye keyword fallback).
- **T4** Notifs — 9 enviadas primera corrida, 9 deduplicadas en la segunda. Idempotencia perfecta.
- **T5** Magic link — token inválido (HTTP 401 + HTML "Link inválido"), válido (200 + ejecuta tool + movimiento creado), re-uso ("Ya fue confirmed").
- **T6** Tool agente — 3 casos: persistencia real, sin teléfono → error, obra_ref inexistente → envía sin obra_id.
- **T7** UI Mensajes — 11 mensajes en tabla, big numbers correctos, botón "Correr notificaciones" dispara y refleja resumen.
- **T8** Suite E2E final — los 6 flujos juntos en un solo script: 13 OutboundMessages generados, 5 notification_types diferentes (agente_ia, cheque_venciendo, evento_critico, manual, resumen_semanal).

## Estado y deuda

✅ **Implementado y testeado en `log_only`:** todos los flujos del sprint funcionan.

🔒 **Bloqueado por falta de cuenta externa:**
- Tests E2E reales con Twilio o Meta Cloud API (necesitan credenciales activas + número de teléfono verificado). El cambio a producción real es 1 variable.
- El sprint mantiene un fallback al keyword parser viejo. Cuando haya saldo Anthropic, ese branch debería reemplazarse por una llamada al orchestrator del agente con `canal=whatsapp`.

📌 **Próximos pasos naturales (Sprint 5+):**
- **Vision IA** sobre `foto_url` que ya viene en el webhook: OCR de tickets/facturas, detección de cascos en fotos de obra.
- **Voice notes** transcritos con Whisper antes de pasar al parser.
- **Cron job** que corra `/api/notifications/check` cada N minutos en producción.
- **Tabla `Socio`** propia para no usar `User` con `admin_finanzas` como proxy.
