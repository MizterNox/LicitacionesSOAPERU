import sys
import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, desc

from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Asegurar resolución de rutas relativas y absolutas
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
backend_dir = os.path.dirname(src_dir)
for p in [src_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from database import AsyncSessionLocal, engine, Base
from models.tenders import TenderModel
from models.cron_log import CronExecutionModel
from models.settings import AppSettingModel
from etl.extractor import OCESCExtractor
from etl.loader import ELTOrchestrator
from services.search import TenderFilters, build_search_query, get_search_suggestions
from services.ai_enricher import RUBROS_VALIDOS
from services.alert_matcher import run_alert_matching
from schemas.ocds_schema import (
    extract_entidad_info,
    extract_region_info,
    extract_tipo_proceso_real,
    extract_fecha_limite_real,
    extract_items_normalized,
    extract_documents_normalized,
    is_menor_cuantia,
)
from api.routers.export import router as export_router
from api.routers.metrics import router as metrics_router
from api.routers.auth import router as auth_router
from api.routers.saved_filters import router as saved_filters_router
from config import settings

API_URL = settings.API_URL

DEFAULT_TIPOS = ["Servicios"]

# Lock asíncrono para evitar ejecuciones concurrentes del pipeline ETL
_etl_lock = asyncio.Lock()

async def get_active_tipos() -> List[str]:
    """Obtiene la lista de tipos de licitación configurados por el usuario."""
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(AppSettingModel).where(AppSettingModel.clave == "tipos_activos"))
            setting = res.scalar_one_or_none()
            if setting and isinstance(setting.valor, list) and len(setting.valor) > 0:
                return setting.valor
    except Exception as e:
        print(f"[SETTINGS] Error al consultar tipos_activos: {e}")
    return DEFAULT_TIPOS

async def set_active_tipos(tipos: List[str]) -> List[str]:
    """Guarda la lista de tipos de licitación habilitados."""
    valid_tipos = [t for t in tipos if t in ["Servicios", "Bienes", "Obras"]]
    if not valid_tipos:
        valid_tipos = DEFAULT_TIPOS
    async with AsyncSessionLocal() as session:
        async with session.begin():
            res = await session.execute(select(AppSettingModel).where(AppSettingModel.clave == "tipos_activos"))
            setting = res.scalar_one_or_none()
            if setting:
                setting.valor = valid_tipos
                setting.actualizado_en = datetime.now()
            else:
                session.add(AppSettingModel(clave="tipos_activos", valor=valid_tipos))
    return valid_tipos

# Estado en memoria para monitoreo inmediato
ultimo_estado_etl = {
    "status": "idle",
    "ultima_ejecucion": None,
    "resultado": None,
    "error": None
}

scheduler = AsyncIOScheduler()

