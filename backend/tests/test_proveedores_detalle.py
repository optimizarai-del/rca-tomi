"""Tests Sprint 15 — Proveedores extendido: materiales que vende, historial filtrable, ocultar inactivos."""
from datetime import date, timedelta
import pytest

from app import models
from app.stock import cargar_compra_pendiente, marcar_retirado


@pytest.fixture
def proveedor(db):
    p = models.Proveedor(nombre="Holcim", cuit="30-12345678-9", rubro="cemento")
    db.add(p); db.commit(); db.refresh(p)
    return p


@pytest.fixture
def proveedor_2(db):
    p = models.Proveedor(nombre="Acindar", cuit="30-87654321-9", rubro="hierro")
    db.add(p); db.commit(); db.refresh(p)
    return p


@pytest.fixture
def material(db, proveedor):
    m = models.Material(nombre="Cemento", categoria="cemento", unidad="bolsa",
                        precio_unitario=8000, proveedor_id=proveedor.id, stock=0)
    db.add(m); db.commit(); db.refresh(m)
    return m


@pytest.fixture
def material_otro_prov(db, proveedor_2):
    m = models.Material(nombre="Hierro 8", categoria="hierro", unidad="kg",
                        precio_unitario=2500, proveedor_id=proveedor_2.id, stock=0)
    db.add(m); db.commit(); db.refresh(m)
    return m


def test_list_proveedores_oculta_inactivos_por_default(client, db, auth_headers, proveedor, proveedor_2):
    # Sin actividad → ambos se muestran (no hay registros antiguos)
    r = client.get("/api/proveedores", headers=auth_headers)
    assert r.status_code == 200
    nombres = {p["nombre"] for p in r.json()}
    assert {"Holcim", "Acindar"}.issubset(nombres)


def test_list_proveedores_oculta_solo_con_actividad_vieja(
    client, db, auth_headers, proveedor, proveedor_2, material, material_otro_prov, admin_user
):
    # proveedor_2 (Acindar): retiro hace 18 meses → debería ocultarse
    cargar_compra_pendiente(db, material_id=material_otro_prov.id, proveedor_id=proveedor_2.id, cantidad=50)
    retiro = marcar_retirado(
        db,
        stock_material_id=db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == material_otro_prov.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
        ).first().id,
        cantidad=50,
        usuario_id=admin_user.id,
    )
    retiro.fecha_retiro = date.today() - timedelta(days=600)
    db.commit()

    # proveedor (Holcim): retiro reciente
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=20)
    marcar_retirado(
        db,
        stock_material_id=db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == material.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
        ).first().id,
        cantidad=20,
        usuario_id=admin_user.id,
    )

    # Default: Acindar oculto
    r = client.get("/api/proveedores", headers=auth_headers)
    nombres = {p["nombre"] for p in r.json()}
    assert "Holcim" in nombres
    assert "Acindar" not in nombres

    # Con flag incluir_inactivos: ambos
    r = client.get("/api/proveedores?incluir_inactivos=true", headers=auth_headers)
    nombres = {p["nombre"] for p in r.json()}
    assert {"Holcim", "Acindar"}.issubset(nombres)


def test_materiales_que_vende_proveedor(client, db, auth_headers, proveedor, material):
    # Agrego un segundo material del mismo proveedor
    m2 = models.Material(nombre="Cal", categoria="cemento", unidad="bolsa",
                         precio_unitario=3500, proveedor_id=proveedor.id, stock=0)
    db.add(m2); db.commit()

    r = client.get(f"/api/proveedores/{proveedor.id}/materiales", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    nombres = {i["nombre"] for i in items}
    assert nombres == {"Cemento", "Cal"}


def test_materiales_incluye_pendiente_retiro_en_ese_proveedor(
    client, db, auth_headers, proveedor, material
):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=80)
    r = client.get(f"/api/proveedores/{proveedor.id}/materiales", headers=auth_headers)
    items = r.json()
    cemento = next(i for i in items if i["nombre"] == "Cemento")
    assert cemento["pendiente_retiro"] == 80.0


