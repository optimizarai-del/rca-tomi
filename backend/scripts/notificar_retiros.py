"""Cron / job nocturno — Sprint 14.

Para cada StockMaterial con fecha_retirar = mañana, manda alerta por Telegram
a los admins que tengan chat vinculado.

Programar en Easy Panel / cron VPS:
    0 8 * * *  cd /app && python -m scripts.notificar_retiros

Idempotente: si ya se mandó la alerta para esa fila/fecha, no la repite.
"""
from __future__ import annotations
import sys
import logging
from app.database import SessionLocal
from app.notificaciones import notificar_retiros_pendientes


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = SessionLocal()
    try:
        resumen = notificar_retiros_pendientes(db, dias_antes=1)
    finally:
        db.close()

    logging.info(
        "Alertas de retiro: filas=%s destinatarios=%s errores=%s",
        resumen["filas_notificadas"], resumen["destinatarios"], resumen["errores"],
    )
    return 0 if not resumen["errores"] else 1


if __name__ == "__main__":
    sys.exit(main())
