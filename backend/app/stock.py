"""Servicio de stock multi-ubicación (Sprint 9 + Sprint 14).

Contiene la lógica de negocio para mover stock entre las 3 ubicaciones:
- deposito_propio: depósito de RCA (sin obra ni proveedor)
- en_obra: ya entregado a una obra específica
- comprado_no_retirado: pago/factura emitida, mercadería sigue en el proveedor

Todas las mutaciones:
1. Validan que el material exista.
2. Validan que el stock no quede negativo (excepción: deposito_propio puede caer a 0).
3. Registran un MovimientoMaterial (auditoría).
4. Recalculan Material.stock como cache de (deposito + en_obras), sin contar pendientes.

Tanto los endpoints REST como las tools del agente usan estas funciones, así que
toda la consistencia queda en un único lugar.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models


# ─── Helpers internos ──────────────────────────────────────────────────────

def _fila_stock(
    db: Session, material_id: int, ubicacion_tipo: models.UbicacionStockTipo,
    ubicacion_ref: Optional[int],
) -> models.StockMaterial:
    """Devuelve la fila StockMaterial para esa combinación, creándola si no existe."""
    q = db.query(models.StockMaterial).filter(
        models.StockMaterial.material_id == material_id,
        models.StockMaterial.ubicacion_tipo == ubicacion_tipo,
    )
    if ubicacion_ref is None:
        q = q.filter(models.StockMaterial.ubicacion_ref.is_(None))
    else:
        q = q.filter(models.StockMaterial.ubicacion_ref == ubicacion_ref)
    fila = q.first()
    if fila is None:
        fila = models.StockMaterial(
            material_id=material_id, ubicacion_tipo=ubicacion_tipo,
            ubicacion_ref=ubicacion_ref, cantidad=0,
        )
        db.add(fila); db.flush()
    return fila


def _validar_material(db: Session, material_id: int) -> models.Material:
    m = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not m:
        raise ValueError(f"Material id={material_id} no existe")
    return m


def _recalc_material_stock(db: Session, material_id: int) -> None:
    """Recalcula Material.stock = sum(deposito + en_obra), excluye pendientes de retiro."""
    db.flush()  # asegura que cambios en StockMaterial sean visibles para el SUM
    total = db.query(func.coalesce(func.sum(models.StockMaterial.cantidad), 0)).filter(
        models.StockMaterial.material_id == material_id,
        models.StockMaterial.ubicacion_tipo.in_([
            models.UbicacionStockTipo.deposito_propio,
            models.UbicacionStockTipo.en_obra,
        ]),
    ).scalar() or 0
    m = db.query(models.Material).filter(models.Material.id == material_id).first()
    if m:
        m.stock = float(total)


def _registrar_movimiento(
    db: Session, *, material_id: int, obra_id: Optional[int],
    tipo: str, cantidad: float, nota: Optional[str], usuario_id: Optional[int],
):
    db.add(models.MovimientoMaterial(
        material_id=material_id, obra_id=obra_id, tipo=tipo,
        cantidad=cantidad, nota=nota, usuario_id=usuario_id,
    ))


# ─── Operaciones públicas ──────────────────────────────────────────────────

def cargar_compra_pendiente(
    db: Session, *, material_id: int, proveedor_id: int, cantidad: float,
    nota: Optional[str] = None, usuario_id: Optional[int] = None,
):
    """Compra registrada, mercadería sigue en el proveedor."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    _validar_material(db, material_id)
    prov = db.query(models.Proveedor).filter(models.Proveedor.id == proveedor_id).first()
    if not prov:
        raise ValueError(f"Proveedor id={proveedor_id} no existe")
    fila = _fila_stock(db, material_id, models.UbicacionStockTipo.comprado_no_retirado, proveedor_id)
    fila.cantidad = (fila.cantidad or 0) + cantidad
    _registrar_movimiento(db, material_id=material_id, obra_id=None,
                         tipo="ingreso_pendiente", cantidad=cantidad,
                         nota=nota or f"Compra pendiente de retiro - prov {proveedor_id}",
                         usuario_id=usuario_id)
    db.commit()


