"""Fase 1: columnas de enriquecimiento IA + Full-Text Search (tsvector + GIN)

- Columnas IA: descripcion_limpia, rubro, rubro_confianza, palabras_clave, ia_estado, ia_hash, ia_procesado_en.
- Extensión `unaccent` + envoltorio IMMUTABLE `f_unaccent()` (requerido para columnas generadas / índices).
- `search_vector`: columna GENERADA STORED con pesos (A=título, B=descripción limpia o cruda, C=rubro).
  PostgreSQL la recalcula sola en cada INSERT/UPDATE → el ETL no necesita mantenerla.
- Índice GIN sobre search_vector, índice por rubro, índice parcial de pendientes IA.

Revision ID: 0002_ai_fts
Revises: 0001_baseline
Create Date: 2026-10-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_ai_fts"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Debe coincidir EXACTAMENTE con models/tenders.py (SEARCH_VECTOR_EXPR)
SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(titulo, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(descripcion_limpia, descripcion, ''))), 'B') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(rubro, ''))), 'C')"
)


def upgrade() -> None:
    # 1. Columnas de enriquecimiento IA
    op.add_column("tenders", sa.Column("descripcion_limpia", sa.Text, nullable=True))
    op.add_column("tenders", sa.Column("rubro", sa.String(80), nullable=True))
    op.add_column("tenders", sa.Column("rubro_confianza", sa.Numeric(3, 2), nullable=True))
    op.add_column("tenders", sa.Column("palabras_clave", postgresql.JSONB, nullable=True))
    op.add_column(
        "tenders",
        sa.Column("ia_estado", sa.String(20), nullable=False, server_default="PENDIENTE"),
    )
    op.add_column("tenders", sa.Column("ia_hash", sa.String(64), nullable=True))
    op.add_column("tenders", sa.Column("ia_procesado_en", sa.DateTime, nullable=True))

    # 2. unaccent + envoltorio IMMUTABLE (unaccent() es STABLE y no puede usarse en columnas generadas)
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $func$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $func$
        """
    )

    # 3. Columna tsvector generada + índice GIN
    op.execute(
        f"ALTER TABLE tenders ADD COLUMN search_vector tsvector "
        f"GENERATED ALWAYS AS ({SEARCH_VECTOR_EXPR}) STORED"
    )
    op.create_index(
        "ix_tenders_search_vector", "tenders", ["search_vector"], postgresql_using="gin"
    )

    # 4. Índices de apoyo
    op.create_index("ix_tenders_rubro", "tenders", ["rubro"])
    op.create_index(
        "ix_tenders_ia_pendientes",
        "tenders",
        ["ia_estado"],
        postgresql_where=sa.text("ia_estado <> 'OK'"),
    )


def downgrade() -> None:
    op.drop_index("ix_tenders_ia_pendientes", table_name="tenders")
    op.drop_index("ix_tenders_rubro", table_name="tenders")
    op.drop_index("ix_tenders_search_vector", table_name="tenders")
    op.drop_column("tenders", "search_vector")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
    # La extensión unaccent se conserva (inofensiva y podría usarse en otros objetos).
    for col in (
        "ia_procesado_en",
        "ia_hash",
        "ia_estado",
        "palabras_clave",
        "rubro_confianza",
        "rubro",
        "descripcion_limpia",
    ):
        op.drop_column("tenders", col)
