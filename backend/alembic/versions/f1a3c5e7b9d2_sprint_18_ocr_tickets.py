"""sprint 18 - OCR de tickets con Claude Vision (TicketOCR)

Revision ID: f1a3c5e7b9d2
Revises: e8fbc1d2a4f5
Create Date: 2026-05-31 23:00:00.000000

Tabla tickets_ocr: borradores de comprobante generados por Claude Vision
desde fotos enviadas por Telegram, hasta que el usuario confirma con /confirmar.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a3c5e7b9d2'
down_revision: Union[str, None] = 'e8fbc1d2a4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OCR_ESTADO = sa.Enum("pendiente", "confirmado", "rechazado", "error", name="ticketocrestado")


def upgrade() -> None:
    OCR_ESTADO.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tickets_ocr",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("telegram_chat_id", sa.String(60)),
        sa.Column("telegram_message_id", sa.String(60)),
        sa.Column("telegram_file_id", sa.String(200)),
        sa.Column("imagen_url_cached", sa.String(500)),
        sa.Column("resultado_json", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(60)),
        sa.Column("error_msg", sa.Text()),
        sa.Column("estado", OCR_ESTADO, nullable=False, server_default="pendiente"),
        sa.Column("obra_id", sa.Integer(), sa.ForeignKey("obras.id")),
        sa.Column("comprobante_id", sa.Integer(), sa.ForeignKey("comprobantes.id")),
        sa.Column("movimiento_obra_id", sa.Integer(), sa.ForeignKey("movimientos_obra.id")),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime()),
    )
    op.create_index("ix_tickets_ocr_is_demo", "tickets_ocr", ["is_demo"])
    op.create_index("ix_tickets_ocr_telegram_chat_id", "tickets_ocr", ["telegram_chat_id"])
    op.create_index("ix_tickets_ocr_estado", "tickets_ocr", ["estado"])
    op.create_index("ix_tickets_ocr_created_at", "tickets_ocr", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tickets_ocr_created_at", table_name="tickets_ocr")
    op.drop_index("ix_tickets_ocr_estado", table_name="tickets_ocr")
    op.drop_index("ix_tickets_ocr_telegram_chat_id", table_name="tickets_ocr")
    op.drop_index("ix_tickets_ocr_is_demo", table_name="tickets_ocr")
    op.drop_table("tickets_ocr")
    OCR_ESTADO.drop(op.get_bind(), checkfirst=True)
