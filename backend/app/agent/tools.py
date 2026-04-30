"""Tool registry del agente operario.

Sprint 1: SOLO LECTURA. Cada tool es:
- una entrada en TOOLS_SCHEMA (lo que ve Claude)
- una función registrada en TOOL_HANDLERS que recibe (input_dict, user, db)

Sprint 2 sumará tools de escritura con confirmación humana.
"""
from __future__ import annotations
from typing import Any, Callable
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date, timedelta
from app import models


# ─── Helpers ───
def _obra_by_ref(ref: str | int, db: Session) -> models.Obra | None:
    """Busca una obra por id, código o nombre (case-insensitive parcial)."""
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        o = db.query(models.Obra).filter(models.Obra.id == int(ref)).first()
        if o:
            return o
    if isinstance(ref, str):
        low = ref.strip()
        # match exacto por código
        o = db.query(models.Obra).filter(func.lower(models.Obra.codigo) == low.lower()).first()
        if o:
            return o
        # match parcial por nombre
        return db.query(models.Obra).filter(models.Obra.nombre.ilike(f"%{low}%")).first()
    return None


def _serialize_obra(o: models.Obra) -> dict:
    return {
        "id": o.id,
        "codigo": o.codigo,
        "nombre": o.nombre,
        "ciudad": o.ciudad,
        "cliente": o.cliente,
        "status": o.status.value if o.status else None,
        "salud": o.salud.value if o.salud else None,
        "progreso": round(o.progreso or 0, 1),
        "presupuesto_total": o.presupuesto_total or 0,
        "presupuesto_consumido": o.presupuesto_consumido or 0,
        "presupuesto_disponible": (o.presupuesto_total or 0) - (o.presupuesto_consumido or 0),
        "fecha_inicio": o.fecha_inicio.isoformat() if o.fecha_inicio else None,
        "fecha_fin_estimada": o.fecha_fin_estimada.isoformat() if o.fecha_fin_estimada else None,
    }


# ─── Tool handlers ───

def t_listar_obras(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Obra)
    estado = input.get("estado")
    if estado:
        try:
            q = q.filter(models.Obra.status == models.ObraStatus(estado))
        except ValueError:
            return {"error": f"estado inválido: {estado}. Valores: planificacion, en_obra, pausada, finalizada"}
    salud = input.get("salud")
    if salud:
        try:
            q = q.filter(models.Obra.salud == models.ObraSalud(salud))
        except ValueError:
            return {"error": f"salud inválida: {salud}. Valores: optimo, atencion, critico"}
    obras = q.order_by(models.Obra.created_at.desc()).limit(50).all()
    return {"total": len(obras), "obras": [_serialize_obra(o) for o in obras]}


def t_obtener_obra(input: dict, user: models.User, db: Session) -> dict:
    ref = input.get("referencia")
    if not ref:
        return {"error": "Falta 'referencia' (id, código o nombre)"}
    o = _obra_by_ref(ref, db)
    if not o:
        return {"error": f"No encontré obra '{ref}'"}
    # info enriquecida: frentes, ordenes, cuadrillas
    frentes = db.query(models.Frente).filter(models.Frente.obra_id == o.id).all()
    ordenes_pend = db.query(models.OrdenTrabajo).filter(
        models.OrdenTrabajo.obra_id == o.id,
        models.OrdenTrabajo.status.in_([models.TaskStatus.pendiente, models.TaskStatus.en_progreso])
    ).count()
    eventos_recientes = db.query(models.Evento).filter(
        models.Evento.obra_id == o.id
    ).order_by(models.Evento.fecha.desc()).limit(5).all()
    data = _serialize_obra(o)
    data.update({
        "frentes": [
            {"id": f.id, "nombre": f.nombre, "estado": f.estado.value, "progreso": f.progreso}
            for f in frentes
        ],
        "ordenes_pendientes": ordenes_pend,
        "eventos_recientes": [
            {"tipo": e.tipo.value, "titulo": e.titulo, "es_critico": e.es_critico,
             "fecha": e.fecha.isoformat() if e.fecha else None}
            for e in eventos_recientes
        ],
    })
    return data


