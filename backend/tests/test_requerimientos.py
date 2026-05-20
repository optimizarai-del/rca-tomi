"""Tests Sprint 17 — Requerimientos por obra."""
from app import models
from app.slash_commands import handle_slash


def _crear_req(client, headers, obra_id, mensaje):
    r = client.post(
        "/api/requerimientos",
        json={"obra_id": obra_id, "mensaje": mensaje},
        headers=headers,
    )
    return r


def test_crear_requerimiento(client, auth_headers, obra):
    r = _crear_req(client, auth_headers, obra.id, "Falta cemento")
    assert r.status_code == 201
    data = r.json()
    assert data["mensaje"] == "Falta cemento"
    assert data["estado"] == "abierto"
    assert data["canal"] == "web"
    assert data["obra_id"] == obra.id


def test_obra_inexistente_404(client, auth_headers):
    r = _crear_req(client, auth_headers, 99999, "test")
    assert r.status_code == 404


def test_mensaje_vacio_422(client, auth_headers, obra):
    r = _crear_req(client, auth_headers, obra.id, "")
    assert r.status_code == 422


def test_listar_por_obra(client, auth_headers, obra):
    _crear_req(client, auth_headers, obra.id, "req 1")
    _crear_req(client, auth_headers, obra.id, "req 2")
    r = client.get(f"/api/obras/{obra.id}/requerimientos", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert {it["mensaje"] for it in items} == {"req 1", "req 2"}


def test_filtrar_por_estado(client, auth_headers, obra):
    r1 = _crear_req(client, auth_headers, obra.id, "abierto 1").json()
    _crear_req(client, auth_headers, obra.id, "abierto 2")
    client.patch(f"/api/requerimientos/{r1['id']}/resolver", headers=auth_headers)

    r = client.get(
        f"/api/obras/{obra.id}/requerimientos?estado=abierto", headers=auth_headers
    )
    items = r.json()
    assert len(items) == 1
    assert items[0]["mensaje"] == "abierto 2"


def test_resolver_y_reabrir(client, auth_headers, obra, admin_user):
    rid = _crear_req(client, auth_headers, obra.id, "test").json()["id"]

    r = client.patch(f"/api/requerimientos/{rid}/resolver", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["estado"] == "resuelto"
    assert data["resuelto_by_id"] == admin_user.id
    assert data["resuelto_at"] is not None

    r = client.patch(f"/api/requerimientos/{rid}/reabrir", headers=auth_headers)
    data = r.json()
    assert data["estado"] == "abierto"
    assert data["resuelto_by_id"] is None
    assert data["resuelto_at"] is None


def test_eliminar(client, auth_headers, obra):
    rid = _crear_req(client, auth_headers, obra.id, "borrar").json()["id"]
    r = client.delete(f"/api/requerimientos/{rid}", headers=auth_headers)
    assert r.status_code == 204
    r = client.get(f"/api/obras/{obra.id}/requerimientos", headers=auth_headers)
    assert r.json() == []


def test_supervisor_solo_ve_obras_de_su_whitelist(
    client, db, headers_for, user_supervisor, obra, cliente, regimen_ri
):
    from datetime import date

    obra2 = models.Obra(
        codigo="ZZZ", nombre="Obra fuera del scope",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=100,
        fecha_inicio=date.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra2); db.commit(); db.refresh(obra2)

    # Crear req en obra2 con admin
    from app.security import create_access_token
    # Como admin (sin filas en permisos_usuario_obra → ve todas)
    admin_h = headers_for(_get_admin(db))
    _crear_req(client, admin_h, obra2.id, "req en obra que no debe ver")

    # Whitelist supervisor → solo `obra`
    db.add(models.PermisoUsuarioObra(user_id=user_supervisor.id, obra_id=obra.id))
    db.commit()

    # GET /api/requerimientos no incluye obra2
    r = client.get("/api/requerimientos", headers=headers_for(user_supervisor))
    assert r.status_code == 200
    obra_ids = {it["obra_id"] for it in r.json()}
    assert obra2.id not in obra_ids

    # GET /api/obras/:obra2.id/requerimientos da 404 para supervisor
    r = client.get(f"/api/obras/{obra2.id}/requerimientos", headers=headers_for(user_supervisor))
    assert r.status_code == 404


def _get_admin(db):
    """Devuelve un admin existente — el conftest crea admin@test.com."""
    return db.query(models.User).filter(models.User.email == "admin@test.com").first()


def test_slash_req_crea_requerimiento(db, admin_user, obra):
    res = handle_slash(f"/req {obra.codigo} falta cemento, mando 5 bolsas", admin_user, db)
    assert res["ok"] is True
    assert "Requerimiento anotado" in res["reply"]
    assert res["requerimiento_id"]

    r = db.query(models.Requerimiento).filter(
        models.Requerimiento.id == res["requerimiento_id"]
    ).first()
    assert r is not None
    assert r.mensaje == "falta cemento, mando 5 bolsas"
    assert r.estado == models.RequerimientoEstado.abierto
    assert r.canal == models.CanalCarga.whatsapp


def test_slash_req_obra_inexistente(db, admin_user):
    res = handle_slash("/req INEXISTENTE algo", admin_user, db)
    assert res["ok"] is False
    assert "no encontrada" in res["reply"]


def test_slash_req_sin_args(db, admin_user, obra):
    res = handle_slash("/req", admin_user, db)
    assert res["ok"] is False
    assert "Uso" in res["reply"]


def test_slash_help_incluye_req(db, admin_user):
    res = handle_slash("/help", admin_user, db)
    assert "/req" in res["reply"]
