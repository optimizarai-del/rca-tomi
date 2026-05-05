"""Comprobantes fiscales (facturas, NC, ND, recibos)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_finanzas

router = APIRouter(prefix="/api/comprobantes", tags=["comprobantes"])


@router.get("", response_model=List[schemas.ComprobanteOut])
def list_comprobantes(
    obra_id: Optional[int] = None,
    es_venta: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_finanzas),
):
    q = db.query(models.Comprobante)
    if obra_id:
        q = q.filter(models.Comprobante.obra_id == obra_id)
    if es_venta is not None:
        q = q.filter(models.Comprobante.es_venta == es_venta)
    return q.order_by(models.Comprobante.fecha_emision.desc()).all()


@router.post("", response_model=schemas.ComprobanteOut, status_code=201)
def create_comprobante(
    data: schemas.ComprobanteIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_finanzas),
):
    # Validación: total = neto_gravado + neto_no_gravado + iva_21 + iva_105
    suma = data.neto_gravado + data.neto_no_gravado + data.iva_21 + data.iva_105
    if abs(suma - data.total) > 0.05:
        raise HTTPException(400, f"Total ({data.total}) no coincide con suma de netos+IVA ({suma:.2f})")
    c = models.Comprobante(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return c


@router.get("/{cid}", response_model=schemas.ComprobanteOut)
def get_comprobante(cid: int, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    c = db.query(models.Comprobante).filter(models.Comprobante.id == cid).first()
    if not c:
        raise HTTPException(404, "Comprobante no encontrado")
    return c


@router.delete("/{cid}", status_code=204)
def delete_comprobante(cid: int, db: Session = Depends(get_db), _: models.User = Depends(require_finanzas)):
    c = db.query(models.Comprobante).filter(models.Comprobante.id == cid).first()
    if not c:
        raise HTTPException(404, "Comprobante no encontrado")
    # No permitir borrar si hay movimientos vinculados
    if db.query(models.MovimientoObra).filter(models.MovimientoObra.comprobante_id == cid).count() > 0:
        raise HTTPException(400, "Tiene movimientos vinculados; desvinculá primero")
    db.delete(c); db.commit()
