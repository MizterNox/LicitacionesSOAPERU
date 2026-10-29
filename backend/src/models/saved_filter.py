"""
Modelo ORM para filtros de búsqueda guardados y configuración de alertas.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class SavedFilterModel(Base):
    __tablename__ = "saved_filters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    filtros = Column(JSON, nullable=False, default=dict)
    alertas_activas = Column(Boolean, nullable=False, default=True)
    frecuencia = Column(String(20), nullable=False, default="inmediata")  # 'inmediata' | 'diaria'
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    user = relationship("UserModel", back_populates="saved_filters")
    alert_logs = relationship("AlertLogModel", back_populates="saved_filter", cascade="all, delete-orphan")
