"""Matriz de permisos por rol (Sprint 7)."""
import pytest


# ─── usuario_bot bloqueado en cualquier endpoint web ─────────────────

def test_usuario_bot_no_accede_a_endpoints_web(client, user_bot, headers_for):
    """usuario_bot solo opera vía WhatsApp — toda llamada web devuelve 403."""
    h = headers_for(user_bot)
    for path in ["/api/obras", "/api/movimientos", "/api/socios", "/api/dashboard/hud", "/api/auth/me"]:
        r = client.get(path, headers=h)
        assert r.status_code == 403, f"{path} debería ser 403, fue {r.status_code}"
        assert "whatsapp" in r.json()["detail"].lower()


# ─── supervisor: lee obras, pero NO accede a finanzas/admin ──────────

def test_supervisor_lee_obras(client, user_supervisor, headers_for):
    r = client.get("/api/obras", headers=headers_for(user_supervisor))
    assert r.status_code == 200


def test_supervisor_no_crea_obra(client, user_supervisor, headers_for, regimen_ri, cliente):
    r = client.post("/api/obras", headers=headers_for(user_supervisor), json={
        "codigo": "X", "nombre": "X", "cliente_id": cliente.id,
        "tipo_facturacion": "MIXTA",
    })
    assert r.status_code == 403


def test_supervisor_no_accede_descalce_fiscal(client, user_supervisor, headers_for):
    r = client.get("/api/movimientos/descalce-fiscal", headers=headers_for(user_supervisor))
    assert r.status_code == 403


# ─── admin (PM): crea/edita pero no ve descalce ──────────────────────

def test_admin_pm_crea_obra(client, user_admin, headers_for, cliente):
    r = client.post("/api/obras", headers=headers_for(user_admin), json={
        "codigo": "PMTST", "nombre": "Test PM", "cliente_id": cliente.id,
        "tipo_facturacion": "MIXTA",
    })
    assert r.status_code == 201


def test_admin_pm_no_accede_descalce_fiscal(client, user_admin, headers_for):
    """admin (PM) NO está en FINANZAS_ROLES."""
    r = client.get("/api/movimientos/descalce-fiscal", headers=headers_for(user_admin))
    assert r.status_code == 403


# ─── admin_finanzas: SÍ accede a descalce ─────────────────────────────

def test_admin_finanzas_accede_descalce(client, user_admin_finanzas, headers_for):
    r = client.get("/api/movimientos/descalce-fiscal", headers=headers_for(user_admin_finanzas))
    assert r.status_code == 200


def test_admin_finanzas_crea_obra(client, user_admin_finanzas, headers_for, cliente):
    """admin_finanzas también está en ADMIN_ROLES, puede crear obras."""
    r = client.post("/api/obras", headers=headers_for(user_admin_finanzas), json={
        "codigo": "AF", "nombre": "Test AF", "cliente_id": cliente.id,
        "tipo_facturacion": "MIXTA",
    })
    assert r.status_code == 201


# ─── super_admin: acceso total ────────────────────────────────────────

def test_super_admin_accede_a_todo(client, auth_headers):
    """Fixture auth_headers usa el super_admin del fixture admin_user."""
    for path in ["/api/obras", "/api/movimientos", "/api/socios",
                 "/api/dashboard/hud", "/api/movimientos/descalce-fiscal", "/api/users"]:
        r = client.get(path, headers=auth_headers)
        assert r.status_code == 200, f"{path} debería ser 200 para super_admin, fue {r.status_code}"


# ─── CRUD socios ──────────────────────────────────────────────────────

def test_crud_socios(client, auth_headers, admin_user):
    # CREATE
    r = client.post("/api/socios", headers=auth_headers, json={
        "nombre": "Juan", "apellido": "Pérez", "cuit": "20-44444444-4",
        "participacion_pct": 50, "user_id": admin_user.id,
    })
    assert r.status_code == 201
    sid = r.json()["id"]

    # CUIT duplicado rechaza
    r2 = client.post("/api/socios", headers=auth_headers, json={
        "nombre": "Otro", "cuit": "20-44444444-4",
    })
    assert r2.status_code == 400
    assert "cuit" in r2.json()["detail"].lower()

    # READ
    r = client.get(f"/api/socios/{sid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Juan"

    # LIST
    r = client.get("/api/socios", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # UPDATE
    r = client.put(f"/api/socios/{sid}", headers=auth_headers, json={
        "nombre": "Juan", "apellido": "García", "participacion_pct": 60,
    })
    assert r.status_code == 200
    assert r.json()["apellido"] == "García"

    # DELETE
    r = client.delete(f"/api/socios/{sid}", headers=auth_headers)
    assert r.status_code == 204


def test_supervisor_lee_socios_pero_no_crea(client, user_supervisor, headers_for):
    r = client.get("/api/socios", headers=headers_for(user_supervisor))
    assert r.status_code == 200
    r2 = client.post("/api/socios", headers=headers_for(user_supervisor), json={"nombre": "X"})
    assert r2.status_code == 403


def test_borrar_socio_con_aportes_rechaza(client, auth_headers, obra, socio, db):
    # Crear aporte vinculado al socio
    from datetime import date
    r = client.post("/api/aportes", headers=auth_headers, json={
        "obra_id": obra.id, "socio_id": socio.id,
        "fecha_aporte": date.today().isoformat(),
        "monto": 100000, "motivo": "x", "medio_pago": "EFECTIVO",
    })
    assert r.status_code == 201
    # Intentar borrar el socio
    r = client.delete(f"/api/socios/{socio.id}", headers=auth_headers)
    assert r.status_code == 400
    assert "aporte" in r.json()["detail"].lower()
