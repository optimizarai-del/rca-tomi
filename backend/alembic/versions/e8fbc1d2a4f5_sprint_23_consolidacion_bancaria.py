"""sprint 23 - consolidacion bancaria (extractos + movimientos_bancarios)

Revision ID: e8fbc1d2a4f5
Revises: d7f9a1b3c5e6
Create Date: 2026-05-26 23:00:00.000000

- extractos: agrupador de movimientos bancarios importados.
- movimientos_bancarios: cada linea del extracto + match con movimiento_obra.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e8fbc1d2a4f5'
down_revision: Union[str, None] = 'd7f9a1b3c5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extractos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("banco", sa.String(100), nullable=False),
        sa.Column("cuenta", sa.String(60)),
        sa.Column("periodo_desde", sa.Date()),
        sa.Column("periodo_hasta", sa.Date()),
        sa.Column("archivo_nombre", sa.String(200)),
        sa.Column("total_debe", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_haber", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total_movs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extractos_is_demo", "extractos", ["is_demo"])
    op.create_index("ix_extractos_created_at", "extractos", ["created_at"])

    op.create_table(
        "movimientos_bancarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("extracto_id", sa.Integer(), sa.ForeignKey("extractos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("debito", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("credito", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("saldo", sa.Numeric(15, 2)),
        sa.Column("hash_dedupe", sa.String(64)),
        sa.Column("movimiento_obra_id", sa.Integer(), sa.ForeignKey("movimientos_obra.id")),
        sa.Column("conciliado_at", sa.DateTime()),
        sa.Column("conciliado_by_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_movimientos_bancarios_is_demo", "movimientos_bancarios", ["is_demo"])
    op.create_index("ix_movimientos_bancarios_extracto_id", "movimientos_bancarios", ["extracto_id"])
    op.create_index("ix_movimientos_bancarios_fecha", "movimientos_bancarios", ["fecha"])
    op.create_index("ix_movimientos_bancarios_hash_dedupe", "movimientos_bancarios", ["hash_dedupe"])
    op.create_index("ix_movimientos_bancarios_movimiento_obra_id", "movimientos_bancarios", ["movimiento_obra_id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_bancarios_movimiento_obra_id", table_name="movimientos_bancarios")
    op.drop_index("ix_movimientos_bancarios_hash_dedupe", table_name="movimientos_bancarios")
    op.drop_index("ix_movimientos_bancarios_fecha", table_name="movimientos_bancarios")
    op.drop_index("ix_movimientos_bancarios_extracto_id", table_name="movimientos_bancarios")
    op.drop_index("ix_movimientos_bancarios_is_demo", table_name="movimientos_bancarios")
    op.drop_table("movimientos_bancarios")

    op.drop_index("ix_extractos_created_at", table_name="extractos")
    op.drop_index("ix_extractos_is_demo", table_name="extractos")
    op.drop_table("extractos")
