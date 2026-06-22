#!/usr/bin/env python3
"""Smoke test that calls the real carrier create-shipment path.

Before running, configure backend/.env with the selected carrier's real endpoint
and credentials, then start the backend. This script intentionally calls
POST /api/shipments/create, so it will fail if the carrier API is not configured.

Run:
    conda run -n crp python scripts/real_carrier_flow.py --carrier sf
"""

from __future__ import annotations

import argparse
import json
import sys

import requests


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.trust_env = False

    def set_token(self, token: str) -> None:
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def request(self, method: str, path: str, **kwargs):
        response = self.session.request(method, f"{self.base_url}{path}", timeout=30, **kwargs)
        if response.status_code >= 400:
            print(f"\n{method} {path} failed: {response.status_code}", file=sys.stderr)
            print(response.text, file=sys.stderr)
            response.raise_for_status()
        return response.json()


def login(client: Client, email: str, password: str) -> dict:
    return client.request("POST", "/auth/login", json={"email": email, "password": password})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--carrier", choices=["sf", "jd", "yimi"], default="sf")
    parser.add_argument("--dealer-email", default="dealer@example.com")
    parser.add_argument("--dealer-password", default="dealer123")
    parser.add_argument("--admin-email", default="admin@example.com")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--sync-tracking", action="store_true")
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
            "receiver_name": "真实物流验收",
            "receiver_phone": "13800000000",
            "shipping_address": "上海市浦东新区真实物流测试地址",
        },
    )

    shipment = admin.request("POST", "/shipments/create", json={"order_no": order["order_no"], "carrier": args.carrier})
    tracking_path = f"/tracking/{order['order_no']}?sync={'true' if args.sync_tracking else 'false'}"
    tracking = admin.request("GET", tracking_path)

    print(
        json.dumps(
            {
                "ok": True,
                "real_carrier_create_called": True,
                "carrier": args.carrier,
                "order_no": order["order_no"],
                "shipment_id": shipment["id"],
                "tracking_no": shipment["tracking_no"],
                "shipment_status": shipment["status"],
                "tracking": tracking,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
