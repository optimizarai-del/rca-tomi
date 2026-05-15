"""Sprint 9 — Endpoints de stock multi-ubicación.

Toda la mutación pasa por `app/stock.py` (servicio) para garantizar que:
- Las cantidades nunca queden negativas.
- El cache `Material.stock` se mantiene en sincronía.
- Todo cambio queda registrado en `movimientos_material` (auditoría).

Carga real va por el bot de WhatsApp (premisa). Estos endpoints son consulta + acción
puntual desde la web cuando el admin confirma una acción del agente.
"""
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
)

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/", response_model=List[schemas.MaterialConStockOut])
def listar_stock(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    """Devuelve todos los materiales con desglose de stock por ubicación."""
    return breakdown_por_material(db)


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
