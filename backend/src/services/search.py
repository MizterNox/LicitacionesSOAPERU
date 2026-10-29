"""
Servicio centralizado de búsqueda Full-Text Search (FTS) y filtrado de licitaciones.
Utilizado por:
- API endpoint @app.get('/api/licitaciones')
- Exportador CSV / XLSX (Fase 2)
- Métricas y agregaciones (Fase 2)
- Cruce automático de alertas post-ETL (Fase 3)
"""

import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

from sqlalchemy import select, func, desc, asc, or_, and_, text
from models.tenders import TenderModel


class TenderFilters(BaseModel):
    """Esquema de parámetros de búsqueda y filtros para convocatorias."""
    q: Optional[str] = Field(default=None, description="Término de búsqueda FTS o código SEACE")
    vigentes: Optional[bool] = Field(default=None, description="True = solo vigentes, False = finalizados, None = todos")
    tipo: Optional[str] = Field(default=None, description="Objeto de contratación: 'Bienes', 'Servicios', 'Obras', 'todos'")
    rubro: Optional[str] = Field(default=None, description="Rubro normalizado por IA: ej. 'Tecnología y Software'")
    region: Optional[str] = Field(default=None, description="Región geográfica del Perú")
    monto_min: Optional[float] = Field(default=None, description="Monto estimado mínimo en PEN")
    monto_max: Optional[float] = Field(default=None, description="Monto estimado máximo en PEN")
    fecha: Optional[str] = Field(default=None, description="'hoy', 'todos' o fecha YYYY-MM-DD")
    fecha_desde: Optional[str] = Field(default=None, description="Fecha inicio YYYY-MM-DD")
    fecha_hasta: Optional[str] = Field(default=None, description="Fecha fin YYYY-MM-DD")
    plazo: Optional[str] = Field(default=None, description="'48h', '7d', '30d' o 'todas'")
    sort: Optional[str] = Field(default="relevance", description="'relevance', 'date', 'value', 'deadline'")
    limit: Optional[int] = Field(default=100, ge=1, le=50000)
    offset: Optional[int] = Field(default=0, ge=0)


