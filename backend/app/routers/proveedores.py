"""Proveedores — Sprint 1 base + Sprint 15 detalle (materiales que vende, historial)."""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models, schemas
from app.database import get_db
from app.security import get_current_user, require_admin, scope_demo, stamp_demo

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


def _ultima_actividad(db: Session, pid: int) -> Optional[date]:
    """Max(fecha) entre retiros del proveedor y presupuestos con sus materiales."""
    ult_retiro = db.query(func.max(models.RetiroMaterial.fecha_retiro)).filter(
        models.RetiroMaterial.proveedor_id == pid
    ).scalar()
    ult_presup = db.query(func.max(models.Presupuesto.created_at)).join(
        models.PresupuestoItem, models.PresupuestoItem.presupuesto_id == models.Presupuesto.id
    ).join(
        models.Material, models.Material.id == models.PresupuestoItem.material_id
    ).filter(models.Material.proveedor_id == pid).scalar()
    fechas = [f for f in (ult_retiro, ult_presup.date() if ult_presup else None) if f]
    return max(fechas) if fechas else None


@router.get("", response_model=List[schemas.ProveedorOut])
def list_proveedores(
    activos_meses: int = 12,
    incluir_inactivos: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Lista proveedores. Por default oculta los inactivos hace +12 meses (sin retiros
    ni items en presupuestos). Param `incluir_inactivos=true` para verlos todos.

    Sprint 15: nota del usuario era "los que tengan +1 año los elimine (no borrar
    pero si no mostrar en pantalla)". `activos_meses=0` o `incluir_inactivos=true`
    desactivan el filtro.
    """
    q = scope_demo(db.query(models.Proveedor), models.Proveedor, user)
    proveedores = q.order_by(models.Proveedor.nombre).all()

    if incluir_inactivos or activos_meses <= 0:
        return proveedores

    horizonte = date.today() - timedelta(days=int(activos_meses * 30.4))
    out = []
    for p in proveedores:
        ult = _ultima_actividad(db, p.id)
        # Si no tiene actividad registrada, lo mostramos (es nuevo o sin uso aún).
        # Si la tiene y es vieja, lo ocultamos.
        if ult is None or ult >= horizonte:
            out.append(p)
    return out


@router.post("", response_model=schemas.ProveedorOut, status_code=201)
def create_proveedor(data: schemas.ProveedorIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = models.Proveedor(**data.model_dump())
    stamp_demo(p, user)
    db.add(p); db.commit(); db.refresh(p)
    return p


# Sprint 15: detalle del proveedor (path fijo → antes de /{pid}).


@router.get("/{pid}/detalle", response_model=schemas.ProveedorDetalleOut)
def detalle_proveedor(
    pid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    p = scope_demo(db.query(models.Proveedor), models.Proveedor, user).filter(
        models.Proveedor.id == pid
    ).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    materiales = _materiales_vendidos(db, pid)
    base = schemas.ProveedorOut.model_validate(p)
    return schemas.ProveedorDetalleOut(
        **base.model_dump(),
        materiales_vendidos=materiales,
        ultima_actividad=_ultima_actividad(db, pid),
    )


def _materiales_vendidos(db: Session, pid: int) -> List[schemas.ProveedorMaterialOut]:
    materiales = db.query(models.Material).filter(
        models.Material.proveedor_id == pid
    ).order_by(models.Material.nombre).all()

    out: List[schemas.ProveedorMaterialOut] = []
    for m in materiales:
        # Pendiente de retiro EN ESE PROVEEDOR
        pend = db.query(func.coalesce(func.sum(models.StockMaterial.cantidad), 0)).filter(
            models.StockMaterial.material_id == m.id,
            models.StockMaterial.ubicacion_tipo == models.UbicacionStockTipo.comprado_no_retirado,
            models.StockMaterial.ubicacion_ref == pid,
        ).scalar() or 0
        out.append(schemas.ProveedorMaterialOut(
            material_id=m.id, nombre=m.nombre, categoria=m.categoria,
            unidad=m.unidad, precio_unitario=float(m.precio_unitario or 0),
            stock_actual=float(m.stock or 0),
            pendiente_retiro=float(pend),
        ))
    return out


@router.get("/{pid}/materiales", response_model=List[schemas.ProveedorMaterialOut])
def materiales_proveedor(
    pid: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Tipos de materiales que vende este proveedor (lo que pidió Tomi)."""
    p = scope_demo(db.query(models.Proveedor), models.Proveedor, user).filter(
        models.Proveedor.id == pid
    ).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")
    return _materiales_vendidos(db, pid)


