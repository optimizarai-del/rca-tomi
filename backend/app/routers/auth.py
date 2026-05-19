from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import (
    hash_password, verify_password, create_access_token, get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email ya registrado")
    is_first = db.query(models.User).count() == 0
    role = models.UserRole.admin_finanzas if is_first else data.role
    user = models.User(
        name=data.name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=role,
        status=models.UserStatus.active,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Email o contraseña inválidos")
    if not user.is_active:
        raise HTTPException(403, "Usuario inactivo")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/demo-login", response_model=schemas.Token)
def demo_login(db: Session = Depends(get_db)):
    """Login express al perfil demo (Sprint 12).

    Busca/usa el usuario `demo@rca.com` con `is_demo=True`. No requiere pass.
    El usuario verá SOLO datos demo (filas con is_demo=True) — la base "real"
    queda intocada.
    """
    user = db.query(models.User).filter(
        models.User.email == "demo@rca.com",
        models.User.is_demo == True,  # noqa: E712
    ).first()
    if not user:
        raise HTTPException(
            503,
            "Modo demo no configurado. Pedile al admin que corra el seed o cree el usuario demo.",
        )
    if not user.is_active:
        raise HTTPException(403, "Usuario demo inactivo")
    token = create_access_token({"sub": str(user.id), "role": user.role.value, "demo": True})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.patch("/me/onboarding", response_model=schemas.UserOut)
def update_onboarding(
    step: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    user.onboarding_step = max(user.onboarding_step, min(step, 3))
    db.commit(); db.refresh(user)
    return user
