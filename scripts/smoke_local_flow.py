#!/usr/bin/env python3
"""Local business-flow smoke test without calling carrier create APIs.

This script validates the application workflow with the manual bind endpoint:
dealer login -> product list -> order -> admin bind waybill -> manual status
-> manual POD -> order complete -> tracking readback.

Run after starting the backend:
    conda run -n crp python scripts/smoke_local_flow.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import requests


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = False

    def set_token(self, token: str) -> None:
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs):
        response = self.session.request(method, f"{self.base_url}{path}", timeout=20, **kwargs)
        if response.status_code >= 400:
            print(f"\n{method} {path} failed: {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            response.raise_for_status()
        return response.json()


def login(client: Client, email: str, password: str) -> dict:
    data = client.request("POST", "/auth/login", json={"email": email, "password": password})
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--dealer-email", default="dealer@example.com")
    parser.add_argument("--dealer-password", default="dealer123")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--carrier", choices=["sf", "jd", "yimi"], default="sf")
    parser.add_argument("--tracking-no", default="")
    parser.add_argument("--pod-url", default="https://oss.example.com/pod/demo-paint-order.jpg")
    args = parser.parse_args()

    dealer = Client(args.base_url)
    admin = Client(args.base_url)

    dealer_login = login(dealer, args.dealer_email, args.dealer_password)
    dealer.set_token(dealer_login["token"])
    admin_login = login(admin, args.admin_email, args.admin_password)
    admin.set_token(admin_login["token"])

    products = dealer.request("GET", "/products")
    assert products, "products should not be empty"
    product = products[0]
    order = dealer.request(
        "POST",
        "/orders",
        json={
            "items": [{"product_id": product["id"], "quantity": 1}],
            "receiver_name": "验收经销商",
            "receiver_phone": "13800000000",
            "shipping_address": "上海市浦东新区测试路 100 号",
        },
    )
    assert order["status_code"] == "ALLOCATED", order
    tracking_no = args.tracking_no or f"LOCAL-{args.carrier.upper()}-{order['order_no']}"

    shipment = admin.request(
        "POST",
        "/shipments/0/bind",
        json={"order_no": order["order_no"], "carrier": args.carrier, "tracking_no": tracking_no},
    )
    assert shipment["tracking_no"] == tracking_no, shipment
    assert shipment["status_code"] == "SHIPPED", shipment

    status_payload = {
        "status": "IN_TRANSIT",
        "location": "上海分拨中心",
        "time": datetime.now(timezone.utc).isoformat(),
        "raw": {"source": "smoke_local_flow", "step": "in_transit"},
    }
    shipment = admin.request("POST", f"/shipments/{shipment['id']}/status", json=status_payload)
    assert shipment["status_code"] == "IN_TRANSIT", shipment

    pod_payload = {
        "image_url": args.pod_url,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "gps_location": "31.2304,121.4737",
        "raw": {"source": "smoke_local_flow", "step": "pod"},
    }
    shipment = admin.request("POST", f"/shipments/{shipment['id']}/pod", json=pod_payload)
    assert shipment["status_code"] == "DELIVERED", shipment
    assert shipment["proof"]["image_url"] == args.pod_url, shipment

    completed = dealer.request("POST", f"/orders/{order['order_no']}/complete", json={"order_no": order["order_no"]})
    assert completed["status_code"] == "COMPLETED", completed

    tracking = dealer.request("GET", f"/tracking/{order['order_no']}")
    events = tracking["shipments"][0]["events"]
    statuses = [event["status"] for event in events]
    status_codes = [event["status_code"] for event in events]
    for required in ["SHIPPED", "IN_TRANSIT", "DELIVERED"]:
        assert required in status_codes, status_codes

    print(
        json.dumps(
            {
                "ok": True,
                "order_no": order["order_no"],
                "shipment_id": shipment["id"],
                "carrier": args.carrier,
                "tracking_no": tracking_no,
                "final_order_status": completed["status"],
                "event_status_codes": status_codes,
                "event_statuses": statuses,
                "pod_url": args.pod_url,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
