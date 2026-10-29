"""
Script CLI para el backfill (procesamiento retroactivo) de IA en licitaciones históricas.
Permite procesar todos los registros existentes en PostgreSQL que tengan ia_estado != 'OK'.

Uso:
    python -m etl.backfill_ai --limit 150
    python -m etl.backfill_ai --limit 500 --batch-size 15
    python -m etl.backfill_ai --force-all
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime

# Asegurar path de imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from database import AsyncSessionLocal
from models.tenders import TenderModel, IA_OK, IA_PENDIENTE
from services.ai_enricher import ai_enricher, compute_text_hash
from sqlalchemy import select, update, func


async def run_backfill(limit: int = 500, batch_size: int = 15, force_all: bool = False):
    start_time = time.time()
    print("===============================================================")
    print("  INICIANDO BACKFILL DE IA (LIMPIEZA + CLASIFICACIÓN DE RUBROS)")
    print("===============================================================")
    print(f"Límite máximo: {limit} | Tamaño de lote: {batch_size} | Forzar todo: {force_all}")

    async with AsyncSessionLocal() as session:
        # 1. Contar pendientes totales
        stmt_count = select(func.count(TenderModel.ocid))
        if not force_all:
            stmt_count = stmt_count.where(
                (TenderModel.ia_estado != IA_OK) | (TenderModel.ia_estado.is_(None))
            )
        res_count = await session.execute(stmt_count)
        total_pendientes = res_count.scalar() or 0

        print(f"[BACKFILL] Total de registros pendientes en base de datos: {total_pendientes}")
        if total_pendientes == 0:
            print("[BACKFILL] ¡No hay registros pendientes por procesar! Todo está al día.")
            return

        # 2. Obtener lote a procesar
        stmt_fetch = select(TenderModel)
        if not force_all:
            stmt_fetch = stmt_fetch.where(
                (TenderModel.ia_estado != IA_OK) | (TenderModel.ia_estado.is_(None))
            )
        stmt_fetch = stmt_fetch.order_by(TenderModel.fecha_lanzamiento.desc().nullslast()).limit(limit)

        res_fetch = await session.execute(stmt_fetch)
        records = res_fetch.scalars().all()
        to_process_count = len(records)
        print(f"[BACKFILL] Procesando {to_process_count} registros en esta ejecución...\n")

        # Convertir a diccionarios para el enricher
        input_data = []
        for r in records:
            input_data.append({
                "ocid": r.ocid,
                "titulo": r.titulo or "",
                "descripcion": r.descripcion or "",
                "objeto_contratacion": r.objeto_contratacion or "",
            })

    # 3. Procesar en chunks
    total_guardados = 0
    total_fallidos = 0

    for i in range(0, len(input_data), batch_size):
        chunk = input_data[i : i + batch_size]
        chunk_num = (i // batch_size) + 1
        total_chunks = (len(input_data) + batch_size - 1) // batch_size
        print(f"-> Procesando lote {chunk_num}/{total_chunks} ({len(chunk)} registros)...", end="", flush=True)

        enriched_chunk = await ai_enricher.enrich_batch(chunk)

        # 4. Actualizar en PostgreSQL
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for item in enriched_chunk:
                    ocid = item["ocid"]
                    stmt_upd = (
                        update(TenderModel)
                        .where(TenderModel.ocid == ocid)
                        .values(
                            descripcion_limpia=item.get("descripcion_limpia"),
                            rubro=item.get("rubro"),
                            rubro_confianza=item.get("rubro_confianza"),
                            palabras_clave=item.get("palabras_clave"),
                            ia_estado=item.get("ia_estado", IA_OK),
                            ia_hash=item.get("ia_hash"),
                            ia_procesado_en=item.get("ia_procesado_en") or datetime.utcnow(),
                        )
                    )
                    await session.execute(stmt_upd)
                    if item.get("ia_estado") == IA_OK:
                        total_guardados += 1
                    else:
                        total_fallidos += 1

        print(f" ¡Listo! (Guardados IA: {total_guardados}, Fallback/Pendientes: {total_fallidos})")

    elapsed = round(time.time() - start_time, 2)
    print("\n===============================================================")
    print(f"  BACKFILL COMPLETADO EN {elapsed}s")
    print(f"  Total procesados: {to_process_count}")
    print(f"  Enriquecidos exitosos con IA: {total_guardados}")
    print(f"  Pendientes / Fallback: {total_fallidos}")
    print("===============================================================")


def main():
    parser = argparse.ArgumentParser(description="Backfill de IA en convocatorias de PostgreSQL")
    parser.add_argument("--limit", type=int, default=500, help="Límite máximo de registros a procesar")
    parser.add_argument("--batch-size", type=int, default=15, help="Tamaño de lote para la API de Gemini")
    parser.add_argument("--force-all", action="store_true", help="Reprocesar todo ignorando ia_estado previo")
    args = parser.parse_args()

    asyncio.run(run_backfill(limit=args.limit, batch_size=args.batch_size, force_all=args.force_all))


if __name__ == "__main__":
    main()
