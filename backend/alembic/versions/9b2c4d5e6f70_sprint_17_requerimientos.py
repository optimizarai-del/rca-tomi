"""sprint 17 - requerimientos por obra

Revision ID: 9b2c4d5e6f70
Revises: 8a1b3c2d5e0f
Create Date: 2026-05-20 14:00:00.000000

Tabla `requerimientos`: imprevistos/pedidos sobre una obra reportados por bot o web.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9b2c4d5e6f70'
down_revision: Union[str, None] = '8a1b3c2d5e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REQ_ESTADO = sa.Enum("abierto", "resuelto", name="requerimientoestado")
CANAL = sa.Enum(
    "whatsapp", "web", "automatico", "agente_ia",
    name="canalcarga", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    REQ_ESTADO.create(bind, checkfirst=True)

    op.create_table(
        "requerimientos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("estado", REQ_ESTADO, nullable=False, server_default="abierto"),
        sa.Column("canal", CANAL, nullable=False, server_default="web"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("resuelto_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resuelto_at", sa.DateTime()),
    )
    op.create_index("ix_requerimientos_obra_id", "requerimientos", ["obra_id"])
    op.create_index("ix_requerimientos_estado", "requerimientos", ["estado"])
    op.create_index("ix_requerimientos_is_demo", "requerimientos", ["is_demo"])
    op.create_index("ix_requerimientos_created_at", "requerimientos", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_requerimientos_created_at", table_name="requerimientos")
    op.drop_index("ix_requerimientos_is_demo", table_name="requerimientos")
    op.drop_index("ix_requerimientos_estado", table_name="requerimientos")
    op.drop_index("ix_requerimientos_obra_id", table_name="requerimientos")
    op.drop_table("requerimientos")
    REQ_ESTADO.drop(op.get_bind(), checkfirst=True)
