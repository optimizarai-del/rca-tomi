"""Tool registry del agente operario IA — Sprint 1.5: lectura sobre nuevo modelo financiero.

Tools nuevas vs. anteriores:
- listar_obras (actualizado: incluye datos de cliente y régimen)
- obtener_obra (incluye saldo, etapas, aportes pendientes)
- listar_clientes (NUEVO)
- listar_etapas (NUEVO)
- listar_movimientos (NUEVO — reemplaza gastos)
- saldo_obra (NUEVO)
- flujo_caja_obra (NUEVO)
- aportes_pendientes (NUEVO)
- cheques_a_vencer (NUEVO)
- descalce_fiscal (NUEVO — admin/finanzas)
- dashboard_hud (actualizado)
- alertas_stock_bajo (mantenida)
- listar_proveedores (mantenida)
- listar_cuadrillas (mantenida — capa lúdica)
- eventos_recientes (mantenida)
- listar_usuarios (mantenida — admin)
"""
from __future__ import annotations
from typing import Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from app import models
from app.security import ADMIN_ROLES, FINANZAS_ROLES


# ─── Helpers ───
def _obra_by_ref(ref, db: Session) -> models.Obra | None:
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        o = db.query(models.Obra).filter(models.Obra.id == int(ref)).first()
        if o:
            return o
    if isinstance(ref, str):
        low = ref.strip()
        o = db.query(models.Obra).filter(func.lower(models.Obra.codigo) == low.lower()).first()
        if o:
            return o
        return db.query(models.Obra).filter(models.Obra.nombre.ilike(f"%{low}%")).first()
    return None


def _saldo_obra(db: Session, oid: int) -> dict:
    rows = db.query(
        models.MovimientoObra.tipo,
        func.coalesce(func.sum(models.MovimientoObra.monto), 0),
    ).filter(models.MovimientoObra.obra_id == oid).group_by(models.MovimientoObra.tipo).all()
    ingresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.INGRESO), 0.0)
    egresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.EGRESO), 0.0)
    return {"ingresos": ingresos, "egresos": egresos, "saldo": ingresos - egresos}


def _serialize_obra(o: models.Obra, db: Session = None) -> dict:
    data = {
        "id": o.id,
        "codigo": o.codigo,
        "nombre": o.nombre,
        "ciudad": o.ciudad,
        "cliente_id": o.cliente_id,
        "cliente_nombre": o.cliente.nombre if o.cliente else None,
        "estado": o.estado.value if o.estado else None,
        "salud": o.salud.value if o.salud else None,
        "tipo_facturacion": o.tipo_facturacion.value if o.tipo_facturacion else None,
        "monto_contrato": float(o.monto_contrato or 0),
        "progreso": round(o.progreso or 0, 1),
        "fecha_inicio": o.fecha_inicio.isoformat() if o.fecha_inicio else None,
        "fecha_fin_estimada": o.fecha_fin_estimada.isoformat() if o.fecha_fin_estimada else None,
    }
    if db is not None:
        s = _saldo_obra(db, o.id)
        data.update({
            "total_ingresos": s["ingresos"],
            "total_egresos": s["egresos"],
            "saldo": s["saldo"],
        })
    return data


# ════════════════════════════════════════════════════════════════════
# TOOL HANDLERS
# ════════════════════════════════════════════════════════════════════

def t_listar_obras(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Obra)
    if estado := input.get("estado"):
        try:
            q = q.filter(models.Obra.estado == models.ObraStatus(estado))
        except ValueError:
            return {"error": f"estado inválido: {estado}. Valores: EN_CURSO, PAUSADA, FINALIZADA, CANCELADA"}
    obras = q.order_by(models.Obra.created_at.desc()).limit(50).all()
    return {"total": len(obras), "obras": [_serialize_obra(o, db) for o in obras]}


def t_obtener_obra(input: dict, user: models.User, db: Session) -> dict:
    ref = input.get("referencia")
    if not ref:
        return {"error": "Falta 'referencia' (id, código o nombre)"}
    o = _obra_by_ref(ref, db)
    if not o:
        return {"error": f"No encontré obra '{ref}'"}
    data = _serialize_obra(o, db)

    # Etapas
    etapas = db.query(models.EtapaObra).filter(
        models.EtapaObra.obra_id == o.id
    ).order_by(models.EtapaObra.nro_etapa).all()
    data["etapas"] = [
        {
            "id": e.id, "nombre": e.nombre, "nro": e.nro_etapa,
            "estado": e.estado.value, "monto": float(e.monto_contractual or 0),
            "fecha_estimada": e.fecha_estimada.isoformat() if e.fecha_estimada else None,
        }
        for e in etapas
    ]

    # Aportes pendientes
    aportes_pend = db.query(models.AporteSocio).filter(
        models.AporteSocio.obra_id == o.id,
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL,
    ).all()
    data["aportes_pendientes_total"] = sum(
        float(a.monto) - float(a.monto_devuelto) for a in aportes_pend
    )
    data["aportes_pendientes_count"] = len(aportes_pend)

    # Cheques a vencer
    today = date.today()
    cheques = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == o.id,
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque > today,
    ).all()
    data["cheques_a_vencer_total"] = sum(float(c.monto) for c in cheques)
    data["cheques_a_vencer_count"] = len(cheques)

    # Eventos recientes
    eventos = db.query(models.Evento).filter(
        models.Evento.obra_id == o.id
    ).order_by(models.Evento.fecha.desc()).limit(5).all()
    data["eventos_recientes"] = [
        {"tipo": e.tipo.value, "titulo": e.titulo, "es_critico": e.es_critico,
         "fecha": e.fecha.isoformat() if e.fecha else None}
        for e in eventos
    ]
    return data


def t_listar_clientes(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Cliente).filter(models.Cliente.activo == True)  # noqa: E712
    if tipo := input.get("tipo"):
        q = q.filter(models.Cliente.tipo == tipo)
    clientes = q.order_by(models.Cliente.nombre).all()
    return {
        "total": len(clientes),
        "clientes": [
            {
                "id": c.id, "nombre": c.nombre, "cuit": c.cuit, "tipo": c.tipo,
                "regimen": c.regimen_fiscal.codigo if c.regimen_fiscal else None,
                "obras_count": len(c.obras),
            }
            for c in clientes
        ],
    }


def t_listar_etapas(input: dict, user: models.User, db: Session) -> dict:
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra' (id, código o nombre)"}
    o = _obra_by_ref(obra_ref, db)
    if not o:
        return {"error": f"Obra '{obra_ref}' no encontrada"}
    etapas = db.query(models.EtapaObra).filter(
        models.EtapaObra.obra_id == o.id
    ).order_by(models.EtapaObra.nro_etapa).all()
    return {
        "obra": o.nombre,
        "total": len(etapas),
        "etapas": [
            {
                "id": e.id, "nombre": e.nombre, "nro": e.nro_etapa,
                "monto_contractual": float(e.monto_contractual or 0),
                "estado": e.estado.value,
                "fecha_estimada": e.fecha_estimada.isoformat() if e.fecha_estimada else None,
                "fecha_cobro_real": e.fecha_cobro_real.isoformat() if e.fecha_cobro_real else None,
            }
            for e in etapas
        ],
    }


def t_listar_movimientos(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.MovimientoObra)
    if obra_ref := input.get("obra"):
        o = _obra_by_ref(obra_ref, db)
        if not o:
            return {"error": f"Obra '{obra_ref}' no encontrada"}
        q = q.filter(models.MovimientoObra.obra_id == o.id)
    if tipo := input.get("tipo"):
        try:
            q = q.filter(models.MovimientoObra.tipo == models.TipoMovimiento(tipo))
        except ValueError:
            return {"error": f"tipo inválido: {tipo}. Valores: INGRESO, EGRESO"}
    if categoria := input.get("categoria"):
        try:
            q = q.filter(models.MovimientoObra.categoria_egreso == models.CategoriaEgreso(categoria))
        except ValueError:
            return {"error": f"categoría inválida: {categoria}"}
    if input.get("solo_a_revisar"):
        q = q.filter(models.MovimientoObra.estado == models.EstadoMovimiento.A_REVISAR)
    limit = min(int(input.get("limit", 30)), 100)
    movs = q.order_by(models.MovimientoObra.fecha.desc()).limit(limit).all()
    return {
        "total": len(movs),
        "movimientos": [
            {
                "id": m.id, "obra_id": m.obra_id, "fecha": m.fecha.isoformat(),
                "tipo": m.tipo.value, "concepto": m.concepto, "monto": float(m.monto),
                "medio_pago": m.medio_pago.value,
                "categoria": m.categoria_egreso.value if m.categoria_egreso else None,
                "origen": m.origen_ingreso.value if m.origen_ingreso else None,
                "tiene_comprobante": m.tiene_comprobante,
                "estado": m.estado.value,
                "hoja_fisica": m.hoja_fisica,
            }
            for m in movs
        ],
    }


def t_saldo_obra(input: dict, user: models.User, db: Session) -> dict:
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    o = _obra_by_ref(obra_ref, db)
    if not o:
        return {"error": f"Obra '{obra_ref}' no encontrada"}
    s = _saldo_obra(db, o.id)
    return {
        "obra": o.nombre,
        "monto_contrato": float(o.monto_contrato or 0),
        "total_ingresos": s["ingresos"],
        "total_egresos": s["egresos"],
        "saldo": s["saldo"],
        "porcentaje_ejecutado": round((s["egresos"] / float(o.monto_contrato) * 100), 1) if o.monto_contrato else 0,
    }


def t_flujo_caja_obra(input: dict, user: models.User, db: Session) -> dict:
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    o = _obra_by_ref(obra_ref, db)
    if not o:
        return {"error": f"Obra '{obra_ref}' no encontrada"}
    movs = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.obra_id == o.id
    ).order_by(models.MovimientoObra.fecha).all()
    semanas: dict[date, dict] = {}
    for m in movs:
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
    return {"obra": o.nombre, "semanas": out}


def t_aportes_pendientes(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.AporteSocio).filter(
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL
    )
    if obra_ref := input.get("obra"):
        o = _obra_by_ref(obra_ref, db)
        if o:
            q = q.filter(models.AporteSocio.obra_id == o.id)
    aportes = q.all()
    return {
        "total_aportes": len(aportes),
        "monto_total_pendiente": sum(float(a.monto) - float(a.monto_devuelto) for a in aportes),
        "aportes": [
            {
                "id": a.id, "obra_id": a.obra_id,
                "socio": a.socio.name + " " + (a.socio.last_name or "") if a.socio else None,
                "monto": float(a.monto),
                "monto_devuelto": float(a.monto_devuelto),
                "pendiente": float(a.monto) - float(a.monto_devuelto),
                "motivo": a.motivo,
                "fecha_aporte": a.fecha_aporte.isoformat(),
                "estado": a.estado_devolucion.value,
            }
            for a in aportes
        ],
    }


