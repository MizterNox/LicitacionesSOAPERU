"""Fase 3: Tablas de usuarios, filtros guardados y bitácora de alertas

- `users`: usuarios autenticados con Argon2, roles (user/admin), estado activo.
- `saved_filters`: criterios de búsqueda guardados en JSONB, alertas activas y frecuencia.
- `alert_log`: registro de deduplicación con restricción UNIQUE(saved_filter_id, ocid).

Revision ID: 0003_users_alerts
Revises: 0002_ai_fts
Create Date: 2026-10-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_users_alerts"
down_revision: Union[str, None] = "0002_ai_fts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla de usuarios
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("rol", sa.String(length=20), server_default="user", nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # 2. Tabla de filtros guardados
    op.create_table(
        "saved_filters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("filtros", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("alertas_activas", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("frecuencia", sa.String(length=20), server_default="inmediata", nullable=False),
        sa.Column("creado_en", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_filters_id", "saved_filters", ["id"])
    op.create_index("ix_saved_filters_user_id", "saved_filters", ["user_id"])

    # 3. Tabla de registro de alertas enviadas (deduplicación)
    op.create_table(
        "alert_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("saved_filter_id", sa.Integer(), nullable=False),
        sa.Column("ocid", sa.String(length=100), nullable=False),
        sa.Column("enviado_en", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["saved_filter_id"], ["saved_filters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ocid"], ["tenders.ocid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("saved_filter_id", "ocid", name="uq_alert_log_filter_ocid"),
    )
    op.create_index("ix_alert_log_id", "alert_log", ["id"])
    op.create_index("ix_alert_log_user_id", "alert_log", ["user_id"])
    op.create_index("ix_alert_log_saved_filter_id", "alert_log", ["saved_filter_id"])
    op.create_index("ix_alert_log_ocid", "alert_log", ["ocid"])


def downgrade() -> None:
    op.drop_table("alert_log")
    op.drop_table("saved_filters")
    op.drop_table("users")
