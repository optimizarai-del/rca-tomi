"""Movimientos de obra — la tabla central. CRUD + flujo de caja."""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, require_finanzas, scope_demo, stamp_demo

router = APIRouter(prefix="/api/movimientos", tags=["movimientos"])


def _validar_movimiento(data: schemas.MovimientoIn) -> Optional[str]:
    """Validaciones de coherencia. Devuelve error string o None."""
    if data.tipo == models.TipoMovimiento.INGRESO:
        if not data.origen_ingreso:
            return "Para INGRESO se requiere origen_ingreso"
        if data.categoria_egreso:
            return "categoria_egreso debe ser null en INGRESO"
    else:  # EGRESO
        if not data.categoria_egreso:
            return "Para EGRESO se requiere categoria_egreso"
        if data.origen_ingreso:
            return "origen_ingreso debe ser null en EGRESO"

    if data.medio_pago in (models.MedioPago.CHEQUE_PROPIO, models.MedioPago.CHEQUE_TERCERO):
        if not data.nro_cheque or not data.fecha_vto_cheque:
            return "Cheque requiere nro_cheque y fecha_vto_cheque"

    return None


@router.get("", response_model=List[schemas.MovimientoOut])
def list_movimientos(
    obra_id: Optional[int] = None,
    etapa_id: Optional[int] = None,
    tipo: Optional[models.TipoMovimiento] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    estado: Optional[models.EstadoMovimiento] = None,
    # Sprint 21
    legalidad: Optional[models.LegalidadMovimiento] = None,
    cobro_pago_estado: Optional[models.CobroPagoEstado] = None,
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    q = db.query(models.MovimientoObra)
    q = scope_demo(q, models.MovimientoObra, user)
    if obra_id:
        q = q.filter(models.MovimientoObra.obra_id == obra_id)
    if etapa_id:
        q = q.filter(models.MovimientoObra.etapa_id == etapa_id)
    if tipo:
        q = q.filter(models.MovimientoObra.tipo == tipo)
    if desde:
        q = q.filter(models.MovimientoObra.fecha >= desde)
    if hasta:
        q = q.filter(models.MovimientoObra.fecha <= hasta)
    if estado:
        q = q.filter(models.MovimientoObra.estado == estado)
    if legalidad:
        q = q.filter(models.MovimientoObra.legalidad == legalidad)
    if cobro_pago_estado:
        q = q.filter(models.MovimientoObra.cobro_pago_estado == cobro_pago_estado)
    return q.order_by(models.MovimientoObra.fecha.desc(), models.MovimientoObra.id.desc()).limit(limit).all()


@router.post("", response_model=schemas.MovimientoOut, status_code=201)
def create_movimiento(
    data: schemas.MovimientoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if err := _validar_movimiento(data):
        raise HTTPException(400, err)
    # R: TOTAL_BLANCO exige comprobante en INGRESOS de cliente
    obra = db.query(models.Obra).filter(models.Obra.id == data.obra_id).first()
    if not obra:
        raise HTTPException(404, "Obra no encontrada")
    if (
        obra.tipo_facturacion == models.TipoFacturacion.TOTAL_BLANCO
        and data.tipo == models.TipoMovimiento.INGRESO
        and data.origen_ingreso in (models.OrigenIngreso.ANTICIPO_CLIENTE, models.OrigenIngreso.CERTIFICADO_ETAPA, models.OrigenIngreso.PAGO_FINAL)
        and not data.comprobante_id
    ):
        raise HTTPException(400, "Obra TOTAL_BLANCO: este ingreso requiere comprobante")

    payload = data.model_dump()
    m = models.MovimientoObra(**payload, cargado_por=user.id)
    db.add(m); db.commit(); db.refresh(m)
    return m


# ─── REPORTES / VISTAS (deben venir ANTES de /{mid} para no chocar) ───

@router.get("/obra/{oid}/saldo")
def saldo_obra(oid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """R1: saldo = SUM(INGRESO) - SUM(EGRESO), sin filtrar por estado."""
    rows = db.query(
        models.MovimientoObra.tipo,
        func.coalesce(func.sum(models.MovimientoObra.monto), 0).label("total"),
    ).filter(models.MovimientoObra.obra_id == oid).group_by(models.MovimientoObra.tipo).all()
    ingresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.INGRESO), 0.0)
    egresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.EGRESO), 0.0)
    return {"obra_id": oid, "total_ingresos": ingresos, "total_egresos": egresos, "saldo": ingresos - egresos}


