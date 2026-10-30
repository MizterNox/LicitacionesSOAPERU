import logging
from typing import Any, Dict, List, Optional

from schemas.ocds_schema import (
    compute_content_hash,
    compute_estado,
    extract_cui,
    extract_entidad_info,
    extract_fecha_limite_real,
    extract_region_info,
    extract_tipo_proceso_real,
    is_menor_cuantia,
    parse_fecha,
)
from services.soaperu_scorer import SoaPeruOpportunityScorer

logger = logging.getLogger(__name__)

# Enum OCDS (mainProcurementCategory) → etiqueta en español
CATEGORIA_DISPLAY = {
    "services": "Servicios",
    "consultingservices": "Servicios",
    "goods": "Bienes",
    "works": "Obras",
}

# Etiqueta en español → enum OCDS canónico (para comparar contra el filtro solicitado)
_OBJETO_A_CATEGORIA = {
    "servicios": "Servicios", "servicio": "Servicios", "services": "Servicios",
    "consultoria": "Servicios", "consultoría": "Servicios",
    "bienes": "Bienes", "bien": "Bienes", "goods": "Bienes",
    "obras": "Obras", "obra": "Obras", "works": "Obras",
}


def _normalizar_objeto(objeto: Optional[str]) -> Optional[str]:
    if not objeto or objeto.strip().lower() in ("todos", "all", ""):
        return None
    return _OBJETO_A_CATEGORIA.get(objeto.strip().lower(), objeto.strip())


def transform_and_filter_releases(
    releases: List[Dict[str, Any]],
    estado_filtro: Optional[str] = "Vigente",
    objeto_buscado: Optional[str] = "Servicios",
) -> List[Dict[str, Any]]:
    """
    Transformación y filtrado del ETL.

    1. Vigencia: se evalúan todos los ítems y `tender.status` (ver `compute_estado`).
    2. Categoría: se respeta SIEMPRE `mainProcurementCategory` del release. Si no coincide con
       `objeto_buscado`, el release se descarta (antes se re-etiquetaba como 'Servicios').
    3. Se agregan derivados para el nicho de contrataciones menores (entidad, región,
       tipo de procedimiento, <= 8 UIT, fecha límite, content_hash). El loader solo persiste
       las claves que existan como columnas en `tenders`.
    """
    objeto_req = _normalizar_objeto(objeto_buscado)
    filtro_estado = (estado_filtro or "").strip().lower()
    transformed: List[Dict[str, Any]] = []
    descartados_categoria = 0

    for release in releases:
        if not isinstance(release, dict):
            continue
        ocid = release.get("ocid")
        if not ocid:
            continue

        tender = release.get("tender") if isinstance(release.get("tender"), dict) else {}
        value = tender.get("value") if isinstance(tender.get("value"), dict) else {}

        # 1. Estado real
        est = compute_estado(release)
        if filtro_estado and filtro_estado not in ("todos", "all"):
            if filtro_estado == "vigente":
                if not est["es_vigente"]:
                    continue
            elif filtro_estado != est["estado"].lower():
                continue

        # 2. Categoría real
        api_cat = str(tender.get("mainProcurementCategory") or "").strip().lower()
        categoria = CATEGORIA_DISPLAY.get(api_cat)
        if categoria is None:
            # La fuente no informa categoría: usamos el filtro solicitado como mejor estimación
            categoria = objeto_req or (api_cat.capitalize() if api_cat else "General")
        elif objeto_req and categoria != objeto_req:
            descartados_categoria += 1
            continue

        # 3. Fechas y montos
        fecha_lanzamiento = parse_fecha(tender.get("datePublished") or release.get("date"))
        monto_raw = value.get("amount")
        try:
            monto = float(monto_raw) if monto_raw is not None else None
        except (TypeError, ValueError):
            monto = None
        if monto is not None and monto < 0:
            monto = None

        titulo = tender.get("title")
        descripcion = tender.get("description")

        # 4. Derivados
        ent = extract_entidad_info(release)
        tipo = extract_tipo_proceso_real(titulo, release, monto)
        fl = extract_fecha_limite_real(release, fecha_lanzamiento)
        region_str = extract_region_info(release, descripcion or "")

        # 5. Clasificación y Scoring de Oportunidad SOAPERU
        scoring = SoaPeruOpportunityScorer.score_tender(
            titulo=titulo,
            descripcion=descripcion,
            objeto_contratacion=categoria,
            monto_estimado=monto,
            region=region_str,
            entidad_nombre=ent["nombre"],
            tipo_proceso=tipo,
            raw_payload=release,
        )

        transformed.append({
            "ocid": ocid,
            "id_proceso": str(tender.get("id") or release.get("id") or ""),
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": est["estado"],
            "objeto_contratacion": categoria,
            "monto_estimado": monto,
            "moneda": value.get("currency") or "PEN",
            "fecha_lanzamiento": fecha_lanzamiento,
            "raw_payload": release,
            # Derivados (columnas promovidas en la migración 0004)
            "entidad_nombre": ent["nombre"],
            "entidad_ruc": ent["ruc"],
            "region": region_str,
            "tipo_proceso": tipo,
            "es_menor_cuantia": is_menor_cuantia(monto, tipo),
            "cui": extract_cui(titulo, descripcion),
            "fecha_limite": parse_fecha(fl["fecha_limite"]),
            "content_hash": compute_content_hash(release, est["estado"]),
            # Clasificación y Scoring SOAPERU (migración 0005)
            "relevance_score": scoring["relevance_score"],
            "primary_tag": scoring["primary_tag"],
            "matched_tags": scoring["matched_tags"],
            "matched_keywords": scoring["matched_keywords"],
            "is_minor_contract": scoring["is_minor_contract"],
        })

    if descartados_categoria:
        logger.info(f"[TRANSFORM] {descartados_categoria} releases descartados por no coincidir con '{objeto_req}'.")
    return transformed
