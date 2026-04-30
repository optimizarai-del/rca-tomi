"""Router del agente operario IA."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.security import get_current_user
from app.agent import orchestrator

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str
    tools_used: list[str]
    session_id: int | None


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
            "ok": a.ok,
            "error": a.error,
            "canal": a.canal.value if a.canal else None,
            "fecha": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]
