import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_saved_filters_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "licitador_filtros@empresa.com"
        pwd = "FiltrosSeguros2026!"

        # Registrar / Login
        await ac.post("/api/v1/auth/register", json={
            "email": email,
            "password": pwd,
            "nombre": "Proveedor de Tecnología"
        })
        login_res = await ac.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Crear filtro guardado
        create_res = await ac.post("/api/v1/me/filters", json={
            "nombre": "Licitaciones TI Vigentes",
            "filtros": {
                "rubro": "Tecnología y Software",
                "tipo": "Servicios",
                "vigentes": True
            },
            "alertas_activas": True,
            "frecuencia": "inmediata"
        }, headers=headers)
        assert create_res.status_code == 201
        created_data = create_res.json()
        filter_id = created_data["id"]
        assert created_data["nombre"] == "Licitaciones TI Vigentes"
        assert created_data["filtros"]["rubro"] == "Tecnología y Software"

        # 2. Listar filtros guardados del usuario
        list_res = await ac.get("/api/v1/me/filters", headers=headers)
        assert list_res.status_code == 200
        filters_list = list_res.json()
        assert len(filters_list) >= 1
        found = next((f for f in filters_list if f["id"] == filter_id), None)
        assert found is not None
        assert "coincidencias_actuales" in found

        # 3. Actualizar filtro
        update_res = await ac.put(f"/api/v1/me/filters/{filter_id}", json={
            "nombre": "Software y Consultoría TI",
            "alertas_activas": False
        }, headers=headers)
        assert update_res.status_code == 200
        assert update_res.json()["nombre"] == "Software y Consultoría TI"
        assert update_res.json()["alertas_activas"] is False

        # 4. Consultar historial de alertas
        history_res = await ac.get("/api/v1/me/alerts/history", headers=headers)
        assert history_res.status_code == 200
        assert isinstance(history_res.json(), list)

        # 5. Eliminar filtro
        del_res = await ac.delete(f"/api/v1/me/filters/{filter_id}", headers=headers)
        assert del_res.status_code == 200

        # Verificar que ya no existe
        list_after = await ac.get("/api/v1/me/filters", headers=headers)
        assert not any(f["id"] == filter_id for f in list_after.json())
