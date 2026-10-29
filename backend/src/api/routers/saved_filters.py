"""
Router para gestión de filtros de búsqueda favoritos y alertas personalizadas:
- CRUD de filtros guardados asociados al usuario autenticado.
- Validación de criterios con el esquema centralizado TenderFilters.
- Conteo de oportunidades coincidentes actuales.
- Historial de alertas emitidas.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func, desc

from database import AsyncSessionLocal
from models.user import UserModel
from models.saved_filter import SavedFilterModel
from models.alert_log import AlertLogModel
from models.tenders import TenderModel
from services.search import TenderFilters, build_search_query
from services.exporter import extract_entidad
from api.deps import get_current_user

router = APIRouter(prefix="/api/v1/me", tags=["Filtros y Alertas"])


# =========================================================================
# ESQUEMAS PYDANTIC
# =========================================================================

class SavedFilterCreateRequest(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120, description="Nombre descriptivo de la búsqueda guardada")
    filtros: Dict[str, Any] = Field(default_factory=dict, description="Diccionario de criterios de búsqueda")
    alertas_activas: bool = Field(default=True, description="Indica si se deben enviar notificaciones para este filtro")
    frecuencia: str = Field(default="inmediata", description="Frecuencia de alerta: 'inmediata' o 'diaria'")


class SavedFilterUpdateRequest(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=2, max_length=120)
    filtros: Optional[Dict[str, Any]] = None
    alertas_activas: Optional[bool] = None
    frecuencia: Optional[str] = None


class SavedFilterResponse(BaseModel):
    id: int
    nombre: str
    filtros: Dict[str, Any]
    alertas_activas: bool
    frecuencia: str
    creado_en: datetime
    actualizado_en: datetime
    coincidencias_actuales: Optional[int] = 0
    total_alertas_enviadas: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# =========================================================================
# ENDPOINTS
# =========================================================================

@router.get("/filters", response_model=List[SavedFilterResponse])
async def list_user_saved_filters(current_user: UserModel = Depends(get_current_user)):
    """Lista todos los filtros guardados del usuario autenticado con conteo de coincidencias."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(SavedFilterModel)
            .where(SavedFilterModel.user_id == current_user.id)
            .order_by(desc(SavedFilterModel.creado_en))
        )
        saved_list = res.scalars().all()

        output = []
        for sf in saved_list:
            # Calcular coincidencias activas en PostgreSQL usando el motor FTS
            coincidencias = 0
            try:
                # Validar y normalizar parámetros
                filter_obj = TenderFilters(**(sf.filtros or {}))
                query, _ = build_search_query(filter_obj)
                # Contar sobre el query resultante
                count_query = select(func.count()).select_from(query.subquery())
                res_count = await session.execute(count_query)
                coincidencias = res_count.scalar() or 0
            except Exception as e:
                print(f"[SAVED FILTER COUNT ERROR]: {e}")

            # Contar alertas enviadas
            res_alerts = await session.execute(
                select(func.count(AlertLogModel.id)).where(AlertLogModel.saved_filter_id == sf.id)
            )
            total_alertas = res_alerts.scalar() or 0

            output.append({
                "id": sf.id,
                "nombre": sf.nombre,
                "filtros": sf.filtros or {},
                "alertas_activas": sf.alertas_activas,
                "frecuencia": sf.frecuencia,
                "creado_en": sf.creado_en,
                "actualizado_en": sf.actualizado_en,
                "coincidencias_actuales": coincidencias,
                "total_alertas_enviadas": total_alertas,
            })

        return output


