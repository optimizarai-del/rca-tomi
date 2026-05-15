"""Tests Sprint 9 — stock multi-ubicación.

Cubre:
- Data: 3 ubicaciones (deposito_propio, en_obra, comprado_no_retirado).
- Servicio: cargar_compra_pendiente, retirar_de_proveedor, consumir_en_obra, transferir_stock.
- Reglas: cantidades no negativas, validaciones de obra/proveedor inexistentes.
- Cache Material.stock = sum(deposito + en_obra), sin contar pendientes.
- Endpoints /api/stock.
- Tools del agente (consultar_stock, cargar_compra_pendiente_retiro, etc.).
"""
import pytest
from app import models
from app.stock import (
    cargar_compra_pendiente, retirar_de_proveedor, consumir_en_obra,
    transferir_stock, breakdown_por_material,
)
from app.agent.tools import TOOL_HANDLERS


@pytest.fixture()
def material(db):
    m = models.Material(nombre="Cemento Holcim", categoria="cemento", unidad="bolsa",
                        stock=0, stock_minimo=10, precio_unitario=2500)
    db.add(m); db.commit(); db.refresh(m)
    return m


@pytest.fixture()
def proveedor(db):
    p = models.Proveedor(nombre="Holcim SA", cuit="30-77777777-7", rubro="cemento")
    db.add(p); db.commit(); db.refresh(p)
    return p


# ─── Lógica de stock ───────────────────────────────────────────────────────

def test_cargar_compra_pendiente_genera_fila_y_no_afecta_cache(db, material, proveedor, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=100, usuario_id=admin_user.id)

    filas = db.query(models.StockMaterial).filter_by(material_id=material.id).all()
    assert len(filas) == 1
    f = filas[0]
    assert f.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado
    assert f.ubicacion_ref == proveedor.id
    assert f.cantidad == 100

    # Material.stock NO debería contar pendientes
    db.refresh(material)
    assert material.stock == 0


def test_retirar_a_deposito_mueve_stock(db, material, proveedor, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=100, usuario_id=admin_user.id)

    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=60, destino_tipo="deposito_propio", usuario_id=admin_user.id)

    detalle = breakdown_por_material(db, material_id=material.id)[0]
    assert detalle["stock_pendiente_retiro"] == 40
    assert detalle["stock_total_disponible"] == 60
    db.refresh(material)
    assert material.stock == 60


def test_retirar_directo_a_obra(db, material, proveedor, obra, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=100, usuario_id=admin_user.id)

    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=100, destino_tipo="en_obra", destino_obra_id=obra.id,
                        usuario_id=admin_user.id)

    detalle = breakdown_por_material(db, material_id=material.id)[0]
    assert detalle["stock_pendiente_retiro"] == 0
    assert detalle["stock_total_disponible"] == 100
    # Debería haber UNA fila en_obra para esa obra
    en_obra = [u for u in detalle["ubicaciones"]
               if u["ubicacion_tipo"] == "en_obra" and u["ubicacion_ref"] == obra.id]
    assert len(en_obra) == 1
    assert en_obra[0]["cantidad"] == 100


def test_no_se_puede_retirar_mas_de_lo_pendiente(db, material, proveedor, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=50, usuario_id=admin_user.id)
    with pytest.raises(ValueError, match="No hay suficiente pendiente"):
        retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=80, destino_tipo="deposito_propio", usuario_id=admin_user.id)


def test_consumir_en_obra_descontados_cache(db, material, proveedor, obra, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=100, usuario_id=admin_user.id)
    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=100, destino_tipo="en_obra", destino_obra_id=obra.id,
                        usuario_id=admin_user.id)
    consumir_en_obra(db, material_id=material.id, obra_id=obra.id, cantidad=30,
                    usuario_id=admin_user.id)

    detalle = breakdown_por_material(db, material_id=material.id)[0]
    assert detalle["stock_total_disponible"] == 70  # 100 - 30


def test_consumir_mas_de_lo_disponible_falla(db, material, proveedor, obra, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=50, usuario_id=admin_user.id)
    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=50, destino_tipo="en_obra", destino_obra_id=obra.id,
                        usuario_id=admin_user.id)
    with pytest.raises(ValueError, match="No hay suficiente stock"):
        consumir_en_obra(db, material_id=material.id, obra_id=obra.id, cantidad=100,
                        usuario_id=admin_user.id)


