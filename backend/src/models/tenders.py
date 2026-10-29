from sqlalchemy import Column, String, DateTime, Text, Numeric, Index, Computed, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from database import Base
from datetime import datetime

# Expresión de la columna generada search_vector.
# Debe coincidir EXACTAMENTE con alembic/versions/0002_ai_fts.py
SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(titulo, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(descripcion_limpia, descripcion, ''))), 'B') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(rubro, ''))), 'C')"
)

# Estados del enriquecimiento IA
IA_PENDIENTE = "PENDIENTE"
IA_OK = "OK"
IA_ERROR = "ERROR"


class TenderModel(Base):
    __tablename__ = "tenders"

    ocid = Column(String(100), primary_key=True)
    id_proceso = Column(String(100))
    titulo = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)  # Texto CRUDO original de OECE (nunca se sobrescribe con IA)
    estado = Column(String(50))  # Ej: Vigente
    objeto_contratacion = Column(String(100))  # Bienes, Servicios, Obras
    monto_estimado = Column(Numeric(15, 2), nullable=True)
    moneda = Column(String(10), default="PEN")
    fecha_lanzamiento = Column(DateTime, nullable=True)

    # Columna JSONB crucial para auditoría y almacenar todo el payload OCDS crudo
    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ---------------- Enriquecimiento IA (Fase 1) ----------------
    descripcion_limpia = Column(Text, nullable=True)  # Descripción corregida/estandarizada por Gemini
    rubro = Column(String(80), nullable=True)  # Categoría asignada por IA (taxonomía cerrada)
    rubro_confianza = Column(Numeric(3, 2), nullable=True)  # 0.00 – 1.00
    palabras_clave = Column(JSONB, nullable=True)  # ["laptops", "equipos de cómputo", ...]
    ia_estado = Column(String(20), nullable=False, default=IA_PENDIENTE, server_default=IA_PENDIENTE)
    ia_hash = Column(String(64), nullable=True)  # sha256 del texto crudo → evita reprocesar
    ia_procesado_en = Column(DateTime, nullable=True)

    # ---------------- Full-Text Search ----------------
    # Columna generada por PostgreSQL (solo lectura desde el ORM)
    search_vector = Column(TSVECTOR, Computed(SEARCH_VECTOR_EXPR, persisted=True))

    __table_args__ = (
        Index("idx_tenders_estado", "estado"),
        Index("idx_tenders_fecha", "fecha_lanzamiento"),
        Index("idx_tenders_objeto", "objeto_contratacion"),
        Index("ix_tenders_rubro", "rubro"),
        Index("ix_tenders_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_tenders_ia_pendientes", "ia_estado", postgresql_where=text("ia_estado <> 'OK'")),
    )