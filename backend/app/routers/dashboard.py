"""Dashboard global — calcula desde movimientos_obra (no más Gasto)."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/hud", response_model=schemas.HudGlobal)
def hud(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    obras = db.query(models.Obra).all()
    monto_contratos = sum(float(o.monto_contrato or 0) for o in obras)
    obras_activas = sum(1 for o in obras if o.estado == models.ObraStatus.EN_CURSO)

    # Saldo global desde movimientos
    ingresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO
    ).scalar() or 0
    egresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO
    ).scalar() or 0

    aportes_pend = db.query(func.coalesce(
        func.sum(models.AporteSocio.monto - models.AporteSocio.monto_devuelto), 0
    )).filter(
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL
    ).scalar() or 0

    today = date.today()
    cheques_v = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque > today,
    ).scalar() or 0

    # Operativo
    materiales = db.query(models.Material).all()
    mat_total = len(materiales)
    mat_criticos = sum(1 for m in materiales if (m.stock or 0) <= (m.stock_minimo or 0))
    cuadrillas = db.query(models.Cuadrilla).filter(models.Cuadrilla.activa == True).all()  # noqa: E712
    obreros = sum(c.cantidad_miembros for c in cuadrillas)
    productividad = sum(c.eficiencia for c in cuadrillas) / len(cuadrillas) if cuadrillas else 0
    alertas = db.query(models.Evento).filter(models.Evento.es_critico == True).count()  # noqa: E712

    return schemas.HudGlobal(
        monto_contratos_total=monto_contratos,
        total_ingresos=float(ingresos),
        total_egresos=float(egresos),
        saldo_global=float(ingresos) - float(egresos),
        aportes_pendientes=float(aportes_pend),
        cheques_a_vencer=float(cheques_v),
        obras_total=len(obras),
        obras_activas=obras_activas,
        cuadrillas_activas=len(cuadrillas),
        obreros_total=obreros,
        materiales_total=mat_total,
        materiales_criticos=mat_criticos,
        productividad=round(productividad, 1),
        alertas_total=alertas,
    )
