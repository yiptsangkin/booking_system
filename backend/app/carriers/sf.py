import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from app.carriers.base import BaseCarrier, CarrierAPIError, ShipmentResult


class SFCarrier(BaseCarrier):
    code = "sf"

    def _sign(self, payload: Dict[str, Any]) -> str:
        secret = self.settings.sf_app_secret
        canonical = self._canonical_json(payload)
        algorithm = self.settings.sf_sign_algorithm.lower()
        if algorithm == "md5":
            return hashlib.md5(f"{canonical}{secret}".encode("utf-8")).hexdigest()
        if algorithm in {"hmac-sha256", "sha256"}:
            return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        raise CarrierAPIError(f"不支持的顺丰签名算法：{self.settings.sf_sign_algorithm}")

    def _fengqiao_digest(self, msg_data: str, timestamp: str) -> str:
        raw = quote_plus(f"{msg_data}{timestamp}{self.settings.sf_check_word}", encoding="utf-8")
        digest = hashlib.md5(raw.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("ascii")

    def _fengqiao_request(self, service_code: str, msg_data: Dict[str, Any]) -> Dict[str, Any]:
        self._require(SF_PARTNER_ID=self.settings.sf_partner_id, SF_CHECK_WORD=self.settings.sf_check_word, SF_GATEWAY_URL=self.settings.sf_gateway_url)
        timestamp = str(int(time.time()))
        msg_text = self._canonical_json(msg_data)
        form = {
            "partnerID": self.settings.sf_partner_id,
            "requestID": str(uuid.uuid4()),
            "serviceCode": service_code,
            "timestamp": timestamp,
            "msgDigest": self._fengqiao_digest(msg_text, timestamp),
            "msgData": msg_text,
        }
        response = self._request(
            "POST",
            self.settings.sf_gateway_url,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data_payload=form,
        )
        if response.get("apiResultCode") and response.get("apiResultCode") != "A1000":
            raise CarrierAPIError(f"顺丰接口错误 {response.get('apiResultCode')}：{response.get('apiErrorMsg')}")
        result_data = response.get("apiResultData")
        if isinstance(result_data, str) and result_data:
            try:
                response["apiResultData"] = json.loads(result_data)
            except ValueError:
                pass
        result_data = response.get("apiResultData")
        if isinstance(result_data, dict) and isinstance(result_data.get("msgData"), str):
            try:
                result_data["msgData"] = json.loads(result_data["msgData"])
            except ValueError:
                pass
        return response

    def _create_by_fengqiao(self, order) -> ShipmentResult:
        self._require(SHIPPER_NAME=self.settings.shipper_name, SHIPPER_PHONE=self.settings.shipper_phone, SHIPPER_ADDRESS=self.settings.shipper_address)
        payload = {
            "language": "zh-CN",
            "orderId": order.order_no,
            "cargoDetails": [
                {
                    "name": item.product.name,
                    "count": item.quantity,
                    "unit": "桶",
                    "amount": str(item.price),
                }
                for item in order.items
            ],
            "contactInfoList": [
                {
                    "contactType": 1,
                    "contact": self.settings.shipper_name,
                    "tel": self.settings.shipper_phone,
                    "address": self.settings.shipper_address,
                },
                {
                    "contactType": 2,
                    "contact": order.receiver_name,
                    "tel": order.receiver_phone,
                    "address": order.shipping_address,
                },
            ],
            "payMethod": self.settings.sf_pay_method,
            "expressTypeId": self.settings.sf_express_type_id,
        }
        response = self._fengqiao_request(self.settings.sf_create_service_code, payload)
        return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)

    def create_shipment(self, order) -> ShipmentResult:
        if self.settings.sf_partner_id and self.settings.sf_check_word:
            return self._create_by_fengqiao(order)
        self._require(SF_APP_ID=self.settings.sf_app_id, SF_APP_SECRET=self.settings.sf_app_secret, SF_API_URL=self.settings.sf_api_url)
        payload = {
            "appId": self.settings.sf_app_id,
            "timestamp": int(time.time()),
            "orderId": order.order_no,
            "receiver": {
                "name": order.receiver_name,
                "phone": order.receiver_phone,
                "address": order.shipping_address,
            },
            "items": [
                {
                    "sku": str(item.product_id),
                    "name": item.product.name,
                    "quantity": item.quantity,
                }
                for item in order.items
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "X-SF-App-Id": self.settings.sf_app_id,
            "X-SF-Timestamp": str(payload["timestamp"]),
            "X-SF-Sign": self._sign(payload),
        }
        response = self._request("POST", self.settings.sf_api_url, headers=headers, json_payload=payload)
        return ShipmentResult(tracking_no=self._extract_tracking(response), status="SHIPPED", raw=response)

    def track_shipment(self, tracking_no: str) -> Dict[str, Any]:
        if self.settings.sf_partner_id and self.settings.sf_check_word:
            payload = {
                "trackingType": "1",
                "trackingNumber": [tracking_no],
                "methodType": "1",
            }
            return self._fengqiao_request(self.settings.sf_track_service_code, payload)
        self._require(SF_APP_ID=self.settings.sf_app_id, SF_APP_SECRET=self.settings.sf_app_secret, SF_TRACK_URL=self.settings.sf_track_url)
        payload = {"appId": self.settings.sf_app_id, "timestamp": int(time.time()), "trackingNo": tracking_no}
        headers = {
            "Content-Type": "application/json",
            "X-SF-App-Id": self.settings.sf_app_id,
            "X-SF-Sign": self._sign(payload),
        }
        return self._request("POST", self.settings.sf_track_url, headers=headers, json_payload=payload)

    def handle_webhook(self, data: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        if self.settings.sf_webhook_secret:
            expected = hmac.new(
                self.settings.sf_webhook_secret.encode("utf-8"),
                self._canonical_json(data).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not signature or not hmac.compare_digest(expected, signature):
                raise CarrierAPIError("顺丰物流回调签名无效")
        return data
