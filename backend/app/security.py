import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

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
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise cred_exc
    # Sprint 7: usuario_bot solo puede entrar vía WhatsApp, no por la web
    if user.role in WEB_BLOCKED_ROLES:
        raise HTTPException(403, "Este rol solo opera vía WhatsApp, no tiene acceso web")
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
