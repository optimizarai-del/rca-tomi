"""sprint 22 - memoria de cliente (campos extra + tabla cliente_notas)

Revision ID: c5e7f9a1b3d4
Revises: b4d6e8f0a2c1
Create Date: 2026-05-21 00:00:00.000000

- Cliente: +cbu, alias_bancario, condiciones_pago, contacto_secundario,
  preferencias, last_interaction_at.
- cliente_notas: tabla nueva para historial de interacciones del cliente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5e7f9a1b3d4'
down_revision: Union[str, None] = 'b4d6e8f0a2c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("clientes") as batch_op:
        batch_op.add_column(sa.Column("cbu", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("alias_bancario", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("condiciones_pago", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("contacto_secundario", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("preferencias", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_interaction_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_clientes_last_interaction_at", ["last_interaction_at"])

    op.create_table(
        "cliente_notas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("autor_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("importante", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_cliente_notas_cliente_id", "cliente_notas", ["cliente_id"])
    op.create_index("ix_cliente_notas_is_demo", "cliente_notas", ["is_demo"])
    op.create_index("ix_cliente_notas_created_at", "cliente_notas", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_cliente_notas_created_at", table_name="cliente_notas")
    op.drop_index("ix_cliente_notas_is_demo", table_name="cliente_notas")
    op.drop_index("ix_cliente_notas_cliente_id", table_name="cliente_notas")
    op.drop_table("cliente_notas")

    with op.batch_alter_table("clientes") as batch_op:
        batch_op.drop_index("ix_clientes_last_interaction_at")
        batch_op.drop_column("last_interaction_at")
        batch_op.drop_column("preferencias")
        batch_op.drop_column("contacto_secundario")
        batch_op.drop_column("condiciones_pago")
        batch_op.drop_column("alias_bancario")
        batch_op.drop_column("cbu")
