#!/usr/bin/env python3
"""Backend end-to-end test using FastAPI TestClient and a temporary SQLite DB."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    db_path = Path("/private/tmp/paint_order_backend_e2e.db")
    if db_path.exists():
        db_path.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["AUTH_SECRET"] = "test-secret"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        dealer_login = client.post("/api/auth/login", json={"email": "dealer@example.com", "password": "dealer123"})
        assert dealer_login.status_code == 200, dealer_login.text
        dealer_headers = {"Authorization": f"Bearer {dealer_login.json()['token']}"}

        admin_login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"})
        assert admin_login.status_code == 200, admin_login.text
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

        product_create = client.post(
            "/api/products",
            json={"name": "验收专用漆", "color": "蓝灰", "category": "industrial", "price": "199.50", "stock": 5},
            headers=admin_headers,
        )
        assert product_create.status_code == 200, product_create.text
        product = product_create.json()
        assert product["family_id"], product
        assert product["family_code"], product
        assert product["color_hex"].startswith("#"), product

        custom_color = client.post(
            "/api/products",
            json={
                "family_id": product["family_id"],
                "name": "验收专用漆",
                "color": "暮山紫",
                "color_hex": "#8b5fa8",
                "category": "industrial",
                "price": "209.50",
                "stock": 3,
            },
            headers=admin_headers,
        )
        assert custom_color.status_code == 200, custom_color.text
        assert custom_color.json()["color_hex"] == "#8b5fa8"

        duplicate_color = client.post(
            "/api/products",
            json={
                "family_id": product["family_id"],
                "name": "验收专用漆",
                "color": "蓝灰",
                "color_hex": "#8094a6",
                "category": "industrial",
                "price": "199.50",
                "stock": 1,
            },
            headers=admin_headers,
        )
        assert duplicate_color.status_code == 409, duplicate_color.text

        stock_adjust = client.post(f"/api/products/{product['id']}/stock", json={"delta": 5, "reason": "test"}, headers=admin_headers)
        assert stock_adjust.status_code == 200, stock_adjust.text
        assert stock_adjust.json()["stock"] == 10

        seeded_products = client.get("/api/products", headers=dealer_headers)
        assert seeded_products.status_code == 200, seeded_products.text
        interior_colors = {item["color"] for item in seeded_products.json() if item["name"] == "净味内墙乳胶漆"}
        assert {"象牙白", "珍珠白", "浅杏"}.issubset(interior_colors), interior_colors
        product_families = client.get("/api/products/families", headers=dealer_headers)
        assert product_families.status_code == 200, product_families.text
        assert any(item["name"] == "净味内墙乳胶漆" for item in product_families.json()), product_families.json()
        color_options = client.get("/api/products/colors", headers=dealer_headers)
        assert color_options.status_code == 200, color_options.text
        assert any(item["name"] == "蓝灰" and item["hex"].startswith("#") for item in color_options.json()), color_options.json()
        assert any(item["name"] == "暮山紫" and item["hex"] == "#8b5fa8" for item in color_options.json()), color_options.json()

        admin_order = client.post(
            "/api/orders",
            json={
                "items": [{"product_id": product["id"], "quantity": 1}],
                "receiver_name": "后台不应下单",
                "receiver_phone": "13800000000",
                "shipping_address": "上海市测试路 2 号",
            },
            headers=admin_headers,
        )
        assert admin_order.status_code == 403, admin_order.text

        order_create = client.post(
            "/api/orders",
            json={
                "items": [{"product_id": product["id"], "quantity": 2}],
                "receiver_name": "端到端验收",
                "receiver_phone": "13800000000",
                "shipping_address": "上海市测试路 1 号",
            },
            headers=dealer_headers,
        )
        assert order_create.status_code == 200, order_create.text
        order = order_create.json()
        assert order["status"] == "已分配库存"
        assert order["status_code"] == "ALLOCATED"
        assert order["order_no"].startswith("PO")
        product_after_order = client.get("/api/products", headers=dealer_headers)
        assert product_after_order.status_code == 200, product_after_order.text
        ordered_product = next(item for item in product_after_order.json() if item["id"] == product["id"])
        assert ordered_product["stock"] == 8, ordered_product

        complete_too_early = client.post(f"/api/orders/{order['order_no']}/complete", json={"order_no": order["order_no"]}, headers=dealer_headers)
        assert complete_too_early.status_code == 409, complete_too_early.text

        shipment_bind = client.post(
            "/api/shipments/0/bind",
            json={"order_no": order["order_no"], "carrier": "sf", "tracking_no": f"SF-E2E-{order['order_no']}"},
            headers=admin_headers,
        )
        assert shipment_bind.status_code == 200, shipment_bind.text
        shipment = shipment_bind.json()
        assert shipment["status"] == "已发货"
        assert shipment["status_code"] == "SHIPPED"

        duplicate_shipment = client.post(
            "/api/shipments/0/bind",
            json={"order_no": order["order_no"], "carrier": "sf", "tracking_no": f"SF-E2E-DUP-{order['order_no']}"},
            headers=admin_headers,
        )
        assert duplicate_shipment.status_code == 409, duplicate_shipment.text

        dealer_sync = client.get(f"/api/tracking/{order['order_no']}?sync=true", headers=dealer_headers)
        assert dealer_sync.status_code == 403, dealer_sync.text

        status_update = client.post(
            f"/api/shipments/{shipment['id']}/status",
            json={"status": "IN_TRANSIT", "location": "上海分拨中心", "time": datetime.now(timezone.utc).isoformat()},
            headers=admin_headers,
        )
        assert status_update.status_code == 200, status_update.text
        assert status_update.json()["status"] == "运输中"
        assert status_update.json()["status_code"] == "IN_TRANSIT"

        pod = client.post(
            f"/api/shipments/{shipment['id']}/pod",
            json={
                "image_url": "https://oss.example.com/pod/e2e.jpg",
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "gps_location": "31.2304,121.4737",
            },
            headers=admin_headers,
        )
        assert pod.status_code == 200, pod.text
        assert pod.json()["status"] == "已签收"
        assert pod.json()["status_code"] == "DELIVERED"
        assert pod.json()["proof"]["image_url"] == "https://oss.example.com/pod/e2e.jpg"

        backward_status = client.post(
            f"/api/shipments/{shipment['id']}/status",
            json={"status": "IN_TRANSIT", "location": "重复回退", "time": datetime.now(timezone.utc).isoformat()},
            headers=admin_headers,
        )
        assert backward_status.status_code == 409, backward_status.text

        admin_complete = client.post(f"/api/orders/{order['order_no']}/complete", json={"order_no": order["order_no"]}, headers=admin_headers)
        assert admin_complete.status_code == 403, admin_complete.text

        complete = client.post(f"/api/orders/{order['order_no']}/complete", json={"order_no": order["order_no"]}, headers=dealer_headers)
        assert complete.status_code == 200, complete.text
        assert complete.json()["status"] == "已完成"
        assert complete.json()["status_code"] == "COMPLETED"

        pod_after_complete = client.post(
            f"/api/shipments/{shipment['id']}/pod",
            json={
                "image_url": "https://oss.example.com/pod/after-complete.jpg",
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "gps_location": "31.2304,121.4737",
            },
            headers=admin_headers,
        )
        assert pod_after_complete.status_code == 409, pod_after_complete.text

        tracking = client.get(f"/api/tracking/{order['order_no']}", headers=dealer_headers)
        assert tracking.status_code == 200, tracking.text
        event_status_codes = [event["status_code"] for event in tracking.json()["shipments"][0]["events"]]
        event_statuses = [event["status"] for event in tracking.json()["shipments"][0]["events"]]
        assert {"SHIPPED", "IN_TRANSIT", "DELIVERED"}.issubset(set(event_status_codes)), event_status_codes

        print(
            json.dumps(
                {
                    "ok": True,
                    "db": str(db_path),
                    "order_no": order["order_no"],
                    "shipment_id": shipment["id"],
                    "event_status_codes": event_status_codes,
                    "event_statuses": event_statuses,
                    "final_status": complete.json()["status"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
