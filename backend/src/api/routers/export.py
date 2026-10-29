"""
Router para exportación masiva de licitaciones en formatos CSV y Excel (XLSX).
Soporta todos los filtros FTS, rubros IA, montos y rangos de fecha.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import Response

from database import AsyncSessionLocal
from services.search import TenderFilters, build_search_query
from services.exporter import generate_csv_bytes, generate_xlsx_bytes

router = APIRouter(prefix="/api/licitaciones", tags=["Exportación"])


@router.get("/export")
async def export_licitaciones(
    format: str = Query(default="csv", description="Formato de descarga: 'csv' o 'xlsx'"),
    vigentes: Optional[bool] = Query(default=None, description="Filtrar vigentes (True/False/None)"),
    fecha: Optional[str] = Query(default=None, description="'hoy', 'todos' o fecha YYYY-MM-DD"),
    tipo: Optional[str] = Query(default=None, description="Objeto: 'Bienes', 'Servicios', 'Obras' o 'todos'"),
    search: Optional[str] = Query(default=None, description="Búsqueda por texto general"),
    q: Optional[str] = Query(default=None, description="Término FTS"),
    rubro: Optional[str] = Query(default=None, description="Rubro normalizado por IA"),
    monto_min: Optional[float] = Query(default=None, description="Monto mínimo"),
    monto_max: Optional[float] = Query(default=None, description="Monto máximo"),
    fecha_desde: Optional[str] = Query(default=None, description="Fecha desde (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(default=None, description="Fecha hasta (YYYY-MM-DD)"),
    sort: Optional[str] = Query(default="relevance", description="'relevance', 'date', 'value'"),
    limit: int = Query(default=10000, ge=1, le=50000, description="Límite máximo de filas a exportar"),
    offset: int = Query(default=0, ge=0),
):
    """
    Exporta el conjunto filtrado de convocatorias a CSV (UTF-8 con BOM y delimitador ;)
    o a Excel XLSX con estilos profesionales.
    """
    fmt = (format or "csv").strip().lower()
    if fmt not in ["csv", "xlsx"]:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use 'csv' o 'xlsx'.")

    query_text = (q or search or "").strip() or None

    filter_params = TenderFilters(
        q=query_text,
        vigentes=vigentes,
        tipo=tipo,
        rubro=rubro,
        monto_min=monto_min,
        monto_max=monto_max,
        fecha=fecha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        sort=sort or "relevance",
        limit=limit,
        offset=offset,
    )

    async with AsyncSessionLocal() as session:
        query, _ = build_search_query(filter_params)
        result = await session.execute(query)
        rows = result.scalars().all()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "csv":
        content_bytes = generate_csv_bytes(rows)
        media_type = "text/csv; charset=utf-8-sig"
        filename = f"licitaciones_{timestamp}.csv"
    else:
        content_bytes = generate_xlsx_bytes(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"licitaciones_{timestamp}.xlsx"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Length": str(len(content_bytes)),
    }

    return Response(content=content_bytes, media_type=media_type, headers=headers)
