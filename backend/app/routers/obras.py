from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["obras"])


def _calcular_salud(obra: models.Obra, alertas: int, dias_restantes) -> models.ObraSalud:
    pct_pres = (obra.presupuesto_consumido / obra.presupuesto_total * 100) if obra.presupuesto_total else 0
    if alertas >= 5 or pct_pres > 110:
        return models.ObraSalud.critico
    if alertas >= 2 or pct_pres > 90 or (dias_restantes is not None and dias_restantes < 7):
        return models.ObraSalud.atencion
    return models.ObraSalud.optimo


def _refrescar_progreso(db: Session, obra: models.Obra):
    frentes = db.query(models.Frente).filter(models.Frente.obra_id == obra.id).all()
    if frentes:
        obra.progreso = sum(f.progreso for f in frentes) / len(frentes)
    db.commit()


@router.get("/obras", response_model=List[schemas.ObraOut])
def list_obras(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.query(models.Obra).order_by(models.Obra.created_at.desc()).all()


@router.post("/obras", response_model=schemas.ObraOut, status_code=201)
def create_obra(data: schemas.ObraIn, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    o = models.Obra(**data.model_dump())
    db.add(o); db.commit(); db.refresh(o)
    return o


@router.get("/obras/{oid}", response_model=schemas.ObraOut)
def get_obra(oid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    o = db.query(models.Obra).filter(models.Obra.id == oid).first()
    if not o: raise HTTPException(404, "Obra no encontrada")
    return o


@router.put("/obras/{oid}", response_model=schemas.ObraOut)
def update_obra(oid: int, data: schemas.ObraIn, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    o = db.query(models.Obra).filter(models.Obra.id == oid).first()
    if not o: raise HTTPException(404, "Obra no encontrada")
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    db.commit(); db.refresh(o)
    return o


@router.delete("/obras/{oid}", status_code=204)
def delete_obra(oid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    o = db.query(models.Obra).filter(models.Obra.id == oid).first()
    if not o: raise HTTPException(404, "Obra no encontrada")
    db.delete(o); db.commit()


@router.get("/obras/{oid}/dashboard", response_model=schemas.ObraDashboard)
def obra_dashboard(oid: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    o = db.query(models.Obra).filter(models.Obra.id == oid).first()
    if not o: raise HTTPException(404, "Obra no encontrada")

    frentes_total = db.query(models.Frente).filter(models.Frente.obra_id == oid).count()
    frentes_completados = db.query(models.Frente).filter(
        models.Frente.obra_id == oid, models.Frente.estado == models.FrenteEstado.completado
    ).count()
    cuadrillas_ids = [f.cuadrilla_id for f in db.query(models.Frente).filter(models.Frente.obra_id == oid).all() if f.cuadrilla_id]
    cuadrillas_activas = len(set(cuadrillas_ids))
    obreros_total = sum(c.cantidad_miembros for c in db.query(models.Cuadrilla).filter(
        models.Cuadrilla.id.in_(cuadrillas_ids)
    ).all()) if cuadrillas_ids else 0

    eventos_recientes = db.query(models.Evento).filter(models.Evento.obra_id == oid).count()
    alertas = db.query(models.Evento).filter(
        models.Evento.obra_id == oid, models.Evento.es_critico == True
    ).count()
    ordenes_pendientes = db.query(models.OrdenTrabajo).filter(
        models.OrdenTrabajo.obra_id == oid,
        models.OrdenTrabajo.status.in_([models.TaskStatus.pendiente, models.TaskStatus.en_progreso])
    ).count()

    pct = (o.presupuesto_consumido / o.presupuesto_total * 100) if o.presupuesto_total else 0
    dias_rest = None
    if o.fecha_fin_estimada:
        dias_rest = (o.fecha_fin_estimada - date.today()).days

    o.salud = _calcular_salud(o, alertas, dias_rest)
    db.commit()

    return schemas.ObraDashboard(
        obra=schemas.ObraOut.model_validate(o),
        frentes_total=frentes_total,
        frentes_completados=frentes_completados,
        cuadrillas_activas=cuadrillas_activas,
        obreros_total=obreros_total,
        eventos_recientes=eventos_recientes,
        alertas=alertas,
        ordenes_pendientes=ordenes_pendientes,
        presupuesto_pct=pct,
        dias_restantes=dias_rest,
    )


# ─── Frentes ───
@router.get("/frentes", response_model=List[schemas.FrenteOut])
def list_frentes(obra_id: int = None, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    q = db.query(models.Frente)
    if obra_id: q = q.filter(models.Frente.obra_id == obra_id)
    return q.all()


@router.post("/frentes", response_model=schemas.FrenteOut, status_code=201)
def create_frente(data: schemas.FrenteIn, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    f = models.Frente(**data.model_dump())
    db.add(f); db.commit(); db.refresh(f)
    obra = db.query(models.Obra).filter(models.Obra.id == data.obra_id).first()
    if obra: _refrescar_progreso(db, obra)
    return f


@router.patch("/frentes/{fid}", response_model=schemas.FrenteOut)
def update_frente(fid: int, data: schemas.FrenteIn, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    f = db.query(models.Frente).filter(models.Frente.id == fid).first()
    if not f: raise HTTPException(404, "Frente no encontrado")
    for k, v in data.model_dump().items():
        setattr(f, k, v)
    if data.progreso >= 100:
        f.estado = models.FrenteEstado.completado
    db.commit(); db.refresh(f)
    obra = db.query(models.Obra).filter(models.Obra.id == f.obra_id).first()
    if obra: _refrescar_progreso(db, obra)
    return f


@router.delete("/frentes/{fid}", status_code=204)
def delete_frente(fid: int, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    f = db.query(models.Frente).filter(models.Frente.id == fid).first()
    if not f: raise HTTPException(404, "Frente no encontrado")
    obra_id = f.obra_id
    db.delete(f); db.commit()
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if obra: _refrescar_progreso(db, obra)
