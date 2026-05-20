"""Sprint 17 — Requerimientos por obra.

Carga rápida de imprevistos/pedidos via bot o web. Se anotan contra una obra
y quedan visibles en `/obras/:id/requerimientos` hasta que alguien los marca resueltos.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import (
    get_current_user,
    scope_demo,
    scope_obras,
    stamp_demo,
)

router = APIRouter(prefix="/api", tags=["requerimientos"])


def _filter_by_obras(db: Session, user: models.User, q):
    """Restringe los requerimientos a las obras visibles para el user (whitelist)."""
    from app.security import user_visible_obra_ids
    ids = user_visible_obra_ids(db, user)
    if ids is None:
        return q
    return q.filter(models.Requerimiento.obra_id.in_(ids))


@router.get("/obras/{oid}/requerimientos", response_model=List[schemas.RequerimientoOut])
def list_by_obra(
    oid: int,
    estado: Optional[models.RequerimientoEstado] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # Validar acceso a la obra (whitelist por usuario)
    obra_q = scope_demo(db.query(models.Obra), models.Obra, user)
    obra_q = scope_obras(obra_q, models.Obra, db, user)
    if not obra_q.filter(models.Obra.id == oid).first():
        raise HTTPException(404, "Obra no encontrada")

    q = db.query(models.Requerimiento).filter(models.Requerimiento.obra_id == oid)
    if estado is not None:
        q = q.filter(models.Requerimiento.estado == estado)
    return q.order_by(models.Requerimiento.created_at.desc()).all()


@router.get("/requerimientos", response_model=List[schemas.RequerimientoOut])
def list_all(
    estado: Optional[models.RequerimientoEstado] = None,
    obra_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.Requerimiento)
    q = _filter_by_obras(db, user, q)
    if estado is not None:
        q = q.filter(models.Requerimiento.estado == estado)
    if obra_id is not None:
        q = q.filter(models.Requerimiento.obra_id == obra_id)
    return q.order_by(models.Requerimiento.created_at.desc()).limit(200).all()


@router.post("/requerimientos", response_model=schemas.RequerimientoOut, status_code=201)
def create(
    data: schemas.RequerimientoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # Validar acceso a la obra
    obra_q = scope_demo(db.query(models.Obra), models.Obra, user)
    obra_q = scope_obras(obra_q, models.Obra, db, user)
    obra = obra_q.filter(models.Obra.id == data.obra_id).first()
    if not obra:
        raise HTTPException(404, "Obra no encontrada")

    r = models.Requerimiento(
        obra_id=data.obra_id,
        mensaje=data.mensaje.strip(),
        estado=models.RequerimientoEstado.abierto,
        canal=models.CanalCarga.web,
        created_by_id=user.id,
    )
    stamp_demo(r, user)
    db.add(r); db.commit(); db.refresh(r)
    return r


@router.patch("/requerimientos/{rid}/resolver", response_model=schemas.RequerimientoOut)
def resolver(
    rid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = _filter_by_obras(db, user, db.query(models.Requerimiento))
    r = q.filter(models.Requerimiento.id == rid).first()
    if not r:
        raise HTTPException(404, "Requerimiento no encontrado")
    if r.estado == models.RequerimientoEstado.resuelto:
        return r
    r.estado = models.RequerimientoEstado.resuelto
    r.resuelto_by_id = user.id
    r.resuelto_at = datetime.utcnow()
    db.commit(); db.refresh(r)
    return r


@router.patch("/requerimientos/{rid}/reabrir", response_model=schemas.RequerimientoOut)
def reabrir(
    rid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = _filter_by_obras(db, user, db.query(models.Requerimiento))
    r = q.filter(models.Requerimiento.id == rid).first()
    if not r:
        raise HTTPException(404, "Requerimiento no encontrado")
    r.estado = models.RequerimientoEstado.abierto
    r.resuelto_by_id = None
    r.resuelto_at = None
    db.commit(); db.refresh(r)
    return r


@router.delete("/requerimientos/{rid}", status_code=204)
def delete(
    rid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = _filter_by_obras(db, user, db.query(models.Requerimiento))
    r = q.filter(models.Requerimiento.id == rid).first()
    if not r:
        raise HTTPException(404, "Requerimiento no encontrado")
    db.delete(r); db.commit()
