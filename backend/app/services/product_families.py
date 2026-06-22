import re

from sqlalchemy.orm import Session

from app.models.product_family import ProductFamily


def product_family_code(name: str, category: str) -> str:
    base = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", f"{category}-{name}").strip("-").lower()
    return base[:80] or "product-family"


def get_or_create_family(db: Session, name: str, category: str) -> ProductFamily:
    code = product_family_code(name, category)
    family = db.query(ProductFamily).filter(ProductFamily.code == code).first()
    if family is not None:
        return family
    family = ProductFamily(code=code, name=name, category=category)
    db.add(family)
    db.flush()
    return family