def test_historial_facturado_y_presupuestado(
    client, db, auth_headers, proveedor, material, obra, admin_user
):
    # facturado: 1 retiro
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=30)
    marcar_retirado(
        db,
        stock_material_id=db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == material.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
        ).first().id,
        cantidad=30,
        forma_pago=models.MedioPago.TRANSFERENCIA,
        en_negro=False,
        usuario_id=admin_user.id,
    )

    # presupuestado: 1 PresupuestoItem cuyo material apunta a este proveedor
    presupuesto = models.Presupuesto(
        obra_id=obra.id, nombre="Pres ago", estado=models.EstadoPresupuesto.borrador,
        total_estimado=0,
    )
    db.add(presupuesto); db.commit(); db.refresh(presupuesto)
    item = models.PresupuestoItem(
        presupuesto_id=presupuesto.id, material_id=material.id,
        cantidad=10, precio_unitario_estimado=8000, subtotal=80000,
    )
    db.add(item); db.commit()

    r = client.get(f"/api/proveedores/{proveedor.id}/historial", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    tipos = {it["tipo"] for it in items}
    assert tipos == {"facturado", "presupuestado"}


def test_historial_default_oculta_mayor_1_anio(
    client, db, auth_headers, proveedor, material, admin_user
):
    """Con retiros hace 2 años no aparecen sin incluir_antiguos."""
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=10)
    retiro = marcar_retirado(
        db,
        stock_material_id=db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == material.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
        ).first().id,
        cantidad=10,
        usuario_id=admin_user.id,
    )
    retiro.fecha_retiro = date.today() - timedelta(days=400)
    db.commit()

    r = client.get(f"/api/proveedores/{proveedor.id}/historial", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []

    r = client.get(
        f"/api/proveedores/{proveedor.id}/historial?incluir_antiguos=true", headers=auth_headers
    )
    items = r.json()
    assert len(items) == 1
    assert items[0]["tipo"] == "facturado"


def test_historial_orden_por_fecha_desc(
    client, db, auth_headers, proveedor, material, obra, admin_user
):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=100)
    sm = db.query(models.StockMaterial).filter(
        models.StockMaterial.material_id == material.id,
        models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
    ).first()
    r1 = marcar_retirado(db, stock_material_id=sm.id, cantidad=20, usuario_id=admin_user.id)
    r1.fecha_retiro = date(2026, 5, 1)
    db.commit()
    r2 = marcar_retirado(db, stock_material_id=sm.id, cantidad=30, usuario_id=admin_user.id)
    r2.fecha_retiro = date(2026, 5, 18)
    db.commit()

    r = client.get(f"/api/proveedores/{proveedor.id}/historial", headers=auth_headers)
    fechas = [it["fecha"] for it in r.json()]
    assert fechas == sorted(fechas, reverse=True)


def test_detalle_proveedor_completo(client, db, auth_headers, proveedor, material, admin_user):
    cargar_compra_pendiente(db, material_id=material.id, proveedor_id=proveedor.id, cantidad=15)
    marcar_retirado(
        db,
        stock_material_id=db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == material.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
        ).first().id,
        cantidad=15,
        usuario_id=admin_user.id,
    )
    r = client.get(f"/api/proveedores/{proveedor.id}/detalle", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == proveedor.id
    assert data["nombre"] == "Holcim"
    assert len(data["materiales_vendidos"]) == 1
    assert data["materiales_vendidos"][0]["nombre"] == "Cemento"
    assert data["ultima_actividad"] is not None


def test_detalle_proveedor_inexistente_404(client, auth_headers):
    r = client.get("/api/proveedores/99999/detalle", headers=auth_headers)
    assert r.status_code == 404


def test_materiales_inexistente_404(client, auth_headers):
    r = client.get("/api/proveedores/99999/materiales", headers=auth_headers)
    assert r.status_code == 404


def test_historial_inexistente_404(client, auth_headers):
    r = client.get("/api/proveedores/99999/historial", headers=auth_headers)
    assert r.status_code == 404
