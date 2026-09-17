def pen_total(quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return 20 * quantity

print(pen_total(3))
try:
    pen_total(0)
except ValueError as error:
    print(error)