async def job_etl_programado():
    """Tarea ejecutada automáticamente por el programador APScheduler de forma dinámica."""
    global ultimo_estado_etl
    if _etl_lock.locked():
        print("[SCHEDULER] ETL ya en ejecución por otra tarea, se omite este ciclo.")
        return

    async with _etl_lock:
        now = datetime.now()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        print(f"\n=======================================================")
        print(f"[SCHEDULER] ¡Ejecución automática del ETL iniciada! ({now_str})")
        print(f"=======================================================")

        tipos_a_ejecutar = await get_active_tipos()
        print(f"[SCHEDULER] Tipos configurados activos: {tipos_a_ejecutar}")

        cron_entry_id = None
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    entry = CronExecutionModel(
                        iniciado_en=now,
                        tipo_ejecucion="AUTOMATICO",
                        estado="RUNNING",
                        objetos_procesados=tipos_a_ejecutar
                    )
                    session.add(entry)
                    await session.flush()
                    cron_entry_id = entry.id
        except Exception as e_log:
            print(f"[SCHEDULER] Error al registrar inicio de cron: {e_log}")

        ultimo_estado_etl["status"] = "running"
        ultimo_estado_etl["ultima_ejecucion"] = datetime.now().isoformat()
        ultimo_estado_etl["error"] = None

        extractor = OCESCExtractor(API_URL)
        orchestrator = ELTOrchestrator(extractor)

        total_extraidos_gen = 0
        total_guardados_gen = 0
        total_ignorados_gen = 0
        nuevos_ocids_gen = []
        detalles_por_tipo = {}
        error_str = None

        try:
            for obj in tipos_a_ejecutar:
                try:
                    print(f"[SCHEDULER] Extrayendo {obj} con fecha_desde={hoy_str}...")
                    res = await orchestrator.run_pipeline(
                        objeto=obj,
                        estado="Vigente",
                        fecha_desde=hoy_str,
                        max_pages=2
                    )
                    ext = res.get("total_extraidos", 0)
                    guardados = res.get("total_guardados_db", 0)
                    ignorados = res.get("total_ignorados", 0)
                    nuevos_tipo = res.get("nuevos_ocids", [])
                    nuevos_ocids_gen.extend(nuevos_tipo)
                    total_extraidos_gen += ext
                    total_guardados_gen += guardados
                    total_ignorados_gen += ignorados
                    detalles_por_tipo[obj] = res
                    print(f"[SCHEDULER] -> {obj}: {guardados} persistidos/actualizados ({len(nuevos_tipo)} nuevos), {ignorados} no sobreescritos")
                except Exception as e_obj:
                    print(f"[SCHEDULER] Error al procesar {obj}: {e_obj}")
                    detalles_por_tipo[obj] = {"error": str(e_obj)}

            # Cruce automático de alertas para las convocatorias nuevas
            alertas_resultado = None
            if nuevos_ocids_gen:
                print(f"[SCHEDULER] Ejecutando cruce de alertas para {len(nuevos_ocids_gen)} nuevas convocatorias...")
                try:
                    alertas_resultado = await run_alert_matching(nuevos_ocids=nuevos_ocids_gen)
                    detalles_por_tipo["alertas"] = alertas_resultado
                    print(f"[SCHEDULER] Cruce de alertas finalizado: {alertas_resultado.get('total_coincidencias', 0)} coincidencias, {alertas_resultado.get('alertas_registradas', 0)} registradas.")
                except Exception as e_alert:
                    print(f"[SCHEDULER WARN] Error en cruce de alertas: {e_alert}")
                    detalles_por_tipo["alertas"] = {"error": str(e_alert)}

            estado_final = "COMPLETED"
            ultimo_estado_etl["status"] = "completed"
            ultimo_estado_etl["resultado"] = {
                "mensaje": f"ETL automático finalizado. Total guardados: {total_guardados_gen}, No sobreescritos: {total_ignorados_gen}",
                "fecha": hoy_str,
                "tipos": tipos_a_ejecutar,
                "alertas": alertas_resultado
            }
            print(f"[SCHEDULER] Fin de ejecución programada. Total guardados: {total_guardados_gen}, No sobreescritos: {total_ignorados_gen}\n")
        except Exception as exc:
            estado_final = "FAILED"
            error_str = str(exc)
            ultimo_estado_etl["status"] = "failed"
            ultimo_estado_etl["error"] = error_str
            print(f"[SCHEDULER ERROR]: {exc}\n")

        # Persistir finalización en cron_executions
        try:
            if cron_entry_id:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        res = await session.execute(select(CronExecutionModel).where(CronExecutionModel.id == cron_entry_id))
                        entry = res.scalar_one_or_none()
                        if entry:
                            entry.finalizado_en = datetime.now()
                            entry.estado = estado_final
                            entry.total_extraidos = total_extraidos_gen
                            entry.total_guardados = total_guardados_gen
                            entry.total_ignorados = total_ignorados_gen
                            entry.detalles = detalles_por_tipo
                            entry.error = error_str
        except Exception as e_upd:
            print(f"[SCHEDULER] Error al actualizar log de cron en BD: {e_upd}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verificar conectividad con PostgreSQL
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("[FASTAPI LIFESPAN] Conexión a Base de Datos PostgreSQL verificada correctamente.")
    except Exception as e:
        print(f"[FASTAPI LIFESPAN ERROR] Error al conectar con la base de datos: {e}")

    # 1. Monitoreo frecuente en horario de oficina (8am - 6pm cada 2h) para capturar contrataciones menores
    scheduler.add_job(job_etl_programado, 'cron', day_of_week='mon-sat', hour='8,10,12,14,16,18', minute=0, id='job_diurno')
    # 2. Rutina de Noche / Madrugada (02:00 AM) - Consolida todo el día anterior
    scheduler.add_job(job_etl_programado, 'cron', hour=2, minute=0, id='job_noche')

    scheduler.start()
    print("\n[FASTAPI LIFESPAN] APScheduler iniciado automáticamente en segundo plano.")
    print("[FASTAPI LIFESPAN] Horarios programados:")
    print("  -> Horario Hábil (Lun-Sáb): 08:00, 10:00, 12:00, 14:00, 16:00, 18:00")
    print("  -> Turno Noche (Consolidación): 02:00 AM\n")
    yield
    scheduler.shutdown()
    print("[FASTAPI LIFESPAN] APScheduler detenido.")

app = FastAPI(
    title="Licitaciones Engine API (OECE / SEACE)",
    version="1.2.0",
    description="Backend API para extracción ETL de compras públicas del Perú y consumo desde el Frontend.",
    lifespan=lifespan
)

# Habilitar CORS para permitir llamadas desde el Frontend (React en http://localhost:5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class ETLConfigRequest(BaseModel):
    """Esquema de configuración enviado desde el Frontend."""
    objeto: str = Field(default="Servicios", description="Objeto de contratación: 'Servicios', 'Bienes', 'Obras', 'Todos'")
    estado: str = Field(default="Vigente", description="Filtro de estado: 'Vigente' o 'Todos'")
    fecha_desde: Optional[str] = Field(default=None, description="Fecha de inicio (YYYY-MM-DD). Por defecto hoy.")
    fecha_hasta: Optional[str] = Field(default=None, description="Fecha de fin (YYYY-MM-DD). Por defecto hoy.")
    dias_atras: Optional[int] = Field(default=0, description="Días hacia atrás a partir de hoy (ej. 7, 15, 30). Si se especifica, calcula fecha_desde automáticamente.")
    max_pages: int = Field(default=1, ge=1, le=20, description="Número de páginas a extraer (20 registros por página).")

async def ejecutar_etl_task(config: ETLConfigRequest):
    """Función de ejecución del pipeline orquestado."""
    global ultimo_estado_etl
    if _etl_lock.locked():
        print("[ETL TASK] Pipeline ya en ejecución, se omite nueva llamada en segundo plano.")
        return

    async with _etl_lock:
        ultimo_estado_etl["status"] = "running"
        ultimo_estado_etl["ultima_ejecucion"] = datetime.now().isoformat()
        ultimo_estado_etl["error"] = None

        now = datetime.now()
        cron_entry_id = None
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    entry = CronExecutionModel(
                        iniciado_en=now,
                        tipo_ejecucion="MANUAL",
                        estado="RUNNING",
                        objetos_procesados=[config.objeto]
                    )
                    session.add(entry)
                    await session.flush()
                    cron_entry_id = entry.id
        except Exception as e_log:
            print(f"[MANUAL RUN] Error al registrar inicio de ejecución: {e_log}")

        try:
            extractor = OCESCExtractor(API_URL)
            orchestrator = ELTOrchestrator(extractor)

            hoy = datetime.now()
            f_hasta = config.fecha_hasta if config.fecha_hasta and config.fecha_hasta.strip().lower() not in ["string", "null", "none", ""] else None
            f_desde = config.fecha_desde if config.fecha_desde and config.fecha_desde.strip().lower() not in ["string", "null", "none", ""] else None

            fecha_fin = f_hasta or hoy.strftime("%Y-%m-%d")

            if config.dias_atras and config.dias_atras > 0:
                fecha_inicio = (hoy - timedelta(days=config.dias_atras)).strftime("%Y-%m-%d")
            else:
                fecha_inicio = f_desde or hoy.strftime("%Y-%m-%d")

            resultado = await orchestrator.run_pipeline(
                objeto=config.objeto,
                estado=config.estado,
                fecha_desde=fecha_inicio,
                fecha_hasta=fecha_fin,
                max_pages=config.max_pages
            )

            # Cruce automático de alertas para las convocatorias nuevas extraídas
            nuevos = resultado.get("nuevos_ocids", [])
            if nuevos:
                print(f"[MANUAL RUN] Ejecutando cruce de alertas para {len(nuevos)} convocatorias...")
                try:
                    alertas_res = await run_alert_matching(nuevos_ocids=nuevos)
                    resultado["alertas"] = alertas_res
                    print(f"[MANUAL RUN] Cruce de alertas finalizado: {alertas_res.get('total_coincidencias', 0)} coincidencias.")
                except Exception as e_alert:
                    print(f"[MANUAL RUN WARN] Error en cruce de alertas: {e_alert}")
                    resultado["alertas"] = {"error": str(e_alert)}

            ultimo_estado_etl["status"] = "completed"
            ultimo_estado_etl["resultado"] = resultado

            if cron_entry_id:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        res = await session.execute(select(CronExecutionModel).where(CronExecutionModel.id == cron_entry_id))
                        entry = res.scalar_one_or_none()
                        if entry:
                            entry.finalizado_en = datetime.now()
                            entry.estado = "COMPLETED"
                            entry.total_extraidos = resultado.get("total_extraidos", 0)
                            entry.total_guardados = resultado.get("total_guardados_db", 0)
                            entry.total_ignorados = resultado.get("total_ignorados", 0)
                            entry.detalles = resultado
        except Exception as exc:
            ultimo_estado_etl["status"] = "failed"
            ultimo_estado_etl["error"] = str(exc)
            print(f"[ERROR ETL BACKGROUND]: {exc}")
            if cron_entry_id:
                try:
                    async with AsyncSessionLocal() as session:
                        async with session.begin():
                            res = await session.execute(select(CronExecutionModel).where(CronExecutionModel.id == cron_entry_id))
                            entry = res.scalar_one_or_none()
                            if entry:
                                entry.finalizado_en = datetime.now()
                                entry.estado = "FAILED"
                                entry.error = str(exc)
                except Exception:
                    pass

@app.get("/api/v1/health")
async def health_check():
    """Health check del backend y validación de base de datos."""
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(func.count(TenderModel.ocid)))
            db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy",
        "database_connected": db_ok,
        "timestamp": datetime.now().isoformat()
    }

