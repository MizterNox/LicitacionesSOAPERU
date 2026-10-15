import sys
import os
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
from config import settings

API_URL = settings.API_URL

DEFAULT_TIPOS = ["Servicios", "Bienes", "Obras"]

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
                total_extraidos_gen += ext
                total_guardados_gen += guardados
                total_ignorados_gen += ignorados
                detalles_por_tipo[obj] = res
                print(f"[SCHEDULER] -> {obj}: {guardados} persistidos/actualizados, {ignorados} no sobreescritos")
            except Exception as e_obj:
                print(f"[SCHEDULER] Error al procesar {obj}: {e_obj}")
                detalles_por_tipo[obj] = {"error": str(e_obj)}

        estado_final = "COMPLETED"
        ultimo_estado_etl["status"] = "completed"
        ultimo_estado_etl["resultado"] = {
            "mensaje": f"ETL automático finalizado. Total guardados: {total_guardados_gen}, No sobreescritos: {total_ignorados_gen}",
            "fecha": hoy_str,
            "tipos": tipos_a_ejecutar
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
    # Asegurar creación automática de nuevas tablas en PostgreSQL
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[FASTAPI LIFESPAN] Tablas de Base de Datos sincronizadas correctamente.")
    except Exception as e:
        print(f"[FASTAPI LIFESPAN ERROR] Error al sincronizar tablas: {e}")

    # 1. Rutina de Día / Tarde (14:00 PM) - Captura publicaciones de la mañana
    scheduler.add_job(job_etl_programado, 'cron', hour=14, minute=0, id='job_dia')
    # 2. Rutina de Noche / Madrugada (02:00 AM) - Consolida todo el día anterior
    scheduler.add_job(job_etl_programado, 'cron', hour=2, minute=0, id='job_noche')

    scheduler.start()
    print("\n[FASTAPI LIFESPAN] APScheduler iniciado automáticamente en segundo plano.")
    print("[FASTAPI LIFESPAN] Horarios programados:")
    print("  -> Turno Día:   14:00 PM")
    print("  -> Turno Noche: 02:00 AM\n")
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
    fecha: Optional[str] = Query(default="hoy", description="'hoy' para fecha actual, 'todos' para omitir filtro de fecha, o YYYY-MM-DD"),
    tipo: Optional[str] = Query(default="todos", description="Objeto contractual: 'Bienes', 'Servicios', 'Obras' o 'todos'"),
    search: Optional[str] = Query(default=None, description="Búsqueda por texto en código SEACE, título o descripción")
):
    """
    Endpoint principal para el Frontend React:
    Retorna los procesos de licitación almacenados en PostgreSQL con formato y props
    idénticas a las esperadas por los componentes visuales (BiddingTable, DetailPanel, KpiRow).
    """
    async with AsyncSessionLocal() as session:
        query = select(TenderModel)

        # 1. Filtro Vigentes
        if vigentes is True:
            query = query.where(TenderModel.estado.ilike("%Vigente%"))
        elif vigentes is False:
            query = query.where(~TenderModel.estado.ilike("%Vigente%"))

        # 2. Filtro Tipo de Objeto
        if tipo and tipo.lower() not in ["todos", "all", ""]:
            query = query.where(TenderModel.objeto_contratacion.ilike(f"%{tipo.strip()}%"))

        # 3. Filtro Fecha (Opción A: comparación por fecha exacta)
        hoy_date = datetime.now().date()
        if fecha:
            fecha_clean = fecha.strip().lower()
            if fecha_clean == "hoy":
                query = query.where(func.date(TenderModel.fecha_lanzamiento) == hoy_date)
            elif fecha_clean not in ["todos", "all", ""]:
                try:
                    dt = datetime.fromisoformat(fecha_clean).date()
                    query = query.where(func.date(TenderModel.fecha_lanzamiento) == dt)
                except ValueError:
                    pass

        # 4. Filtro Búsqueda
        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.where(
                TenderModel.titulo.ilike(pat) |
                TenderModel.descripcion.ilike(pat) |
                TenderModel.ocid.ilike(pat)
            )

        query = query.order_by(desc(TenderModel.fecha_lanzamiento))
        result = await session.execute(query)
        rows = result.scalars().all()

        formatted = []
        for idx, t in enumerate(rows, start=1):
            raw = t.raw_payload if isinstance(t.raw_payload, dict) else {}
            entidad = extract_entidad(raw)
            desc_text = t.descripcion or t.titulo or "Sin descripción"
            region = extract_region(raw, desc_text)
            f_limite = extract_fecha_limite(raw, t.fecha_lanzamiento)
            f_pub = t.fecha_lanzamiento.strftime("%Y-%m-%d") if t.fecha_lanzamiento else datetime.now().strftime("%Y-%m-%d")

            hitos = [
                {"nombre": "Convocatoria publicada", "fecha": f_pub},
                {"nombre": "Formulación de consultas", "fecha": f_pub},
                {"nombre": "Presentación de ofertas", "fecha": f_limite or f_pub},
                {"nombre": "Apertura de ofertas", "fecha": f_limite or f_pub}
            ]

            documentos = []
            tender_docs = raw.get("tender", {}).get("documents", [])
            if isinstance(tender_docs, list) and tender_docs:
                for d in tender_docs:
                    documentos.append({
                        "nombre": d.get("title", "Bases del Proceso"),
                        "formato": "PDF",
                        "tamano": "1.5 MB",
                        "actualizado": f_pub
                    })
            if not documentos:
                documentos = [
                    {"nombre": "Bases Administrativas", "formato": "PDF", "tamano": "2.4 MB", "actualizado": f_pub},
                    {"nombre": "Resumen Ejecutivo", "formato": "PDF", "tamano": "850 KB", "actualizado": f_pub}
                ]

            formatted.append({
                "id": t.ocid,
                "ocid": t.ocid,
                "codigo_seace": t.titulo or t.id_proceso,
                "entidad": entidad,
                "objeto": desc_text,
                "tipo_objeto": t.objeto_contratacion or "Servicios",
                "estado": t.estado or "Vigente",
                "fecha_publicacion": f_pub,
                "fecha_limite": f_limite,
                "valor_estimado": float(t.monto_estimado) if t.monto_estimado is not None else 0.0,
                "moneda": t.moneda or "PEN",
                "region": region,
                "modalidad": t.titulo.split("-")[0] if t.titulo else "CP",
                "tipo_proceso": extract_tipo_proceso(t.titulo),
                "cui": t.id_proceso or "",
                "match_score": 85 + (idx % 14),
                "fase_actual": 2,
                "hitos": hitos,
                "documentos": documentos,
                "motivos_ia": [
                    f"Proceso de {t.objeto_contratacion} registrado en SEACE",
                    f"Entidad compradora: {entidad}",
                    f"Monto estimado de S/ {float(t.monto_estimado or 0):,.2f}"
                ],
                "raw_payload": raw
            })

        return formatted

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
        "horarios_programados": ["14:00 PM (Día)", "02:00 AM (Noche)"],
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