def test_transferir_deposito_a_obra(db, material, proveedor, obra, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=100, usuario_id=admin_user.id)
    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=100, destino_tipo="deposito_propio", usuario_id=admin_user.id)
    transferir_stock(db, material_id=material.id, cantidad=40,
                    origen_tipo="deposito_propio", origen_obra_id=None,
                    destino_tipo="en_obra", destino_obra_id=obra.id,
                    usuario_id=admin_user.id)

    detalle = breakdown_por_material(db, material_id=material.id)[0]
    deposito = next(u for u in detalle["ubicaciones"] if u["ubicacion_tipo"] == "deposito_propio")
    en_obra = next(u for u in detalle["ubicaciones"] if u["ubicacion_tipo"] == "en_obra")
    assert deposito["cantidad"] == 60
    assert en_obra["cantidad"] == 40
    assert detalle["stock_total_disponible"] == 100  # depósito + obras


def test_cantidad_cero_rechazada(db, material, proveedor, admin_user):
    with pytest.raises(ValueError, match="positiva"):
        cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                                cantidad=0, usuario_id=admin_user.id)


def test_material_inexistente_rechazado(db, proveedor, admin_user):
    with pytest.raises(ValueError, match="no existe"):
        cargar_compra_pendiente(db, material_id=9999, proveedor_id=proveedor.id,
                                cantidad=10, usuario_id=admin_user.id)


# ─── Auditoría: cada operación deja MovimientoMaterial ─────────────────────

def test_cada_operacion_registra_movimiento(db, material, proveedor, obra, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=50, usuario_id=admin_user.id)
    retirar_de_proveedor(db, material_id=material.id, proveedor_id=proveedor.id,
                        cantidad=50, destino_tipo="en_obra", destino_obra_id=obra.id,
                        usuario_id=admin_user.id)
    consumir_en_obra(db, material_id=material.id, obra_id=obra.id, cantidad=10,
                    usuario_id=admin_user.id)
    movs = db.query(models.MovimientoMaterial).filter_by(material_id=material.id).all()
    assert len(movs) == 3
    tipos = {m.tipo for m in movs}
    assert {"ingreso_pendiente", "retiro_proveedor", "consumo"} == tipos


# ─── Endpoints REST ────────────────────────────────────────────────────────

def test_endpoint_get_stock_lista_materiales(client, material, proveedor, admin_user, auth_headers):
    r = client.get("/api/stock/", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["nombre"] == "Cemento Holcim"
    assert data[0]["stock_total_disponible"] == 0


def test_endpoint_compra_pendiente_y_retiro(client, material, proveedor, obra, admin_user, auth_headers):
    r = client.post("/api/stock/compra-pendiente",
                    json={"material_id": material.id, "proveedor_id": proveedor.id, "cantidad": 200},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["stock_pendiente_retiro"] == 200

    r = client.post("/api/stock/retiro-proveedor",
                    json={"material_id": material.id, "proveedor_id": proveedor.id,
                          "cantidad": 150, "destino_tipo": "en_obra", "destino_obra_id": obra.id},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stock_pendiente_retiro"] == 50
    assert body["stock_total_disponible"] == 150


# ─── Tool del agente ───────────────────────────────────────────────────────

def test_tool_consultar_stock_devuelve_breakdown(db, material, proveedor, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id,
                            cantidad=20, usuario_id=admin_user.id)
    out = TOOL_HANDLERS["consultar_stock"]({"material": material.nombre}, admin_user, db)
    assert out["total_materiales"] == 1
    item = out["materiales"][0]
    assert item["stock_pendiente_retiro"] == 20


def test_tool_cargar_compra_resuelve_nombres(db, material, proveedor, admin_user):
    out = TOOL_HANDLERS["cargar_compra_pendiente_retiro"](
        {"material": "Cemento", "proveedor": "Holcim", "cantidad": 30},
        admin_user, db,
    )
    assert out.get("ok") is True
    assert out["cantidad_agregada"] == 30
    assert out["pendiente_total_ahora"] == 30


def test_tool_retirar_a_obra_resuelve_obra_por_codigo(db, material, proveedor, obra, admin_user):
    TOOL_HANDLERS["cargar_compra_pendiente_retiro"](
        {"material": material.id, "proveedor": proveedor.id, "cantidad": 50},
        admin_user, db,
    )
    out = TOOL_HANDLERS["retirar_de_proveedor"]({
        "material": material.id, "proveedor": proveedor.id, "cantidad": 50,
        "destino_tipo": "en_obra", "obra": obra.codigo,
    }, admin_user, db)
    assert out.get("ok") is True
    assert out["pendiente_restante"] == 0
    assert out["stock_disponible_total"] == 50


def test_tool_falla_si_no_encuentra_material(db, admin_user):
    out = TOOL_HANDLERS["consultar_stock"]({"material": "no-existe-fasdfas"}, admin_user, db)
    assert "error" in out
