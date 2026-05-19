"""Sprint 11 — Registra el webhook de Telegram contra una URL pública.

Uso:
    cd backend
    ./.venv/Scripts/python.exe scripts/telegram_set_webhook.py https://api.tu-dominio.com

Esto le dice a Telegram: "cuando llegue un mensaje al bot, llamá a
<URL>/api/telegram/webhook con el header X-Telegram-Bot-Api-Secret-Token=$TELEGRAM_WEBHOOK_SECRET".

Para BORRAR el webhook (volver a polling):
    ./.venv/Scripts/python.exe scripts/telegram_set_webhook.py --delete
"""
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

import httpx

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("tg_set_webhook")

API_BASE = "https://api.telegram.org"


def main():
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    secret = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()

    if not token:
        log.error("Falta TELEGRAM_BOT_TOKEN en .env")
        sys.exit(1)

    args = sys.argv[1:]
    if not args:
        log.error("Uso: telegram_set_webhook.py <URL_PUBLICA>  |  --delete  |  --info")
        sys.exit(1)

    arg = args[0]
    if arg == "--delete":
        r = httpx.post(f"{API_BASE}/bot{token}/deleteWebhook", timeout=15.0)
        log.info(f"deleteWebhook: {r.json()}")
        return

    if arg == "--info":
        r = httpx.get(f"{API_BASE}/bot{token}/getWebhookInfo", timeout=15.0)
        log.info(f"webhook info: {r.json()}")
        return

    base_url = arg.rstrip("/")
    webhook_url = f"{base_url}/api/telegram/webhook"
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": True,
    }
    if secret:
        payload["secret_token"] = secret

    r = httpx.post(f"{API_BASE}/bot{token}/setWebhook", json=payload, timeout=15.0)
    data = r.json()
    if data.get("ok"):
        log.info(f"✅ Webhook registrado: {webhook_url}")
        if secret:
            log.info("✅ secret_token configurado.")
        else:
            log.warning("⚠️  Sin TELEGRAM_WEBHOOK_SECRET en .env — webhook abierto al mundo.")
    else:
        log.error(f"❌ setWebhook falló: {data}")
        sys.exit(1)

    # Info de confirmación
    r2 = httpx.get(f"{API_BASE}/bot{token}/getWebhookInfo", timeout=10.0)
    log.info(f"webhook info: {r2.json().get('result')}")


if __name__ == "__main__":
    main()
