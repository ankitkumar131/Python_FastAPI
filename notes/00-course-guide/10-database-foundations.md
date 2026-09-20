# 10 — Databases before database libraries

[Previous](09-async-and-lifespan.md) · [Course map](./) · [Next](11-sqlalchemy.md)

## What is a database, and why do we need one?

A database is a managed system for storing, retrieving and changing data. Unlike our dictionary, a durable database can preserve committed data across application restarts, coordinate concurrent writers and enforce constraints. Think of an organized shared ledger rather than each employee keeping a private sticky note.

**Persistence** means data outlives the running Python process. A disk file can persist data, but building safe concurrent edits, indexes, queries and recovery around ad-hoc JSON files becomes difficult. A database solves those coordination problems, not just “saving a list.” It does not automatically make the data correct: you must choose constraints and transactions.

## SQL versus NoSQL

**SQL (Structured Query Language)** is a language used by relational database systems. PostgreSQL, MySQL and SQLite support relational data, though their features and concurrency models differ. A **relational database** organizes records in tables and relates them using keys.

**NoSQL** is an umbrella term including document, key/value and graph databases. MongoDB stores documents containing nested objects and arrays. NoSQL does not mean “no schema,” “no transactions” or “always faster.” Applications still need data rules.

Use relational storage when joins, constraints and multi-record transactions match the domain: orders, line items, payments. Document storage can fit aggregate-shaped data frequently read/written together: varied product specifications. Avoid choosing based only on popularity. Embedding a continually growing history in one document can hit document-size and write-contention limits.

## Vocabulary with a product/order example

| Term         | Meaning                                            | Example / why needed                           |
| ------------ | -------------------------------------------------- | ---------------------------------------------- |
| Table        | Named collection with defined columns              | `products`                                     |
| Row          | One record                                         | Product 7                                      |
| Column       | One typed property                                 | `name`, `price_minor`                          |
| Primary key  | Unique non-null row identity                       | `products.id`                                  |
| Foreign key  | Reference constrained to another table's key       | `order_items.product_id` references products   |
| Relationship | How records connect conceptually or in an ORM      | An order has many line items                   |
| Query        | Request for selected or changed data               | Find products below a price                    |
| Index        | Extra lookup structure maintained alongside rows   | Find a unique name without scanning everything |
| Constraint   | Database-enforced rule                             | Price nonnegative; name unique                 |
| Connection   | Communication channel/session to a database        | TCP connection to PostgreSQL                   |
| Pool         | Reusable set of connections                        | Avoid reconnecting per query                   |
| Transaction  | Group of changes succeeding or failing as one unit | Create an order and reserve stock              |

A foreign key enforces referential validity. An ORM relationship makes navigation convenient; they are not the same thing. A Python `order.product` property without a database foreign key cannot stop another program inserting a nonexistent product ID.

## Transactions: why “all or nothing” matters

Suppose checkout creates an order and reduces stock. If only the order write succeeds, you may promise unavailable goods. A transaction groups changes so either both commit or both roll back. **Commit** makes changes durable according to the database's guarantees. **Rollback** cancels uncommitted changes.

**ACID** summarizes important goals: **Atomicity** (all or nothing), **Consistency** (declared invariants hold), **Isolation** (concurrent work interacts according to a defined isolation level), **Durability** (committed data survives specified failures). Isolation does not always mean every transaction behaves as though no others exist. At READ COMMITTED isolation, separate statements may see different committed data. Preventing overselling may require conditional updates or row locks.

Do not hold a transaction open while waiting for a customer click or remote payment. A payment provider and your local database are not automatically one transaction. Use explicit workflow states, retry safety and reconciliation at that boundary.

## Complete SQL example with SQLite

**SQLite** is an embedded SQL database: a library works with a local file instead of a separate server. It suits learning, local tools and some small workloads. Limited concurrent writers and shared-volume deployment require care. This example deliberately uses `:memory:` for repeatability, not durability.

