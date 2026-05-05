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
from app.agent.tools import TOOLS_SCHEMA, TOOL_HANDLERS


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
Tu trabajo es ayudar al usuario a operar la plataforma: consultar obras, cuadrillas, materiales, proveedores, órdenes, eventos y finanzas.

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
- CHEQUES PROPIOS: se registran en fecha de emisión, pero la salida real ocurre en fecha_vto_cheque.
- DESCALCE FISCAL: cuando una obra tiene egresos con factura > ingresos con factura.

REGLAS:
1. Respondé en español rioplatense, conciso y directo. Sin emojis innecesarios.
2. Cuando el usuario pregunte algo que requiere datos, USÁ las herramientas — no inventes números.
3. Podés encadenar varias herramientas en una sola respuesta si hace falta (ej: saldo_obra + cheques_a_vencer).
4. Si el usuario pide algo de escritura (crear, modificar, borrar, registrar), avisá: "Esto lo voy a poder hacer en el próximo sprint, por ahora solo puedo consultar". NO inventes que lo hiciste.
5. Si una tool devuelve {{"error": ...}}, explicá el problema en lenguaje natural.
6. Cuando muestres montos, usá $ y formato corto ("$12.3M", "$450k").
7. Para listas largas, resumí: top 5 + "y N más" en vez de volcar todo.
8. Los permisos del usuario los chequea cada tool — si tira "Requiere rol admin/finanzas", informá amablemente.

Sprint actual: solo lectura. Próximo sprint: vas a poder registrar movimientos, aportes, gastos."""


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
        db.add(action); db.commit()
        return {"error": f"tool '{name}' no implementada"}
    try:
        result = handler(tool_input, user, db)
        action.tool_output_json = json.dumps(result, default=str)[:8000]
        action.ok = "error" not in result
        if not action.ok:
            action.error = str(result.get("error"))
        db.add(action); db.commit()
        return result
    except Exception as e:
        action.ok = False
        action.error = str(e)[:1000]
        db.add(action); db.commit()
        return {"error": f"falla interna: {e}"}


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
