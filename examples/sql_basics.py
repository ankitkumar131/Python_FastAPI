import sqlite3
connection = sqlite3.connect(":memory:")
try:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, price_minor INTEGER NOT NULL CHECK(price_minor >= 0))")
    with connection:
        connection.execute("INSERT INTO products (name, price_minor) VALUES (?, ?)", ("Pen", 2000))
    rows = connection.execute("SELECT id, name, price_minor FROM products WHERE price_minor <= ? ORDER BY id", (3000,)).fetchall()
    print(rows)
    with connection:
        connection.execute("UPDATE products SET price_minor = ? WHERE id = ?", (2500, 1))
    print(connection.execute("SELECT price_minor FROM products WHERE id = ?", (1,)).fetchone())
    with connection:
        connection.execute("DELETE FROM products WHERE id = ?", (1,))
finally:
    connection.close()
