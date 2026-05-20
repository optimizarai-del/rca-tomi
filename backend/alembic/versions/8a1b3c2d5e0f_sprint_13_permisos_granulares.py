"""sprint 13 - permisos granulares (secciones + obras visibles por usuario)

Revision ID: 8a1b3c2d5e0f
Revises: 7f8c91a4d2e0
Create Date: 2026-05-20 12:00:00.000000

Agrega dos tablas:
- permisos_usuario: blacklist por seccion (si no hay fila, la seccion es visible).
- permisos_usuario_obra: whitelist de obras (si no hay filas, ve todas).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8a1b3c2d5e0f'
down_revision: Union[str, None] = '7f8c91a4d2e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inlining UniqueConstraint en create_table porque ALTER de constraints
    # no esta soportado en SQLite (usado en dev).
    op.create_table(
        "permisos_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seccion", sa.String(40), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "seccion", name="uq_permisos_usuario_user_seccion"),
    )
    op.create_index("ix_permisos_usuario_user_id", "permisos_usuario", ["user_id"])
    op.create_index("ix_permisos_usuario_seccion", "permisos_usuario", ["seccion"])

    op.create_table(
        "permisos_usuario_obra",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "obra_id", name="uq_permisos_usuario_obra_user_obra"),
    )
    op.create_index("ix_permisos_usuario_obra_user_id", "permisos_usuario_obra", ["user_id"])
    op.create_index("ix_permisos_usuario_obra_obra_id", "permisos_usuario_obra", ["obra_id"])


def downgrade() -> None:
    op.drop_index("ix_permisos_usuario_obra_obra_id", table_name="permisos_usuario_obra")
    op.drop_index("ix_permisos_usuario_obra_user_id", table_name="permisos_usuario_obra")
    op.drop_table("permisos_usuario_obra")

    op.drop_index("ix_permisos_usuario_seccion", table_name="permisos_usuario")
    op.drop_index("ix_permisos_usuario_user_id", table_name="permisos_usuario")
    op.drop_table("permisos_usuario")
