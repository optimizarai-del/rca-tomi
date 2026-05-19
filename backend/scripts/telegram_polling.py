"""Sprint 11 — Polling local del bot de Telegram (alternativa al webhook).

En producción se usa webhook (Telegram llama a tu URL). En desarrollo,
si no tenés URL pública, este script hace getUpdates en loop.

Uso:
    cd backend
    ./.venv/Scripts/python.exe scripts/telegram_polling.py

Requiere TELEGRAM_BOT_TOKEN en backend/.env.

Para que el script y el webhook NO compitan, deshabilita primero cualquier
webhook activo: el script llama a `deleteWebhook` al arrancar.
"""
from __future__ import annotations
import os
import sys
import time
import logging
import signal
from pathlib import Path

# Asegurar que importamos app.* desde backend/
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

# Cargar .env ANTES de importar app
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

import httpx
from app.database import SessionLocal
from app.routers.telegram import _handle_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("tg_polling")

API_BASE = "https://api.telegram.org"
POLL_TIMEOUT = 25  # long-poll: Telegram retiene la conexión hasta 25s si no hay update

_running = True


def _on_signal(signum, frame):
    global _running
    log.info(f"señal {signum} recibida, terminando...")
    _running = False


def main():
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        log.error("Falta TELEGRAM_BOT_TOKEN en backend/.env")
        sys.exit(1)

    signal.signal(signal.SIGINT, _on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _on_signal)

    # Asegurar que no hay webhook activo (no se puede polling + webhook a la vez).
    try:
        httpx.post(f"{API_BASE}/bot{token}/deleteWebhook", timeout=10.0)
        log.info("webhook anterior limpiado (si existía)")
    except Exception as e:
        log.warning(f"deleteWebhook falló (sigo igual): {e}")

    # Verificar bot
    r = httpx.get(f"{API_BASE}/bot{token}/getMe", timeout=10.0)
    if not r.json().get("ok"):
        log.error(f"getMe falló: {r.text}")
        sys.exit(1)
    me = r.json()["result"]
    log.info(f"✅ Bot @{me.get('username')} ({me.get('first_name')}) listo. Esperando mensajes...")

    last_update_id = 0
    while _running:
        try:
            r = httpx.get(
                f"{API_BASE}/bot{token}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": POLL_TIMEOUT},
                timeout=POLL_TIMEOUT + 10,
            )
            data = r.json()
            if not data.get("ok"):
                log.error(f"getUpdates error: {data}")
                time.sleep(3)
                continue
            for update in data.get("result", []):
                last_update_id = max(last_update_id, update.get("update_id", 0))
                try:
                    db = SessionLocal()
                    result = _handle_update(update, db)
                    db.close()
                    log.info(f"update_id={update.get('update_id')} → {result}")
                except Exception as e:
                    log.exception(f"error procesando update: {e}")
        except httpx.ReadTimeout:
            continue  # esperado en long-poll
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception(f"loop error: {e}")
            time.sleep(3)

    log.info("polling terminado.")


if __name__ == "__main__":
    main()
