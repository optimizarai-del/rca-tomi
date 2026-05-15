"""Adaptador para enviar mensajes salientes por WhatsApp.

3 providers configurables vía env `WHATSAPP_PROVIDER`:
    - log_only  → registra en `outbound_messages` con status=log_only, NO envía. Default.
    - twilio    → llama a Twilio WhatsApp API.
    - cloud_api → llama a Meta WhatsApp Cloud API.

Uso:
    from app.whatsapp_sender import send_whatsapp
    send_whatsapp(db, "+5491100000001", "Hola desde RCA.", notification_type="manual", user_id=admin.id)

Devuelve el `OutboundMessage` persistido. El llamador puede inspeccionar `.status`,
`.error`, `.provider_message_id` para reaccionar.
"""
from __future__ import annotations
import os
import re
import logging
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


def _provider() -> str:
    return (os.getenv("WHATSAPP_PROVIDER") or "log_only").strip().lower()


def normalize_phone(phone: str) -> str:
    """Saca prefijo 'whatsapp:', espacios, guiones. Devuelve tipo +5491100000001."""
    if not phone:
        return ""
    p = phone.strip()
    if p.lower().startswith("whatsapp:"):
        p = p[9:]
    p = re.sub(r"[\s\-()]", "", p)
    if not p.startswith("+"):
        # asumimos +54 si vino sin prefijo y arranca con 9 o 1
        p = "+" + p
    return p


def send_whatsapp(
    db: Session,
    destinatario: str,
    mensaje: str,
    *,
    foto_url: Optional[str] = None,
    notification_type: str = "manual",
    obra_id: Optional[int] = None,
    user_id: Optional[int] = None,
    related_action_id: Optional[int] = None,
    context_key: Optional[str] = None,
    dedupe: bool = False,
) -> Optional[models.OutboundMessage]:
    """Envía un mensaje de WhatsApp y persiste el registro.

    Crea SIEMPRE un `OutboundMessage`. Si el provider es log_only, queda con
    status=log_only y no se intenta enviar. Si falla el envío real, queda
    status=failed con el error guardado.

    Si `dedupe=True` y `context_key` está definido, NO se envía si ya hay otro
    mensaje con el mismo (destinatario, context_key) en cualquier estado válido.
    Devuelve None en ese caso.
    """
    provider = _provider()
    destinatario = normalize_phone(destinatario)

    if dedupe and context_key:
        existing = db.query(models.OutboundMessage).filter(
            models.OutboundMessage.destinatario == destinatario,
            models.OutboundMessage.context_key == context_key,
            models.OutboundMessage.status.in_([
                models.OutboundMessageStatus.log_only,
                models.OutboundMessageStatus.sent,
                models.OutboundMessageStatus.pending,
            ]),
        ).first()
        if existing:
            logger.info(f"[wsp:dedupe] saltado {destinatario} key={context_key} (existing #{existing.id})")
            return None

    msg = models.OutboundMessage(
        canal="whatsapp",
        destinatario=destinatario,
        mensaje=mensaje[:4000],
        foto_url=foto_url,
        provider=provider,
        status=models.OutboundMessageStatus.pending,
        notification_type=notification_type,
        context_key=context_key,
        obra_id=obra_id,
        user_id=user_id,
        related_action_id=related_action_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    if provider == "log_only":
        msg.status = models.OutboundMessageStatus.log_only
        msg.sent_at = datetime.utcnow()
        db.commit()
        logger.info(f"[wsp:log_only] → {destinatario}: {mensaje[:80]}")
        return msg

    try:
        if provider == "twilio":
            sid = _send_twilio(destinatario, mensaje, foto_url)
            msg.provider_message_id = sid
            msg.status = models.OutboundMessageStatus.sent
            msg.sent_at = datetime.utcnow()
        elif provider == "cloud_api":
            api_id = _send_cloud_api(destinatario, mensaje, foto_url)
            msg.provider_message_id = api_id
            msg.status = models.OutboundMessageStatus.sent
            msg.sent_at = datetime.utcnow()
        else:
            msg.status = models.OutboundMessageStatus.failed
            msg.error = f"provider desconocido: {provider}"
    except Exception as e:
        msg.status = models.OutboundMessageStatus.failed
        msg.error = str(e)[:1000]
        logger.error(f"[wsp:{provider}] error enviando a {destinatario}: {e}")

    db.commit()
    db.refresh(msg)
    return msg


def _send_twilio(destinatario: str, mensaje: str, foto_url: Optional[str]) -> str:
    """POST a Twilio Messages API. Devuelve el SID del mensaje."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_FROM")  # ej "whatsapp:+14155238886"
    if not (sid and token and from_):
        raise RuntimeError("Faltan TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM en .env")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = {
        "From": from_,
        "To": f"whatsapp:{destinatario}",
        "Body": mensaje,
    }
    if foto_url:
        data["MediaUrl"] = foto_url

    r = httpx.post(url, data=data, auth=(sid, token), timeout=15.0)
    r.raise_for_status()
    return r.json().get("sid", "")


def _send_cloud_api(destinatario: str, mensaje: str, foto_url: Optional[str]) -> str:
    """POST a Meta WhatsApp Cloud API. Devuelve el message id."""
    phone_id = os.getenv("CLOUD_API_PHONE_ID")
    token = os.getenv("CLOUD_API_TOKEN")
    if not (phone_id and token):
        raise RuntimeError("Faltan CLOUD_API_PHONE_ID / CLOUD_API_TOKEN en .env")

    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if foto_url:
        payload = {
            "messaging_product": "whatsapp",
            "to": destinatario.lstrip("+"),
            "type": "image",
            "image": {"link": foto_url, "caption": mensaje},
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": destinatario.lstrip("+"),
            "type": "text",
            "text": {"body": mensaje},
        }

    r = httpx.post(url, json=payload, headers=headers, timeout=15.0)
    r.raise_for_status()
    msgs = r.json().get("messages", [])
    return msgs[0]["id"] if msgs else ""
