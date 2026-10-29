import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from config import settings
from database import AsyncSessionLocal
from etl.extractor import OCESCExtractor
from etl.transformer import transform_and_filter_releases
from models.tenders import IA_OK, TenderModel
from services.ai_enricher import ai_enricher, compute_text_hash

logger = logging.getLogger(__name__)

# Columnas persistibles (search_vector es generada por PostgreSQL)
_TENDER_COLUMNS = {c.name for c in TenderModel.__table__.columns if c.name != "search_vector"}

AI_COLUMNS = ("descripcion_limpia", "rubro", "rubro_confianza", "palabras_clave", "ia_estado", "ia_hash", "ia_procesado_en")

# Derivados de raw_payload: se pueden refrescar siempre sin pisar datos editoriales
DERIVED_COLUMNS = ("entidad_nombre", "entidad_ruc", "region", "tipo_proceso", "es_menor_cuantia", "cui", "fecha_limite")

# Campos operativos que cambian con prórrogas / fe de erratas / bases integradas
OPERATIONAL_COLUMNS = ("raw_payload", "monto_estimado", "content_hash") + DERIVED_COLUMNS


def _only_columns(values: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in values.items() if k in _TENDER_COLUMNS}


def _pick(values: Dict[str, Any], keys) -> Dict[str, Any]:
    return {k: values[k] for k in keys if k in values}


async def guardar_releases_en_db(records_to_save: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Carga idempotente en PostgreSQL:

    - No existe → INSERT (ON CONFLICT DO NOTHING para tolerar cargas concurrentes).
    - Existe y cambió el estado (ej. Vigente → Adjudicado) → UPDATE de estado, textos, IA y derivados.
      `fecha_lanzamiento` nunca se sobrescribe.
    - Existe con el mismo estado:
        * `content_hash` distinto al guardado → UPDATE solo de campos operativos
          (prórroga de plazo, fe de erratas, nuevas bases). Títulos/IA se preservan.
        * `content_hash` guardado vacío (registros previos a la Fase 4) → backfill de derivados.
        * Sin cambios → IGNORAR.
    Retorna además `nuevos_ocids` para el sistema de alertas.
    """
    stats = {"nuevos": 0, "actualizados": 0, "actualizados_plazo": 0, "backfill": 0, "ignorados": 0}
    nuevos_ocids: List[str] = []

    # Deduplicar por ocid dentro del lote (la API puede repetir releases entre páginas)
    by_ocid: Dict[str, Dict[str, Any]] = {}
    for r in records_to_save or []:
        if r.get("ocid"):
            by_ocid[r["ocid"]] = r

    if not by_ocid:
        logger.info("[LOADER] No hay registros para guardar.")
        return {"total_guardados": 0, **stats, "nuevos_ocids": []}

    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(
                select(TenderModel.ocid, TenderModel.estado, TenderModel.content_hash)
                .where(TenderModel.ocid.in_(list(by_ocid)))
            )
            existing = {row.ocid: row for row in res.all()}

            to_insert = [_only_columns(v) for o, v in by_ocid.items() if o not in existing]
            # Un INSERT multi-fila exige las mismas columnas en cada fila → agrupar por conjunto de claves
            grupos: Dict[frozenset, List[Dict[str, Any]]] = {}
            for row in to_insert:
                grupos.setdefault(frozenset(row), []).append(row)
            for rows in grupos.values():
                ins = (
                    insert(TenderModel)
                    .values(rows)
                    .on_conflict_do_nothing(index_elements=[TenderModel.ocid])
                    .returning(TenderModel.ocid)
                )
                inserted = (await session.execute(ins)).scalars().all()
                nuevos_ocids.extend(inserted)
                stats["nuevos"] += len(inserted)
                stats["ignorados"] += len(rows) - len(inserted)

            for ocid, values in by_ocid.items():
                prev = existing.get(ocid)
                if prev is None:
                    continue

                new_hash = values.get("content_hash")
                if prev.estado != values.get("estado"):
                    set_fields = _pick(values, ("estado", "titulo", "descripcion", "monto_estimado", "raw_payload", "content_hash") + DERIVED_COLUMNS)
                    set_fields.update({k: values[k] for k in AI_COLUMNS if values.get(k) is not None})
                    stats["actualizados"] += 1
                elif new_hash and prev.content_hash and new_hash != prev.content_hash:
                    set_fields = _pick(values, OPERATIONAL_COLUMNS)
                    stats["actualizados_plazo"] += 1
                elif new_hash and not prev.content_hash:
                    set_fields = _pick(values, ("content_hash",) + DERIVED_COLUMNS)
                    stats["backfill"] += 1
                else:
                    stats["ignorados"] += 1
                    continue

                await session.execute(update(TenderModel).where(TenderModel.ocid == ocid).values(**set_fields))

    total = stats["nuevos"] + stats["actualizados"] + stats["actualizados_plazo"]
    logger.info(
        f"[LOADER] {stats['nuevos']} nuevos, {stats['actualizados']} por cambio de estado, "
        f"{stats['actualizados_plazo']} por cambio de plazo/bases, {stats['backfill']} backfill, "
        f"{stats['ignorados']} sin cambios."
    )
    return {"total_guardados": total, **stats, "nuevos_ocids": nuevos_ocids}


async def reutilizar_enriquecimiento_ia(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Copia el enriquecimiento IA ya guardado a los registros cuyo texto no cambió
    (mismo ia_hash con ia_estado OK) y devuelve SOLO los que aún necesitan Gemini.

    Antes, cada corrida del cron volvía a enviar a Gemini licitaciones ya procesadas.
    """
    if not records:
        return []

    for r in records:
        r["ia_hash"] = compute_text_hash(r.get("titulo"), r.get("descripcion"))

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(
                TenderModel.ocid, TenderModel.ia_hash, TenderModel.descripcion_limpia, TenderModel.rubro,
                TenderModel.rubro_confianza, TenderModel.palabras_clave, TenderModel.ia_procesado_en,
            ).where(TenderModel.ocid.in_([r["ocid"] for r in records]), TenderModel.ia_estado == IA_OK)
        )
        ok_map = {row.ocid: row for row in res.all()}

    pendientes = []
    for r in records:
        prev = ok_map.get(r["ocid"])
        if prev is not None and prev.ia_hash == r["ia_hash"]:
            r.update({
                "descripcion_limpia": prev.descripcion_limpia,
                "rubro": prev.rubro,
                "rubro_confianza": prev.rubro_confianza,
                "palabras_clave": prev.palabras_clave,
                "ia_estado": IA_OK,
                "ia_procesado_en": prev.ia_procesado_en,
            })
        else:
            pendientes.append(r)
    return pendientes


