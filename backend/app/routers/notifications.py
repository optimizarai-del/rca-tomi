"""Endpoints de notificaciones (Sprint 4 · T4)."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import models, notifications
from app.database import get_db
from app.security import require_admin, get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/check")
def run_checks(
    types: Optional[List[str]] = Query(None, description="cheques, eventos, semanal, ordenes"),
    cheques_dias: int = 7,
    eventos_horas: int = 24,
    semanal_force: bool = False,
    ordenes_horas: int = 48,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    """Dispara los checks de notificaciones. Idempotente — usar como cron job."""
    return notifications.run_all(
        db,
        cheques_dias=cheques_dias,
        eventos_horas=eventos_horas,
        semanal_force=semanal_force,
        ordenes_horas=ordenes_horas,
        types=types,
    )


@router.get("/outbound")
def list_outbound(
    limit: int = 100,
    notification_type: Optional[str] = None,
    status: Optional[models.OutboundMessageStatus] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Lista los últimos N mensajes salientes. Filtrable por tipo y estado."""
    q = db.query(models.OutboundMessage)
    if notification_type:
        q = q.filter(models.OutboundMessage.notification_type == notification_type)
    if status:
        q = q.filter(models.OutboundMessage.status == status)
    rows = q.order_by(models.OutboundMessage.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": m.id,
            "destinatario": m.destinatario,
            "mensaje": m.mensaje,
            "provider": m.provider,
            "status": m.status.value,
            "notification_type": m.notification_type,
            "context_key": m.context_key,
            "obra_id": m.obra_id,
            "user_id": m.user_id,
            "provider_message_id": m.provider_message_id,
            "error": m.error,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
