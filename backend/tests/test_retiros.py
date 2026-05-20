"""Tests Sprint 14 — pedidos / retiros con foto, forma de pago, blanco/negro y alertas."""
from datetime import date, timedelta
import pytest

from app import models
from app.stock import (
    cargar_compra_pendiente,
    agendar_retiro,
    marcar_retirado,
    pendientes_retiro_proximos,
    listar_retiros,
)
from app.notificaciones import notificar_retiros_pendientes
from app.slash_commands import handle_slash


@pytest.fixture
def material(db):
    m = models.Material(nombre="Cemento", categoria="cemento", unidad="bolsa",
                        stock=0, stock_minimo=10, precio_unitario=8000)
    db.add(m); db.commit(); db.refresh(m)
    return m


@pytest.fixture
def proveedor(db):
    p = models.Proveedor(nombre="Holcim", cuit="30-12345678-9", rubro="cemento")
    db.add(p); db.commit(); db.refresh(p)
    return p


@pytest.fixture
def stock_pendiente(db, material, proveedor):
    """100 bolsas de cemento compradas, pendientes en Holcim."""
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=100)
    fila = db.query(models.StockMaterial).filter(
        models.StockMaterial.material_id == material.id,
        models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
    ).first()
    return fila


def test_agendar_retiro_setea_fecha(db, stock_pendiente):
    fila = agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date(2026, 6, 1))
    assert fila.fecha_retirar == date(2026, 6, 1)
    assert fila.retiro_alertado_at is None


def test_agendar_retiro_resetea_alertado(db, stock_pendiente):
    from datetime import datetime
    stock_pendiente.retiro_alertado_at = datetime.utcnow()
    db.commit()
    fila = agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date(2026, 6, 2))
    assert fila.retiro_alertado_at is None  # se rearma para que vuelva a alertar


def test_agendar_solo_acepta_pendientes(db, material):
    # crear stock en deposito_propio directamente
    fila = models.StockMaterial(
        material_id=material.id,
        ubicacion_tipo=models.UbicacionStockTipo.deposito_propio,
        cantidad=10,
    )
    db.add(fila); db.commit(); db.refresh(fila)
    with pytest.raises(ValueError, match="comprado_no_retirado"):
        agendar_retiro(db, stock_material_id=fila.id, fecha_retirar=date.today())


def test_marcar_retirado_completo_a_deposito(db, stock_pendiente, admin_user):
    retiro = marcar_retirado(
        db,
        stock_material_id=stock_pendiente.id,
        cantidad=100,
        fecha_retiro=date(2026, 6, 1),
        forma_pago=models.MedioPago.TRANSFERENCIA,
        en_negro=False,
        usuario_id=admin_user.id,
    )
    assert retiro.id is not None
    assert retiro.cantidad == 100
    assert retiro.forma_pago == models.MedioPago.TRANSFERENCIA
    assert retiro.en_negro is False
    assert retiro.obra_destino_id is None

    # comprado_no_retirado quedó en 0, fecha y alerta limpiadas
    db.refresh(stock_pendiente)
    assert stock_pendiente.cantidad == 0
    assert stock_pendiente.fecha_retirar is None
    assert stock_pendiente.retiro_alertado_at is None

    # depósito propio recibió las 100
    dep = db.query(models.StockMaterial).filter(
        models.StockMaterial.material_id == stock_pendiente.material_id,
        models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.deposito_propio,
    ).first()
    assert dep is not None and dep.cantidad == 100


def test_marcar_retirado_parcial_directo_a_obra(db, stock_pendiente, obra, admin_user):
    retiro = marcar_retirado(
        db,
        stock_material_id=stock_pendiente.id,
        cantidad=40,
        forma_pago=models.MedioPago.EFECTIVO,
        en_negro=True,
        destino_tipo="en_obra",
        destino_obra_id=obra.id,
        notas="cheque del banco galicia",
        usuario_id=admin_user.id,
    )
    assert retiro.cantidad == 40
    assert retiro.obra_destino_id == obra.id
    assert retiro.en_negro is True

    db.refresh(stock_pendiente)
    assert stock_pendiente.cantidad == 60  # quedaron 60 pendientes


def test_marcar_retirado_cantidad_mayor_que_disponible(db, stock_pendiente, admin_user):
    with pytest.raises(ValueError, match="No hay suficiente"):
        marcar_retirado(
            db, stock_material_id=stock_pendiente.id, cantidad=999, usuario_id=admin_user.id
        )


def test_marcar_retirado_en_obra_requiere_obra_id(db, stock_pendiente, admin_user):
    with pytest.raises(ValueError):
        marcar_retirado(
            db, stock_material_id=stock_pendiente.id, cantidad=10,
            destino_tipo="en_obra", destino_obra_id=None, usuario_id=admin_user.id,
        )