class ELTOrchestrator:
    """
    Orquestador ETL: Extracción (OECE) → Transformación/Filtrado → Enriquecimiento IA → Carga.
    """

    def __init__(self, extractor: OCESCExtractor):
        self.extractor = extractor

    async def _extract_all(self, objeto_param: Optional[str], estado: Optional[str], fecha_desde: Optional[str],
                           fecha_hasta: Optional[str], max_pages: int) -> Dict[str, Any]:
        releases: List[Dict[str, Any]] = []
        errores: List[Dict[str, Any]] = []
        paginas_ok = 0
        for page in range(1, max_pages + 1):
            try:
                data = await self.extractor.fetch_tenders(
                    objeto=objeto_param, estado=estado, fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta, page=page,
                )
            except Exception as exc:
                # Se registra explícitamente: antes un fallo cortaba la paginación y se reportaba "success"
                logger.error(f"[EXTRACT] Error en página {page}: {exc}")
                errores.append({"page": page, "error": str(exc)[:500]})
                break
            page_releases = data.get("releases", [])
            if not page_releases:
                break
            releases.extend(page_releases)
            paginas_ok += 1
            if len(page_releases) < 20:  # última página
                break
        return {"releases": releases, "errores": errores, "paginas_ok": paginas_ok}

    async def run_pipeline(
        self,
        objeto: Optional[str] = "Servicios",
        estado: Optional[str] = "Vigente",
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        max_pages: int = 1,
    ) -> Dict[str, Any]:
        logger.info(f"[PIPELINE] objeto={objeto} estado={estado} desde={fecha_desde} hasta={fecha_hasta} páginas={max_pages}")

        objeto_param = None if objeto and objeto.strip().lower() in ("todos", "all") else objeto

        # 1. Extracción (reutiliza el pool HTTP durante toda la paginación)
        async with self.extractor:
            ext = await self._extract_all(objeto_param, estado, fecha_desde, fecha_hasta, max_pages)
        releases = ext["releases"]

        # 2. Transformación
        records = transform_and_filter_releases(releases=releases, estado_filtro=estado, objeto_buscado=objeto)

        # 3. Enriquecimiento IA solo de lo nuevo o modificado
        total_ia_reutilizados = 0
        total_enriquecidos_ia = 0
        if records:
            pendientes = await reutilizar_enriquecimiento_ia(records)
            total_ia_reutilizados = len(records) - len(pendientes)
            if settings.AI_ENABLED and pendientes:
                try:
                    enriched = await ai_enricher.enrich_records(pendientes)
                    total_enriquecidos_ia = sum(1 for r in enriched if r.get("ia_estado") == IA_OK)
                except Exception as e_ai:
                    logger.warning(f"[AI] Error en enriquecimiento: {e_ai}. Se continúa con fallback.")

        # 4. Carga
        save = await guardar_releases_en_db(records)

        status = "partial_success" if ext["errores"] else "success"
        return {
            "status": status,
            "total_extraidos": len(releases),
            "paginas_procesadas": ext["paginas_ok"],
            "errores_extraccion": ext["errores"],
            "total_filtrados_vigentes": len(records),
            "total_enriquecidos_ia": total_enriquecidos_ia,
            "total_ia_reutilizados": total_ia_reutilizados,
            "total_guardados_db": save["total_guardados"],
            "total_nuevos": save["nuevos"],
            "total_actualizados": save["actualizados"],
            "total_actualizados_plazo": save["actualizados_plazo"],
            "total_ignorados": save["ignorados"],
            "nuevos_ocids": save.get("nuevos_ocids", []),
            "config": {"objeto": objeto, "estado": estado, "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta},
        }
