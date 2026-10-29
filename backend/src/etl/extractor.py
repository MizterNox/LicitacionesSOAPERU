import json
import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Categorías en español → enum OCDS del OECE ('goods', 'works', 'services')
CATEGORIA_MAP = {
    "servicios": "services",
    "servicio": "services",
    "consultoria": "services",
    "consultoría": "services",
    "consultingservices": "services",
    "bienes": "goods",
    "bien": "goods",
    "obras": "works",
    "obra": "works",
}

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "LicitLens-ETL/1.3 (+OCDS client)",
}


def _is_transient(exc: BaseException) -> bool:
    """Reintentar solo errores transitorios: red, timeout, 429 y 5xx. Un 4xx no mejora reintentando."""
    if isinstance(exc, (httpx.NetworkError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


class OCESCExtractor:
    """
    Extractor para la API de Contrataciones Abiertas de Perú (OECE/OSCE).

    Puede usarse como context manager para reutilizar el pool de conexiones durante
    una paginación completa:

        async with OCESCExtractor(url) as ex:
            await ex.fetch_tenders(page=1)
            await ex.fetch_tenders(page=2)

    Si se usa sin context manager, cada llamada abre un cliente temporal (compatibilidad).
    """

    def __init__(self, base_url: str = "https://contratacionesabiertas.oece.gob.pe/api/v1/releases",
                 timeout: float = 30.0):
        clean_url = base_url.rstrip("/")
        if not clean_url.endswith("/releases"):
            if clean_url.endswith("/api"):
                clean_url = f"{clean_url}/v1/releases"
            elif clean_url.endswith("/api/v1"):
                clean_url = f"{clean_url}/releases"
            else:
                clean_url = f"{clean_url}/api/v1/releases"
        self.base_url = clean_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OCESCExtractor":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers=DEFAULT_HEADERS,
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def build_params(objeto: Optional[str], fecha_desde: Optional[str],
                     fecha_hasta: Optional[str], page: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "order": "desc"}
        if objeto and objeto.strip().lower() not in ("todos", "all", ""):
            key = objeto.strip().lower()
            params["mainProcurementCategory"] = CATEGORIA_MAP.get(key, key)
        if fecha_desde:
            params["startDate"] = fecha_desde
        if fecha_hasta:
            params["endDate"] = fecha_hasta
        return params

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )
    async def fetch_tenders(
        self,
        objeto: Optional[str] = None,
        estado: Optional[str] = "Vigente",
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Extrae una página de releases (20 por página).

        `estado` se conserva por compatibilidad: la API no filtra por estado; el filtrado
        de vigencia se hace en el transformador.
        """
        params = self.build_params(objeto, fecha_desde, fecha_hasta, page)
        logger.info(f"[EXTRACT] GET {self.base_url} params={params}")

        if self._client is not None:
            response = await self._client.get(self.base_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=self.timeout, headers=DEFAULT_HEADERS) as client:
                response = await client.get(self.base_url, params=params)

        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise ValueError(
                f"La API respondió {response.status_code} sin JSON (Content-Type: '{content_type}'). "
                f"Posible fallback HTML por URL incorrecta. Inicio: {response.text[:300].strip()}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as err:
            raise ValueError(f"JSON inválido de la API ({err}). Inicio: {response.text[:500]}") from err

        if not isinstance(data, dict) or not isinstance(data.get("releases", []), list):
            raise ValueError("Esquema inesperado: se esperaba un objeto con lista 'releases'.")

        logger.info(f"[EXTRACT] Página {page}: {len(data.get('releases', []))} releases.")
        return data
