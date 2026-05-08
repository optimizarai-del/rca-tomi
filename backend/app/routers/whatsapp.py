"""Webhook inbound de WhatsApp (Sprint 4 — bidireccional).

Pipeline:
  1. Validar token compartido (`WHATSAPP_WEBHOOK_TOKEN`).
  2. Identificar usuario por `phone`.
  3. Si el texto empieza con `/`, parsear como slash command (no requiere LLM).
  4. Si no, fallback al parser keyword viejo (crea Evento).
  5. (Futuro: si hay saldo Anthropic, intentar primero con orchestrator del agente IA.)
  6. Enviar la respuesta al user con el adapter (`send_whatsapp`).
     Por default `WHATSAPP_PROVIDER=log_only` solo registra en la DB.

Devuelve 200 con `{ok, reply, ...}` para que el provider externo (n8n, Twilio webhook
forwarder, etc) pueda log/debugear.
"""
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.slash_commands import is_slash_command, handle_slash
from app.whatsapp_sender import send_whatsapp

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

WEBHOOK_TOKEN = os.getenv("WHATSAPP_WEBHOOK_TOKEN", "set-shared-token-with-n8n")

# Mapeo de palabras clave a tipo de evento (parser fallback)
KEYWORDS = {
    "llegó": models.EventoTipo.material_llegada,
    "llego": models.EventoTipo.material_llegada,
    "recibido": models.EventoTipo.material_llegada,
    "avance": models.EventoTipo.avance,
    "terminé": models.EventoTipo.avance,
    "termine": models.EventoTipo.avance,
    "terminado": models.EventoTipo.avance,
    "incidente": models.EventoTipo.incidente,
    "accidente": models.EventoTipo.incidente,
    "problema": models.EventoTipo.incidente,
    "inspección": models.EventoTipo.inspeccion,
    "inspeccion": models.EventoTipo.inspeccion,
    "foto": models.EventoTipo.foto,
    "hito": models.EventoTipo.hito,
}


def _parsear_keyword(text: str):
    low = text.lower()
    tipo = next((v for k, v in KEYWORDS.items() if k in low), models.EventoTipo.otro)
    es_critico = any(w in low for w in ["urgente", "crítico", "critico", "accidente", "emergencia"])
    return tipo, es_critico


def _detectar_obra(text: str, db: Session) -> int | None:
    low = text.lower()
    for o in db.query(models.Obra).all():
        if o.nombre.lower() in low or (o.codigo and o.codigo.lower() in low):
            return o.id
    m = re.search(r"obra\s+([a-z0-9]+)", low)
    if m:
        codigo = m.group(1).upper()
        o = db.query(models.Obra).filter(models.Obra.codigo.ilike(f"%{codigo}%")).first()
        if o:
            return o.id
    return None


@router.post("/inbound")
def inbound(payload: schemas.WhatsAppMessageIn, db: Session = Depends(get_db)):
    if payload.token != WEBHOOK_TOKEN:
        raise HTTPException(401, "Token inválido")

    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        # Aunque el user no existe, devolvemos 200 (no exponemos info)
        return {"ok": False, "reply": "📵 Número no registrado. Pedí invitación al admin."}

    text = (payload.text or "").strip()

    # ─── 1. Slash commands ─────────────────────────────────────
    if is_slash_command(text):
        result = handle_slash(text, user, db)
        reply = result.get("reply", "(sin respuesta)")
        # Enviar respuesta al user (adapter decide si log_only o real)
        send_whatsapp(
            db, payload.phone, reply,
            notification_type="slash_response",
            user_id=user.id,
            obra_id=result.get("obra_id"),
        )
        return {**result, "mode": "slash"}

    # ─── 2. Parser fallback (keyword-based del Sprint 0) ──────
    # En el futuro, cuando haya saldo Anthropic, este branch lo reemplaza el orchestrator.
    tipo, es_critico = _parsear_keyword(text)
    obra_id = _detectar_obra(text, db)
    e = models.Evento(
        obra_id=obra_id,
        tipo=tipo,
        titulo=text[:80],
        descripcion=text,
        foto_url=payload.foto_url,
        canal=models.CanalCarga.whatsapp,
        usuario_id=user.id,
        es_critico=es_critico,
    )
    db.add(e)
    user.xp = (user.xp or 0) + 5
    db.commit()
    db.refresh(e)

    obra_txt = ""
    if obra_id:
        obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
        obra_txt = f" en {obra.icono} {obra.nombre}"

    icon = "🚨" if es_critico else "✅"
    reply = f"{icon} Registrado: {tipo.value}{obra_txt}. +5 XP! (Total: {user.xp})"

    send_whatsapp(
        db, payload.phone, reply,
        notification_type="event_logged",
        user_id=user.id,
        obra_id=obra_id,
    )

    return {
        "ok": True,
        "reply": reply,
        "evento_id": e.id,
        "mode": "keyword",
        "tipo": tipo.value,
        "es_critico": es_critico,
    }
