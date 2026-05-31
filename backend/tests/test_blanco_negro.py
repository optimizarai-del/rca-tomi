"""Tests Sprint 21 — contabilidad blanco/negro por obra."""
from datetime import date
import pytest

from app import models


def _crear_mov(client, headers, obra_id, *, tipo, monto, legalidad="blanco",
               cobro_pago_estado="pendiente", iva_pct=None, iibb_pct=None,
               gastos_banco=0, medio_pago="EFECTIVO"):
    payload = {
        "obra_id": obra_id,
        "fecha": "2026-05-20",
        "tipo": tipo,
        "concepto": f"test {tipo} {legalidad}",
        "monto": monto,
        "medio_pago": medio_pago,
        "legalidad": legalidad,
        "cobro_pago_estado": cobro_pago_estado,
        "gastos_banco": gastos_banco,
    }
    if tipo == "INGRESO":
        payload["origen_ingreso"] = "ANTICIPO_CLIENTE"
    else:
        payload["categoria_egreso"] = "MATERIALES"
    if iva_pct is not None:
        payload["iva_pct"] = iva_pct
    if iibb_pct is not None:
        payload["iibb_pct"] = iibb_pct
    return client.post("/api/movimientos", json=payload, headers=headers)


def test_crear_movimiento_default_blanco_pendiente(client, auth_headers, obra):
    r = _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=100000)
    assert r.status_code == 201
    data = r.json()
    assert data["legalidad"] == "blanco"
    assert data["cobro_pago_estado"] == "pendiente"
    assert data["gastos_banco"] == 0


def test_crear_movimiento_negro(client, auth_headers, obra):
    r = _crear_mov(client, auth_headers, obra.id, tipo="EGRESO", monto=50000, legalidad="negro")
    assert r.status_code == 201
    assert r.json()["legalidad"] == "negro"


def test_filtro_por_legalidad(client, auth_headers, obra):
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=100, legalidad="blanco")
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=200, legalidad="negro")
    _crear_mov(client, auth_headers, obra.id, tipo="EGRESO", monto=50, legalidad="blanco")

    r = client.get("/api/movimientos?legalidad=blanco", headers=auth_headers)
    items = r.json()
    legalidades = {m["legalidad"] for m in items}
    assert legalidades == {"blanco"}
    assert len(items) == 2


def test_filtro_por_cobro_pago_estado(client, auth_headers, obra):
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=100, cobro_pago_estado="pendiente")
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=200, cobro_pago_estado="cobrado")

    r = client.get("/api/movimientos?cobro_pago_estado=cobrado", headers=auth_headers)
    items = r.json()
    assert len(items) == 1
    assert items[0]["monto"] == 200


