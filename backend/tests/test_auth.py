"""Endpoints de auth + protección de rutas."""


def test_login_credenciales_correctas(client, admin_user):
    r = client.post("/api/auth/login", json={"email": admin_user.email, "password": "test1234"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == admin_user.email


def test_login_credenciales_incorrectas(client, admin_user):
    r = client.post("/api/auth/login", json={"email": admin_user.email, "password": "wrong"})
    assert r.status_code == 401


def test_login_email_inexistente(client):
    r = client.post("/api/auth/login", json={"email": "nadie@nada.com", "password": "x"})
    assert r.status_code == 401


def test_endpoint_protegido_sin_token(client):
    r = client.get("/api/obras")
    assert r.status_code == 401


def test_endpoint_protegido_con_token(client, auth_headers):
    r = client.get("/api/obras", headers=auth_headers)
    assert r.status_code == 200


def test_me_devuelve_usuario_logueado(client, auth_headers, admin_user):
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == admin_user.email
