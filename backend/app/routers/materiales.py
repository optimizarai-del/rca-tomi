from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/materiales", tags=["materiales"])


@router.get("/", response_model=List[schemas.MaterialOut])
def list_materiales(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.query(models.Material).all()


@router.post("/", response_model=schemas.MaterialOut, status_code=201)
def create_material(data: schemas.MaterialIn, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    m = models.Material(**data.model_dump())
    db.add(m); db.flush()
    # Sprint 9: si vino con stock inicial, lo asentamos en depósito propio
    if (data.stock or 0) > 0:
        db.add(models.StockMaterial(
            material_id=m.id,
            ubicacion_tipo=models.UbicacionStockTipo.deposito_propio,
            ubicacion_ref=None,
            cantidad=float(data.stock),
        ))
    db.commit(); db.refresh(m)
    return m


@router.post("/{mid}/movimientos", response_model=schemas.MaterialOut)
def registrar_movimiento(
    mid: int, mov: schemas.MovimientoIn,
    db: Session = Depends(get_db), user: models.User = Depends(get_current_user),
):
    m = db.query(models.Material).filter(models.Material.id == mid).first()
    if not m: raise HTTPException(404, "Material no encontrado")
    if mov.tipo not in ("ingreso", "consumo"):
        raise HTTPException(400, "tipo debe ser ingreso o consumo")
    delta = mov.cantidad if mov.tipo == "ingreso" else -mov.cantidad
    m.stock = (m.stock or 0) + delta
    db.add(models.MovimientoMaterial(
        material_id=mid, obra_id=mov.obra_id, tipo=mov.tipo,
        cantidad=mov.cantidad, nota=mov.nota, usuario_id=user.id,
    ))
    db.commit(); db.refresh(m)
    return m


@router.delete("/{mid}", status_code=204)
def delete_material(mid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    m = db.query(models.Material).filter(models.Material.id == mid).first()
    if not m: raise HTTPException(404, "Material no encontrado")
    # Sprint 9: limpiar stock multi-ubicación asociado (no hay cascade)
    db.query(models.StockMaterial).filter(models.StockMaterial.material_id == mid).delete()
    db.delete(m); db.commit()
