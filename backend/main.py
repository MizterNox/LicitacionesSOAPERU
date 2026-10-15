import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from etl.extractor import OCESCExtractor
from etl.loader import ELTOrchestrator
from config import settings

# URL del endpoint OCDS del OECE
API_URL = settings.API_URL

async def job_etl_diario():
    """Tarea programada que se ejecuta automáticamente."""
    extractor = OCESCExtractor(API_URL)
    orchestrator = ELTOrchestrator(extractor)
    
    # Por defecto filtro de fecha de hoy hacia atrás o según config del Front
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    # Ejecutamos para un objeto dinámico (ej. por defecto Servicios o iterando sobre objetos)
    await orchestrator.run_pipeline(objeto="Servicios", estado="Vigente", fecha_desde=hoy_str)

async def main():
    scheduler = AsyncIOScheduler()
    
    # Programar el ETL para que corra automáticamente dos veces al día:
    # 1. Turno Noche / Madrugada (02:00 AM) - Consolida todo el día anterior
    scheduler.add_job(job_etl_diario, 'cron', hour=2, minute=0, id='etl_noche')
    # 2. Turno Día / Tarde (14:00 PM) - Captura publicaciones de la mañana
    scheduler.add_job(job_etl_diario, 'cron', hour=14, minute=0, id='etl_dia')
    
    print("Iniciando planificador de tareas ETL (Día 14:00 PM / Noche 02:00 AM)...")
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        print("Deteniendo planificador...")
        scheduler.shutdown()

if __name__ == "__main__":
    # Si prefieres probar ejecutarlo una vez de forma manual primero:
    # asyncio.run(job_etl_diario())
    
    # Si quieres activar el agendador automático:
    asyncio.run(main())