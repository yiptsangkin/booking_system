from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    family_id: Optional[int] = None
    family_code: str
    family_name: str
    family_category: str
    name: str
    color: str
    color_hex: str
    category: str
    price: Decimal
    stock: int


class ProductFamilyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str


class ProductFamilyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: Literal["interior", "exterior", "industrial"] = "interior"


class ColorOptionOut(BaseModel):
    name: str
    hex: str


class ProductCreate(BaseModel):
    family_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=160)
    color: str = Field(min_length=1, max_length=80)
    color_hex: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    category: Literal["interior", "exterior", "industrial"] = "interior"
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)


class ProductUpdate(BaseModel):
    family_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    color: Optional[str] = Field(default=None, min_length=1, max_length=80)
    color_hex: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    category: Optional[Literal["interior", "exterior", "industrial"]] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)


class StockAdjustRequest(BaseModel):
    delta: int
    reason: str = ""


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    receiver_name: str = Field(min_length=1, max_length=120)
    receiver_phone: str = Field(min_length=1, max_length=40)
    shipping_address: str = Field(min_length=1, max_length=500)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    price: Decimal
    product: ProductOut


class LogisticsEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    status: str = Field(validation_alias="status_label")
    status_code: str = Field(validation_alias="status")
    location: str
    time: datetime


class DeliveryProofOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    signed_at: datetime
    gps_location: str


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    order_no: str
    carrier: str
    tracking_no: str
    status: str = Field(validation_alias="status_label")
    status_code: str = Field(validation_alias="status")
    events: List[LogisticsEventOut] = Field(default_factory=list)
    proof: Optional[DeliveryProofOut] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    order_no: str
    status: str = Field(validation_alias="status_label")
    status_code: str = Field(validation_alias="status")
    total_price: Decimal
    receiver_name: str
    receiver_phone: str
    shipping_address: str
    created_at: datetime
    items: List[OrderItemOut] = Field(default_factory=list)
    shipments: List[ShipmentOut] = Field(default_factory=list)


class CreateShipmentRequest(BaseModel):
    order_no: str
    carrier: Optional[Literal["sf", "jd", "yimi"]] = None


class BindShipmentRequest(BaseModel):
    order_no: str
    carrier: Literal["sf", "jd", "yimi"]
    tracking_no: str = Field(min_length=1, max_length=120)


class TrackingResponse(BaseModel):
    order_no: str
    shipments: List[ShipmentOut] = Field(default_factory=list)


class WebhookStatusRequest(BaseModel):
    carrier: str
    tracking_no: str
    order_no: Optional[str] = None
    status: str
    location: str = ""
    time: Optional[datetime] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class WebhookPODRequest(BaseModel):
    carrier: str
    tracking_no: str
    order_no: str
    image_url: HttpUrl
    signed_at: datetime
    gps_location: str
    raw: Dict[str, Any] = Field(default_factory=dict)


class ManualStatusRequest(BaseModel):
    status: str
    location: str = ""
    time: Optional[datetime] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class ManualPODRequest(BaseModel):
    image_url: HttpUrl
    signed_at: datetime
    gps_location: str
    raw: Dict[str, Any] = Field(default_factory=dict)


class CompleteOrderRequest(BaseModel):
    order_no: str
