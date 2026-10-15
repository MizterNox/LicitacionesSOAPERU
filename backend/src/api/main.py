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

from database import AsyncSessionLocal
from models.tenders import TenderModel
from etl.extractor import OCESCExtractor
from etl.loader import ELTOrchestrator
from config import settings

API_URL = settings.API_URL

# Estado en memoria para monitorear la última ejecución del ETL
ultimo_estado_etl = {
    "status": "idle",
    "ultima_ejecucion": None,
    "resultado": None,
    "error": None
}

scheduler = AsyncIOScheduler()

async def job_etl_programado():
    """Tarea ejecutada automáticamente por el programador."""
    global ultimo_estado_etl
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    print(f"\n=======================================================")
    print(f"[SCHEDULER] ¡Ejecución automática del ETL iniciada! ({now_str})")
    print(f"=======================================================")

    ultimo_estado_etl["status"] = "running"
    ultimo_estado_etl["ultima_ejecucion"] = datetime.now().isoformat()
    ultimo_estado_etl["error"] = None

    try:
        extractor = OCESCExtractor(API_URL)
        orchestrator = ELTOrchestrator(extractor)

        total_guardados_general = 0
        for obj in ["Servicios", "Bienes"]:
            try:
                print(f"[SCHEDULER] Extrayendo {obj} con fecha_desde={hoy_str}...")
                res = await orchestrator.run_pipeline(
                    objeto=obj,
                    estado="Vigente",
                    fecha_desde=hoy_str,
                    max_pages=2
                )
                guardados = res.get("total_guardados_db", 0)
                total_guardados_general += guardados
                print(f"[SCHEDULER] -> {obj}: {guardados} registros procesados/guardados")
            except Exception as e_obj:
                print(f"[SCHEDULER] Error al procesar {obj}: {e_obj}")

        ultimo_estado_etl["status"] = "completed"
        ultimo_estado_etl["resultado"] = {
            "mensaje": f"ETL automático finalizado. Guardados: {total_guardados_general}",
            "fecha": hoy_str
        }
        print(f"[SCHEDULER] Fin de ejecución programada. Total guardados: {total_guardados_general}\n")
    except Exception as exc:
        ultimo_estado_etl["status"] = "failed"
        ultimo_estado_etl["error"] = str(exc)
        print(f"[SCHEDULER ERROR]: {exc}\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
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

    try:
        extractor = OCESCExtractor(API_URL)
        orchestrator = ELTOrchestrator(extractor)

        hoy = datetime.now()
        fecha_fin = config.fecha_hasta or hoy.strftime("%Y-%m-%d")

        if config.dias_atras and config.dias_atras > 0:
            fecha_inicio = (hoy - timedelta(days=config.dias_atras)).strftime("%Y-%m-%d")
        else:
            fecha_inicio = config.fecha_desde or hoy.strftime("%Y-%m-%d")

        resultado = await orchestrator.run_pipeline(
            objeto=config.objeto,
            estado=config.estado,
            fecha_desde=fecha_inicio,
            fecha_hasta=fecha_fin,
            max_pages=config.max_pages
        )
        ultimo_estado_etl["status"] = "completed"
        ultimo_estado_etl["resultado"] = resultado
    except Exception as exc:
        ultimo_estado_etl["status"] = "failed"
        ultimo_estado_etl["error"] = str(exc)
        print(f"[ERROR ETL BACKGROUND]: {exc}")

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

        # 3. Filtro Fecha
        hoy_date = datetime.now().date()
        if fecha:
            fecha_clean = fecha.strip().lower()
            if fecha_clean == "hoy":
                query = query.where(func.date(TenderModel.fecha_lanzamiento) >= hoy_date)
            elif fecha_clean not in ["todos", "all", ""]:
                try:
                    dt = datetime.fromisoformat(fecha_clean).date()
                    query = query.where(func.date(TenderModel.fecha_lanzamiento) >= dt)
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
    fecha_fin = config.fecha_hasta or hoy.strftime("%Y-%m-%d")
    if config.dias_atras and config.dias_atras > 0:
        fecha_inicio = (hoy - timedelta(days=config.dias_atras)).strftime("%Y-%m-%d")
    else:
        fecha_inicio = config.fecha_desde or hoy.strftime("%Y-%m-%d")

    config_calculada = {
        "objeto": config.objeto,
        "estado": config.estado,
        "fecha_desde": fecha_inicio,
        "fecha_hasta": fecha_fin,
        "max_pages": config.max_pages
    }

    if sync:
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
            return {"status": "success", "mode": "sync", "resultado": resultado}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(ejecutar_etl_task, config)

    return {
        "status": "accepted",
        "message": "Pipeline ETL encolado exitosamente en segundo plano.",
        "config_aplicada": config_calculada
    }