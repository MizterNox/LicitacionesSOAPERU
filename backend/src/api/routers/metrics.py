"""
Router de métricas y analítica agregada para Dashboard (Recharts).
Endpoints:
- GET /api/v1/metrics/monthly: Serie temporal agrupada por mes y (tipo de objeto | rubro IA).
- GET /api/v1/metrics/summary: Resumen ejecutivo (totales, ticket promedio, top rubros, top entidades).
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text, select, func, desc

from database import AsyncSessionLocal
from models.tenders import TenderModel

router = APIRouter(prefix="/api/v1/metrics", tags=["Métricas"])

MESES_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Oct", 11: "Nov", 12: "Dic"
}


def format_mes_label(yyyy_mm: str) -> str:
    """Convierte '2026-08' en 'Ago 2026'."""
    try:
        parts = yyyy_mm.split("-")
        y = parts[0]
        m = int(parts[1])
        return f"{MESES_ES.get(m, str(m))} {y}"
    except Exception:
        return yyyy_mm


@router.get("/monthly")
async def get_monthly_metrics(
    meses: int = Query(default=12, ge=1, le=60, description="Número de meses hacia atrás a consultar"),
    group_by: str = Query(default="tipo", pattern="^(tipo|rubro)$", description="Agrupación secundaria: 'tipo' u 'rubro'")
):
    """
    Retorna métricas mensuales agrupadas para alimentar gráficos temporales (Recharts).
    Cada registro mensual incluye total de convocatorias, monto total y desglose por dimensión.
    """
    columna_grupo = "objeto_contratacion" if group_by == "tipo" else "COALESCE(rubro, 'Otros')"

    sql = text(f"""
        SELECT 
            TO_CHAR(fecha_lanzamiento, 'YYYY-MM') AS mes,
            {columna_grupo} AS grupo,
            COUNT(*) AS total_convocatorias,
            COALESCE(SUM(monto_estimado), 0) AS monto_total
        FROM tenders
        WHERE fecha_lanzamiento IS NOT NULL
          AND fecha_lanzamiento >= (CURRENT_DATE - INTERVAL '{meses} months')
        GROUP BY 1, 2
        ORDER BY 1 ASC, 2 ASC;
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(sql)
        rows = result.fetchall()

        # Si el filtro por fecha relativo a hoy no retornase filas (por fechas de prueba),
        # usamos el rango histórico disponible para garantizar visualización.
        if not rows:
            sql_fallback = text(f"""
                SELECT 
                    TO_CHAR(fecha_lanzamiento, 'YYYY-MM') AS mes,
                    {columna_grupo} AS grupo,
                    COUNT(*) AS total_convocatorias,
                    COALESCE(SUM(monto_estimado), 0) AS monto_total
                FROM tenders
                WHERE fecha_lanzamiento IS NOT NULL
                GROUP BY 1, 2
                ORDER BY 1 ASC, 2 ASC;
            """)
            result = await session.execute(sql_fallback)
            rows = result.fetchall()

    # Consolidar datos por mes con llaves planas para Recharts
    meses_map: Dict[str, Dict[str, Any]] = {}
    grupos_vistos = set()

    for r in rows:
        mes = r[0]
        grupo = r[1] or "Otros"
        count = int(r[2])
        monto = float(r[3])

        grupos_vistos.add(grupo)

        if mes not in meses_map:
            meses_map[mes] = {
                "mes": mes,
                "mes_label": format_mes_label(mes),
                "total": 0,
                "monto": 0.0,
                "desglose": {}
            }

        meses_map[mes]["total"] += count
        meses_map[mes]["monto"] += monto
        meses_map[mes][grupo] = count
        meses_map[mes][f"monto_{grupo}"] = monto
        meses_map[mes]["desglose"][grupo] = {
            "count": count,
            "monto": monto
        }

    # Asegurar que todos los meses tengan llaves numéricas en 0 para grupos faltantes
    lista_ordenada = []
    for mes in sorted(meses_map.keys()):
        item = meses_map[mes]
        for g in grupos_vistos:
            if g not in item:
                item[g] = 0
            if f"monto_{g}" not in item:
                item[f"monto_{g}"] = 0.0
        lista_ordenada.append(item)

    return {
        "group_by": group_by,
        "grupos": sorted(list(grupos_vistos)),
        "data": lista_ordenada
    }