@router.get("/{pid}/historial", response_model=List[schemas.ProveedorHistorialItem])
def historial_proveedor(
    pid: int,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    incluir_antiguos: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Listado combinado de items facturados (retiros) y presupuestados.

    Default oculta items con fecha > 1 año. `incluir_antiguos=true` para ver todo.
    Orden: fecha descendente.
    """
    p = scope_demo(db.query(models.Proveedor), models.Proveedor, user).filter(
        models.Proveedor.id == pid
    ).first()
    if not p:
        raise HTTPException(404, "Proveedor no encontrado")

    if not incluir_antiguos:
        limite = date.today() - timedelta(days=365)
        if desde is None or desde < limite:
            desde = limite

    items: List[schemas.ProveedorHistorialItem] = []

    # Facturado: retiros efectivos del proveedor (Sprint 14)
    q = db.query(models.RetiroMaterial).filter(models.RetiroMaterial.proveedor_id == pid)
    if desde:
        q = q.filter(models.RetiroMaterial.fecha_retiro >= desde)
    if hasta:
        q = q.filter(models.RetiroMaterial.fecha_retiro <= hasta)
    for r in q.all():
        material = db.query(models.Material).filter(models.Material.id == r.material_id).first()
        obra = (
            db.query(models.Obra).filter(models.Obra.id == r.obra_destino_id).first()
            if r.obra_destino_id else None
        )
        precio = float(material.precio_unitario or 0) if material else 0
        items.append(schemas.ProveedorHistorialItem(
            fecha=r.fecha_retiro,
            tipo="facturado",
            material_id=r.material_id,
            material_nombre=material.nombre if material else f"#{r.material_id}",
            unidad=material.unidad if material else "u",
            cantidad=float(r.cantidad),
            precio_unitario=precio,
            subtotal=float(r.cantidad) * precio if precio else None,
            en_negro=r.en_negro,
            forma_pago=r.forma_pago,
            obra_destino_nombre=obra.nombre if obra else None,
            ref_id=r.id,
        ))

    # Presupuestado: items de presupuestos cuyo material apunta a este proveedor
    q2 = (
        db.query(models.PresupuestoItem, models.Presupuesto, models.Material)
        .join(models.Presupuesto, models.PresupuestoItem.presupuesto_id == models.Presupuesto.id)
        .join(models.Material, models.PresupuestoItem.material_id == models.Material.id)
        .filter(models.Material.proveedor_id == pid)
    )
    if desde:
        q2 = q2.filter(func.date(models.Presupuesto.created_at) >= desde)
    if hasta:
        q2 = q2.filter(func.date(models.Presupuesto.created_at) <= hasta)
    for item, presupuesto, material in q2.all():
        items.append(schemas.ProveedorHistorialItem(
            fecha=presupuesto.created_at.date() if presupuesto.created_at else date.today(),
            tipo="presupuestado",
            material_id=material.id,
            material_nombre=material.nombre,
            unidad=material.unidad,
            cantidad=float(item.cantidad),
            precio_unitario=float(item.precio_unitario_estimado or 0),
            subtotal=float(item.subtotal or 0),
            presupuesto_nombre=presupuesto.nombre,
            presupuesto_estado=presupuesto.estado.value if hasattr(presupuesto.estado, "value") else str(presupuesto.estado),
            ref_id=item.id,
        ))

    # Pago directo: MovimientoObra tipo=EGRESO con proveedor_id=pid
    # (sprint 23: cierra la conexión cliente↔proveedor también cuando el pago
    # se cargó como Movimiento directo, sin pasar por RetiroMaterial).
    q3 = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.proveedor_id == pid,
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO,
    )
    if desde:
        q3 = q3.filter(models.MovimientoObra.fecha >= desde)
    if hasta:
        q3 = q3.filter(models.MovimientoObra.fecha <= hasta)
    for mo in q3.all():
        obra = db.query(models.Obra).filter(models.Obra.id == mo.obra_id).first()
        es_negro = mo.legalidad == models.LegalidadMovimiento.negro if mo.legalidad else False
        items.append(schemas.ProveedorHistorialItem(
            fecha=mo.fecha,
            tipo="pago_directo",
            material_id=0,  # no aplica
            material_nombre=mo.concepto[:100],
            unidad="—",
            cantidad=1,
            precio_unitario=float(mo.monto),
            subtotal=float(mo.monto),
            en_negro=es_negro,
            forma_pago=mo.medio_pago,
            obra_destino_nombre=obra.codigo if obra else None,
            ref_id=mo.id,
        ))

    items.sort(key=lambda it: it.fecha, reverse=True)
    return items


@router.put("/{pid}", response_model=schemas.ProveedorOut)
def update_proveedor(pid: int, data: schemas.ProveedorIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = db.query(models.Proveedor).filter(models.Proveedor.id == pid).first()
    if not p: raise HTTPException(404, "Proveedor no encontrado")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return p


@router.delete("/{pid}", status_code=204)
def delete_proveedor(pid: int, db: Session = Depends(get_db), user: models.User = Depends(require_admin)):
    p = db.query(models.Proveedor).filter(models.Proveedor.id == pid).first()
    if not p: raise HTTPException(404, "Proveedor no encontrado")
    db.delete(p); db.commit()
