import pytest
import sys
import os
from datetime import datetime

# Añadir backend/src al path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(backend_dir, "src")
for p in [src_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from etl.loader import guardar_releases_en_db
from models.tenders import TenderModel
from database import AsyncSessionLocal
from sqlalchemy import select, delete

@pytest.mark.asyncio
async def test_no_sobreescritura_opcion_b():
    """
    Valida que:
    1. Un registro nuevo se inserta.
    2. El mismo registro con el mismo estado se ignora (no se sobreescribe).
    3. Si el estado cambia, se actualiza el estado preservando la fecha original.
    """
    test_ocid = f"test-ocid-{int(datetime.utcnow().timestamp())}"
    fecha_original = datetime(2026, 10, 15, 8, 30, 0)

    # Limpiar si existiera
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid == test_ocid))

    record_1 = {
        "ocid": test_ocid,
        "id_proceso": "PROC-001",
        "titulo": "Licitación de Prueba Inicial",
        "descripcion": "Descripción original",
        "estado": "Vigente",
        "objeto_contratacion": "Servicios",
        "monto_estimado": 50000.0,
        "moneda": "PEN",
        "fecha_lanzamiento": fecha_original,
        "raw_payload": {"test": 1}
    }

    # Paso 1: Inserción inicial
    res_1 = await guardar_releases_en_db([record_1])
    assert res_1["nuevos"] == 1
    assert res_1["actualizados"] == 0
    assert res_1["ignorados"] == 0

    # Paso 2: Segundo intento con el MISMO estado ('Vigente') pero texto modificado
    record_2 = {
        **record_1,
        "titulo": "Intento de sobreescritura con mismo estado",
        "monto_estimado": 999999.0
    }
    res_2 = await guardar_releases_en_db([record_2])
    assert res_2["nuevos"] == 0
    assert res_2["actualizados"] == 0
    assert res_2["ignorados"] == 1  # ¡Validado: No se sobreescribe!

    # Verificar en base de datos que el registro se mantuvo intacto
    async with AsyncSessionLocal() as session:
        q = select(TenderModel).where(TenderModel.ocid == test_ocid)
        row = (await session.execute(q)).scalar_one()
        assert row.titulo == "Licitación de Prueba Inicial"  # Mantuvo el título original
        assert float(row.monto_estimado) == 50000.0

    # Paso 3: Tercer intento con CAMBIO de estado ('Vigente' -> 'Adjudicado')
    record_3 = {
        **record_1,
        "estado": "Adjudicado",
        "titulo": "Licitación Adjudicada Actualizada",
        "fecha_lanzamiento": datetime(2026, 10, 20, 0, 0, 0) # Fecha que NO debe sobreescribir la original
    }
    res_3 = await guardar_releases_en_db([record_3])
    assert res_3["actualizados"] == 1
    assert res_3["nuevos"] == 0
    assert res_3["ignorados"] == 0

    # Verificar que el estado cambió pero la fecha_lanzamiento original se preservó
    async with AsyncSessionLocal() as session:
        row = (await session.execute(q)).scalar_one()
        assert row.estado == "Adjudicado"
        assert row.fecha_lanzamiento == fecha_original  # ¡Fecha original protegida!

    # Limpieza final
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid == test_ocid))
