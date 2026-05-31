"""Tests Sprint 23 — Consolidación bancaria."""
from datetime import date
import pytest

from app import models


def _crear_extracto(client, headers, movimientos, banco="Galicia", cuenta="CA AR$ #1"):
    return client.post("/api/extractos", json={
        "banco": banco, "cuenta": cuenta,
        "periodo_desde": "2026-05-01", "periodo_hasta": "2026-05-31",
        "archivo_nombre": "test.csv",
        "movimientos": movimientos,
    }, headers=headers)


def test_crear_extracto_calcula_totales(client, auth_headers):
    r = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "Pago proveedor", "debito": 30000, "credito": 0},
        {"fecha": "2026-05-12", "descripcion": "Cobro cliente", "debito": 0, "credito": 100000},
    ])
    assert r.status_code == 201
    data = r.json()
    assert data["banco"] == "Galicia"
    assert data["total_debe"] == 30000
    assert data["total_haber"] == 100000
    assert data["total_movs"] == 2


def test_extracto_sin_movs_400(client, auth_headers):
    r = _crear_extracto(client, auth_headers, [])
    assert r.status_code == 400


def test_dedupe_dentro_del_extracto(client, auth_headers):
    """Dos líneas idénticas en el mismo extracto cuentan como una."""
    r = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "Pago X", "debito": 100, "credito": 0},
        {"fecha": "2026-05-10", "descripcion": "Pago X", "debito": 100, "credito": 0},
        {"fecha": "2026-05-10", "descripcion": "Pago Y", "debito": 200, "credito": 0},
    ])
    assert r.json()["total_movs"] == 2  # la 2da repetida no se persiste


def test_get_extracto_devuelve_movimientos(client, auth_headers):
    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "Pago", "debito": 50, "credito": 0},
    ]).json()["id"]
    r = client.get(f"/api/extractos/{eid}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["movimientos"]) == 1
    assert data["movimientos"][0]["descripcion"] == "Pago"


def test_sugerencias_match_por_monto_y_fecha(
    client, db, auth_headers, obra, admin_user
):
    """Sugerencias se filtran por monto exacto + EGRESO/INGRESO + ventana de días."""
    # Mov de obra: EGRESO de 30000 el 2026-05-11
    mo = models.MovimientoObra(
        obra_id=obra.id, fecha=date(2026, 5, 11),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.MATERIALES,
        concepto="Cemento Holcim", monto=30000,
        medio_pago=models.MedioPago.TRANSFERENCIA,
        cargado_por=admin_user.id,
    )
    db.add(mo); db.commit(); db.refresh(mo)

    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "TRF a HOLCIM SA", "debito": 30000, "credito": 0},
    ]).json()["id"]

    r = client.get(f"/api/extractos/{eid}/sugerencias", headers=auth_headers)
    movs = r.json()
    assert len(movs) == 1
    assert len(movs[0]["sugerencias"]) == 1
    assert movs[0]["sugerencias"][0]["movimiento_obra_id"] == mo.id
    assert movs[0]["sugerencias"][0]["distancia_dias"] == 1


def test_sugerencias_excluye_ya_matcheados(
    client, db, auth_headers, obra, admin_user
):
    mo = models.MovimientoObra(
        obra_id=obra.id, fecha=date(2026, 5, 11),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.MATERIALES,
        concepto="X", monto=500,
        medio_pago=models.MedioPago.TRANSFERENCIA,
        cargado_por=admin_user.id,
    )
    db.add(mo); db.commit(); db.refresh(mo)

    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "PRIMERO", "debito": 500, "credito": 0},
        {"fecha": "2026-05-11", "descripcion": "SEGUNDO", "debito": 500, "credito": 0},
    ]).json()["id"]

    movs_inicial = client.get(f"/api/extractos/{eid}", headers=auth_headers).json()["movimientos"]
    primero_id = next(m["id"] for m in movs_inicial if m["descripcion"] == "PRIMERO")

    # Matcheo el primero
    client.post(
        f"/api/movimientos-bancarios/{primero_id}/match",
        json={"movimiento_obra_id": mo.id},
        headers=auth_headers,
    )

    # Sugerencias: el SEGUNDO ya no debería sugerir mo (porque está matched)
    r = client.get(f"/api/extractos/{eid}/sugerencias", headers=auth_headers)
    segundo = next(m for m in r.json() if m["descripcion"] == "SEGUNDO")
    assert segundo["sugerencias"] == []


