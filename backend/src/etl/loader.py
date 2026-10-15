import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert

from database import AsyncSessionLocal
from models.tenders import TenderModel
from etl.extractor import OCESCExtractor
from etl.transformer import transform_and_filter_releases

logger = logging.getLogger(__name__)

async def guardar_releases_en_db(records_to_save: List[Dict[str, Any]]) -> int:
    """
    Carga los registros transformados en PostgreSQL realizando UPSERT (INSERT ... ON CONFLICT DO UPDATE).
    """
    if not records_to_save:
        print("[LOADER] No hay registros para guardar en base de datos.")
        return 0

    guardados = 0
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for values in records_to_save:
                stmt = insert(TenderModel).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[TenderModel.ocid],
                    set_={
                        "titulo": stmt.excluded.titulo,
                        "descripcion": stmt.excluded.descripcion,
                        "estado": stmt.excluded.estado,
                        "objeto_contratacion": stmt.excluded.objeto_contratacion,
                        "monto_estimado": stmt.excluded.monto_estimado,
                        "moneda": stmt.excluded.moneda,
                        "fecha_lanzamiento": stmt.excluded.fecha_lanzamiento,
                        "raw_payload": stmt.excluded.raw_payload
                    }
                )
                await session.execute(stmt)
                guardados += 1

    print(f"[LOADER] ¡Se persistieron exitosamente {guardados} registros en la base de datos PostgreSQL!")
    return guardados

class ELTOrchestrator:
    """
    Orquestador del pipeline ETL / ELT:
    Coordina la Extracción (OECE API), Transformación/Filtrado (Estado 'Vigente', Objeto)
    y Carga idempotente en PostgreSQL.
    """
    def __init__(self, extractor: OCESCExtractor):
        self.extractor = extractor

    async def run_pipeline(
        self,
        objeto: Optional[str] = "Servicios",
        estado: Optional[str] = "Vigente",
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        max_pages: int = 1
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo completo del pipeline.
        """
        print(f"\n================ INICIANDO PIPELINE ETL ================")
        print(f"Configuración: Objeto={objeto}, Estado={estado}, Desde={fecha_desde}, Hasta={fecha_hasta}, Páginas={max_pages}")

        todos_los_releases = []
        
        # Si objeto es 'Todos', no enviamos categoría a la API para que traiga general
        objeto_param = None if objeto and objeto.strip().lower() in ["todos", "all"] else objeto

        # 1. Fase de Extracción (soporta paginación)
        for page in range(1, max_pages + 1):
            try:
                data = await self.extractor.fetch_tenders(
                    objeto=objeto_param,
                    estado=estado,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    page=page
                )
                page_releases = data.get("releases", [])
                if not page_releases:
                    break
                todos_los_releases.extend(page_releases)
            except Exception as exc:
                print(f"[ERROR] Error al extraer página {page}: {exc}")
                break

        total_extraidos = len(todos_los_releases)
        print(f"[EXTRACT] Total de releases extraídos desde OECE: {total_extraidos}")

        # 2. Fase de Transformación y Filtrado (Filtro 'Vigente' y atributos)
        records_transformados = transform_and_filter_releases(
            releases=todos_los_releases,
            estado_filtro=estado,
            objeto_buscado=objeto
        )
        total_filtrados = len(records_transformados)
        print(f"[TRANSFORM] Releases vigentes filtrados y listos: {total_filtrados} (de {total_extraidos} extraídos)")

        # 3. Fase de Carga (PostgreSQL UPSERT)
        total_guardados = await guardar_releases_en_db(records_transformados)

        resultado = {
            "status": "success",
            "total_extraidos": total_extraidos,
            "total_filtrados_vigentes": total_filtrados,
            "total_guardados_db": total_guardados,
            "config": {
                "objeto": objeto,
                "estado": estado,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            }
        }
        print(f"================ PIPELINE ETL COMPLETADO ================\n")
        return resultado