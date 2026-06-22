import re
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import delivery_proof, logistics_event, order, order_item, product, product_family, shipment, user  # noqa: F401
    from app.models.order import generate_order_no

    _copy_demo_db_to_tmp_if_needed()
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    _migrate_product_families(inspector)
    if "orders" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("orders")}
    with engine.begin() as connection:
        if "order_no" not in columns:
            connection.execute(text("ALTER TABLE orders ADD COLUMN order_no VARCHAR(40)"))
        used = {
            row.order_no
            for row in connection.execute(text("SELECT order_no FROM orders WHERE order_no IS NOT NULL AND order_no != ''")).fetchall()
            if row.order_no and not _is_legacy_order_no(row.order_no)
        }
        rows = connection.execute(text("SELECT id, order_no, created_at FROM orders ORDER BY created_at, id")).fetchall()
        daily_sequences: dict[str, int] = {}
        for value in used:
            match = re.match(r"^PO(\d{8})(\d{4,})$", value)
            if match:
                daily_sequences[match.group(1)] = max(daily_sequences.get(match.group(1), 0), int(match.group(2)))
        for row in rows:
            if row.order_no and not _is_legacy_order_no(row.order_no):
                continue
            created_at = _coerce_datetime(row.created_at)
            date_text = created_at.strftime("%Y%m%d")
            daily_sequences[date_text] = daily_sequences.get(date_text, 0) + 1
            order_no = generate_order_no(daily_sequences[date_text], created_at)
            while order_no in used:
                daily_sequences[date_text] += 1
                order_no = generate_order_no(daily_sequences[date_text], created_at)
            used.add(order_no)
            connection.execute(text("UPDATE orders SET order_no = :order_no WHERE id = :id"), {"order_no": order_no, "id": row.id})
        if "order_no" not in columns:
            if engine.dialect.name == "sqlite":
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_no ON orders (order_no)"))
            else:
                connection.execute(text("CREATE UNIQUE INDEX ix_orders_order_no ON orders (order_no)"))


def _copy_demo_db_to_tmp_if_needed() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    database = make_url(settings.database_url).database
    if not database:
        return
    target = Path(database)
    if not target.is_absolute() or target.exists() or not str(target).startswith("/tmp/"):
        return
    source = Path(__file__).resolve().parents[1] / "dev.db"
    if not source.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _migrate_product_families(inspector) -> None:
    from app.services.color_catalog import color_hex

    if "products" not in inspector.get_table_names():
        return
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    with engine.begin() as connection:
        if "family_id" not in product_columns:
            connection.execute(text("ALTER TABLE products ADD COLUMN family_id INTEGER"))
        if "color_hex" not in product_columns:
            connection.execute(text("ALTER TABLE products ADD COLUMN color_hex VARCHAR(20)"))
        rows = connection.execute(text("SELECT id, name, color, category, family_id, color_hex FROM products ORDER BY id")).fetchall()
        for row in rows:
            if not row.color_hex:
                connection.execute(text("UPDATE products SET color_hex = :color_hex WHERE id = :id"), {"color_hex": color_hex(row.color), "id": row.id})
            if row.family_id:
                continue
            code = _product_family_code(row.name, row.category)
            family = connection.execute(text("SELECT id FROM product_families WHERE code = :code"), {"code": code}).fetchone()
            if family is None:
                connection.execute(
                    text("INSERT INTO product_families (code, name, category) VALUES (:code, :name, :category)"),
                    {"code": code, "name": row.name, "category": row.category},
                )
                family = connection.execute(text("SELECT id FROM product_families WHERE code = :code"), {"code": code}).fetchone()
            connection.execute(text("UPDATE products SET family_id = :family_id WHERE id = :id"), {"family_id": family.id, "id": row.id})


def _is_legacy_order_no(value: str) -> bool:
    return value.startswith("ORD-") or len(value) > 18


def _coerce_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.utcnow()
    return datetime.utcnow()


def _product_family_code(name: str, category: str) -> str:
    from app.services.product_families import product_family_code

    return product_family_code(name, category)
