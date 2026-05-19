from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


@router.get("", response_model=List[schemas.ProveedorOut])
def list_proveedores(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return scope_demo(db.query(models.Proveedor), models.Proveedor, user).all()


@router.post("", response_model=schemas.ProveedorOut, status_code=201)
def create_proveedor(data: schemas.ProveedorIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = models.Proveedor(**data.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return p


@router.put("/{pid}", response_model=schemas.ProveedorOut)
def update_proveedor(pid: int, data: schemas.ProveedorIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = db.query(models.Proveedor).filter(models.Proveedor.id == pid).first()
    if not p: raise HTTPException(404, "Proveedor no encontrado")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return p


@router.delete("/{pid}", status_code=204)
def delete_proveedor(pid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = db.query(models.Proveedor).filter(models.Proveedor.id == pid).first()
    if not p: raise HTTPException(404, "Proveedor no encontrado")
    db.delete(p); db.commit()
