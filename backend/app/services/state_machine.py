from fastapi import HTTPException, status

ORDER_STATUSES = ["CREATED", "ALLOCATED", "SHIPPED", "IN_TRANSIT", "DELIVERED", "COMPLETED"]
SHIPMENT_STATUSES = ["SHIPPED", "IN_TRANSIT", "DELIVERED"]

STATUS_LABELS = {
    "CREATED": "已创建",
    "ALLOCATED": "待发货",
    "SHIPPED": "已发货",
    "IN_TRANSIT": "运输中",
    "DELIVERED": "已签收",
    "COMPLETED": "已完成",
}

STATUS_CODES_BY_LABEL = {label: code for code, label in STATUS_LABELS.items()}


def assert_order_transition(current: str, target: str) -> None:
    if current == target:
        return
    try:
        current_index = ORDER_STATUSES.index(current)
        target_index = ORDER_STATUSES.index(target)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知订单状态：{status_label(current)} -> {status_label(target)}") from exc
    if target_index != current_index + 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"订单状态不能从「{status_label(current)}」变更为「{status_label(target)}」",
        )


def transition_order(order, target: str) -> None:
    assert_order_transition(order.status, target)
    order.status = target


def status_label(status_code: str) -> str:
    return STATUS_LABELS.get(status_code, status_code)


def normalize_status_code(status_text: str) -> str:
    text = status_text.strip()
    if text in STATUS_CODES_BY_LABEL:
        return STATUS_CODES_BY_LABEL[text]
    normalized = text.upper()
    if normalized in STATUS_LABELS:
        return normalized
    return map_carrier_status(text)


def map_carrier_status(status_text: str) -> str:
    normalized = status_text.strip().upper()
    if any(keyword in status_text for keyword in ("签收", "已妥投", "已送达")):
        return "DELIVERED"
    if any(keyword in status_text for keyword in ("运输", "转运", "派送", "到达", "离开", "中转", "揽收")):
        return "IN_TRANSIT"
    if normalized in {"PICKED_UP", "IN_TRANSIT", "TRANSIT", "ON_ROAD", "运输中"}:
        return "IN_TRANSIT"
    if normalized in {"SIGNED", "DELIVERED", "RECEIVED", "签收", "已签收"}:
        return "DELIVERED"
    if normalized in {"SHIPPED", "CREATED", "WAYBILL_CREATED", "已发货"}:
        return "SHIPPED"
    return normalized
