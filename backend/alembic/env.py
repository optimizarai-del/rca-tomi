"""Alembic environment — lee DATABASE_URL del .env (o env var override) y usa el metadata del proyecto.

Para crear una migración nueva después de cambiar models.py:
    alembic revision --autogenerate -m "agrega campo X a obra"

Para aplicar pendientes:
    alembic upgrade head

Para volver una migración:
    alembic downgrade -1

Prioridad de DATABASE_URL: env var del shell > .env del backend > placeholder de alembic.ini.
"""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

# Capturamos PRIMERO la var del shell, antes de que app.database (que hace load_dotenv override=True) la pise
_SHELL_DB_URL = os.getenv("DATABASE_URL")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env", override=False)

from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base  # OJO: este import hace load_dotenv(override=True), por eso preservamos _SHELL_DB_URL arriba
from app import models  # noqa: F401 — fuerza el registro de todas las tablas

config = context.config

# El shell siempre tiene prioridad (útil para CI con DATABASE_URL=postgres://...)
db_url = _SHELL_DB_URL or os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: genera SQL sin conectar a la DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=(url or "").startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: se conecta a la DB y aplica migraciones."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
