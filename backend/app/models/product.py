from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db import Base
from app.services.color_catalog import color_hex


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("product_families.id"), nullable=True, index=True)
    name = Column(String(160), nullable=False)
    color = Column(String(80), nullable=False)
    color_hex = Column(String(20), nullable=False, default="#d5dde2")
    category = Column(String(80), nullable=False, default="interior")
    price = Column(Numeric(12, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)

    family = relationship("ProductFamily", back_populates="variants")

    @property
    def family_code(self) -> str:
        return self.family.code if self.family else f"legacy-{self.category}-{self.name}"

    @property
    def family_name(self) -> str:
        return self.family.name if self.family else self.name

    @property
    def family_category(self) -> str:
        return self.family.category if self.family else self.category

    def apply_default_color_hex(self) -> None:
        if not self.color_hex:
            self.color_hex = color_hex(self.color)