def retirar_de_proveedor(
    db: Session, *, material_id: int, proveedor_id: int, cantidad: float,
    destino_tipo: str, destino_obra_id: Optional[int] = None,
    nota: Optional[str] = None, usuario_id: Optional[int] = None,
):
    """Mueve mercadería desde 'comprado_no_retirado' hacia depósito propio o directo a obra."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    _validar_material(db, material_id)
    if destino_tipo not in ("deposito_propio", "en_obra"):
        raise ValueError("destino_tipo debe ser 'deposito_propio' o 'en_obra'")
    if destino_tipo == "en_obra" and not destino_obra_id:
        raise ValueError("Si destino es 'en_obra' hay que pasar destino_obra_id")
    if destino_tipo == "en_obra":
        obra = db.query(models.Obra).filter(models.Obra.id == destino_obra_id).first()
        if not obra:
            raise ValueError(f"Obra id={destino_obra_id} no existe")

    origen = _fila_stock(db, material_id, models.UbicacionStockTipo.comprado_no_retirado, proveedor_id)
    if (origen.cantidad or 0) < cantidad:
        raise ValueError(
            f"No hay suficiente pendiente de retiro en el proveedor. Disponible: {origen.cantidad}"
        )
    origen.cantidad -= cantidad

    destino_ubicacion = (
        models.UbicacionStockTipo.deposito_propio
        if destino_tipo == "deposito_propio"
        else models.UbicacionStockTipo.en_obra
    )
    destino_ref = None if destino_tipo == "deposito_propio" else destino_obra_id
    destino = _fila_stock(db, material_id, destino_ubicacion, destino_ref)
    destino.cantidad = (destino.cantidad or 0) + cantidad

    _registrar_movimiento(db, material_id=material_id, obra_id=destino_obra_id,
                         tipo="retiro_proveedor", cantidad=cantidad,
                         nota=nota or f"Retiro de proveedor {proveedor_id} hacia {destino_tipo}",
                         usuario_id=usuario_id)
    _recalc_material_stock(db, material_id)
    db.commit()


def consumir_en_obra(
    db: Session, *, material_id: int, obra_id: int, cantidad: float,
    nota: Optional[str] = None, usuario_id: Optional[int] = None,
):
    """Resta de en_obra (cuadrilla consumió el material)."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    _validar_material(db, material_id)
    fila = _fila_stock(db, material_id, models.UbicacionStockTipo.en_obra, obra_id)
    if (fila.cantidad or 0) < cantidad:
        raise ValueError(
            f"No hay suficiente stock en obra {obra_id}. Disponible: {fila.cantidad}"
        )
    fila.cantidad -= cantidad
    _registrar_movimiento(db, material_id=material_id, obra_id=obra_id,
                         tipo="consumo", cantidad=cantidad,
                         nota=nota or f"Consumo en obra {obra_id}",
                         usuario_id=usuario_id)
    _recalc_material_stock(db, material_id)
    db.commit()