# =========================================================================
# FUNCIONES AUXILIARES PARA NORMALIZACIÓN DE DATOS HACIA REACT
# =========================================================================

def extract_tipo_proceso(titulo: Optional[str]) -> str:
    if not titulo:
        return "CP"
    t = titulo.strip().upper()
    for prefix in ["CP", "LP", "AS", "MS", "MC"]:
        if t.startswith(prefix):
            return prefix
    if "DIRECTA" in t:
        return "AS"
    parts = t.split("-")
    if len(parts) > 0 and parts[0]:
        return parts[0][:4]
    return "CP"

def extract_entidad(raw_payload: Any) -> str:
    if not isinstance(raw_payload, dict):
        return "Entidad del Estado"
    buyer = raw_payload.get("buyer")
    if isinstance(buyer, dict) and buyer.get("name"):
        return buyer.get("name")
    tender = raw_payload.get("tender")
    if isinstance(tender, dict):
        pe = tender.get("procuringEntity")
        if isinstance(pe, dict) and pe.get("name"):
            return pe.get("name")
    parties = raw_payload.get("parties", [])
    if isinstance(parties, list):
        for p in parties:
            if isinstance(p, dict) and any(r in ["buyer", "procuringEntity"] for r in p.get("roles", [])):
                if p.get("name"):
                    return p.get("name")
    return "Municipalidad / Entidad Pública"

