import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_api_licitaciones_fts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Búsqueda FTS básica
        res = await ac.get("/api/licitaciones?q=consultoria&vigentes=true&fecha=todos")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        if data:
            assert "rubro" in data[0]
            assert "descripcion_limpia" in data[0]

        # 2. Sugerencias de autocompletado
        res_sugg = await ac.get("/api/v1/search/suggest?q=tecnologia")
        assert res_sugg.status_code == 200
        suggs = res_sugg.json()
        assert isinstance(suggs, list)

        # 3. Listado de rubros con conteos
        res_rubros = await ac.get("/api/v1/rubros")
        assert res_rubros.status_code == 200
        rubros = res_rubros.json()
        assert isinstance(rubros, list)
        assert len(rubros) >= 10
        assert any(r["id"] == "Tecnología y Software" for r in rubros)
