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
}
