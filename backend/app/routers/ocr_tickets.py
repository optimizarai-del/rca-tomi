"""Sprint 18 — endpoints REST para borradores de OCR de tickets.

El flujo principal es por bot Telegram (foto → parser → /confirmar), pero
expone los mismos pasos por HTTP para tener una alternativa web:

- POST /api/ocr-tickets/parse-now: sube imagen y obtiene un borrador.
- GET  /api/ocr-tickets: lista (filtrable por estado).
- GET  /api/ocr-tickets/{id}: detalle.
- POST /api/ocr-tickets/{id}/confirmar: crea Comprobante + MovimientoObra.
- POST /api/ocr-tickets/{id}/rechazar: marca rechazado.
- DELETE /api/ocr-tickets/{id}: hard delete (admin).
"""
from __future__ import annotations
import base64
import json
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import (
    get_current_user, require_admin, require_finanzas, scope_demo, stamp_demo,
)
from app import ocr_vision

router = APIRouter(prefix="/api/ocr-tickets", tags=["ocr-tickets"])


def _serialize(t: models.TicketOCR) -> schemas.TicketOCROut:
    try:
        data = json.loads(t.resultado_json)
    except (TypeError, ValueError):
        data = {}
    return schemas.TicketOCROut(
        id=t.id,
        estado=t.estado,
        resultado=schemas.TicketOCRResultado.model_validate(data),
        model_used=t.model_used,
        error_msg=t.error_msg,
        telegram_chat_id=t.telegram_chat_id,
        imagen_url_cached=t.imagen_url_cached,
        obra_id=t.obra_id,
        comprobante_id=t.comprobante_id,
        movimiento_obra_id=t.movimiento_obra_id,
        created_by_id=t.created_by_id,
        created_at=t.created_at,
        confirmed_at=t.confirmed_at,
    )


