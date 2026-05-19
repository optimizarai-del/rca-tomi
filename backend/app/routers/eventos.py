from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, scope_demo, stamp_demo

router = APIRouter(prefix="/api/eventos", tags=["eventos"])


@router.get("/", response_model=List[schemas.EventoOut])
def list_eventos(
    obra_id: int = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db), _: models.User = Depends(get_current_user),
):
    q = db.query(models.Evento)
    if obra_id: q = q.filter(models.Evento.obra_id == obra_id)
    return q.order_by(models.Evento.fecha.desc()).limit(limit).all()


@router.post("/", response_model=schemas.EventoOut, status_code=201)
def create_evento(data: schemas.EventoIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    e = models.Evento(**data.model_dump(), usuario_id=user.id, canal=models.CanalCarga.web)
    db.add(e); db.commit(); db.refresh(e)
    return e
