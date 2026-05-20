"""Servicio de notificaciones recurrentes (Sprint 14).

Funciones que llaman a `send_telegram` / `send_whatsapp` para alertas con dedupe.
Pensado para correr desde scripts/cron — no expone HTTP por ahora.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Iterable
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models
from app.messaging.telegram_sender import send_telegram


def notificar_retiros_pendientes(db: Session, dias_antes: int = 1) -> dict:
    """Para cada StockMaterial con fecha_retirar = hoy+dias_antes y sin alerta previa,
    manda mensaje por Telegram a TODOS los users admin con `telegram_chat_id`.

    Idempotente: marca `retiro_alertado_at` después de enviar. Si la fecha se cambia,
    `agendar_retiro` resetea el alertado_at y vuelve a poder dispararse.

    Devuelve resumen {filas_notificadas, destinatarios, errores}.
    """
    target_date = date.today() + timedelta(days=dias_antes)

    filas = db.query(models.StockMaterial).filter(
        models.StockMaterial.ubicacion_tipo
        == models.UbicacionStockTipo.comprado_no_retirado,
        models.StockMaterial.cantidad > 0,
        models.StockMaterial.fecha_retirar == target_date,
        models.StockMaterial.retiro_alertado_at.is_(None),
    ).all()

    if not filas:
        return {"filas_notificadas": 0, "destinatarios": 0, "errores": []}

    # Destinatarios: admins activos con Telegram vinculado
    admins_roles = (
        models.UserRole.super_admin,
        models.UserRole.admin,
        models.UserRole.admin_finanzas,
    )
    destinos = db.query(models.User).filter(
        models.User.is_active == True,  # noqa: E712
        models.User.telegram_chat_id.isnot(None),
        models.User.role.in_(admins_roles),
    ).all()

    errores: list[str] = []
    notificados = 0
    for fila in filas:
        material = db.query(models.Material).filter(
            models.Material.id == fila.material_id
        ).first()
        proveedor = (
            db.query(models.Proveedor).filter(models.Proveedor.id == fila.ubicacion_ref).first()
            if fila.ubicacion_ref else None
        )
        nombre_m = material.nombre if material else f"material #{fila.material_id}"
        nombre_p = proveedor.nombre if proveedor else "proveedor"
        cantidad = float(fila.cantidad or 0)
        unidad = material.unidad if material else "u"

        cuerpo = (
            f"🚚 Mañana hay que retirar:\n"
            f"  • {cantidad:.0f} {unidad} de {nombre_m}\n"
            f"  • Proveedor: {nombre_p}\n"
            f"  • Fecha: {fila.fecha_retirar.isoformat()}\n"
            f"Cuando lo retires, marcalo desde /materiales o por la app."
        )
        ctx_key = f"retiro_pendiente:stock={fila.id}:fecha={fila.fecha_retirar.isoformat()}"

        for u in destinos:
            try:
                send_telegram(
                    db, chat_id=u.telegram_chat_id, mensaje=cuerpo,
                    notification_type="retiro_pendiente",
                    context_key=ctx_key + f":user={u.id}",
                    user_id=u.id,
                    dedupe=True,
                )
                notificados += 1
            except Exception as e:
                errores.append(f"stock={fila.id} user={u.id}: {e}")

        fila.retiro_alertado_at = datetime.utcnow()

    db.commit()
    return {
        "filas_notificadas": len(filas),
        "destinatarios": notificados,
        "errores": errores,
    }
