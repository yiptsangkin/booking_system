from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.product import Product
from app.models.user import User
from app.services.color_catalog import color_hex
from app.services.product_families import get_or_create_family


DEFAULT_PRODUCTS = [
    ("净味内墙乳胶漆", "象牙白", "interior", Decimal("268.00"), 120),
    ("净味内墙乳胶漆", "珍珠白", "interior", Decimal("268.00"), 96),
    ("净味内墙乳胶漆", "浅杏", "interior", Decimal("278.00"), 72),
    ("耐候外墙工程漆", "浅灰", "exterior", Decimal("398.00"), 80),
    ("耐候外墙工程漆", "米白", "exterior", Decimal("398.00"), 68),
    ("耐候外墙工程漆", "海盐蓝", "exterior", Decimal("418.00"), 42),
    ("防霉厨卫专用漆", "米白", "interior", Decimal("328.00"), 64),
    ("防霉厨卫专用漆", "浅灰", "interior", Decimal("328.00"), 58),
    ("防霉厨卫专用漆", "薄荷绿", "interior", Decimal("338.00"), 36),
    ("工业金属防锈漆", "铁红", "industrial", Decimal("459.00"), 50),
    ("工业金属防锈漆", "中灰", "industrial", Decimal("459.00"), 44),
    ("工业金属防锈漆", "哑黑", "industrial", Decimal("478.00"), 32),
]


def seed_defaults(db: Session) -> None:
    if db.query(User).count() == 0:
        db.add_all(
            [
                User(name="示例经销商", email="dealer@example.com", password_hash=hash_password("dealer123"), role="dealer"),
                User(name="后台管理员", email="admin@example.com", password_hash=hash_password("admin123"), role="admin"),
            ]
        )
    for name, color, category, price, stock in DEFAULT_PRODUCTS:
        family = get_or_create_family(db, name, category)
        exists = db.query(Product).filter(Product.family_id == family.id, Product.color == color).first()
        if exists is None:
            db.add(Product(family_id=family.id, name=family.name, color=color, color_hex=color_hex(color), category=family.category, price=price, stock=stock))
        elif exists.family_id is None:
            exists.family_id = family.id
        elif not exists.color_hex:
            exists.color_hex = color_hex(color)
    db.commit()
