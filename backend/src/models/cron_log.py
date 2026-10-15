from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from database import Base

class CronExecutionModel(Base):
    """
    Registro histórico de operaciones del cron o sincronizaciones manuales.
    Permite auditar fecha/hora de ejecución, objetos procesados,
    registros extraídos, registros guardados e ignorados, y estado final.
    """
    __tablename__ = "cron_executions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    iniciado_en = Column(DateTime, default=datetime.now, nullable=False, index=True)
    finalizado_en = Column(DateTime, nullable=True)
    tipo_ejecucion = Column(String(50), default="AUTOMATICO")  # 'AUTOMATICO' | 'MANUAL'
    estado = Column(String(20), default="RUNNING", index=True)  # 'RUNNING' | 'COMPLETED' | 'FAILED'
    objetos_procesados = Column(JSON, default=list)  # ["Servicios", "Bienes", "Obras"]
    total_extraidos = Column(Integer, default=0)
    total_guardados = Column(Integer, default=0)
    total_ignorados = Column(Integer, default=0)
    detalles = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
