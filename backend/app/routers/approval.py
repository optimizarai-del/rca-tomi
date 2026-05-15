"""Endpoint público de aprobación con magic link (Sprint 4 · T5).

Se accede desde WhatsApp (link firmado, no requiere login). Confirma o
cancela un `AgentAction` pendiente y devuelve un HTML mínimo con el estado.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app import models
from app.database import get_db
from app.approval import verify_approval_token
from app.agent import orchestrator

router = APIRouter(prefix="/api/approve", tags=["approval"])


def _html_page(title: str, body_html: str, accent: str = "navy") -> str:
    color = {"navy": "#1E2B5E", "olive": "#3D4F1E", "leather": "#6B4C30", "danger": "#C45A4D"}.get(accent, "#1E2B5E")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
         background: #EEEAE3; color: #1E2B5E; margin: 0;
         min-height: 100vh; display: grid; place-items: center; padding: 24px; }}
  .card {{ background: #fff; border-radius: 24px; padding: 40px;
         max-width: 400px; box-shadow: 0 4px 16px rgba(30,43,94,0.08); text-align: center; }}
  .eyebrow {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.18em;
            color: {color}; font-weight: 700; margin-bottom: 8px; }}
  h1 {{ font-size: 28px; margin: 8px 0 16px; letter-spacing: -0.02em; line-height: 1.1; }}
  p {{ color: #666; font-size: 14px; margin: 0 0 8px; line-height: 1.5; }}
  .icon {{ font-size: 48px; margin-bottom: 16px; }}
</style>
</head>
<body>
  <div class="card">
    {body_html}
  </div>
</body>
</html>"""


@router.get("/{action_id}", response_class=HTMLResponse)
def approve(
    action_id: int,
    token: str,
    confirm: bool = True,
    db: Session = Depends(get_db),
):
    """Endpoint público: valida el JWT y confirma/cancela el AgentAction."""
    payload = verify_approval_token(token, action_id)
    if not payload:
        return HTMLResponse(_html_page(
            "Link inválido",
            f'<div class="icon">❌</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Link inválido o expirado.</h1>'
            f'<p>Pedile al admin que vuelva a generar el link de confirmación.</p>',
            accent="danger",
        ), status_code=401)

    user_id = payload.get("confirmer")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return HTMLResponse(_html_page(
            "Usuario no encontrado",
            f'<div class="icon">❌</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Usuario inválido.</h1>',
            accent="danger",
        ), status_code=404)

    action = db.query(models.AgentAction).filter(models.AgentAction.id == action_id).first()
    if not action:
        return HTMLResponse(_html_page(
            "No encontrada",
            f'<div class="icon">❓</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Acción no encontrada.</h1>',
            accent="leather",
        ), status_code=404)

    # Si ya fue resuelta, mostrar estado actual
    if action.status != models.AgentActionStatus.pending:
        return HTMLResponse(_html_page(
            "Ya resuelta",
            f'<div class="icon">ℹ️</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Esta acción ya fue {action.status.value}.</h1>'
            f'<p>Tool: <strong>{action.tool_name}</strong></p>',
            accent="navy",
        ))

    result = orchestrator.confirm_action(action_id, user, confirm, db)

    if confirm and result.get("ok"):
        return HTMLResponse(_html_page(
            "Confirmada",
            f'<div class="icon">✅</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Acción confirmada.</h1>'
            f'<p><strong>{action.tool_name}</strong> ejecutada.</p>'
            f'<p>Ya podés cerrar esta página.</p>',
            accent="olive",
        ))

    if not confirm:
        return HTMLResponse(_html_page(
            "Cancelada",
            f'<div class="icon">🚫</div><div class="eyebrow">Aprobación</div>'
            f'<h1>Acción cancelada.</h1>'
            f'<p>La acción <strong>{action.tool_name}</strong> no se ejecutó.</p>',
            accent="leather",
        ))

    # confirm=true pero la tool falló
    err = result.get("error", "error desconocido") if isinstance(result, dict) else "error"
    return HTMLResponse(_html_page(
        "Falló",
        f'<div class="icon">⚠️</div><div class="eyebrow">Aprobación</div>'
        f'<h1>La acción se confirmó pero falló al ejecutar.</h1>'
        f'<p>{err}</p>',
        accent="leather",
    ), status_code=500)
