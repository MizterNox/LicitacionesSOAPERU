import httpx
import asyncio
import json
from datetime import datetime

# URL base oficial proporcionada por la documentación de OECE (incluyendo versión /v1)
BASE_URL = "https://contratacionesabiertas.oece.gob.pe/api/v1"

# Mapeo de objetos en español al estándar OCDS usado por la API OECE (enum: goods, works, services)
OBJETO_MAP = {
    "servicios": "services",
    "bienes": "goods",
    "obras": "works",
    "consultoria": "services",
    "consultoría": "services"
}

import pytest

async def test_extraccion_etl(objeto: str = "Servicios", estado: str = "Vigente", fecha_desde: str = None):
    endpoint = f"{BASE_URL}/releases"
    
    # Construcción de parámetros según el esquema OpenAPI oficial de OECE
    params = {
        "page": 1,
        "order": "desc"
    }

    # Mapeo de categoría si se especifica
    if objeto:
        categoria_api = OBJETO_MAP.get(objeto.lower(), objeto.lower())
        if categoria_api in ["goods", "works", "services"]:
            params["mainProcurementCategory"] = categoria_api

    # Filtro de fecha de inicio (formato YYYY-MM-DD según esquema OpenAPI)
    if fecha_desde:
        params["startDate"] = fecha_desde

    print(f"--- PROBANDO CONEXIÓN A LA API ---")
    print(f"URL: {endpoint}")
    print(f"Filtros aplicados (Query Params): {params}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(endpoint, params=params)
            
            # Inspección HTTP: código de estado y vista previa del contenido crudo
            content_type = response.headers.get("content-type", "")
            print(f"Código de Estado HTTP: {response.status_code}")
            print(f"Content-Type: {content_type}")
            print(f"Respuesta Cruda (primeros 250 caracteres):\n{response.text[:250]}\n")
            
            # Verificación de código de estado HTTP
            response.raise_for_status()
            
            # Verificación preventiva de Content-Type antes de parsear JSON
            if "application/json" not in content_type:
                print(f"[ERROR] El servidor respondió con 200 pero el formato no es JSON ({content_type}).")
                print("Es posible que la ruta no exista y el servidor esté devolviendo el HTML del SPA (Single Page Application).")
                return

            # Parseo seguro de JSON
            try:
                data = response.json()
            except json.JSONDecodeError as json_err:
                print(f"[ERROR] Error al decodificar JSON: {json_err}")
                print(f"Contenido completo recibido:\n{response.text}")
                return

            releases = data.get("releases", [])
            print(f"¡Conexión exitosa! Se obtuvieron {len(releases)} registros.")
            
            # Si se desea filtrar por estado 'Vigente' (en OCDS suele ser tender.status == 'active'),
            if releases:
                primer_proceso = releases[0]
                tender = primer_proceso.get("tender", {})
                
                # En OECE OCDS, el estado viene dentro de la lista de items (status y statusDetails)
                items = tender.get("items", [])
                estado_ocds = items[0].get("status") if items else tender.get("status", "No especificado")
                estado_detalle = items[0].get("statusDetails") if items else "No especificado"

                print("\nEjemplo de proceso encontrado:")
                print(f" - OCID: {primer_proceso.get('ocid')}")
                print(f" - Título: {tender.get('title', 'Sin título')}")
                print(f" - Categoría: {tender.get('mainProcurementCategory')}")
                print(f" - Estado OCDS (ítem): {estado_ocds} (ej. active = vigente)")
                print(f" - Estado SEACE (statusDetails): {estado_detalle} (ej. CONVOCADO)")
                print(f" - Fecha: {primer_proceso.get('date')}")
            else:
                print("La API respondió correctamente (JSON válido), pero no se encontraron registros para los filtros indicados.")
                
        except httpx.HTTPStatusError as http_err:
            print(f"Error HTTP devuelto por la API ({http_err.response.status_code}): {http_err.response.text[:200]}")
        except httpx.HTTPError as net_err:
            print(f"Error de red o conexión al conectar con OECE: {net_err}")
if __name__ == "__main__":
    # Ejecutamos la prueba asíncrona directamente si se corre como script
    asyncio.run(test_extraccion_etl(objeto="Servicios", estado="Vigente"))