"""Resetea la base de datos: borra TODAS las tablas y vuelve a seedear.

Uso desde backend/:
    .venv\\Scripts\\python.exe -m scripts.reset_db          (Windows)
    .venv/bin/python -m scripts.reset_db                    (Mac/Linux)

Funciona con SQLite y Postgres (lee DATABASE_URL del .env).
"""
import os
import sys
from pathlib import Path

# Permitir correr el script desde cualquier dir
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
    print("[reset] Recreando schema...")
    Base.metadata.create_all(bind=engine)
    print("[reset] Cargando seed...")
    seed_run()
    print("[reset] OK - Base de datos reseteada.")


if __name__ == "__main__":
    main()
