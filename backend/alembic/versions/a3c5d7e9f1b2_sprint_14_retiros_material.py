"""sprint 14 - retiros de material (pedido / retirar / retirado + alertas)

Revision ID: a3c5d7e9f1b2
Revises: 9b2c4d5e6f70
Create Date: 2026-05-20 16:00:00.000000

- StockMaterial: fecha_retirar (Date) + retiro_alertado_at (DateTime).
- RetiroMaterial: historico con forma_pago, en_negro, comprobante, obra destino.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c5d7e9f1b2'
down_revision: Union[str, None] = '9b2c4d5e6f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MEDIO_PAGO = sa.Enum(
    "EFECTIVO", "TRANSFERENCIA", "CHEQUE_PROPIO", "CHEQUE_TERCERO", "DEPOSITO_BANCARIO",
    name="mediopago", create_type=False,
)


def upgrade() -> None:
    with op.batch_alter_table("stock_material") as batch_op:
        batch_op.add_column(sa.Column("fecha_retirar", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("retiro_alertado_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_stock_material_fecha_retirar", ["fecha_retirar"])

    op.create_table(
        "retiros_material",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("material_id", sa.Integer(), sa.ForeignKey("materiales.id"), nullable=False),
        sa.Column("proveedor_id", sa.Integer(), sa.ForeignKey("proveedores.id")),
        sa.Column("obra_destino_id", sa.Integer(), sa.ForeignKey("obras.id")),
        sa.Column("cantidad", sa.Float(), nullable=False),
        sa.Column("fecha_retiro", sa.Date(), nullable=False),
        sa.Column("forma_pago", MEDIO_PAGO),
        sa.Column("en_negro", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comprobante_id", sa.Integer(), sa.ForeignKey("comprobantes.id")),
        sa.Column("notas", sa.Text()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_retiros_material_material_id", "retiros_material", ["material_id"])
    op.create_index("ix_retiros_material_fecha_retiro", "retiros_material", ["fecha_retiro"])
    op.create_index("ix_retiros_material_is_demo", "retiros_material", ["is_demo"])


def downgrade() -> None:
    op.drop_index("ix_retiros_material_is_demo", table_name="retiros_material")
    op.drop_index("ix_retiros_material_fecha_retiro", table_name="retiros_material")
    op.drop_index("ix_retiros_material_material_id", table_name="retiros_material")
    op.drop_table("retiros_material")

    with op.batch_alter_table("stock_material") as batch_op:
        batch_op.drop_index("ix_stock_material_fecha_retirar")
        batch_op.drop_column("retiro_alertado_at")
        batch_op.drop_column("fecha_retirar")
