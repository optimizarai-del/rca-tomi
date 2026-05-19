"""Sprint 11 — Webhook inbound de Telegram.

Pipeline cuando llega un Update de Telegram:
  1. Validar X-Telegram-Bot-Api-Secret-Token contra TELEGRAM_WEBHOOK_SECRET.
  2. Sacar chat_id + texto del payload.
  3. Si es `/start` o `/vincular <codigo>`: flujo especial (sin requerir whitelist).
  4. Si chat_id NO está en TELEGRAM_AUTHORIZED_CHAT_IDS → ignorar silencioso (whitelist policy b).
  5. Identificar User por telegram_chat_id; si no está vinculado → mensaje guía.
  6. Si texto empieza con /: slash command (sin LLM).
  7. Sino: chat() del agente IA (orchestrator), responder con el texto + acciones pendientes.
  8. send_telegram con la respuesta.

El endpoint devuelve 200 siempre (Telegram reintenta agresivamente si recibe 5xx).
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.slash_commands import is_slash_command, handle_slash
from app.messaging.telegram_sender import (
    send_telegram, authorized_chat_ids, webhook_secret,
)
from app.agent.orchestrator import chat as agent_chat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["telegram"])


def _bind_user_to_chat(db: Session, code: str, chat_id: str, username: Optional[str]) -> Optional[models.User]:
    """Si el código existe y no expiró, asocia el chat_id al User. Devuelve el User o None."""
    if not code:
        return None
    now = datetime.utcnow()
    user = db.query(models.User).filter(
        models.User.telegram_vinculacion_code == code.strip(),
        models.User.telegram_vinculacion_exp.is_not(None),
        models.User.telegram_vinculacion_exp > now,
    ).first()
    if not user:
        return None
    # Si otro user ya tiene este chat_id, lo desvinculamos
    db.query(models.User).filter(
        models.User.telegram_chat_id == chat_id,
        models.User.id != user.id,
    ).update({"telegram_chat_id": None, "telegram_username": None})
    user.telegram_chat_id = chat_id
    user.telegram_username = username
    user.telegram_vinculacion_code = None
    user.telegram_vinculacion_exp = None
    db.commit(); db.refresh(user)
    return user


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """Webhook que Telegram llama cuando llega un mensaje al bot."""
    secret = webhook_secret()
    if secret and x_telegram_bot_api_secret_token != secret:
        # Telegram interpreta 401 como "no reintentar".
        return {"ok": False, "reason": "bad-secret"}

    try:
        update = await request.json()
    except Exception as e:
        logger.warning(f"[tg] payload no JSON: {e}")
        return {"ok": False, "reason": "bad-payload"}

    return _handle_update(update, db)


def _handle_update(update: dict, db: Session) -> dict:
    """Procesa un Update. Separado para reusar desde polling script."""
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    from_ = message.get("from") or {}
    username = from_.get("username")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        # Por ahora ignoramos mensajes no-texto (fotos, etc.) — Sprint 11b las maneja
        if message.get("photo"):
            send_telegram(db, chat_id, "📸 Imágenes todavía no las proceso — voy a aprender en el próximo sprint.",
                         notification_type="telegram_unsupported")
        return {"ok": True, "handled": False}

    # ─── Vinculación (acepta SIN whitelist) ─────────────────────
    if text.startswith("/start") or text.startswith("/vincular"):
        parts = text.split(maxsplit=1)
        code = (parts[1] if len(parts) > 1 else "").strip()
        if not code:
            send_telegram(
                db, chat_id,
                "👋 Hola! Para vincular tu cuenta:\n\n"
                "1. Entrá a la web RCA. → Usuarios.\n"
                "2. Buscá tu usuario y apretá 'Vincular Telegram'.\n"
                "3. Vuelve acá y mandá:  /vincular <código>\n\n"
                f"📋 Tu chat_id es: `{chat_id}`",
                parse_mode="Markdown",
                notification_type="telegram_help",
            )
            return {"ok": True, "handled": True, "mode": "vincular_help"}

        user = _bind_user_to_chat(db, code, chat_id, username)
        if not user:
            send_telegram(
                db, chat_id,
                "❌ Código inválido o expirado. Generá uno nuevo desde la web.",
                notification_type="telegram_vincular_fail",
            )
            return {"ok": True, "handled": True, "mode": "vincular_fail"}

        send_telegram(
            db, chat_id,
            f"✅ Listo, {user.name}! Tu cuenta está vinculada.\n\n"
            "Probá:\n"
            "  /saldo               - saldo global\n"
            "  /stock cemento       - stock de un material\n"
            "  /cheques 30          - cheques a vencer\n"
            "  /help                - ver todos los comandos\n\n"
            "O escribime libre y entiendo lo que necesitás.",
            notification_type="telegram_vincular_ok",
            user_id=user.id,
        )
        return {"ok": True, "handled": True, "mode": "vincular_ok", "user_id": user.id}

    # ─── Whitelist (policy b: ignorar silencioso) ───────────────
    # Whitelist vacía = nadie autorizado (seguridad por defecto).
    autorizados = authorized_chat_ids()
    if chat_id not in autorizados:
        logger.info(f"[tg:unauth] chat={chat_id} username={username} text={text[:40]!r}")
        return {"ok": True, "handled": False, "reason": "not-whitelisted"}

    # ─── User identification ────────────────────────────────────
    user = db.query(models.User).filter(models.User.telegram_chat_id == chat_id).first()
    if not user:
        send_telegram(
            db, chat_id,
            "⚠️ Tu chat está en la whitelist pero todavía no está vinculado a un usuario.\n"
            "Pedile al admin un código y mandá:  /vincular <código>",
            notification_type="telegram_no_user",
        )
        return {"ok": True, "handled": False, "reason": "no-user-binding"}

    # ─── Slash commands ─────────────────────────────────────────
    if is_slash_command(text):
        try:
            result = handle_slash(text, user, db)
        except Exception as e:
            logger.exception(f"[tg:slash] error: {e}")
            send_telegram(db, chat_id, f"❌ Error procesando el comando: {e}",
                         notification_type="telegram_slash_error", user_id=user.id)
            return {"ok": False, "handled": True}
        reply = result.get("reply", "(sin respuesta)")
        send_telegram(db, chat_id, reply,
                     notification_type="slash_response",
                     user_id=user.id, obra_id=result.get("obra_id"))
        return {"ok": True, "handled": True, "mode": "slash"}

    # ─── Agente IA ──────────────────────────────────────────────
    try:
        result = agent_chat(user, text, db)
    except Exception as e:
        logger.exception(f"[tg:agent] error: {e}")
        send_telegram(db, chat_id, f"❌ El agente tuvo un error: {e}",
                     notification_type="telegram_agent_error", user_id=user.id)
        return {"ok": False, "handled": True}

    reply = result.get("reply") or "(sin respuesta)"
    pendientes = result.get("pending_actions") or []
    if pendientes:
        bloques = ["⏸️ Acciones pendientes de confirmar:"]
        for a in pendientes:
            bloques.append(f"  • #{a.get('id')}: {a.get('tool_name')} — {a.get('preview', '')[:120]}")
        bloques.append("\nConfirmá desde la web (Operario IA → botones de cada acción).")
        reply = (reply + "\n\n" + "\n".join(bloques)).strip()

    send_telegram(db, chat_id, reply,
                 notification_type="agente_ia",
                 user_id=user.id)
    return {"ok": True, "handled": True, "mode": "agent",
            "tools_used": result.get("tools_used", []),
            "pending": len(pendientes)}
