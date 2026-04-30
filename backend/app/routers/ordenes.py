from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/api/ordenes", tags=["ordenes"])


@router.get("/", response_model=List[schemas.OrdenOut])
def list_ordenes(obra_id: int = None, cuadrilla_id: int = None, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    q = db.query(models.OrdenTrabajo)
    if obra_id: q = q.filter(models.OrdenTrabajo.obra_id == obra_id)
    if cuadrilla_id: q = q.filter(models.OrdenTrabajo.cuadrilla_id == cuadrilla_id)
    return q.order_by(models.OrdenTrabajo.created_at.desc()).all()


@router.post("/", response_model=schemas.OrdenOut, status_code=201)
def create_orden(data: schemas.OrdenIn, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    o = models.OrdenTrabajo(**data.model_dump(), creada_por_id=user.id, canal_creacion=models.CanalCarga.web)
    db.add(o); db.commit(); db.refresh(o)
    return o


@router.patch("/{oid}/completar", response_model=schemas.OrdenOut)
def completar_orden(oid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    o = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == oid).first()
    if not o: raise HTTPException(404, "Orden no encontrada")
    o.status = models.TaskStatus.completada
    o.completada_at = datetime.utcnow()
    # Otorgar XP al usuario y a la cuadrilla
    user.xp += o.xp_reward
    if o.cuadrilla_id:
        cuad = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == o.cuadrilla_id).first()
        if cuad:
            cuad.experiencia += o.xp_reward
            cuad.nivel = max(1, 1 + cuad.experiencia // 100)
    db.commit(); db.refresh(o)
    return o


@router.patch("/{oid}/iniciar", response_model=schemas.OrdenOut)
def iniciar_orden(oid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    o = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == oid).first()
    if not o: raise HTTPException(404, "Orden no encontrada")
    o.status = models.TaskStatus.en_progreso
    db.commit(); db.refresh(o)
    return o


@router.delete("/{oid}", status_code=204)
def delete_orden(oid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    o = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == oid).first()
    if not o: raise HTTPException(404, "Orden no encontrada")
    db.delete(o); db.commit()
