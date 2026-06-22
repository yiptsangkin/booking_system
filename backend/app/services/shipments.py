import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.carriers.base import CarrierAPIError, CarrierConfigError
from app.carriers.dispatcher import LogisticsDispatcher
from app.models.delivery_proof import DeliveryProof
from app.models.logistics_event import LogisticsEvent
from app.models.order import Order
from app.models.shipment import Shipment
from app.schemas import BindShipmentRequest, ManualPODRequest, ManualStatusRequest, WebhookPODRequest, WebhookStatusRequest
from app.services.orders import allocate_stock, get_order_by_no
from app.services.state_machine import ORDER_STATUSES, SHIPMENT_STATUSES, map_carrier_status, status_label, transition_order


def _raw_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)[:4000]


def _event_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.utcnow()
    return datetime.utcnow()


def _extract_tracking_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = []
    for key in ("events", "traces", "routes", "trackList", "logisticsEvents"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates = value
            break
    nested = payload.get("routeResps")
    if not candidates and isinstance(nested, list):
        events: list[dict[str, Any]] = []
        for item in nested:
            if isinstance(item, dict):
                events.extend(_extract_tracking_events(item))
        return events
    if not candidates:
        for key in ("data", "apiResultData", "result", "msgData"):
            value = payload.get(key)
            if isinstance(value, dict):
                return _extract_tracking_events(value)
    events: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        status_text = item.get("status") or item.get("statusName") or item.get("opCode") or item.get("remark") or item.get("desc") or item.get("description") or ""
        location = item.get("location") or item.get("acceptAddress") or item.get("city") or item.get("siteName") or item.get("station") or ""
        time_value = item.get("time") or item.get("acceptTime") or item.get("operateTime") or item.get("timestamp")
        events.append({"status": map_carrier_status(str(status_text)), "location": str(location), "time": _event_time(time_value), "raw": item})
    return events


def _advance_order_to(order: Order, target: str) -> None:
    if order.status == target:
        return
    if target not in ORDER_STATUSES:
        transition_order(order, target)
        return
    if ORDER_STATUSES.index(target) < ORDER_STATUSES.index(order.status):
        return
    while order.status != target:
        current_index = ORDER_STATUSES.index(order.status)
        next_status = ORDER_STATUSES[current_index + 1]
        transition_order(order, next_status)


def _carrier_or_400(carrier_code: str | None = None):
    try:
        return LogisticsDispatcher().get(carrier_code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _assert_can_ship(order: Order) -> None:
    if order.shipments:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="订单已绑定运单")
    if order.status != "ALLOCATED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"当前订单状态为「{status_label(order.status)}」，不能发货")


def _assert_tracking_available(db: Session, carrier: str, tracking_no: str) -> str:
    tracking_no = tracking_no.strip()
    if not tracking_no:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="运单号不能为空")
    existing = db.query(Shipment).filter(Shipment.carrier == carrier, Shipment.tracking_no == tracking_no).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该物流公司的运单号已存在")
    return tracking_no