def t_listar_ordenes(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.OrdenTrabajo)
    if obra_ref := input.get("obra"):
        o = _obra_by_ref(obra_ref, db)
        if not o:
            return {"error": f"Obra '{obra_ref}' no encontrada"}
        q = q.filter(models.OrdenTrabajo.obra_id == o.id)
    if status := input.get("status"):
        try:
            q = q.filter(models.OrdenTrabajo.status == models.TaskStatus(status))
        except ValueError:
            return {"error": f"status inválido: {status}. Valores: pendiente, en_progreso, completada, bloqueada"}
    ordenes = q.order_by(models.OrdenTrabajo.created_at.desc()).limit(50).all()
    return {
        "total": len(ordenes),
        "ordenes": [
            {
                "id": x.id,
                "obra_id": x.obra_id,
                "titulo": x.titulo,
                "status": x.status.value,
                "prioridad": x.prioridad,
                "xp_reward": x.xp_reward,
                "fecha_limite": x.fecha_limite.isoformat() if x.fecha_limite else None,
            }
            for x in ordenes
        ],
    }


def t_listar_cuadrillas(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Cuadrilla).filter(models.Cuadrilla.activa == True)  # noqa: E712
    if esp := input.get("especialidad"):
        q = q.filter(models.Cuadrilla.especialidad.ilike(f"%{esp}%"))
    cuadrillas = q.order_by(models.Cuadrilla.experiencia.desc()).all()
    return {
        "total": len(cuadrillas),
        "cuadrillas": [
            {
                "id": c.id,
                "nombre": c.nombre,
                "especialidad": c.especialidad,
                "miembros": c.cantidad_miembros,
                "nivel": c.nivel,
                "xp": c.experiencia,
                "eficiencia": c.eficiencia,
                "telefono": c.telefono,
            }
            for c in cuadrillas
        ],
    }


def t_consultar_stock(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Material)
    if nombre := input.get("material"):
        q = q.filter(models.Material.nombre.ilike(f"%{nombre}%"))
    if cat := input.get("categoria"):
        q = q.filter(models.Material.categoria.ilike(f"%{cat}%"))
    mats = q.all()
    return {
        "total": len(mats),
        "materiales": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "categoria": m.categoria,
                "stock": m.stock,
                "stock_minimo": m.stock_minimo,
                "unidad": m.unidad,
                "alerta": m.stock < m.stock_minimo,
                "precio_unitario": m.precio_unitario,
            }
            for m in mats
        ],
    }


def t_alertas_stock_bajo(input: dict, user: models.User, db: Session) -> dict:
    mats = db.query(models.Material).filter(
        models.Material.stock < models.Material.stock_minimo
    ).all()
    return {
        "total": len(mats),
        "materiales_criticos": [
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
            {
                "id": p.id,
                "nombre": p.nombre,
                "rubro": p.rubro,
                "rating": p.rating,
                "plazo_dias": p.plazo_entrega_dias,
                "moroso": p.moroso,
                "telefono": p.telefono,
            }
            for p in provs
        ],
    }


