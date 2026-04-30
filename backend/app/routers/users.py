from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import require_admin, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    return db.query(models.User).filter(models.User.is_active == True).all()


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
