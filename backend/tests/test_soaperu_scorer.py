"""
Suite de pruebas unitarias para el motor de clasificación y scoring SOAPERU S.R.L.
(Fase 2 - Motor de Scoring e Inteligencia Comercial para TI en el Estado)
"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from api.main import app
from services.soaperu_scorer import SoaPeruOpportunityScorer, SOAPERU_TAXONOMY
from models.user import UserModel
from database import AsyncSessionLocal
from sqlalchemy import select


def test_scorer_todas_las_lineas_soaperu():
    """Verifica que cada una de las 7 líneas de negocio de SOAPERU sea identificada correctamente."""
    casos = [
        ("SERVICIO DE IMPLEMENTACION Y CONFIGURACION DE ODOO ERP", "ERP_ODOO"),
        ("CONTRATACION DE SERVICIO DE TABLEROS DE CONTROL EN POWER BI", "BI_ANALITICA"),
        ("ADQUISICION DE LICENCIAS KASPERSKY ENDPOINT SECURITY PARA SERVIDORES", "CIBERSEGURIDAD"),
        ("SERVICIO DE RESPALDO Y COPIAS DE SEGURIDAD CON VEEAM BACKUP", "BACKUP_CONTINUIDAD"),
        ("RENOVACION DE SUSCRIPCIONES MICROSOFT 365 Y CORREO INSTITUCIONAL", "MICROSOFT_CLOUD"),
        ("SERVICIO DE FACTURACION ELECTRONICA E INTEGRACION SUNAT", "FACTURACION_ELECTRONICA"),
        ("CONTRATACION DE FABRICA DE SOFTWARE PARA DESARROLLO DE APLICATIVO WEB", "DESARROLLO_SOFTWARE"),
    ]

    for titulo, tag_esperado in casos:
        res = SoaPeruOpportunityScorer.score_tender(
            titulo=titulo,
            descripcion="Servicio especializado para la entidad",
            objeto_contratacion="SERVICIOS",
            monto_estimado=30000.0,
            region="LAMBAYEQUE",
            entidad_nombre="GOBIERNO REGIONAL DE LAMBAYEQUE",
        )
        assert res["primary_tag"] == tag_esperado, f"Fallo para {titulo}: obtuvo {res['primary_tag']}"
        assert res["relevance_score"] >= 70, f"Puntaje esperado alto para {titulo}, obtuvo {res['relevance_score']}"
        assert tag_esperado in res["matched_tags"]
        assert res["is_minor_contract"] is True


def test_scorer_exclusion_negativa_obras_y_fisico():
    """Comprueba que términos no tecnológicos sean excluidos inmediatamente con puntaje 0."""
    res_obra = SoaPeruOpportunityScorer.score_tender(
        titulo="MANTENIMIENTO DE RED DE AGUA POTABLE Y ALCANTARILLADO",
        descripcion="Reparacion de tuberias de obra civil",
        objeto_contratacion="OBRAS",
        monto_estimado=25000.0,
    )
    assert res_obra["relevance_score"] == 0
    assert res_obra["primary_tag"] == "EXCLUIDO"

    res_vehiculo = SoaPeruOpportunityScorer.score_tender(
        titulo="ADQUISICION DE NEUMATICOS PARA CAMIONETA Y VEHICULOS",
        descripcion="Mantenimiento de camionetas de la entidad",
        objeto_contratacion="BIENES",
        monto_estimado=15000.0,
    )
    assert res_vehiculo["relevance_score"] == 0
    assert res_vehiculo["primary_tag"] == "EXCLUIDO"


def test_scorer_inmunidad_tecnologica():
    """Si aparece una marca/tecnología core de SOAPERU junto a una palabra excluida, se prioriza TI."""
    res = SoaPeruOpportunityScorer.score_tender(
        titulo="MANTENIMIENTO DEL SISTEMA ELECTRICO Y SEGURIDAD KASPERSKY",
        descripcion="Antivirus y proteccion perimetral kaspersky",
        objeto_contratacion="SERVICIOS",
        monto_estimado=22000.0,
    )
    assert res["primary_tag"] == "CIBERSEGURIDAD"
    assert res["relevance_score"] >= 60


def test_scorer_bonificacion_cubso():
    """Valida la bonificación por prefijos CUBSO 8111 (Servicios TI) y 4323 (Software)."""
    payload_cubso = {
        "tender": {
            "items": [
                {
                    "classification": {
                        "id": "8111210200361940",
                        "description": "Servicios de soporte informático",
                        "scheme": "CUBSO"
                    }
                }
            ]
        }
    }
    res = SoaPeruOpportunityScorer.score_tender(
        titulo="CONTRATACION DE SERVICIO PARA MANTENIMIENTO",
        descripcion="Soporte tecnico preventivo",
        objeto_contratacion="SERVICIOS",
        monto_estimado=18000.0,
        raw_payload=payload_cubso,
    )
    assert any("CUBSO:8111" in k for k in res["matched_keywords"])
    assert res["relevance_score"] >= 35


@pytest.mark.asyncio
async def test_endpoint_recalculate_scoring_requiere_admin():
    """Verifica que el endpoint /api/v1/etl/recalculate-scoring exija privilegios de administrador."""
    transport = ASGITransport(app=app)
    test_user_email = f"user_{uuid.uuid4().hex[:8]}@empresa.pe"
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Sin autenticación -> 401
        res_no_auth = await ac.post("/api/v1/etl/recalculate-scoring")
        assert res_no_auth.status_code == 401

        # 2. Con usuario normal (rol: 'user') -> 403 Forbidden
        reg_user = await ac.post("/api/v1/auth/register", json={
            "email": test_user_email,
            "password": "PasswordUser2026!",
            "nombre": "Usuario Comun"
        })
        assert reg_user.status_code == 201
        user_token = reg_user.json()["access_token"]
        res_forbidden = await ac.post(
            "/api/v1/etl/recalculate-scoring",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert res_forbidden.status_code == 403

        # 3. Con usuario admin -> 200 OK
        # Promover al usuario a admin en base de datos para la prueba
        async with AsyncSessionLocal() as session:
            q = select(UserModel).where(UserModel.email == test_user_email)
            res_db = await session.execute(q)
            usr = res_db.scalar_one()
            usr.rol = "admin"
            await session.commit()

        # Al re-login o con nuevo token se convierte en admin
        login_res = await ac.post("/api/v1/auth/login", json={
            "email": test_user_email,
            "password": "PasswordUser2026!"
        })
        admin_token = login_res.json()["access_token"]
        res_admin = await ac.post(
            "/api/v1/etl/recalculate-scoring",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert data["status"] == "success"
        assert "resultado" in data


@pytest.mark.asyncio
async def test_api_licitaciones_filtros_soaperu():
    """Valida los nuevos filtros primary_tag y min_score en GET /api/licitaciones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/licitaciones", params={"min_score": 30})
        assert res.status_code == 200
        tenders = res.json()
        for t in tenders:
            assert t["relevance_score"] >= 30
            assert "primary_tag" in t
            assert "matched_tags" in t
            assert "matched_keywords" in t
            assert "is_minor_contract" in t