def extract_region(raw_payload: Any, desc: str = "") -> str:
    regiones_peru = [
        "Lima", "Arequipa", "Cusco", "Piura", "La Libertad", "Lambayeque", "Junín",
        "Áncash", "Ica", "Loreto", "San Martín", "Cajamarca", "Puno", "Ucayali",
        "Ayacucho", "Huánuco", "Tacna", "Madre de Dios", "Moquegua", "Amazonas",
        "Apurímac", "Huancavelica", "Pasco", "Tumbes"
    ]
    if isinstance(raw_payload, dict):
        parties = raw_payload.get("parties", [])
        if isinstance(parties, list):
            for p in parties:
                addr = p.get("address", {})
                if isinstance(addr, dict):
                    loc = addr.get("region") or addr.get("locality")
                    if loc:
                        return loc
        text_all = f"{desc} {raw_payload.get('tender', {}).get('title', '')}"
        for r in regiones_peru:
            if r.lower() in text_all.lower():
                return r
    return "Lima"

def extract_fecha_limite(raw_payload: Any, fecha_lanzamiento: Optional[datetime]) -> str:
    pub_str = fecha_lanzamiento.strftime("%Y-%m-%d") if fecha_lanzamiento else ""
    if isinstance(raw_payload, dict):
        tender = raw_payload.get("tender", {})
        tp = tender.get("tenderPeriod", {})
        tp_end = (tp.get("endDate") or "")[:10]
        # En la API del OECE, tenderPeriod.endDate suele ser idéntico al día de publicación
        # para marcar el evento de convocatoria. Solo es fecha límite si es posterior a la publicación.
        if tp_end and tp_end > pub_str:
            return tp_end
        
        ep = tender.get("enquiryPeriod", {})
        ep_end = (ep.get("endDate") or "")[:10]
        if ep_end and ep_end >= pub_str:
            # En el SEACE la presentación de ofertas ocurre posterior al fin de consultas
            try:
                dt_ep = datetime.fromisoformat(ep_end)
                return (dt_ep + timedelta(days=7)).strftime("%Y-%m-%d")
            except ValueError:
                return ep_end

    if fecha_lanzamiento:
        return (fecha_lanzamiento + timedelta(days=15)).strftime("%Y-%m-%d")
    return ""

# =========================================================================
# ENDPOINT PRINCIPAL REQUERIDO POR EL FRONTEND: @app.get("/api/licitaciones")
# =========================================================================

