import pytest
from datetime import datetime
from database import AsyncSessionLocal
from models.tenders import TenderModel, IA_OK
from services.search import TenderFilters, build_search_query, get_search_suggestions
from sqlalchemy import select, delete


@pytest.mark.asyncio
async def test_search_fts_and_filters():
    test_ocid_1 = f"test-search-1-{int(datetime.utcnow().timestamp())}"
    test_ocid_2 = f"test-search-2-{int(datetime.utcnow().timestamp())}"

    # Limpieza
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid.in_([test_ocid_1, test_ocid_2])))

    # Crear registros de prueba
    r1 = TenderModel(
        ocid=test_ocid_1,
        id_proceso="PROC-TECH-01",
        titulo="Adquisición de Laptops y Computadoras Portátiles para Educación",
        descripcion="Contratacion para compra de computadoras portatiles y servidores",
        descripcion_limpia="Adquisición de computadoras portátiles y servidores de alto rendimiento",
        rubro="Tecnología y Software",
        rubro_confianza=0.98,
        palabras_clave=["laptops", "computadoras", "servidores"],
        ia_estado=IA_OK,
        estado="Vigente",
        objeto_contratacion="Bienes",
        monto_estimado=250000.0,
        moneda="PEN",
        fecha_lanzamiento=datetime(2026, 10, 1)
    )

    r2 = TenderModel(
        ocid=test_ocid_2,
        id_proceso="PROC-OBRA-02",
        titulo="Construcción de Puente y Mantenimiento de Pistas",
        descripcion="Mejoramiento de transitabilidad vial urbana",
        descripcion_limpia="Construcción de puente carrozable y pavimentación de vías",
        rubro="Construcción e Infraestructura",
        rubro_confianza=0.95,
        palabras_clave=["puente", "pistas", "vial"],
        ia_estado=IA_OK,
        estado="Vigente",
        objeto_contratacion="Obras",
        monto_estimado=850000.0,
        moneda="PEN",
        fecha_lanzamiento=datetime(2026, 10, 5)
    )

    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add_all([r1, r2])

    async with AsyncSessionLocal() as session:
        # 1. Búsqueda FTS: 'computacion' o 'computadoras' sin tilde
        f1 = TenderFilters(q="computadoras portatiles", sort="relevance")
        stmt1, _ = build_search_query(f1)
        res1 = await session.execute(stmt1)
        found1 = [row.ocid for row in res1.scalars().all()]
        assert test_ocid_1 in found1
        assert test_ocid_2 not in found1

        # 2. Búsqueda por rubro
        f2 = TenderFilters(rubro="Construcción e Infraestructura")
        stmt2, _ = build_search_query(f2)
        res2 = await session.execute(stmt2)
        found2 = [row.ocid for row in res2.scalars().all()]
        assert test_ocid_2 in found2
        assert test_ocid_1 not in found2

        # 3. Búsqueda por rango de montos
        f3 = TenderFilters(monto_min=500000.0)
        stmt3, _ = build_search_query(f3)
        res3 = await session.execute(stmt3)
        found3 = [row.ocid for row in res3.scalars().all()]
        assert test_ocid_2 in found3
        assert test_ocid_1 not in found3

        # 4. Búsqueda por código parcial
        f4 = TenderFilters(q="PROC-TECH")
        stmt4, _ = build_search_query(f4)
        res4 = await session.execute(stmt4)
        found4 = [row.ocid for row in res4.scalars().all()]
        assert test_ocid_1 in found4

        # 5. Sugerencias de autocompletado
        suggs = await get_search_suggestions(session, "Tecnolo", limit=5)
        rubro_suggs = [s["texto"] for s in suggs if s["tipo"] == "rubro"]
        assert "Tecnología y Software" in rubro_suggs

    # Limpieza
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(TenderModel).where(TenderModel.ocid.in_([test_ocid_1, test_ocid_2])))