def t_cheques_a_vencer(input: dict, user: models.User, db: Session) -> dict:
    dias = min(int(input.get("dias", 30)), 365)
    today = date.today()
    horizonte = today + timedelta(days=dias)
    cheques = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque.isnot(None),
        models.MovimientoObra.fecha_vto_cheque >= today,
        models.MovimientoObra.fecha_vto_cheque <= horizonte,
    ).order_by(models.MovimientoObra.fecha_vto_cheque).all()
    return {
        "horizonte_dias": dias,
        "total_cheques": len(cheques),
        "monto_total": sum(float(c.monto) for c in cheques),
        "cheques": [
            {
                "id": c.id, "obra_id": c.obra_id, "concepto": c.concepto,
                "monto": float(c.monto), "nro": c.nro_cheque, "banco": c.banco,
                "fecha_vto": c.fecha_vto_cheque.isoformat(),
                "dias_restantes": (c.fecha_vto_cheque - today).days,
            }
            for c in cheques
        ],
    }


def t_descalce_fiscal(input: dict, user: models.User, db: Session) -> dict:
    if user.role not in ADMIN_ROLES:
        return {"error": "Requiere rol admin/finanzas"}
    obra_id = input.get("obra_id")
    obras = [db.query(models.Obra).filter(models.Obra.id == obra_id).first()] if obra_id else db.query(models.Obra).all()
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
        out.append({
            "obra": o.nombre,
            "tipo_facturacion": o.tipo_facturacion.value,
            "ingresos_con_comprobante": float(ingresos_cf),
            "egresos_con_comprobante": float(egresos_cf),
            "descalce": descalce,
            "tiene_descalce": descalce > 0,
        })
    return {"total": len(out), "obras": out, "resumen_descalce_total": sum(o["descalce"] for o in out if o["tiene_descalce"])}


def t_dashboard_hud(input: dict, user: models.User, db: Session) -> dict:
    obras = db.query(models.Obra).all()
    monto_contratos = sum(float(o.monto_contrato or 0) for o in obras)
    obras_activas = sum(1 for o in obras if o.estado == models.ObraStatus.EN_CURSO)
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
        models.MovimientoObra.fecha_vto_cheque > date.today(),
    ).scalar() or 0
    materiales_criticos = db.query(models.Material).filter(
        models.Material.stock < models.Material.stock_minimo
    ).count()
    eventos_criticos = db.query(models.Evento).filter(models.Evento.es_critico == True).count()  # noqa: E712
    return {
        "monto_contratos_total": monto_contratos,
        "total_ingresos": float(ingresos),
        "total_egresos": float(egresos),
        "saldo_global": float(ingresos) - float(egresos),
        "aportes_pendientes": float(aportes_pend),
        "cheques_a_vencer": float(cheques_v),
        "obras_total": len(obras),
        "obras_activas": obras_activas,
        "materiales_criticos": materiales_criticos,
        "alertas_total": eventos_criticos,
    }


def t_alertas_stock_bajo(input: dict, user: models.User, db: Session) -> dict:
    mats = db.query(models.Material).filter(
        models.Material.stock < models.Material.stock_minimo
    ).all()
    return {
        "total": len(mats),
        "materiales": [
            {"nombre": m.nombre, "stock": m.stock, "stock_minimo": m.stock_minimo, "unidad": m.unidad}
            for m in mats
        ],
    }


def t_listar_proveedores(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Proveedor)
    if rubro := input.get("rubro"):
        q = q.filter(models.Proveedor.rubro.ilike(f"%{rubro}%"))
    if input.get("solo_morosos"):
        q = q.filter(models.Proveedor.moroso == True)  # noqa: E712
    provs = q.order_by(models.Proveedor.rating.desc()).all()
    return {
        "total": len(provs),
        "proveedores": [
            {"id": p.id, "nombre": p.nombre, "rubro": p.rubro, "rating": p.rating,
             "plazo_dias": p.plazo_entrega_dias, "moroso": p.moroso, "telefono": p.telefono}
            for p in provs
        ],
    }


def t_listar_cuadrillas(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Cuadrilla).filter(models.Cuadrilla.activa == True)  # noqa: E712
    if esp := input.get("especialidad"):
        q = q.filter(models.Cuadrilla.especialidad.ilike(f"%{esp}%"))
    cs = q.order_by(models.Cuadrilla.experiencia.desc()).all()
    return {
        "total": len(cs),
        "cuadrillas": [
            {"id": c.id, "nombre": c.nombre, "especialidad": c.especialidad,
             "miembros": c.cantidad_miembros, "nivel": c.nivel, "xp": c.experiencia,
             "eficiencia": c.eficiencia, "telefono": c.telefono}
            for c in cs
        ],
    }


def t_eventos_recientes(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Evento)
    if obra_ref := input.get("obra"):
        o = _obra_by_ref(obra_ref, db)
        if o:
            q = q.filter(models.Evento.obra_id == o.id)
    if input.get("solo_criticos"):
        q = q.filter(models.Evento.es_critico == True)  # noqa: E712
    limit = min(int(input.get("limit", 20)), 100)
    eventos = q.order_by(models.Evento.fecha.desc()).limit(limit).all()
    return {
        "total": len(eventos),
        "eventos": [
            {"id": e.id, "obra_id": e.obra_id, "tipo": e.tipo.value,
             "titulo": e.titulo, "es_critico": e.es_critico,
             "fecha": e.fecha.isoformat() if e.fecha else None}
            for e in eventos
        ],
    }


def t_listar_usuarios(input: dict, user: models.User, db: Session) -> dict:
    if user.role not in ADMIN_ROLES:
        return {"error": "Requiere rol admin"}
    q = db.query(models.User)
    if rol := input.get("rol"):
        try:
            q = q.filter(models.User.role == models.UserRole(rol))
        except ValueError:
            return {"error": f"rol inválido: {rol}"}
    users = q.all()
    return {
        "total": len(users),
        "usuarios": [
            {"id": u.id, "name": u.name, "email": u.email,
             "role": u.role.value, "telefono": u.phone, "xp": u.xp}
            for u in users
        ],
    }


# ════════════════════════════════════════════════════════════════════
# TOOLS DE ESCRITURA (Sprint 2) — todas en REQUIRES_CONFIRMATION_TOOLS
# ════════════════════════════════════════════════════════════════════

def t_registrar_movimiento(input: dict, user: models.User, db: Session) -> dict:
    """Registra un movimiento financiero (INGRESO o EGRESO) en una obra.

    Validaciones espejo del router POST /api/movimientos:
    - INGRESO requiere origen_ingreso, no debe tener categoria_egreso.
    - EGRESO requiere categoria_egreso, no debe tener origen_ingreso.
    - Cheques (CHEQUE_PROPIO/CHEQUE_TERCERO) requieren nro_cheque + fecha_vto_cheque.
    - Obra TOTAL_BLANCO + INGRESO de cliente requiere comprobante.
    """
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra' (id, código o parte del nombre)"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    tipo_str = input.get("tipo")
    if tipo_str not in ("INGRESO", "EGRESO"):
        return {"error": "tipo debe ser INGRESO o EGRESO"}
    tipo = models.TipoMovimiento(tipo_str)

    try:
        monto = float(input.get("monto", 0))
    except (TypeError, ValueError):
        return {"error": "monto inválido (debe ser número)"}
    if monto <= 0:
        return {"error": "monto debe ser > 0"}

    fecha_str = input.get("fecha")
    if fecha_str:
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            return {"error": "fecha debe estar en formato YYYY-MM-DD"}
    else:
        fecha = date.today()

    concepto = (input.get("concepto") or "").strip()
    if not concepto:
        return {"error": "Falta 'concepto'"}

    medio_str = input.get("medio_pago")
    try:
        medio_pago = models.MedioPago(medio_str)
    except (ValueError, TypeError):
        return {"error": f"medio_pago inválido: {medio_str}. Valores: EFECTIVO, TRANSFERENCIA, CHEQUE_PROPIO, CHEQUE_TERCERO, DEPOSITO_BANCARIO"}

    origen_ingreso = None
    categoria_egreso = None
    if tipo == models.TipoMovimiento.INGRESO:
        origen_str = input.get("origen_ingreso")
        if not origen_str:
            return {"error": "Para INGRESO se requiere origen_ingreso (ANTICIPO_CLIENTE, CERTIFICADO_ETAPA, PAGO_FINAL, AJUSTE_CONTRATO, APORTE_SOCIO_RCA, DEVOLUCION_PROVEEDOR)"}
        try:
            origen_ingreso = models.OrigenIngreso(origen_str)
        except ValueError:
            return {"error": f"origen_ingreso inválido: {origen_str}"}
        if input.get("categoria_egreso"):
            return {"error": "categoria_egreso no aplica en INGRESO"}
    else:
        cat_str = input.get("categoria_egreso")
        if not cat_str:
            return {"error": "Para EGRESO se requiere categoria_egreso (MANO_DE_OBRA, MATERIALES, SUBCONTRATO, SERVICIO_EXTERNO, GASTO_DIRECTO_OBRA, HERRAMIENTA_EQUIPO, APORTE_PRESTAMO)"}
        try:
            categoria_egreso = models.CategoriaEgreso(cat_str)
        except ValueError:
            return {"error": f"categoria_egreso inválida: {cat_str}"}
        if input.get("origen_ingreso"):
            return {"error": "origen_ingreso no aplica en EGRESO"}

    nro_cheque = input.get("nro_cheque")
    banco = input.get("banco")
    fecha_vto_cheque = None
    if medio_pago in (models.MedioPago.CHEQUE_PROPIO, models.MedioPago.CHEQUE_TERCERO):
        if not nro_cheque:
            return {"error": "Cheque requiere nro_cheque"}
        vto_str = input.get("fecha_vto_cheque")
        if not vto_str:
            return {"error": "Cheque requiere fecha_vto_cheque (YYYY-MM-DD)"}
        try:
            fecha_vto_cheque = date.fromisoformat(vto_str)
        except ValueError:
            return {"error": "fecha_vto_cheque debe estar en formato YYYY-MM-DD"}

    comprobante_id = input.get("comprobante_id")
    if (
        obra.tipo_facturacion == models.TipoFacturacion.TOTAL_BLANCO
        and tipo == models.TipoMovimiento.INGRESO
        and origen_ingreso in (
            models.OrigenIngreso.ANTICIPO_CLIENTE,
            models.OrigenIngreso.CERTIFICADO_ETAPA,
            models.OrigenIngreso.PAGO_FINAL,
        )
        and not comprobante_id
    ):
        return {"error": f"Obra '{obra.nombre}' es TOTAL_BLANCO: este ingreso requiere comprobante. Cargá la factura primero con cargar_comprobante."}

    etapa_id = input.get("etapa_id")
    if etapa_id:
        etapa = db.query(models.EtapaObra).filter(
            models.EtapaObra.id == etapa_id,
            models.EtapaObra.obra_id == obra.id,
        ).first()
        if not etapa:
            return {"error": f"Etapa {etapa_id} no existe en esta obra"}

    mov = models.MovimientoObra(
        obra_id=obra.id,
        etapa_id=etapa_id,
        fecha=fecha,
        tipo=tipo,
        origen_ingreso=origen_ingreso,
        categoria_egreso=categoria_egreso,
        concepto=concepto,
        monto=monto,
        medio_pago=medio_pago,
        nro_cheque=nro_cheque,
        banco=banco,
        fecha_vto_cheque=fecha_vto_cheque,
        comprobante_id=comprobante_id,
        canal=models.CanalCarga.agente_ia,
        cargado_por=user.id,
    )
    db.add(mov); db.commit(); db.refresh(mov)

    saldo = _saldo_obra(db, obra.id)
    return {
        "ok": True,
        "movimiento_id": mov.id,
        "obra": obra.nombre,
        "tipo": tipo.value,
        "monto": float(mov.monto),
        "fecha": mov.fecha.isoformat(),
        "concepto": mov.concepto,
        "saldo_obra_actualizado": saldo["saldo"],
    }