def t_dashboard_hud(input: dict, user: models.User, db: Session) -> dict:
    obras = db.query(models.Obra).all()
    cuadrillas = db.query(models.Cuadrilla).filter(models.Cuadrilla.activa == True).all()  # noqa: E712
    materiales = db.query(models.Material).all()
    materiales_criticos = sum(1 for m in materiales if m.stock < m.stock_minimo)
    eventos_criticos = db.query(models.Evento).filter(models.Evento.es_critico == True).count()  # noqa: E712
    presup_total = sum(o.presupuesto_total or 0 for o in obras)
    presup_consumido = sum(o.presupuesto_consumido or 0 for o in obras)
    obras_activas = sum(1 for o in obras if o.status == models.ObraStatus.en_obra)
    productividad = (sum(c.eficiencia for c in cuadrillas) / len(cuadrillas)) if cuadrillas else 0
    obreros = sum(c.cantidad_miembros for c in cuadrillas)
    return {
        "presupuesto_total": presup_total,
        "presupuesto_consumido": presup_consumido,
        "presupuesto_disponible": presup_total - presup_consumido,
        "obras_total": len(obras),
        "obras_activas": obras_activas,
        "cuadrillas_activas": len(cuadrillas),
        "obreros_total": obreros,
        "productividad_promedio": round(productividad, 1),
        "materiales_total": len(materiales),
        "materiales_criticos": materiales_criticos,
        "alertas_total": eventos_criticos,
    }


def t_eventos_recientes(input: dict, user: models.User, db: Session) -> dict:
    q = db.query(models.Evento)
    if obra_ref := input.get("obra"):
        o = _obra_by_ref(obra_ref, db)
        if not o:
            return {"error": f"Obra '{obra_ref}' no encontrada"}
        q = q.filter(models.Evento.obra_id == o.id)
    if input.get("solo_criticos"):
        q = q.filter(models.Evento.es_critico == True)  # noqa: E712
    limit = min(int(input.get("limit", 20)), 100)
    eventos = q.order_by(models.Evento.fecha.desc()).limit(limit).all()
    return {
        "total": len(eventos),
        "eventos": [
            {
                "id": e.id,
                "obra_id": e.obra_id,
                "tipo": e.tipo.value,
                "titulo": e.titulo,
                "es_critico": e.es_critico,
                "canal": e.canal.value if e.canal else None,
                "fecha": e.fecha.isoformat() if e.fecha else None,
            }
            for e in eventos
        ],
    }


def t_finanzas_obra(input: dict, user: models.User, db: Session) -> dict:
    # gated por rol
    if user.role not in (models.UserRole.admin, models.UserRole.admin_finanzas):
        return {"error": "No tenés permiso para ver finanzas detalladas"}
    ref = input.get("obra")
    if not ref:
        return {"error": "Falta 'obra' (id, código o nombre)"}
    o = _obra_by_ref(ref, db)
    if not o:
        return {"error": f"Obra '{ref}' no encontrada"}
    gastos = db.query(models.Gasto).filter(models.Gasto.obra_id == o.id).all()
    por_categoria: dict[str, float] = {}
    pendientes = 0.0
    for g in gastos:
        por_categoria[g.categoria] = por_categoria.get(g.categoria, 0) + g.monto
        if not g.pagado:
            pendientes += g.monto
    return {
        "obra": o.nombre,
        "presupuesto_total": o.presupuesto_total,
        "presupuesto_consumido": o.presupuesto_consumido,
        "presupuesto_disponible": (o.presupuesto_total or 0) - (o.presupuesto_consumido or 0),
        "porcentaje_consumido": round(((o.presupuesto_consumido or 0) / o.presupuesto_total * 100), 1) if o.presupuesto_total else 0,
        "gastos_totales": sum(g.monto for g in gastos),
        "gastos_pendientes_pago": pendientes,
        "gastos_por_categoria": por_categoria,
        "cantidad_gastos": len(gastos),
    }


def t_listar_usuarios(input: dict, user: models.User, db: Session) -> dict:
    if user.role not in (models.UserRole.admin, models.UserRole.admin_finanzas):
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
            {"id": u.id, "name": u.name, "email": u.email, "role": u.role.value,
             "status": u.status.value, "xp": u.xp, "telefono": u.phone}
            for u in users
        ],
    }


