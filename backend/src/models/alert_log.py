"""
Modelo ORM para registro y deduplicación de alertas de licitaciones enviadas.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class AlertLogModel(Base):
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_filter_id = Column(Integer, ForeignKey("saved_filters.id", ondelete="CASCADE"), nullable=False, index=True)
    ocid = Column(String(100), ForeignKey("tenders.ocid", ondelete="CASCADE"), nullable=False, index=True)
    enviado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("saved_filter_id", "ocid", name="uq_alert_log_filter_ocid"),
    )

    # Relaciones
    user = relationship("UserModel", back_populates="alert_logs")
    saved_filter = relationship("SavedFilterModel", back_populates="alert_logs")
