import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_metrics_monthly_by_tipo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/metrics/monthly?meses=12&group_by=tipo")
        assert res.status_code == 200
        data = res.json()
        assert data["group_by"] == "tipo"
        assert isinstance(data["grupos"], list)
        assert isinstance(data["data"], list)
        if data["data"]:
            first = data["data"][0]
            assert "mes" in first
            assert "mes_label" in first
            assert "total" in first
            assert "monto" in first


@pytest.mark.asyncio
async def test_metrics_monthly_by_rubro():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/metrics/monthly?meses=6&group_by=rubro")
        assert res.status_code == 200
        data = res.json()
        assert data["group_by"] == "rubro"
        assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_metrics_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/metrics/summary")
        assert res.status_code == 200
        data = res.json()
        assert "total_convocatorias" in data
        assert "monto_total" in data
        assert "ticket_promedio" in data
        assert "vigentes" in data
        assert isinstance(data["distribucion_tipo"], list)
        assert isinstance(data["top_rubros"], list)
        assert isinstance(data["top_entidades"], list)
