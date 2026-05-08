"""Magic links firmados para aprobar/cancelar acciones del agente IA sin login.

Genera un JWT con `aud=approve` que permite confirmar o cancelar un
`AgentAction` específico. El link se manda por WhatsApp y abre un endpoint
público (no requiere sesión).

Uso:
    token = make_approval_token(action_id=42, user_id=1, ttl_hours=24)
    url = approval_url(base_url="https://app.rca.com", action_id=42, token=token, confirm=True)
    # send via WhatsApp...
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
APPROVE_AUD = "approve"


def make_approval_token(action_id: int, user_id: int, ttl_hours: int = 24) -> str:
    """Crea un JWT corto que autoriza ejecutar/cancelar el AgentAction `action_id`.

    El token expira en `ttl_hours` horas (default 24). El `user_id` indica quién
    queda registrado como confirmador.
    """
    payload = {
        "aud": APPROVE_AUD,
        "sub": str(action_id),
        "confirmer": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=ttl_hours),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_approval_token(token: str, action_id: int) -> Optional[dict]:
    """Verifica el JWT. Devuelve el payload si es válido y matchea action_id, sino None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=APPROVE_AUD)
    except JWTError:
        return None
    if str(payload.get("sub")) != str(action_id):
        return None
    return payload


def approval_url(base_url: str, action_id: int, token: str, confirm: bool) -> str:
    """Arma la URL pública para abrir desde WhatsApp."""
    base = base_url.rstrip("/")
    return f"{base}/api/approve/{action_id}?token={token}&confirm={'true' if confirm else 'false'}"
