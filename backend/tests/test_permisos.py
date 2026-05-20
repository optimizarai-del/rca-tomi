"""Tests Sprint 13 — permisos granulares por seccion + obras visibles por usuario."""
from app import models
from app.security import (
    user_section_allowed,
    user_visible_obra_ids,
    scope_obras,
)


def test_get_permisos_inicial_todas_secciones_permitidas(client, auth_headers, user_supervisor):
    r = client.get(f"/api/users/{user_supervisor.id}/permisos", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    # Sin filas → todas permitidas
    assert set(data["secciones_permitidas"]) == set(models.SECCIONES)
    assert data["secciones_bloqueadas"] == []
    assert data["obras_visibles_ids"] is None
    assert set(data["secciones_catalogo"]) == set(models.SECCIONES)


def test_set_permisos_bloquea_secciones_no_permitidas(client, auth_headers, user_supervisor):
    payload = {"secciones_permitidas": ["obras", "feed"], "obras_visibles_ids": None}
    r = client.put(
        f"/api/users/{user_supervisor.id}/permisos", json=payload, headers=auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data["secciones_permitidas"]) == {"obras", "feed"}
    bloqueadas = set(data["secciones_bloqueadas"])
    assert "movimientos" in bloqueadas
    assert "equipo" in bloqueadas


def test_seccion_inexistente_da_400(client, auth_headers, user_supervisor):
    r = client.put(
        f"/api/users/{user_supervisor.id}/permisos",
        json={"secciones_permitidas": ["inexistente"]},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_obras_inexistentes_da_400(client, auth_headers, user_supervisor, obra):
    r = client.put(
        f"/api/users/{user_supervisor.id}/permisos",
        json={"obras_visibles_ids": [obra.id, 99999]},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_user_section_allowed_admin_bypass(db, user_admin):
    """Admins ignoran filas de PermisoUsuario."""
    db.add(models.PermisoUsuario(user_id=user_admin.id, seccion="finanzas", allowed=False))
    db.commit()
    assert user_section_allowed(db, user_admin, "finanzas") is True


def test_user_section_allowed_supervisor_bloqueado(db, user_supervisor):
    db.add(models.PermisoUsuario(user_id=user_supervisor.id, seccion="finanzas", allowed=False))
    db.commit()
    assert user_section_allowed(db, user_supervisor, "finanzas") is False
    assert user_section_allowed(db, user_supervisor, "obras") is True  # sin fila → True


def test_user_visible_obra_ids_admin_ve_todas(db, user_admin, obra):
    """Admin nunca se restringe a una whitelist."""
    db.add(models.PermisoUsuarioObra(user_id=user_admin.id, obra_id=obra.id))
    db.commit()
    assert user_visible_obra_ids(db, user_admin) is None


def test_user_visible_obra_ids_supervisor_whitelist(db, user_supervisor, obra):
    db.add(models.PermisoUsuarioObra(user_id=user_supervisor.id, obra_id=obra.id))
    db.commit()
    assert user_visible_obra_ids(db, user_supervisor) == [obra.id]


def test_user_visible_obra_ids_supervisor_sin_filas(db, user_supervisor):
    assert user_visible_obra_ids(db, user_supervisor) is None  # sin filas = todas


def test_scope_obras_filtra_supervisor(db, user_supervisor, obra, cliente, regimen_ri):
    """scope_obras filtra la query a la whitelist."""
    from datetime import date

    obra2 = models.Obra(
        codigo="OTRA", nombre="Obra 2",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=500_000,
        fecha_inicio=date.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra2); db.commit(); db.refresh(obra2)

    # supervisor solo ve obra (no obra2)
    db.add(models.PermisoUsuarioObra(user_id=user_supervisor.id, obra_id=obra.id))
    db.commit()

    q = scope_obras(db.query(models.Obra), models.Obra, db, user_supervisor)
    ids = sorted([o.id for o in q.all()])
    assert ids == [obra.id]


def test_list_obras_endpoint_respeta_whitelist(
    client, db, headers_for, user_supervisor, obra, cliente, regimen_ri
):
    from datetime import date

    obra2 = models.Obra(
        codigo="ZTR", nombre="Obra fuera del scope",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA, monto_contrato=200_000,
        fecha_inicio=date.today(), estado=models.ObraStatus.EN_CURSO,
    )
    db.add(obra2); db.commit(); db.refresh(obra2)

    # supervisor ve solo `obra`
    db.add(models.PermisoUsuarioObra(user_id=user_supervisor.id, obra_id=obra.id))
    db.commit()

    r = client.get("/api/obras", headers=headers_for(user_supervisor))
    assert r.status_code == 200
    codigos = [o["codigo"] for o in r.json()]
    assert "TST" in codigos
    assert "ZTR" not in codigos


def test_me_permisos_endpoint(client, headers_for, user_supervisor):
    r = client.get("/api/users/me/permisos", headers=headers_for(user_supervisor))
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == user_supervisor.id
    assert set(data["secciones_permitidas"]) == set(models.SECCIONES)


def test_non_admin_no_puede_editar_permisos_de_otro(
    client, headers_for, user_supervisor, user_admin
):
    r = client.put(
        f"/api/users/{user_admin.id}/permisos",
        json={"secciones_permitidas": []},
        headers=headers_for(user_supervisor),
    )
    assert r.status_code == 403
