from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.services.state_machine import status_label


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    carrier = Column(String(40), nullable=False)
    tracking_no = Column(String(120), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="SHIPPED")

    order = relationship("Order", back_populates="shipments")
    events = relationship("LogisticsEvent", cascade="all, delete-orphan", back_populates="shipment", order_by="LogisticsEvent.time")
    proof = relationship("DeliveryProof", cascade="all, delete-orphan", back_populates="shipment", uselist=False)

    @property
    def status_label(self) -> str:
        return status_label(self.status)

    @property
    def order_no(self) -> str:
        return self.order.order_no if self.order else ""
