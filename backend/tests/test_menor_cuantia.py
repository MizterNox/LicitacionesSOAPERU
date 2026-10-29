"""
Tests unitarios para las funciones y lógica de negocio de Contrataciones Menores (<= 8 UIT)
y normalización OCDS (Servicios, Bienes, Obras).
"""

import pytest
from datetime import datetime, timedelta
from schemas.ocds_schema import (
    is_menor_cuantia,
    extract_tipo_proceso_real,
    extract_entidad_info,
    extract_region_info,
    extract_cui,
    extract_items_normalized,
    extract_documents_normalized,
    extract_fecha_limite_real,
    compute_estado,
    compute_content_hash,
    build_metadata
)
from services.search import TenderFilters, build_search_query
from config import settings


def test_is_menor_cuantia():
    # Menor al tope de 8 UIT (S/ 42,800)
    assert is_menor_cuantia(25000.0, "AS") is True
    assert is_menor_cuantia(42800.0, "AS") is True
    # Superior a 8 UIT
    assert is_menor_cuantia(42801.0, "AS") is False
    assert is_menor_cuantia(150000.0, "CP") is False
    # Tipo MC siempre es menor cuantía independiente del monto
    assert is_menor_cuantia(100000.0, "MC") is True
    assert is_menor_cuantia(60000.0, extract_tipo_proceso_real("COMPRE-01-2025")) is True


def test_extract_tipo_proceso_real():
    assert extract_tipo_proceso_real("MC-001-2025-MML") == "MC"
    assert extract_tipo_proceso_real("AS-005-2025-MINSA") == "AS"
    assert extract_tipo_proceso_real("LP-002-2025-MTC") == "LP"
    assert extract_tipo_proceso_real("CP-010-2025-GRC") == "CP"
    assert extract_tipo_proceso_real("COMPRE-003-2025-MINEDU") == "MC"
    
    # Desde raw_payload methodDetails
    raw = {"tender": {"procurementMethodDetails": "Subasta Inversa Electrónica"}}
    assert extract_tipo_proceso_real(None, raw) == "SIE"


def test_extract_entidad_and_region_info():
    raw = {
        "buyer": {"name": "MUNICIPALIDAD DISTRITAL DE MIRAFLORES", "id": "PE-RUC-20131378372"},
        "parties": [
            {
                "roles": ["buyer", "procuringEntity"],
                "name": "MUNICIPALIDAD DISTRITAL DE MIRAFLORES",
                "identifier": {"id": "20131378372", "legalName": "MUNICIPALIDAD DISTRITAL DE MIRAFLORES"},
                "address": {"locality": "Miraflores", "region": "Lima", "countryName": "Perú"}
            }
        ]
    }
    info = extract_entidad_info(raw)
    assert "MIRAFLORES" in info["nombre"]
    assert info["ruc"] == "20131378372"

    region = extract_region_info(raw, "Mantenimiento vial en Miraflores")
    assert region == "Lima"


def test_extract_cui():
    raw = {
        "tender": {
            "title": "MEJORAMIENTO DEL SERVICIO DE TRANSITABILIDAD CON CUI 2456789 EN PUNO"
        }
    }
    cui = extract_cui(raw["tender"]["title"], "CUI 2456789")
    assert cui == "2456789"


def test_extract_items_normalized():
    raw = {
        "tender": {
            "items": [
                {
                    "id": "item-1",
                    "description": "Laptops para servidores públicos",
                    "classification": {"id": "43211503", "description": "Computadores portatiles"},
                    "quantity": 15,
                    "unit": {"name": "UNIDAD"}
                }
            ]
        }
    }
    items = extract_items_normalized(raw)
    assert len(items) == 1
    assert items[0]["codigo_cubso"] == "43211503"
    assert items[0]["cantidad"] == 15.0
    assert items[0]["unidad"] == "UNIDAD"


