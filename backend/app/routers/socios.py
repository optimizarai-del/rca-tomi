"""Socios — personas/entidades con participación en RCA. (Sprint 7)

Antes se usaba `User` con rol `admin_finanzas` como proxy. Ahora tiene
tabla propia con datos fiscales, participación y vínculo opcional a User.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/socios", tags=["socios"])


@router.get("", response_model=List[schemas.SocioOut])
def list_socios(
    activos_solo: bool = True,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.Socio)
    q = scope_demo(q, models.Socio, user)
    if activos_solo:
        q = q.filter(models.Socio.activo == True)  # noqa: E712
    return q.order_by(models.Socio.nombre).all()


@router.post("", response_model=schemas.SocioOut, status_code=201)
def create_socio(
    data: schemas.SocioIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    if data.cuit:
        existente = db.query(models.Socio).filter(models.Socio.cuit == data.cuit).first()
        if existente:
            raise HTTPException(400, f"Ya existe un socio con CUIT {data.cuit}: {existente.nombre}")
    if data.user_id:
        u = db.query(models.User).filter(models.User.id == data.user_id).first()
        if not u:
            raise HTTPException(400, f"User #{data.user_id} no existe")
    s = models.Socio(**data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return s


@router.get("/{sid}", response_model=schemas.SocioOut)
def get_socio(sid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    s = db.query(models.Socio).filter(models.Socio.id == sid).first()
    if not s:
        raise HTTPException(404, "Socio no encontrado")
    return s


@router.put("/{sid}", response_model=schemas.SocioOut)
def update_socio(
    sid: int,
    data: schemas.SocioIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    s = db.query(models.Socio).filter(models.Socio.id == sid).first()
    if not s:
        raise HTTPException(404, "Socio no encontrado")
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit(); db.refresh(s)
    return s


@router.delete("/{sid}", status_code=204)
def delete_socio(sid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    s = db.query(models.Socio).filter(models.Socio.id == sid).first()
    if not s:
        raise HTTPException(404, "Socio no encontrado")
    if s.aportes:
        raise HTTPException(400, f"Socio tiene {len(s.aportes)} aporte(s). Marcalo como inactivo en lugar de borrar.")
    db.delete(s); db.commit()
