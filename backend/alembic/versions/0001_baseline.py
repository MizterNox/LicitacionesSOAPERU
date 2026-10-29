"""baseline: esquema existente (tenders, cron_executions, app_settings)

Refleja el esquema que ya existe en producción/local antes de introducir Alembic.
- En una BD EXISTENTE no se ejecuta: se marca con `alembic stamp 0001_baseline`.
- En una BD NUEVA crea las tablas desde cero.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenders",
        sa.Column("ocid", sa.String(100), primary_key=True),
        sa.Column("id_proceso", sa.String(100)),
        sa.Column("titulo", sa.Text),
        sa.Column("descripcion", sa.Text),
        sa.Column("estado", sa.String(50)),
        sa.Column("objeto_contratacion", sa.String(100)),
        sa.Column("monto_estimado", sa.Numeric(15, 2)),
        sa.Column("moneda", sa.String(10), server_default="PEN"),
        sa.Column("fecha_lanzamiento", sa.DateTime),
        sa.Column("raw_payload", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_tenders_estado", "tenders", ["estado"])
    op.create_index("idx_tenders_fecha", "tenders", ["fecha_lanzamiento"])
    op.create_index("idx_tenders_objeto", "tenders", ["objeto_contratacion"])

    op.create_table(
        "cron_executions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("iniciado_en", sa.DateTime, nullable=False),
        sa.Column("finalizado_en", sa.DateTime),
        sa.Column("tipo_ejecucion", sa.String(50)),
        sa.Column("estado", sa.String(20)),
        sa.Column("objetos_procesados", sa.JSON),
        sa.Column("total_extraidos", sa.Integer),
        sa.Column("total_guardados", sa.Integer),
        sa.Column("total_ignorados", sa.Integer),
        sa.Column("detalles", sa.JSON),
        sa.Column("error", sa.Text),
    )
    op.create_index("ix_cron_executions_id", "cron_executions", ["id"])
    op.create_index("ix_cron_executions_estado", "cron_executions", ["estado"])
    op.create_index("ix_cron_executions_iniciado_en", "cron_executions", ["iniciado_en"])

    op.create_table(
        "app_settings",
        sa.Column("clave", sa.String(50), primary_key=True),
        sa.Column("valor", sa.JSON, nullable=False),
        sa.Column("actualizado_en", sa.DateTime),
    )
    op.create_index("ix_app_settings_clave", "app_settings", ["clave"])


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("cron_executions")
    op.drop_table("tenders")
