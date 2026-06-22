from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class DeliveryProof(Base):
    __tablename__ = "delivery_proof"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, unique=True, index=True)
    image_url = Column(String(1000), nullable=False)
    signed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    gps_location = Column(String(160), nullable=False)

    shipment = relationship("Shipment", back_populates="proof")
