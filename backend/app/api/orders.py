from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.dependencies import get_current_user, require_dealer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas import CompleteOrderRequest, OrderCreate, OrderOut
from app.services.orders import create_order
from app.services.state_machine import transition_order

router = APIRouter(prefix="/orders", tags=["orders"])


def _base_query(db: Session):
    return db.query(Order).options(
        joinedload(Order.items),
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.shipments),
        joinedload(Order.shipments).joinedload(Shipment.events),
        joinedload(Order.shipments).joinedload(Shipment.proof),
    )


@router.post("", response_model=OrderOut)
def post_order(data: OrderCreate, user: User = Depends(require_dealer), db: Session = Depends(get_db)):
    return create_order(db, dealer_id=user.id, data=data)


@router.get("", response_model=list[OrderOut])
def list_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = _base_query(db)
    if user.role != "admin":
        query = query.filter(Order.dealer_id == user.id)
    return query.order_by(Order.created_at.desc()).all()


@router.get("/{order_no}", response_model=OrderOut)
def get_order(order_no: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = _base_query(db).filter(Order.order_no == order_no).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if user.role != "admin" and order.dealer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该订单")
    return order


@router.post("/{order_no}/complete", response_model=OrderOut)
def complete_order(order_no: str, data: CompleteOrderRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.order_no != order_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单号不一致")
    order = _base_query(db).filter(Order.order_no == order_no).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if user.role != "dealer" or order.dealer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权完成该订单")
    if order.status != "DELIVERED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="只有已签收订单才能确认完成")
    transition_order(order, "COMPLETED")
    db.commit()
    db.refresh(order)
    return order