def test_match_y_resumen_consolidacion(
    client, db, auth_headers, obra, admin_user
):
    mo = models.MovimientoObra(
        obra_id=obra.id, fecha=date(2026, 5, 10),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.MATERIALES,
        concepto="x", monto=50000,
        medio_pago=models.MedioPago.TRANSFERENCIA,
        cargado_por=admin_user.id,
    )
    db.add(mo); db.commit(); db.refresh(mo)

    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "Pago", "debito": 50000, "credito": 0},
        {"fecha": "2026-05-11", "descripcion": "Otro pago no matcheado", "debito": 20000, "credito": 0},
    ]).json()["id"]

    # Resumen antes del match
    r = client.get(f"/api/extractos/{eid}/consolidacion", headers=auth_headers)
    base = r.json()
    assert base["movs_total"] == 2
    assert base["movs_conciliados"] == 0
    assert base["diferencia_debe"] == 70000

    # Matchear el primero
    movs = client.get(f"/api/extractos/{eid}", headers=auth_headers).json()["movimientos"]
    primero = next(m["id"] for m in movs if m["debito"] == 50000)
    rmatch = client.post(
        f"/api/movimientos-bancarios/{primero}/match",
        json={"movimiento_obra_id": mo.id},
        headers=auth_headers,
    )
    assert rmatch.status_code == 200
    assert rmatch.json()["movimiento_obra_id"] == mo.id
    assert rmatch.json()["conciliado_at"] is not None

    # Resumen post-match
    r2 = client.get(f"/api/extractos/{eid}/consolidacion", headers=auth_headers)
    d = r2.json()
    assert d["movs_conciliados"] == 1
    assert d["movs_sin_match"] == 1
    assert d["total_debe_obra_conciliado"] == 50000
    assert d["diferencia_debe"] == 20000


def test_match_doble_400(client, db, auth_headers, obra, admin_user):
    mo = models.MovimientoObra(
        obra_id=obra.id, fecha=date(2026, 5, 10),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.MATERIALES,
        concepto="x", monto=100,
        medio_pago=models.MedioPago.EFECTIVO,
        cargado_por=admin_user.id,
    )
    db.add(mo); db.commit(); db.refresh(mo)

    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "A", "debito": 100, "credito": 0},
        {"fecha": "2026-05-10", "descripcion": "B", "debito": 100, "credito": 0},
    ]).json()["id"]
    movs = client.get(f"/api/extractos/{eid}", headers=auth_headers).json()["movimientos"]
    a, b = movs[0]["id"], movs[1]["id"]

    client.post(f"/api/movimientos-bancarios/{a}/match",
                json={"movimiento_obra_id": mo.id}, headers=auth_headers)
    r = client.post(f"/api/movimientos-bancarios/{b}/match",
                    json={"movimiento_obra_id": mo.id}, headers=auth_headers)
    assert r.status_code == 400


def test_desvincular_match(client, db, auth_headers, obra, admin_user):
    mo = models.MovimientoObra(
        obra_id=obra.id, fecha=date(2026, 5, 10),
        tipo=models.TipoMovimiento.INGRESO,
        origen_ingreso=models.OrigenIngreso.ANTICIPO_CLIENTE,
        concepto="x", monto=200,
        medio_pago=models.MedioPago.TRANSFERENCIA,
        cargado_por=admin_user.id,
    )
    db.add(mo); db.commit(); db.refresh(mo)

    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "Z", "debito": 0, "credito": 200},
    ]).json()["id"]
    mb = client.get(f"/api/extractos/{eid}", headers=auth_headers).json()["movimientos"][0]["id"]

    client.post(f"/api/movimientos-bancarios/{mb}/match",
                json={"movimiento_obra_id": mo.id}, headers=auth_headers)
    r = client.delete(f"/api/movimientos-bancarios/{mb}/match", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["movimiento_obra_id"] is None
    assert r.json()["conciliado_at"] is None


def test_delete_extracto_cascadea_movimientos(client, db, auth_headers):
    eid = _crear_extracto(client, auth_headers, [
        {"fecha": "2026-05-10", "descripcion": "x", "debito": 1, "credito": 0},
    ]).json()["id"]
    assert db.query(models.MovimientoBancario).filter(models.MovimientoBancario.extracto_id == eid).count() == 1
    client.delete(f"/api/extractos/{eid}", headers=auth_headers)
    assert db.query(models.MovimientoBancario).filter(models.MovimientoBancario.extracto_id == eid).count() == 0


def test_extracto_inexistente_404(client, auth_headers):
    r = client.get("/api/extractos/99999", headers=auth_headers)
    assert r.status_code == 404
    r = client.get("/api/extractos/99999/sugerencias", headers=auth_headers)
    assert r.status_code == 404
    r = client.get("/api/extractos/99999/consolidacion", headers=auth_headers)
    assert r.status_code == 404


def test_solo_finanzas_puede_crear(client, headers_for, user_admin):
    """admin sin finanzas no puede crear extracto (require_finanzas)."""
    r = _crear_extracto(client, headers_for(user_admin), [
        {"fecha": "2026-05-10", "descripcion": "x", "debito": 1, "credito": 0},
    ])
    assert r.status_code == 403