@router.get("/obra/{oid}/flujo-caja")
def flujo_caja_semanal(
    oid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    """Flujo de caja agrupado por semana, con saldo acumulado."""
    movs = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == oid
    ).order_by(models.MovimientoObra.fecha).all()

    # Agrupación en Python para portabilidad SQLite/PG
    semanas: dict[date, dict] = {}
    for m in movs:
        # date_trunc('week') → lunes de esa semana
        weekday = m.fecha.weekday()
        semana = m.fecha - timedelta(days=weekday)
        if semana not in semanas:
            semanas[semana] = {"ingresos": 0.0, "egresos": 0.0}
        if m.tipo == models.TipoMovimiento.INGRESO:
            semanas[semana]["ingresos"] += float(m.monto)
        else:
            semanas[semana]["egresos"] += float(m.monto)

    out = []
    saldo_acum = 0.0
    for semana in sorted(semanas):
        d = semanas[semana]
        saldo_sem = d["ingresos"] - d["egresos"]
        saldo_acum += saldo_sem
        out.append({
            "semana": semana.isoformat(),
            "ingresos": round(d["ingresos"], 2),
            "egresos": round(d["egresos"], 2),
            "saldo_semana": round(saldo_sem, 2),
            "saldo_acumulado": round(saldo_acum, 2),
        })
    return out


@router.get("/obra/{oid}/flujo-proyectado")
def flujo_proyectado(
    oid: int,
    horizonte_dias: int = 90,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Flujo proyectado: movimientos reales + cheques a vencer + etapas estimadas."""
    today = date.today()
    horizonte = today + timedelta(days=horizonte_dias)
    items = []

    # Movimientos reales (R3: cheque propio "sale" en fecha_vto)
    movs = db.query(models.MovimientoObra).filter(models.MovimientoObra.obra_id == oid).all()
    for m in movs:
        # cheque propio: la salida real ocurre al vencimiento
        if m.medio_pago == models.MedioPago.CHEQUE_PROPIO and m.fecha_vto_cheque and m.fecha_vto_cheque > today:
            if m.fecha_vto_cheque <= horizonte:
                items.append({
                    "fecha_efectiva": m.fecha_vto_cheque.isoformat(),
                    "tipo": "EGRESO",
                    "monto": float(m.monto),
                    "concepto": f"[Cheque] {m.concepto}",
                    "origen": "cheque_pendiente",
                })
        else:
            items.append({
                "fecha_efectiva": m.fecha.isoformat(),
                "tipo": m.tipo.value,
                "monto": float(m.monto),
                "concepto": m.concepto,
                "origen": "real",
            })

    # Etapas futuras estimadas
    etapas = db.query(models.EtapaObra).filter(
        models.EtapaObra.obra_id == oid,
        models.EtapaObra.estado.in_([models.EtapaEstado.PENDIENTE, models.EtapaEstado.EN_EJECUCION, models.EtapaEstado.EJECUTADA, models.EtapaEstado.FACTURADA]),
        models.EtapaObra.fecha_estimada.isnot(None),
    ).all()
    for e in etapas:
        if e.fecha_estimada and today < e.fecha_estimada <= horizonte and e.monto_contractual:
            items.append({
                "fecha_efectiva": e.fecha_estimada.isoformat(),
                "tipo": "INGRESO",
                "monto": float(e.monto_contractual),
                "concepto": f"[Estimado] {e.nombre}",
                "origen": "etapa_estimada",
            })

    items.sort(key=lambda x: x["fecha_efectiva"])
    return items


@router.get("/cheques-a-vencer")
def cheques_a_vencer(
    dias: int = 30,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Cheques propios que vencen en los próximos N días."""
    today = date.today()
    horizonte = today + timedelta(days=dias)
    rows = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque.isnot(None),
        models.MovimientoObra.fecha_vto_cheque >= today,
        models.MovimientoObra.fecha_vto_cheque <= horizonte,
    ).order_by(models.MovimientoObra.fecha_vto_cheque).all()
    return [
        {
            "id": r.id,
            "obra_id": r.obra_id,
            "concepto": r.concepto,
            "monto": float(r.monto),
            "nro_cheque": r.nro_cheque,
            "banco": r.banco,
            "fecha_vto": r.fecha_vto_cheque.isoformat(),
            "dias_restantes": (r.fecha_vto_cheque - today).days,
        }
        for r in rows
    ]