@app.get("/api/licitaciones")
async def get_licitaciones(
    vigentes: Optional[bool] = Query(default=True, description="Filtrar solo convocatorias activas/vigentes"),
    fecha: Optional[str] = Query(default="todos", description="'hoy' para fecha actual, 'todos' para omitir filtro de fecha, o YYYY-MM-DD"),
    tipo: Optional[str] = Query(default="todos", description="Objeto contractual: 'Bienes', 'Servicios', 'Obras' o 'todos'"),
    search: Optional[str] = Query(default=None, description="Búsqueda por texto en código SEACE, título o descripción"),
    q: Optional[str] = Query(default=None, description="Término de búsqueda Full-Text Search (FTS)"),
    rubro: Optional[str] = Query(default=None, description="Rubro normalizado por IA"),
    region: Optional[str] = Query(default=None, description="Región geográfica"),
    entidad: Optional[str] = Query(default=None, description="Entidad compradora"),
    tipo_proceso: Optional[str] = Query(default=None, description="Tipo de proceso: MC, AS, SIE, CP, LP"),
    solo_menores: Optional[bool] = Query(default=None, description="Filtrar solo contrataciones menores (<= 8 UIT)"),
    plazo: Optional[str] = Query(default=None, description="Filtro de plazo restante: '48h', '7d', '30d'"),
    monto_min: Optional[float] = Query(default=None, description="Monto estimado mínimo"),
    monto_max: Optional[float] = Query(default=None, description="Monto estimado máximo"),
    fecha_desde: Optional[str] = Query(default=None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_hasta: Optional[str] = Query(default=None, description="Fecha de fin (YYYY-MM-DD)"),
    sort: Optional[str] = Query(default="relevance", description="'relevance', 'date', 'value', 'deadline', 'match'"),
    limit: int = Query(default=100, ge=1, le=5000),
    offset: int = Query(default=0, ge=0)
):
    """
    Endpoint principal para el Frontend React:
    Retorna los procesos de licitación almacenados en PostgreSQL optimizados con Full-Text Search,
    ponderaciones (A=título, B=descripción limpia, C=rubro) y ranking por relevancia.
    """
    query_text = (q or search or "").strip() or None

    filter_params = TenderFilters(
        q=query_text,
        vigentes=vigentes,
        tipo=tipo,
        rubro=rubro,
        region=region,
        entidad=entidad,
        tipo_proceso=tipo_proceso,
        solo_menores=solo_menores,
        monto_min=monto_min,
        monto_max=monto_max,
        fecha=fecha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        plazo=plazo,
        sort=sort or "relevance",
        limit=limit,
        offset=offset
    )

    async with AsyncSessionLocal() as session:
        query, _ = build_search_query(filter_params)
        result = await session.execute(query)
        rows = result.scalars().all()

        formatted = []
        for idx, t in enumerate(rows, start=1):
            raw = t.raw_payload if isinstance(t.raw_payload, dict) else {}
            desc_text = t.descripcion_limpia or t.descripcion or t.titulo or "Sin descripción"
            entidad = t.entidad_nombre or extract_entidad(raw)
            region_val = t.region or extract_region(raw, desc_text)
            f_lim_obj = extract_fecha_limite_real(raw, t.fecha_lanzamiento)
            f_limite = t.fecha_limite or f_lim_obj.get("fecha_limite")
            f_pub = t.fecha_lanzamiento.strftime("%Y-%m-%d") if t.fecha_lanzamiento else datetime.now().strftime("%Y-%m-%d")
            proc_tipo = t.tipo_proceso or extract_tipo_proceso_real(t.titulo, raw)
            es_menor = t.es_menor_cuantia if t.es_menor_cuantia is not None else is_menor_cuantia(float(t.monto_estimado or 0), proc_tipo)

            hitos = [
                {"nombre": "Convocatoria publicada", "fecha": f_pub},
                {"nombre": "Formulación de consultas", "fecha": f_pub},
                {"nombre": "Presentación de ofertas", "fecha": f_limite or f_pub},
                {"nombre": "Apertura de ofertas", "fecha": f_limite or f_pub}
            ]

            documentos = extract_documents_normalized(raw)
            items = extract_items_normalized(raw)

            motivos_ia = [
                f"Proceso de {t.objeto_contratacion} registrado en SEACE",
                f"Entidad compradora: {entidad}",
                f"Monto estimado de S/ {float(t.monto_estimado or 0):,.2f}"
            ]
            if es_menor:
                motivos_ia.insert(0, "Contratación de Menor Cuantía (≤ 8 UIT)")
            if t.rubro:
                motivos_ia.insert(0, f"Rubro identificado por IA: {t.rubro}")

            # Match score determinístico basado en calidad y relevancia
            base_score = 70
            if t.rubro_confianza:
                base_score += int(float(t.rubro_confianza) * 15)
            if t.monto_estimado and t.monto_estimado > 0:
                base_score += 5
            if f_limite:
                base_score += 5
            if es_menor:
                base_score += 5
            match_score = min(100, max(50, base_score))

            formatted.append({
                "id": t.ocid,
                "ocid": t.ocid,
                "codigo_seace": t.titulo or t.id_proceso,
                "entidad": entidad,
                "entidad_ruc": t.entidad_ruc or "",
                "objeto": desc_text,
                "descripcion_limpia": t.descripcion_limpia or desc_text,
                "descripcion_original": t.descripcion or t.titulo or "",
                "rubro": t.rubro or "Servicios Generales",
                "rubro_confianza": float(t.rubro_confianza) if t.rubro_confianza is not None else None,
                "palabras_clave": t.palabras_clave or [],
                "ia_estado": t.ia_estado or "PENDIENTE",
                "tipo_objeto": t.objeto_contratacion or "Servicios",
                "estado": t.estado or "Vigente",
                "fecha_publicacion": f_pub,
                "fecha_limite": f_limite,
                "valor_estimado": float(t.monto_estimado) if t.monto_estimado is not None else 0.0,
                "moneda": t.moneda or "PEN",
                "region": region_val,
                "modalidad": t.titulo.split("-")[0] if t.titulo else "CP",
                "tipo_proceso": proc_tipo,
                "es_menor_cuantia": es_menor,
                "cui": t.cui or t.id_proceso or "",
                "match_score": match_score,
                "fase_actual": 2,
                "hitos": hitos,
                "documentos": documentos,
                "items": items,
                "motivos_ia": motivos_ia,
                "raw_payload": raw
            })

        return formatted
    
# Montar router de exportación CSV / XLSX antes de la ruta parametrizada /{ocid}
app.include_router(export_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(saved_filters_router)

@app.get("/api/licitaciones/{ocid}")
async def get_licitacion_by_ocid(ocid: str):
    """Retorna el detalle completo de una licitación por su OCID."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(TenderModel).where(TenderModel.ocid == ocid))
        t = res.scalar_one_or_none()
        if not t:
            raise HTTPException(status_code=404, detail="Licitación no encontrada")

        raw = t.raw_payload if isinstance(t.raw_payload, dict) else {}
        desc_text = t.descripcion_limpia or t.descripcion or t.titulo or "Sin descripción"
        entidad = t.entidad_nombre or extract_entidad(raw)
        region_val = t.region or extract_region(raw, desc_text)
        f_pub = t.fecha_lanzamiento.strftime("%Y-%m-%d") if t.fecha_lanzamiento else ""
        f_lim_obj = extract_fecha_limite_real(raw, t.fecha_lanzamiento)
        f_limite = t.fecha_limite or f_lim_obj.get("fecha_limite")
        proc_tipo = t.tipo_proceso or extract_tipo_proceso_real(t.titulo, raw)
        es_menor = t.es_menor_cuantia if t.es_menor_cuantia is not None else is_menor_cuantia(float(t.monto_estimado or 0), proc_tipo)

        documentos = extract_documents_normalized(raw)
        items = extract_items_normalized(raw)

        hitos = [
            {"nombre": "Convocatoria publicada", "fecha": f_pub},
            {"nombre": "Formulación de consultas", "fecha": f_pub},
            {"nombre": "Presentación de ofertas", "fecha": f_limite or f_pub},
            {"nombre": "Apertura de ofertas", "fecha": f_limite or f_pub}
        ]

        motivos_ia = [
            f"Proceso de {t.objeto_contratacion} registrado en SEACE",
            f"Entidad compradora: {entidad}",
            f"Monto estimado de S/ {float(t.monto_estimado or 0):,.2f}"
        ]
        if es_menor:
            motivos_ia.insert(0, "Contratación de Menor Cuantía (≤ 8 UIT)")
        if t.rubro:
            motivos_ia.insert(0, f"Rubro identificado por IA: {t.rubro}")

        base_score = 70
        if t.rubro_confianza:
            base_score += int(float(t.rubro_confianza) * 15)
        if t.monto_estimado and t.monto_estimado > 0:
            base_score += 5
        if f_limite:
            base_score += 5
        if es_menor:
            base_score += 5
        match_score = min(100, max(50, base_score))

        return {
            "id": t.ocid,
            "ocid": t.ocid,
            "codigo_seace": t.titulo or t.id_proceso,
            "entidad": entidad,
            "entidad_ruc": t.entidad_ruc or "",
            "objeto": desc_text,
            "descripcion_limpia": t.descripcion_limpia or desc_text,
            "descripcion_original": t.descripcion or t.titulo or "",
            "rubro": t.rubro or "Servicios Generales",
            "rubro_confianza": float(t.rubro_confianza) if t.rubro_confianza is not None else None,
            "palabras_clave": t.palabras_clave or [],
            "ia_estado": t.ia_estado or "PENDIENTE",
            "tipo_objeto": t.objeto_contratacion or "Servicios",
            "estado": t.estado or "Vigente",
            "fecha_publicacion": f_pub,
            "fecha_limite": f_limite,
            "valor_estimado": float(t.monto_estimado) if t.monto_estimado is not None else 0.0,
            "moneda": t.moneda or "PEN",
            "region": region_val,
            "modalidad": t.titulo.split("-")[0] if t.titulo else "CP",
            "tipo_proceso": proc_tipo,
            "es_menor_cuantia": es_menor,
            "cui": t.cui or t.id_proceso or "",
            "match_score": match_score,
            "fase_actual": 2,
            "hitos": hitos,
            "documentos": documentos,
            "items": items,
            "motivos_ia": motivos_ia,
            "raw_payload": raw
        }

@app.get("/api/v1/search/suggest")
async def get_search_autocomplete(q: str = Query(..., min_length=2, description="Término de búsqueda")):
    """Sugerencias de autocompletado en tiempo real para la barra de búsqueda."""
    async with AsyncSessionLocal() as session:
        return await get_search_suggestions(session, q)

@app.get("/api/v1/rubros")
async def get_rubros():
    """Retorna la lista de rubros disponibles con el conteo de convocatorias en base de datos."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TenderModel.rubro, func.count(TenderModel.ocid))
            .where(TenderModel.rubro.isnot(None))
            .group_by(TenderModel.rubro)
            .order_by(desc(func.count(TenderModel.ocid)))
        )
        res = await session.execute(stmt)
        counts = {r[0]: r[1] for r in res.all()}

        items = []
        for rubro in RUBROS_VALIDOS:
            items.append({
                "id": rubro,
                "label": rubro,
                "total": counts.get(rubro, 0)
            })
        return items

@app.get("/api/v1/etl/config-options")
async def get_config_options():
    hoy = datetime.now()
    hoy_str = hoy.strftime("%Y-%m-%d")

    return {
        "objetos_contratacion": [
            {"id": "Servicios", "label": "Servicios (y Consultorías)"},
            {"id": "Bienes", "label": "Bienes"},
            {"id": "Obras", "label": "Obras"},
            {"id": "Todos", "label": "Todos los Objetos"}
        ],
        "estados_disponibles": [
            {"id": "Vigente", "label": "Vigente (Convocado / En Proceso)"},
            {"id": "Todos", "label": "Todos los Estados"}
        ],
        "fecha_defecto_hoy": hoy_str,
        "rangos_hacia_atras": [
            {"label": "Solo hoy", "dias": 0, "fecha_desde": hoy_str, "fecha_hasta": hoy_str},
            {"label": "Últimos 7 días", "dias": 7, "fecha_desde": (hoy - timedelta(days=7)).strftime("%Y-%m-%d"), "fecha_hasta": hoy_str},
            {"label": "Últimos 15 días", "dias": 15, "fecha_desde": (hoy - timedelta(days=15)).strftime("%Y-%m-%d"), "fecha_hasta": hoy_str},
            {"label": "Últimos 30 días", "dias": 30, "fecha_desde": (hoy - timedelta(days=30)).strftime("%Y-%m-%d"), "fecha_hasta": hoy_str}
        ]
    }

@app.get("/api/v1/etl/status")
async def get_etl_status():
    return ultimo_estado_etl

@app.post("/api/v1/etl/trigger")
async def trigger_etl(
    config: ETLConfigRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(default=False)
):
    if _etl_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Hay una ejecución del pipeline ETL en curso. Por favor espere a que finalice."
        )

    hoy = datetime.now()
    f_hasta = config.fecha_hasta if config.fecha_hasta and config.fecha_hasta.strip().lower() not in ["string", "null", "none", ""] else None
    f_desde = config.fecha_desde if config.fecha_desde and config.fecha_desde.strip().lower() not in ["string", "null", "none", ""] else None

    fecha_fin = f_hasta or hoy.strftime("%Y-%m-%d")
    if config.dias_atras and config.dias_atras > 0:
        fecha_inicio = (hoy - timedelta(days=config.dias_atras)).strftime("%Y-%m-%d")
    else:
        fecha_inicio = f_desde or hoy.strftime("%Y-%m-%d")

    config_calculada = {
        "objeto": config.objeto,
        "estado": config.estado,
        "fecha_desde": fecha_inicio,
        "fecha_hasta": fecha_fin,
        "max_pages": config.max_pages
    }

    if sync:
        async with _etl_lock:
            now = datetime.now()
            cron_entry_id = None
            try:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        entry = CronExecutionModel(
                            iniciado_en=now,
                            tipo_ejecucion="MANUAL_SYNC",
                            estado="RUNNING",
                            objetos_procesados=[config.objeto]
                        )
                        session.add(entry)
                        await session.flush()
                        cron_entry_id = entry.id
            except Exception as e_log:
                print(f"[MANUAL SYNC] Error al registrar inicio de ejecución: {e_log}")

            try:
                extractor = OCESCExtractor(API_URL)
                orchestrator = ELTOrchestrator(extractor)
                resultado = await orchestrator.run_pipeline(
                    objeto=config.objeto,
                    estado=config.estado,
                    fecha_desde=fecha_inicio,
                    fecha_hasta=fecha_fin,
                    max_pages=config.max_pages
                )

                # Cruce de alertas para convocatorias nuevas
                nuevos = resultado.get("nuevos_ocids", [])
                if nuevos:
                    try:
                        alertas_res = await run_alert_matching(nuevos_ocids=nuevos)
                        resultado["alertas"] = alertas_res
                    except Exception as e_alert:
                        resultado["alertas"] = {"error": str(e_alert)}

                if cron_entry_id:
                    async with AsyncSessionLocal() as session:
                        async with session.begin():
                            res = await session.execute(select(CronExecutionModel).where(CronExecutionModel.id == cron_entry_id))
                            entry = res.scalar_one_or_none()
                            if entry:
                                entry.finalizado_en = datetime.now()
                                entry.estado = "COMPLETED"
                                entry.total_extraidos = resultado.get("total_extraidos", 0)
                                entry.total_guardados = resultado.get("total_guardados_db", 0)
                                entry.total_ignorados = resultado.get("total_ignorados", 0)
                                entry.detalles = resultado

                return {"status": "success", "mode": "sync", "resultado": resultado}
            except Exception as e:
                if cron_entry_id:
                    try:
                        async with AsyncSessionLocal() as session:
                            async with session.begin():
                                res = await session.execute(select(CronExecutionModel).where(CronExecutionModel.id == cron_entry_id))
                                entry = res.scalar_one_or_none()
                                if entry:
                                    entry.finalizado_en = datetime.now()
                                    entry.estado = "FAILED"
                                    entry.error = str(e)
                    except Exception:
                        pass
                raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(ejecutar_etl_task, config)

    return {
        "status": "accepted",
        "message": "Pipeline ETL encolado exitosamente en segundo plano.",
        "config_aplicada": config_calculada
    }

