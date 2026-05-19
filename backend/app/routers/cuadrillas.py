from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/cuadrillas", tags=["cuadrillas"])


@router.get("", response_model=List[schemas.CuadrillaOut])
def list_cuadrillas(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return scope_demo(db.query(models.Cuadrilla), models.Cuadrilla, user).filter(models.Cuadrilla.activa == True).all()


@router.post("", response_model=schemas.CuadrillaOut, status_code=201)
def create_cuadrilla(data: schemas.CuadrillaIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    c = models.Cuadrilla(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c


@router.put("/{cid}", response_model=schemas.CuadrillaOut)
def update_cuadrilla(cid: int, data: schemas.CuadrillaIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    c = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == cid).first()
    if not c: raise HTTPException(404, "Cuadrilla no encontrada")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return c


@router.delete("/{cid}", status_code=204)
def delete_cuadrilla(cid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    c = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == cid).first()
    if not c: raise HTTPException(404, "Cuadrilla no encontrada")
    c.activa = False
    db.commit()
