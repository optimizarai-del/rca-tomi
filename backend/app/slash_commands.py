"""Parser de comandos slash para WhatsApp.

Comandos disponibles (sintaxis):
    /help                                  - lista los comandos
    /saldo [obra]                          - saldo global o de una obra (código o nombre)
    /cheques [dias]                        - cheques a vencer en N días (default 30)
    /aportes                               - aportes de socios pendientes
    /avance <obra> <%>                     - actualiza progreso de obra (0-100)
    /gasto <obra> <monto> <concepto>       - registra EGRESO (categoría: GASTO_DIRECTO_OBRA)

Cada comando devuelve un dict {ok, reply, ...}. El llamador envía `reply` por WhatsApp.
Funciona sin LLM — todo es parsing local + queries directas a la DB.
"""
from __future__ import annotations
import shlex
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models


HELP = (
    "📋 Comandos disponibles:\n"
    "/saldo [obra]           - saldo global o por obra\n"
    "/cheques [dias]         - cheques a vencer en N días\n"
    "/aportes                - aportes pendientes\n"
    "/avance <obra> <%>      - actualiza progreso\n"
    "/gasto <obra> <monto> <concepto>  - registra egreso\n"
    "/stock [material]       - stock multi-ubicación (Sprint 9)\n"
    "/pendientes [dias]      - stock pendiente de retiro (Sprint 14)\n"
    "/req <obra> <mensaje>   - anota requerimiento/imprevisto (Sprint 17)\n"
    "/pendientes_ocr         - tickets de OCR sin confirmar (Sprint 18)\n"
    "/confirmar <id> <obra>  - confirma ticket OCR y crea movimiento\n"
    "/rechazar <id>          - descarta ticket OCR\n"
    "/help                   - este menú"
)


def fmt_money(n: float) -> str:
    if n is None:
        return "$0"
    sign = "-" if n < 0 else ""
    abs_n = abs(n)
    if abs_n >= 1e6:
        return f"{sign}${abs_n / 1e6:.2f}M"
    if abs_n >= 1e3:
        return f"{sign}${abs_n / 1e3:.0f}k"
    return f"{sign}${round(abs_n)}"


def _obra_by_ref(ref: str, db: Session) -> Optional[models.Obra]:
    if not ref:
        return None
    if ref.isdigit():
        o = db.query(models.Obra).filter(models.Obra.id == int(ref)).first()
        if o:
            return o
    o = db.query(models.Obra).filter(func.lower(models.Obra.codigo) == ref.lower()).first()
    if o:
        return o
    return db.query(models.Obra).filter(models.Obra.nombre.ilike(f"%{ref}%")).first()


def _saldo(obra_id: int, db: Session) -> dict:
    rows = db.query(
        models.MovimientoObra.tipo,
        func.coalesce(func.sum(models.MovimientoObra.monto), 0),
    ).filter(models.MovimientoObra.obra_id == obra_id).group_by(models.MovimientoObra.tipo).all()
    ingresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.INGRESO), 0.0)
    egresos = next((float(t) for tp, t in rows if tp == models.TipoMovimiento.EGRESO), 0.0)
    return {"ingresos": ingresos, "egresos": egresos, "saldo": ingresos - egresos}


def is_slash_command(text: str) -> bool:
    return bool(text) and text.strip().startswith("/")


def handle_slash(text: str, user: models.User, db: Session) -> dict:
    """Procesa un slash command. Devuelve {ok, reply, [extra...]}.

    Si el comando crea/modifica datos, también devuelve los IDs / saldos relevantes.
    """
    text = text.strip()
    try:
        parts = shlex.split(text)
    except ValueError:
        parts = text.split()
    if not parts:
        return {"ok": False, "reply": "❓ Comando vacío. Probá /help"}

    cmd = parts[0].lower().lstrip("/")
    args = parts[1:]

    if cmd == "help":
        return {"ok": True, "reply": HELP}
    if cmd == "saldo":
        return _cmd_saldo(args, db)
    if cmd == "cheques":
        return _cmd_cheques(args, db)
    if cmd == "aportes":
        return _cmd_aportes(args, db)
    if cmd == "avance":
        return _cmd_avance(args, user, db)
    if cmd == "gasto":
        return _cmd_gasto(args, user, db)
    if cmd == "stock":
        return _cmd_stock(args, db)
    if cmd == "req":
        return _cmd_req(args, user, db)
    if cmd == "pendientes":
        return _cmd_pendientes(args, db)
    if cmd == "pendientes_ocr":
        return _cmd_pendientes_ocr(db)
    if cmd == "confirmar":
        return _cmd_confirmar_ocr(args, user, db)
    if cmd == "rechazar":
        return _cmd_rechazar_ocr(args, user, db)

    return {
        "ok": False,
        "reply": f"❓ Comando '/{cmd}' desconocido. Probá /help",
    }


