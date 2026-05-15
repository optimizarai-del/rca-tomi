"""Loop de tool-use con Claude Sonnet 4.6.

Mantiene historial por usuario en AgentSession y registra cada tool-call
en AgentAction para audit log.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from app import models
from app.agent.tools import TOOLS_SCHEMA, TOOL_HANDLERS, REQUIRES_CONFIRMATION_TOOLS


# Anthropic se importa lazy: si no está instalado o no hay API key, devolvemos error claro.
try:
    from anthropic import Anthropic
    _SDK_OK = True
except ImportError:
    Anthropic = None  # type: ignore
    _SDK_OK = False


MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-5")
MAX_TOOL_ITERATIONS = 8
MAX_HISTORY_MESSAGES = 30


def _system_prompt(user: models.User) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"""Sos el "Operario IA" del centro de mando de RCA., una constructora.
Tu trabajo es ayudar al usuario a operar la plataforma: consultar Y modificar obras, cuadrillas, materiales, proveedores, órdenes, eventos y finanzas.

DATOS DEL USUARIO ACTUAL:
- Nombre: {user.name} {user.last_name or ""}
- Email: {user.email}
- Rol: {user.role.value}
- ID interno: {user.id}
- Fecha de hoy: {today}

CONTEXTO DEL MODELO (Sprint A+B):
- Cada OBRA tiene un cliente, un régimen fiscal y un tipo_facturacion (TOTAL_BLANCO, TOTAL_NEGRO, MIXTA).
- Cada obra se divide en ETAPAS con monto contractual (anticipo, etapa 1, final).
- TODOS los movimientos de dinero (ingresos y egresos) están en una sola tabla "movimientos_obra".
  El SALDO = ingresos - egresos. El campo "estado" (CONFIRMADO/A_REVISAR) NO afecta el saldo.
- APORTES de socios = préstamos internos con obligación de devolución (NO ingresos libres).
  Al crear un aporte se genera automáticamente un movimiento INGRESO espejo (R2).
- CHEQUES PROPIOS: se registran en fecha de emisión, pero la salida real ocurre en fecha_vto_cheque (R3).
- DESCALCE FISCAL: cuando una obra tiene egresos con factura > ingresos con factura (R4).
- ETAPA pasada a COBRADA con aportes pendientes deja una nota automática (R5).

TOOLS DE LECTURA (no piden confirmación):
dashboard_hud, listar_obras, obtener_obra, listar_clientes, listar_etapas,
listar_movimientos, saldo_obra, flujo_caja_obra, aportes_pendientes,
cheques_a_vencer, descalce_fiscal, alertas_stock_bajo, listar_proveedores,
listar_cuadrillas, eventos_recientes, listar_usuarios.

TOOLS DE ESCRITURA (Sprint 2 — TODAS requieren confirmación humana):
- Financiero: registrar_movimiento, registrar_aporte_socio, registrar_devolucion_aporte, cargar_comprobante.
- Estructura: crear_cliente, crear_obra, crear_etapa, cambiar_estado_etapa.
- Capa lúdica: crear_orden, cerrar_orden, reportar_evento.
- Mensajería: enviar_whatsapp (stub hasta Sprint 4).

CICLO DE CONFIRMACIÓN — IMPORTANTE:
Cuando llamás a una tool de escritura, NO se ejecuta inmediatamente: el sistema
te devuelve {{"requires_confirmation": true, "action_id": N, "preview": {{...}}}}.
La acción queda pendiente y la UI le muestra al usuario los botones [Confirmar] [Cancelar].

Cuando recibas ese resultado:
1. NO digas que la acción se hizo — todavía no se hizo.
2. Resumile al usuario en lenguaje natural QUÉ vas a hacer (los datos clave del preview).
3. Pedile que confirme con el botón. Por ejemplo: "Voy a registrar un egreso de $75.000
   en IDS por flete. Apretá Confirmar abajo y lo cargo."
4. Si una tool devuelve un {{"error": ...}}, explicá el problema y sugerí cómo corregirlo.

