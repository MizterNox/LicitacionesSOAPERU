from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
from database import Base

class AppSettingModel(Base):
    """
    Configuración general de la aplicación persistida en PostgreSQL.
    Permite almacenar los tipos activos de licitación para el cron y preferencias globales.
    """
    __tablename__ = "app_settings"

    clave = Column(String(50), primary_key=True, index=True)
    valor = Column(JSON, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
