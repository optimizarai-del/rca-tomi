"""Aportes de socios — préstamos internos con obligación de devolución."""
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/aportes", tags=["aportes_socios"])


@router.get("", response_model=List[schemas.AporteOut])
def list_aportes(
    obra_id: Optional[int] = None,
    pendientes_solo: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.AporteSocio)
    q = scope_demo(q, models.AporteSocio, user)
    if obra_id:
        q = q.filter(models.AporteSocio.obra_id == obra_id)
    if pendientes_solo:
        q = q.filter(models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL)
    return q.order_by(models.AporteSocio.fecha_aporte.desc()).all()


@router.post("", response_model=schemas.AporteOut, status_code=201)
def create_aporte(
    data: schemas.AporteIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """R2: al crear un aporte, automáticamente crea un MovimientoObra INGRESO espejo."""
    obra = db.query(models.Obra).filter(models.Obra.id == data.obra_id).first()
    if not obra:
        raise HTTPException(404, "Obra no encontrada")
    socio = db.query(models.Socio).filter(models.Socio.id == data.socio_id).first()
    if not socio:
        raise HTTPException(404, "Socio no encontrado")
    if not socio.activo:
        raise HTTPException(400, f"El socio '{socio.nombre}' está inactivo")

    aporte = models.AporteSocio(**data.model_dump())
    db.add(aporte); db.flush()  # obtener id antes del movimiento espejo

    # Movimiento espejo (R2)
    mov = models.MovimientoObra(
        obra_id=aporte.obra_id,
        etapa_id=aporte.etapa_reintegro_id,
        fecha=aporte.fecha_aporte,
        tipo=models.TipoMovimiento.INGRESO,
        origen_ingreso=models.OrigenIngreso.APORTE_SOCIO_RCA,
        concepto=f"Aporte de socio: {aporte.motivo}",
        monto=aporte.monto,
        medio_pago=aporte.medio_pago,
        aporte_socio_id=aporte.id,
        estado=models.EstadoMovimiento.CONFIRMADO,
        canal=models.CanalCarga.automatico,
        cargado_por=user.id,
    )
    db.add(mov)
    db.commit(); db.refresh(aporte)
    return aporte


@router.post("/{aid}/devolucion", response_model=schemas.AporteOut)
def registrar_devolucion(
    aid: int,
    data: schemas.AporteDevolucionIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Registra una devolución parcial o total. Crea un EGRESO espejo."""
    aporte = db.query(models.AporteSocio).filter(models.AporteSocio.id == aid).first()
    if not aporte:
        raise HTTPException(404, "Aporte no encontrado")
    if aporte.estado_devolucion == models.EstadoDevolucion.DEVUELTO_TOTAL:
        raise HTTPException(400, "El aporte ya está totalmente devuelto")
    pendiente = float(aporte.monto) - float(aporte.monto_devuelto)
    if data.monto > pendiente + 0.01:
        raise HTTPException(400, f"Monto excede el pendiente ({pendiente:.2f})")

    aporte.monto_devuelto = float(aporte.monto_devuelto) + data.monto
    aporte.fecha_devolucion = data.fecha
    if abs(float(aporte.monto_devuelto) - float(aporte.monto)) < 0.01:
        aporte.estado_devolucion = models.EstadoDevolucion.DEVUELTO_TOTAL
    else:
        aporte.estado_devolucion = models.EstadoDevolucion.DEVUELTO_PARCIAL

    # EGRESO espejo
    mov = models.MovimientoObra(
        obra_id=aporte.obra_id,
        fecha=data.fecha,
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.APORTE_PRESTAMO,
        concepto=f"Devolución aporte socio (id {aporte.id}): {data.notas or aporte.motivo}",
        monto=data.monto,
        medio_pago=data.medio_pago,
        aporte_socio_id=aporte.id,
        estado=models.EstadoMovimiento.CONFIRMADO,
        canal=models.CanalCarga.automatico,
        cargado_por=user.id,
    )
    db.add(mov)
    db.commit(); db.refresh(aporte)
    return aporte


@router.delete("/{aid}", status_code=204)
def delete_aporte(aid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    aporte = db.query(models.AporteSocio).filter(models.AporteSocio.id == aid).first()
    if not aporte:
        raise HTTPException(404, "Aporte no encontrado")
    # Borrar movimientos espejo
    db.query(models.MovimientoObra).filter(models.MovimientoObra.aporte_socio_id == aid).delete()
    db.delete(aporte); db.commit()