def create_shipment_with_carrier(db: Session, order_no: str, carrier_code: str | None = None) -> Shipment:
    order = get_order_by_no(db, order_no)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    allocate_stock(db, order)
    _assert_can_ship(order)
    carrier = _carrier_or_400(carrier_code)
    try:
        result = carrier.create_shipment(order)
    except (CarrierConfigError, CarrierAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    tracking_no = _assert_tracking_available(db, carrier.code, result.tracking_no)
    shipment = Shipment(order_id=order.id, carrier=carrier.code, tracking_no=tracking_no, status=result.status)
    db.add(shipment)
    db.flush()
    db.add(LogisticsEvent(shipment_id=shipment.id, status="SHIPPED", location="", time=datetime.utcnow(), raw_payload=_raw_text(result.raw)))
    transition_order(order, "SHIPPED")
    db.commit()
    db.refresh(shipment)
    return shipment


def bind_shipment(db: Session, data: BindShipmentRequest) -> Shipment:
    order = get_order_by_no(db, data.order_no)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    allocate_stock(db, order)
    _assert_can_ship(order)
    carrier = _carrier_or_400(data.carrier)
    tracking_no = _assert_tracking_available(db, carrier.code, data.tracking_no)
    shipment = Shipment(order_id=order.id, carrier=carrier.code, tracking_no=tracking_no, status="SHIPPED")
    db.add(shipment)
    db.flush()
    db.add(LogisticsEvent(shipment_id=shipment.id, status="SHIPPED", location="", time=datetime.utcnow(), raw_payload="{}"))
    transition_order(order, "SHIPPED")
    db.commit()
    db.refresh(shipment)
    return shipment


def sync_tracking_from_carrier(db: Session, shipment: Shipment) -> Shipment:
    if shipment.order.status == "COMPLETED":
        return shipment
    carrier = _carrier_or_400(shipment.carrier)
    try:
        payload = carrier.track_shipment(shipment.tracking_no)
    except (CarrierConfigError, CarrierAPIError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    for event in sorted(_extract_tracking_events(payload), key=lambda item: item["time"]):
        db.add(
            LogisticsEvent(
                shipment_id=shipment.id,
                status=event["status"],
                location=event["location"],
                time=event["time"],
                raw_payload=_raw_text(event["raw"]),
            )
        )
        if event["status"] in {"IN_TRANSIT", "DELIVERED"} and shipment.status != event["status"]:
            shipment.status = event["status"]
            _advance_order_to(shipment.order, event["status"])
    db.commit()
    db.refresh(shipment)
    return shipment


def _record_status(
    db: Session,
    shipment: Shipment,
    status_text: str,
    location: str,
    event_time: datetime | None,
    raw: dict[str, Any],
) -> Shipment:
    normalized_status = map_carrier_status(status_text)
    if normalized_status not in SHIPMENT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"不支持的物流状态：{status_text}")
    if shipment.order.status == "COMPLETED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成订单不能继续更新物流状态")
    if SHIPMENT_STATUSES.index(normalized_status) < SHIPMENT_STATUSES.index(shipment.status):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"物流状态不能回退：{status_label(shipment.status)} -> {status_label(normalized_status)}")
    db.add(
        LogisticsEvent(
            shipment_id=shipment.id,
            status=normalized_status,
            location=location,
            time=event_time or datetime.utcnow(),
            raw_payload=_raw_text(raw),
        )
    )
    if normalized_status in {"IN_TRANSIT", "DELIVERED"} and shipment.status != normalized_status:
        shipment.status = normalized_status
        _advance_order_to(shipment.order, normalized_status)
    db.commit()
    db.refresh(shipment)
    return shipment


def record_manual_status(db: Session, shipment_id: int, data: ManualStatusRequest) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运单不存在")
    return _record_status(db, shipment, data.status, data.location, data.time, data.raw or data.model_dump(mode="json"))


def record_status_webhook(db: Session, data: WebhookStatusRequest, signature: str | None) -> Shipment:
    carrier = _carrier_or_400(data.carrier)
    try:
        carrier.handle_webhook(data.model_dump(mode="json"), signature)
    except CarrierAPIError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    shipment = db.query(Shipment).filter(Shipment.tracking_no == data.tracking_no, Shipment.carrier == data.carrier.lower()).first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运单不存在")
    if data.order_no is not None and shipment.order.order_no != data.order_no:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="物流回调订单号与运单不匹配")
    return _record_status(db, shipment, data.status, data.location, data.time, data.raw or data.model_dump(mode="json"))


def _record_pod(
    db: Session,
    shipment: Shipment,
    image_url: str,
    signed_at: datetime,
    gps_location: str,
    raw: dict[str, Any],
) -> Shipment:
    image_url = str(image_url)
    if not image_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="签收图片必须是 OSS 或 http(s) 地址")
    if shipment.order.status == "COMPLETED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成订单不能继续回传签收凭证")
    proof = shipment.proof or DeliveryProof(shipment_id=shipment.id)
    proof.image_url = image_url
    proof.signed_at = signed_at
    proof.gps_location = gps_location
    db.add(proof)
    db.add(
        LogisticsEvent(
            shipment_id=shipment.id,
            status="DELIVERED",
            location=gps_location,
            time=signed_at,
            raw_payload=_raw_text(raw),
        )
    )
    if shipment.status != "DELIVERED":
        shipment.status = "DELIVERED"
        _advance_order_to(shipment.order, "DELIVERED")
    db.commit()
    db.refresh(shipment)
    return shipment


def record_manual_pod(db: Session, shipment_id: int, data: ManualPODRequest) -> Shipment:
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运单不存在")
    return _record_pod(db, shipment, str(data.image_url), data.signed_at, data.gps_location, data.raw or data.model_dump(mode="json"))


def record_pod_webhook(db: Session, data: WebhookPODRequest, signature: str | None) -> Shipment:
    carrier = _carrier_or_400(data.carrier)
    try:
        carrier.handle_webhook(data.model_dump(mode="json"), signature)
    except CarrierAPIError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    shipment = db.query(Shipment).filter(Shipment.tracking_no == data.tracking_no, Shipment.carrier == data.carrier.lower()).first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运单不存在")
    if shipment.order.order_no != data.order_no:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="签收回传订单号与运单不匹配")
    return _record_pod(db, shipment, str(data.image_url), data.signed_at, data.gps_location, data.raw or data.model_dump(mode="json"))