REGLAS GENERALES:
1. Respondé en español rioplatense, conciso y directo. Sin emojis innecesarios.
2. Para preguntas de datos, USÁ las herramientas — no inventes números.
3. Podés encadenar varias tools de lectura en una sola respuesta.
4. NUNCA invoques varias tools de escritura en paralelo: una a la vez, esperando confirmación.
5. Cuando muestres montos, usá $ y formato corto ("$12.3M", "$450k").
6. Para listas largas, resumí: top 5 + "y N más" en vez de volcar todo.
7. Los permisos los chequea cada tool — si tira "Requiere rol admin/finanzas", explicale al usuario."""


def _truncate_history(messages: list[dict]) -> list[dict]:
    """Mantiene los últimos N mensajes. Cuida de no cortar a la mitad de un par tool_use/tool_result."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    cut = messages[-MAX_HISTORY_MESSAGES:]
    # si el primero del cut es un tool_result huérfano, descartalo
    while cut and isinstance(cut[0].get("content"), list) and \
          any(b.get("type") == "tool_result" for b in cut[0]["content"]):
        cut = cut[1:]
    return cut


def _block_to_dict(block: Any) -> dict:
    """Convierte un bloque del SDK Anthropic a dict serializable."""
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if isinstance(block, dict):
        return block
    return {"type": "text", "text": str(block)}


def _execute_tool(name: str, tool_input: dict, user: models.User, session_id: int, db: Session) -> dict:
    """Ejecuta una tool del agente con audit log.

    Si la tool está en REQUIRES_CONFIRMATION_TOOLS, NO la ejecuta:
    persiste un AgentAction con status=pending y devuelve un payload
    {requires_confirmation, action_id, preview} para que Claude le diga
    al usuario qué se va a hacer y la UI muestre los botones.

    La ejecución real ocurre cuando el usuario clickea Confirmar
    (POST /api/agent/confirm/{action_id} → confirm_action()).
    """
    handler = TOOL_HANDLERS.get(name)
    action = models.AgentAction(
        user_id=user.id,
        session_id=session_id,
        tool_name=name,
        tool_input_json=json.dumps(tool_input, default=str)[:4000],
        canal=models.CanalCarga.web,
    )
    if not handler:
        action.ok = False
        action.error = "tool no registrada"
        action.status = models.AgentActionStatus.executed
        db.add(action); db.commit()
        return {"error": f"tool '{name}' no implementada"}

    # Interceptar tools sensibles → quedan pending hasta confirmación humana
    if name in REQUIRES_CONFIRMATION_TOOLS:
        action.status = models.AgentActionStatus.pending
        action.ok = None  # se resuelve al confirmar/cancelar
        db.add(action); db.commit(); db.refresh(action)
        return {
            "requires_confirmation": True,
            "action_id": action.id,
            "tool_name": name,
            "preview": tool_input,
            "message": (
                f"Acción '{name}' pendiente de confirmación humana. "
                f"Decile al usuario qué vas a hacer y esperá que confirme en la UI."
            ),
        }

    try:
        result = handler(tool_input, user, db)
        action.tool_output_json = json.dumps(result, default=str)[:8000]
        action.ok = "error" not in result
        action.status = models.AgentActionStatus.executed
        if not action.ok:
            action.error = str(result.get("error"))
        db.add(action); db.commit()
        return result
    except Exception as e:
        action.ok = False
        action.error = str(e)[:1000]
        action.status = models.AgentActionStatus.executed
        db.add(action); db.commit()
        return {"error": f"falla interna: {e}"}


