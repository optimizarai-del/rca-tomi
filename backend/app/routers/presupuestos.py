"""Sprint 10 — Endpoints de presupuestos de materiales por obra.

La premisa es que TODA la carga va por bot. Estos endpoints existen para:
- listar/consultar presupuestos desde la web
- aprobar un presupuesto (acción web mínima del admin)
- crear un presupuesto en modo de respaldo (no para uso operativo normal)
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin
from app.presupuestos_svc import (
    crear_presupuesto, agregar_item, aprobar_presupuesto, serialize,
)

router = APIRouter(prefix="/api/presupuestos", tags=["presupuestos"])


@router.get("/", response_model=List[schemas.PresupuestoOut])
def listar(
    obra_id: Optional[int] = None, estado: Optional[str] = None,
    db: Session = Depends(get_db), _: models.User = Depends(get_current_user),
):
    q = db.query(models.Presupuesto)
    if obra_id is not None:
        q = q.filter(models.Presupuesto.obra_id == obra_id)
    if estado:
        q = q.filter(models.Presupuesto.estado == estado)
    return [serialize(p, db) for p in q.order_by(models.Presupuesto.created_at.desc()).all()]


@router.get("/{pid}", response_model=schemas.PresupuestoOut)
def detalle(pid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    p = db.query(models.Presupuesto).filter(models.Presupuesto.id == pid).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    return serialize(p, db)


@router.post("/", response_model=schemas.PresupuestoOut, status_code=201)
def endpoint_crear(
    payload: schemas.PresupuestoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    try:
        p = crear_presupuesto(db, obra_id=payload.obra_id, nombre=payload.nombre,
                              items=[i.model_dump() for i in payload.items],
                              notas=payload.notas, created_by_id=user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return serialize(p, db)


@router.post("/{pid}/items", response_model=schemas.PresupuestoOut)
def endpoint_agregar_item(
    pid: int, item: schemas.PresupuestoItemIn,
    db: Session = Depends(get_db), _: models.User = Depends(require_admin),
):
    try:
        p = agregar_item(db, presupuesto_id=pid, material_id=item.material_id,
                        cantidad=item.cantidad,
                        precio_unitario_estimado=item.precio_unitario_estimado)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return serialize(p, db)


@router.post("/{pid}/aprobar", response_model=schemas.PresupuestoOut)
def endpoint_aprobar(pid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    try:
        p = aprobar_presupuesto(db, presupuesto_id=pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return serialize(p, db)


@router.delete("/{pid}", status_code=204)
def endpoint_borrar(pid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    p = db.query(models.Presupuesto).filter(models.Presupuesto.id == pid).first()
    if not p:
        raise HTTPException(404, "Presupuesto no encontrado")
    if p.estado == models.EstadoPresupuesto.aprobado:
        raise HTTPException(400, "No se puede borrar un presupuesto aprobado. Marcalo cerrado primero.")
    db.delete(p); db.commit()
