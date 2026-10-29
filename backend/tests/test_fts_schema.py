import pytest
from datetime import datetime
from sqlalchemy import select, delete, func, text
from database import AsyncSessionLocal
from models.tenders import TenderModel, IA_PENDIENTE, IA_OK


@pytest.mark.asyncio
async def test_schema_columns_and_fts():
    test_ocid = f"test-fts-{int(datetime.utcnow().timestamp())}"
    
    # 1. Limpieza preventiva
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid == test_ocid))

    # 2. Inserción con columnas de IA
    record = TenderModel(
        ocid=test_ocid,
        id_proceso="PROC-FTS-001",
        titulo="Adquisición de Laptops y Computadoras Portátiles",
        descripcion="Servicio de adquisición de equipos informáticos para la sede central",
        descripcion_limpia="Adquisición de computadoras portátiles para modernización de oficinas centrales",
        rubro="Tecnología y Software",
        rubro_confianza=0.95,
        palabras_clave=["laptops", "computadoras", "hardware"],
        ia_estado=IA_OK,
        ia_hash="dummyhash123",
        ia_procesado_en=datetime.utcnow(),
        estado="Vigente",
        objeto_contratacion="Bienes",
        monto_estimado=120000.0,
        moneda="PEN",
        fecha_lanzamiento=datetime.utcnow()
    )

    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(record)

    # 3. Validar persistencia y autogeneración de search_vector
    async with AsyncSessionLocal() as session:
        stmt = select(TenderModel).where(TenderModel.ocid == test_ocid)
        res = await session.execute(stmt)
        item = res.scalar_one()

        assert item.rubro == "Tecnología y Software"
        assert item.ia_estado == IA_OK
        assert float(item.rubro_confianza) == 0.95
        assert "laptops" in item.palabras_clave

        # 4. Probar búsqueda FTS con y sin tildes (unaccent)
        # Buscar 'computacion' o 'computadoras' sin tilde en la query
        tsquery = func.websearch_to_tsquery('spanish', func.f_unaccent('computadoras portatiles'))
        fts_stmt = select(TenderModel).where(
            TenderModel.ocid == test_ocid,
            TenderModel.search_vector.op('@@')(tsquery)
        )
        fts_res = await session.execute(fts_stmt)
        assert fts_res.scalar_one_or_none() is not None

        # Probar búsqueda por rubro 'tecnologia' sin tilde
        rubro_query = func.websearch_to_tsquery('spanish', func.f_unaccent('tecnologia'))
        fts_rubro = select(TenderModel).where(
            TenderModel.ocid == test_ocid,
            TenderModel.search_vector.op('@@')(rubro_query)
        )
        fts_rubro_res = await session.execute(fts_rubro)
        assert fts_rubro_res.scalar_one_or_none() is not None

    # 5. Limpieza
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid == test_ocid))