def confirm_action(action_id: int, user: models.User, confirm: bool, db: Session) -> dict:
    """Confirma o cancela un AgentAction pendiente.

    - confirm=True → re-ejecuta el handler con el input guardado, marca confirmed,
      devuelve {ok, result, action_id}.
    - confirm=False → marca cancelled y devuelve {ok: true, cancelled: true, action_id}.

    Errores: action no existe, no pertenece al user, o ya no está pending → 404/400.
    """
    action = db.query(models.AgentAction).filter(models.AgentAction.id == action_id).first()
    if not action:
        return {"error": "Acción no encontrada", "code": 404}
    if action.user_id != user.id:
        return {"error": "Esta acción no te pertenece", "code": 403}
    if action.status != models.AgentActionStatus.pending:
        return {
            "error": f"La acción ya está en estado '{action.status.value}', no se puede modificar",
            "code": 400,
        }

    if not confirm:
        action.status = models.AgentActionStatus.cancelled
        action.confirmed_by = user.id
        action.confirmed_at = datetime.utcnow()
        action.ok = False
        db.commit()
        return {
            "ok": True,
            "cancelled": True,
            "action_id": action.id,
            "tool_name": action.tool_name,
        }

    handler = TOOL_HANDLERS.get(action.tool_name)
    if not handler:
        action.status = models.AgentActionStatus.confirmed
        action.confirmed_by = user.id
        action.confirmed_at = datetime.utcnow()
        action.ok = False
        action.error = "tool ya no está registrada"
        db.commit()
        return {"error": f"tool '{action.tool_name}' no implementada", "code": 500}

    try:
        tool_input = json.loads(action.tool_input_json or "{}")
    except json.JSONDecodeError:
        tool_input = {}

    try:
        result = handler(tool_input, user, db)
        action.tool_output_json = json.dumps(result, default=str)[:8000]
        action.ok = "error" not in result
        action.status = models.AgentActionStatus.confirmed
        action.confirmed_by = user.id
        action.confirmed_at = datetime.utcnow()
        if not action.ok:
            action.error = str(result.get("error"))
        db.commit()
        return {
            "ok": action.ok,
            "result": result,
            "action_id": action.id,
            "tool_name": action.tool_name,
        }
    except Exception as e:
        action.ok = False
        action.error = str(e)[:1000]
        action.status = models.AgentActionStatus.confirmed  # se intentó ejecutar
        action.confirmed_by = user.id
        action.confirmed_at = datetime.utcnow()
        db.commit()
        return {"error": f"falla interna: {e}", "code": 500}


def chat(user: models.User, user_message: str, db: Session) -> dict:
    """Punto de entrada del agente. Devuelve {reply, tools_used, session_id}."""
    if not _SDK_OK:
        return {
            "reply": "El agente no está disponible: falta instalar la librería 'anthropic' en el backend.",
            "tools_used": [],
            "session_id": None,
        }

    api_key = os.getenv("ANTHROPIC_API_KEY") or ""
    if not api_key.strip():
        from dotenv import load_dotenv as _ld
        from pathlib import Path
        # Buscar .env en backend/ (un nivel arriba de app/)
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        _ld(dotenv_path=env_path, override=True)
        api_key = os.getenv("ANTHROPIC_API_KEY") or ""
    if not api_key.strip():
        return {
            "reply": f"El agente no está configurado: falta ANTHROPIC_API_KEY en backend/.env. (cwd={os.getcwd()}, env_len={len(os.getenv('ANTHROPIC_API_KEY','') or '')})",
            "tools_used": [],
            "session_id": None,
        }

    # Sesión persistente por usuario
    session = db.query(models.AgentSession).filter(
        models.AgentSession.user_id == user.id
    ).first()
    if not session:
        session = models.AgentSession(user_id=user.id, messages_json="[]")
        db.add(session); db.commit(); db.refresh(session)

    try:
        messages = json.loads(session.messages_json or "[]")
    except json.JSONDecodeError:
        messages = []

    messages.append({"role": "user", "content": user_message})

    client = Anthropic(api_key=api_key)
    tools_used: list[str] = []
    pending_actions: list[dict] = []
    final_text = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=_system_prompt(user),
            tools=TOOLS_SCHEMA,
            messages=messages,
        )

        # Guardar el turno del asistente como dict serializable
        assistant_blocks = [_block_to_dict(b) for b in response.content]
        messages.append({"role": "assistant", "content": assistant_blocks})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    tools_used.append(block.name)
                    result = _execute_tool(block.name, block.input or {}, user, session.id, db)
                    if result.get("requires_confirmation"):
                        pending_actions.append({
                            "action_id": result["action_id"],
                            "tool_name": result["tool_name"],
                            "preview": result["preview"],
                        })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str, ensure_ascii=False),
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Fin del turno
        for block in response.content:
            if getattr(block, "type", None) == "text":
                final_text += block.text
        break
    else:
        final_text = final_text or "(El agente alcanzó el límite de pasos sin terminar. Probá reformular la pregunta.)"

    # Persistir historial truncado
    session.messages_json = json.dumps(_truncate_history(messages), default=str, ensure_ascii=False)
    session.last_message_at = datetime.utcnow()
    db.commit()

    return {
        "reply": final_text or "(sin respuesta)",
        "tools_used": tools_used,
        "pending_actions": pending_actions,
        "session_id": session.id,
    }


def reset_session(user: models.User, db: Session) -> None:
    session = db.query(models.AgentSession).filter(
        models.AgentSession.user_id == user.id
    ).first()
    if session:
        session.messages_json = "[]"
        session.last_message_at = datetime.utcnow()
        db.commit()
