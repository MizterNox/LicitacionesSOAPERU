from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, Numeric, Index, Computed, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from database import Base
from datetime import datetime

# Expresión de la columna generada search_vector.
# Debe coincidir EXACTAMENTE con alembic/versions/0004_menor_cuantia.py (NEW_SEARCH_VECTOR_EXPR)
SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(titulo, ''))), 'A') || "
    "setweight(to_tsvector('spanish'::regconfig, f_unaccent(coalesce(entidad_nombre, ''))), 'A') || "
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
    objeto_contratacion = Column(String(100), default="SERVICIOS", server_default="SERVICIOS")  # Servicios, Bienes, Obras
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

    # ---------------- Contrataciones menores (Fase 4) ----------------
    # Derivados del raw_payload promovidos a columnas para filtrar en SQL (ver schemas/ocds_schema.py)
    entidad_nombre = Column(String(300), nullable=True)
    entidad_ruc = Column(String(11), nullable=True)
    region = Column(String(80), nullable=True)
    tipo_proceso = Column(String(10), nullable=True)  # MC | AS | SIE | CP | LP
    es_menor_cuantia = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    cui = Column(String(20), nullable=True)  # Código Único de Inversiones (Obras)
    fecha_limite = Column(DateTime, nullable=True)  # Fin de presentación de ofertas (None si la fuente no lo informa)
    content_hash = Column(String(64), nullable=True)  # Detecta prórrogas / fe de erratas en procesos vigentes

    # ---------------- Clasificación y Scoring SOAPERU S.R.L. ----------------
    relevance_score = Column(Integer, nullable=False, default=0, server_default=text("0"), index=True)
    primary_tag = Column(String(50), nullable=False, default="OTROS", server_default=text("'OTROS'"), index=True)
    matched_tags = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    matched_keywords = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    is_minor_contract = Column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)

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
        Index("ix_tenders_region", "region"),
        Index("ix_tenders_entidad_nombre", "entidad_nombre"),
        Index("ix_tenders_fecha_limite", "fecha_limite"),
        Index("ix_tenders_tipo_proceso", "tipo_proceso"),
        Index("ix_tenders_menor_cuantia", "fecha_lanzamiento", postgresql_where=text("es_menor_cuantia = true")),
        Index("ix_tenders_estado_objeto_fecha", "estado", "objeto_contratacion", text("fecha_lanzamiento DESC")),
        Index("ix_tenders_relevance_score", "relevance_score"),
        Index("ix_tenders_primary_tag", "primary_tag"),
        Index("ix_tenders_is_minor_contract", "is_minor_contract"),
        Index("ix_tenders_objeto_contratacion", "objeto_contratacion"),
        Index("ix_tenders_soaperu_relevance_fecha", "relevance_score", text("fecha_lanzamiento DESC")),
        Index("ix_tenders_soaperu_tag_score", "primary_tag", "relevance_score"),
    )