def _cmd_saldo(args: list[str], db: Session) -> dict:
    if args:
        obra = _obra_by_ref(args[0], db)
        if not obra:
            return {"ok": False, "reply": f"❌ Obra '{args[0]}' no encontrada."}
        s = _saldo(obra.id, db)
        contrato = float(obra.monto_contrato or 0)
        pct = (s["egresos"] / contrato * 100) if contrato else 0
        return {
            "ok": True,
            "reply": (
                f"💰 {obra.codigo} — {obra.nombre}\n"
                f"Contrato: {fmt_money(contrato)}\n"
                f"Ingresos: {fmt_money(s['ingresos'])}\n"
                f"Egresos:  {fmt_money(s['egresos'])} ({pct:.0f}%)\n"
                f"Saldo:    {fmt_money(s['saldo'])}"
            ),
            "obra_id": obra.id,
            "saldo": s["saldo"],
        }

    # Global
    ingresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.INGRESO
    ).scalar() or 0
    egresos = db.query(func.coalesce(func.sum(models.MovimientoObra.monto), 0)).filter(
        models.MovimientoObra.tipo == models.TipoMovimiento.EGRESO
    ).scalar() or 0
    obras_count = db.query(models.Obra).count()
    return {
        "ok": True,
        "reply": (
            f"💰 Saldo global ({obras_count} obras)\n"
            f"Ingresos: {fmt_money(float(ingresos))}\n"
            f"Egresos:  {fmt_money(float(egresos))}\n"
            f"Saldo:    {fmt_money(float(ingresos) - float(egresos))}"
        ),
        "saldo": float(ingresos) - float(egresos),
    }


def _cmd_cheques(args: list[str], db: Session) -> dict:
    try:
        dias = int(args[0]) if args else 30
    except ValueError:
        return {"ok": False, "reply": f"❌ '/cheques {args[0]}' inválido. El parámetro debe ser un número de días."}
    dias = max(1, min(365, dias))
    today = date.today()
    horizonte = today + timedelta(days=dias)
    cheques = db.query(models.MovimientoObra).filter(
        models.MovimientoObra.medio_pago == models.MedioPago.CHEQUE_PROPIO,
        models.MovimientoObra.fecha_vto_cheque.isnot(None),
        models.MovimientoObra.fecha_vto_cheque >= today,
        models.MovimientoObra.fecha_vto_cheque <= horizonte,
    ).order_by(models.MovimientoObra.fecha_vto_cheque).all()

    if not cheques:
        return {"ok": True, "reply": f"✅ No hay cheques a vencer en los próximos {dias} días."}

    total = sum(float(c.monto) for c in cheques)
    lines = [f"🏦 Cheques a vencer ({dias}d) — {len(cheques)} por {fmt_money(total)}:"]
    for c in cheques[:10]:
        d = (c.fecha_vto_cheque - today).days
        lines.append(f"  • {c.fecha_vto_cheque.isoformat()} ({d}d) · {c.banco} #{c.nro_cheque} · {fmt_money(float(c.monto))}")
    if len(cheques) > 10:
        lines.append(f"  ...y {len(cheques) - 10} más")
    return {"ok": True, "reply": "\n".join(lines), "total": total, "count": len(cheques)}


def _cmd_aportes(args: list[str], db: Session) -> dict:
    aportes = db.query(models.AporteSocio).filter(
        models.AporteSocio.estado_devolucion != models.EstadoDevolucion.DEVUELTO_TOTAL
    ).all()
    if not aportes:
        return {"ok": True, "reply": "✅ No hay aportes de socios pendientes."}

    total_pend = sum(float(a.monto) - float(a.monto_devuelto) for a in aportes)
    lines = [f"🤝 Aportes pendientes — {len(aportes)} por {fmt_money(total_pend)}:"]
    for a in aportes[:8]:
        socio = a.socio.name if a.socio else f"Socio #{a.socio_id}"
        pend = float(a.monto) - float(a.monto_devuelto)
        lines.append(f"  • {socio} · {fmt_money(pend)} · {a.motivo[:40]}")
    if len(aportes) > 8:
        lines.append(f"  ...y {len(aportes) - 8} más")
    return {"ok": True, "reply": "\n".join(lines), "total_pendiente": total_pend}


