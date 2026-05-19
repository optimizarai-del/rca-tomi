"""Dashboard global — calcula desde movimientos_obra (no más Gasto)."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, scope_demo, stamp_demo

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/hud", response_model=schemas.HudGlobal)
def hud(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Sprint 12: forzamos filter is_demo en CADA query explicitamente para que
    # las agregaciones tambien respeten el scope (el listener global cubre las
    # queries simples, esta es defensa en profundidad sobre func.sum/count).
    is_demo = bool(user.is_demo)

    obras = db.query(models.Obra).filter(models.Obra.is_demo == is_demo).all()
    monto_contratos = sum(float(o.monto_contrato or 0) for o in obras)
    obras_activas = sum(1 for o in obras if o.estado == models.ObraStatus.EN_CURSO)

    ingresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.is_demo == is_demo,
        models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO,
    ).scalar() or 0
    egresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.is_demo == is_demo,
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO,
    ).scalar() or 0

    aportes_pend = db.query(func.coalesce(
        func.sum(models.AporteSocio.monto - models.AporteSocio.monto_devuelto), 0
    )).filter(
        models.AporteSocio.is_demo == is_demo,
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL,
    ).scalar() or 0

    today = date.today()
    cheques_v = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.is_demo == is_demo,
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque > today,
    ).scalar() or 0

    materiales = db.query(models.Material).filter(models.Material.is_demo == is_demo).all()
    mat_total = len(materiales)
    mat_criticos = sum(1 for m in materiales if (m.stock or 0) <= (m.stock_minimo or 0))
    cuadrillas = db.query(models.Cuadrilla).filter(
        models.Cuadrilla.is_demo == is_demo,
        models.Cuadrilla.activa == True,  # noqa: E712
    ).all()
    obreros = sum(c.cantidad_miembros for c in cuadrillas)
    productividad = sum(c.eficiencia for c in cuadrillas) / len(cuadrillas) if cuadrillas else 0
    alertas = db.query(models.Evento).filter(
        models.Evento.is_demo == is_demo,
        models.Evento.es_critico == True,  # noqa: E712
    ).count()

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