def test_pendientes_retiro_filtra_por_fecha(db, stock_pendiente):
    # sin fecha → no entra (default incluir_sin_fecha=False)
    out = pendientes_retiro_proximos(db, dias=7)
    assert out == []

    # con fecha mañana
    agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date.today() + timedelta(days=1))
    out = pendientes_retiro_proximos(db, dias=7)
    assert len(out) == 1
    assert out[0].id == stock_pendiente.id

    # fuera de horizonte
    agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date.today() + timedelta(days=30))
    assert pendientes_retiro_proximos(db, dias=7) == []
    assert len(pendientes_retiro_proximos(db, dias=60)) == 1


def test_pendientes_con_sin_fecha(db, stock_pendiente):
    out = pendientes_retiro_proximos(db, dias=7, incluir_sin_fecha=True)
    assert len(out) == 1


def test_notificar_retiros_pendientes_log_only(db, stock_pendiente, admin_user):
    """Sin TELEGRAM_BOT_TOKEN, OutboundMessage queda en log_only — pero la fila
    se marca como alertada igual."""
    agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date.today() + timedelta(days=1))
    admin_user.telegram_chat_id = "1234567890"
    db.commit()

    resumen = notificar_retiros_pendientes(db, dias_antes=1)
    assert resumen["filas_notificadas"] == 1
    assert resumen["destinatarios"] >= 1

    db.refresh(stock_pendiente)
    assert stock_pendiente.retiro_alertado_at is not None

    msg = db.query(models.OutboundMessage).filter(
        models.OutboundMessage.notification_type == "retiro_pendiente"
    ).first()
    assert msg is not None
    assert "Cemento" in msg.mensaje
    assert "Holcim" in msg.mensaje


def test_notificar_es_idempotente(db, stock_pendiente, admin_user):
    """Llamar dos veces no genera doble alerta."""
    agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date.today() + timedelta(days=1))
    admin_user.telegram_chat_id = "1234567890"
    db.commit()

    r1 = notificar_retiros_pendientes(db, dias_antes=1)
    r2 = notificar_retiros_pendientes(db, dias_antes=1)
    assert r1["filas_notificadas"] == 1
    assert r2["filas_notificadas"] == 0  # ya estaba alertado


def test_endpoint_pendientes_lista(client, db, auth_headers, material, proveedor):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=50)
    r = client.get("/api/stock/pendientes?dias=30&incluir_sin_fecha=true", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["material_nombre"] == "Cemento"
    assert data[0]["proveedor_nombre"] == "Holcim"
    assert data[0]["cantidad"] == 50.0


def test_endpoint_agendar_retiro(client, db, auth_headers, stock_pendiente):
    r = client.patch(
        f"/api/stock/{stock_pendiente.id}/agendar-retiro",
        json={"fecha_retirar": "2026-06-15"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["fecha_retirar"] == "2026-06-15"


def test_endpoint_marcar_retirado(client, db, auth_headers, stock_pendiente, obra):
    r = client.post(
        f"/api/stock/{stock_pendiente.id}/retirar",
        json={
            "cantidad": 30,
            "fecha_retiro": "2026-05-22",
            "forma_pago": "CHEQUE_PROPIO",
            "en_negro": False,
            "destino_tipo": "en_obra",
            "destino_obra_id": obra.id,
            "notas": "cheque #4521",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["cantidad"] == 30
    assert data["forma_pago"] == "CHEQUE_PROPIO"
    assert data["en_negro"] is False
    assert data["obra_destino_id"] == obra.id


def test_endpoint_historico_retiros(client, db, auth_headers, stock_pendiente, admin_user):
    marcar_retirado(db, stock_material_id=stock_pendiente.id, cantidad=20, usuario_id=admin_user.id)
    marcar_retirado(db, stock_material_id=stock_pendiente.id, cantidad=10, usuario_id=admin_user.id)
    r = client.get("/api/stock/retiros", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2


def test_slash_pendientes(db, admin_user, stock_pendiente):
    agendar_retiro(db, stock_material_id=stock_pendiente.id, fecha_retirar=date.today() + timedelta(days=2))
    res = handle_slash("/pendientes 7", admin_user, db)
    assert res["ok"] is True
    assert "Pendientes de retiro" in res["reply"]
    assert "Cemento" in res["reply"]


def test_slash_pendientes_sin_nada(db, admin_user):
    res = handle_slash("/pendientes", admin_user, db)
    assert res["ok"] is True
    assert "No hay pendientes" in res["reply"]


def test_slash_pendientes_param_invalido(db, admin_user):
    res = handle_slash("/pendientes hola", admin_user, db)
    assert res["ok"] is False
