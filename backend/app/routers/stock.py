"""Sprint 9 — Endpoints de stock multi-ubicación.

Toda la mutación pasa por `app/stock.py` (servicio) para garantizar que:
- Las cantidades nunca queden negativas.
- El cache `Material.stock` se mantiene en sincronía.
- Todo cambio queda registrado en `movimientos_material` (auditoría).

Carga real va por el bot de WhatsApp (premisa). Estos endpoints son consulta + acción
puntual desde la web cuando el admin confirma una acción del agente.
"""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin
from app.stock import (
    breakdown_por_material,
    cargar_compra_pendiente,
    retirar_de_proveedor,
    consumir_en_obra,
    transferir_stock,
    agendar_retiro,
    marcar_retirado,
    pendientes_retiro_proximos,
    listar_retiros,
)

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("", response_model=List[schemas.MaterialConStockOut])
def listar_stock(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    """Devuelve todos los materiales con desglose de stock por ubicación."""
    return breakdown_por_material(db)


# Sprint 14: rutas con paths fijos van ANTES de /{material_id} para no chocar.


@router.get("/pendientes", response_model=List[schemas.StockPendienteRetiroOut])
def listar_pendientes(
    dias: int = 30,
    incluir_sin_fecha: bool = True,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Stock comprado_no_retirado. Filtra por fecha_retirar dentro de N días."""
    filas = pendientes_retiro_proximos(db, dias=dias, incluir_sin_fecha=incluir_sin_fecha)
    return [_resolve_pendiente(db, f) for f in filas]


@router.get("/retiros", response_model=List[schemas.RetiroMaterialOut])
def listar_retiros_endpoint(
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    obra_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Histórico de retiros con filtros."""
    out = listar_retiros(
        db, desde=desde, hasta=hasta, obra_id=obra_id, proveedor_id=proveedor_id,
    )
    return [_enrich_retiro(db, r) for r in out]


@router.get("/{material_id}", response_model=schemas.MaterialConStockOut)
def stock_de_material(material_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    items = breakdown_por_material(db, material_id=material_id)
    if not items:
        raise HTTPException(404, "Material no encontrado")
    return items[0]


@router.post("/compra-pendiente", response_model=schemas.MaterialConStockOut)
def endpoint_compra_pendiente(
    payload: schemas.StockCompraPendienteIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Registra una compra cuya mercadería sigue en el proveedor."""
    cargar_compra_pendiente(db, material_id=payload.material_id, proveedor_id=payload.proveedor_id,
                            cantidad=payload.cantidad, nota=payload.nota, usuario_id=user.id)
    return breakdown_por_material(db, material_id=payload.material_id)[0]


@router.post("/retiro-proveedor", response_model=schemas.MaterialConStockOut)
def endpoint_retiro_proveedor(
    payload: schemas.StockRetiroProveedorIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Marca materiales como retirados del proveedor. Van a depósito propio o directo a obra."""
    retirar_de_proveedor(
        db, material_id=payload.material_id, proveedor_id=payload.proveedor_id,
        cantidad=payload.cantidad, destino_tipo=payload.destino_tipo,
        destino_obra_id=payload.destino_obra_id, nota=payload.nota, usuario_id=user.id,
    )
    return breakdown_por_material(db, material_id=payload.material_id)[0]


@router.post("/consumo-obra", response_model=schemas.MaterialConStockOut)
def endpoint_consumo_obra(
    payload: schemas.StockConsumoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Resta stock de en_obra (la cuadrilla usó material)."""
    consumir_en_obra(db, material_id=payload.material_id, obra_id=payload.obra_id,
                    cantidad=payload.cantidad, nota=payload.nota, usuario_id=user.id)
    return breakdown_por_material(db, material_id=payload.material_id)[0]


@router.post("/transferir", response_model=schemas.MaterialConStockOut)
def endpoint_transferir(
    payload: schemas.StockTransferenciaIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    transferir_stock(
        db, material_id=payload.material_id, cantidad=payload.cantidad,
        origen_tipo=payload.origen_tipo, origen_obra_id=payload.origen_obra_id,
        destino_tipo=payload.destino_tipo, destino_obra_id=payload.destino_obra_id,
        nota=payload.nota, usuario_id=user.id,
    )
    return breakdown_por_material(db, material_id=payload.material_id)[0]


# ─── Sprint 14: agendar y registrar retiros ────────────────────────────────


def _resolve_pendiente(db: Session, sm: models.StockMaterial) -> schemas.StockPendienteRetiroOut:
    material = db.query(models.Material).filter(models.Material.id == sm.material_id).first()
    proveedor = (
        db.query(models.Proveedor).filter(models.Proveedor.id == sm.ubicacion_ref).first()
        if sm.ubicacion_ref else None
    )
    dias = None
    if sm.fecha_retirar:
        dias = (sm.fecha_retirar - date.today()).days
    return schemas.StockPendienteRetiroOut(
        stock_material_id=sm.id,
        material_id=sm.material_id,
        material_nombre=material.nombre if material else "—",
        unidad=material.unidad if material else "u",
        proveedor_id=sm.ubicacion_ref,
        proveedor_nombre=proveedor.nombre if proveedor else None,
        cantidad=float(sm.cantidad or 0),
        fecha_retirar=sm.fecha_retirar,
        dias_para_retiro=dias,
        alertado_at=sm.retiro_alertado_at,
    )


@router.patch("/{stock_material_id}/agendar-retiro")
def endpoint_agendar_retiro(
    stock_material_id: int,
    payload: schemas.StockAgendarRetiroIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Setea fecha_retirar para una fila comprado_no_retirado."""
    try:
        fila = agendar_retiro(
            db, stock_material_id=stock_material_id, fecha_retirar=payload.fecha_retirar,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _resolve_pendiente(db, fila)


@router.post("/{stock_material_id}/retirar", response_model=schemas.RetiroMaterialOut, status_code=201)
def endpoint_marcar_retirado(
    stock_material_id: int,
    payload: schemas.StockMarcarRetiradoIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    """Marca como retirado: mueve stock + crea RetiroMaterial con forma_pago/en_negro/comprobante."""
    try:
        retiro = marcar_retirado(
            db,
            stock_material_id=stock_material_id,
            cantidad=payload.cantidad,
            fecha_retiro=payload.fecha_retiro,
            forma_pago=payload.forma_pago,
            en_negro=payload.en_negro,
            comprobante_id=payload.comprobante_id,
            destino_tipo=payload.destino_tipo,
            destino_obra_id=payload.destino_obra_id,
            notas=payload.notas,
            usuario_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _enrich_retiro(db, retiro)


def _enrich_retiro(db: Session, r: models.RetiroMaterial) -> schemas.RetiroMaterialOut:
    material = db.query(models.Material).filter(models.Material.id == r.material_id).first()
    proveedor = (
        db.query(models.Proveedor).filter(models.Proveedor.id == r.proveedor_id).first()
        if r.proveedor_id else None
    )
    obra = (
        db.query(models.Obra).filter(models.Obra.id == r.obra_destino_id).first()
        if r.obra_destino_id else None
    )
    return schemas.RetiroMaterialOut(
        id=r.id, material_id=r.material_id, proveedor_id=r.proveedor_id,
        obra_destino_id=r.obra_destino_id, cantidad=float(r.cantidad),
        fecha_retiro=r.fecha_retiro, forma_pago=r.forma_pago, en_negro=r.en_negro,
        comprobante_id=r.comprobante_id, notas=r.notas, created_by_id=r.created_by_id,
        created_at=r.created_at,
        material_nombre=material.nombre if material else None,
        proveedor_nombre=proveedor.nombre if proveedor else None,
        obra_destino_nombre=obra.nombre if obra else None,
    )