def _cmd_avance(args: list[str], user: models.User, db: Session) -> dict:
    if len(args) < 2:
        return {"ok": False, "reply": "Uso: /avance <obra> <%>\nEj: /avance IDS 65"}
    obra_ref = args[0]
    try:
        pct = float(args[1].rstrip("%"))
    except ValueError:
        return {"ok": False, "reply": f"❌ '{args[1]}' no es un porcentaje válido."}
    if not (0 <= pct <= 100):
        return {"ok": False, "reply": "❌ El porcentaje debe estar entre 0 y 100."}

    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"ok": False, "reply": f"❌ Obra '{obra_ref}' no encontrada."}

    obra.progreso = pct
    # Crear evento de avance asociado
    ev = models.Evento(
        obra_id=obra.id,
        tipo=models.EventoTipo.avance,
        titulo=f"Avance reportado: {pct:.0f}%",
        descripcion=f"Reportado por {user.name} vía WhatsApp",
        canal=models.CanalCarga.whatsapp,
        usuario_id=user.id,
    )
    db.add(ev)
    user.xp = (user.xp or 0) + 5
    db.commit()
    return {
        "ok": True,
        "reply": (
            f"📈 Avance actualizado: {obra.codigo} → {pct:.0f}%\n"
            f"+5 XP (total: {user.xp})"
        ),
        "obra_id": obra.id,
        "progreso": pct,
        "evento_id": ev.id,
    }


def _cmd_gasto(args: list[str], user: models.User, db: Session) -> dict:
    if len(args) < 3:
        return {"ok": False, "reply": "Uso: /gasto <obra> <monto> <concepto>\nEj: /gasto IDS 5000 nafta"}
    obra_ref = args[0]
    try:
        monto = float(args[1].replace(",", ""))
    except ValueError:
        return {"ok": False, "reply": f"❌ '{args[1]}' no es un monto válido."}
    if monto <= 0:
        return {"ok": False, "reply": "❌ El monto debe ser > 0."}
    concepto = " ".join(args[2:]).strip()
    if not concepto:
        return {"ok": False, "reply": "❌ Falta concepto."}

    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"ok": False, "reply": f"❌ Obra '{obra_ref}' no encontrada."}

    # Crear movimiento EGRESO con categoría GASTO_DIRECTO_OBRA y medio EFECTIVO por default
    mov = models.MovimientoObra(
        obra_id=obra.id,
        fecha=date.today(),
        tipo=models.TipoMovimiento.EGRESO,
        categoria_egreso=models.CategoriaEgreso.GASTO_DIRECTO_OBRA,
        concepto=concepto,
        monto=monto,
        medio_pago=models.MedioPago.EFECTIVO,
        estado=models.EstadoMovimiento.A_REVISAR,  # entra a revisar (vino por WhatsApp)
        canal=models.CanalCarga.whatsapp,
        cargado_por=user.id,
    )
    db.add(mov)
    user.xp = (user.xp or 0) + 5
    db.commit()
    db.refresh(mov)

    s = _saldo(obra.id, db)
    return {
        "ok": True,
        "reply": (
            f"💸 Gasto registrado en {obra.codigo}\n"
            f"{concepto} · {fmt_money(monto)}\n"
            f"Estado: A_REVISAR (cargá la factura cuando puedas)\n"
            f"Saldo obra: {fmt_money(s['saldo'])}\n"
            f"+5 XP (total: {user.xp})"
        ),
        "movimiento_id": mov.id,
        "saldo_obra": s["saldo"],
    }


