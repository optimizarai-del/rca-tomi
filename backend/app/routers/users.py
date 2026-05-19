import secrets
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import require_admin, hash_password, scope_demo, stamp_demo

router = APIRouter(prefix="/api/users", tags=["users"])

VINCULACION_TTL_MIN = 15  # el código del Telegram link expira en 15 minutos


@router.get("", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    return scope_demo(db.query(models.User), models.User, user).filter(models.User.is_active == True).all()


@router.post("/invite", response_model=schemas.UserOut, status_code=201)
def invite(
    data: schemas.UserCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email ya registrado")
    if data.role == models.UserRole.admin_finanzas and actor.role != models.UserRole.admin_finanzas:
        raise HTTPException(403, "Solo admin_finanzas puede asignar ese rol")
    user = models.User(
        name=data.name, last_name=data.last_name, email=data.email, phone=data.phone,
        password_hash=hash_password(data.password), role=data.role,
        status=models.UserStatus.active,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@router.patch("/{uid}/role", response_model=schemas.UserOut)
def update_role(
    uid: int, data: schemas.UserRoleUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if data.role == models.UserRole.admin_finanzas and actor.role != models.UserRole.admin_finanzas:
        raise HTTPException(403, "Sin permisos")
    user.role = data.role
    db.commit(); db.refresh(user)
    return user


@router.delete("/{uid}", status_code=204)
def deactivate(uid: int, db: Session = Depends(get_db), actor: models.User = Depends(require_admin)):
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.id == actor.id:
        raise HTTPException(400, "No podés desactivarte")
    user.is_active = False
    db.commit()


# ─── Sprint 11 — Vinculación con Telegram ──────────────────────────────────

@router.post("/{uid}/telegram/generate-code")
def telegram_generate_code(
    uid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Genera un código de un solo uso para que el user mande /vincular <code> al bot.

    El código expira en 15 minutos. Mientras tanto, la fila User tiene
    `telegram_vinculacion_code` y `telegram_vinculacion_exp` seteadas.
    """
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    # 6 dígitos numéricos — fácil de tipear en el celular
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    user.telegram_vinculacion_code = code
    user.telegram_vinculacion_exp = datetime.utcnow() + timedelta(minutes=VINCULACION_TTL_MIN)
    db.commit()
    return {
        "ok": True,
        "code": code,
        "expires_in_minutes": VINCULACION_TTL_MIN,
        "instructions": f"Pedile al usuario que abra el bot y mande:  /vincular {code}",
    }


@router.delete("/{uid}/telegram", status_code=204)
def telegram_unlink(
    uid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Desvincula el chat de Telegram del usuario."""
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    user.telegram_chat_id = None
    user.telegram_username = None
    user.telegram_vinculacion_code = None
    user.telegram_vinculacion_exp = None
    db.commit()
