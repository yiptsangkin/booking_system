from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.services.state_machine import status_label


def generate_order_no(sequence: int = 1, created_at: datetime | None = None) -> str:
    date_text = (created_at or datetime.utcnow()).strftime("%Y%m%d")
    return f"PO{date_text}{sequence:04d}"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(40), unique=True, index=True, nullable=False)
    dealer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="CREATED", index=True)
    total_price = Column(Numeric(12, 2), nullable=False, default=0)
    receiver_name = Column(String(120), nullable=False)
    receiver_phone = Column(String(40), nullable=False)
    shipping_address = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    dealer = relationship("User")
    items = relationship("OrderItem", cascade="all, delete-orphan", back_populates="order")
    shipments = relationship("Shipment", cascade="all, delete-orphan", back_populates="order")

    @property
    def status_label(self) -> str:
        return status_label(self.status)