Run `python examples/sql_basics.py`. No pip package or database server is needed.

## Example

### File: `examples/sql_basics.py`

```python
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
```

## Code Explanation

### Line 1

Import Python's standard SQLite adapter.

### Line 2

Open a private transient database; a filename would store it on disk.

### Line 3

Arrange reliable closure even when SQL fails.

### Line 4

Enable foreign-key enforcement for this SQLite connection.

### Line 5

Define identity, required values, unique names and a nonnegative price constraint.

### Line 6

Commit on successful exit or roll back on failure; this context does not itself close the connection.

### Line 7

Insert using bound parameters, keeping values separate from SQL syntax.

### Line 8

Query filtered ordered rows; the comma creates a one-element parameter tuple.

### Line 9

Display the selected records as Python tuples.

### Line 10

Start another commit-or-rollback block.

### Line 11

Update only one known product using WHERE.

### Line 12

Verify the new price by reading one row.

### Line 13

Define a deletion transaction boundary.

### Line 14

Delete the chosen record, not all records.

### Line 15

Cleanup runs on either success or failure.

### Line 16

Release the connection explicitly.

## Test it and what happens internally

Expect `[(1, 'Pen', 2000)]` then `(2500,)`. INSERT changes a transaction; successful context exit commits. SELECT reads matching stored rows. Try inserting a duplicate Pen or setting price to -1 before deletion: the database raises `IntegrityError`, even though Python itself accepts those values. A missing `fetchone()` returns None, not an automatic HTTP 404. The API must translate absence.

## Parameterization and injection

SQL injection occurs when untrusted input changes query structure. Formatting user input into SQL can turn a name into executable syntax. Bound parameters keep values separate. Placeholder syntax differs by driver; SQLAlchemy expression construction handles it for supported drivers. Table/column names and sort directions generally cannot be bound as values; select them from an allowlist.

## Connections, pooling and FastAPI

FastAPI does not speak the database wire protocol itself. Your handler calls a library; that library uses a **driver**, an adapter implementing database communication. An ORM adds object/table mapping above the driver.

An engine/client should usually be long-lived, while a session/unit of work is short-lived. Creating a new engine per request creates excessive pools. Sharing one mutable session across requests mixes user transactions. Session closure usually returns a borrowed connection to the pool rather than destroying the engine.

Pools are per process. Four workers each allowing five base connections plus five overflow connections can potentially use forty. Include replicas, jobs and administrative tools when calculating a database's connection budget.

## When to use / not use; common mistakes and best practices

Use persistent storage for shared durable state, not merely because every tutorial has a database. Do not expect in-memory databases to survive a restart. Do not forget WHERE in UPDATE or DELETE: without it, every row can be affected. Application validation does not replace constraints. Indexes speed selected reads but consume storage and add write work.

Keep transactions short, use constraints and bound parameters, fetch bounded results, and test backups by restoring them. Learn your chosen database's actual locking and isolation rules.

## Practice

**Beginner:** Insert a Book costing 12000. **Intermediate:** Query only products costing at most 3000. **Challenge:** Prevent two buyers taking the last unit.

## Expected Result and Solution

Inside the first `with connection` in the complete file, add:

```python
        connection.execute("INSERT INTO products (name, price_minor) VALUES (?, ?)", ("Book", 12000))
```

This single line sends a parameterized insert in the same transaction. The existing filtered SELECT is the complete intermediate solution: only Pen appears, proving Book is excluded.

For the challenge, perform `UPDATE inventory SET stock = stock - 1 WHERE product_id = ? AND stock >= 1` inside a transaction and verify exactly one row changed before creating the order. Use the chosen database's isolation and retry rules. A Python read/check/later-write sequence without database coordination permits both buyers to read stock=1.

## Summary

Databases contribute durability, constraints and transaction coordination. An ORM makes them convenient from Python without removing those responsibilities.
