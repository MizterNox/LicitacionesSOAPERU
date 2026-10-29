import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from services.mailer import (
    render_alert_email,
    send_email,
    dispatch_user_alerts,
    send_test_alert_email
)
from config import settings


def test_render_alert_email():
    filtros = [
        {
            "saved_filter_id": 10,
            "nombre_filtro": "Servidores y Laptops",
            "oportunidades": [
                {
                    "ocid": "ocds-test-123",
                    "id_proceso": "LP-001-2026-MINEDU",
                    "titulo": "Adquisición de Servidores de Alta Disponibilidad",
                    "descripcion_corta": "Suministro e instalación de servidores para centros de datos",
                    "rubro": "Tecnología y Software",
                    "monto_estimado": 150000.50,
                    "moneda": "PEN"
                }
            ]
        }
    ]

    html_content, text_content = render_alert_email(
        user_nombre="Ing. Roberto Quispe",
        total_oportunidades=1,
        filtros_coincidentes=filtros,
        frontend_url="http://localhost:5173"
    )

    assert "Ing. Roberto Quispe" in html_content
    assert "Servidores y Laptops" in html_content
    assert "LP-001-2026-MINEDU" in html_content
    assert "150,000.50" in html_content
    assert "http://localhost:5173" in html_content

    assert "Ing. Roberto Quispe" in text_content
    assert "LP-001-2026-MINEDU" in text_content


@pytest.mark.asyncio
async def test_send_email_dry_run():
    # En entorno de prueba, MAIL_DRY_RUN debe ser True
    assert settings.MAIL_DRY_RUN is True
    ok = await send_email(
        to_email="test_licitador@empresa.com.pe",
        subject="Prueba de alerta",
        html_content="<p>Hola mundo</p>",
        text_content="Hola mundo"
    )
    assert ok is True

    # Correo inválido debe fallar elegantemente
    bad_email = await send_email(
        to_email="correo_invalido_sin_arroba",
        subject="Fallo",
        html_content="<p>Error</p>"
    )
    assert bad_email is False


@pytest.mark.asyncio
async def test_dispatch_user_alerts():
    mock_users_map = {
        101: {
            "email": "user1@constructora.pe",
            "nombre": "Constructora Norte",
            "total_oportunidades": 1,
            "filtros_coincidentes": [
                {
                    "saved_filter_id": 1,
                    "nombre_filtro": "Obras Viales",
                    "oportunidades": [
                        {
                            "ocid": "ocds-obras-001",
                            "titulo": "Asfaltado Carretera Central",
                            "monto_estimado": 5000000.0,
                            "rubro": "Construcción e Infraestructura"
                        }
                    ]
                }
            ]
        },
        102: {
            "email": "user2@farmaceutica.pe",
            "nombre": "Farmacia Central",
            "total_oportunidades": 2,
            "filtros_coincidentes": [
                {
                    "saved_filter_id": 2,
                    "nombre_filtro": "Medicamentos",
                    "oportunidades": [
                        {
                            "ocid": "ocds-farma-001",
                            "titulo": "Adquisición de Vacunas",
                            "monto_estimado": 350000.0,
                            "rubro": "Salud y Farmacia"
                        }
                    ]
                }
            ]
        }
    }

    res = await dispatch_user_alerts(mock_users_map)
    assert res["total_usuarios"] == 2
    assert res["enviados"] == 2
    assert res["fallidos"] == 0
    assert len(res["detalles"]) == 2


@pytest.mark.asyncio
async def test_send_test_alert_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        email = "test_endpoint_mailer@empresa.pe"
        pwd = "MailerPassword2026!"

        # 1. Registrar / Iniciar sesión
        await ac.post("/api/v1/auth/register", json={
            "email": email,
            "password": pwd,
            "nombre": "Gerente de Licitaciones"
        })
        login_res = await ac.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Invocar endpoint de prueba de correo
        test_email_res = await ac.post("/api/v1/me/alerts/test", headers=headers)
        assert test_email_res.status_code == 200
        data = test_email_res.json()
        assert data["status"] == "success"
        assert data["enviado"] is True
        assert data["email"] == email
        assert "simulado_dry_run" in data
