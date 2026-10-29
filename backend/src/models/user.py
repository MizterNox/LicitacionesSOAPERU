"""
Modelo ORM para usuarios del sistema y control de acceso RBAC.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nombre = Column(String(150), nullable=False)
    rol = Column(String(20), nullable=False, default="user")  # 'user' | 'admin'
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    saved_filters = relationship("SavedFilterModel", back_populates="user", cascade="all, delete-orphan")
    alert_logs = relationship("AlertLogModel", back_populates="user", cascade="all, delete-orphan")
