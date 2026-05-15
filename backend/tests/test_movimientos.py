"""Movimientos: validaciones de coherencia + R1 (saldo NO se filtra por estado)."""
from datetime import date
from app import models


def _mov(obra, **overrides):
    """Factory rápido para crear un MovimientoObra."""
    base = dict(
        obra_id=obra.id,
        fecha=date.today(),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.MATERIALES,
        concepto="test",
        monto=1000,
        medio_pago=models.MedioPago.EFECTIVO,
        estado=models.EstadoMovimiento.CONFIRMADO,
        cargado_por=1,
    )
    base.update(overrides)
    return models.MovimientoObra(**base)


def test_bancarizado_se_calcula_segun_medio_pago(db, obra, admin_user):
    """El evento before_insert pone bancarizado=True para todo lo que no sea efectivo."""
    db.add(_mov(obra, cargado_por=admin_user.id, medio_pago=models.MedioPago.EFECTIVO))
    db.add(_mov(obra, cargado_por=admin_user.id, medio_pago=models.MedioPago.TRANSFERENCIA, concepto="trf"))
    db.commit()
    efectivo = db.query(models.MovimientoObra).filter_by(concepto="test").first()
    transf = db.query(models.MovimientoObra).filter_by(concepto="trf").first()
    assert efectivo.bancarizado is False
    assert transf.bancarizado is True


def test_R1_saldo_no_filtra_por_estado(db, obra, admin_user):
    """R1: SUM(INGRESO) - SUM(EGRESO), sin importar estado CONFIRMADO/A_REVISAR."""
    db.add(_mov(obra, cargado_por=admin_user.id, tipo=models.TipoMovimiento.INGRESO,
                origen_ingreso=models.OrigenIngreso.ANTICIPO_CLIENTE,
                categoria_egreso=None, monto=10000, estado=models.EstadoMovimiento.CONFIRMADO))
    db.add(_mov(obra, cargado_por=admin_user.id, monto=3000,
                estado=models.EstadoMovimiento.A_REVISAR))
    db.add(_mov(obra, cargado_por=admin_user.id, monto=2000,
                estado=models.EstadoMovimiento.CONFIRMADO))
    db.commit()

    from sqlalchemy import func
    ing = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO
    ).scalar()
    egr = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO
    ).scalar()
    assert float(ing) == 10000
    assert float(egr) == 5000  # 3000 a_revisar + 2000 confirmado, ambos cuentan


def test_tiene_comprobante_se_setea_segun_fk(db, obra, admin_user):
    m = _mov(obra, cargado_por=admin_user.id)
    m.comprobante_id = None
    db.add(m); db.commit(); db.refresh(m)
    assert m.tiene_comprobante is False
