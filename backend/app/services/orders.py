import re
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, generate_order_no
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas import OrderCreate
from app.services.state_machine import transition_order


def get_order_by_no(db: Session, order_no: str) -> Order | None:
    return db.query(Order).filter(Order.order_no == order_no).first()


def next_order_no(db: Session, created_at: datetime | None = None) -> str:
    created_at = created_at or datetime.utcnow()
    prefix = f"PO{created_at:%Y%m%d}"
    next_sequence = 1
    for row in db.query(Order.order_no).filter(Order.order_no.like(f"{prefix}%")).all():
        match = re.match(rf"^{prefix}(\d{{4,}})$", row.order_no or "")
        if match:
            next_sequence = max(next_sequence, int(match.group(1)) + 1)
    return generate_order_no(next_sequence, created_at)


def create_order(db: Session, dealer_id: int, data: OrderCreate) -> Order:
    if not data.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="订单至少需要包含一个商品")
    quantities: dict[int, int] = {}
    for item in data.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    product_ids = list(quantities)
    products = db.query(Product).filter(Product.id.in_(product_ids)).with_for_update().all()
    product_map = {product.id: product for product in products}
    missing_ids = sorted(set(product_ids) - set(product_map))
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"商品不存在：{missing_ids}")
    for product_id, quantity in quantities.items():
        product = product_map[product_id]
        if product.stock < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{product.name} 库存不足：需要 {quantity}，当前库存 {product.stock}",
            )
    total = Decimal("0")
    created_at = datetime.utcnow()
    order = Order(
        order_no=next_order_no(db, created_at),
        dealer_id=dealer_id,
        status="CREATED",
        total_price=Decimal("0"),
        receiver_name=data.receiver_name,
        receiver_phone=data.receiver_phone,
        shipping_address=data.shipping_address,
        created_at=created_at,
    )
    db.add(order)
    db.flush()
    for item in data.items:
        product = product_map[item.product_id]
        line_total = Decimal(product.price) * item.quantity
        total += line_total
        db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=item.quantity, price=product.price))
    for product_id, quantity in quantities.items():
        product_map[product_id].stock -= quantity
    order.total_price = total
    transition_order(order, "ALLOCATED")
    db.commit()
    db.refresh(order)
    return order


def allocate_stock(db: Session, order: Order) -> None:
    if order.status != "CREATED":
        return
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"商品不存在：{item.product_id}")
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{product.name} 库存不足：需要 {item.quantity}，当前库存 {product.stock}",
            )
        product.stock -= item.quantity
    transition_order(order, "ALLOCATED")
