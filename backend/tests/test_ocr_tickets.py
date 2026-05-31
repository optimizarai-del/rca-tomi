"""Tests Sprint 18 — OCR de tickets con Claude Vision.

Force ANTHROPIC_API_KEY="" para usar placeholder y no llamar al SDK real.
"""
import base64
import json
import pytest

from app import models
from app import ocr_vision


@pytest.fixture(autouse=True)
def _no_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")


@pytest.fixture
def proveedor_holcim(db):
    p = models.Proveedor(nombre="Holcim Argentina SA", cuit="30-50001234-5", rubro="cemento")
    db.add(p); db.commit(); db.refresh(p)
    return p


def test_parsear_placeholder(db):
    res, model = ocr_vision.parsear_ticket(image_url="http://example.com/x.jpg")
    assert model == "placeholder"
    assert res["tipo_documento"] == "FC_A"
    assert res["total"] == 121


def test_endpoint_parse_now_con_url(client, auth_headers):
    r = client.post(
        "/api/ocr-tickets/parse-now",
        json={"image_url": "http://example.com/factura.jpg"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["estado"] == "pendiente"
    assert data["resultado"]["total"] == 121
    assert data["model_used"] == "placeholder"


def test_endpoint_parse_now_con_base64(client, auth_headers):
    # bytes vacíos pero válidos para base64
    fake_b64 = base64.b64encode(b"fake_image_bytes").decode()
    r = client.post(
        "/api/ocr-tickets/parse-now",
        json={"image_base64": fake_b64},
        headers=auth_headers,
    )
    assert r.status_code == 201


def test_endpoint_parse_now_sin_imagen_400(client, auth_headers):
    r = client.post("/api/ocr-tickets/parse-now", json={}, headers=auth_headers)
    assert r.status_code == 400


def test_listar_tickets_filtrado_por_estado(client, db, auth_headers):
    # crear 2 pendientes
    for _ in range(2):
        client.post("/api/ocr-tickets/parse-now",
                    json={"image_url": "http://x.com/y.jpg"}, headers=auth_headers)
    r = client.get("/api/ocr-tickets?estado=pendiente", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2

    r = client.get("/api/ocr-tickets?estado=confirmado", headers=auth_headers)
    assert r.json() == []


def test_confirmar_crea_comprobante_y_movimiento(
    client, db, auth_headers, obra, proveedor_holcim,
):
    # crear ticket
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    # parchear el resultado del ticket para que tenga el CUIT de Holcim
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    resultado = json.loads(t.resultado_json)
    resultado["proveedor_cuit"] = "30-50001234-5"
    resultado["proveedor_nombre"] = "Holcim Argentina SA"
    t.resultado_json = json.dumps(resultado)
    db.commit()

    movs_antes = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == obra.id
    ).count()

    r = client.post(
        f"/api/ocr-tickets/{tid}/confirmar",
        json={"obra_id": obra.id, "es_venta": False, "categoria_egreso": "MATERIALES"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["estado"] == "confirmado"
    assert out["comprobante_id"]
    assert out["movimiento_obra_id"]
    assert out["confirmed_at"]

    # se creó el Comprobante y el MovimientoObra con proveedor matcheado
    cmp = db.query(models.Comprobante).filter(
        models.Comprobante.id == out["comprobante_id"]
    ).first()
    assert cmp.total == 121

    mov = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.id == out["movimiento_obra_id"]
    ).first()
    assert mov.tipo == models.TipoMovimiento.EGRESO
    assert mov.proveedor_id == proveedor_holcim.id
    assert mov.comprobante_id == cmp.id
    assert mov.canal == models.CanalCarga.agente_ia
    assert mov.legalidad == models.LegalidadMovimiento.blanco

    movs_despues = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == obra.id
    ).count()
    assert movs_despues - movs_antes == 1


def test_confirmar_dos_veces_400(client, auth_headers, obra):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    client.post(f"/api/ocr-tickets/{tid}/confirmar",
                json={"obra_id": obra.id, "es_venta": False}, headers=auth_headers)
    r = client.post(f"/api/ocr-tickets/{tid}/confirmar",
                    json={"obra_id": obra.id, "es_venta": False}, headers=auth_headers)
    assert r.status_code == 400


def test_confirmar_obra_inexistente_400(client, auth_headers):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    r = client.post(f"/api/ocr-tickets/{tid}/confirmar",
                    json={"obra_id": 99999}, headers=auth_headers)
    assert r.status_code == 400


def test_rechazar(client, auth_headers):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    r = client.post(f"/api/ocr-tickets/{tid}/rechazar", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "rechazado"


def test_no_se_puede_confirmar_rechazado(client, auth_headers, obra):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    client.post(f"/api/ocr-tickets/{tid}/rechazar", headers=auth_headers)
    r = client.post(f"/api/ocr-tickets/{tid}/confirmar",
                    json={"obra_id": obra.id}, headers=auth_headers)
    assert r.status_code == 400


def test_delete_admin(client, auth_headers):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    r = client.delete(f"/api/ocr-tickets/{tid}", headers=auth_headers)
    assert r.status_code == 204
    r = client.get(f"/api/ocr-tickets/{tid}", headers=auth_headers)
    assert r.status_code == 404


def test_matchear_proveedor_por_cuit(db, proveedor_holcim):
    p = ocr_vision.matchear_proveedor(db, cuit="30-50001234-5", nombre=None)
    assert p and p.id == proveedor_holcim.id


def test_matchear_proveedor_cuit_sin_guiones(db, proveedor_holcim):
    p = ocr_vision.matchear_proveedor(db, cuit="30500012345", nombre=None)
    assert p and p.id == proveedor_holcim.id


def test_matchear_proveedor_por_nombre_contains(db, proveedor_holcim):
    p = ocr_vision.matchear_proveedor(db, cuit=None, nombre="Holcim")
    assert p and p.id == proveedor_holcim.id


def test_matchear_proveedor_no_encuentra(db):
    p = ocr_vision.matchear_proveedor(db, cuit=None, nombre="Inexistente SA")
    assert p is None


def test_slash_pendientes_ocr(db, admin_user, auth_headers, client):
    # crear 2 tickets via API
    for _ in range(2):
        client.post("/api/ocr-tickets/parse-now",
                    json={"image_url": "http://x.com/y.jpg"},
                    headers=auth_headers)
    from app.slash_commands import handle_slash
    res = handle_slash("/pendientes_ocr", admin_user, db)
    assert res["ok"] is True
    assert "pendientes" in res["reply"].lower()
    assert res["count"] == 2


def test_slash_confirmar_via_bot(client, db, admin_user, auth_headers, obra):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    from app.slash_commands import handle_slash
    res = handle_slash(f"/confirmar {tid} {obra.codigo}", admin_user, db)
    assert res["ok"] is True, res
    assert "confirmado" in res["reply"].lower()
    # ticket actualizado
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    assert t.estado == models.TicketOCREstado.confirmado


def test_slash_rechazar_via_bot(client, db, admin_user, auth_headers):
    tid = client.post("/api/ocr-tickets/parse-now",
                      json={"image_url": "http://x.com/y.jpg"},
                      headers=auth_headers).json()["id"]
    from app.slash_commands import handle_slash
    res = handle_slash(f"/rechazar {tid}", admin_user, db)
    assert res["ok"] is True
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    assert t.estado == models.TicketOCREstado.rechazado