def test_resumen_finanzas_obra_calcula_neto_y_compromiso(client, auth_headers, obra):
    # Caja blanco: ingreso cobrado 100k, ingreso pendiente 50k, egreso pagado 30k
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=100000, cobro_pago_estado="cobrado")
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=50000, cobro_pago_estado="pendiente")
    _crear_mov(client, auth_headers, obra.id, tipo="EGRESO", monto=30000, cobro_pago_estado="pagado")
    # Caja negro: ingreso cobrado 20k
    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=20000, legalidad="negro", cobro_pago_estado="cobrado")

    r = client.get(f"/api/movimientos/obra/{obra.id}/resumen-finanzas", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()

    # Blanco
    assert data["blanco"]["ingresos_cobrado"] == 100000
    assert data["blanco"]["ingresos_pendiente"] == 50000
    assert data["blanco"]["egresos_pagado"] == 30000
    assert data["blanco"]["egresos_pendiente"] == 0
    assert data["blanco"]["neto_efectivo"] == 70000  # 100k - 30k
    assert data["blanco"]["saldo_compromiso"] == 50000  # 50k pendiente

    # Negro
    assert data["negro"]["ingresos_cobrado"] == 20000
    assert data["negro"]["neto_efectivo"] == 20000

    # Consolidados
    assert data["lo_que_tenes"] == 90000  # 70k blanco + 20k negro
    assert data["lo_que_se_debe"] == 50000  # solo blanco tiene compromiso


def test_resumen_finanzas_impuestos(client, auth_headers, obra):
    # 100k con IVA 21% y IIBB 3% y 500 de gastos_banco
    _crear_mov(
        client, auth_headers, obra.id, tipo="INGRESO", monto=100000,
        cobro_pago_estado="cobrado", iva_pct=0.21, iibb_pct=0.03, gastos_banco=500,
    )
    r = client.get(f"/api/movimientos/obra/{obra.id}/resumen-finanzas", headers=auth_headers)
    blanco = r.json()["blanco"]
    assert blanco["iva_total"] == 21000  # 100000 * 0.21
    assert blanco["iibb_total"] == 3000   # 100000 * 0.03
    assert blanco["gastos_banco_total"] == 500


def test_resumen_obra_inexistente_404(client, auth_headers):
    r = client.get("/api/movimientos/obra/99999/resumen-finanzas", headers=auth_headers)
    assert r.status_code == 404


def test_patch_finanzas_marcar_cobrado(client, auth_headers, obra):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=1000).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "cobrado"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["cobro_pago_estado"] == "cobrado"
    assert data["fecha_cobro_pago"] is not None  # default to hoy


def test_patch_finanzas_marcar_pagado(client, auth_headers, obra):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="EGRESO", monto=500).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "pagado", "fecha_cobro_pago": "2026-05-22"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["cobro_pago_estado"] == "pagado"
    assert r.json()["fecha_cobro_pago"] == "2026-05-22"


def test_patch_finanzas_volver_a_pendiente_borra_fecha(client, auth_headers, obra):
    mid = _crear_mov(
        client, auth_headers, obra.id, tipo="INGRESO", monto=1000,
        cobro_pago_estado="cobrado",
    ).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "pendiente"},
        headers=auth_headers,
    )
    assert r.json()["fecha_cobro_pago"] is None


def test_patch_finanzas_ingreso_no_acepta_pagado(client, auth_headers, obra):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=1000).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "pagado"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_patch_finanzas_egreso_no_acepta_cobrado(client, auth_headers, obra):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="EGRESO", monto=1000).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "cobrado"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_patch_finanzas_cambiar_legalidad(client, auth_headers, obra):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=1000).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"legalidad": "negro"},
        headers=auth_headers,
    )
    assert r.json()["legalidad"] == "negro"


def test_patch_finanzas_inexistente_404(client, auth_headers):
    r = client.patch(
        "/api/movimientos/99999/finanzas",
        json={"cobro_pago_estado": "cobrado"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_patch_finanzas_solo_admin(client, headers_for, user_supervisor, obra, auth_headers):
    mid = _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=1000).json()["id"]
    r = client.patch(
        f"/api/movimientos/{mid}/finanzas",
        json={"cobro_pago_estado": "cobrado"},
        headers=headers_for(user_supervisor),
    )
    assert r.status_code == 403


def test_resumen_solo_movs_de_esa_obra(
    client, db, auth_headers, obra, cliente, regimen_ri
):
    """Resumen no debe incluir movimientos de otra obra."""
    from datetime import date as dt

    obra2 = models.Obra(
        codigo="OTRA", nombre="Otra obra",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=10,
        fecha_inicio=dt.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra2); db.commit(); db.refresh(obra2)

    _crear_mov(client, auth_headers, obra.id, tipo="INGRESO", monto=100, cobro_pago_estado="cobrado")
    _crear_mov(client, auth_headers, obra2.id, tipo="INGRESO", monto=99999, cobro_pago_estado="cobrado")

    r = client.get(f"/api/movimientos/obra/{obra.id}/resumen-finanzas", headers=auth_headers)
    assert r.json()["blanco"]["ingresos_cobrado"] == 100