@router.get("/summary")
async def get_metrics_summary():
    """
    Retorna métricas ejecutivas globales:
    - Convocatorias totales y vigentes
    - Presupuesto total analizado y ticket promedio
    - Top rubros identificados por IA
    - Distribución por tipo de objeto
    - Top entidades contratantes
    """
    async with AsyncSessionLocal() as session:
        # 1. Totales globales
        res_totales = await session.execute(text("""
            SELECT 
                COUNT(*) AS total_convocatorias,
                COALESCE(SUM(monto_estimado), 0) AS monto_total,
                COALESCE(AVG(monto_estimado), 0) AS ticket_promedio,
                COUNT(*) FILTER (WHERE estado ILIKE '%Vigente%') AS vigentes
            FROM tenders;
        """))
        totales = res_totales.fetchone()
        total_convocatorias = int(totales[0]) if totales else 0
        monto_total = float(totales[1]) if totales else 0.0
        ticket_promedio = float(totales[2]) if totales else 0.0
        vigentes = int(totales[3]) if totales else 0

        # 2. Distribución por tipo de contratación
        res_tipo = await session.execute(text("""
            SELECT 
                COALESCE(objeto_contratacion, 'Servicios') AS tipo,
                COUNT(*) AS count,
                COALESCE(SUM(monto_estimado), 0) AS monto
            FROM tenders
            GROUP BY 1
            ORDER BY count DESC;
        """))
        tipos_data = []
        for r in res_tipo.fetchall():
            c = int(r[1])
            m = float(r[2])
            pct = round((c / total_convocatorias * 100), 1) if total_convocatorias > 0 else 0
            tipos_data.append({
                "tipo": r[0],
                "count": c,
                "monto": m,
                "porcentaje": pct
            })

        # 3. Top rubros IA
        res_rubros = await session.execute(text("""
            SELECT 
                COALESCE(rubro, 'Otros') AS rubro,
                COUNT(*) AS count,
                COALESCE(SUM(monto_estimado), 0) AS monto
            FROM tenders
            GROUP BY 1
            ORDER BY count DESC
            LIMIT 10;
        """))
        rubros_data = []
        for r in res_rubros.fetchall():
            c = int(r[1])
            m = float(r[2])
            pct = round((c / total_convocatorias * 100), 1) if total_convocatorias > 0 else 0
            rubros_data.append({
                "rubro": r[0],
                "count": c,
                "monto": m,
                "porcentaje": pct
            })

        # 4. Top entidades compradoras (desde raw_payload o entidad normalizada)
        from services.exporter import extract_entidad
        res_entidades_raw = await session.execute(select(TenderModel.raw_payload, TenderModel.monto_estimado))
        entidades_map = {}
        for row in res_entidades_raw.fetchall():
            raw = row[0] if isinstance(row[0], dict) else {}
            entidad_nombre = extract_entidad(raw)
            monto = float(row[1]) if row[1] is not None else 0.0
            if entidad_nombre not in entidades_map:
                entidades_map[entidad_nombre] = {"count": 0, "monto": 0.0}
            entidades_map[entidad_nombre]["count"] += 1
            entidades_map[entidad_nombre]["monto"] += monto

        top_entidades = [
            {"entidad": k, "count": v["count"], "monto": v["monto"]}
            for k, v in sorted(entidades_map.items(), key=lambda x: x[1]["monto"], reverse=True)[:8]
        ]

        return {
            "total_convocatorias": total_convocatorias,
            "monto_total": monto_total,
            "ticket_promedio": ticket_promedio,
            "vigentes": vigentes,
            "distribucion_tipo": tipos_data,
            "top_rubros": rubros_data,
            "top_entidades": top_entidades
        }
