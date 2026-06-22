from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.services.state_machine import status_label


class LogisticsEvent(Base):
    __tablename__ = "logistics_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False)
    location = Column(String(255), nullable=False, default="")
    time = Column(DateTime, nullable=False, default=datetime.utcnow)
    raw_payload = Column(String(4000), nullable=False, default="")

    shipment = relationship("Shipment", back_populates="events")

    @property
    def status_label(self) -> str:
        return status_label(self.status)
