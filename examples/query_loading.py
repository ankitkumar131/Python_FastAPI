from sqlalchemy import ForeignKey, String, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload

class Base(DeclarativeBase):
    pass

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    products: Mapped[list["Product"]] = relationship(back_populates="supplier")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    supplier: Mapped[Supplier] = relationship(back_populates="products")

engine = create_engine("sqlite://")

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")

try:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        supplier = Supplier(name="PaperCo")
        session.add_all([Product(name="Pen", supplier=supplier), Product(name="Book", supplier=supplier)])
        session.commit()
    with Session(engine) as session:
        statement = select(Product).options(selectinload(Product.supplier)).order_by(Product.id).limit(10)
        products = session.scalars(statement).all()
        output = [{"name": product.name, "supplier": product.supplier.name} for product in products]
    print(output)
finally:
    engine.dispose()
