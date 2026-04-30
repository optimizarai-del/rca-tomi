"""Webhook para n8n / WhatsApp Bot - parsing simple para constructora."""
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

WEBHOOK_TOKEN = os.getenv("WHATSAPP_WEBHOOK_TOKEN", "set-shared-token-with-n8n")

# Mapeo de palabras clave a tipo de evento
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


def parsear(text: str):
    low = text.lower()
    tipo = next((v for k, v in KEYWORDS.items() if k in low), models.EventoTipo.otro)
    es_critico = any(w in low for w in ["urgente", "crítico", "critico", "accidente", "emergencia"])
    return tipo, es_critico


def detectar_obra(text: str, db: Session) -> int | None:
    low = text.lower()
    obras = db.query(models.Obra).all()
    for o in obras:
        if o.nombre.lower() in low or (o.codigo and o.codigo.lower() in low):
            return o.id
    # buscar por "obra X" o "frente Y"
    m = re.search(r"obra\s+([a-z0-9]+)", low)
    if m:
        codigo = m.group(1).upper()
        o = db.query(models.Obra).filter(models.Obra.codigo.ilike(f"%{codigo}%")).first()
        if o: return o.id
    return None


@router.post("/inbound")
def inbound(payload: schemas.WhatsAppMessageIn, db: Session = Depends(get_db)):
    if payload.token != WEBHOOK_TOKEN:
        raise HTTPException(401, "Token inválido")

    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        return {"ok": False, "reply": "📵 Número no registrado. Pedí invitación al admin."}

    tipo, es_critico = parsear(payload.text)
    obra_id = detectar_obra(payload.text, db)

    e = models.Evento(
        obra_id=obra_id,
        tipo=tipo,
        titulo=payload.text[:80],
        descripcion=payload.text,
        foto_url=payload.foto_url,
        canal=models.CanalCarga.whatsapp,
        usuario_id=user.id,
        es_critico=es_critico,
    )
    db.add(e); db.commit(); db.refresh(e)

    # Recompensa XP por reportar
    user.xp += 5
    db.commit()

    obra_txt = ""
    if obra_id:
        obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
        obra_txt = f" en {obra.icono} {obra.nombre}"

    icon = "🚨" if es_critico else "✅"
    return {
        "ok": True,
        "reply": f"{icon} Registrado: {tipo.value}{obra_txt}. +5 XP! (Total: {user.xp})",
        "evento_id": e.id,
    }
