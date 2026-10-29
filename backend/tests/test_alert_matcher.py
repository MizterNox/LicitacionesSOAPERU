import pytest
from datetime import datetime
from sqlalchemy import select, delete
from database import AsyncSessionLocal
from models.user import UserModel
from models.saved_filter import SavedFilterModel
from models.alert_log import AlertLogModel
from models.tenders import TenderModel
from services.alert_matcher import match_alerts_for_tenders, run_alert_matching
from core.security import hash_password


@pytest.mark.asyncio
async def test_alert_matcher_empty():
    res = await run_alert_matching([])
    assert res["status"] == "success"
    assert res["total_evaluados"] == 0
    assert res["total_coincidencias"] == 0
    assert res["usuarios_alertados"] == 0


@pytest.mark.asyncio
async def test_alert_matcher_matching_and_deduplication():
    test_email = "matcher_test_user@licitlens.pe"
    ocid_a = "ocid-test-alert-match-laptop-1"
    ocid_b = "ocid-test-alert-match-cemento-2"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Limpiar datos previos si existen
            await session.execute(delete(AlertLogModel).where(AlertLogModel.ocid.in_([ocid_a, ocid_b])))
            await session.execute(delete(TenderModel).where(TenderModel.ocid.in_([ocid_a, ocid_b])))
            
            # 1. Crear usuario de prueba
            res_user = await session.execute(select(UserModel).where(UserModel.email == test_email))
            user = res_user.scalar_one_or_none()
            if not user:
                user = UserModel(
                    email=test_email,
                    password_hash=hash_password("TestPassword2026!"),
                    nombre="Usuario Matcher Test",
                    activo=True,
                    rol="user"
                )
                session.add(user)
                await session.flush()

            # 2. Crear filtro guardado activo con rubro y término de búsqueda
            await session.execute(delete(SavedFilterModel).where(SavedFilterModel.user_id == user.id))
            saved_filter = SavedFilterModel(
                user_id=user.id,
                nombre="Alerta Laptops Estado",
                filtros={
                    "q": "laptop",
                    "rubro": "Tecnología y Software",
                    "tipo": "Bienes",
                    "vigentes": True
                },
                alertas_activas=True,
                frecuencia="inmediata"
            )
            session.add(saved_filter)
            await session.flush()
            filter_id = saved_filter.id

            # 3. Crear 2 licitaciones: una que cumple el filtro y otra que no
            tender_match = TenderModel(
                ocid=ocid_a,
                id_proceso="LP-001-2026-MINEDU",
                titulo="Adquisicion de laptop y tablets educativas",
                descripcion_limpia="Suministro e instalacion de laptop de alto rendimiento para colegios",
                estado="Vigente",
                objeto_contratacion="Bienes",
                rubro="Tecnología y Software",
                monto_estimado=250000.00,
                moneda="PEN",
                fecha_lanzamiento=datetime.utcnow()
            )
            tender_no_match = TenderModel(
                ocid=ocid_b,
                id_proceso="CP-002-2026-MTC",
                titulo="Pavimentacion y compra de cemento",
                descripcion_limpia="Obras viales y adquisicion de cemento portland",
                estado="Vigente",
                objeto_contratacion="Obras",
                rubro="Construcción e Infraestructura",
                monto_estimado=1800000.00,
                moneda="PEN",
                fecha_lanzamiento=datetime.utcnow()
            )
            session.add_all([tender_match, tender_no_match])

    # 4. Ejecutar primer cruce de alertas
    res_run1 = await run_alert_matching([ocid_a, ocid_b])
    assert res_run1["status"] == "success"
    assert res_run1["total_evaluados"] == 2
    assert res_run1["total_coincidencias"] == 1
    assert res_run1["alertas_registradas"] == 1
    assert res_run1["usuarios_alertados"] == 1

    # Verificar que el usuario agrupado contenga la licitación que coincide
    user_payload = list(res_run1["usuarios"].values())[0]
    assert user_payload["email"] == test_email
    assert len(user_payload["filtros_coincidentes"]) == 1
    matched_filter_data = user_payload["filtros_coincidentes"][0]
    assert matched_filter_data["saved_filter_id"] == filter_id
    assert len(matched_filter_data["oportunidades"]) == 1
    assert matched_filter_data["oportunidades"][0]["ocid"] == ocid_a

    # Verificar registro en base de datos en alert_log
    async with AsyncSessionLocal() as session:
        res_log = await session.execute(
            select(AlertLogModel).where(
                AlertLogModel.saved_filter_id == filter_id,
                AlertLogModel.ocid == ocid_a
            )
        )
        log_entry = res_log.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.user_id == user_payload["user_id"]

    # 5. Ejecutar SEGUNDO cruce con el mismo OCID (Prueba de Deduplicación / Idempotencia)
    res_run2 = await run_alert_matching([ocid_a, ocid_b])
    assert res_run2["status"] == "success"
    # Debe ser ignorado por deduplicación (ya fue enviado)
    assert res_run2["total_coincidencias"] == 0
    assert res_run2["alertas_registradas"] == 0
    assert res_run2["usuarios_alertados"] == 0

    # 6. Limpieza defensiva
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(delete(AlertLogModel).where(AlertLogModel.ocid.in_([ocid_a, ocid_b])))
            await session.execute(delete(TenderModel).where(TenderModel.ocid.in_([ocid_a, ocid_b])))
            await session.execute(delete(SavedFilterModel).where(SavedFilterModel.id == filter_id))
            await session.execute(delete(UserModel).where(UserModel.email == test_email))