def t_registrar_aporte_socio(input: dict, user: models.User, db: Session) -> dict:
    """Registra un aporte de socio en una obra. R2: dispara INGRESO espejo automático.

    Espejo de POST /api/aportes — crea AporteSocio y MovimientoObra en la misma transacción.
    """
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    socio_id = input.get("socio_id")
    if not socio_id:
        return {"error": "Falta 'socio_id' (id del usuario que actúa como socio)"}
    socio = db.query(models.User).filter(models.User.id == socio_id).first()
    if not socio:
        return {"error": f"Socio (user id {socio_id}) no encontrado"}

    try:
        monto = float(input.get("monto", 0))
    except (TypeError, ValueError):
        return {"error": "monto inválido"}
    if monto <= 0:
        return {"error": "monto debe ser > 0"}

    motivo = (input.get("motivo") or "").strip()
    if not motivo:
        return {"error": "Falta 'motivo' (texto explicativo del aporte)"}

    fecha_str = input.get("fecha_aporte")
    if fecha_str:
        try:
            fecha_aporte = date.fromisoformat(fecha_str)
        except ValueError:
            return {"error": "fecha_aporte debe estar en formato YYYY-MM-DD"}
    else:
        fecha_aporte = date.today()

    medio_str = input.get("medio_pago")
    try:
        medio_pago = models.MedioPago(medio_str)
    except (ValueError, TypeError):
        return {"error": f"medio_pago inválido: {medio_str}"}

    etapa_reintegro_id = input.get("etapa_reintegro_id")
    if etapa_reintegro_id:
        e = db.query(models.EtapaObra).filter(
            models.EtapaObra.id == etapa_reintegro_id,
            models.EtapaObra.obra_id == obra.id,
        ).first()
        if not e:
            return {"error": f"Etapa {etapa_reintegro_id} no existe en esta obra"}

    aporte = models.AporteSocio(
        obra_id=obra.id,
        socio_id=socio.id,
        etapa_reintegro_id=etapa_reintegro_id,
        fecha_aporte=fecha_aporte,
        monto=monto,
        motivo=motivo,
        medio_pago=medio_pago,
        estado_devolucion=models.EstadoDevolucion.PENDIENTE,
        monto_devuelto=0,
    )
    db.add(aporte); db.flush()

    # R2: movimiento espejo INGRESO
    mov = models.MovimientoObra(
        obra_id=obra.id,
        etapa_id=etapa_reintegro_id,
        fecha=fecha_aporte,
        tipo=models.TipoMovimiento.INGRESO,
        origen_ingreso=models.OrigenIngreso.APORTE_SOCIO_RCA,
        concepto=f"Aporte de socio: {motivo}",
        monto=monto,
        medio_pago=medio_pago,
        aporte_socio_id=aporte.id,
        estado=models.EstadoMovimiento.CONFIRMADO,
        canal=models.CanalCarga.agente_ia,
        cargado_por=user.id,
    )
    db.add(mov)
    db.commit(); db.refresh(aporte)

    saldo = _saldo_obra(db, obra.id)
    return {
        "ok": True,
        "aporte_id": aporte.id,
        "movimiento_espejo_id": mov.id,
        "obra": obra.nombre,
        "socio": f"{socio.name} {socio.last_name or ''}".strip(),
        "monto": monto,
        "saldo_obra_actualizado": saldo["saldo"],
    }


def t_enviar_whatsapp(input: dict, user: models.User, db: Session) -> dict:
    """Envía un mensaje de WhatsApp al destinatario indicado.

    Usa el adapter `whatsapp_sender` que respeta `WHATSAPP_PROVIDER`:
        - log_only (default): registra en outbound_messages con status=log_only.
        - twilio / cloud_api: envía de verdad si las credenciales están en .env.
    """
    from app.whatsapp_sender import send_whatsapp
    telefono = (input.get("telefono") or "").strip()
    if not telefono:
        return {"error": "Falta 'telefono' (formato +5491100000000)"}
    mensaje = (input.get("mensaje") or "").strip()
    if not mensaje:
        return {"error": "Falta 'mensaje'"}

    obra_ref = input.get("obra_ref")
    obra_id = None
    if obra_ref:
        obra = _obra_by_ref(obra_ref, db)
        if obra:
            obra_id = obra.id

    msg = send_whatsapp(
        db, telefono, mensaje,
        notification_type="agente_ia",
        obra_id=obra_id,
        user_id=user.id,
    )
    return {
        "ok": msg.status != models.OutboundMessageStatus.failed,
        "outbound_id": msg.id,
        "destinatario": msg.destinatario,
        "provider": msg.provider,
        "status": msg.status.value,
        "error": msg.error,
    }


def t_cargar_comprobante(input: dict, user: models.User, db: Session) -> dict:
    """Crea un comprobante AFIP (FC_A/B/C, NC, ND, Recibo, Remito) ligado a una obra.
    Validación: neto_gravado + neto_no_gravado + iva_21 + iva_105 = total (±0.05).
    """
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    tipo_str = input.get("tipo_comprobante")
    try:
        tipo = models.TipoComprobante(tipo_str)
    except (ValueError, TypeError):
        return {"error": f"tipo_comprobante inválido: {tipo_str}. Valores: FC_A, FC_B, FC_C, NC_A, NC_B, ND_A, ND_B, RECIBO_X, REMITO"}

    nro = (input.get("nro_comprobante") or "").strip()
    if not nro:
        return {"error": "Falta 'nro_comprobante' (formato 00001-00000001)"}

    fecha_str = input.get("fecha_emision")
    if not fecha_str:
        return {"error": "Falta 'fecha_emision' (YYYY-MM-DD)"}
    try:
        fecha_emision = date.fromisoformat(fecha_str)
    except ValueError:
        return {"error": "fecha_emision debe estar en formato YYYY-MM-DD"}

    cuit_emisor = input.get("cuit_emisor")
    cuit_receptor = input.get("cuit_receptor")
    if not cuit_emisor or not cuit_receptor:
        return {"error": "Faltan 'cuit_emisor' y/o 'cuit_receptor'"}

    try:
        neto_gravado = float(input.get("neto_gravado", 0))
        neto_no_gravado = float(input.get("neto_no_gravado", 0))
        iva_21 = float(input.get("iva_21", 0))
        iva_105 = float(input.get("iva_105", 0))
        total = float(input.get("total", 0))
    except (TypeError, ValueError):
        return {"error": "Montos deben ser números"}

    suma = neto_gravado + neto_no_gravado + iva_21 + iva_105
    if abs(suma - total) > 0.05:
        return {"error": f"Total ({total:.2f}) no coincide con neto+IVA ({suma:.2f})"}

    if "es_venta" not in input:
        return {"error": "Falta 'es_venta' (true=emitido, false=recibido)"}

    cae = input.get("cae")
    cae_vto_str = input.get("cae_vencimiento")
    cae_vto = None
    if cae_vto_str:
        try:
            cae_vto = date.fromisoformat(cae_vto_str)
        except ValueError:
            return {"error": "cae_vencimiento debe estar en formato YYYY-MM-DD"}

    estado_fiscal_str = input.get("estado_fiscal", "VALIDO")
    try:
        estado_fiscal = models.EstadoFiscal(estado_fiscal_str)
    except (ValueError, TypeError):
        return {"error": f"estado_fiscal inválido: {estado_fiscal_str}"}

    c = models.Comprobante(
        obra_id=obra.id,
        tipo_comprobante=tipo,
        punto_venta=input.get("punto_venta"),
        nro_comprobante=nro,
        fecha_emision=fecha_emision,
        cuit_emisor=cuit_emisor,
        cuit_receptor=cuit_receptor,
        neto_gravado=neto_gravado,
        neto_no_gravado=neto_no_gravado,
        iva_21=iva_21,
        iva_105=iva_105,
        total=total,
        cae=cae,
        cae_vencimiento=cae_vto,
        es_venta=bool(input.get("es_venta")),
        estado_fiscal=estado_fiscal,
        archivo_url=input.get("archivo_url"),
        notas=input.get("notas"),
    )
    db.add(c); db.commit(); db.refresh(c)
    return {
        "ok": True,
        "comprobante_id": c.id,
        "obra": obra.nombre,
        "tipo": c.tipo_comprobante.value,
        "nro": c.nro_comprobante,
        "total": float(c.total),
        "es_venta": c.es_venta,
    }


def t_crear_cliente(input: dict, user: models.User, db: Session) -> dict:
    """Crea un cliente nuevo."""
    nombre = (input.get("nombre") or "").strip()
    if not nombre:
        return {"error": "Falta 'nombre'"}

    cuit = input.get("cuit")
    if cuit:
        existente = db.query(models.Cliente).filter(models.Cliente.cuit == cuit).first()
        if existente:
            return {"error": f"Ya existe un cliente con CUIT {cuit}: {existente.nombre}"}

    regimen_id = input.get("regimen_fiscal_id")
    if regimen_id:
        rf = db.query(models.RegimenFiscal).filter(models.RegimenFiscal.id == regimen_id).first()
        if not rf:
            return {"error": f"Régimen fiscal {regimen_id} no encontrado"}

    c = models.Cliente(
        nombre=nombre,
        cuit=cuit,
        razon_social=input.get("razon_social"),
        direccion=input.get("direccion"),
        email=input.get("email"),
        telefono=input.get("telefono"),
        tipo=input.get("tipo"),  # publico, privado_ri, privado_mt, particular
        regimen_fiscal_id=regimen_id,
        notas=input.get("notas"),
        activo=True,
    )
    db.add(c); db.commit(); db.refresh(c)
    return {
        "ok": True,
        "cliente_id": c.id,
        "nombre": c.nombre,
        "cuit": c.cuit,
        "tipo": c.tipo,
    }


