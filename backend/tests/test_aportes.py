"""R2 (movimiento espejo automático al crear aporte) y devolución parcial/total."""
from datetime import date
from app import models


def _post_aporte(client, auth_headers, obra_id, socio_id, monto=100000):
    return client.post("/api/aportes", headers=auth_headers, json={
        "obra_id": obra_id, "socio_id": socio_id,
        "fecha_aporte": date.today().isoformat(),
        "monto": monto, "motivo": "test", "medio_pago": "TRANSFERENCIA",
    })


def test_R2_crear_aporte_genera_movimiento_espejo(db, client, auth_headers, obra, admin_user):
    r = _post_aporte(client, auth_headers, obra.id, admin_user.id, monto=500000)
    assert r.status_code == 201
    aporte_id = r.json()["id"]

    movs = db.query(models.MovimientoObra).filter_by(aporte_socio_id=aporte_id).all()
    assert len(movs) == 1
    m = movs[0]
    assert m.tipo == models.TipoMovimiento.INGRESO
    assert m.origen_ingreso == models.OrigenIngreso.APORTE_SOCIO_RCA
    assert float(m.monto) == 500000


def test_devolucion_parcial_marca_estado_y_crea_egreso_espejo(db, client, auth_headers, obra, admin_user):
    r = _post_aporte(client, auth_headers, obra.id, admin_user.id, monto=200000)
    aporte_id = r.json()["id"]

    r2 = client.post(f"/api/aportes/{aporte_id}/devolucion", headers=auth_headers, json={
        "monto": 80000, "fecha": date.today().isoformat(), "medio_pago": "EFECTIVO",
    })
    assert r2.status_code == 200
    ap = db.query(models.AporteSocio).filter_by(id=aporte_id).first()
    db.refresh(ap)
    assert ap.estado_devolucion == models.EstadoDevolucion.DEVUELTO_PARCIAL
    assert float(ap.monto_devuelto) == 80000

    egresos = db.query(models.MovimientoObra).filter_by(
        aporte_socio_id=aporte_id, tipo=models.TipoMovimiento.EGRESO
    ).all()
    assert len(egresos) == 1
    assert egresos[0].categoria_egreso == models.CategoriaEgreso.APORTE_PRESTAMO


def test_devolucion_total_marca_estado_total(db, client, auth_headers, obra, admin_user):
    r = _post_aporte(client, auth_headers, obra.id, admin_user.id, monto=100000)
    aporte_id = r.json()["id"]

    r2 = client.post(f"/api/aportes/{aporte_id}/devolucion", headers=auth_headers, json={
        "monto": 100000, "fecha": date.today().isoformat(), "medio_pago": "EFECTIVO",
    })
    assert r2.status_code == 200
    ap = db.query(models.AporteSocio).filter_by(id=aporte_id).first()
    db.refresh(ap)
    assert ap.estado_devolucion == models.EstadoDevolucion.DEVUELTO_TOTAL


def test_devolucion_excede_pendiente_rechaza(client, auth_headers, obra, admin_user):
    r = _post_aporte(client, auth_headers, obra.id, admin_user.id, monto=50000)
    aporte_id = r.json()["id"]
    r2 = client.post(f"/api/aportes/{aporte_id}/devolucion", headers=auth_headers, json={
        "monto": 999999, "fecha": date.today().isoformat(), "medio_pago": "EFECTIVO",
    })
    assert r2.status_code == 400
    assert "excede" in r2.json()["detail"].lower()
