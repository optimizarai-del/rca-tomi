"""Router de Clientes — entidades con régimen fiscal heredable a obras."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=List[schemas.ClienteOut])
def list_clientes(
    activos_solo: bool = True,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.Cliente)
    q = scope_demo(q, models.Cliente, user)
    if activos_solo:
        q = q.filter(models.Cliente.activo == True)  # noqa: E712
    return q.order_by(models.Cliente.nombre).all()


@router.post("", response_model=schemas.ClienteOut, status_code=201)
def create_cliente(
    data: schemas.ClienteIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    if data.regimen_fiscal_id:
        rf = db.query(models.RegimenFiscal).filter(models.RegimenFiscal.id == data.regimen_fiscal_id).first()
        if not rf:
            raise HTTPException(400, "Régimen fiscal no existe")
    c = models.Cliente(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c


@router.get("/{cid}", response_model=schemas.ClienteOut)
def get_cliente(cid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return c


@router.put("/{cid}", response_model=schemas.ClienteOut)
def update_cliente(
    cid: int,
    data: schemas.ClienteIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return c


@router.delete("/{cid}", status_code=204)
def delete_cliente(cid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    if c.obras:
        raise HTTPException(400, f"No se puede borrar: tiene {len(c.obras)} obras asociadas. Marcalo como inactivo.")
    db.delete(c); db.commit()
