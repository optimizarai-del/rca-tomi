"""sprint 12 - demo scoping dual (is_demo flag en tablas raiz)

Revision ID: 7f8c91a4d2e0
Revises: 6706465fbb3c
Create Date: 2026-05-19 02:00:00.000000

Agrega `is_demo: bool` (default False) a las tablas que el usuario filtra.
Permite un perfil "demo" que solo ve filas marcadas is_demo=True, y la base
"real" queda libre para datos productivos (is_demo=False).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f8c91a4d2e0'
down_revision: Union[str, None] = '6706465fbb3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = [
    "users", "clientes", "obras", "etapas_obra", "movimientos_obra",
    "socios", "aportes_socios", "comprobantes", "notas_obra",
    "frentes", "cuadrillas", "materiales", "proveedores",
    "ordenes_trabajo", "eventos",
]


def upgrade() -> None:
    for t in TABLES:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.add_column(sa.Column(
                'is_demo', sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ))
            batch_op.create_index(f'ix_{t}_is_demo', ['is_demo'], unique=False)


def downgrade() -> None:
    for t in TABLES:
        with op.batch_alter_table(t, schema=None) as batch_op:
            batch_op.drop_index(f'ix_{t}_is_demo')
            batch_op.drop_column('is_demo')
