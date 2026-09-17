from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Product
from .repositories import ProductRepository
from .schemas import ProductWrite

class ProductMissing(Exception):
    pass

class ProductConflict(Exception):
    pass

class ProductService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = ProductRepository(session)

    def get(self, product_id: int) -> Product:
        product = self.repo.get(product_id)
        if product is None:
            raise ProductMissing()
        return product

    def save(self, product: Product) -> Product:
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise ProductConflict() from error
        self.session.refresh(product)
        return product

    def create(self, data: ProductWrite) -> Product:
        product = Product(**data.model_dump())
        self.repo.add(product)
        return self.save(product)

    def replace(self, product_id: int, data: ProductWrite) -> Product:
        product = self.get(product_id)
        product.name = data.name
        product.price_minor = data.price_minor
        return self.save(product)

    def delete(self, product_id: int) -> None:
        self.repo.delete(self.get(product_id))
        self.session.commit()
