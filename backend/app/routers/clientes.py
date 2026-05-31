"""Router de Clientes — entidades con régimen fiscal heredable a obras.

Sprint 22 — Memoria de cliente: además del CRUD básico expone:
- GET /api/clientes/{cid}/detalle — perfil + obras + agregados financieros + notas
- CRUD de notas (ClienteNota) — historial de interacciones
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/clientes", tags=["clientes"])


@router.get("", response_model=List[schemas.ClienteOut])
def list_clientes(
    activos_solo: bool = True,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.Cliente)
    q = scope_demo(q, models.Cliente, user)
    if activos_solo:
        q = q.filter(models.Cliente.activo == True)  # noqa: E712
    return q.order_by(models.Cliente.nombre).all()


@router.post("", response_model=schemas.ClienteOut, status_code=201)
def create_cliente(
    data: schemas.ClienteIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    if data.regimen_fiscal_id:
        rf = db.query(models.RegimenFiscal).filter(models.RegimenFiscal.id == data.regimen_fiscal_id).first()
        if not rf:
            raise HTTPException(400, "Régimen fiscal no existe")
    c = models.Cliente(**data.model_dump())
    stamp_demo(c, user)
    db.add(c); db.commit(); db.refresh(c)
    return c


# ─── Sprint 22: detalle + notas (paths fijos antes de /{cid}) ───────────


def _calcular_resumen(db: Session, cliente_id: int) -> schemas.ClienteResumenFinanciero:
    obras = db.query(models.Obra).filter(models.Obra.cliente_id == cliente_id).all()
    obra_ids = [o.id for o in obras]
    resumen = schemas.ClienteResumenFinanciero(
        obras_total=len(obras),
        obras_en_curso=sum(1 for o in obras if o.estado == models.ObraStatus.EN_CURSO),
        obras_finalizadas=sum(1 for o in obras if o.estado == models.ObraStatus.FINALIZADA),
        monto_contratos_total=sum(float(o.monto_contrato or 0) for o in obras),
    )
    if not obra_ids:
        return resumen

    rows = db.query(
        models.MovimientoObra.tipo,
        models.MovimientoObra.cobro_pago_estado,
        func.coalesce(func.sum(models.MovimientoObra.monto), 0),
    ).filter(
        models.MovimientoObra.obra_id.in_(obra_ids)
    ).group_by(
        models.MovimientoObra.tipo, models.MovimientoObra.cobro_pago_estado,
    ).all()

    for tipo, estado, total in rows:
        monto = float(total or 0)
        if tipo == models.TipoMovimiento.INGRESO:
            if estado == models.CobroPagoEstado.cobrado:
                resumen.ingresos_cobrado_total += monto
            else:
                resumen.ingresos_pendiente_total += monto
        else:  # EGRESO
            if estado == models.CobroPagoEstado.pagado:
                resumen.egresos_pagado_total += monto
            else:
                resumen.egresos_pendiente_total += monto
    return resumen


def _obras_resumen(db: Session, cliente_id: int) -> List[schemas.ClienteObraResumen]:
    obras = db.query(models.Obra).filter(
        models.Obra.cliente_id == cliente_id
    ).order_by(models.Obra.created_at.desc()).all()

    out = []
    for o in obras:
        ing_cob = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
            models.MovimientoObra.obra_id == o.id,
            models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO,
            models.MovimientoObra.cobro_pago_estado == models.CobroPagoEstado.cobrado,
        ).scalar() or 0
        ing_pen = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
            models.MovimientoObra.obra_id == o.id,
            models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO,
            models.MovimientoObra.cobro_pago_estado == models.CobroPagoEstado.pendiente,
        ).scalar() or 0
        egr_pag = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
            models.MovimientoObra.obra_id == o.id,
            models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO,
            models.MovimientoObra.cobro_pago_estado == models.CobroPagoEstado.pagado,
        ).scalar() or 0
        out.append(schemas.ClienteObraResumen(
            id=o.id, codigo=o.codigo, nombre=o.nombre, estado=o.estado,
            monto_contrato=float(o.monto_contrato or 0),
            fecha_inicio=o.fecha_inicio, fecha_fin_estimada=o.fecha_fin_estimada,
            progreso=float(o.progreso or 0),
            ingresos_cobrado=float(ing_cob),
            ingresos_pendiente=float(ing_pen),
            saldo_obra=float(ing_cob) - float(egr_pag),
        ))
    return out


@router.get("/{cid}/detalle", response_model=schemas.ClienteDetalleOut)
def detalle_cliente(
    cid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    c = scope_demo(db.query(models.Cliente), models.Cliente, user).filter(
        models.Cliente.id == cid
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")

    notas = db.query(models.ClienteNota).filter(
        models.ClienteNota.cliente_id == cid
    ).order_by(models.ClienteNota.created_at.desc(), models.ClienteNota.id.desc()).limit(50).all()

    base = schemas.ClienteOut.model_validate(c)
    return schemas.ClienteDetalleOut(
        **base.model_dump(),
        obras=_obras_resumen(db, cid),
        resumen_financiero=_calcular_resumen(db, cid),
        interacciones=[schemas.ClienteNotaOut.model_validate(n) for n in notas],
    )


@router.get("/{cid}/notas", response_model=List[schemas.ClienteNotaOut])
def list_notas(
    cid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    c = scope_demo(db.query(models.Cliente), models.Cliente, user).filter(
        models.Cliente.id == cid
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return db.query(models.ClienteNota).filter(
        models.ClienteNota.cliente_id == cid
    ).order_by(models.ClienteNota.created_at.desc(), models.ClienteNota.id.desc()).all()


@router.post("/{cid}/notas", response_model=schemas.ClienteNotaOut, status_code=201)
def crear_nota(
    cid: int,
    data: schemas.ClienteNotaIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    c = scope_demo(db.query(models.Cliente), models.Cliente, user).filter(
        models.Cliente.id == cid
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    if data.cliente_id != cid:
        raise HTTPException(400, "cliente_id del body no coincide con el path")
    nota = models.ClienteNota(
        cliente_id=cid, texto=data.texto.strip(),
        importante=data.importante, autor_id=user.id,
    )
    stamp_demo(nota, user)
    # Marcar interacción
    c.last_interaction_at = datetime.utcnow()
    db.add(nota); db.commit(); db.refresh(nota)
    return nota


@router.delete("/notas/{nid}", status_code=204)
def borrar_nota(
    nid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    n = db.query(models.ClienteNota).filter(models.ClienteNota.id == nid).first()
    if not n:
        raise HTTPException(404, "Nota no encontrada")
    db.delete(n); db.commit()


@router.get("/{cid}", response_model=schemas.ClienteOut)
def get_cliente(cid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return c


@router.put("/{cid}", response_model=schemas.ClienteOut)
def update_cliente(
    cid: int,
    data: schemas.ClienteIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return c


@router.delete("/{cid}", status_code=204)
def delete_cliente(cid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    c = db.query(models.Cliente).filter(models.Cliente.id == cid).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    if c.obras:
        raise HTTPException(400, f"No se puede borrar: tiene {len(c.obras)} obras asociadas. Marcalo como inactivo.")
    db.delete(c); db.commit()
