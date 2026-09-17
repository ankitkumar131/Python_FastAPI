def total(price: int, quantity: int = 1) -> int:
    if price < 0 or quantity < 1:
        raise ValueError("Invalid price or quantity")
    return price * quantity

products = [{"name": "Notebook", "price": 120}, {"name": "Pen", "price": 20}]
for product in products:
    print(product["name"], total(product["price"], quantity=2))
try:
    total(-1)
except ValueError as error:
    print(str(error))
