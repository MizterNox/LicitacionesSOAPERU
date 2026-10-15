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

async def guardar_releases_en_db(records_to_save: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Carga los registros transformados en PostgreSQL con validación de no-sobreescritura (Opción B):
    - Si el registro no existe: INSERT.
    - Si el registro ya existe con el MISMO estado: IGNORAR (DO NOTHING, preservando intacto el registro).
    - Si el registro ya existe pero su estado CAMBIÓ: UPDATE del estado y payload, preservando fecha_lanzamiento y created_at.
    """
    if not records_to_save:
        print("[LOADER] No hay registros para guardar en base de datos.")
        return {"total_guardados": 0, "nuevos": 0, "actualizados": 0, "ignorados": 0}

    nuevos = 0
    actualizados = 0
    ignorados = 0

    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Obtener ocids existentes y sus estados actuales para validación defensiva
            ocids = [r["ocid"] for r in records_to_save if r.get("ocid")]
            existing_map = {}
            if ocids:
                stmt_check = select(TenderModel.ocid, TenderModel.estado).where(TenderModel.ocid.in_(ocids))
                res = await session.execute(stmt_check)
                existing_map = {row.ocid: row.estado for row in res.all()}

            for values in records_to_save:
                ocid = values.get("ocid")
                if not ocid:
                    continue

                if ocid not in existing_map:
                    # Nuevo registro: inserción completa
                    stmt_insert = insert(TenderModel).values(**values)
                    await session.execute(stmt_insert)
                    nuevos += 1
                else:
                    estado_anterior = existing_map[ocid]
                    estado_nuevo = values.get("estado")
                    if estado_anterior != estado_nuevo:
                        # El estado ha cambiado (ej. Vigente -> Adjudicado): actualizar campos permitidos
                        # preservando fecha_lanzamiento y created_at original
                        stmt_update = insert(TenderModel).values(**values).on_conflict_do_update(
                            index_elements=[TenderModel.ocid],
                            set_={
                                "estado": values.get("estado"),
                                "titulo": values.get("titulo"),
                                "descripcion": values.get("descripcion"),
                                "monto_estimado": values.get("monto_estimado"),
                                "raw_payload": values.get("raw_payload")
                            }
                        )
                        await session.execute(stmt_update)
                        actualizados += 1
                    else:
                        # Mismo estado: NO SOBREESCRIBIR, preservar datos previos
                        ignorados += 1

    total_guardados = nuevos + actualizados
    print(f"[LOADER] Resultado: {nuevos} nuevos, {actualizados} actualizados por cambio de estado, {ignorados} ignorados (sin sobreescritura).")
    return {
        "total_guardados": total_guardados,
        "nuevos": nuevos,
        "actualizados": actualizados,
        "ignorados": ignorados
    }

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

        # 3. Fase de Carga (PostgreSQL con validación de no sobreescritura)
        save_stats = await guardar_releases_en_db(records_transformados)

        resultado = {
            "status": "success",
            "total_extraidos": total_extraidos,
            "total_filtrados_vigentes": total_filtrados,
            "total_guardados_db": save_stats["total_guardados"],
            "total_nuevos": save_stats["nuevos"],
            "total_actualizados": save_stats["actualizados"],
            "total_ignorados": save_stats["ignorados"],
            "config": {
                "objeto": objeto,
                "estado": estado,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            }
        }
        print(f"================ PIPELINE ETL COMPLETADO ================\n")
        return resultado