# ─── Sprint 21: resumen contable blanco/negro por obra ───────────────────


def _agregar_caja(rows, legalidad: models.LegalidadMovimiento) -> schemas.FinanzasCajaResumen:
    """Calcula totales de una caja (blanco o negro) desde la lista de movimientos."""
    out = schemas.FinanzasCajaResumen()
    for m in rows:
        if m.legalidad != legalidad:
            continue
        monto = float(m.monto or 0)
        gastos = float(m.gastos_banco or 0)
        iva = float(m.iva_pct or 0) * monto if m.iva_pct else 0
        iibb = float(m.iibb_pct or 0) * monto if m.iibb_pct else 0
        out.iva_total += iva
        out.iibb_total += iibb
        out.gastos_banco_total += gastos
        if m.tipo == models.TipoMovimiento.INGRESO:
            if m.cobro_pago_estado == models.CobroPagoEstado.cobrado:
                out.ingresos_cobrado += monto
            else:
                out.ingresos_pendiente += monto
        else:  # EGRESO
            if m.cobro_pago_estado == models.CobroPagoEstado.pagado:
                out.egresos_pagado += monto
            else:
                out.egresos_pendiente += monto
    out.neto_efectivo = round(out.ingresos_cobrado - out.egresos_pagado, 2)
    out.saldo_compromiso = round(out.ingresos_pendiente - out.egresos_pendiente, 2)
    out.iva_total = round(out.iva_total, 2)
    out.iibb_total = round(out.iibb_total, 2)
    out.gastos_banco_total = round(out.gastos_banco_total, 2)
    out.ingresos_cobrado = round(out.ingresos_cobrado, 2)
    out.ingresos_pendiente = round(out.ingresos_pendiente, 2)
    out.egresos_pagado = round(out.egresos_pagado, 2)
    out.egresos_pendiente = round(out.egresos_pendiente, 2)
    return out


