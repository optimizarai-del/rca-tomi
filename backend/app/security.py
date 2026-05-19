import os
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import event
from sqlalchemy.orm import Session, Query
from app.database import get_db
from app import models


# ─── Sprint 12: scoping dual demo/real via ContextVar ──────────────────
# get_current_user setea este context var con el scope is_demo del usuario.
# El event listener de SQLAlchemy abajo lo lee y agrega un filter automatico
# a TODA query sobre tablas que tengan la columna is_demo.
# Si el ContextVar es None (request sin usuario, scripts, seed), no filtra.
_current_user_demo: ContextVar[Optional[bool]] = ContextVar(
    "_current_user_demo", default=None,
)


def get_demo_scope() -> Optional[bool]:
    """Devuelve el scope is_demo de la request actual, o None si no hay user."""
    return _current_user_demo.get()


def set_demo_scope(value: Optional[bool]) -> None:
    _current_user_demo.set(value)


@event.listens_for(Query, "before_compile", retval=True)
def _demo_scope_filter(query):  # pragma: no cover
    """Inyecta filter is_demo en cualquier query sobre tablas con esa columna."""
    demo = _current_user_demo.get()
    if demo is None:
        return query
    for column_desc in query.column_descriptions:
        entity = column_desc.get("entity")
        if entity is not None and hasattr(entity, "is_demo"):
            query = query.filter(entity.is_demo == demo)
    return query


# ─── Auto-stamp is_demo en INSERTs ──────────────────────────────────────
# Para cualquier entidad nueva insertada durante un request con scope demo,
# heredar is_demo=True del scope si no se especificó explícitamente.
# Usamos Session.before_flush porque event.listens_for(Mapper, ...) requiere
# instancias de mapper, no la clase.
_DEMO_TABLES = {
    "users", "clientes", "obras", "etapas_obra", "movimientos_obra",
    "socios", "aportes_socios", "comprobantes", "notas_obra",
    "frentes", "cuadrillas", "materiales", "proveedores",
    "ordenes_trabajo", "eventos",
}


@event.listens_for(Session, "before_flush")
def _demo_stamp_before_flush(session, flush_context, instances):  # pragma: no cover
    """Solo marca is_demo=True en inserts nuevos cuando el scope activo es True.
    Cuando el scope es False o None, no escribimos nada (preservamos lo que
    haya seteado el caller, default False)."""
    demo = _current_user_demo.get()
    if demo is not True:
        return
    for obj in session.new:
        if not hasattr(obj, "is_demo"):
            continue
        tablename = getattr(obj, "__tablename__", "")
        if tablename not in _DEMO_TABLES:
            continue
        if not obj.is_demo:
            obj.is_demo = True

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ─── Matriz de permisos (Sprint 7) ──────────────────────────────────
# Cada constante define el conjunto de roles autorizados a una capacidad.
# Composición: super_admin entra a TODO; cada rol agrega su scope específico.

ADMIN_ROLES = {
    models.UserRole.super_admin,
    models.UserRole.admin,
    models.UserRole.admin_finanzas,
}
"""Acceso administrativo: ver/editar recursos, invitar usuarios."""

FINANZAS_ROLES = {
    models.UserRole.super_admin,
    models.UserRole.admin_finanzas,
}
"""Acceso a finanzas detalladas: movimientos confidenciales, descalce, comprobantes."""

SUPERVISOR_ROLES = {
    models.UserRole.super_admin,
    models.UserRole.admin,
    models.UserRole.admin_finanzas,
    models.UserRole.supervisor,
}
"""Acceso operativo: cargar movimientos básicos, reportar avance, ver obras asignadas."""

# Roles que NUNCA acceden a endpoints web — solo entran vía WhatsApp
WEB_BLOCKED_ROLES = {
    models.UserRole.usuario_bot,
}


def hash_password(p: str) -> str:
    return pwd_context.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd_context.verify(p, h)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise cred_exc
    # Bypass del scoping para resolver el usuario (sino entrariamos en loop
    # cuando el demo busca su propio user).
    _previous = _current_user_demo.get()
    _current_user_demo.set(None)
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
    finally:
        _current_user_demo.set(_previous)
    if not user or not user.is_active:
        raise cred_exc
    # Sprint 7: usuario_bot solo puede entrar vía WhatsApp, no por la web
    if user.role in WEB_BLOCKED_ROLES:
        raise HTTPException(403, "Este rol solo opera vía WhatsApp, no tiene acceso web")
    # Sprint 12: setear el scope para que TODAS las queries posteriores
    # de este request se filtren automáticamente por is_demo.
    _current_user_demo.set(bool(getattr(user, "is_demo", False)))
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role not in ADMIN_ROLES:
        raise HTTPException(403, "Requiere rol administrador")
    return user


def require_finanzas(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role not in FINANZAS_ROLES:
        raise HTTPException(403, "Requiere acceso a finanzas")
    return user


def require_supervisor(user: models.User = Depends(get_current_user)) -> models.User:
    """Permite supervisor + admin + admin_finanzas + super_admin."""
    if user.role not in SUPERVISOR_ROLES:
        raise HTTPException(403, "Requiere rol supervisor o superior")
    return user


def scope_demo(query, model, user: "models.User"):
    """Filtra una query por is_demo según el scope del usuario.

    Sprint 12: usuarios `is_demo=True` solo ven filas `is_demo=True`;
    usuarios `is_demo=False` (reales) solo ven filas `is_demo=False`.
    Si el modelo no tiene `is_demo`, la query queda intacta.
    """
    if hasattr(model, "is_demo"):
        return query.filter(model.is_demo == bool(user.is_demo))
    return query


def stamp_demo(obj, user: "models.User"):
    """Setea obj.is_demo según el usuario antes de persistir."""
    if hasattr(obj, "is_demo"):
        obj.is_demo = bool(user.is_demo)
    return obj


def require_role(*allowed_roles: models.UserRole):
    """Factory de dependency para gatear endpoints por roles específicos.

    Uso:
        @router.get("/secreto", dependencies=[Depends(require_role(UserRole.super_admin))])
    """
    allowed = set(allowed_roles)

    def _dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in allowed:
            names = ", ".join(r.value for r in allowed)
            raise HTTPException(403, f"Requiere uno de los roles: {names}")
        return user

    return _dep
