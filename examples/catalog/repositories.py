from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Product

class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def list(self, limit: int, offset: int) -> list[Product]:
        return list(self.session.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)))

    def add(self, product: Product) -> None:
        self.session.add(product)

    def delete(self, product: Product) -> None:
        self.session.delete(product)
