from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_admin
from app.models.product import Product
from app.models.product_family import ProductFamily
from app.models.user import User
from app.schemas import ColorOptionOut, ProductCreate, ProductFamilyCreate, ProductFamilyOut, ProductOut, ProductUpdate, StockAdjustRequest
from app.services.color_catalog import color_hex, color_options
from app.services.product_families import get_or_create_family

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    return query.order_by(Product.id).all()


@router.get("/families", response_model=list[ProductFamilyOut])
def list_product_families(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ProductFamily)
    if category:
        query = query.filter(ProductFamily.category == category)
    return query.order_by(ProductFamily.category, ProductFamily.name).all()


@router.post("/families", response_model=ProductFamilyOut)
def create_product_family(data: ProductFamilyCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    family = get_or_create_family(db, data.name, data.category)
    db.commit()
    db.refresh(family)
    return family


@router.get("/colors", response_model=list[ColorOptionOut])
def list_colors(db: Session = Depends(get_db)):
    colors = {item["name"]: item["hex"] for item in color_options()}
    for row in db.query(Product.color, Product.color_hex).distinct().all():
        if row.color:
            colors[row.color] = row.color_hex or color_hex(row.color)
    return [{"name": name, "hex": hex_value} for name, hex_value in colors.items()]


@router.post("", response_model=ProductOut)
def create_product(data: ProductCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    family = _resolve_family(db, data.family_id, data.name, data.category)
    _assert_sku_unique(db, family.id, data.color)
    product = Product(
        family_id=family.id,
        name=family.name,
        color=data.color,
        color_hex=_normalize_color_hex(data.color, data.color_hex),
        category=family.category,
        price=data.price,
        stock=data.stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    updates = data.model_dump(exclude_unset=True)
    if "color" in updates or "color_hex" in updates:
        updates["color_hex"] = _normalize_color_hex(updates.get("color", product.color), updates.get("color_hex", product.color_hex))
    if "family_id" in updates:
        family = _resolve_family(db, updates["family_id"], updates.get("name") or product.name, updates.get("category") or product.category)
        updates["family_id"] = family.id
        updates["name"] = family.name
        updates["category"] = family.category
    elif "name" in updates or "category" in updates:
        family = get_or_create_family(db, updates.get("name") or product.name, updates.get("category") or product.category)
        updates["family_id"] = family.id
        updates["name"] = family.name
        updates["category"] = family.category
    target_family_id = updates.get("family_id", product.family_id)
    target_color = updates.get("color", product.color)
    if target_family_id is not None and (target_color != product.color or target_family_id != product.family_id):
        _assert_sku_unique(db, target_family_id, target_color, product.id)
    for key, value in updates.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def _resolve_family(db: Session, family_id: int | None, name: str, category: str) -> ProductFamily:
    if family_id is None:
        return get_or_create_family(db, name, category)
    family = db.query(ProductFamily).filter(ProductFamily.id == family_id).first()
    if family is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品款式不存在")
    return family


def _assert_sku_unique(db: Session, family_id: int, color: str, exclude_product_id: int | None = None) -> None:
    query = db.query(Product).filter(Product.family_id == family_id, Product.color == color)
    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)
    if query.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该商品款式下已存在相同色号")


def _normalize_color_hex(color: str, hex_value: str | None = None) -> str:
    return (hex_value or color_hex(color)).lower()


@router.post("/{product_id}/stock", response_model=ProductOut)
def adjust_stock(product_id: int, data: StockAdjustRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    new_stock = product.stock + data.delta
    if new_stock < 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="库存不能小于 0")
    product.stock = new_stock
    db.commit()
    db.refresh(product)
    return product
