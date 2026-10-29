"""
Servicio de matching y cruce automático de alertas post-ETL.

Compara las nuevas convocatorias extraídas por el pipeline ETL
contra los filtros guardados por los usuarios en 'saved_filters',
generando registros de auditoría en 'alert_log' y agrupando
las oportunidades por usuario para su posterior notificación por email.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pydantic import ValidationError
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal
from models.saved_filter import SavedFilterModel
from models.alert_log import AlertLogModel
from models.user import UserModel
from models.tenders import TenderModel
from services.search import TenderFilters, build_search_query

logger = logging.getLogger(__name__)


def _serialize_tender_for_alert(tender: TenderModel) -> Dict[str, Any]:
    """Extrae y formatea los datos clave de una convocatoria para la alerta/correo."""
    return {
        "ocid": tender.ocid,
        "id_proceso": tender.id_proceso,
        "titulo": tender.titulo,
        "descripcion": tender.descripcion_limpia or tender.descripcion,
        "descripcion_corta": (tender.descripcion_limpia or tender.descripcion or "")[:200] + ("..." if len(tender.descripcion_limpia or tender.descripcion or "") > 200 else ""),
        "estado": tender.estado,
        "objeto_contratacion": tender.objeto_contratacion,
        "rubro": tender.rubro or "General",
        "monto_estimado": float(tender.monto_estimado) if tender.monto_estimado is not None else None,
        "moneda": tender.moneda or "PEN",
        "fecha_lanzamiento": tender.fecha_lanzamiento.isoformat() if tender.fecha_lanzamiento else None,
    }


async def match_alerts_for_tenders(
    nuevos_ocids: List[str],
    frecuencia: Optional[str] = None,
    session=None,
    record_in_log: bool = True,
    dispatch_emails: bool = True
) -> Dict[str, Any]:
    """
    Evalúa los `nuevos_ocids` contra todos los filtros guardados activos.
    
    Parámetros:
    - nuevos_ocids: Lista de identificadores de convocatorias nuevas/actualizadas.
    - frecuencia: 'inmediata', 'diaria' o None (para evaluar todas).
    - session: AsyncSession existente (opcional para transacciones y testing).
    - record_in_log: Si es True, inserta los registros en `alert_log` con deduplicación.

    Retorna un diccionario con métricas del cruce y las oportunidades agrupadas por usuario.
    """
    if not nuevos_ocids:
        logger.info("[ALERT_MATCHER] Lista de nuevos_ocids vacía. Ninguna alerta requerida.")
        return {
            "status": "success",
            "total_evaluados": 0,
            "total_filtros_activos": 0,
            "total_coincidencias": 0,
            "usuarios_alertados": 0,
            "alertas_registradas": 0,
            "usuarios": {}
        }

    # Eliminar duplicados en los ocids de entrada
    unique_ocids = list(set([o.strip() for o in nuevos_ocids if o and o.strip()]))
    if not unique_ocids:
        return {
            "status": "success",
            "total_evaluados": 0,
            "total_filtros_activos": 0,
            "total_coincidencias": 0,
            "usuarios_alertados": 0,
            "alertas_registradas": 0,
            "usuarios": {}
        }

    should_close_session = False
    if session is None:
        session = AsyncSessionLocal()
        should_close_session = True

    try:
        # 1. Obtener todos los filtros guardados activos pertenecientes a usuarios activos
        stmt_filters = (
            select(SavedFilterModel)
            .join(UserModel, SavedFilterModel.user_id == UserModel.id)
            .where(
                SavedFilterModel.alertas_activas.is_(True),
                UserModel.activo.is_(True)
            )
            .options(selectinload(SavedFilterModel.user))
        )
        if frecuencia and frecuencia.strip():
            stmt_filters = stmt_filters.where(SavedFilterModel.frecuencia == frecuencia.strip().lower())

        res_filters = await session.execute(stmt_filters)
        active_saved_filters = res_filters.scalars().all()

        total_filtros_activos = len(active_saved_filters)
        logger.info(f"[ALERT_MATCHER] Evaluando {len(unique_ocids)} nuevas convocatorias contra {total_filtros_activos} filtros activos...")

        if not active_saved_filters:
            return {
                "status": "success",
                "total_evaluados": len(unique_ocids),
                "total_filtros_activos": 0,
                "total_coincidencias": 0,
                "usuarios_alertados": 0,
                "alertas_registradas": 0,
                "usuarios": {}
            }

        total_coincidencias = 0
        alertas_registradas = 0
        usuarios_map: Dict[int, Dict[str, Any]] = {}

        # 2. Para cada filtro, construir query de coincidencia
        for sf in active_saved_filters:
            user = sf.user
            if not user or not user.activo:
                continue

            try:
                # Validar y preparar esquema de filtros
                raw_filtros = dict(sf.filtros or {})
                filter_params = TenderFilters(**raw_filtros)
            except ValidationError as ve:
                logger.warning(f"[ALERT_MATCHER] Error de validación en filtro ID={sf.id}: {ve}")
                continue

            # Evitar truncamiento por paginación en el matching
            filter_params.limit = len(unique_ocids) + 50
            filter_params.offset = 0

            # Construir query SQL usando la lógica de búsqueda centralizada
            base_stmt, _ = build_search_query(filter_params)

            # Acotar estrictamente al lote de nuevos ocids
            base_stmt = base_stmt.where(TenderModel.ocid.in_(unique_ocids))

            # Deduplicación: Consultar los que ya fueron alertados para este filtro específico
            stmt_already_logged = select(AlertLogModel.ocid).where(
                AlertLogModel.saved_filter_id == sf.id,
                AlertLogModel.ocid.in_(unique_ocids)
            )
            res_logged = await session.execute(stmt_already_logged)
            already_logged_set: Set[str] = set(res_logged.scalars().all())

            if already_logged_set:
                base_stmt = base_stmt.where(TenderModel.ocid.not_in(already_logged_set))

            # Ejecutar consulta de coincidencia
            res_matches = await session.execute(base_stmt)
            matched_tenders = res_matches.scalars().all()

            if not matched_tenders:
                continue

            total_coincidencias += len(matched_tenders)

            # Registrar en alert_log si está habilitado
            newly_inserted_ocids = []
            if record_in_log:
                for t in matched_tenders:
                    stmt_insert_log = (
                        pg_insert(AlertLogModel)
                        .values(
                            user_id=sf.user_id,
                            saved_filter_id=sf.id,
                            ocid=t.ocid,
                            enviado_en=datetime.utcnow()
                        )
                        .on_conflict_do_nothing(
                            index_elements=["saved_filter_id", "ocid"]
                        )
                    )
                    log_res = await session.execute(stmt_insert_log)
                    if log_res.rowcount > 0:
                        alertas_registradas += 1
                        newly_inserted_ocids.append(t.ocid)
            else:
                newly_inserted_ocids = [t.ocid for t in matched_tenders]

            # Si no hubo registros nuevos (todos ya existían por conflicto concurrente), continuar
            tenders_to_notify = [t for t in matched_tenders if t.ocid in newly_inserted_ocids] if record_in_log else matched_tenders
            if not tenders_to_notify:
                continue

            # Agrupar oportunidades por usuario para preparar un solo resumen / correo
            if user.id not in usuarios_map:
                usuarios_map[user.id] = {
                    "user_id": user.id,
                    "email": user.email,
                    "nombre": user.nombre or "Usuario LicitLens",
                    "filtros_coincidentes": [],
                    "total_oportunidades": 0
                }

            filtro_entry = {
                "saved_filter_id": sf.id,
                "nombre_filtro": sf.nombre,
                "frecuencia": sf.frecuencia,
                "criterios": sf.filtros,
                "oportunidades": [_serialize_tender_for_alert(t) for t in tenders_to_notify]
            }
            usuarios_map[user.id]["filtros_coincidentes"].append(filtro_entry)
            usuarios_map[user.id]["total_oportunidades"] += len(tenders_to_notify)

        if record_in_log and should_close_session:
            await session.commit()

        despacho_stats = {"enviados": 0, "fallidos": 0}
        if dispatch_emails and usuarios_map:
            try:
                from services.mailer import dispatch_user_alerts
                despacho_stats = await dispatch_user_alerts(usuarios_map)
                logger.info(f"[ALERT_MATCHER] Despacho de correos completado: {despacho_stats.get('enviados', 0)} enviados.")
            except Exception as e_dispatch:
                logger.error(f"[ALERT_MATCHER] Error al despachar correos: {e_dispatch}")
                despacho_stats["error"] = str(e_dispatch)

        resultado = {
            "status": "success",
            "total_evaluados": len(unique_ocids),
            "total_filtros_activos": total_filtros_activos,
            "total_coincidencias": total_coincidencias,
            "usuarios_alertados": len(usuarios_map),
            "alertas_registradas": alertas_registradas,
            "usuarios": usuarios_map,
            "despacho_email": despacho_stats
        }
        logger.info(
            f"[ALERT_MATCHER] Cruce finalizado: {total_coincidencias} coincidencias, "
            f"{alertas_registradas} alertas registradas, {len(usuarios_map)} usuarios a notificar."
        )
        return resultado

    except Exception as exc:
        logger.error(f"[ALERT_MATCHER ERROR] Error durante el cruce de alertas: {exc}", exc_info=True)
        if should_close_session:
            await session.rollback()
        return {
            "status": "error",
            "error": str(exc),
            "total_evaluados": len(unique_ocids),
            "total_filtros_activos": 0,
            "total_coincidencias": 0,
            "usuarios_alertados": 0,
            "alertas_registradas": 0,
            "usuarios": {}
        }
    finally:
        if should_close_session:
            await session.close()


async def run_alert_matching(
    nuevos_ocids: List[str],
    frecuencia: Optional[str] = None,
    dispatch_emails: bool = True
) -> Dict[str, Any]:
    """
    Función de punto de entrada seguro para invocar el cruce de alertas desde tareas en segundo plano.
    Aislada para no interrumpir el flujo principal del ETL si ocurre una excepción.
    """
    try:
        return await match_alerts_for_tenders(
            nuevos_ocids=nuevos_ocids,
            frecuencia=frecuencia,
            dispatch_emails=dispatch_emails
        )
    except Exception as e:
        logger.error(f"[RUN_ALERT_MATCHING] Excepción no controlada: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
