"""Contrataciones menores: columnas promovidas desde raw_payload + FTS por entidad

- Columnas: entidad_nombre, entidad_ruc, region, tipo_proceso, es_menor_cuantia, cui,
  fecha_limite, content_hash. Antes se recalculaban en Python leyendo el JSONB en cada request
  (y /metrics/summary cargaba TODOS los payloads en memoria).
- Índices para filtros server-side (región, entidad, plazo, <= 8 UIT, listado por categoría).
- search_vector se regenera para incluir entidad_nombre (peso A).
- Backfill SQL básico; el backfill completo (región, tipo, RUC, CUI) lo hace
  `python -m etl.backfill_metadata`.

Revision ID: 0004_menor_cuantia
Revises: 0003_users_alerts
Create Date: 2026-10-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_menor_cuantia"
down_revision: Union[str, None] = "0003_users_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(titulo, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(descripcion_limpia, descripcion, ''))), 'B') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(rubro, ''))), 'C')"
)

# Debe coincidir EXACTAMENTE con models/tenders.py (SEARCH_VECTOR_EXPR)
NEW_SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(titulo, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(entidad_nombre, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(descripcion_limpia, descripcion, ''))), 'B') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(rubro, ''))), 'C')"
)

TOPE_MENOR_CUANTIA_PEN = 42800


def _replace_search_vector(expr: str) -> None:
    op.drop_index("ix_tenders_search_vector", table_name="tenders")
    op.drop_column("tenders", "search_vector")
    op.execute(f"ALTER TABLE tenders ADD COLUMN search_vector tsvector GENERATED ALWAYS AS ({expr}) STORED")
    op.create_index("ix_tenders_search_vector", "tenders", ["search_vector"], postgresql_using="gin")


def upgrade() -> None:
    op.add_column("tenders", sa.Column("entidad_nombre", sa.String(300), nullable=True))
    op.add_column("tenders", sa.Column("entidad_ruc", sa.String(11), nullable=True))
    op.add_column("tenders", sa.Column("region", sa.String(80), nullable=True))
    op.add_column("tenders", sa.Column("tipo_proceso", sa.String(10), nullable=True))
    op.add_column(
        "tenders",
        sa.Column("es_menor_cuantia", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("tenders", sa.Column("cui", sa.String(20), nullable=True))
    op.add_column("tenders", sa.Column("fecha_limite", sa.DateTime(), nullable=True))
    op.add_column("tenders", sa.Column("content_hash", sa.String(64), nullable=True))

    # Backfill SQL básico (lo que se puede derivar sin lógica Python)
    op.execute(
        """
        UPDATE tenders SET
            entidad_nombre = COALESCE(
                raw_payload->'buyer'->>'name',
                raw_payload->'tender'->'procuringEntity'->>'name'
            ),
            fecha_limite = CASE
                WHEN (raw_payload->'tender'->'tenderPeriod'->>'endDate') IS NOT NULL
                 AND left(raw_payload->'tender'->'tenderPeriod'->>'endDate', 10)
                     > to_char(fecha_lanzamiento, 'YYYY-MM-DD')
                THEN left(raw_payload->'tender'->'tenderPeriod'->>'endDate', 10)::timestamp
                ELSE NULL
            END
        WHERE raw_payload IS NOT NULL
        """
    )
    op.execute(
        f"UPDATE tenders SET es_menor_cuantia = true "
        f"WHERE monto_estimado > 0 AND monto_estimado <= {TOPE_MENOR_CUANTIA_PEN}"
    )

    _replace_search_vector(NEW_SEARCH_VECTOR_EXPR)

    op.create_index("ix_tenders_region", "tenders", ["region"])
    op.create_index("ix_tenders_entidad_nombre", "tenders", ["entidad_nombre"])
    op.create_index("ix_tenders_fecha_limite", "tenders", ["fecha_limite"])
    op.create_index("ix_tenders_tipo_proceso", "tenders", ["tipo_proceso"])
    op.create_index(
        "ix_tenders_menor_cuantia", "tenders", ["fecha_lanzamiento"],
        postgresql_where=sa.text("es_menor_cuantia = true"),
    )
    op.create_index(
        "ix_tenders_estado_objeto_fecha", "tenders",
        ["estado", "objeto_contratacion", sa.text("fecha_lanzamiento DESC")],
    )


def downgrade() -> None:
    for ix in (
        "ix_tenders_estado_objeto_fecha", "ix_tenders_menor_cuantia", "ix_tenders_tipo_proceso",
        "ix_tenders_fecha_limite", "ix_tenders_entidad_nombre", "ix_tenders_region",
    ):
        op.drop_index(ix, table_name="tenders")
    _replace_search_vector(OLD_SEARCH_VECTOR_EXPR)
    for col in (
        "content_hash", "fecha_limite", "cui", "es_menor_cuantia",
        "tipo_proceso", "region", "entidad_ruc", "entidad_nombre",
    ):
        op.drop_column("tenders", col)