def test_extract_documents_normalized():
    raw = {
        "tender": {
            "documents": [
                {
                    "id": "doc-bases-01",
                    "title": "Bases Integradas del Proceso",
                    "documentType": "tenderNotice",
                    "url": "https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/ficha/bases.pdf",
                    "datePublished": "2025-05-10T12:00:00Z"
                }
            ]
        }
    }
    docs = extract_documents_normalized(raw)
    assert len(docs) == 1
    assert docs[0]["url"] == "https://prodapp2.seace.gob.pe/seacebus-uiwd-pub/ficha/bases.pdf"
    assert docs[0]["formato"] == "PDF"


def test_extract_fecha_limite_real():
    # Caso 1: tenderPeriod.endDate válido posterior a publicación
    pub_dt = datetime(2025, 6, 1, 10, 0, 0)
    raw = {
        "tender": {
            "tenderPeriod": {"endDate": "2025-06-15T23:59:59Z"}
        }
    }
    res = extract_fecha_limite_real(raw, pub_dt)
    assert res["fecha_limite"] == "2025-06-15"
    assert res["es_estimada"] is False

    # Caso 2: tenderPeriod no tiene fin real pero enquiryPeriod sí (consultas + 2 días)
    raw2 = {
        "tender": {
            "tenderPeriod": {"endDate": "2025-06-01T10:00:00Z"},
            "enquiryPeriod": {"endDate": "2025-06-08T18:00:00Z"}
        }
    }
    res2 = extract_fecha_limite_real(raw2, pub_dt)
    assert res2["fecha_limite"] == "2025-06-10"
    assert res2["es_estimada"] is True

    # Caso 3: sin fecha real -> retorna None (no inventa +15 días)
    raw3 = {"tender": {}}
    res3 = extract_fecha_limite_real(raw3, pub_dt)
    assert res3["fecha_limite"] is None


def test_compute_content_hash():
    release1 = {
        "tender": {
            "value": {"amount": 1000},
            "tenderPeriod": {"endDate": "2025-06-15"},
            "enquiryPeriod": {"endDate": "2025-06-10"},
            "documents": [{"id": "1"}]
        }
    }
    release2 = {
        "tender": {
            "value": {"amount": 1000},
            "tenderPeriod": {"endDate": "2025-06-15"},
            "enquiryPeriod": {"endDate": "2025-06-10"},
            "documents": [{"id": "1"}]
        }
    }
    release3 = {
        "tender": {
            "value": {"amount": 2000},
            "tenderPeriod": {"endDate": "2025-06-15"},
            "enquiryPeriod": {"endDate": "2025-06-10"},
            "documents": [{"id": "1"}]
        }
    }

    # Hash idéntico para mismos valores operativos
    assert compute_content_hash(release1, "Vigente") == compute_content_hash(release2, "Vigente")
    # Cambio de monto altera hash
    assert compute_content_hash(release1, "Vigente") != compute_content_hash(release3, "Vigente")
    # Cambio de estado altera hash
    assert compute_content_hash(release1, "Vigente") != compute_content_hash(release1, "Adjudicado")


def test_build_metadata():
    raw = {
        "buyer": {"name": "MUNICIPALIDAD DE LIMA"},
        "parties": [{"roles": ["buyer"], "name": "MUNICIPALIDAD DE LIMA", "address": {"region": "Lima"}}],
        "tender": {
            "title": "SERVICIO DE LIMPIEZA",
            "items": [{"id": "1", "description": "Limpieza general", "quantity": 1}],
            "documents": [{"id": "d1", "title": "Bases", "url": "http://seace/b.pdf"}]
        }
    }
    meta = build_metadata(raw, "AS-01-2025-MML", "Servicio de limpieza", 30000.0, datetime(2025, 1, 1))
    assert meta["entidad"] == "MUNICIPALIDAD DE LIMA"
    assert meta["region"] == "Lima"
    assert meta["es_menor_cuantia"] is True
    assert len(meta["items"]) == 1
    assert len(meta["documentos"]) == 1


def test_search_filters_menor_cuantia():
    filters = TenderFilters(solo_menores=True, region="Lima", plazo="48h")
    stmt, _ = build_search_query(filters)
    sql_str = str(stmt)
    assert "es_menor_cuantia" in sql_str
    assert "region" in sql_str
    assert "fecha_limite" in sql_str