def _cmd_req(args: list[str], user: models.User, db: Session) -> dict:
    """Sprint 17 — /req <obra> <mensaje libre>

    Anota un requerimiento/imprevisto contra una obra. Queda en estado `abierto`
    hasta que alguien lo marque resuelto desde la web.
    """
    if len(args) < 2:
        return {"ok": False, "reply": "Uso: /req <obra> <mensaje>\nEj: /req IDS falta cemento, mando 5 bolsas"}
    obra_ref = args[0]
    mensaje = " ".join(args[1:]).strip()
    if not mensaje:
        return {"ok": False, "reply": "❌ Falta el mensaje del requerimiento."}

    obra = _obra_by_ref(obra_ref, db)
    if not obra:
        return {"ok": False, "reply": f"❌ Obra '{obra_ref}' no encontrada."}

    r = models.Requerimiento(
        obra_id=obra.id,
        mensaje=mensaje,
        estado=models.RequerimientoEstado.abierto,
        canal=models.CanalCarga.whatsapp,
        created_by_id=user.id,
        is_demo=bool(getattr(user, "is_demo", False)),
    )
    db.add(r); db.commit(); db.refresh(r)
    user.xp = (user.xp or 0) + 3
    db.commit()

    return {
        "ok": True,
        "reply": (
            f"📝 Requerimiento anotado en {obra.codigo}\n"
            f"#{r.id} · {mensaje[:80]}{'…' if len(mensaje) > 80 else ''}\n"
            f"Estado: abierto. Marcalo resuelto cuando se accione.\n"
            f"+3 XP (total: {user.xp})"
        ),
        "requerimiento_id": r.id,
        "obra_id": obra.id,
    }


def _cmd_pendientes(args: list[str], db: Session) -> dict:
    """Sprint 14 — /pendientes [dias]

    Lista los materiales comprado_no_retirado con fecha_retirar dentro de N días
    (default 7). También incluye los pendientes sin fecha agendada.
    """
    from app.stock import pendientes_retiro_proximos

    try:
        dias = int(args[0]) if args else 7
    except ValueError:
        return {"ok": False, "reply": f"❌ '/pendientes {args[0]}' inválido. Debe ser un número de días."}
    dias = max(1, min(180, dias))

    filas = pendientes_retiro_proximos(db, dias=dias, incluir_sin_fecha=True)
    if not filas:
        return {"ok": True, "reply": f"✅ No hay pendientes de retiro en los próximos {dias} días."}

    today = date.today()
    lines = [f"🚚 Pendientes de retiro ({dias}d) — {len(filas)} items:"]
    for f in filas[:15]:
        material = db.query(models.Material).filter(models.Material.id == f.material_id).first()
        proveedor = (
            db.query(models.Proveedor).filter(models.Proveedor.id == f.ubicacion_ref).first()
            if f.ubicacion_ref else None
        )
        nombre_m = material.nombre if material else f"material #{f.material_id}"
        nombre_p = proveedor.nombre if proveedor else "—"
        unidad = material.unidad if material else "u"
        fecha_str = "sin fecha"
        if f.fecha_retirar:
            d = (f.fecha_retirar - today).days
            if d < 0:
                fecha_str = f"⚠️ vencido (-{-d}d)"
            elif d == 0:
                fecha_str = "HOY"
            else:
                fecha_str = f"en {d}d ({f.fecha_retirar.isoformat()})"
        lines.append(f"  • #{f.id} · {float(f.cantidad):.0f} {unidad} {nombre_m}")
        lines.append(f"      {nombre_p} · {fecha_str}")
    if len(filas) > 15:
        lines.append(f"  …y {len(filas) - 15} más")
    return {"ok": True, "reply": "\n".join(lines), "count": len(filas)}


def _cmd_stock(args: list[str], db: Session) -> dict:
    """Sprint 9 — /stock [material]

    Sin args: top de los materiales con desglose.
    Con material (id o nombre): desglose detallado de ese material.
    """
    from app.stock import breakdown_por_material

    if args:
        ref = " ".join(args).strip()
        # buscar por id o nombre
        material_id = int(ref) if ref.isdigit() else None
        if material_id is None:
            m = db.query(models.Material).filter(models.Material.nombre.ilike(f"%{ref}%")).first()
            if not m:
                return {"ok": False, "reply": f"❌ No encontré el material '{ref}'."}
            material_id = m.id
        items = breakdown_por_material(db, material_id=material_id)
        if not items:
            return {"ok": False, "reply": f"❌ Material id={material_id} no existe."}
        it = items[0]
        lines = [f"📦 *{it['nombre']}* ({it['unidad']})"]
        lines.append(f"  Total disponible: {it['stock_total_disponible']:.0f} · pendiente retiro: {it['stock_pendiente_retiro']:.0f}")
        if it["stock_minimo"] and it["stock_total_disponible"] < it["stock_minimo"]:
            lines.append(f"  ⚠️ Bajo mínimo ({it['stock_minimo']:.0f})")
        for u in it["ubicaciones"]:
            if u["cantidad"] > 0:
                lines.append(f"  • {u['ubicacion_nombre']}: {u['cantidad']:.0f}")
        return {"ok": True, "reply": "\n".join(lines)}

    items = breakdown_por_material(db)
    if not items:
        return {"ok": True, "reply": "📦 No hay materiales cargados."}
    lines = [f"📦 Stock — {len(items)} materiales"]
    for it in items[:15]:
        flag = ""
        if it["stock_minimo"] and it["stock_total_disponible"] < it["stock_minimo"]:
            flag = " ⚠️"
        pend_str = f" (+{it['stock_pendiente_retiro']:.0f} pendiente)" if it["stock_pendiente_retiro"] else ""
        lines.append(f"  • {it['nombre']}: {it['stock_total_disponible']:.0f} {it['unidad']}{pend_str}{flag}")
    if len(items) > 15:
        lines.append(f"  ...y {len(items) - 15} más")
    return {"ok": True, "reply": "\n".join(lines)}


