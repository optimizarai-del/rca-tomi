"""Fixtures comunes para los tests.

- `db` → SQLAlchemy Session con SQLite en memoria, schema creado vía `Base.metadata.create_all`.
- `client` → TestClient de FastAPI con `app` real y dependencia `get_db` overrideada para usar `db`.
- `admin_user` → User super_admin de seed (admin@rca.com / demo1234).
- `auth_token` → JWT del admin.
- `auth_headers` → dict listo para usar en `client.get(..., headers=auth_headers)`.

NO usa la DB de desarrollo (`fielddata.db`). Cada test arranca con DB limpia.
"""
import os
import sys
from pathlib import Path

# Asegurar que importamos desde backend/
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Forzar SQLite in-memory para todos los tests, ANTES de importar app.database
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-fixed"
os.environ.setdefault("WHATSAPP_PROVIDER", "log_only")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app import models
from app.security import hash_password, create_access_token


@pytest.fixture()
def db():
    """SQLite in-memory por test. Una sola conexión compartida (StaticPool) así :memory: persiste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def admin_user(db):
    """Crea un super_admin testable."""
    u = models.User(
        name="Admin", last_name="Test", email="admin@test.com",
        phone="+5491100000001", password_hash=hash_password("test1234"),
        role=models.UserRole.super_admin, status=models.UserStatus.active,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def regimen_ri(db):
    r = models.RegimenFiscal(codigo="RI", nombre="Responsable Inscripto", iva_default=0.21)
    db.add(r); db.commit(); db.refresh(r)
    return r


@pytest.fixture()
def cliente(db, regimen_ri):
    c = models.Cliente(nombre="Cliente Test", cuit="30-12345678-9", tipo="privado_ri", regimen_fiscal_id=regimen_ri.id)
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.fixture()
def obra(db, cliente, regimen_ri):
    from datetime import date, timedelta
    o = models.Obra(
        codigo="TST", nombre="Obra Test",
        cliente_id=cliente.id, regimen_fiscal_id=regimen_ri.id,
        tipo_facturacion=models.TipoFacturacion.MIXTA,
        monto_contrato=1_000_000,
        fecha_inicio=date.today() - timedelta(days=10),
        estado=models.ObraStatus.EN_CURSO,
    )
    db.add(o); db.commit(); db.refresh(o)
    return o


@pytest.fixture()
def client(db, admin_user):
    """TestClient con DB overrideada al fixture `db`."""
    def _get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_token(admin_user):
    return create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
