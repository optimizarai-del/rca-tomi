"""Servicio de presupuestos de materiales por obra (Sprint 10).

Centraliza la lógica para mantener consistente `total_estimado` y las
transiciones de estado borrador → aprobado → cerrado.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app import models


def _calcular_total(p: models.Presupuesto) -> float:
    return float(sum((i.subtotal or 0) for i in p.items))


def _resolve_precio(db: Session, material_id: int, precio_pasado: Optional[float]) -> float:
    """Si no se pasa precio, usa el del Material."""
    if precio_pasado is not None and precio_pasado >= 0:
        return float(precio_pasado)
    m = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not m:
        raise ValueError(f"Material id={material_id} no existe")
    return float(m.precio_unitario or 0)


def crear_presupuesto(
    db: Session, *, obra_id: int, nombre: str,
    items: Optional[List[dict]] = None,
    notas: Optional[str] = None,
    created_by_id: Optional[int] = None,
) -> models.Presupuesto:
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if not obra:
        raise ValueError(f"Obra id={obra_id} no existe")
    if not nombre or not nombre.strip():
        raise ValueError("nombre es requerido")
    p = models.Presupuesto(
        obra_id=obra_id, nombre=nombre.strip(),
        estado=models.EstadoPresupuesto.borrador,
        notas=notas, created_by_id=created_by_id,
    )
    db.add(p); db.flush()

    for it in (items or []):
        if it.get("cantidad", 0) <= 0:
            raise ValueError(f"Cantidad inválida para material_id={it.get('material_id')}")
        material_id = it["material_id"]
        cant = float(it["cantidad"])
        precio = _resolve_precio(db, material_id, it.get("precio_unitario_estimado"))
        db.add(models.PresupuestoItem(
            presupuesto_id=p.id, material_id=material_id, cantidad=cant,
            precio_unitario_estimado=precio, subtotal=cant * precio,
        ))
    db.flush()
    p.total_estimado = _calcular_total(p)
    db.commit(); db.refresh(p)
    return p


def agregar_item(
    db: Session, *, presupuesto_id: int, material_id: int, cantidad: float,
    precio_unitario_estimado: Optional[float] = None,
) -> models.Presupuesto:
    p = db.query(models.Presupuesto).filter(models.Presupuesto.id == presupuesto_id).first()
    if not p:
        raise ValueError(f"Presupuesto id={presupuesto_id} no existe")
    if p.estado != models.EstadoPresupuesto.borrador:
        raise ValueError("Solo se pueden agregar items a presupuestos en borrador")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser positiva")
    precio = _resolve_precio(db, material_id, precio_unitario_estimado)
    db.add(models.PresupuestoItem(
        presupuesto_id=p.id, material_id=material_id, cantidad=float(cantidad),
        precio_unitario_estimado=precio, subtotal=cantidad * precio,
    ))
    db.flush()
    p.total_estimado = _calcular_total(p)
    db.commit(); db.refresh(p)
    return p


def aprobar_presupuesto(db: Session, *, presupuesto_id: int) -> models.Presupuesto:
    p = db.query(models.Presupuesto).filter(models.Presupuesto.id == presupuesto_id).first()
    if not p:
        raise ValueError(f"Presupuesto id={presupuesto_id} no existe")
    if p.estado != models.EstadoPresupuesto.borrador:
        raise ValueError("Solo se pueden aprobar presupuestos en borrador")
    if not p.items:
        raise ValueError("Un presupuesto vacío no se puede aprobar")
    p.estado = models.EstadoPresupuesto.aprobado
    p.aprobado_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return p


def serialize(p: models.Presupuesto, db: Session) -> dict:
    items = []
    for i in p.items:
        mat = db.query(models.Material).filter(models.Material.id == i.material_id).first()
        items.append({
            "id": i.id, "material_id": i.material_id,
            "material_nombre": mat.nombre if mat else f"Material {i.material_id}",
            "cantidad": float(i.cantidad), "precio_unitario_estimado": float(i.precio_unitario_estimado),
            "subtotal": float(i.subtotal),
        })
    return {
        "id": p.id, "obra_id": p.obra_id,
        "obra_nombre": p.obra.nombre if p.obra else f"Obra {p.obra_id}",
        "nombre": p.nombre,
        "estado": p.estado.value if hasattr(p.estado, "value") else p.estado,
        "total_estimado": float(p.total_estimado or 0),
        "notas": p.notas, "created_at": p.created_at, "aprobado_at": p.aprobado_at,
        "items": items,
    }
