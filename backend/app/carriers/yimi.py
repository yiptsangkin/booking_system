import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from app.carriers.base import BaseCarrier, CarrierAPIError, ShipmentResult


class YimiCarrier(BaseCarrier):
    code = "yimi"

    def _sign(self, timestamp: str, payload: Dict[str, Any]) -> str:
        canonical = self._canonical_json(payload)
        raw = f"appKey={self.settings.yimi_app_key}&timestamp={timestamp}&body={canonical}&secret={self.settings.yimi_app_secret}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()

    def _gateway_request(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._require(YIMI_APP_KEY=self.settings.yimi_app_key, YIMI_APP_SECRET=self.settings.yimi_app_secret, YIMI_GATEWAY_URL=self.settings.yimi_gateway_url)
        timestamp = str(int(time.time()))
        envelope = {
            "method": method,
            "appKey": self.settings.yimi_app_key,
            "timestamp": timestamp,
            "data": payload,
        }
        envelope["sign"] = self._sign(timestamp, payload)
        return self._request(
            "POST",
            self.settings.yimi_gateway_url,
            headers={"Content-Type": "application/json", "X-YIMI-App-Key": self.settings.yimi_app_key, "X-YIMI-Sign": envelope["sign"]},
            json_payload=envelope,
        )

    def create_shipment(self, order) -> ShipmentResult:
        if self.settings.yimi_gateway_url and self.settings.yimi_create_method:
            payload = {
                "order": order.order_no,
                "shipper": {
                    "name": self.settings.shipper_name,
                    "mobile": self.settings.shipper_phone,
                    "address": self.settings.shipper_address,
                },
                "consignee": order.receiver_name,
                "mobile": order.receiver_phone,
                "address": order.shipping_address,
                "cargoList": [
                    {"cargoName": item.product.name, "quantity": item.quantity}
                    for item in order.items
                ],
            }
            response = self._gateway_request(self.settings.yimi_create_method, payload)
            return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)
        self._require(YIMI_APP_KEY=self.settings.yimi_app_key, YIMI_APP_SECRET=self.settings.yimi_app_secret, YIMI_API_URL=self.settings.yimi_api_url)
        payload = {
            "order": order.order_no,
            "consignee": order.receiver_name,
            "mobile": order.receiver_phone,
            "address": order.shipping_address,
            "cargoList": [
                {"cargoName": item.product.name, "quantity": item.quantity}
                for item in order.items
            ],
        }
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "X-YIMI-App-Key": self.settings.yimi_app_key,
            "X-YIMI-Timestamp": timestamp,
            "X-YIMI-Sign": self._sign(timestamp, payload),
        }
        response = self._request("POST", self.settings.yimi_api_url, headers=headers, json_payload=payload)
        return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)

    def track_shipment(self, tracking_no: str) -> Dict[str, Any]:
        if self.settings.yimi_gateway_url and self.settings.yimi_track_method:
            return self._gateway_request(self.settings.yimi_track_method, {"billCode": tracking_no})
        self._require(YIMI_APP_KEY=self.settings.yimi_app_key, YIMI_APP_SECRET=self.settings.yimi_app_secret, YIMI_TRACK_URL=self.settings.yimi_track_url)
        payload = {"billCode": tracking_no}
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "X-YIMI-App-Key": self.settings.yimi_app_key,
            "X-YIMI-Timestamp": timestamp,
            "X-YIMI-Sign": self._sign(timestamp, payload),
        }
        return self._request("POST", self.settings.yimi_track_url, headers=headers, json_payload=payload)

    def handle_webhook(self, data: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        if self.settings.yimi_webhook_secret:
            expected = hmac.new(
                self.settings.yimi_webhook_secret.encode("utf-8"),
                self._canonical_json(data).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature):
                raise CarrierAPIError("一米滴答物流回调签名无效")
        return data
