from sqlalchemy import Column, String, DateTime, Text, Numeric, JSON
from database import Base
from datetime import datetime

class TenderModel(Base):
    __tablename__ = "tenders"

    ocid = Column(String(100), primary_key=True, index=True)
    id_proceso = Column(String(100), index=True)
    titulo = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(50), index=True)  # Ej: Vigente
    objeto_contratacion = Column(String(100), index=True)  # Bienes, Servicios, etc.
    monto_estimado = Column(Numeric(15, 2), nullable=True)
    moneda = Column(String(10), default="PEN")
    fecha_lanzamiento = Column(DateTime, nullable=True)
    
    # Columna JSONB crucial para auditoría y almacenar todo el payload OCDS crudo
    raw_payload = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)