def t_crear_obra(input: dict, user: models.User, db: Session) -> dict:
    """Crea una obra ligada a un cliente con su régimen fiscal."""
    nombre = (input.get("nombre") or "").strip()
    if not nombre:
        return {"error": "Falta 'nombre'"}

    codigo = (input.get("codigo") or "").strip().upper()
    if not codigo:
        return {"error": "Falta 'codigo' (ej: IDS, SP)"}

    cliente_id = input.get("cliente_id")
    if not cliente_id:
        return {"error": "Falta 'cliente_id' (creá primero el cliente con crear_cliente)"}
    cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not cliente:
        return {"error": f"Cliente {cliente_id} no encontrado"}

    if db.query(models.Obra).filter(models.Obra.codigo == codigo).first():
        return {"error": f"Ya existe una obra con código '{codigo}'"}

    tipo_fact_str = input.get("tipo_facturacion", "SIN_DEFINIR")
    try:
        tipo_facturacion = models.TipoFacturacion(tipo_fact_str)
    except (ValueError, TypeError):
        return {"error": f"tipo_facturacion inválido: {tipo_fact_str}"}

    regimen_id = input.get("regimen_fiscal_id") or cliente.regimen_fiscal_id

    monto_contrato = input.get("monto_contrato")
    if monto_contrato is not None:
        try:
            monto_contrato = float(monto_contrato)
        except (TypeError, ValueError):
            return {"error": "monto_contrato inválido"}

    fecha_inicio = None
    if (fi := input.get("fecha_inicio")):
        try:
            fecha_inicio = date.fromisoformat(fi)
        except ValueError:
            return {"error": "fecha_inicio debe estar en formato YYYY-MM-DD"}

    fecha_fin = None
    if (ff := input.get("fecha_fin_estimada")):
        try:
            fecha_fin = date.fromisoformat(ff)
        except ValueError:
            return {"error": "fecha_fin_estimada debe estar en formato YYYY-MM-DD"}

    o = models.Obra(
        codigo=codigo,
        nombre=nombre,
        cliente_id=cliente.id,
        regimen_fiscal_id=regimen_id,
        tipo_facturacion=tipo_facturacion,
        direccion=input.get("direccion"),
        ciudad=input.get("ciudad"),
        descripcion=input.get("descripcion"),
        monto_contrato=monto_contrato,
        fecha_inicio=fecha_inicio,
        fecha_fin_estimada=fecha_fin,
        estado=models.ObraStatus.EN_CURSO,
        icono=input.get("icono", "🏗️"),
        color=input.get("color", "#1E2B5E"),
        superficie_m2=input.get("superficie_m2", 0),
        pisos=input.get("pisos", 1),
    )
    db.add(o); db.commit(); db.refresh(o)
    return {
        "ok": True,
        "obra_id": o.id,
        "codigo": o.codigo,
        "nombre": o.nombre,
        "cliente": cliente.nombre,
        "tipo_facturacion": o.tipo_facturacion.value,
        "monto_contrato": float(o.monto_contrato) if o.monto_contrato else None,
    }


def t_crear_orden(input: dict, user: models.User, db: Session) -> dict:
    """Crea una orden de trabajo (quest operativa) en una obra."""
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    titulo = (input.get("titulo") or "").strip()
    if not titulo:
        return {"error": "Falta 'titulo'"}

    frente_id = input.get("frente_id")
    if frente_id:
        f = db.query(models.Frente).filter(
            models.Frente.id == frente_id, models.Frente.obra_id == obra.id,
        ).first()
        if not f:
            return {"error": f"Frente {frente_id} no existe en esta obra"}

    cuadrilla_id = input.get("cuadrilla_id")
    if cuadrilla_id:
        c = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == cuadrilla_id).first()
        if not c:
            return {"error": f"Cuadrilla {cuadrilla_id} no encontrada"}

    fecha_limite = None
    if (fl := input.get("fecha_limite")):
        try:
            fecha_limite = date.fromisoformat(fl)
        except ValueError:
            return {"error": "fecha_limite debe estar en formato YYYY-MM-DD"}

    try:
        xp_reward = int(input.get("xp_reward", 10))
    except (TypeError, ValueError):
        return {"error": "xp_reward debe ser entero"}
    if xp_reward < 0:
        return {"error": "xp_reward no puede ser negativo"}

    o = models.OrdenTrabajo(
        obra_id=obra.id,
        frente_id=frente_id,
        cuadrilla_id=cuadrilla_id,
        titulo=titulo,
        descripcion=input.get("descripcion"),
        prioridad=input.get("prioridad", "normal"),
        status=models.TaskStatus.pendiente,
        xp_reward=xp_reward,
        fecha_limite=fecha_limite,
        creada_por_id=user.id,
        canal_creacion=models.CanalCarga.agente_ia,
    )
    db.add(o); db.commit(); db.refresh(o)
    return {
        "ok": True,
        "orden_id": o.id,
        "obra": obra.nombre,
        "titulo": o.titulo,
        "xp_reward": o.xp_reward,
        "status": o.status.value,
    }


def t_cerrar_orden(input: dict, user: models.User, db: Session) -> dict:
    """Cierra una orden de trabajo. Suma XP al usuario y a la cuadrilla asignada,
    sube nivel de la cuadrilla si corresponde. Crea evento 'avance' en el feed.
    """
    orden_id = input.get("orden_id")
    if not orden_id:
        return {"error": "Falta 'orden_id'"}
    o = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not o:
        return {"error": f"Orden {orden_id} no encontrada"}
    if o.status == models.TaskStatus.completada:
        return {"error": "La orden ya está completada"}

    o.status = models.TaskStatus.completada
    o.completada_at = datetime.utcnow()

    # XP al usuario
    user.xp = (user.xp or 0) + o.xp_reward
    cuad_info = None
    if o.cuadrilla_id:
        cuad = db.query(models.Cuadrilla).filter(models.Cuadrilla.id == o.cuadrilla_id).first()
        if cuad:
            cuad.experiencia = (cuad.experiencia or 0) + o.xp_reward
            cuad.nivel = max(1, 1 + cuad.experiencia // 100)
            cuad_info = {"id": cuad.id, "xp_total": cuad.experiencia, "nivel": cuad.nivel}

    # Evento de avance
    ev = models.Evento(
        obra_id=o.obra_id,
        frente_id=o.frente_id,
        tipo=models.EventoTipo.avance,
        titulo=f"Orden completada: {o.titulo}",
        descripcion=input.get("nota_cierre"),
        canal=models.CanalCarga.agente_ia,
        usuario_id=user.id,
    )
    db.add(ev); db.commit(); db.refresh(o)

    return {
        "ok": True,
        "orden_id": o.id,
        "status": o.status.value,
        "xp_otorgado_user": o.xp_reward,
        "user_xp_total": user.xp,
        "cuadrilla": cuad_info,
        "evento_id": ev.id,
    }


def t_reportar_evento(input: dict, user: models.User, db: Session) -> dict:
    """Crea un evento en el feed de actividad de una obra (avance, incidente, foto, etc.)."""
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    titulo = (input.get("titulo") or "").strip()
    if not titulo:
        return {"error": "Falta 'titulo'"}

    tipo_str = input.get("tipo", "otro")
    try:
        tipo = models.EventoTipo(tipo_str)
    except (ValueError, TypeError):
        return {"error": f"tipo de evento inválido: {tipo_str}"}

    frente_id = input.get("frente_id")
    if frente_id:
        f = db.query(models.Frente).filter(
            models.Frente.id == frente_id, models.Frente.obra_id == obra.id,
        ).first()
        if not f:
            return {"error": f"Frente {frente_id} no existe en esta obra"}

    es_critico = bool(input.get("es_critico", tipo == models.EventoTipo.incidente))

    ev = models.Evento(
        obra_id=obra.id,
        frente_id=frente_id,
        tipo=tipo,
        titulo=titulo,
        descripcion=input.get("descripcion"),
        foto_url=input.get("foto_url"),
        canal=models.CanalCarga.agente_ia,
        usuario_id=user.id,
        es_critico=es_critico,
    )
    db.add(ev); db.commit(); db.refresh(ev)
    return {
        "ok": True,
        "evento_id": ev.id,
        "obra": obra.nombre,
        "tipo": ev.tipo.value,
        "titulo": ev.titulo,
        "es_critico": ev.es_critico,
    }


def t_crear_etapa(input: dict, user: models.User, db: Session) -> dict:
    """Crea una etapa nueva en una obra (anticipo, etapa N, final)."""
    obra_ref = input.get("obra")
    if not obra_ref:
        return {"error": "Falta 'obra'"}
    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"error": f"Obra '{obra_ref}' no encontrada"}

    nombre = (input.get("nombre") or "").strip()
    if not nombre:
        return {"error": "Falta 'nombre' (ej: 'Etapa 2 - Terminaciones')"}

    nro_etapa = input.get("nro_etapa")
    if nro_etapa is None:
        return {"error": "Falta 'nro_etapa' (0=anticipo, 1=etapa1, 2=etapa2, ...)"}
    try:
        nro_etapa = int(nro_etapa)
    except (TypeError, ValueError):
        return {"error": "nro_etapa debe ser entero"}

    # Verificar duplicado
    existente = db.query(models.EtapaObra).filter(
        models.EtapaObra.obra_id == obra.id,
        models.EtapaObra.nro_etapa == nro_etapa,
    ).first()
    if existente:
        return {"error": f"La obra ya tiene una etapa con nro_etapa={nro_etapa}: '{existente.nombre}'"}

    monto_contractual = input.get("monto_contractual")
    if monto_contractual is not None:
        try:
            monto_contractual = float(monto_contractual)
        except (TypeError, ValueError):
            return {"error": "monto_contractual inválido"}
        if monto_contractual < 0:
            return {"error": "monto_contractual no puede ser negativo"}

    porcentaje = input.get("porcentaje_avance")
    if porcentaje is not None:
        try:
            porcentaje = float(porcentaje)
        except (TypeError, ValueError):
            return {"error": "porcentaje_avance inválido"}

    fecha_str = input.get("fecha_estimada")
    fecha_estimada = None
    if fecha_str:
        try:
            fecha_estimada = date.fromisoformat(fecha_str)
        except ValueError:
            return {"error": "fecha_estimada debe estar en formato YYYY-MM-DD"}

    estado_str = input.get("estado", "PENDIENTE")
    try:
        estado = models.EtapaEstado(estado_str)
    except (ValueError, TypeError):
        return {"error": f"estado inválido: {estado_str}"}

    e = models.EtapaObra(
        obra_id=obra.id,
        nombre=nombre,
        nro_etapa=nro_etapa,
        monto_contractual=monto_contractual,
        porcentaje_avance=porcentaje,
        estado=estado,
        fecha_estimada=fecha_estimada,
        notas=input.get("notas"),
    )
    db.add(e); db.commit(); db.refresh(e)
    return {
        "ok": True,
        "etapa_id": e.id,
        "obra": obra.nombre,
        "nombre": e.nombre,
        "nro_etapa": e.nro_etapa,
        "estado": e.estado.value,
        "monto_contractual": float(e.monto_contractual) if e.monto_contractual else None,
    }


