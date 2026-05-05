"""Catálogo de regímenes fiscales (RI, MT, Exento, etc.)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api/regimenes-fiscales", tags=["regimenes_fiscales"])


@router.get("", response_model=List[schemas.RegimenFiscalOut])
def list_regimenes(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.query(models.RegimenFiscal).order_by(models.RegimenFiscal.codigo).all()


@router.post("", response_model=schemas.RegimenFiscalOut, status_code=201)
def create_regimen(
    data: schemas.RegimenFiscalIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    if db.query(models.RegimenFiscal).filter(models.RegimenFiscal.codigo == data.codigo).first():
        raise HTTPException(400, "Ya existe un régimen con ese código")
    r = models.RegimenFiscal(**data.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return r