@router.get("/obra/{oid}/resumen-finanzas", response_model=schemas.FinanzasObraResumen)
def resumen_finanzas_obra(
    oid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Sprint 21 — Resumen contable de la obra desglosado por caja blanco/negro.

    Devuelve los dos lados (blanco y negro) con cobrado/pendiente, y los
    consolidados 'lo que tenés' (cobrado − pagado) y 'lo que se debe'
    (pendiente neto: positivo = a favor, negativo = en contra).
    """
    obra = db.query(models.Obra).filter(models.Obra.id == oid).first()
    if not obra:
        raise HTTPException(404, "Obra no encontrada")

    movs = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == oid
    ).all()

    blanco = _agregar_caja(movs, models.LegalidadMovimiento.blanco)
    negro = _agregar_caja(movs, models.LegalidadMovimiento.negro)

    lo_que_tenes = round(blanco.neto_efectivo + negro.neto_efectivo, 2)
    lo_que_se_debe = round(blanco.saldo_compromiso + negro.saldo_compromiso, 2)
    return schemas.FinanzasObraResumen(
        obra_id=oid,
        monto_contrato=float(obra.monto_contrato or 0),
        blanco=blanco,
        negro=negro,
        lo_que_tenes=lo_que_tenes,
        lo_que_se_debe=lo_que_se_debe,
        saldo_total=round(lo_que_tenes + lo_que_se_debe, 2),
    )


@router.patch("/{mid}/finanzas", response_model=schemas.MovimientoOut)
def patch_finanzas_movimiento(
    mid: int,
    data: schemas.FinanzasMovimientoUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Actualiza solo los campos contables (legalidad, cobrado/pagado, fechas, %).

    Usado por la UI cuando hacés 'marcar cobrado' / 'marcar pagado' / cambiar a
    blanco o negro sin tener que reenviar todo el payload del movimiento.
    """
    m = db.query(models.MovimientoObra).filter(models.MovimientoObra.id == mid).first()
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    payload = data.model_dump(exclude_unset=True)

    # Validar coherencia tipo ↔ cobro_pago_estado
    if "cobro_pago_estado" in payload:
        nuevo = payload["cobro_pago_estado"]
        if m.tipo == models.TipoMovimiento.INGRESO and nuevo == models.CobroPagoEstado.pagado:
            raise HTTPException(400, "Un INGRESO no puede tener cobro_pago_estado='pagado' (usar 'cobrado')")
        if m.tipo == models.TipoMovimiento.EGRESO and nuevo == models.CobroPagoEstado.cobrado:
            raise HTTPException(400, "Un EGRESO no puede tener cobro_pago_estado='cobrado' (usar 'pagado')")
        # Si quedó cobrado/pagado y no hay fecha_cobro_pago, default a hoy
        if nuevo in (models.CobroPagoEstado.cobrado, models.CobroPagoEstado.pagado):
            if "fecha_cobro_pago" not in payload and not m.fecha_cobro_pago:
                payload["fecha_cobro_pago"] = date.today()
        if nuevo == models.CobroPagoEstado.pendiente:
            payload["fecha_cobro_pago"] = None

    for k, v in payload.items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return m


@router.get("/descalce-fiscal")
def descalce_fiscal(
    obra_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    """R4: detecta obras donde egresos con comprobante > ingresos con comprobante.

    Solo super_admin + admin_finanzas — datos fiscales sensibles.
    """
    obras = db.query(models.Obra).all() if not obra_id else [
        db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    ]
    out = []
    for o in obras:
        if not o:
            continue
        ingresos_cf = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
            models.MovimientoObra.obra_id == o.id,
            models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO,
            models.MovimientoObra.tiene_comprobante == True,  # noqa: E712
        ).scalar() or 0
        egresos_cf = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
            models.MovimientoObra.obra_id == o.id,
            models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO,
            models.MovimientoObra.tiene_comprobante == True,  # noqa: E712
        ).scalar() or 0
        descalce = float(egresos_cf) - float(ingresos_cf)
        if descalce > 0 or obra_id:  # solo reportar si hay descalce, salvo que se pida una específica
            out.append({
                "obra_id": o.id,
                "obra": o.nombre,
                "tipo_facturacion": o.tipo_facturacion.value,
                "ingresos_con_comprobante": float(ingresos_cf),
                "egresos_con_comprobante": float(egresos_cf),
                "descalce": descalce,
                "tiene_descalce": descalce > 0,
            })
    return out


# ─── CRUD por id (al final para no chocar con rutas estáticas) ───

@router.get("/{mid}", response_model=schemas.MovimientoOut)
def get_movimiento(mid: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    m = db.query(models.MovimientoObra).filter(models.MovimientoObra.id == mid).first()
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    return m


@router.put("/{mid}", response_model=schemas.MovimientoOut)
def update_movimiento(
    mid: int,
    data: schemas.MovimientoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    m = db.query(models.MovimientoObra).filter(models.MovimientoObra.id == mid).first()
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    if err := _validar_movimiento(data):
        raise HTTPException(400, err)
    for k, v in data.model_dump().items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return m


@router.delete("/{mid}", status_code=204)
def delete_movimiento(
    mid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    m = db.query(models.MovimientoObra).filter(models.MovimientoObra.id == mid).first()
    if not m:
        raise HTTPException(404, "Movimiento no encontrado")
    db.delete(m); db.commit()
