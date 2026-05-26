"""sprint 24 - planificacion de obra asistida (PlanObraBorrador)

Revision ID: d7f9a1b3c5e6
Revises: c5e7f9a1b3d4
Create Date: 2026-05-21 02:00:00.000000

Tabla planes_obra_borrador: guarda los borradores de plan generados con IA
(etapas, frentes, materiales sugeridos) hasta que el usuario los aplica.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7f9a1b3c5e6'
down_revision: Union[str, None] = 'c5e7f9a1b3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PLAN_ESTADO = sa.Enum("borrador", "aplicado", "descartado", name="planobraestado")


def upgrade() -> None:
    PLAN_ESTADO.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "planes_obra_borrador",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_input", sa.Text(), nullable=False),
        sa.Column("resultado_json", sa.Text(), nullable=False),
        sa.Column("estado", PLAN_ESTADO, nullable=False, server_default="borrador"),
        sa.Column("model_used", sa.String(60)),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("aplicado_at", sa.DateTime()),
    )
    op.create_index("ix_planes_obra_borrador_obra_id", "planes_obra_borrador", ["obra_id"])
    op.create_index("ix_planes_obra_borrador_estado", "planes_obra_borrador", ["estado"])
    op.create_index("ix_planes_obra_borrador_is_demo", "planes_obra_borrador", ["is_demo"])
    op.create_index("ix_planes_obra_borrador_created_at", "planes_obra_borrador", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_planes_obra_borrador_created_at", table_name="planes_obra_borrador")
    op.drop_index("ix_planes_obra_borrador_is_demo", table_name="planes_obra_borrador")
    op.drop_index("ix_planes_obra_borrador_estado", table_name="planes_obra_borrador")
    op.drop_index("ix_planes_obra_borrador_obra_id", table_name="planes_obra_borrador")
    op.drop_table("planes_obra_borrador")
    PLAN_ESTADO.drop(op.get_bind(), checkfirst=True)
