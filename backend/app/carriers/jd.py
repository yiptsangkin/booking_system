import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

from app.carriers.base import BaseCarrier, CarrierAPIError, ShipmentResult


class JDCarrier(BaseCarrier):
    code = "jd"

    _token: str | None = None
    _token_expire_at: int = 0

    def _sign(self, timestamp: str, body: Dict[str, Any]) -> str:
        message = f"{self.settings.jd_app_key}{timestamp}{self._canonical_json(body)}"
        return hmac.new(self.settings.jd_app_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

    def _jos_sign(self, params: Dict[str, Any]) -> str:
        pieces = [self.settings.jd_app_secret]
        for key in sorted(params):
            if key == "sign":
                continue
            value = params[key]
            if value is None:
                continue
            pieces.append(f"{key}{value}")
        pieces.append(self.settings.jd_app_secret)
        return hashlib.md5("".join(pieces).encode("utf-8")).hexdigest().upper()

    def _jos_request(self, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._require(JD_APP_KEY=self.settings.jd_app_key, JD_APP_SECRET=self.settings.jd_app_secret, JD_GATEWAY_URL=self.settings.jd_gateway_url)
        token = self.get_token()
        params = {
            "method": method,
            "app_key": self.settings.jd_app_key,
            "access_token": token,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "format": "json",
            "v": self.settings.jd_version,
            "sign_method": self.settings.jd_sign_method,
            "360buy_param_json": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        }
        params["sign"] = self._jos_sign(params)
        return self._request(
            "POST",
            self.settings.jd_gateway_url,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data_payload=params,
        )

    def get_token(self) -> str:
        if self.settings.jd_access_token:
            return self.settings.jd_access_token
        self._require(JD_APP_KEY=self.settings.jd_app_key, JD_APP_SECRET=self.settings.jd_app_secret, JD_TOKEN_URL=self.settings.jd_token_url)
        now = int(time.time())
        if self._token and self._token_expire_at > now + 60:
            return self._token
        payload = {
            "grant_type": "client_credentials" if not self.settings.jd_refresh_token else "refresh_token",
            "client_id": self.settings.jd_app_key,
            "client_secret": self.settings.jd_app_secret,
        }
        if self.settings.jd_refresh_token:
            payload["refresh_token"] = self.settings.jd_refresh_token
        response = self._request("POST", self.settings.jd_token_url, headers={"Content-Type": "application/json"}, json_payload=payload)
        token = response.get("access_token") or response.get("accessToken")
        if not token:
            raise CarrierAPIError("京东物流接口未返回 access_token")
        self._token = str(token)
        self._token_expire_at = now + int(response.get("expires_in") or response.get("expiresIn") or 3600)
        return self._token

    def create_shipment(self, order) -> ShipmentResult:
        if self.settings.jd_create_method:
            payload = {
                "orderNo": order.order_no,
                "sender": {
                    "name": self.settings.shipper_name,
                    "mobile": self.settings.shipper_phone,
                    "address": self.settings.shipper_address,
                },
                "receiver": {
                    "name": order.receiver_name,
                    "mobile": order.receiver_phone,
                    "address": order.shipping_address,
                },
                "goods": [
                    {"sku": str(item.product_id), "name": item.product.name, "count": item.quantity}
                    for item in order.items
                ],
            }
            response = self._jos_request(self.settings.jd_create_method, payload)
            return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)
        self._require(JD_API_URL=self.settings.jd_api_url)
        token = self.get_token()
        payload = {
            "orderNo": order.order_no,
            "receiver": {
                "name": order.receiver_name,
                "mobile": order.receiver_phone,
                "address": order.shipping_address,
            },
            "goods": [
                {"sku": str(item.product_id), "name": item.product.name, "count": item.quantity}
                for item in order.items
            ],
        }
        timestamp = str(int(time.time()))
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-JD-App-Key": self.settings.jd_app_key,
            "X-JD-Timestamp": timestamp,
            "X-JD-Signature": self._sign(timestamp, payload),
        }
        response = self._request("POST", self.settings.jd_api_url, headers=headers, json_payload=payload)
        return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)

    def track_shipment(self, tracking_no: str) -> Dict[str, Any]:
        if self.settings.jd_track_method:
            return self._jos_request(self.settings.jd_track_method, {"waybillNo": tracking_no})
        self._require(JD_TRACK_URL=self.settings.jd_track_url)
        token = self.get_token()
        payload = {"waybillNo": tracking_no}
        timestamp = str(int(time.time()))
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-JD-App-Key": self.settings.jd_app_key,
            "X-JD-Timestamp": timestamp,
            "X-JD-Signature": self._sign(timestamp, payload),
        }
        return self._request("POST", self.settings.jd_track_url, headers=headers, json_payload=payload)

    def handle_webhook(self, data: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        if self.settings.jd_webhook_secret:
            expected = hmac.new(
                self.settings.jd_webhook_secret.encode("utf-8"),
                self._canonical_json(data).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature):
                raise CarrierAPIError("京东物流回调签名无效")
        return data