def t_cambiar_estado_etapa(input: dict, user: models.User, db: Session) -> dict:
    """Cambia el estado de una etapa. R5: si pasa a COBRADA con aportes pendientes,
    crea automáticamente una nota importante para alertar al admin.
    """
    etapa_id = input.get("etapa_id")
    if not etapa_id:
        return {"error": "Falta 'etapa_id'"}
    e = db.query(models.EtapaObra).filter(models.EtapaObra.id == etapa_id).first()
    if not e:
        return {"error": f"Etapa {etapa_id} no encontrada"}

    estado_str = input.get("nuevo_estado")
    if not estado_str:
        return {"error": "Falta 'nuevo_estado' (PENDIENTE, EN_EJECUCION, EJECUTADA, FACTURADA, COBRADA)"}
    try:
        nuevo = models.EtapaEstado(estado_str)
    except (ValueError, TypeError):
        return {"error": f"estado inválido: {estado_str}"}

    estado_anterior = e.estado
    e.estado = nuevo

    # Fecha de cobro real si pasa a COBRADA
    if nuevo == models.EtapaEstado.COBRADA and not e.fecha_cobro_real:
        fecha_str = input.get("fecha_cobro_real")
        if fecha_str:
            try:
                e.fecha_cobro_real = date.fromisoformat(fecha_str)
            except ValueError:
                return {"error": "fecha_cobro_real debe estar en formato YYYY-MM-DD"}
        else:
            e.fecha_cobro_real = date.today()

    nota_creada = None
    if nuevo == models.EtapaEstado.COBRADA:
        pendientes = db.query(models.AporteSocio).filter(
            models.AporteSocio.etapa_reintegro_id == etapa_id,
            models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL,
        ).count()
        if pendientes > 0:
            n = models.NotaObra(
                obra_id=e.obra_id,
                texto=f"⚠️ Etapa '{e.nombre}' marcada COBRADA con {pendientes} aporte(s) de socio pendiente(s) de devolución. (R5 cascada — registrado por agente IA)",
                importante=True,
                autor_id=user.id,
            )
            db.add(n); db.flush()
            nota_creada = n.id

    db.commit(); db.refresh(e)
    return {
        "ok": True,
        "etapa_id": e.id,
        "estado_anterior": estado_anterior.value,
        "estado_nuevo": e.estado.value,
        "fecha_cobro_real": e.fecha_cobro_real.isoformat() if e.fecha_cobro_real else None,
        "nota_r5_creada": nota_creada,
    }


def t_registrar_devolucion_aporte(input: dict, user: models.User, db: Session) -> dict:
    """Registra una devolución (parcial o total) de un aporte de socio. Crea EGRESO espejo."""
    aporte_id = input.get("aporte_id")
    if not aporte_id:
        return {"error": "Falta 'aporte_id'"}
    aporte = db.query(models.AporteSocio).filter(models.AporteSocio.id == aporte_id).first()
    if not aporte:
        return {"error": f"Aporte {aporte_id} no encontrado"}
    if aporte.estado_devolucion == models.EstadoDevolucion.DEVUELTO_TOTAL:
        return {"error": "El aporte ya está totalmente devuelto"}

    try:
        monto = float(input.get("monto", 0))
    except (TypeError, ValueError):
        return {"error": "monto inválido"}
    if monto <= 0:
        return {"error": "monto debe ser > 0"}

    pendiente = float(aporte.monto) - float(aporte.monto_devuelto)
    if monto > pendiente + 0.01:
        return {"error": f"Monto excede el pendiente ({pendiente:.2f})"}

    fecha_str = input.get("fecha")
    if fecha_str:
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            return {"error": "fecha debe estar en formato YYYY-MM-DD"}
    else:
        fecha = date.today()

    medio_str = input.get("medio_pago")
    try:
        medio_pago = models.MedioPago(medio_str)
    except (ValueError, TypeError):
        return {"error": f"medio_pago inválido: {medio_str}"}

    notas = input.get("notas") or aporte.motivo

    aporte.monto_devuelto = float(aporte.monto_devuelto) + monto
    aporte.fecha_devolucion = fecha
    if abs(float(aporte.monto_devuelto) - float(aporte.monto)) < 0.01:
        aporte.estado_devolucion = models.EstadoDevolucion.DEVUELTO_TOTAL
    else:
        aporte.estado_devolucion = models.EstadoDevolucion.DEVUELTO_PARCIAL

    mov = models.MovimientoObra(
        obra_id=aporte.obra_id,
        fecha=fecha,
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.APORTE_PRESTAMO,
        concepto=f"Devolución aporte socio (id {aporte.id}): {notas}",
        monto=monto,
        medio_pago=medio_pago,
        aporte_socio_id=aporte.id,
        estado=models.EstadoMovimiento.CONFIRMADO,
        canal=models.CanalCarga.agente_ia,
        cargado_por=user.id,
    )
    db.add(mov)
    db.commit(); db.refresh(aporte)

    return {
        "ok": True,
        "aporte_id": aporte.id,
        "estado_devolucion": aporte.estado_devolucion.value,
        "monto_devuelto_total": float(aporte.monto_devuelto),
        "pendiente_restante": float(aporte.monto) - float(aporte.monto_devuelto),
        "movimiento_egreso_id": mov.id,
    }


# ════════════════════════════════════════════════════════════════════
# SPRINT 9 — STOCK MULTI-UBICACIÓN
# ════════════════════════════════════════════════════════════════════

def _material_by_ref(ref, db: Session) -> models.Material | None:
    if ref is None:
        return None
    if isinstance(ref, int) or (isinstance(ref, str) and str(ref).isdigit()):
        m = db.query(models.Material).filter(models.Material.id == int(ref)).first()
        if m:
            return m
    if isinstance(ref, str):
        return db.query(models.Material).filter(models.Material.nombre.ilike(f"%{ref.strip()}%")).first()
    return None


def _proveedor_by_ref(ref, db: Session) -> models.Proveedor | None:
    if ref is None:
        return None
    if isinstance(ref, int) or (isinstance(ref, str) and str(ref).isdigit()):
        p = db.query(models.Proveedor).filter(models.Proveedor.id == int(ref)).first()
        if p:
            return p
    if isinstance(ref, str):
        return db.query(models.Proveedor).filter(models.Proveedor.nombre.ilike(f"%{ref.strip()}%")).first()
    return None


def t_consultar_stock(input: dict, user: models.User, db: Session) -> dict:
    """LECTURA — devuelve el desglose de stock por ubicación de uno o todos los materiales."""
    from app.stock import breakdown_por_material
    ref = input.get("material")
    material_id = None
    if ref is not None:
        m = _material_by_ref(ref, db)
        if not m:
            return {"error": f"No encontré el material '{ref}'"}
        material_id = m.id
    items = breakdown_por_material(db, material_id=material_id)
    # achatar para devolver al agente
    return {
        "total_materiales": len(items),
        "materiales": [
            {
                "id": it["id"], "nombre": it["nombre"], "unidad": it["unidad"],
                "stock_minimo": it["stock_minimo"],
                "stock_total_disponible": it["stock_total_disponible"],
                "stock_pendiente_retiro": it["stock_pendiente_retiro"],
                "ubicaciones": it["ubicaciones"],
            }
            for it in items
        ],
    }


