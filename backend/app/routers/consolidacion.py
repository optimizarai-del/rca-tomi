"""Sprint 23 — Consolidación bancaria: importar extractos y matchear con movimientos."""
from __future__ import annotations
import hashlib
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, require_finanzas, scope_demo, stamp_demo

router = APIRouter(prefix="/api/extractos", tags=["consolidacion-bancaria"])


def _hash_mov(fecha: date, descripcion: str, debito: float, credito: float) -> str:
    raw = f"{fecha.isoformat()}|{descripcion.strip().lower()}|{debito:.2f}|{credito:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.get("", response_model=List[schemas.ExtractoOut])
def list_extractos(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    q = scope_demo(db.query(models.Extracto), models.Extracto, user)
    return q.order_by(models.Extracto.created_at.desc()).limit(200).all()


@router.post("", response_model=schemas.ExtractoOut, status_code=201)
def create_extracto(
    data: schemas.ExtractoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    if not data.movimientos:
        raise HTTPException(400, "El extracto debe tener al menos un movimiento")

    total_debe = sum(m.debito or 0 for m in data.movimientos)
    total_haber = sum(m.credito or 0 for m in data.movimientos)

    extracto = models.Extracto(
        banco=data.banco.strip(),
        cuenta=(data.cuenta or "").strip() or None,
        periodo_desde=data.periodo_desde,
        periodo_hasta=data.periodo_hasta,
        archivo_nombre=data.archivo_nombre,
        total_debe=total_debe,
        total_haber=total_haber,
        total_movs=len(data.movimientos),
        created_by_id=user.id,
    )
    stamp_demo(extracto, user)
    db.add(extracto); db.flush()

    # Dedupe por hash dentro del extracto (no global — distintos extractos pueden tener
    # mismas líneas si se reimporta un periodo).
    seen_hashes = set()
    creados = 0
    for m in data.movimientos:
        h = _hash_mov(m.fecha, m.descripcion, m.debito or 0, m.credito or 0)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        mb = models.MovimientoBancario(
            extracto_id=extracto.id,
            fecha=m.fecha,
            descripcion=m.descripcion.strip()[:500],
            debito=m.debito or 0,
            credito=m.credito or 0,
            saldo=m.saldo,
            hash_dedupe=h,
        )
        stamp_demo(mb, user)
        db.add(mb); creados += 1

    extracto.total_movs = creados
    db.commit(); db.refresh(extracto)
    return extracto


@router.get("/{eid}", response_model=schemas.ExtractoDetalleOut)
def get_extracto(
    eid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    e = scope_demo(db.query(models.Extracto), models.Extracto, user).filter(
        models.Extracto.id == eid
    ).first()
    if not e:
        raise HTTPException(404, "Extracto no encontrado")
    movs = db.query(models.MovimientoBancario).filter(
        models.MovimientoBancario.extracto_id == eid
    ).order_by(models.MovimientoBancario.fecha, models.MovimientoBancario.id).all()
    base = schemas.ExtractoOut.model_validate(e)
    return schemas.ExtractoDetalleOut(
        **base.model_dump(),
        movimientos=[schemas.MovimientoBancarioOut.model_validate(m) for m in movs],
    )


@router.delete("/{eid}", status_code=204)
def delete_extracto(
    eid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    e = db.query(models.Extracto).filter(models.Extracto.id == eid).first()
    if not e:
        raise HTTPException(404, "Extracto no encontrado")
    db.delete(e); db.commit()


@router.get("/{eid}/sugerencias", response_model=List[schemas.MovimientoBancarioConSugerenciasOut])
def sugerencias_match(
    eid: int,
    tolerancia_dias: int = 7,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    """Para cada movimiento bancario sin match, propone movimientos_obra con mismo
    monto (debe→EGRESO, haber→INGRESO) dentro de ±N días.
    """
    e = scope_demo(db.query(models.Extracto), models.Extracto, user).filter(
        models.Extracto.id == eid
    ).first()
    if not e:
        raise HTTPException(404, "Extracto no encontrado")

    movs_banco = db.query(models.MovimientoBancario).filter(
        models.MovimientoBancario.extracto_id == eid,
    ).all()

    out: List[schemas.MovimientoBancarioConSugerenciasOut] = []
    for mb in movs_banco:
        sugerencias: List[schemas.SugerenciaMatchOut] = []
        if mb.movimiento_obra_id is None:
            monto = float(mb.debito or 0) or float(mb.credito or 0)
            tipo = models.TipoMovimiento.EGRESO if float(mb.debito or 0) > 0 else models.TipoMovimiento.INGRESO
            f_min = mb.fecha - timedelta(days=tolerancia_dias)
            f_max = mb.fecha + timedelta(days=tolerancia_dias)
            candidatos = db.query(models.MovimientoObra).join(
                models.Obra, models.MovimientoObra.obra_id == models.Obra.id,
            ).filter(
                models.MovimientoObra.tipo == tipo,
                models.MovimientoObra.monto == monto,
                models.MovimientoObra.fecha >= f_min,
                models.MovimientoObra.fecha <= f_max,
                ~models.MovimientoObra.id.in_(
                    db.query(models.MovimientoBancario.movimiento_obra_id).filter(
                        models.MovimientoBancario.movimiento_obra_id.isnot(None),
                    )
                ),
            ).limit(5).all()
            for mo in candidatos:
                obra = db.query(models.Obra).filter(models.Obra.id == mo.obra_id).first()
                sugerencias.append(schemas.SugerenciaMatchOut(
                    movimiento_obra_id=mo.id,
                    obra_codigo=obra.codigo if obra else "—",
                    concepto=mo.concepto,
                    fecha=mo.fecha,
                    monto=float(mo.monto),
                    tipo=mo.tipo,
                    distancia_dias=abs((mo.fecha - mb.fecha).days),
                ))
            sugerencias.sort(key=lambda s: (s.distancia_dias, s.movimiento_obra_id))
        base = schemas.MovimientoBancarioOut.model_validate(mb)
        out.append(schemas.MovimientoBancarioConSugerenciasOut(
            **base.model_dump(),
            sugerencias=sugerencias,
        ))
    return out


@router.get("/{eid}/consolidacion", response_model=schemas.ConsolidacionResumen)
def resumen_consolidacion(
    eid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    e = scope_demo(db.query(models.Extracto), models.Extracto, user).filter(
        models.Extracto.id == eid
    ).first()
    if not e:
        raise HTTPException(404, "Extracto no encontrado")

    movs = db.query(models.MovimientoBancario).filter(
        models.MovimientoBancario.extracto_id == eid,
    ).all()
    debe_conc = 0.0
    haber_conc = 0.0
    conciliados = 0
    for mb in movs:
        if mb.movimiento_obra_id:
            conciliados += 1
            mo = db.query(models.MovimientoObra).filter(
                models.MovimientoObra.id == mb.movimiento_obra_id,
            ).first()
            if not mo:
                continue
            if mo.tipo == models.TipoMovimiento.EGRESO:
                debe_conc += float(mo.monto)
            else:
                haber_conc += float(mo.monto)
    return schemas.ConsolidacionResumen(
        extracto_id=eid,
        total_debe_extracto=float(e.total_debe or 0),
        total_haber_extracto=float(e.total_haber or 0),
        total_debe_obra_conciliado=round(debe_conc, 2),
        total_haber_obra_conciliado=round(haber_conc, 2),
        diferencia_debe=round(float(e.total_debe or 0) - debe_conc, 2),
        diferencia_haber=round(float(e.total_haber or 0) - haber_conc, 2),
        movs_total=len(movs),
        movs_conciliados=conciliados,
        movs_sin_match=len(movs) - conciliados,
    )


# ─── Endpoints sobre movimientos individuales ────────────────────────────


mov_router = APIRouter(prefix="/api/movimientos-bancarios", tags=["consolidacion-bancaria"])


@mov_router.post("/{mbid}/match", response_model=schemas.MovimientoBancarioOut)
def match_movimiento(
    mbid: int,
    data: schemas.MatchIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    mb = db.query(models.MovimientoBancario).filter(models.MovimientoBancario.id == mbid).first()
    if not mb:
        raise HTTPException(404, "Movimiento bancario no encontrado")

    mo = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.id == data.movimiento_obra_id
    ).first()
    if not mo:
        raise HTTPException(400, "MovimientoObra no encontrado")

    # No matchear dos movs bancarios al mismo movimiento de obra
    ya = db.query(models.MovimientoBancario).filter(
        models.MovimientoBancario.movimiento_obra_id == mo.id,
        models.MovimientoBancario.id != mbid,
    ).first()
    if ya:
        raise HTTPException(400, f"El movimiento de obra {mo.id} ya está conciliado con #{ya.id}")

    mb.movimiento_obra_id = mo.id
    mb.conciliado_at = datetime.utcnow()
    mb.conciliado_by_id = user.id
    db.commit(); db.refresh(mb)
    return mb


@mov_router.delete("/{mbid}/match", response_model=schemas.MovimientoBancarioOut)
def desvincular_match(
    mbid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    mb = db.query(models.MovimientoBancario).filter(models.MovimientoBancario.id == mbid).first()
    if not mb:
        raise HTTPException(404, "Movimiento bancario no encontrado")
    mb.movimiento_obra_id = None
    mb.conciliado_at = None
    mb.conciliado_by_id = None
    db.commit(); db.refresh(mb)
    return mb
