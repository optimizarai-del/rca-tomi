"""Sistema de notificaciones automáticas (Sprint 4 · T4).

Pensado para correr periódicamente (cron / scheduler externo). Es **idempotente**:
si ya se envió una notif para el mismo evento, no la duplica (gracias a `context_key`
en `OutboundMessage`).

Tipos de check:
    - cheques_venciendo: cheques propios que vencen en próximos N días
    - eventos_criticos: eventos con `es_critico=true` recientes y sin notificar
    - resumen_semanal: stats globales (idempotente por semana ISO)
    - asignacion_orden: orden creada con cuadrilla → mensaje al capataz
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app.whatsapp_sender import send_whatsapp
from app.slash_commands import fmt_money


def _admins_con_telefono(db: Session) -> list[models.User]:
    """Usuarios admin/super_admin/admin_finanzas con teléfono cargado."""
    return db.query(models.User).filter(
        models.User.role.in_([
            models.UserRole.super_admin,
            models.UserRole.admin,
            models.UserRole.admin_finanzas,
        ]),
        models.User.phone.isnot(None),
        models.User.phone != "",
        models.User.is_active == True,  # noqa: E712
    ).all()


def check_cheques_venciendo(db: Session, dias: int = 7) -> dict:
    """Notifica a los admin sobre cheques que vencen en próximos `dias` días."""
    today = date.today()
    horizonte = today + timedelta(days=dias)
    cheques = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque.isnot(None),
        models.MovimientoObra.fecha_vto_cheque >= today,
        models.MovimientoObra.fecha_vto_cheque <= horizonte,
    ).order_by(models.MovimientoObra.fecha_vto_cheque).all()

    admins = _admins_con_telefono(db)
    sent = 0
    skipped_dedupe = 0

    for c in cheques:
        dias_restantes = (c.fecha_vto_cheque - today).days
        obra = db.query(models.Obra).filter(models.Obra.id == c.obra_id).first()
        msg = (
            f"🏦 Cheque a vencer en {dias_restantes}d\n"
            f"Obra: {obra.codigo if obra else '?'} — {obra.nombre[:40] if obra else ''}\n"
            f"#{c.nro_cheque} · {c.banco}\n"
            f"Vto: {c.fecha_vto_cheque.isoformat()}\n"
            f"Monto: {fmt_money(float(c.monto))}"
        )
        ckey = f"cheque_venciendo:movimiento={c.id}:vto={c.fecha_vto_cheque.isoformat()}"
        for u in admins:
            r = send_whatsapp(
                db, u.phone, msg,
                notification_type="cheque_venciendo",
                context_key=ckey,
                obra_id=c.obra_id,
                user_id=u.id,
                dedupe=True,
            )
            if r is None:
                skipped_dedupe += 1
            else:
                sent += 1

    return {
        "type": "cheques_venciendo",
        "horizonte_dias": dias,
        "cheques_encontrados": len(cheques),
        "admins_destinatarios": len(admins),
        "sent": sent,
        "skipped_dedupe": skipped_dedupe,
    }


def check_eventos_criticos(db: Session, horas: int = 24) -> dict:
    """Notifica eventos críticos creados en las últimas `horas` horas."""
    desde = datetime.utcnow() - timedelta(hours=horas)
    eventos = db.query(models.Evento).filter(
        models.Evento.es_critico == True,  # noqa: E712
        models.Evento.fecha >= desde,
    ).order_by(models.Evento.fecha.desc()).all()

    admins = _admins_con_telefono(db)
    sent = 0
    skipped_dedupe = 0

    for ev in eventos:
        obra = db.query(models.Obra).filter(models.Obra.id == ev.obra_id).first() if ev.obra_id else None
        msg = (
            f"🚨 Evento crítico\n"
            f"Tipo: {ev.tipo.value}\n"
            f"Obra: {obra.codigo if obra else '—'}\n"
            f"{ev.titulo}\n"
            f"{ev.descripcion[:200] if ev.descripcion else ''}"
        )
        ckey = f"evento_critico:evento={ev.id}"
        for u in admins:
            r = send_whatsapp(
                db, u.phone, msg,
                notification_type="evento_critico",
                context_key=ckey,
                obra_id=ev.obra_id,
                user_id=u.id,
                dedupe=True,
            )
            if r is None:
                skipped_dedupe += 1
            else:
                sent += 1

    return {
        "type": "eventos_criticos",
        "horas": horas,
        "eventos_encontrados": len(eventos),
        "admins_destinatarios": len(admins),
        "sent": sent,
        "skipped_dedupe": skipped_dedupe,
    }


def check_resumen_semanal(db: Session, force: bool = False) -> dict:
    """Resumen semanal a admins. Idempotente por semana ISO (year-week)."""
    today = date.today()
    iso_y, iso_w, _ = today.isocalendar()
    ckey = f"semanal:{iso_y}-W{iso_w:02d}"

    # Si no es lunes y no force, skip
    if not force and today.weekday() != 0:  # 0 = lunes
        return {
            "type": "resumen_semanal",
            "skipped_reason": f"hoy es {today.strftime('%A')}, solo corro los lunes (usá force=true para forzar)",
            "sent": 0,
        }

    # Stats
    obras_count = db.query(models.Obra).count()
    obras_activas = db.query(models.Obra).filter(models.Obra.estado == models.ObraStatus.EN_CURSO).count()
    ingresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO
    ).scalar() or 0
    egresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO
    ).scalar() or 0
    aportes_pend = db.query(func.coalesce(
        func.sum(models.AporteSocio.monto - models.AporteSocio.monto_devuelto), 0
    )).filter(
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL
    ).scalar() or 0
    cheques_v = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque > today,
    ).scalar() or 0
    eventos_criticos = db.query(models.Evento).filter(
        models.Evento.es_critico == True,  # noqa: E712
        models.Evento.fecha >= datetime.utcnow() - timedelta(days=7),
    ).count()

    msg = (
        f"📊 Resumen semanal RCA — semana {iso_w}\n"
        f"Obras: {obras_activas}/{obras_count} activas\n"
        f"Ingresos: {fmt_money(float(ingresos))}\n"
        f"Egresos:  {fmt_money(float(egresos))}\n"
        f"Saldo:    {fmt_money(float(ingresos) - float(egresos))}\n"
        f"Aportes pendientes: {fmt_money(float(aportes_pend))}\n"
        f"Cheques a vencer: {fmt_money(float(cheques_v))}\n"
        f"Eventos críticos esta semana: {eventos_criticos}"
    )

    admins = _admins_con_telefono(db)
    sent = 0
    skipped = 0
    for u in admins:
        r = send_whatsapp(
            db, u.phone, msg,
            notification_type="resumen_semanal",
            context_key=ckey,
            user_id=u.id,
            dedupe=True,
        )
        if r is None:
            skipped += 1
        else:
            sent += 1

    return {
        "type": "resumen_semanal",
        "semana_iso": ckey,
        "admins_destinatarios": len(admins),
        "sent": sent,
        "skipped_dedupe": skipped,
    }


def check_ordenes_asignadas(db: Session, horas: int = 48) -> dict:
    """Avisa al capataz cuando se creó una orden con cuadrilla en últimas N horas."""
    desde = datetime.utcnow() - timedelta(hours=horas)
    ordenes = db.query(models.OrdenTrabajo).filter(
        models.OrdenTrabajo.cuadrilla_id.isnot(None),
        models.OrdenTrabajo.created_at >= desde,
    ).all()

    sent = 0
    skipped_dedupe = 0
    no_phone = 0

    for o in ordenes:
        cuad = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == o.cuadrilla_id).first()
        if not cuad or not cuad.capataz_id:
            no_phone += 1
            continue
        capataz = db.query(models.User).filter(models.User.id == cuad.capataz_id).first()
        if not capataz or not capataz.phone:
            no_phone += 1
            continue

        obra = db.query(models.Obra).filter(models.Obra.id == o.obra_id).first()
        msg = (
            f"📋 Nueva orden asignada a {cuad.nombre}\n"
            f"Obra: {obra.codigo if obra else '?'} — {obra.nombre[:40] if obra else ''}\n"
            f"{o.titulo}\n"
            f"Prioridad: {o.prioridad}\n"
            f"XP: {o.xp_reward}"
        )
        ckey = f"asignacion_orden:{o.id}"
        r = send_whatsapp(
            db, capataz.phone, msg,
            notification_type="asignacion_orden",
            context_key=ckey,
            obra_id=o.obra_id,
            user_id=capataz.id,
            dedupe=True,
        )
        if r is None:
            skipped_dedupe += 1
        else:
            sent += 1

    return {
        "type": "asignacion_orden",
        "horas": horas,
        "ordenes_encontradas": len(ordenes),
        "sent": sent,
        "skipped_dedupe": skipped_dedupe,
        "skipped_no_phone": no_phone,
    }


def run_all(
    db: Session,
    *,
    cheques_dias: int = 7,
    eventos_horas: int = 24,
    semanal_force: bool = False,
    ordenes_horas: int = 48,
    types: Optional[list[str]] = None,
) -> dict:
    """Corre todos (o un subset) los checks. Usado por el endpoint /api/notifications/check."""
    if types is None:
        types = ["cheques", "eventos", "semanal", "ordenes"]

    results = []
    if "cheques" in types:
        results.append(check_cheques_venciendo(db, dias=cheques_dias))
    if "eventos" in types:
        results.append(check_eventos_criticos(db, horas=eventos_horas))
    if "semanal" in types:
        results.append(check_resumen_semanal(db, force=semanal_force))
    if "ordenes" in types:
        results.append(check_ordenes_asignadas(db, horas=ordenes_horas))

    return {
        "checks_run": len(results),
        "total_sent": sum(r.get("sent", 0) for r in results),
        "total_skipped_dedupe": sum(r.get("skipped_dedupe", 0) for r in results),
        "details": results,
    }
