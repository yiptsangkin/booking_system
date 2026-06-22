from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db import Base


class ProductFamily(Base):
    __tablename__ = "product_families"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False, default="interior", index=True)

    variants = relationship("Product", back_populates="family")
