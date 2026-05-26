"""Sprint 24 — endpoints de planificación de obra asistida por IA."""
from __future__ import annotations
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, scope_obras, stamp_demo
from app import plan_obra as plan_service

router = APIRouter(prefix="/api/obras", tags=["plan-obra"])


def _serialize_borrador(b: models.PlanObraBorrador) -> schemas.PlanObraBorradorOut:
    """Deserializa el resultado_json en estructura tipada."""
    try:
        data = json.loads(b.resultado_json)
    except (TypeError, ValueError):
        data = {}
    return schemas.PlanObraBorradorOut(
        id=b.id, obra_id=b.obra_id,
        prompt_input=b.prompt_input,
        resultado=schemas.PlanObraResultado.model_validate(data),
        estado=b.estado, model_used=b.model_used,
        created_by_id=b.created_by_id, created_at=b.created_at,
        aplicado_at=b.aplicado_at,
    )


def _validar_acceso_obra(db: Session, user: models.User, oid: int) -> models.Obra:
    q = scope_demo(db.query(models.Obra), models.Obra, user)
    q = scope_obras(q, models.Obra, db, user)
    obra = q.filter(models.Obra.id == oid).first()
    if not obra:
        raise HTTPException(404, "Obra no encontrada")
    return obra


@router.post("/{oid}/plan/generar", response_model=schemas.PlanObraBorradorOut, status_code=201)
def generar_plan(
    oid: int,
    data: schemas.PlanObraGenerarIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Genera un nuevo borrador. Si no hay ANTHROPIC_API_KEY usa un plan placeholder
    determinístico — el front debería mostrar el `model_used` para diferenciar.
    """
    obra = _validar_acceso_obra(db, user, oid)
    borrador = plan_service.generar_plan(
        db, obra=obra, contexto=data.contexto, user_id=user.id,
        model_override=data.model_override,
    )
    stamp_demo(borrador, user)
    db.commit(); db.refresh(borrador)
    return _serialize_borrador(borrador)


@router.get("/{oid}/plan", response_model=List[schemas.PlanObraBorradorOut])
def listar_borradores(
    oid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    obra = _validar_acceso_obra(db, user, oid)
    borradores = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.obra_id == oid
    ).order_by(models.PlanObraBorrador.created_at.desc(), models.PlanObraBorrador.id.desc()).all()
    return [_serialize_borrador(b) for b in borradores]


@router.get("/{oid}/plan/{plan_id}", response_model=schemas.PlanObraBorradorOut)
def get_borrador(
    oid: int,
    plan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    obra = _validar_acceso_obra(db, user, oid)
    b = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.id == plan_id,
        models.PlanObraBorrador.obra_id == oid,
    ).first()
    if not b:
        raise HTTPException(404, "Borrador no encontrado")
    return _serialize_borrador(b)


@router.put("/{oid}/plan/{plan_id}", response_model=schemas.PlanObraBorradorOut)
def editar_borrador(
    oid: int,
    plan_id: int,
    data: schemas.PlanObraEditIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Edita el resultado del borrador antes de aplicarlo. Solo si está en estado borrador."""
    _validar_acceso_obra(db, user, oid)
    b = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.id == plan_id,
        models.PlanObraBorrador.obra_id == oid,
    ).first()
    if not b:
        raise HTTPException(404, "Borrador no encontrado")
    if b.estado != models.PlanObraEstado.borrador:
        raise HTTPException(400, f"Solo se puede editar un borrador en estado 'borrador' (actual: {b.estado.value})")
    b.resultado_json = data.resultado.model_dump_json()
    db.commit(); db.refresh(b)
    return _serialize_borrador(b)


@router.post("/{oid}/plan/{plan_id}/aplicar", response_model=schemas.PlanObraAplicarOut)
def aplicar_borrador(
    oid: int,
    plan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Crea EtapaObra y Frente reales basados en el borrador."""
    _validar_acceso_obra(db, user, oid)
    b = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.id == plan_id,
        models.PlanObraBorrador.obra_id == oid,
    ).first()
    if not b:
        raise HTTPException(404, "Borrador no encontrado")
    try:
        resumen = plan_service.aplicar_plan(db, b)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PlanObraAplicarOut(**resumen)


@router.post("/{oid}/plan/{plan_id}/descartar", response_model=schemas.PlanObraBorradorOut)
def descartar_borrador(
    oid: int,
    plan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    _validar_acceso_obra(db, user, oid)
    b = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.id == plan_id,
        models.PlanObraBorrador.obra_id == oid,
    ).first()
    if not b:
        raise HTTPException(404, "Borrador no encontrado")
    if b.estado != models.PlanObraEstado.borrador:
        raise HTTPException(400, f"Solo se puede descartar un borrador (actual: {b.estado.value})")
    b.estado = models.PlanObraEstado.descartado
    db.commit(); db.refresh(b)
    return _serialize_borrador(b)


@router.delete("/{oid}/plan/{plan_id}", status_code=204)
def borrar_borrador(
    oid: int,
    plan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Hard delete — útil para limpiar borradores descartados o duplicados."""
    _validar_acceso_obra(db, user, oid)
    b = db.query(models.PlanObraBorrador).filter(
        models.PlanObraBorrador.id == plan_id,
        models.PlanObraBorrador.obra_id == oid,
    ).first()
    if not b:
        raise HTTPException(404, "Borrador no encontrado")
    db.delete(b); db.commit()