def transferir_stock(
    db: Session, *, material_id: int, cantidad: float,
    origen_tipo: str, origen_obra_id: Optional[int],
    destino_tipo: str, destino_obra_id: Optional[int],
    nota: Optional[str] = None, usuario_id: Optional[int] = None,
):
    """Mueve stock entre depósito propio y obras (o entre obras)."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    if origen_tipo not in ("deposito_propio", "en_obra"):
        raise ValueError("origen_tipo debe ser 'deposito_propio' o 'en_obra'")
    if destino_tipo not in ("deposito_propio", "en_obra"):
        raise ValueError("destino_tipo debe ser 'deposito_propio' o 'en_obra'")
    if origen_tipo == destino_tipo and origen_obra_id == destino_obra_id:
        raise ValueError("Origen y destino son la misma ubicación")
    _validar_material(db, material_id)

    origen_ub = (
        models.UbicacionStockTipo.deposito_propio
        if origen_tipo == "deposito_propio"
        else models.UbicacionStockTipo.en_obra
    )
    origen_ref = None if origen_tipo == "deposito_propio" else origen_obra_id
    origen = _fila_stock(db, material_id, origen_ub, origen_ref)
    if (origen.cantidad or 0) < cantidad:
        raise ValueError(
            f"No hay suficiente stock en {origen_tipo}. Disponible: {origen.cantidad}"
        )
    origen.cantidad -= cantidad

    destino_ub = (
        models.UbicacionStockTipo.deposito_propio
        if destino_tipo == "deposito_propio"
        else models.UbicacionStockTipo.en_obra
    )
    destino_ref = None if destino_tipo == "deposito_propio" else destino_obra_id
    destino = _fila_stock(db, material_id, destino_ub, destino_ref)
    destino.cantidad = (destino.cantidad or 0) + cantidad

    _registrar_movimiento(db, material_id=material_id, obra_id=destino_obra_id or origen_obra_id,
                         tipo="transferencia", cantidad=cantidad,
                         nota=nota or f"Transferencia {origen_tipo} → {destino_tipo}",
                         usuario_id=usuario_id)
    _recalc_material_stock(db, material_id)
    db.commit()


# ─── Lectura ───────────────────────────────────────────────────────────────

# ─── Sprint 14: agendar y registrar retiros ────────────────────────────────


def agendar_retiro(
    db: Session, *, stock_material_id: int, fecha_retirar: date,
) -> models.StockMaterial:
    """Agenda una fecha para ir a buscar la mercadería pendiente."""
    fila = db.query(models.StockMaterial).filter(
        models.StockMaterial.id == stock_material_id,
    ).first()
    if not fila:
        raise ValueError(f"StockMaterial id={stock_material_id} no existe")
    if fila.ubicacion_tipo != models.UbicacionStockTipo.comprado_no_retirado:
        raise ValueError("Solo se puede agendar retiro de stock 'comprado_no_retirado'")
    fila.fecha_retirar = fecha_retirar
    fila.retiro_alertado_at = None  # rearmar alerta si cambian la fecha
    db.commit()
    return fila


def marcar_retirado(
    db: Session,
    *,
    stock_material_id: int,
    cantidad: float,
    fecha_retiro: Optional[date] = None,
    forma_pago: Optional[models.MedioPago] = None,
    en_negro: bool = False,
    comprobante_id: Optional[int] = None,
    destino_tipo: str = "deposito_propio",
    destino_obra_id: Optional[int] = None,
    notas: Optional[str] = None,
    usuario_id: Optional[int] = None,
) -> models.RetiroMaterial:
    """Efectivo retiro: mueve stock + crea RetiroMaterial con detalles de pago."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    if destino_tipo not in ("deposito_propio", "en_obra"):
        raise ValueError("destino_tipo debe ser 'deposito_propio' o 'en_obra'")
    if destino_tipo == "en_obra" and not destino_obra_id:
        raise ValueError("Si destino es 'en_obra' hay que pasar destino_obra_id")

    origen = db.query(models.StockMaterial).filter(
        models.StockMaterial.id == stock_material_id,
    ).first()
    if not origen:
        raise ValueError(f"StockMaterial id={stock_material_id} no existe")
    if origen.ubicacion_tipo != models.UbicacionStockTipo.comprado_no_retirado:
        raise ValueError("La fila origen debe ser 'comprado_no_retirado'")
    if (origen.cantidad or 0) < cantidad:
        raise ValueError(
            f"No hay suficiente pendiente de retiro. Disponible: {origen.cantidad}"
        )

    # Validar obra destino
    if destino_tipo == "en_obra":
        obra = db.query(models.Obra).filter(models.Obra.id == destino_obra_id).first()
        if not obra:
            raise ValueError(f"Obra id={destino_obra_id} no existe")

    # Validar comprobante (si vino)
    if comprobante_id is not None:
        cmp = db.query(models.Comprobante).filter(
            models.Comprobante.id == comprobante_id
        ).first()
        if not cmp:
            raise ValueError(f"Comprobante id={comprobante_id} no existe")

    proveedor_id = origen.ubicacion_ref

    # 1) Bajar de comprado_no_retirado
    origen.cantidad = (origen.cantidad or 0) - cantidad
    # Si quedó en 0, limpiar agenda de retiro (no tiene sentido)
    if origen.cantidad <= 0:
        origen.cantidad = 0
        origen.fecha_retirar = None
        origen.retiro_alertado_at = None

    # 2) Subir destino
    destino_ub = (
        models.UbicacionStockTipo.deposito_propio
        if destino_tipo == "deposito_propio"
        else models.UbicacionStockTipo.en_obra
    )
    destino_ref = None if destino_tipo == "deposito_propio" else destino_obra_id
    destino = _fila_stock(db, origen.material_id, destino_ub, destino_ref)
    destino.cantidad = (destino.cantidad or 0) + cantidad

    # 3) Registrar histórico
    retiro = models.RetiroMaterial(
        material_id=origen.material_id,
        proveedor_id=proveedor_id,
        obra_destino_id=destino_obra_id if destino_tipo == "en_obra" else None,
        cantidad=cantidad,
        fecha_retiro=fecha_retiro or date.today(),
        forma_pago=forma_pago,
        en_negro=bool(en_negro),
        comprobante_id=comprobante_id,
        notas=notas,
        created_by_id=usuario_id,
    )
    db.add(retiro)

    # 4) Auditoría en movimientos_material
    _registrar_movimiento(
        db, material_id=origen.material_id,
        obra_id=destino_obra_id if destino_tipo == "en_obra" else None,
        tipo="retiro_proveedor", cantidad=cantidad,
        nota=notas or f"Retiro de proveedor {proveedor_id} hacia {destino_tipo}"
             + (" (negro)" if en_negro else ""),
        usuario_id=usuario_id,
    )

    _recalc_material_stock(db, origen.material_id)
    db.commit()
    db.refresh(retiro)
    return retiro