# ─── Schema para Anthropic ───
TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "listar_obras",
        "description": "Lista todas las obras de la constructora, con su estado, salud (verde/amarillo/rojo) y progreso. Útil para preguntas como 'qué obras tengo', 'qué obras están en rojo', 'qué obras están en planificación'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "estado": {"type": "string", "enum": ["planificacion", "en_obra", "pausada", "finalizada"], "description": "Filtrar por estado"},
                "salud": {"type": "string", "enum": ["optimo", "atencion", "critico"], "description": "Filtrar por salud (verde/amarillo/rojo)"},
            },
        },
    },
    {
        "name": "obtener_obra",
        "description": "Trae el detalle completo de una obra: frentes, órdenes pendientes, eventos recientes, presupuesto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "referencia": {"type": "string", "description": "id, código o parte del nombre de la obra"},
            },
            "required": ["referencia"],
        },
    },
    {
        "name": "listar_ordenes",
        "description": "Lista órdenes de trabajo, opcionalmente filtradas por obra y/o status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string", "description": "id, código o nombre de la obra"},
                "status": {"type": "string", "enum": ["pendiente", "en_progreso", "completada", "bloqueada"]},
            },
        },
    },
    {
        "name": "listar_cuadrillas",
        "description": "Lista cuadrillas (equipos) con su especialidad, nivel, XP y eficiencia.",
        "input_schema": {
            "type": "object",
            "properties": {
                "especialidad": {"type": "string", "description": "filtrar por especialidad (albañilería, electricidad, plomería, etc.)"},
            },
        },
    },
    {
        "name": "consultar_stock",
        "description": "Consulta stock actual de materiales. Sin parámetros lista todos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "material": {"type": "string", "description": "nombre o parte del nombre"},
                "categoria": {"type": "string", "description": "categoría (cemento, hierro, etc.)"},
            },
        },
    },
    {
        "name": "alertas_stock_bajo",
        "description": "Devuelve materiales cuyo stock está por debajo del mínimo configurado.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "listar_proveedores",
        "description": "Lista proveedores con rating y plazo de entrega.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rubro": {"type": "string"},
                "solo_morosos": {"type": "boolean", "description": "True para listar solo proveedores morosos"},
            },
        },
    },
    {
        "name": "dashboard_hud",
        "description": "Resumen ejecutivo global: presupuesto total/consumido/disponible, obras activas, cuadrillas, productividad promedio, alertas. Usar para preguntas tipo 'cómo va todo' o 'dame un resumen'.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "eventos_recientes",
        "description": "Trae eventos del feed de actividad (avances, materiales, incidentes, fotos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string", "description": "filtrar por obra"},
                "solo_criticos": {"type": "boolean"},
                "limit": {"type": "integer", "description": "default 20, max 100"},
            },
        },
    },
    {
        "name": "finanzas_obra",
        "description": "Detalle financiero de una obra: presupuesto, gastos totales, gastos pendientes de pago, breakdown por categoría. Solo admin/admin_finanzas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "obra": {"type": "string", "description": "id, código o nombre de la obra"},
            },
            "required": ["obra"],
        },
    },
    {
        "name": "listar_usuarios",
        "description": "Lista usuarios del sistema y sus roles. Solo admin.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rol": {"type": "string", "enum": ["admin_finanzas", "admin", "supervisor", "usuario_bot"]},
            },
        },
    },
]


TOOL_HANDLERS: dict[str, Callable[[dict, models.User, Session], dict]] = {
    "listar_obras": t_listar_obras,
    "obtener_obra": t_obtener_obra,
    "listar_ordenes": t_listar_ordenes,
    "listar_cuadrillas": t_listar_cuadrillas,
    "consultar_stock": t_consultar_stock,
    "alertas_stock_bajo": t_alertas_stock_bajo,
    "listar_proveedores": t_listar_proveedores,
    "dashboard_hud": t_dashboard_hud,
    "eventos_recientes": t_eventos_recientes,
    "finanzas_obra": t_finanzas_obra,
    "listar_usuarios": t_listar_usuarios,
}
