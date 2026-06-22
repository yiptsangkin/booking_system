import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

from app.core.config import get_settings


class CarrierConfigError(RuntimeError):
    pass


class CarrierAPIError(RuntimeError):
    pass


@dataclass
class ShipmentResult:
    tracking_no: str
    status: str
    raw: Dict[str, Any]


class BaseCarrier:
    code = "base"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.session = requests.Session()

    def create_shipment(self, order) -> ShipmentResult:
        raise NotImplementedError

    def track_shipment(self, tracking_no: str) -> Dict[str, Any]:
        raise NotImplementedError

    def handle_webhook(self, data: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def _require(self, **values: str) -> None:
        missing = [key for key, value in values.items() if not value]
        if missing:
            raise CarrierConfigError(f"{self.code} 物流配置缺失：{', '.join(missing)}")

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Dict[str, str],
        json_payload: Dict[str, Any] | None = None,
        data_payload: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.carrier_retry_attempts + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_payload,
                    data=data_payload,
                    timeout=self.settings.carrier_timeout_seconds,
                )
                if response.status_code >= 500 and attempt < self.settings.carrier_retry_attempts:
                    time.sleep(self.settings.carrier_retry_backoff_seconds * attempt)
                    continue
                response.raise_for_status()
                try:
                    return response.json()
                except ValueError as exc:
                    raise CarrierAPIError(f"{self.code} 物流接口返回的不是 JSON：{response.text[:500]}") from exc
            except (requests.RequestException, CarrierAPIError) as exc:
                last_error = exc
                if attempt >= self.settings.carrier_retry_attempts:
                    break
                time.sleep(self.settings.carrier_retry_backoff_seconds * attempt)
        raise CarrierAPIError(f"{self.code} 物流接口请求失败：{last_error}") from last_error

    @staticmethod
    def _canonical_json(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _extract_tracking(response: Any) -> str:
        if isinstance(response, list):
            for item in response:
                try:
                    return BaseCarrier._extract_tracking(item)
                except CarrierAPIError:
                    continue
            raise CarrierAPIError("物流接口未返回运单号")
        if not isinstance(response, dict):
            raise CarrierAPIError("物流接口未返回运单号")
        for key in ("tracking_no", "trackingNo", "waybillNo", "mailNo", "expressNo", "billCode", "waybillCode", "deliveryId"):
            value = response.get(key)
            if value:
                return str(value)
        for key in ("waybillNoList", "mailNoList"):
            value = response.get(key)
            if isinstance(value, list) and value:
                return str(value[0])
        for key in ("data", "apiResultData", "result", "jingdong_response", "msgData", "waybillNoInfoList", "waybillInfoList"):
            value = response.get(key)
            if isinstance(value, (dict, list)):
                return BaseCarrier._extract_tracking(value)
        raise CarrierAPIError("物流接口未返回运单号")
