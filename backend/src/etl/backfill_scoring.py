"""
Script y servicio de recálculo retroactivo (Backfill) del scoring SOAPERU S.R.L.

Recalcula relevance_score, primary_tag, matched_tags, matched_keywords e is_minor_contract
para todas las licitaciones registradas en la base de datos PostgreSQL.

Uso CLI:
    python -m etl.backfill_scoring [--batch-size 100]
"""

import asyncio
import logging
import sys
from typing import Any, Dict, Optional

from sqlalchemy import select, update

from database import AsyncSessionLocal
from models.tenders import TenderModel
from services.soaperu_scorer import SoaPeruOpportunityScorer

logger = logging.getLogger("backfill_scoring")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def run_backfill_scoring(batch_size: int = 100) -> Dict[str, Any]:
    """
    Recalcula y actualiza en base de datos las columnas de scoring SOAPERU para todos los registros.
    Retorna un diccionario con estadísticas de procesamiento y distribución de tags.
    """
    stats = {
        "total_procesados": 0,
        "con_relevancia_mayor_cero": 0,
        "alta_relevancia_75_mas": 0,
        "media_relevancia_40_74": 0,
        "baja_relevancia_1_39": 0,
        "excluidos": 0,
        "distribucion_tags": {},
    }

    async with AsyncSessionLocal() as session:
        # 1. Obtener todos los OCIDs y datos necesarios
        query = select(
            TenderModel.ocid,
            TenderModel.titulo,
            TenderModel.descripcion,
            TenderModel.objeto_contratacion,
            TenderModel.monto_estimado,
            TenderModel.region,
            TenderModel.entidad_nombre,
            TenderModel.tipo_proceso,
            TenderModel.raw_payload,
        )
        res = await session.execute(query)
        rows = res.all()

        total = len(rows)
        logger.info(f"[BACKFILL SOAPERU] Iniciando recálculo para {total} licitaciones en base de datos...")

        if total == 0:
            return {"status": "success", "total_tenders": 0, **stats}

        # Procesar en lotes para optimizar memoria y transacciones
        for i in range(0, total, batch_size):
            batch = rows[i : i + batch_size]
            for row in batch:
                monto = float(row.monto_estimado) if row.monto_estimado is not None else None
                score_res = SoaPeruOpportunityScorer.score_tender(
                    titulo=row.titulo,
                    descripcion=row.descripcion,
                    objeto_contratacion=row.objeto_contratacion,
                    monto_estimado=monto,
                    region=row.region,
                    entidad_nombre=row.entidad_nombre,
                    tipo_proceso=row.tipo_proceso,
                    raw_payload=row.raw_payload,
                )

                score_val = score_res["relevance_score"]
                tag = score_res["primary_tag"]

                # Registrar estadísticas
                stats["total_procesados"] += 1
                if score_val >= 75:
                    stats["alta_relevancia_75_mas"] += 1
                elif score_val >= 40:
                    stats["media_relevancia_40_74"] += 1
                elif score_val > 0:
                    stats["baja_relevancia_1_39"] += 1
                elif tag == "EXCLUIDO":
                    stats["excluidos"] += 1

                if score_val > 0:
                    stats["con_relevancia_mayor_cero"] += 1

                stats["distribucion_tags"][tag] = stats["distribucion_tags"].get(tag, 0) + 1

                # Actualizar registro
                await session.execute(
                    update(TenderModel)
                    .where(TenderModel.ocid == row.ocid)
                    .values(
                        relevance_score=score_val,
                        primary_tag=tag,
                        matched_tags=score_res["matched_tags"],
                        matched_keywords=score_res["matched_keywords"],
                        is_minor_contract=score_res["is_minor_contract"],
                    )
                )

            await session.commit()
            logger.info(f"[BACKFILL SOAPERU] Progreso: {min(i + batch_size, total)}/{total} licitaciones procesadas.")

    logger.info(f"[BACKFILL SOAPERU] Finalizado con éxito. Estadísticas: {stats}")
    return {"status": "success", "total_tenders": total, **stats}


if __name__ == "__main__":
    b_size = 100
    if len(sys.argv) > 1:
        try:
            b_size = int(sys.argv[1])
        except ValueError:
            pass
    asyncio.run(run_backfill_scoring(batch_size=b_size))