def build_search_query(filters: TenderFilters) -> Tuple[Any, Optional[Any]]:
    """
    Construye la sentencia SQLAlchemy `select(TenderModel)` aplicando los filtros
    y la expresión de ranking FTS (si existe término de búsqueda).
    Retorna (stmt, rank_expr).
    """
    stmt = select(TenderModel)
    rank_expr = None

    # 1. Búsqueda de Texto Completo (Full-Text Search con unaccent y español)
    if filters.q and filters.q.strip():
        q_raw = filters.q.strip()
        # Generar tsquery seguro usando websearch_to_tsquery con f_unaccent
        tsquery = func.websearch_to_tsquery("spanish", func.f_unaccent(q_raw))
        rank_expr = func.ts_rank_cd(TenderModel.search_vector, tsquery)

        # Condición híbrida: Coincidencia FTS sobre search_vector OR coincidencia exacta por código
        is_code_like = bool(re.search(r"[-_/0-9]", q_raw) or len(q_raw) <= 15)
        if is_code_like:
            code_pat = f"%{q_raw}%"
            stmt = stmt.where(
                or_(
                    TenderModel.search_vector.op("@@")(tsquery),
                    TenderModel.ocid.ilike(code_pat),
                    TenderModel.id_proceso.ilike(code_pat),
                    TenderModel.titulo.ilike(code_pat),
                )
            )
        else:
            stmt = stmt.where(TenderModel.search_vector.op("@@")(tsquery))

    # 2. Filtro Vigentes (Estado)
    if filters.vigentes is True:
        stmt = stmt.where(TenderModel.estado.ilike("%Vigente%"))
    elif filters.vigentes is False:
        stmt = stmt.where(~TenderModel.estado.ilike("%Vigente%"))

    # 3. Filtro Tipo de Objeto (Bienes, Servicios, Obras)
    if filters.tipo and filters.tipo.strip().lower() not in ["todos", "all", ""]:
        stmt = stmt.where(TenderModel.objeto_contratacion.ilike(f"%{filters.tipo.strip()}%"))

    # 4. Filtro Rubro (Clasificación IA)
    if filters.rubro and filters.rubro.strip().lower() not in ["todos", "all", ""]:
        stmt = stmt.where(TenderModel.rubro == filters.rubro.strip())

    # 5. Filtro Rango de Montos
    if filters.monto_min is not None:
        stmt = stmt.where(TenderModel.monto_estimado >= filters.monto_min)
    if filters.monto_max is not None:
        stmt = stmt.where(TenderModel.monto_estimado <= filters.monto_max)

    # 6. Filtro Fechas
    today_date = datetime.now().date()
    if filters.fecha:
        f_clean = filters.fecha.strip().lower()
        if f_clean == "hoy":
            stmt = stmt.where(func.date(TenderModel.fecha_lanzamiento) == today_date)
        elif f_clean not in ["todos", "all", ""]:
            try:
                dt_target = datetime.fromisoformat(f_clean).date()
                stmt = stmt.where(func.date(TenderModel.fecha_lanzamiento) == dt_target)
            except ValueError:
                pass

    if filters.fecha_desde and filters.fecha_desde.strip().lower() not in ["null", "none", ""]:
        try:
            d_desde = datetime.fromisoformat(filters.fecha_desde.strip()).date()
            stmt = stmt.where(func.date(TenderModel.fecha_lanzamiento) >= d_desde)
        except ValueError:
            pass

    if filters.fecha_hasta and filters.fecha_hasta.strip().lower() not in ["null", "none", ""]:
        try:
            d_hasta = datetime.fromisoformat(filters.fecha_hasta.strip()).date()
            stmt = stmt.where(func.date(TenderModel.fecha_lanzamiento) <= d_hasta)
        except ValueError:
            pass

    # 7. Ordenamiento
    sort_mode = (filters.sort or "relevance").lower()
    if sort_mode == "relevance" and rank_expr is not None:
        stmt = stmt.order_by(rank_expr.desc(), TenderModel.fecha_lanzamiento.desc().nullslast())
    elif sort_mode == "value":
        stmt = stmt.order_by(TenderModel.monto_estimado.desc().nullslast(), TenderModel.fecha_lanzamiento.desc().nullslast())
    else:  # 'date' u otros
        stmt = stmt.order_by(TenderModel.fecha_lanzamiento.desc().nullslast())

    # 8. Paginación
    if filters.limit:
        stmt = stmt.limit(filters.limit)
    if filters.offset:
        stmt = stmt.offset(filters.offset)

    return stmt, rank_expr


async def get_search_suggestions(session, query_prefix: str, limit: int = 8) -> List[Dict[str, str]]:
    """
    Genera sugerencias rápidas de autocompletado para la barra de búsqueda.
    Combina rubros coincidentes y títulos relevantes mediante coincidencia de prefijo FTS.
    """
    q = (query_prefix or "").strip()
    if not q or len(q) < 2:
        return []

    suggestions = []

    # 1. Sugerir rubros si coinciden con el texto
    from services.ai_enricher import RUBROS_VALIDOS
    q_lower = q.lower()
    for rubro in RUBROS_VALIDOS:
        if q_lower in rubro.lower():
            suggestions.append({
                "tipo": "rubro",
                "texto": rubro,
                "label": f"Rubro: {rubro}"
            })

    # 2. Sugerir títulos de convocatorias existentes en la BD
    try:
        # Búsqueda por prefijo ILIKE y FTS sobre títulos
        stmt_tenders = (
            select(TenderModel.ocid, TenderModel.titulo, TenderModel.rubro)
            .where(
                or_(
                    TenderModel.titulo.ilike(f"%{q}%"),
                    TenderModel.descripcion_limpia.ilike(f"%{q}%"),
                    TenderModel.ocid.ilike(f"%{q}%")
                )
            )
            .order_by(desc(TenderModel.fecha_lanzamiento))
            .limit(limit)
        )
        res = await session.execute(stmt_tenders)
        rows = res.all()

        for r in rows:
            suggestions.append({
                "tipo": "licitacion",
                "ocid": r.ocid,
                "texto": r.titulo or r.ocid,
                "rubro": r.rubro or "General",
                "label": r.titulo or r.ocid
            })
            if len(suggestions) >= limit:
                break
    except Exception as e:
        print(f"[SUGGESTIONS ERROR]: {e}")

    return suggestions[:limit]