def persistir_resultado(
    db: Session, *, user: Optional[models.User],
    resultado: dict, model_used: str,
    image_url: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    telegram_message_id: Optional[str] = None,
    telegram_file_id: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> models.TicketOCR:
    """Crea el TicketOCR. Helper reutilizado por bot y endpoint."""
    estado = models.TicketOCREstado.error if error_msg else models.TicketOCREstado.pendiente
    t = models.TicketOCR(
        telegram_chat_id=telegram_chat_id,
        telegram_message_id=telegram_message_id,
        telegram_file_id=telegram_file_id,
        imagen_url_cached=image_url,
        resultado_json=json.dumps(resultado, ensure_ascii=False, default=str),
        model_used=model_used,
        error_msg=error_msg,
        estado=estado,
        created_by_id=user.id if user else None,
    )
    if user is not None:
        stamp_demo(t, user)
    db.add(t); db.commit(); db.refresh(t)
    return t


@router.post("/parse-now", response_model=schemas.TicketOCROut, status_code=201)
def parse_now(
    data: schemas.TicketOCRSubirIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    """Sube una imagen (URL o base64) y obtiene un borrador OCR.

    Para fotos de Telegram, pasar la URL temporal devuelta por `get_file_url`.
    Para uploads de la web, usar `image_base64`.
    """
    if not data.image_url and not data.image_base64:
        raise HTTPException(400, "Se requiere image_url o image_base64")

    image_bytes = None
    if data.image_base64:
        try:
            image_bytes = base64.b64decode(data.image_base64)
        except Exception:
            raise HTTPException(400, "image_base64 inválido")

    resultado, model_used = ocr_vision.parsear_ticket(
        image_url=data.image_url,
        image_bytes=image_bytes,
        model_override=data.model_override,
    )
    t = persistir_resultado(
        db, user=user, resultado=resultado, model_used=model_used,
        image_url=data.image_url,
        telegram_chat_id=data.telegram_chat_id,
        telegram_message_id=data.telegram_message_id,
        telegram_file_id=data.telegram_file_id,
    )
    return _serialize(t)


@router.get("", response_model=List[schemas.TicketOCROut])
def list_tickets(
    estado: Optional[models.TicketOCREstado] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    q = scope_demo(db.query(models.TicketOCR), models.TicketOCR, user)
    if estado:
        q = q.filter(models.TicketOCR.estado == estado)
    rows = q.order_by(models.TicketOCR.created_at.desc(), models.TicketOCR.id.desc()).limit(200).all()
    return [_serialize(t) for t in rows]


@router.get("/{tid}", response_model=schemas.TicketOCROut)
def get_ticket(
    tid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    t = scope_demo(db.query(models.TicketOCR), models.TicketOCR, user).filter(
        models.TicketOCR.id == tid
    ).first()
    if not t:
        raise HTTPException(404, "Ticket no encontrado")
    return _serialize(t)


@router.post("/{tid}/rechazar", response_model=schemas.TicketOCROut)
def rechazar(
    tid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    if not t:
        raise HTTPException(404, "Ticket no encontrado")
    if t.estado not in (models.TicketOCREstado.pendiente, models.TicketOCREstado.error):
        raise HTTPException(400, f"No se puede rechazar (estado={t.estado.value})")
    t.estado = models.TicketOCREstado.rechazado
    db.commit(); db.refresh(t)
    return _serialize(t)


@router.delete("/{tid}", status_code=204)
def delete_ticket(
    tid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    if not t:
        raise HTTPException(404, "Ticket no encontrado")
    db.delete(t); db.commit()


@router.post("/{tid}/confirmar", response_model=schemas.TicketOCROut)
def confirmar(
    tid: int,
    data: schemas.TicketOCRConfirmarIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_finanzas),
):
    """Crea Comprobante + MovimientoObra desde el ticket parseado."""
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    if not t:
        raise HTTPException(404, "Ticket no encontrado")
    if t.estado != models.TicketOCREstado.pendiente:
        raise HTTPException(400, f"Solo se puede confirmar un ticket pendiente (actual: {t.estado.value})")

    obra = db.query(models.Obra).filter(models.Obra.id == data.obra_id).first()
    if not obra:
        raise HTTPException(400, "Obra no encontrada")

    payload = json.loads(t.resultado_json)
    res = schemas.TicketOCRResultado.model_validate(payload)

    # Resolver proveedor
    proveedor = None
    if data.proveedor_id:
        proveedor = db.query(models.Proveedor).filter(
            models.Proveedor.id == data.proveedor_id
        ).first()
    if not proveedor:
        proveedor = ocr_vision.matchear_proveedor(
            db, cuit=res.proveedor_cuit, nombre=res.proveedor_nombre,
        )

    tipo_doc = ocr_vision.tipo_comprobante_from_str(res.tipo_documento)
    cuit_emisor = (res.proveedor_cuit or "00-00000000-0").strip()
    cuit_receptor = "30-99999999-9"  # placeholder, RCA. En producción tomar de config.

    total = float(res.total or 0)
    if total <= 0:
        raise HTTPException(400, "El total del comprobante debe ser > 0")

    fecha_em = res.fecha_emision or date.today()

    # Crear Comprobante
    cmp = models.Comprobante(
        obra_id=obra.id,
        tipo_comprobante=tipo_doc,
        punto_venta=res.punto_venta,
        nro_comprobante=res.nro_comprobante or f"OCR-{t.id}",
        fecha_emision=fecha_em,
        cuit_emisor=cuit_emisor,
        cuit_receptor=cuit_receptor,
        neto_gravado=res.neto_gravado or 0,
        iva_21=res.iva_21 or 0,
        iva_105=res.iva_105 or 0,
        total=total,
        es_venta=data.es_venta,
        archivo_url=t.imagen_url_cached,
        notas=res.notas,
    )
    stamp_demo(cmp, user)
    db.add(cmp); db.flush()

    # Crear MovimientoObra
    if data.es_venta:
        mov_tipo = models.TipoMovimiento.INGRESO
        origen = models.OrigenIngreso.CERTIFICADO_ETAPA
        categoria = None
    else:
        mov_tipo = models.TipoMovimiento.EGRESO
        origen = None
        categoria = data.categoria_egreso

    iva_pct = None
    if total and (res.iva_21 or 0) > 0:
        iva_pct = 0.21
    elif total and (res.iva_105 or 0) > 0:
        iva_pct = 0.105

    concepto = (
        f"OCR — {tipo_doc.value} {res.nro_comprobante or ''} · "
        f"{res.proveedor_nombre or 'sin proveedor'}"
    ).strip()
    if data.notas_extra:
        concepto = f"{concepto} · {data.notas_extra}"

    mov = models.MovimientoObra(
        obra_id=obra.id,
        fecha=fecha_em,
        tipo=mov_tipo,
        origen_ingreso=origen,
        categoria_egreso=categoria,
        concepto=concepto[:300],
        monto=total,
        medio_pago=data.medio_pago,
        comprobante_id=cmp.id,
        proveedor_id=proveedor.id if proveedor else None,
        canal=models.CanalCarga.agente_ia,
        cargado_por=user.id,
        legalidad=data.legalidad,
        cobro_pago_estado=data.cobro_pago_estado,
        iva_pct=iva_pct,
    )
    stamp_demo(mov, user)
    db.add(mov); db.flush()

    # Actualizar ticket
    t.estado = models.TicketOCREstado.confirmado
    t.obra_id = obra.id
    t.comprobante_id = cmp.id
    t.movimiento_obra_id = mov.id
    t.confirmed_at = datetime.utcnow()

    db.commit(); db.refresh(t)
    return _serialize(t)
