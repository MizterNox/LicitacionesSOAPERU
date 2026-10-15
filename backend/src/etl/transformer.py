import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Mapeo estándar de categorías a texto en español amigable
CATEGORIA_DISPLAY = {
    "services": "Servicios",
    "goods": "Bienes",
    "works": "Obras"
}

def transform_and_filter_releases(
    releases: List[Dict[str, Any]],
    estado_filtro: Optional[str] = "Vigente",
    objeto_buscado: Optional[str] = "Servicios"
) -> List[Dict[str, Any]]:
    """
    Fase de Transformación y Filtrado del ETL:
    1. Extrae los atributos del estándar OCDS al modelo relacional de datos.
    2. Aplica el filtro en memoria del estado 'Vigente' analizando items[0].status,
       items[0].statusDetails y las etiquetas tag del release.
    3. Normaliza categorías, importes y fechas a formato timezone-naive.
    """
    transformed = []

    for release in releases:
        ocid = release.get("ocid")
        if not ocid:
            continue

        tender = release.get("tender", {})
        value = tender.get("value", {})
        items = tender.get("items", [])

        # 1. Extracción del Estado Real (OCDS y SEACE)
        item_status = None
        item_status_details = None
        if items:
            item_status = (items[0].get("status") or "").lower()
            item_status_details = (items[0].get("statusDetails") or "").upper()

        # Determinar si el proceso está Vigente
        es_vigente = (
            item_status == "active"
            or item_status_details in ["CONVOCADO", "VIGENTE"]
            or "tender" in [t.lower() for t in release.get("tag", [])]
        )

        # Estado a persistir
        if es_vigente:
            estado_calculado = "Vigente"
        elif item_status_details:
            estado_calculado = item_status_details.capitalize()
        elif item_status:
            estado_calculado = item_status.capitalize()
        else:
            estado_calculado = "No especificado"

        # Aplicación del Filtro de Estado
        if estado_filtro:
            filtro_norm = estado_filtro.strip().lower()
            if filtro_norm == "vigente" and not es_vigente:
                # Omitir registros que no estén vigentes
                continue
            elif filtro_norm != "vigente" and filtro_norm != estado_calculado.lower():
                continue

        # 2. Extracción de Objeto de Contratación
        api_category = tender.get("mainProcurementCategory", "").lower()
        if objeto_buscado and objeto_buscado.lower() not in ["todos", "all", ""]:
            objeto_final = objeto_buscado
        else:
            objeto_final = CATEGORIA_DISPLAY.get(api_category, api_category.capitalize() or "General")

        # 3. Parseo seguro de fechas: Priorizar datePublished oficial del proceso sobre release.date (marca técnica de exportación)
        fecha_str = tender.get("datePublished") or release.get("date")
        fecha_lanzamiento = None
        if fecha_str:
            try:
                clean_fecha = fecha_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_fecha)
                fecha_lanzamiento = dt.replace(tzinfo=None)
            except (ValueError, TypeError):
                pass

        # 4. Mapeo final al diccionario de la tabla tenders
        monto = value.get("amount")
        transformed.append({
            "ocid": ocid,
            "id_proceso": str(tender.get("id") or release.get("id") or ""),
            "titulo": tender.get("title"),
            "descripcion": tender.get("description"),
            "estado": estado_calculado,
            "objeto_contratacion": objeto_final,
            "monto_estimado": float(monto) if monto is not None else None,
            "moneda": value.get("currency", "PEN"),
            "fecha_lanzamiento": fecha_lanzamiento,
            "raw_payload": release
        })

    return transformed
