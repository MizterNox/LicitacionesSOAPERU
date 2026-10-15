import json
import logging
import httpx
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Mapeo de categorías en español al enum estándar del API OCDS OECE: ['goods', 'works', 'services']
CATEGORIA_MAP = {
    "servicios": "services",
    "servicio": "services",
    "bienes": "goods",
    "bien": "goods",
    "obras": "works",
    "obra": "works",
    "consultoria": "services",
    "consultoría": "services"
}

class OCESCExtractor:
    def __init__(self, base_url: str = "https://contratacionesabiertas.oece.gob.pe/api/v1/releases"):
        """
        Extractor para la API de Contrataciones Abiertas de Perú (OECE/OSCE).
        Normaliza la URL asegurando que apunte al endpoint '/api/v1/releases'.
        """
        clean_url = base_url.rstrip("/")
        if not clean_url.endswith("/releases"):
            if clean_url.endswith("/api"):
                clean_url = f"{clean_url}/v1/releases"
            elif clean_url.endswith("/api/v1"):
                clean_url = f"{clean_url}/releases"
            else:
                clean_url = f"{clean_url}/api/v1/releases"
        self.base_url = clean_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True
    )
    async def fetch_tenders(
        self,
        objeto: Optional[str] = None,
        estado: Optional[str] = "Vigente",
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Extrae releases de la API OECE aplicando los parámetros oficiales de consulta.

        :param objeto: 'Servicios', 'Bienes', 'Obras' o equivalentes ('services', 'goods', 'works').
        :param estado: Estado de referencia ('Vigente', etc.). Nota: La API oficial de releases
                       no filtra directamente por status en query params; este valor se conserva
                       para trazabilidad y filtrado en etapas de carga (loader).
        :param fecha_desde: Formato YYYY-MM-DD (mapeado a 'startDate').
        :param fecha_hasta: Formato YYYY-MM-DD (mapeado a 'endDate').
        :param page: Número de página para paginación (default 1, lote de 20 por página).
        :return: Diccionario con la respuesta JSON del endpoint OCDS.
        """
        params: Dict[str, Any] = {
            "page": page,
            "order": "desc"
        }

        # 1. Filtro por objeto / categoría (OECE espera 'goods', 'works' o 'services')
        if objeto and objeto.strip().lower() not in ["todos", "all", ""]:
            cat_normalizada = CATEGORIA_MAP.get(objeto.strip().lower(), objeto.strip().lower())
            if cat_normalizada in ["goods", "works", "services"]:
                params["mainProcurementCategory"] = cat_normalizada
            else:
                params["mainProcurementCategory"] = objeto

        # 2. Filtro por rango de fechas (startDate / endDate en estándar OECE)
        if fecha_desde:
            params["startDate"] = fecha_desde
        if fecha_hasta:
            params["endDate"] = fecha_hasta

        print(f"\n[INFO] Consultando API OECE: {self.base_url}")
        print(f"[INFO] Parámetros aplicados: {params}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            
            status_code = response.status_code
            content_type = response.headers.get("content-type", "")

            # Inspección HTTP detallada
            print(f"[HTTP] Código de Estado: {status_code}")
            print(f"[HTTP] Content-Type: {content_type}")
            print(f"[HTTP] Vista previa respuesta (200 caracteres):\n{response.text[:200]}...")

            # Validar código de respuesta HTTP (4xx / 5xx)
            response.raise_for_status()

            # Verificación defensiva de Content-Type
            if "application/json" not in content_type:
                snippet = response.text[:300].strip()
                raise ValueError(
                    f"La API respondió con código {status_code} pero no entregó JSON "
                    f"(Content-Type: '{content_type}'). "
                    f"Posible fallback a HTML del Single Page Application por URL incorrecta. "
                    f"Respuesta recibida:\n{snippet}"
                )

            # Decodificación segura de JSON
            try:
                data = response.json()
            except json.JSONDecodeError as decode_err:
                raise ValueError(
                    f"Error crítico al decodificar JSON de la API ({decode_err}). "
                    f"Longitud de contenido: {len(response.content)} bytes. "
                    f"Contenido recibido:\n{response.text[:500]}"
                ) from decode_err

            releases_count = len(data.get("releases", []))
            print(f"[SUCCESS] JSON parseado correctamente. Se obtuvieron {releases_count} releases.")
            return data