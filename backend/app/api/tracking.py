from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models.order import Order
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas import TrackingResponse
from app.services.shipments import sync_tracking_from_carrier

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/{order_no}", response_model=TrackingResponse)
def tracking(order_no: str, sync: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if user.role != "admin" and order.dealer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该物流轨迹")
    shipments = db.query(Shipment).filter(Shipment.order_id == order.id).all()
    if sync:
        if user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限才能同步物流轨迹")
        shipments = [sync_tracking_from_carrier(db, shipment) for shipment in shipments]
    return {"order_no": order.order_no, "shipments": shipments}
