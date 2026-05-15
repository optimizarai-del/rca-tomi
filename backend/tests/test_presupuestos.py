"""Tests Sprint 10 — presupuestos de materiales por obra.

Cubre:
- Servicio: crear_presupuesto, agregar_item, aprobar_presupuesto.
- Cálculo correcto de total_estimado (sum de subtotales).
- Resolución de precio: si no se pasa, toma Material.precio_unitario.
- Transiciones: borrador → aprobado → no se pueden modificar.
- Endpoints REST.
- Tools del agente.
"""
import pytest
from app import models
from app.presupuestos_svc import (
    crear_presupuesto, agregar_item, aprobar_presupuesto, serialize,
)
from app.agent.tools import TOOL_HANDLERS


@pytest.fixture()
def materiales(db):
    m1 = models.Material(nombre="Cemento", categoria="cemento", unidad="bolsa",
                         stock=0, precio_unitario=2500)
    m2 = models.Material(nombre="Ladrillo", categoria="ladrillo", unidad="u",
                         stock=0, precio_unitario=80)
    db.add_all([m1, m2]); db.commit(); db.refresh(m1); db.refresh(m2)
    return m1, m2


# ─── Servicio ──────────────────────────────────────────────────────────────

def test_crear_presupuesto_calcula_total(db, obra, materiales, admin_user):
    m1, m2 = materiales
    p = crear_presupuesto(db, obra_id=obra.id, nombre="Cimientos",
                         items=[
                             {"material_id": m1.id, "cantidad": 100},  # toma 2500 del Material
                             {"material_id": m2.id, "cantidad": 200, "precio_unitario_estimado": 100},
                         ], created_by_id=admin_user.id)
    assert p.id is not None
    assert p.estado == models.EstadoPresupuesto.borrador
    # 100 * 2500 + 200 * 100 = 270.000
    assert p.total_estimado == 100 * 2500 + 200 * 100


def test_crear_presupuesto_sin_obra_falla(db, materiales, admin_user):
    m1, _ = materiales
    with pytest.raises(ValueError, match="Obra"):
        crear_presupuesto(db, obra_id=999, nombre="X",
                         items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)


def test_agregar_item_recalcula_total(db, obra, materiales, admin_user):
    m1, m2 = materiales
    p = crear_presupuesto(db, obra_id=obra.id, nombre="A",
                         items=[{"material_id": m1.id, "cantidad": 10}], created_by_id=admin_user.id)
    base = p.total_estimado
    p = agregar_item(db, presupuesto_id=p.id, material_id=m2.id, cantidad=50, precio_unitario_estimado=200)
    assert p.total_estimado == base + 50 * 200


def test_no_se_puede_agregar_item_a_presupuesto_aprobado(db, obra, materiales, admin_user):
    m1, _ = materiales
    p = crear_presupuesto(db, obra_id=obra.id, nombre="A",
                         items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)
    aprobar_presupuesto(db, presupuesto_id=p.id)
    with pytest.raises(ValueError, match="borrador"):
        agregar_item(db, presupuesto_id=p.id, material_id=m1.id, cantidad=10)


def test_no_se_puede_aprobar_vacio(db, obra, admin_user):
    p = crear_presupuesto(db, obra_id=obra.id, nombre="Vacío", items=[], created_by_id=admin_user.id)
    with pytest.raises(ValueError, match="vacío"):
        aprobar_presupuesto(db, presupuesto_id=p.id)


def test_aprobacion_setea_fecha_aprobado_at(db, obra, materiales, admin_user):
    m1, _ = materiales
    p = crear_presupuesto(db, obra_id=obra.id, nombre="A",
                         items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)
    assert p.aprobado_at is None
    aprobar_presupuesto(db, presupuesto_id=p.id)
    db.refresh(p)
    assert p.aprobado_at is not None


def test_cantidad_invalida_rechaza(db, obra, materiales, admin_user):
    m1, _ = materiales
    with pytest.raises(ValueError, match="Cantidad"):
        crear_presupuesto(db, obra_id=obra.id, nombre="X",
                         items=[{"material_id": m1.id, "cantidad": 0}], created_by_id=admin_user.id)


# ─── Endpoints REST ────────────────────────────────────────────────────────

def test_endpoint_crear_listar_aprobar(client, obra, materiales, admin_user, auth_headers):
    m1, m2 = materiales
    r = client.post("/api/presupuestos/", headers=auth_headers, json={
        "obra_id": obra.id, "nombre": "Cimientos enero",
        "items": [
            {"material_id": m1.id, "cantidad": 100},
            {"material_id": m2.id, "cantidad": 500, "precio_unitario_estimado": 90},
        ],
    })
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["estado"] == "borrador"
    assert p["total_estimado"] == 100 * 2500 + 500 * 90

    # Listar filtrando por obra
    r = client.get(f"/api/presupuestos/?obra_id={obra.id}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Aprobar
    r = client.post(f"/api/presupuestos/{p['id']}/aprobar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "aprobado"


def test_endpoint_borrar_aprobado_falla(client, obra, materiales, admin_user, auth_headers):
    m1, _ = materiales
    r = client.post("/api/presupuestos/", headers=auth_headers, json={
        "obra_id": obra.id, "nombre": "X",
        "items": [{"material_id": m1.id, "cantidad": 1}],
    })
    pid = r.json()["id"]
    client.post(f"/api/presupuestos/{pid}/aprobar", headers=auth_headers)
    r = client.delete(f"/api/presupuestos/{pid}", headers=auth_headers)
    assert r.status_code == 400


# ─── Tools del agente ──────────────────────────────────────────────────────

def test_tool_crear_presupuesto_resuelve_referencias(db, obra, materiales, admin_user):
    out = TOOL_HANDLERS["crear_presupuesto"]({
        "obra": obra.codigo,
        "nombre": "Demo",
        "items": [
            {"material": "Cemento", "cantidad": 50},
            {"material": "Ladrillo", "cantidad": 1000, "precio": 75},
        ],
    }, admin_user, db)
    assert out.get("ok") is True
    p = out["presupuesto"]
    assert p["total_estimado"] == 50 * 2500 + 1000 * 75


def test_tool_aprobar_presupuesto(db, obra, materiales, admin_user):
    m1, _ = materiales
    p = crear_presupuesto(db, obra_id=obra.id, nombre="A",
                         items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)
    out = TOOL_HANDLERS["aprobar_presupuesto"]({"presupuesto_id": p.id}, admin_user, db)
    assert out.get("ok") is True
    assert out["presupuesto"]["estado"] == "aprobado"


def test_tool_consultar_presupuestos_filtra_por_obra(db, obra, cliente, regimen_ri, materiales, admin_user):
    from datetime import date, timedelta
    obra2 = models.Obra(codigo="OTR", nombre="Otra Obra", cliente_id=cliente.id,
                       regimen_fiscal_id=regimen_ri.id,
                       tipo_facturacion=models.TipoFacturacion.MIXTA,
                       monto_contrato=500_000, fecha_inicio=date.today(),
                       estado=models.ObraStatus.EN_CURSO)
    db.add(obra2); db.commit(); db.refresh(obra2)

    m1, _ = materiales
    crear_presupuesto(db, obra_id=obra.id, nombre="P1",
                     items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)
    crear_presupuesto(db, obra_id=obra2.id, nombre="P2",
                     items=[{"material_id": m1.id, "cantidad": 1}], created_by_id=admin_user.id)

    out = TOOL_HANDLERS["consultar_presupuestos"]({"obra": obra.codigo}, admin_user, db)
    assert out["total"] == 1
    assert out["presupuestos"][0]["nombre"] == "P1"
