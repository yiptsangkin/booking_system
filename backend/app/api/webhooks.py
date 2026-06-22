from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ShipmentOut, WebhookPODRequest, WebhookStatusRequest
from app.services.shipments import record_pod_webhook, record_status_webhook

router = APIRouter(prefix="/webhook/logistics", tags=["logistics-webhooks"])


@router.post("/status", response_model=ShipmentOut)
def logistics_status(data: WebhookStatusRequest, x_carrier_signature: str | None = Header(default=None), db: Session = Depends(get_db)):
    return record_status_webhook(db, data, x_carrier_signature)


@router.post("/pod", response_model=ShipmentOut)
def logistics_pod(data: WebhookPODRequest, x_carrier_signature: str | None = Header(default=None), db: Session = Depends(get_db)):
    return record_pod_webhook(db, data, x_carrier_signature)
