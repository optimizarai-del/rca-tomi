"""Etapas de obra — divide cada obra en etapas con monto contractual."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/etapas", tags=["etapas"])


@router.get("", response_model=List[schemas.EtapaOut])
def list_etapas(
    obra_id: int = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.EtapaObra)
    if obra_id:
        q = q.filter(models.EtapaObra.obra_id == obra_id)
    return q.order_by(models.EtapaObra.obra_id, models.EtapaObra.nro_etapa).all()


@router.post("", response_model=schemas.EtapaOut, status_code=201)
def create_etapa(
    data: schemas.EtapaIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    e = models.EtapaObra(**data.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return e


@router.put("/{eid}", response_model=schemas.EtapaOut)
def update_etapa(
    eid: int,
    data: schemas.EtapaIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    e = db.query(models.EtapaObra).filter(models.EtapaObra.id == eid).first()
    if not e:
        raise HTTPException(404, "Etapa no encontrada")
    for k, v in data.model_dump().items():
        setattr(e, k, v)

    # R5: si pasa a COBRADA, alertar aportes pendientes vinculados
    if e.estado == models.EtapaEstado.COBRADA:
        pendientes = db.query(models.AporteSocio).filter(
            models.AporteSocio.etapa_reintegro_id == eid,
            models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL,
        ).count()
        # No bloqueamos, solo log: el frontend muestra la alerta vía notas
        if pendientes > 0:
            n = models.NotaObra(
                obra_id=e.obra_id,
                texto=f"⚠️ Etapa '{e.nombre}' marcada COBRADA con {pendientes} aporte(s) de socio pendiente(s) de devolución.",
                importante=True,
            )
            db.add(n)

    db.commit(); db.refresh(e)
    return e


@router.delete("/{eid}", status_code=204)
def delete_etapa(eid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    e = db.query(models.EtapaObra).filter(models.EtapaObra.id == eid).first()
    if not e:
        raise HTTPException(404, "Etapa no encontrada")
    db.delete(e); db.commit()
