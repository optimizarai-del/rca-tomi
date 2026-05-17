"""Adaptador para enviar mensajes salientes por Telegram Bot API (Sprint 11).

Sigue el mismo patrón que `app/whatsapp_sender.py`:
- Persiste TODO en `outbound_messages` (canal='telegram').
- Si el token no está seteado, queda como `log_only` (no rompe la app).
- Soporta dedupe via `context_key`.

Uso:
    from app.messaging.telegram_sender import send_telegram
    send_telegram(db, chat_id="1222571438", mensaje="hola", notification_type="manual")

API ref: https://core.telegram.org/bots/api#sendmessage
"""
from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)

TG_API_BASE = "https://api.telegram.org"


def _bot_token() -> Optional[str]:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    return token or None


def authorized_chat_ids() -> set[str]:
    """Devuelve el set de chat_id autorizados según .env (como strings)."""
    raw = (os.getenv("TELEGRAM_AUTHORIZED_CHAT_IDS") or "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def webhook_secret() -> Optional[str]:
    s = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    return s or None


def send_telegram(
    db: Session,
    chat_id: str,
    mensaje: str,
    *,
    parse_mode: Optional[str] = None,    # "Markdown" o "HTML" o None
    notification_type: str = "manual",
    obra_id: Optional[int] = None,
    user_id: Optional[int] = None,
    related_action_id: Optional[int] = None,
    context_key: Optional[str] = None,
    dedupe: bool = False,
    reply_to_message_id: Optional[int] = None,
) -> Optional[models.OutboundMessage]:
    """Envía un mensaje de Telegram. Persiste el registro en outbound_messages."""
    chat_id = str(chat_id).strip()
    token = _bot_token()
    provider = "telegram" if token else "log_only"

    if dedupe and context_key:
        existing = db.query(models.OutboundMessage).filter(
            models.OutboundMessage.destinatario == chat_id,
            models.OutboundMessage.context_key == context_key,
            models.OutboundMessage.status.in_([
                models.OutboundMessageStatus.log_only,
                models.OutboundMessageStatus.sent,
                models.OutboundMessageStatus.pending,
            ]),
        ).first()
        if existing:
            logger.info(f"[tg:dedupe] saltado chat={chat_id} key={context_key} (existing #{existing.id})")
            return None

    msg = models.OutboundMessage(
        canal="telegram",
        destinatario=chat_id,
        mensaje=mensaje[:4000],
        provider=provider,
        status=models.OutboundMessageStatus.pending,
        notification_type=notification_type,
        context_key=context_key,
        obra_id=obra_id,
        user_id=user_id,
        related_action_id=related_action_id,
    )
    db.add(msg); db.commit(); db.refresh(msg)

    if not token:
        msg.status = models.OutboundMessageStatus.log_only
        msg.sent_at = datetime.utcnow()
        db.commit()
        logger.info(f"[tg:log_only] → {chat_id}: {mensaje[:80]}")
        return msg

    try:
        payload: dict = {
            "chat_id": chat_id,
            "text": mensaje[:4000],
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        url = f"{TG_API_BASE}/bot{token}/sendMessage"
        r = httpx.post(url, json=payload, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API: {data.get('description')}")
        msg.provider_message_id = str(data.get("result", {}).get("message_id", ""))
        msg.status = models.OutboundMessageStatus.sent
        msg.sent_at = datetime.utcnow()
    except Exception as e:
        msg.status = models.OutboundMessageStatus.failed
        msg.error = str(e)[:1000]
        logger.error(f"[tg] error chat={chat_id}: {e}")

    db.commit(); db.refresh(msg)
    return msg


def get_file_url(file_id: str) -> Optional[str]:
    """Para Sprint 11b (OCR de imágenes): obtiene URL temporal del archivo Telegram.

    Telegram da una URL del estilo:
        https://api.telegram.org/file/bot<TOKEN>/<file_path>
    válida por ~1 hora.
    """
    token = _bot_token()
    if not token:
        return None
    r = httpx.get(f"{TG_API_BASE}/bot{token}/getFile", params={"file_id": file_id}, timeout=10.0)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        return None
    file_path = data.get("result", {}).get("file_path")
    if not file_path:
        return None
    return f"{TG_API_BASE}/file/bot{token}/{file_path}"
