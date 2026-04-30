from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/hud", response_model=schemas.HudGlobal)
def hud(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    obras = db.query(models.Obra).all()
    pres_total = sum(o.presupuesto_total or 0 for o in obras)
    pres_consumido = sum(o.presupuesto_consumido or 0 for o in obras)
    obras_activas = sum(1 for o in obras if o.status == models.ObraStatus.en_obra)

    materiales = db.query(models.Material).all()
    mat_total = len(materiales)
    mat_criticos = sum(1 for m in materiales if (m.stock or 0) <= (m.stock_minimo or 0))

    cuadrillas = db.query(models.Cuadrilla).filter(models.Cuadrilla.activa == True).all()
    obreros = sum(c.cantidad_miembros for c in cuadrillas)
    productividad = sum(c.eficiencia for c in cuadrillas) / len(cuadrillas) if cuadrillas else 0

    alertas = db.query(models.Evento).filter(models.Evento.es_critico == True).count()

    return schemas.HudGlobal(
        presupuesto_total=pres_total,
        presupuesto_consumido=pres_consumido,
        materiales_total=mat_total,
        materiales_criticos=mat_criticos,
        obreros_total=obreros,
        cuadrillas_activas=len(cuadrillas),
        obras_activas=obras_activas,
        productividad=round(productividad, 1),
        alertas_total=alertas,
    )
