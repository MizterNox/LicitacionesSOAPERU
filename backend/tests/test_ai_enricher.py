import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from services.ai_enricher import (
    GeminiEnricher,
    RUBROS_VALIDOS,
    compute_text_hash,
    fallback_clean_text,
    fallback_rubro,
)
from config import settings


def test_compute_text_hash():
    h1 = compute_text_hash("Titulo A", "Descripcion 1")
    h2 = compute_text_hash("Titulo A", "Descripcion 1")
    h3 = compute_text_hash("Titulo A", "Descripcion 2")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_fallback_clean_text():
    raw = "ADQUISICION DE   EQUIPOS   DE COMPUTO\n\nPARA LA SEDE"
    cleaned = fallback_clean_text(raw)
    assert "  " not in cleaned
    assert "\n" not in cleaned
    # Check title/proper casing applied
    assert cleaned.lower().startswith("adquisicion")


def test_fallback_rubro():
    assert fallback_rubro("Servicios") == "Servicios Generales"
    assert fallback_rubro("Obras") == "Construcción e Infraestructura"
    assert fallback_rubro("Bienes") == "Equipamiento y Mobiliario"
    assert fallback_rubro("Desconocido") == "Otros"


@pytest.mark.asyncio
async def test_enrich_batch_mocked_success():
    enricher = GeminiEnricher(api_key="mock_key", model="gemini-3.5-flash-lite")

    mock_response = {
        "items": [
            {
                "ocid": "ocds-test-1",
                "descripcion_limpia": "Adquisición de servidores de almacenamiento",
                "rubro": "Tecnología y Software",
                "confianza": 0.98,
                "palabras_clave": ["servidores", "datacenter", "almacenamiento"],
            }
        ]
    }

    with patch.object(enricher, "_call_gemini_batch", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response

        records = [
            {
                "ocid": "ocds-test-1",
                "titulo": "ADQ. SERVIDORES",
                "descripcion": "adquisicion servidores de datos para oficina",
                "objeto_contratacion": "Bienes",
            }
        ]

        results = await enricher.enrich_batch(records)

        assert len(results) == 1
        r = results[0]
        assert r["ia_estado"] == "OK"
        assert r["rubro"] == "Tecnología y Software"
        assert r["descripcion_limpia"] == "Adquisición de servidores de almacenamiento"
        assert r["rubro_confianza"] == 0.98
        assert "servidores" in r["palabras_clave"]
        assert r["ia_hash"] == compute_text_hash(r["titulo"], r["descripcion"])
        assert r["ia_procesado_en"] is not None


@pytest.mark.asyncio
async def test_enrich_batch_fallback_on_error():
    enricher = GeminiEnricher(api_key="mock_key", model="gemini-3.5-flash-lite")

    with patch.object(enricher, "_call_gemini_batch", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = RuntimeError("Quota exceeded or connection error")

        records = [
            {
                "ocid": "ocds-test-err",
                "titulo": "OBRA DE PAVIMENTACION",
                "descripcion": "construccion de pistas y veredas",
                "objeto_contratacion": "Obras",
            }
        ]

        results = await enricher.enrich_batch(records)

        assert len(results) == 1
        r = results[0]
        # In case of AI error, it gracefully degraded to fallback
        assert r["ia_estado"] == "PENDIENTE"
        assert r["rubro"] == "Construcción e Infraestructura"
        assert r["rubro_confianza"] == 0.50
        assert r["ia_hash"] is not None


@pytest.mark.asyncio
async def test_enrich_real_gemini_api():
    """Prueba real de llamada a la API si GEMINI_API_KEY está configurada."""
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key.startswith("tu_clave"):
        pytest.skip("No hay GEMINI_API_KEY configurada para prueba real.")

    enricher = GeminiEnricher(api_key=api_key, model=settings.GEMINI_MODEL)

    sample = [
        {
            "ocid": "ocds-live-test-1",
            "titulo": "ADQ. DE LICENCIAS DE SOFTWARE ANTIVIRUS Y FIREWALL CORPORATIVO",
            "descripcion": "CONTRATACION PARA LA ADQ DE LICENCIAS DE SOFTWARE SEGURIDAD",
            "objeto_contratacion": "Bienes",
        }
    ]

    results = await enricher.enrich_records(sample)
    assert len(results) == 1
    res = results[0]

    assert res["ia_estado"] == "OK"
    assert res["rubro"] in RUBROS_VALIDOS
    assert len(res["descripcion_limpia"]) > 5
    assert res["rubro_confianza"] >= 0.70
    assert isinstance(res["palabras_clave"], list)
