"""Router del agente operario IA."""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.security import get_current_user
from app.agent import orchestrator

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatIn(BaseModel):
    message: str


class PendingAction(BaseModel):
    action_id: int
    tool_name: str
    preview: dict[str, Any]


class ChatOut(BaseModel):
    reply: str
    tools_used: list[str]
    pending_actions: list[PendingAction] = []
    session_id: int | None


class ConfirmIn(BaseModel):
    confirm: bool  # true = ejecutar, false = cancelar


@router.post("/chat", response_model=ChatOut)
def chat(
    data: ChatIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return orchestrator.chat(user, data.message, db)


@router.post("/reset")
def reset(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    orchestrator.reset_session(user, db)
    return {"ok": True}


@router.post("/confirm/{action_id}")
def confirm_action(
    action_id: int,
    data: ConfirmIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Confirma o cancela una acción del agente que quedó pendiente.

    Sólo el usuario dueño de la acción puede confirmarla. La acción
    debe estar en estado 'pending'. Devuelve el resultado de ejecutar
    la tool (si confirm=true) o el ack de cancelación.
    """
    result = orchestrator.confirm_action(action_id, user, data.confirm, db)
    if "error" in result:
        raise HTTPException(result.get("code", 400), result["error"])
    return result


@router.get("/actions")
def my_actions(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Audit log de las acciones que el agente ejecutó para este usuario."""
    rows = db.query(models.AgentAction).filter(
        models.AgentAction.user_id == user.id
    ).order_by(models.AgentAction.created_at.desc()).limit(min(limit, 100)).all()
    return [
        {
            "id": a.id,
            "tool": a.tool_name,
            "status": a.status.value if a.status else None,
            "ok": a.ok,
            "error": a.error,
            "canal": a.canal.value if a.canal else None,
            "confirmed_by": a.confirmed_by,
            "confirmed_at": a.confirmed_at.isoformat() if a.confirmed_at else None,
            "fecha": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]