# =========================================================================
# ENDPOINTS PARA MONITOREO DE CRON Y CONFIGURACIÓN DE TIPOS
# =========================================================================

class TiposConfigRequest(BaseModel):
    tipos_activos: List[str] = Field(default=["Servicios", "Bienes", "Obras"], description="Lista de tipos activos: 'Servicios', 'Bienes', 'Obras'")

@app.get("/api/v1/cron/status")
async def get_cron_status():
    """
    Retorna la información de la última ejecución del cron registrada en base de datos,
    los próximos horarios programados y los tipos de contratación activos.
    """
    last_exec = None
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(CronExecutionModel).order_by(desc(CronExecutionModel.iniciado_en)).limit(1)
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if record:
                duracion_seg = None
                if record.finalizado_en and record.iniciado_en:
                    duracion_seg = round((record.finalizado_en - record.iniciado_en).total_seconds(), 2)

                last_exec = {
                    "id": record.id,
                    "iniciado_en": record.iniciado_en.isoformat(),
                    "finalizado_en": record.finalizado_en.isoformat() if record.finalizado_en else None,
                    "tipo_ejecucion": record.tipo_ejecucion,
                    "estado": record.estado,
                    "objetos_procesados": record.objetos_procesados or [],
                    "total_extraidos": record.total_extraidos or 0,
                    "total_guardados": record.total_guardados or 0,
                    "total_ignorados": record.total_ignorados or 0,
                    "duracion_segundos": duracion_seg,
                    "error": record.error
                }
    except Exception as e_status:
        print(f"[CRON STATUS ERROR]: {e_status}")

    tipos_activos = await get_active_tipos()

    return {
        "status": "ok",
        "scheduler_activo": scheduler.running,
        "horarios_programados": [
            "08:00, 10:00, 12:00, 14:00, 16:00, 18:00 (Lun-Sáb)",
            "02:00 AM (Consolidación diaria)"
        ],
        "tipos_activos": tipos_activos,
        "ultima_ejecucion": last_exec,
        "memoria_status": ultimo_estado_etl
    }

