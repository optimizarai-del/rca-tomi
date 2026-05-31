"""sprint 21 - contabilidad blanco/negro por obra

Revision ID: b4d6e8f0a2c1
Revises: a3c5d7e9f1b2
Create Date: 2026-05-20 23:00:00.000000

Extiende movimientos_obra con campos para diferenciar caja blanca/negra,
estado de cobro/pago, fecha de efectivizacion e impuestos basicos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4d6e8f0a2c1'
down_revision: Union[str, None] = 'a3c5d7e9f1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEGALIDAD = sa.Enum("blanco", "negro", name="legalidadmovimiento")
COBRO_ESTADO = sa.Enum("pendiente", "cobrado", "pagado", name="cobropagoestado")


def upgrade() -> None:
    bind = op.get_bind()
    LEGALIDAD.create(bind, checkfirst=True)
    COBRO_ESTADO.create(bind, checkfirst=True)

    with op.batch_alter_table("movimientos_obra") as batch_op:
        batch_op.add_column(sa.Column(
            "legalidad", LEGALIDAD, nullable=False, server_default="blanco",
        ))
        batch_op.add_column(sa.Column(
            "cobro_pago_estado", COBRO_ESTADO, nullable=False, server_default="pendiente",
        ))
        batch_op.add_column(sa.Column("fecha_cobro_pago", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("iva_pct", sa.Numeric(5, 4), nullable=True))
        batch_op.add_column(sa.Column("iibb_pct", sa.Numeric(5, 4), nullable=True))
        batch_op.add_column(sa.Column(
            "gastos_banco", sa.Numeric(15, 2), nullable=False, server_default="0",
        ))
        batch_op.create_index("ix_movimientos_obra_legalidad", ["legalidad"])
        batch_op.create_index("ix_movimientos_obra_cobro_pago_estado", ["cobro_pago_estado"])
        batch_op.create_index("ix_movimientos_obra_fecha_cobro_pago", ["fecha_cobro_pago"])


def downgrade() -> None:
    with op.batch_alter_table("movimientos_obra") as batch_op:
        batch_op.drop_index("ix_movimientos_obra_fecha_cobro_pago")
        batch_op.drop_index("ix_movimientos_obra_cobro_pago_estado")
        batch_op.drop_index("ix_movimientos_obra_legalidad")
        batch_op.drop_column("gastos_banco")
        batch_op.drop_column("iibb_pct")
        batch_op.drop_column("iva_pct")
        batch_op.drop_column("fecha_cobro_pago")
        batch_op.drop_column("cobro_pago_estado")
        batch_op.drop_column("legalidad")
    COBRO_ESTADO.drop(op.get_bind(), checkfirst=True)
    LEGALIDAD.drop(op.get_bind(), checkfirst=True)
