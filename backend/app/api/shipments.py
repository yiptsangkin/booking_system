from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas import BindShipmentRequest, CreateShipmentRequest, ManualPODRequest, ManualStatusRequest, ShipmentOut
from app.services.shipments import bind_shipment, create_shipment_with_carrier, record_manual_pod, record_manual_status

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.post("/create", response_model=ShipmentOut)
def create_shipment(data: CreateShipmentRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return create_shipment_with_carrier(db, data.order_no, data.carrier)


@router.post("/{shipment_id}/bind", response_model=ShipmentOut)
def bind_existing_waybill(shipment_id: int, data: BindShipmentRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    # shipment_id is accepted to match the required route shape; binding creates a shipment when an external waybill already exists.
    return bind_shipment(db, data)


@router.post("/{shipment_id}/status", response_model=ShipmentOut)
def manual_status(shipment_id: int, data: ManualStatusRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return record_manual_status(db, shipment_id, data)


@router.post("/{shipment_id}/pod", response_model=ShipmentOut)
def manual_pod(shipment_id: int, data: ManualPODRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    return record_manual_pod(db, shipment_id, data)
