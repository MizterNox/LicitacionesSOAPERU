"""Campos de scoring y clasificacion SOAPERU S.R.L. e indices de busqueda

- Columnas: relevance_score, primary_tag, matched_tags, matched_keywords, is_minor_contract.
- Valor por defecto 'SERVICIOS' e indices en objeto_contratacion, relevance_score,
  primary_tag e is_minor_contract.
- Indices compuestos para ordenamiento por relevancia y filtrado rapido por linea de negocio.

Revision ID: 0005_add_soaperu_scoring_fields
Revises: 0004_menor_cuantia
Create Date: 2026-10-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_soaperu_scoring_fields"
down_revision: Union[str, None] = "0004_menor_cuantia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar nuevas columnas
    op.add_column(
        "tenders",
        sa.Column("relevance_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "tenders",
        sa.Column("primary_tag", sa.String(length=50), nullable=False, server_default=sa.text("'OTROS'")),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "matched_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "tenders",
        sa.Column(
            "matched_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "tenders",
        sa.Column("is_minor_contract", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # 2. Configurar valor por defecto para objeto_contratacion ('SERVICIOS') y sincronizar nulos
    op.execute("ALTER TABLE tenders ALTER COLUMN objeto_contratacion SET DEFAULT 'SERVICIOS'")
    op.execute("UPDATE tenders SET objeto_contratacion = 'SERVICIOS' WHERE objeto_contratacion IS NULL OR trim(objeto_contratacion) = ''")
    op.execute("UPDATE tenders SET is_minor_contract = es_menor_cuantia WHERE es_menor_cuantia IS NOT NULL")

    # 3. Crear indices individuales y compuestos para consultas instantaneas
    op.create_index("ix_tenders_relevance_score", "tenders", ["relevance_score"])
    op.create_index("ix_tenders_primary_tag", "tenders", ["primary_tag"])
    op.create_index("ix_tenders_is_minor_contract", "tenders", ["is_minor_contract"])

    # Verificar si ya existe idx_tenders_objeto para no duplicar
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'tenders' AND indexname = 'ix_tenders_objeto_contratacion') THEN
                CREATE INDEX ix_tenders_objeto_contratacion ON tenders (objeto_contratacion);
            END IF;
        END $$;
        """
    )

    op.create_index(
        "ix_tenders_soaperu_relevance_fecha",
        "tenders",
        ["relevance_score", sa.text("fecha_lanzamiento DESC")],
    )
    op.create_index(
        "ix_tenders_soaperu_tag_score",
        "tenders",
        ["primary_tag", "relevance_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_tenders_soaperu_tag_score", table_name="tenders")
    op.drop_index("ix_tenders_soaperu_relevance_fecha", table_name="tenders")
    op.execute("DROP INDEX IF EXISTS ix_tenders_objeto_contratacion")
    op.drop_index("ix_tenders_is_minor_contract", table_name="tenders")
    op.drop_index("ix_tenders_primary_tag", table_name="tenders")
    op.drop_index("ix_tenders_relevance_score", table_name="tenders")

    op.drop_column("tenders", "is_minor_contract")
    op.drop_column("tenders", "matched_keywords")
    op.drop_column("tenders", "matched_tags")
    op.drop_column("tenders", "primary_tag")
    op.drop_column("tenders", "relevance_score")
