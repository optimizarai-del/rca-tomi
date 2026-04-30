from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import require_finanzas

router = APIRouter(prefix="/api/gastos", tags=["gastos"])


@router.get("/", response_model=List[schemas.GastoOut])
def list_gastos(obra_id: int = None, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    q = db.query(models.Gasto)
    if obra_id: q = q.filter(models.Gasto.obra_id == obra_id)
    return q.order_by(models.Gasto.fecha.desc()).all()


@router.post("/", response_model=schemas.GastoOut, status_code=201)
def create_gasto(data: schemas.GastoIn, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    g = models.Gasto(**data.model_dump(exclude_none=True))
    db.add(g); db.commit(); db.refresh(g)
    # Actualizar presupuesto consumido de la obra
    if g.obra_id:
        obra = db.query(models.Obra).filter(models.Obra.id == g.obra_id).first()
        if obra:
            obra.presupuesto_consumido = (obra.presupuesto_consumido or 0) + g.monto
            db.commit()
    return g


@router.delete("/{gid}", status_code=204)
def delete_gasto(gid: int, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    g = db.query(models.Gasto).filter(models.Gasto.id == gid).first()
    if not g: raise HTTPException(404, "Gasto no encontrado")
    db.delete(g); db.commit()


@router.get("/resumen")
def resumen(obra_id: int = None, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    q = db.query(models.Gasto.categoria, func.sum(models.Gasto.monto))
    if obra_id: q = q.filter(models.Gasto.obra_id == obra_id)
    rows = q.group_by(models.Gasto.categoria).all()
    return [{"categoria": c, "total": t or 0} for c, t in rows]