# ─── Sprint 18: OCR tickets ──────────────────────────────────────────


def _cmd_pendientes_ocr(db: Session) -> dict:
    tickets = db.query(models.TicketOCR).filter(
        models.TicketOCR.estado == models.TicketOCREstado.pendiente,
    ).order_by(models.TicketOCR.created_at.desc()).limit(15).all()
    if not tickets:
        return {"ok": True, "reply": "✅ No hay tickets de OCR pendientes."}
    import json
    lines = [f"🧾 Tickets OCR pendientes ({len(tickets)}):"]
    for t in tickets:
        try:
            data = json.loads(t.resultado_json)
        except Exception:
            data = {}
        nombre = data.get("proveedor_nombre") or "?"
        total = data.get("total") or 0
        nro = data.get("nro_comprobante") or "—"
        lines.append(f"  • #{t.id} {nro} · {nombre[:30]} · ${total:.0f}")
    lines.append("")
    lines.append("Confirmar: /confirmar <id> <obra>")
    lines.append("Rechazar:  /rechazar <id>")
    return {"ok": True, "reply": "\n".join(lines), "count": len(tickets)}


def _cmd_confirmar_ocr(args: list[str], user: models.User, db: Session) -> dict:
    """`/confirmar <ticket_id> <obra_codigo_o_id>`"""
    if len(args) < 2:
        return {"ok": False, "reply": "Uso: /confirmar <ticket_id> <obra>"}
    try:
        tid = int(args[0])
    except ValueError:
        return {"ok": False, "reply": f"❌ '{args[0]}' no es un id válido"}
    obra = _obra_by_ref(args[1], db)
    if not obra:
        return {"ok": False, "reply": f"❌ Obra '{args[1]}' no encontrada."}

    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    if not t:
        return {"ok": False, "reply": f"❌ Ticket #{tid} no existe."}
    if t.estado != models.TicketOCREstado.pendiente:
        return {"ok": False, "reply": f"❌ Ticket #{tid} ya está {t.estado.value}."}

    # Reusa la lógica del endpoint (POST /confirmar) construyendo el payload mínimo.
    from app.routers.ocr_tickets import confirmar as _confirmar_endpoint
    from app import schemas
    data = schemas.TicketOCRConfirmarIn(obra_id=obra.id)
    try:
        out = _confirmar_endpoint(tid, data, db, user)  # type: ignore
    except Exception as e:
        return {"ok": False, "reply": f"❌ Error al confirmar: {e}"}

    return {
        "ok": True,
        "reply": (
            f"✅ Ticket #{tid} confirmado en {obra.codigo}.\n"
            f"  Comprobante #{out.comprobante_id} · Movimiento #{out.movimiento_obra_id}\n"
            f"+5 XP"
        ),
        "ticket_id": tid,
        "obra_id": obra.id,
    }


def _cmd_rechazar_ocr(args: list[str], user: models.User, db: Session) -> dict:
    if len(args) < 1:
        return {"ok": False, "reply": "Uso: /rechazar <ticket_id>"}
    try:
        tid = int(args[0])
    except ValueError:
        return {"ok": False, "reply": f"❌ '{args[0]}' no es un id válido"}
    t = db.query(models.TicketOCR).filter(models.TicketOCR.id == tid).first()
    if not t:
        return {"ok": False, "reply": f"❌ Ticket #{tid} no existe."}
    if t.estado not in (models.TicketOCREstado.pendiente, models.TicketOCREstado.error):
        return {"ok": False, "reply": f"❌ Ticket #{tid} ya está {t.estado.value}."}
    t.estado = models.TicketOCREstado.rechazado
    db.commit()
    return {"ok": True, "reply": f"🗑 Ticket #{tid} descartado."}
