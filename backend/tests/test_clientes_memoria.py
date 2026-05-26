"""Tests Sprint 22 — Memoria de clientes (campos extra + notas + detalle)."""
from datetime import date, datetime
import pytest

from app import models


@pytest.fixture
def cliente_2(db, regimen_ri):
    """Segundo cliente con datos completos de memoria."""
    c = models.Cliente(
        nombre="Constructora SA", cuit="30-99988877-6",
        tipo="privado_ri", regimen_fiscal_id=regimen_ri.id,
        cbu="2850300040094112233445",
        alias_bancario="constructora.sa.galicia",
        condiciones_pago="30 días fecha factura",
        contacto_secundario="María +5491111111111",
        preferencias="Aprueba etapas los lunes",
    )
    db.add(c); db.commit(); db.refresh(c)
    return c


def test_crear_cliente_con_campos_memoria(client, auth_headers, regimen_ri):
    payload = {
        "nombre": "Cliente nuevo",
        "tipo": "privado_ri",
        "regimen_fiscal_id": regimen_ri.id,
        "cbu": "0000000000000000000001",
        "alias_bancario": "mi.alias",
        "condiciones_pago": "Contado",
        "contacto_secundario": "Juan",
        "preferencias": "Prefiere transferencia",
    }
    r = client.post("/api/clientes", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["cbu"] == "0000000000000000000001"
    assert data["alias_bancario"] == "mi.alias"
    assert data["condiciones_pago"] == "Contado"
    assert data["contacto_secundario"] == "Juan"
    assert data["preferencias"] == "Prefiere transferencia"
    assert data["last_interaction_at"] is None  # no se setea al crear


def test_get_cliente_devuelve_campos_memoria(client, auth_headers, cliente_2):
    r = client.get(f"/api/clientes/{cliente_2.id}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cbu"] == "2850300040094112233445"
    assert data["alias_bancario"] == "constructora.sa.galicia"


def test_detalle_cliente_estructura_completa(client, auth_headers, cliente_2, obra):
    r = client.get(f"/api/clientes/{cliente_2.id}/detalle", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Campos base del cliente
    assert data["id"] == cliente_2.id
    assert data["cbu"] == "2850300040094112233445"
    # Estructura nueva
    assert "obras" in data
    assert "resumen_financiero" in data
    assert "interacciones" in data
    assert data["resumen_financiero"]["obras_total"] == 0  # no le linkeé obras a cliente_2
    assert data["interacciones"] == []


def test_detalle_incluye_obras_del_cliente(client, db, auth_headers, cliente):
    """El detalle lista todas las obras del cliente con sus números."""
    from datetime import date
    obra1 = models.Obra(
        codigo="O1", nombre="Obra 1", cliente_id=cliente.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=500000,
        fecha_inicio=date(2026, 1, 1), estado=models.ObraStatus.EN_CURSO,
    )
    obra2 = models.Obra(
        codigo="O2", nombre="Obra 2", cliente_id=cliente.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=300000,
        fecha_inicio=date(2026, 2, 1), estado=models.ObraStatus.FINALIZADA,
    )
    db.add_all([obra1, obra2]); db.commit()

    r = client.get(f"/api/clientes/{cliente.id}/detalle", headers=auth_headers)
    data = r.json()
    assert data["resumen_financiero"]["obras_total"] == 2
    assert data["resumen_financiero"]["obras_en_curso"] == 1
    assert data["resumen_financiero"]["obras_finalizadas"] == 1
    assert data["resumen_financiero"]["monto_contratos_total"] == 800000

    codigos = {o["codigo"] for o in data["obras"]}
    assert codigos == {"O1", "O2"}


def test_detalle_resumen_financiero_agrega_movimientos(
    client, db, auth_headers, cliente, regimen_ri, admin_user
):
    """resumen_financiero suma cobrado/pendiente de todas las obras del cliente."""
    from datetime import date

    obra1 = models.Obra(
        codigo="X1", nombre="X1", cliente_id=cliente.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=100,
        fecha_inicio=date.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra1); db.commit(); db.refresh(obra1)

    # 2 ingresos cobrados de 50k cada uno + 1 pendiente de 30k
    for monto, estado in [(50000, "cobrado"), (50000, "cobrado"), (30000, "pendiente")]:
        client.post("/api/movimientos", json={
            "obra_id": obra1.id, "fecha": "2026-05-20", "tipo": "INGRESO",
            "origen_ingreso": "ANTICIPO_CLIENTE", "monto": monto,
            "medio_pago": "EFECTIVO", "concepto": "test",
            "cobro_pago_estado": estado,
        }, headers=auth_headers)

    r = client.get(f"/api/clientes/{cliente.id}/detalle", headers=auth_headers)
    rf = r.json()["resumen_financiero"]
    assert rf["ingresos_cobrado_total"] == 100000
    assert rf["ingresos_pendiente_total"] == 30000


def test_crear_nota(client, auth_headers, cliente_2):
    r = client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": cliente_2.id, "texto": "Llamó por etapa 3", "importante": False},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["texto"] == "Llamó por etapa 3"
    assert data["importante"] is False
    assert data["autor_id"] is not None  # se setea desde el user logueado


def test_crear_nota_importante(client, auth_headers, cliente_2):
    r = client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": cliente_2.id, "texto": "URGENTE: cambio de fecha", "importante": True},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["importante"] is True


def test_crear_nota_actualiza_last_interaction(client, auth_headers, cliente_2):
    client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": cliente_2.id, "texto": "test"},
        headers=auth_headers,
    )
    r = client.get(f"/api/clientes/{cliente_2.id}", headers=auth_headers)
    assert r.json()["last_interaction_at"] is not None


def test_listar_notas_orden_desc(client, auth_headers, cliente_2):
    client.post(f"/api/clientes/{cliente_2.id}/notas",
                json={"cliente_id": cliente_2.id, "texto": "primera"}, headers=auth_headers)
    client.post(f"/api/clientes/{cliente_2.id}/notas",
                json={"cliente_id": cliente_2.id, "texto": "segunda"}, headers=auth_headers)

    r = client.get(f"/api/clientes/{cliente_2.id}/notas", headers=auth_headers)
    notas = r.json()
    assert len(notas) == 2
    # la más reciente primero
    assert notas[0]["texto"] == "segunda"


def test_crear_nota_cliente_id_mismatch_400(client, auth_headers, cliente_2):
    r = client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": 99999, "texto": "test"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_crear_nota_cliente_inexistente_404(client, auth_headers):
    r = client.post(
        "/api/clientes/99999/notas",
        json={"cliente_id": 99999, "texto": "test"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_borrar_nota(client, auth_headers, cliente_2):
    nid = client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": cliente_2.id, "texto": "borrar"},
        headers=auth_headers,
    ).json()["id"]
    r = client.delete(f"/api/clientes/notas/{nid}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(f"/api/clientes/{cliente_2.id}/notas", headers=auth_headers).json() == []


def test_borrar_nota_solo_admin(client, headers_for, auth_headers, cliente_2, user_supervisor):
    nid = client.post(
        f"/api/clientes/{cliente_2.id}/notas",
        json={"cliente_id": cliente_2.id, "texto": "test"},
        headers=auth_headers,
    ).json()["id"]
    r = client.delete(f"/api/clientes/notas/{nid}", headers=headers_for(user_supervisor))
    assert r.status_code == 403


def test_detalle_cliente_inexistente_404(client, auth_headers):
    r = client.get("/api/clientes/99999/detalle", headers=auth_headers)
    assert r.status_code == 404