@app.get("/api/v1/cron/history")
async def get_cron_history(limit: int = Query(default=15, ge=1, le=50)):
    """Retorna el historial de ejecuciones del cron y sincronizaciones manuales."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(CronExecutionModel).order_by(desc(CronExecutionModel.iniciado_en)).limit(limit)
            res = await session.execute(stmt)
            records = res.scalars().all()

            history = []
            for r in records:
                duracion = None
                if r.finalizado_en and r.iniciado_en:
                    duracion = round((r.finalizado_en - r.iniciado_en).total_seconds(), 2)

                history.append({
                    "id": r.id,
                    "iniciado_en": r.iniciado_en.isoformat(),
                    "finalizado_en": r.finalizado_en.isoformat() if r.finalizado_en else None,
                    "tipo_ejecucion": r.tipo_ejecucion,
                    "estado": r.estado,
                    "objetos_procesados": r.objetos_procesados or [],
                    "total_extraidos": r.total_extraidos or 0,
                    "total_guardados": r.total_guardados or 0,
                    "total_ignorados": r.total_ignorados or 0,
                    "duracion_segundos": duracion,
                    "error": r.error
                })

            return history
    except Exception as e_hist:
        print(f"[CRON HISTORY ERROR]: {e_hist}")
        return []

@app.get("/api/v1/settings/tipos")
async def get_tipos_config():
    """Retorna los tipos de contratación activos y las opciones disponibles."""
    activos = await get_active_tipos()
    return {
        "tipos_activos": activos,
        "opciones_disponibles": [
            {"id": "Servicios", "label": "Servicios (y Consultorías)", "descripcion": "Servicios generales, asesorías, consultorías de obras"},
            {"id": "Bienes", "label": "Bienes", "descripcion": "Suministros, materiales, equipamiento, insumos"},
            {"id": "Obras", "label": "Obras", "descripcion": "Construcción, mantenimiento, infraestructura pública"}
        ]
    }

@app.post("/api/v1/settings/tipos")
async def save_tipos_config(payload: TiposConfigRequest):
    """Guarda los tipos de contratación habilitados para el cron y la plataforma."""
    nuevos_tipos = await set_active_tipos(payload.tipos_activos)
    return {
        "status": "success",
        "message": "Configuración de tipos actualizada correctamente.",
        "tipos_activos": nuevos_tipos
    }