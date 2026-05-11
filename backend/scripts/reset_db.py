"""Resetea la base de datos: borra TODAS las tablas, las recrea con Alembic, y reseedea.

Uso desde backend/:
    .venv\\Scripts\\python.exe -m scripts.reset_db          (Windows)
    .venv/bin/python -m scripts.reset_db                    (Mac/Linux)

Funciona con SQLite y Postgres (lee DATABASE_URL del .env).

Diferencia vs versiones anteriores: el schema se aplica con Alembic
(`upgrade head`), no con `Base.metadata.create_all`. Si agregás migraciones
nuevas con `alembic revision --autogenerate`, las van a aplicar acá también.
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(override=True)

from app.database import Base, engine
from app import models  # noqa: F401 — carga todas las tablas
from app.seed import run as seed_run


def main():
    url = str(engine.url)
    print(f"[reset] Engine: {url}")
    print("[reset] Borrando TODAS las tablas...")
    Base.metadata.drop_all(bind=engine)
    # También limpiar el tracking de alembic (tabla alembic_version)
    with engine.connect() as conn:
        try:
            conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
            conn.commit()
        except Exception:
            pass

    print("[reset] Aplicando migraciones Alembic (upgrade head)...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True, cwd=ROOT,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "")

    print("[reset] Cargando seed...")
    seed_run()
    print("[reset] OK - Base de datos reseteada.")


if __name__ == "__main__":
    main()