def pendientes_retiro_proximos(
    db: Session, dias: int = 7, incluir_sin_fecha: bool = False,
) -> List[models.StockMaterial]:
    """Stock pendiente de retiro con fecha_retirar dentro de N días.

    Si `incluir_sin_fecha=True` también devuelve los que están agendados sin fecha.
    Orden: por fecha_retirar ascendente, los sin fecha al final.
    """
    today = date.today()
    horizonte = today + timedelta(days=dias)
    q = db.query(models.StockMaterial).filter(
        models.StockMaterial.ubicacion_tipo
        == models.UbicacionStockTipo.comprado_no_retirado,
        models.StockMaterial.cantidad > 0,
    )
    if not incluir_sin_fecha:
        q = q.filter(
            models.StockMaterial.fecha_retirar.isnot(None),
            models.StockMaterial.fecha_retirar <= horizonte,
        )
    return q.order_by(
        models.StockMaterial.fecha_retirar.asc().nullslast(),
    ).all()


def listar_retiros(
    db: Session,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    obra_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    limit: int = 200,
) -> List[models.RetiroMaterial]:
    q = db.query(models.RetiroMaterial)
    if desde is not None:
        q = q.filter(models.RetiroMaterial.fecha_retiro >= desde)
    if hasta is not None:
        q = q.filter(models.RetiroMaterial.fecha_retiro <= hasta)
    if obra_id is not None:
        q = q.filter(models.RetiroMaterial.obra_destino_id == obra_id)
    if proveedor_id is not None:
        q = q.filter(models.RetiroMaterial.proveedor_id == proveedor_id)
    return q.order_by(models.RetiroMaterial.fecha_retiro.desc()).limit(limit).all()


def breakdown_por_material(db: Session, material_id: Optional[int] = None) -> List[dict]:
    """Devuelve lista de dicts compatibles con MaterialConStockOut."""
    q = db.query(models.Material)
    if material_id is not None:
        q = q.filter(models.Material.id == material_id)
    out = []
    for m in q.all():
        ubicaciones_raw = db.query(models.StockMaterial).filter(
            models.StockMaterial.material_id == m.id,
        ).all()
        ubicaciones = []
        total_disponible = 0.0
        pendiente = 0.0
        for u in ubicaciones_raw:
            nombre = None
            if u.ubicacion_tipo == models.UbicacionStockTipo.en_obra and u.ubicacion_ref:
                obra = db.query(models.Obra).filter(models.Obra.id == u.ubicacion_ref).first()
                nombre = obra.nombre if obra else f"Obra {u.ubicacion_ref}"
            elif u.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado and u.ubicacion_ref:
                prov = db.query(models.Proveedor).filter(models.Proveedor.id == u.ubicacion_ref).first()
                nombre = prov.nombre if prov else f"Proveedor {u.ubicacion_ref}"
            elif u.ubicacion_tipo == models.UbicacionStockTipo.deposito_propio:
                nombre = "Depósito propio"
            ubicaciones.append({
                "stock_material_id": u.id,  # Sprint 14: id de la fila StockMaterial para acciones
                "ubicacion_tipo": u.ubicacion_tipo.value if hasattr(u.ubicacion_tipo, "value") else u.ubicacion_tipo,
                "ubicacion_ref": u.ubicacion_ref,
                "ubicacion_nombre": nombre,
                "cantidad": float(u.cantidad or 0),
                "fecha_retirar": u.fecha_retirar,  # Sprint 14
            })
            if u.ubicacion_tipo in (models.UbicacionStockTipo.deposito_propio, models.UbicacionStockTipo.en_obra):
                total_disponible += float(u.cantidad or 0)
            elif u.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado:
                pendiente += float(u.cantidad or 0)
        out.append({
            "id": m.id, "nombre": m.nombre, "categoria": m.categoria, "unidad": m.unidad,
            "stock": float(m.stock or 0), "stock_minimo": float(m.stock_minimo or 0),
            "precio_unitario": float(m.precio_unitario or 0), "proveedor_id": m.proveedor_id,
            "icono": m.icono,
            "stock_total_disponible": total_disponible,
            "stock_pendiente_retiro": pendiente,
            "ubicaciones": ubicaciones,
        })
    return out