def t_cargar_compra_pendiente_retiro(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — registra una compra cuya mercadería sigue en el proveedor."""
    from app.stock import cargar_compra_pendiente, breakdown_por_material
    mat = _material_by_ref(input.get("material"), db)
    if not mat:
        return {"error": f"No encontré el material '{input.get('material')}'"}
    prov = _proveedor_by_ref(input.get("proveedor"), db)
    if not prov:
        return {"error": f"No encontré el proveedor '{input.get('proveedor')}'"}
    try:
        cant = float(input.get("cantidad", 0))
    except (TypeError, ValueError):
        return {"error": "cantidad inválida"}
    try:
        cargar_compra_pendiente(db, material_id=mat.id, proveedor_id=prov.id,
                                cantidad=cant, nota=input.get("nota"), usuario_id=user.id)
    except ValueError as e:
        return {"error": str(e)}
    detalle = breakdown_por_material(db, material_id=mat.id)[0]
    return {
        "ok": True, "material": mat.nombre, "proveedor": prov.nombre,
        "cantidad_agregada": cant,
        "pendiente_total_ahora": detalle["stock_pendiente_retiro"],
    }


def t_retirar_de_proveedor(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — marca materiales como retirados del proveedor → depósito propio o directo a obra."""
    from app.stock import retirar_de_proveedor, breakdown_por_material
    mat = _material_by_ref(input.get("material"), db)
    if not mat:
        return {"error": f"No encontré el material '{input.get('material')}'"}
    prov = _proveedor_by_ref(input.get("proveedor"), db)
    if not prov:
        return {"error": f"No encontré el proveedor '{input.get('proveedor')}'"}
    try:
        cant = float(input.get("cantidad", 0))
    except (TypeError, ValueError):
        return {"error": "cantidad inválida"}

    destino_tipo = input.get("destino_tipo")
    destino_obra_id = None
    if destino_tipo == "en_obra":
        obra_ref = input.get("obra")
        obra = _obra_by_ref(obra_ref, db) if obra_ref else None
        if not obra:
            return {"error": f"Necesito una obra de destino (no encontré '{obra_ref}')"}
        destino_obra_id = obra.id
    elif destino_tipo != "deposito_propio":
        return {"error": "destino_tipo debe ser 'deposito_propio' o 'en_obra'"}

    try:
        retirar_de_proveedor(
            db, material_id=mat.id, proveedor_id=prov.id, cantidad=cant,
            destino_tipo=destino_tipo, destino_obra_id=destino_obra_id,
            nota=input.get("nota"), usuario_id=user.id,
        )
    except ValueError as e:
        return {"error": str(e)}
    detalle = breakdown_por_material(db, material_id=mat.id)[0]
    return {
        "ok": True, "material": mat.nombre, "proveedor": prov.nombre,
        "cantidad_retirada": cant,
        "destino": destino_tipo + (f" (obra id={destino_obra_id})" if destino_obra_id else ""),
        "pendiente_restante": detalle["stock_pendiente_retiro"],
        "stock_disponible_total": detalle["stock_total_disponible"],
    }


def t_consumir_en_obra(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — registra consumo de material en una obra (cuadrilla usó X cantidad)."""
    from app.stock import consumir_en_obra, breakdown_por_material
    mat = _material_by_ref(input.get("material"), db)
    if not mat:
        return {"error": f"No encontré el material '{input.get('material')}'"}
    obra = _obra_by_ref(input.get("obra"), db)
    if not obra:
        return {"error": f"No encontré la obra '{input.get('obra')}'"}
    try:
        cant = float(input.get("cantidad", 0))
    except (TypeError, ValueError):
        return {"error": "cantidad inválida"}
    try:
        consumir_en_obra(db, material_id=mat.id, obra_id=obra.id, cantidad=cant,
                         nota=input.get("nota"), usuario_id=user.id)
    except ValueError as e:
        return {"error": str(e)}
    detalle = breakdown_por_material(db, material_id=mat.id)[0]
    return {
        "ok": True, "material": mat.nombre, "obra": obra.nombre,
        "cantidad_consumida": cant,
        "stock_total_disponible": detalle["stock_total_disponible"],
    }


def t_transferir_stock(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — mueve stock entre depósito propio y obras (o entre obras)."""
    from app.stock import transferir_stock, breakdown_por_material
    mat = _material_by_ref(input.get("material"), db)
    if not mat:
        return {"error": f"No encontré el material '{input.get('material')}'"}
    try:
        cant = float(input.get("cantidad", 0))
    except (TypeError, ValueError):
        return {"error": "cantidad inválida"}

    origen_tipo = input.get("origen_tipo")
    destino_tipo = input.get("destino_tipo")
    if origen_tipo not in ("deposito_propio", "en_obra") or destino_tipo not in ("deposito_propio", "en_obra"):
        return {"error": "origen_tipo y destino_tipo deben ser 'deposito_propio' o 'en_obra'"}

    origen_obra_id = None
    destino_obra_id = None
    if origen_tipo == "en_obra":
        o = _obra_by_ref(input.get("obra_origen"), db)
        if not o:
            return {"error": f"No encontré obra origen '{input.get('obra_origen')}'"}
        origen_obra_id = o.id
    if destino_tipo == "en_obra":
        o = _obra_by_ref(input.get("obra_destino"), db)
        if not o:
            return {"error": f"No encontré obra destino '{input.get('obra_destino')}'"}
        destino_obra_id = o.id

    try:
        transferir_stock(
            db, material_id=mat.id, cantidad=cant,
            origen_tipo=origen_tipo, origen_obra_id=origen_obra_id,
            destino_tipo=destino_tipo, destino_obra_id=destino_obra_id,
            nota=input.get("nota"), usuario_id=user.id,
        )
    except ValueError as e:
        return {"error": str(e)}
    detalle = breakdown_por_material(db, material_id=mat.id)[0]
    return {
        "ok": True, "material": mat.nombre, "cantidad_movida": cant,
        "origen": origen_tipo + (f" (obra {origen_obra_id})" if origen_obra_id else ""),
        "destino": destino_tipo + (f" (obra {destino_obra_id})" if destino_obra_id else ""),
        "ubicaciones_actuales": detalle["ubicaciones"],
    }


# ════════════════════════════════════════════════════════════════════
# SPRINT 10 — PRESUPUESTOS DE MATERIALES POR OBRA
# ════════════════════════════════════════════════════════════════════

def t_consultar_presupuestos(input: dict, user: models.User, db: Session) -> dict:
    """LECTURA — lista presupuestos, filtrable por obra y/o estado."""
    from app.presupuestos_svc import serialize
    q = db.query(models.Presupuesto)
    if (ref := input.get("obra")) is not None:
        o = _obra_by_ref(ref, db)
        if not o:
            return {"error": f"No encontré la obra '{ref}'"}
        q = q.filter(models.Presupuesto.obra_id == o.id)
    if (estado := input.get("estado")) is not None:
        q = q.filter(models.Presupuesto.estado == estado)
    presupuestos = q.order_by(models.Presupuesto.created_at.desc()).all()
    return {
        "total": len(presupuestos),
        "presupuestos": [serialize(p, db) for p in presupuestos],
    }


def t_crear_presupuesto(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — crea un presupuesto en estado borrador con sus items.

    Acepta items como lista de objetos {material, cantidad, precio?}.
    'material' puede ser id o nombre. Si no se pasa precio, usa el del Material.
    """
    from app.presupuestos_svc import crear_presupuesto, serialize
    obra = _obra_by_ref(input.get("obra"), db)
    if not obra:
        return {"error": f"No encontré la obra '{input.get('obra')}'"}
    nombre = (input.get("nombre") or "").strip()
    if not nombre:
        return {"error": "Falta 'nombre' del presupuesto"}

    items_in = input.get("items") or []
    items_normalizados: list[dict] = []
    for it in items_in:
        mat_ref = it.get("material") if isinstance(it, dict) else None
        mat = _material_by_ref(mat_ref, db) if mat_ref is not None else None
        if not mat:
            return {"error": f"No encontré el material '{mat_ref}' en un item"}
        try:
            cant = float(it.get("cantidad", 0))
        except (TypeError, ValueError):
            return {"error": f"cantidad inválida para material '{mat.nombre}'"}
        if cant <= 0:
            return {"error": f"cantidad debe ser > 0 para '{mat.nombre}'"}
        items_normalizados.append({
            "material_id": mat.id, "cantidad": cant,
            "precio_unitario_estimado": it.get("precio"),
        })

    try:
        p = crear_presupuesto(
            db, obra_id=obra.id, nombre=nombre,
            items=items_normalizados,
            notas=input.get("notas"), created_by_id=user.id,
        )
    except ValueError as e:
        return {"error": str(e)}
    return {"ok": True, "presupuesto": serialize(p, db)}


def t_aprobar_presupuesto(input: dict, user: models.User, db: Session) -> dict:
    """ESCRITURA — marca un presupuesto como aprobado. Solo desde borrador."""
    from app.presupuestos_svc import aprobar_presupuesto, serialize
    pid = input.get("presupuesto_id")
    if pid is None:
        return {"error": "Falta 'presupuesto_id'"}
    try:
        p = aprobar_presupuesto(db, presupuesto_id=int(pid))
    except (ValueError, TypeError) as e:
        return {"error": str(e)}
    return {"ok": True, "presupuesto": serialize(p, db)}


# ════════════════════════════════════════════════════════════════════
# SCHEMA PARA ANTHROPIC
# ════════════════════════════════════════════════════════════════════

TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "dashboard_hud",
        "description": "Resumen ejecutivo global: monto total de contratos, ingresos/egresos/saldo global, aportes de socios pendientes, cheques a vencer, obras activas, alertas. Para preguntas tipo 'cómo va todo'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_obras",
        "description": "Lista todas las obras con su cliente, régimen fiscal, estado, monto de contrato y saldo (ingresos - egresos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "estado": {"type": "string", "enum": ["EN_CURSO", "PAUSADA", "FINALIZADA", "CANCELADA"]},
            },
        },
    },
    {
        "name": "obtener_obra",
        "description": "Detalle completo de una obra: etapas, saldo, aportes pendientes, cheques a vencer, eventos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "referencia": {"type": "string", "description": "id, código (IDS, SP) o parte del nombre"},
            },
            "required": ["referencia"],
        },
    },
    {
        "name": "listar_clientes",
        "description": "Lista clientes con CUIT, tipo, régimen fiscal y cuántas obras tienen.",
        "input_schema": {
            "type": "object",
            "properties": {"tipo": {"type": "string", "description": "publico, privado_ri, privado_mt, particular"}},
        },
    },
    {
        "name": "listar_etapas",
        "description": "Etapas de una obra (anticipo, etapa 1, etc.) con monto contractual y estado de cobro.",
        "input_schema": {
            "type": "object",
            "properties": {"obra": {"type": "string"}},
            "required": ["obra"],
        },
    },
    {
        "name": "listar_movimientos",
        "description": "Lista movimientos financieros (ingresos/egresos) de una obra. Filtros por tipo, categoría, estado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"]},
                "categoria": {"type": "string", "description": "MANO_DE_OBRA / MATERIALES / SUBCONTRATO / SERVICIO_EXTERNO / GASTO_DIRECTO_OBRA / HERRAMIENTA_EQUIPO / APORTE_PRESTAMO"},
                "solo_a_revisar": {"type": "boolean"},
                "limit": {"type": "integer", "description": "default 30, max 100"},
            },
        },
    },
    {
        "name": "saldo_obra",
        "description": "Saldo financiero de una obra: ingresos, egresos, saldo y % ejecutado del contrato.",
        "input_schema": {
            "type": "object",
            "properties": {"obra": {"type": "string"}},
            "required": ["obra"],
        },
    },
    {
        "name": "flujo_caja_obra",
        "description": "Flujo de caja semanal de una obra con saldo acumulado.",
        "input_schema": {
            "type": "object",
            "properties": {"obra": {"type": "string"}},
            "required": ["obra"],
        },
    },
    {
        "name": "aportes_pendientes",
        "description": "Aportes de socios sin devolver (parcial o total). Útil para chequear deudas internas.",
        "input_schema": {
            "type": "object",
            "properties": {"obra": {"type": "string", "description": "opcional, filtra por obra"}},
        },
    },
    {
        "name": "cheques_a_vencer",
        "description": "Cheques propios cuyo vencimiento cae en los próximos N días. Crítico para flujo de caja.",
        "input_schema": {
            "type": "object",
            "properties": {"dias": {"type": "integer", "description": "horizonte en días, default 30"}},
        },
    },
    {
        "name": "descalce_fiscal",
        "description": "Detecta obras con egresos facturados > ingresos facturados (crédito fiscal IVA pendiente). Solo admin/finanzas.",
        "input_schema": {
            "type": "object",
            "properties": {"obra_id": {"type": "integer", "description": "opcional"}},
        },
    },
    {
        "name": "alertas_stock_bajo",
        "description": "Materiales cuyo stock está por debajo del mínimo configurado.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_proveedores",
        "description": "Proveedores con rating y plazo de entrega. Filtros por rubro o solo morosos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rubro": {"type": "string"},
                "solo_morosos": {"type": "boolean"},
            },
        },
    },
    {
        "name": "listar_cuadrillas",
        "description": "Cuadrillas (capa lúdica/operativa) con su especialidad, nivel y XP.",
        "input_schema": {
            "type": "object",
            "properties": {"especialidad": {"type": "string"}},
        },
    },
    {
        "name": "eventos_recientes",
        "description": "Eventos del feed (avances, materiales, incidentes, fotos) recientes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "solo_criticos": {"type": "boolean"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "listar_usuarios",
        "description": "Lista usuarios del sistema. Solo admin.",
        "input_schema": {
            "type": "object",
            "properties": {"rol": {"type": "string"}},
        },
    },
    # ─── ESCRITURA (Sprint 2) — todas requieren confirmación humana ───
    {
        "name": "registrar_aporte_socio",
        "description": (
            "Registra un aporte de socio en una obra (préstamo interno con obligación de devolución). "
            "REQUIERE CONFIRMACIÓN HUMANA. R2: dispara automáticamente un movimiento INGRESO espejo "
            "con origen APORTE_SOCIO_RCA."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string", "description": "id, código o parte del nombre"},
                "socio_id": {"type": "integer", "description": "id del usuario que actúa como socio"},
                "monto": {"type": "number", "description": "siempre positivo"},
                "motivo": {"type": "string", "description": "explicación corta del aporte"},
                "fecha_aporte": {"type": "string", "description": "YYYY-MM-DD, default hoy"},
                "medio_pago": {
                    "type": "string",
                    "enum": ["EFECTIVO", "TRANSFERENCIA", "CHEQUE_PROPIO", "CHEQUE_TERCERO", "DEPOSITO_BANCARIO"],
                },
                "etapa_reintegro_id": {"type": "integer", "description": "etapa en la que se prevé devolver"},
            },
            "required": ["obra", "socio_id", "monto", "motivo", "medio_pago"],
        },
    },
    {
        "name": "enviar_whatsapp",
        "description": (
            "STUB de Sprint 4. Registra la intención de enviar un WhatsApp pero NO lo entrega aún. "
            "REQUIERE CONFIRMACIÓN. Cuando se integre Twilio/WhatsApp Cloud API, esta misma firma "
            "va a enviar el mensaje real."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "telefono": {"type": "string", "description": "formato +5491100000000"},
                "mensaje": {"type": "string"},
                "obra_ref": {"type": "string", "description": "obra que da contexto al mensaje (opcional)"},
            },
            "required": ["telefono", "mensaje"],
        },
    },
    {
        "name": "cargar_comprobante",
        "description": (
            "Carga un comprobante AFIP (FC_A/B/C, NC, ND, Recibo X, Remito) ligado a una obra. "
            "REQUIERE CONFIRMACIÓN. Validación: neto_gravado + neto_no_gravado + iva_21 + iva_105 = total."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "tipo_comprobante": {
                    "type": "string",
                    "enum": ["FC_A", "FC_B", "FC_C", "NC_A", "NC_B", "ND_A", "ND_B", "RECIBO_X", "REMITO"],
                },
                "punto_venta": {"type": "integer"},
                "nro_comprobante": {"type": "string", "description": "ej '00001-00012345'"},
                "fecha_emision": {"type": "string", "description": "YYYY-MM-DD"},
                "cuit_emisor": {"type": "string"},
                "cuit_receptor": {"type": "string"},
                "neto_gravado": {"type": "number"},
                "neto_no_gravado": {"type": "number"},
                "iva_21": {"type": "number"},
                "iva_105": {"type": "number"},
                "total": {"type": "number"},
                "cae": {"type": "string"},
                "cae_vencimiento": {"type": "string", "description": "YYYY-MM-DD"},
                "es_venta": {"type": "boolean", "description": "true=emitido, false=recibido"},
                "estado_fiscal": {
                    "type": "string",
                    "enum": ["VALIDO", "SIN_CAE", "VENCIDO", "ANULADO"],
                },
                "archivo_url": {"type": "string"},
                "notas": {"type": "string"},
            },
            "required": ["obra", "tipo_comprobante", "nro_comprobante", "fecha_emision",
                         "cuit_emisor", "cuit_receptor", "total", "es_venta"],
        },
    },
    {
        "name": "crear_cliente",
        "description": (
            "Crea un cliente nuevo. REQUIERE CONFIRMACIÓN. "
            "Tipo: publico, privado_ri, privado_mt o particular. CUIT debe ser único si se provee."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"},
                "cuit": {"type": "string"},
                "razon_social": {"type": "string"},
                "direccion": {"type": "string"},
                "email": {"type": "string"},
                "telefono": {"type": "string"},
                "tipo": {"type": "string", "enum": ["publico", "privado_ri", "privado_mt", "particular"]},
                "regimen_fiscal_id": {"type": "integer"},
                "notas": {"type": "string"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "crear_obra",
        "description": (
            "Crea una obra nueva ligada a un cliente. REQUIERE CONFIRMACIÓN. "
            "Si no se especifica regimen_fiscal_id, hereda el del cliente. Código debe ser único."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "codigo": {"type": "string", "description": "ej IDS, SP, CASA-01"},
                "nombre": {"type": "string"},
                "cliente_id": {"type": "integer", "description": "id del cliente (creá primero con crear_cliente)"},
                "regimen_fiscal_id": {"type": "integer", "description": "opcional, default toma el del cliente"},
                "tipo_facturacion": {
                    "type": "string",
                    "enum": ["TOTAL_BLANCO", "TOTAL_NEGRO", "MIXTA", "SIN_DEFINIR"],
                },
                "direccion": {"type": "string"},
                "ciudad": {"type": "string"},
                "descripcion": {"type": "string"},
                "monto_contrato": {"type": "number"},
                "fecha_inicio": {"type": "string", "description": "YYYY-MM-DD"},
                "fecha_fin_estimada": {"type": "string", "description": "YYYY-MM-DD"},
                "icono": {"type": "string", "description": "emoji"},
                "color": {"type": "string", "description": "hex color"},
                "superficie_m2": {"type": "number"},
                "pisos": {"type": "integer"},
            },
            "required": ["codigo", "nombre", "cliente_id"],
        },
    },
    {
        "name": "crear_orden",
        "description": (
            "Crea una orden de trabajo (quest operativa) en una obra. REQUIERE CONFIRMACIÓN. "
            "Puede asignarse a un frente y a una cuadrilla. Otorga XP cuando se cierra."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "titulo": {"type": "string"},
                "descripcion": {"type": "string"},
                "frente_id": {"type": "integer"},
                "cuadrilla_id": {"type": "integer"},
                "prioridad": {"type": "string", "enum": ["baja", "normal", "alta", "critica"]},
                "fecha_limite": {"type": "string", "description": "YYYY-MM-DD"},
                "xp_reward": {"type": "integer", "description": "XP que da al cerrar, default 10"},
            },
            "required": ["obra", "titulo"],
        },
    },
    {
        "name": "cerrar_orden",
        "description": (
            "Marca una orden como completada. REQUIERE CONFIRMACIÓN. "
            "Suma xp_reward al usuario y a la cuadrilla asignada (sube nivel cada 100 XP). "
            "Crea evento 'avance' en el feed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "orden_id": {"type": "integer"},
                "nota_cierre": {"type": "string", "description": "comentario opcional para el evento"},
            },
            "required": ["orden_id"],
        },
    },
    {
        "name": "reportar_evento",
        "description": (
            "Crea un evento en el feed de actividad de una obra. REQUIERE CONFIRMACIÓN. "
            "Tipo 'incidente' marca automáticamente es_critico=true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "titulo": {"type": "string"},
                "descripcion": {"type": "string"},
                "tipo": {
                    "type": "string",
                    "enum": ["avance", "material_llegada", "incidente", "inspeccion", "foto", "hito", "otro"],
                },
                "frente_id": {"type": "integer"},
                "foto_url": {"type": "string"},
                "es_critico": {"type": "boolean"},
            },
            "required": ["obra", "titulo"],
        },
    },
    {
        "name": "crear_etapa",
        "description": (
            "Crea una etapa nueva en una obra (anticipo, etapa N, final) con monto contractual y "
            "fecha estimada de cobro. REQUIERE CONFIRMACIÓN HUMANA. nro_etapa=0 para anticipo, "
            "1+ para sucesivas. No permite duplicados."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "nombre": {"type": "string", "description": "ej: 'Etapa 2 - Terminaciones'"},
                "nro_etapa": {"type": "integer", "description": "0=anticipo, 1=etapa1, 2=etapa2..."},
                "monto_contractual": {"type": "number"},
                "porcentaje_avance": {"type": "number", "description": "% sobre el total de la obra"},
                "fecha_estimada": {"type": "string", "description": "YYYY-MM-DD, fecha estimada de cobro"},
                "estado": {
                    "type": "string",
                    "enum": ["PENDIENTE", "EN_EJECUCION", "EJECUTADA", "FACTURADA", "COBRADA"],
                    "description": "default PENDIENTE",
                },
                "notas": {"type": "string"},
            },
            "required": ["obra", "nombre", "nro_etapa"],
        },
    },
    {
        "name": "cambiar_estado_etapa",
        "description": (
            "Cambia el estado de una etapa siguiendo el ciclo "
            "PENDIENTE → EN_EJECUCION → EJECUTADA → FACTURADA → COBRADA. REQUIERE CONFIRMACIÓN. "
            "R5: al pasar a COBRADA, si hay aportes de socio pendientes vinculados a esta etapa, "
            "se crea automáticamente una nota importante para alertar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "etapa_id": {"type": "integer"},
                "nuevo_estado": {
                    "type": "string",
                    "enum": ["PENDIENTE", "EN_EJECUCION", "EJECUTADA", "FACTURADA", "COBRADA"],
                },
                "fecha_cobro_real": {
                    "type": "string",
                    "description": "YYYY-MM-DD, solo si nuevo_estado=COBRADA, default hoy",
                },
            },
            "required": ["etapa_id", "nuevo_estado"],
        },
    },
    {
        "name": "registrar_devolucion_aporte",
        "description": (
            "Registra una devolución (parcial o total) de un aporte de socio. "
            "REQUIERE CONFIRMACIÓN HUMANA. Crea un EGRESO espejo con categoría APORTE_PRESTAMO. "
            "Si el monto devuelto iguala el aporte original, marca DEVUELTO_TOTAL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aporte_id": {"type": "integer"},
                "monto": {"type": "number", "description": "monto a devolver, no puede exceder el pendiente"},
                "fecha": {"type": "string", "description": "YYYY-MM-DD, default hoy"},
                "medio_pago": {
                    "type": "string",
                    "enum": ["EFECTIVO", "TRANSFERENCIA", "CHEQUE_PROPIO", "CHEQUE_TERCERO", "DEPOSITO_BANCARIO"],
                },
                "notas": {"type": "string"},
            },
            "required": ["aporte_id", "monto", "medio_pago"],
        },
    },
    {
        "name": "registrar_movimiento",
        "description": (
            "Registra un movimiento financiero (INGRESO o EGRESO) en una obra. "
            "REQUIERE CONFIRMACIÓN HUMANA antes de ejecutarse — el sistema mostrará "
            "los datos al usuario y esperará que apriete Confirmar. "
            "Si tipo=INGRESO usar origen_ingreso. Si tipo=EGRESO usar categoria_egreso. "
            "Si medio_pago es CHEQUE_PROPIO o CHEQUE_TERCERO, también nro_cheque + fecha_vto_cheque. "
            "Obras TOTAL_BLANCO exigen comprobante en ingresos de cliente."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string", "description": "id, código (IDS, SP) o parte del nombre"},
                "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"]},
                "monto": {"type": "number", "description": "siempre positivo, en pesos"},
                "concepto": {"type": "string", "description": "descripción corta del movimiento"},
                "fecha": {"type": "string", "description": "YYYY-MM-DD, default hoy"},
                "medio_pago": {
                    "type": "string",
                    "enum": ["EFECTIVO", "TRANSFERENCIA", "CHEQUE_PROPIO", "CHEQUE_TERCERO", "DEPOSITO_BANCARIO"],
                },
                "origen_ingreso": {
                    "type": "string",
                    "enum": [
                        "ANTICIPO_CLIENTE", "CERTIFICADO_ETAPA", "PAGO_FINAL",
                        "AJUSTE_CONTRATO", "APORTE_SOCIO_RCA", "DEVOLUCION_PROVEEDOR",
                    ],
                    "description": "solo si tipo=INGRESO",
                },
                "categoria_egreso": {
                    "type": "string",
                    "enum": [
                        "MANO_DE_OBRA", "MATERIALES", "SUBCONTRATO", "SERVICIO_EXTERNO",
                        "GASTO_DIRECTO_OBRA", "HERRAMIENTA_EQUIPO", "APORTE_PRESTAMO",
                    ],
                    "description": "solo si tipo=EGRESO",
                },
                "nro_cheque": {"type": "string", "description": "requerido si medio_pago es cheque"},
                "banco": {"type": "string"},
                "fecha_vto_cheque": {
                    "type": "string",
                    "description": "YYYY-MM-DD, requerido si medio_pago es cheque",
                },
                "etapa_id": {"type": "integer", "description": "etapa de obra a la que se imputa"},
                "comprobante_id": {"type": "integer", "description": "id de comprobante AFIP previamente cargado"},
            },
            "required": ["obra", "tipo", "monto", "concepto", "medio_pago"],
        },
    },
    # ─── Sprint 9: Stock multi-ubicación ───
    {
        "name": "consultar_stock",
        "description": "LECTURA. Devuelve el desglose de stock por ubicación para uno o todos los materiales. "
                       "Cada material reporta cantidad en depósito propio, en cada obra, y pendiente de retiro en proveedores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "id o nombre parcial. Si se omite, devuelve TODOS."},
            },
        },
    },
    {
        "name": "cargar_compra_pendiente_retiro",
        "description": "ESCRITURA. Registra una compra ya pagada/facturada cuya mercadería sigue en el proveedor (estado 'comprado_no_retirado').",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "id o nombre del material"},
                "proveedor": {"type": "string", "description": "id o nombre del proveedor"},
                "cantidad": {"type": "number"},
                "nota": {"type": "string"},
            },
            "required": ["material", "proveedor", "cantidad"],
        },
    },
    {
        "name": "retirar_de_proveedor",
        "description": "ESCRITURA. Marca como retirada del proveedor parte (o toda) la mercadería pendiente. "
                       "Va a depósito propio o directo a una obra. Decrementa 'comprado_no_retirado' y aumenta el destino.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "proveedor": {"type": "string"},
                "cantidad": {"type": "number"},
                "destino_tipo": {"type": "string", "enum": ["deposito_propio", "en_obra"]},
                "obra": {"type": "string", "description": "obra destino. Requerido si destino_tipo=en_obra"},
                "nota": {"type": "string"},
            },
            "required": ["material", "proveedor", "cantidad", "destino_tipo"],
        },
    },
    {
        "name": "consumir_en_obra",
        "description": "ESCRITURA. Registra consumo de material en una obra (la cuadrilla usó X cantidad). "
                       "Decrementa el stock de en_obra para ese material.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "obra": {"type": "string"},
                "cantidad": {"type": "number"},
                "nota": {"type": "string"},
            },
            "required": ["material", "obra", "cantidad"],
        },
    },
    {
        "name": "transferir_stock",
        "description": "ESCRITURA. Mueve stock entre depósito propio y obras (o entre obras). "
                       "Útil para devolver material no usado al depósito o redistribuir entre obras.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "cantidad": {"type": "number"},
                "origen_tipo": {"type": "string", "enum": ["deposito_propio", "en_obra"]},
                "obra_origen": {"type": "string", "description": "Requerido si origen_tipo=en_obra"},
                "destino_tipo": {"type": "string", "enum": ["deposito_propio", "en_obra"]},
                "obra_destino": {"type": "string", "description": "Requerido si destino_tipo=en_obra"},
                "nota": {"type": "string"},
            },
            "required": ["material", "cantidad", "origen_tipo", "destino_tipo"],
        },
    },
    # ─── Sprint 10: Presupuestos de materiales ───
    {
        "name": "consultar_presupuestos",
        "description": "LECTURA. Lista presupuestos de materiales (filtrable por obra y/o estado borrador/aprobado/cerrado).",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "estado": {"type": "string", "enum": ["borrador", "aprobado", "cerrado"]},
            },
        },
    },
    {
        "name": "crear_presupuesto",
        "description": "ESCRITURA. Crea un presupuesto de materiales para una obra (en estado borrador). "
                       "Acepta items como lista [{material, cantidad, precio?}]. Si no se pasa precio, usa Material.precio_unitario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string"},
                "nombre": {"type": "string", "description": "ej: 'Presupuesto cimientos enero'"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "material": {"type": "string"},
                            "cantidad": {"type": "number"},
                            "precio": {"type": "number"},
                        },
                        "required": ["material", "cantidad"],
                    },
                },
                "notas": {"type": "string"},
            },
            "required": ["obra", "nombre", "items"],
        },
    },
    {
        "name": "aprobar_presupuesto",
        "description": "ESCRITURA. Marca un presupuesto borrador como aprobado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "presupuesto_id": {"type": "integer"},
            },
            "required": ["presupuesto_id"],
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict, models.User, Session], dict]] = {
    "dashboard_hud": t_dashboard_hud,
    "listar_obras": t_listar_obras,
    "obtener_obra": t_obtener_obra,
    "listar_clientes": t_listar_clientes,
    "listar_etapas": t_listar_etapas,
    "listar_movimientos": t_listar_movimientos,
    "saldo_obra": t_saldo_obra,
    "flujo_caja_obra": t_flujo_caja_obra,
    "aportes_pendientes": t_aportes_pendientes,
    "cheques_a_vencer": t_cheques_a_vencer,
    "descalce_fiscal": t_descalce_fiscal,
    "alertas_stock_bajo": t_alertas_stock_bajo,
    "listar_proveedores": t_listar_proveedores,
    "listar_cuadrillas": t_listar_cuadrillas,
    "eventos_recientes": t_eventos_recientes,
    "listar_usuarios": t_listar_usuarios,
    # ─── escritura ───
    "registrar_movimiento": t_registrar_movimiento,
    "registrar_aporte_socio": t_registrar_aporte_socio,
    "registrar_devolucion_aporte": t_registrar_devolucion_aporte,
    "crear_etapa": t_crear_etapa,
    "cambiar_estado_etapa": t_cambiar_estado_etapa,
    "crear_orden": t_crear_orden,
    "cerrar_orden": t_cerrar_orden,
    "reportar_evento": t_reportar_evento,
    "cargar_comprobante": t_cargar_comprobante,
    "crear_cliente": t_crear_cliente,
    "crear_obra": t_crear_obra,
    "enviar_whatsapp": t_enviar_whatsapp,
    # ─── Sprint 9: stock (1 lectura + 4 escritura) ───
    "consultar_stock": t_consultar_stock,
    "cargar_compra_pendiente_retiro": t_cargar_compra_pendiente_retiro,
    "retirar_de_proveedor": t_retirar_de_proveedor,
    "consumir_en_obra": t_consumir_en_obra,
    "transferir_stock": t_transferir_stock,
    # ─── Sprint 10: presupuestos (1 lectura + 2 escritura) ───
    "consultar_presupuestos": t_consultar_presupuestos,
    "crear_presupuesto": t_crear_presupuesto,
    "aprobar_presupuesto": t_aprobar_presupuesto,
}


# Tools sensibles que SIEMPRE requieren confirmación humana antes de ejecutar.
# El orchestrator intercepta estas calls, persiste un AgentAction pendiente
# y devuelve {requires_confirmation: true, action_id, preview} a Claude.
# La ejecución real ocurre cuando el usuario clickea Confirmar en la UI
# (POST /api/agent/confirm/{action_id}).
#
# Criterio (Sprint 2): TODAS las tools de escritura requieren confirmación.
# Las tools de lectura (las 16 originales) nunca piden confirmación.
# En Sprint 7 podríamos relajar para algunos casos según rol del usuario.
REQUIRES_CONFIRMATION_TOOLS: set[str] = {
    # Financiero (crítico)
    "registrar_movimiento",
    "registrar_aporte_socio",
    "registrar_devolucion_aporte",
    "cargar_comprobante",
    # Estructura de obra
    "crear_obra",
    "crear_cliente",
    "crear_etapa",
    "cambiar_estado_etapa",
    # Capa lúdica / operativa
    "crear_orden",
    "cerrar_orden",
    "reportar_evento",
    # Mensajería externa (visible a terceros)
    "enviar_whatsapp",
    # Sprint 9 — Stock (todas las mutaciones requieren confirmación)
    "cargar_compra_pendiente_retiro",
    "retirar_de_proveedor",
    "consumir_en_obra",
    "transferir_stock",
    # Sprint 10 — Presupuestos
    "crear_presupuesto",
    "aprobar_presupuesto",
}
