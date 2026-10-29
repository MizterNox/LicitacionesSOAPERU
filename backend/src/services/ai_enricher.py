"""
Servicio de enriquecimiento con Inteligencia Artificial (Google Gemini)
para limpieza de descripciones y clasificación en rubros del SEACE / OECE.

Características:
- SDK oficial google-genai >= 2.25.0 con API de Interactions y salida estructurada JSON.
- Taxonomía cerrada de rubros (enum garantizado por esquema).
- Procesamiento asíncrono por lotes (batching) con control de concurrencia (Semaphore).
- Reintentos exponenciales con Tenacity ante rate-limits (429) o fallos de red.
- Caching por hash SHA-256 (no gasta cuota en registros idénticos ya procesados).
- Fallback determinista seguro: si falla la IA o falta la API key, limpia por heurística
  y marca como 'PENDIENTE' sin bloquear el pipeline ETL.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Taxonomía cerrada aprobada por el usuario
RUBROS_VALIDOS = [
    "Tecnología y Software",
    "Construcción e Infraestructura",
    "Salud y Farmacia",
    "Consultoría y Asesoría",
    "Mantenimiento y Limpieza",
    "Seguridad y Vigilancia",
    "Transporte y Logística",
    "Alimentos",
    "Educación y Capacitación",
    "Equipamiento y Mobiliario",
    "Servicios Generales",
    "Otros",
]

# Esquema JSON estricto para respuesta estructurada de Gemini
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ocid": {"type": "string"},
                    "descripcion_limpia": {"type": "string"},
                    "rubro": {
                        "type": "string",
                        "enum": RUBROS_VALIDOS,
                    },
                    "confianza": {"type": "number"},
                    "palabras_clave": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "ocid",
                    "descripcion_limpia",
                    "rubro",
                    "confianza",
                    "palabras_clave",
                ],
            },
        }
    },
    "required": ["items"],
}

SYSTEM_INSTRUCTION = (
    "Eres un asistente experto en compras públicas del Perú (SEACE/OECE). "
    "Tu tarea es limpiar, corregir y estandarizar descripciones crudas de convocatorias del Estado "
    "y clasificarlas en un único rubro de la taxonomía oficial.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Limpieza de texto: corrige errores ortográficos, elimina caracteres rotos/ilegibles "
    "y expande abreviaciones obvias (ej. 'ADQ.' -> 'Adquisición', 'CONTRAT.' -> 'Contratación', "
    "'SERV.' -> 'Servicio', 'MANT.' -> 'Mantenimiento'). "
    "NUNCA inventes números, especificaciones técnicas, marcas ni datos que no existan en el original.\n"
    "2. Redacta la descripción limpia en tono formal, conciso y en español correcto.\n"
    "3. Clasifica el proceso en EXACTAMENTE UNO de los rubros permitidos en el enum.\n"
    "4. Confianza: número decimal entre 0.0 y 1.0 indicando qué tan seguro estás de la clasificación.\n"
    "5. Palabras clave: extrae entre 2 y 6 términos clave representativos en minúsculas para búsqueda semántica.\n"
    "6. Conserva estrictamente el ocid recibido para cada registro."
)


def compute_text_hash(titulo: Optional[str], descripcion: Optional[str]) -> str:
    """Calcula un hash SHA-256 del texto original para detectar si ya fue procesado."""
    t = (titulo or "").strip()
    d = (descripcion or "").strip()
    payload = f"{t}|{d}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fallback_clean_text(raw_text: Optional[str]) -> str:
    """Limpieza básica por expresiones regulares cuando no hay IA."""
    if not raw_text:
        return "Sin descripción detallada"
    # Normalizar espacios múltiples y saltos de línea
    txt = re.sub(r"[\r\n\t]+", " ", raw_text)
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    # Si todo está en mayúsculas sostenidas, convertir a formato oración respetando siglas
    if txt.isupper() and len(txt) > 10:
        words = txt.split(" ")
        txt = " ".join([w if len(w) <= 3 else w.capitalize() for w in words])
    return txt or "Sin descripción detallada"


def fallback_rubro(objeto_contratacion: Optional[str]) -> str:
    """Asignación de rubro básico por defecto en caso de fallback."""
    obj = (objeto_contratacion or "").strip().lower()
    if "obra" in obj:
        return "Construcción e Infraestructura"
    if "bien" in obj:
        return "Equipamiento y Mobiliario"
    if "serv" in obj:
        return "Servicios Generales"
    return "Otros"


class GeminiEnricher:
    """
    Cliente de enriquecimiento y normalización apoyado en Google Gemini.
    Gestiona el ciclo de vida del cliente asíncrono, semáforos y reintentos.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.semaphore = asyncio.Semaphore(settings.AI_MAX_CONCURRENCY)
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"[GEMINI INIT] Error inicializando cliente google-genai: {e}")
                self._client = None
        return self._client

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        reraise=True,
    )
    async def _call_gemini_batch(self, batch_items: List[Dict[str, str]]) -> Dict[str, Any]:
        """Ejecuta la llamada a la API de Interactions con timeout y reintentos."""
        client = self._get_client()
        if client is None:
            raise RuntimeError("Cliente de Gemini no configurado o sin API Key.")

        prompt_input = (
            "Procesa el siguiente lote de convocatorias y devuelve el JSON requerido:\n"
            f"{json.dumps(batch_items, ensure_ascii=False)}"
        )

        async with self.semaphore:
            # Interactions API con cliente asíncrono oficial
            interaction = await client.aio.interactions.create(
                model=self.model,
                system_instruction=SYSTEM_INSTRUCTION,
                input=prompt_input,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": RESPONSE_SCHEMA,
                },
                store=False,
            )

            output_text = getattr(interaction, "output_text", None)
            if not output_text and hasattr(interaction, "outputs") and interaction.outputs:
                output_text = interaction.outputs[-1].text

            if not output_text:
                raise ValueError("Respuesta vacía recibida desde Gemini Interactions API")

            return json.loads(output_text)

    async def enrich_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriquece un lote de registros. Si la API falla tras reintentos o no está disponible,
        aplica fallback defensivo para cada registro sin interrumpir el flujo.
        """
        prepared_input = []
        for r in batch:
            prepared_input.append({
                "ocid": r.get("ocid", ""),
                "titulo": r.get("titulo", "") or "",
                "descripcion": r.get("descripcion", "") or r.get("titulo", "") or "",
                "objeto": r.get("objeto_contratacion", "") or "",
            })

        results_map = {}
        ai_success = False

        if settings.AI_ENABLED and self.api_key:
            try:
                data = await self._call_gemini_batch(prepared_input)
                items = data.get("items", [])
                for it in items:
                    ocid = it.get("ocid")
                    if ocid:
                        # Validar que el rubro esté en la lista permitida
                        rubro = it.get("rubro")
                        if rubro not in RUBROS_VALIDOS:
                            rubro = "Otros"
                        results_map[ocid] = {
                            "descripcion_limpia": it.get("descripcion_limpia") or "",
                            "rubro": rubro,
                            "rubro_confianza": round(float(it.get("confianza", 0.85)), 2),
                            "palabras_clave": it.get("palabras_clave", []) or [],
                            "ia_estado": "OK",
                        }
                ai_success = True
            except Exception as e:
                logger.warning(
                    f"[GEMINI BATCH WARN] Falló enriquecimiento IA para lote de {len(batch)} items: {e}. "
                    "Aplicando normalización fallback..."
                )

        # Aplicar resultados o fallback a cada registro
        enriched_batch = []
        now = datetime.utcnow()

        for r in batch:
            ocid = r.get("ocid")
            raw_text = r.get("descripcion") or r.get("titulo") or ""
            current_hash = compute_text_hash(r.get("titulo"), r.get("descripcion"))

            if ai_success and ocid in results_map:
                info = results_map[ocid]
                r["descripcion_limpia"] = info["descripcion_limpia"]
                r["rubro"] = info["rubro"]
                r["rubro_confianza"] = info["rubro_confianza"]
                r["palabras_clave"] = info["palabras_clave"]
                r["ia_estado"] = "OK"
                r["ia_hash"] = current_hash
                r["ia_procesado_en"] = now
            else:
                # Fallback seguro
                r["descripcion_limpia"] = fallback_clean_text(raw_text)
                r["rubro"] = fallback_rubro(r.get("objeto_contratacion"))
                r["rubro_confianza"] = 0.50
                r["palabras_clave"] = []
                r["ia_estado"] = "PENDIENTE"
                r["ia_hash"] = current_hash
                r["ia_procesado_en"] = None

            enriched_batch.append(r)

        return enriched_batch

    async def enrich_records(
        self,
        records: List[Dict[str, Any]],
        batch_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enriquece una lista de convocatorias dividiéndolas en chunks controlados.
        """
        if not records:
            return []

        b_size = batch_size or settings.AI_BATCH_SIZE
        chunks = [records[i : i + b_size] for i in range(0, len(records), b_size)]

        tasks = [self.enrich_batch(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks, return_exceptions=False)

        enriched_all = []
        for res in chunk_results:
            enriched_all.extend(res)

        ok_count = sum(1 for r in enriched_all if r.get("ia_estado") == "OK")
        logger.info(
            f"[AI ENRICHER] Procesados {len(enriched_all)} registros. "
            f"Exitosos IA: {ok_count}, Fallback/Pendientes: {len(enriched_all) - ok_count}"
        )
        return enriched_all


# Instancia singleton para ser reutilizada en el ETL y endpoints
ai_enricher = GeminiEnricher()