@router.post("/filters", response_model=SavedFilterResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_filter(
    payload: SavedFilterCreateRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Crea y persiste un nuevo filtro de búsqueda para el usuario."""
    # Validar que los criterios de filtros sean compatibles con TenderFilters
    try:
        validated_filters = TenderFilters(**(payload.filtros or {}))
        filters_dict = validated_filters.model_dump(exclude_none=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Criterios de filtro inválidos: {str(e)}"
        )

    frec = payload.frecuencia if payload.frecuencia in ["inmediata", "diaria"] else "inmediata"

    async with AsyncSessionLocal() as session:
        new_filter = SavedFilterModel(
            user_id=current_user.id,
            nombre=payload.nombre.strip(),
            filtros=filters_dict,
            alertas_activas=payload.alertas_activas,
            frecuencia=frec,
            creado_en=datetime.utcnow(),
            actualizado_en=datetime.utcnow()
        )
        session.add(new_filter)
        await session.commit()
        await session.refresh(new_filter)

        return {
            "id": new_filter.id,
            "nombre": new_filter.nombre,
            "filtros": new_filter.filtros,
            "alertas_activas": new_filter.alertas_activas,
            "frecuencia": new_filter.frecuencia,
            "creado_en": new_filter.creado_en,
            "actualizado_en": new_filter.actualizado_en,
            "coincidencias_actuales": 0,
            "total_alertas_enviadas": 0
        }


@router.put("/filters/{filter_id}", response_model=SavedFilterResponse)
async def update_saved_filter(
    filter_id: int,
    payload: SavedFilterUpdateRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Actualiza la configuración o criterios de un filtro guardado."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(SavedFilterModel)
            .where(SavedFilterModel.id == filter_id, SavedFilterModel.user_id == current_user.id)
        )
        sf = res.scalar_one_or_none()

        if not sf:
            raise HTTPException(status_code=404, detail="Filtro no encontrado o sin permisos.")

        if payload.nombre is not None:
            sf.nombre = payload.nombre.strip()
        if payload.filtros is not None:
            validated = TenderFilters(**payload.filtros)
            sf.filtros = validated.model_dump(exclude_none=True)
        if payload.alertas_activas is not None:
            sf.alertas_activas = payload.alertas_activas
        if payload.frecuencia is not None:
            if payload.frecuencia in ["inmediata", "diaria"]:
                sf.frecuencia = payload.frecuencia

        sf.actualizado_en = datetime.utcnow()
        await session.commit()
        await session.refresh(sf)

        return {
            "id": sf.id,
            "nombre": sf.nombre,
            "filtros": sf.filtros,
            "alertas_activas": sf.alertas_activas,
            "frecuencia": sf.frecuencia,
            "creado_en": sf.creado_en,
            "actualizado_en": sf.actualizado_en,
            "coincidencias_actuales": 0,
            "total_alertas_enviadas": 0
        }


@router.delete("/filters/{filter_id}")
async def delete_saved_filter(
    filter_id: int,
    current_user: UserModel = Depends(get_current_user)
):
    """Elimina permanentemente un filtro guardado y sus registros de alertas."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(SavedFilterModel)
            .where(SavedFilterModel.id == filter_id, SavedFilterModel.user_id == current_user.id)
        )
        sf = res.scalar_one_or_none()

        if not sf:
            raise HTTPException(status_code=404, detail="Filtro no encontrado o sin permisos.")

        await session.delete(sf)
        await session.commit()

        return {"message": f"Filtro '{sf.nombre}' eliminado correctamente."}


@router.get("/alerts/history")
async def get_alerts_history(
    limit: int = 20,
    current_user: UserModel = Depends(get_current_user)
):
    """Retorna las últimas alertas generadas y notificadas al usuario."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AlertLogModel, TenderModel, SavedFilterModel)
            .join(TenderModel, AlertLogModel.ocid == TenderModel.ocid)
            .join(SavedFilterModel, AlertLogModel.saved_filter_id == SavedFilterModel.id)
            .where(AlertLogModel.user_id == current_user.id)
            .order_by(desc(AlertLogModel.enviado_en))
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()

        history = []
        for log, tender, sfilter in rows:
            raw = tender.raw_payload if isinstance(tender.raw_payload, dict) else {}
            history.append({
                "alert_id": log.id,
                "filtro_nombre": sfilter.nombre,
                "ocid": tender.ocid,
                "codigo_seace": tender.titulo or tender.id_proceso,
                "entidad": extract_entidad(raw),
                "rubro": tender.rubro,
                "objeto": tender.descripcion_limpia or tender.descripcion or tender.titulo,
                "monto_estimado": float(tender.monto_estimado or 0),
                "enviado_en": log.enviado_en.isoformat(),
            })

        return history


@router.post("/alerts/test")
async def send_test_alert(
    current_user: UserModel = Depends(get_current_user)
):
    """Envía un correo de prueba de alerta al usuario autenticado."""
    from services.mailer import send_test_alert_email
    res = await send_test_alert_email(
        to_email=current_user.email,
        user_nombre=current_user.nombre or "Usuario LicitLens"
    )
    return res

