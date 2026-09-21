# Day 18 — SQL Databases

## Learning Objectives

- Use `database/sql` with a Postgres driver; understand `*sql.DB` as a connection pool.
- Run CRUD with parameterized queries (SQL-injection safe).
- Handle NULLs, scan rows properly, and close resources.
- Use transactions for multi-statement consistency.

## Prerequisites

- Day 16–17 (store interface pattern).

## 1. Concept Introduction

`database/sql` is Go's standard DB interface; drivers implement it per database:

```bash
go get github.com/jackc/pgx/v5/stdlib   # Postgres via pgx stdlib adapter
```

```go
import (
	"database/sql"
	_ "github.com/jackc/pgx/v5/stdlib" // driver registers itself
)

db, err := sql.Open("pgx", dsn)
```

**Key mental model**: `*sql.DB` is NOT a connection — it's a **pool**. Create one per app, share it everywhere; it's safe for concurrent use.

## 2. Why This Concept Exists

Every company's data lives in relational DBs. Go's `database/sql` gives one uniform API (`Query`, `QueryRow`, `Exec`) across MySQL/Postgres/SQLite, with the stdlib managing pooling, retries at connection level, and scanning — while staying driver-swappable. Compare: Java JDBC, but with context support and goroutine-safe pooling built in.

## 3. Syntax

```go
// DSN (Postgres): postgres://user:pass@localhost:5432/dbname?sslmode=disable
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(25)
db.SetConnMaxLifetime(5 * time.Minute)

row := db.QueryRowContext(ctx, "SELECT name FROM users WHERE id=$1", id)
err := row.Scan(&name)                       // sql.ErrNoRows if absent

rows, err := db.QueryContext(ctx, "SELECT id, name FROM users")
defer rows.Close()
for rows.Next() {
	err = rows.Scan(&id, &name)
}
err = rows.Err()                             // iteration-level error!

res, err := db.ExecContext(ctx, "DELETE FROM users WHERE id=$1", id)
n, _ := res.RowsAffected()
```

**Always** use placeholders (`$1`, `?`) — never string-format SQL.

## 4. Detailed Explanation

- **Query vs QueryRow vs Exec**: `Query` → multiple rows; `QueryRow` → at most one (returns `sql.ErrNoRows`); `Exec` → no rows (INSERT/UPDATE/DELETE), returns `Result`.
- **Error triage**: `errors.Is(err, sql.ErrNoRows)` = not found; driver errors otherwise. Always check `rows.Err()` **after** the loop — a network drop mid-iteration surfaces only there.
- **NULLs**: scan into `sql.NullString`, `sql.NullInt64`, etc., or use pointer fields. Scanning NULL into `string` panics/errors.
- **Transactions**: `tx, _ := db.BeginTx(ctx, nil)` → use `tx.Exec/Query` → `tx.Commit()` or `tx.Rollback()`. Defer a rollback safety net: after a successful commit, rollback returns `sql.ErrTxDone`, which you ignore.
- **Context**: all `...Context` variants cancel the query if the request dies — pass `r.Context()` from HTTP handlers.

## 5. Example 1 — Setup + CRUD

```go
package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

type User struct {
	ID    int
	Name  string
	Email string
}

func main() {
	db, err := sql.Open("pgx", "postgres://app:app@localhost:5432/appdb?sslmode=disable")
	if err != nil {
		panic(err)
	}
	defer db.Close()

	db.SetMaxOpenConns(20)
	db.SetConnMaxLifetime(30 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// CREATE
	var id int
	err = db.QueryRowContext(ctx,
		`INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id`,
		"Ada", "ada@example.com").Scan(&id)
	fmt.Println("created id:", id, err)

	// READ one
	var u User
	err = db.QueryRowContext(ctx,
		`SELECT id, name, email FROM users WHERE id = $1`, id).
		Scan(&u.ID, &u.Name, &u.Email)
	if errors.Is(err, sql.ErrNoRows) {
		fmt.Println("not found")
	}

	// READ many
	rows, err := db.QueryContext(ctx, `SELECT id, name, email FROM users ORDER BY id`)
	if err != nil {
		panic(err)
	}
	defer rows.Close()
	for rows.Next() {
		if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
			panic(err)
		}
		fmt.Printf("%+v\n", u)
	}
	if err := rows.Err(); err != nil {
		panic(err)
	}

	// UPDATE
	res, _ := db.ExecContext(ctx, `UPDATE users SET email=$1 WHERE id=$2`,
		"new@example.com", id)
	n, _ := res.RowsAffected()
	fmt.Println("updated:", n)
}
```

Schema (run once):

```sql
CREATE TABLE IF NOT EXISTS users (
	id    SERIAL PRIMARY KEY,
	name  TEXT NOT NULL,
	email TEXT UNIQUE
);
```

## 6. Example 2 — Transactions and NULLs

```go
package main

import (
	"context"
	"database/sql"
	"fmt"
)

type Transfer struct{ FromID, ToID, AmountCents int }

func transfer(ctx context.Context, db *sql.DB, t Transfer) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback() // no-op after commit

	// Debit
	var balance int
	err = tx.QueryRowContext(ctx,
		`SELECT balance FROM accounts WHERE id=$1 FOR UPDATE`, t.FromID).
		Scan(&balance)
	if err != nil {
		return err
	}
	if balance < t.AmountCents {
		return fmt.Errorf("insufficient funds: %d < %d", balance, t.AmountCents)
	}
	if _, err := tx.ExecContext(ctx,
		`UPDATE accounts SET balance = balance - $1 WHERE id=$2`,
		t.AmountCents, t.FromID); err != nil {
		return err
	}
	// Credit
	if _, err := tx.ExecContext(ctx,
		`UPDATE accounts SET balance = balance + $1 WHERE id=$2`,
		t.AmountCents, t.ToID); err != nil {
		return err
	}
	return tx.Commit() // atomic: both or neither
}

func nullableExample(db *sql.DB) {
	// middle_name may be NULL
	var mid sql.NullString
	_ = db.QueryRow(`SELECT middle_name FROM users WHERE id=$1`, 1).Scan(&mid)
	if mid.Valid {
		fmt.Println("middle:", mid.String)
	} else {
		fmt.Println("no middle name")
	}
}
```

`FOR UPDATE` locks the row inside the transaction, preventing races between concurrent transfers.

## 7. Real-World Example

Repository implementing Day 16's store interface — handlers don't change, only the store does:

```go
package repository

import (
	"context"
	"database/sql"
	"errors"

	"tasksapi/internal/task"
)

type Postgres struct{ db *sql.DB }

func NewPostgres(db *sql.DB) *Postgres { return &Postgres{db: db} }

func (p *Postgres) Get(ctx context.Context, id int) (task.Task, error) {
	var t task.Task
	var created sql.NullTime
	err := p.db.QueryRowContext(ctx,
		`SELECT id, title, done, created_at FROM tasks WHERE id=$1`, id).
		Scan(&t.ID, &t.Title, &t.Done, &created)
	if errors.Is(err, sql.ErrNoRows) {
		return task.Task{}, task.ErrNotFound // translate driver error → domain error
	}
	if err != nil {
		return task.Task{}, err
	}
	if created.Valid {
		t.CreatedAt = created.Time
	}
	return t, nil
}
```

The translation `sql.ErrNoRows → task.ErrNotFound` at the repository boundary keeps domain layers DB-agnostic — a hallmark of well-structured Go services.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| String-formatting SQL | SQL injection; use `$1`/`?` placeholders |
| Not calling `rows.Close()` | Leaks pool connections until deadlock |
| Skipping `rows.Err()` after loop | Silent partial reads |
| Opening a `*sql.DB` per request | Wasteful; one pool per app |
| Scanning NULL into plain string | Error; use `sql.Null*` or pointers |
| Missing defer rollback in tx | Connections stuck open on error path |
| Forgetting context variants | Queries outlive canceled requests |

## 9. Best Practices

- One `*sql.DB`, tuned pool sizes, shared app-wide.
- Always `...Context` variants with request context.
- Wrap transactions in helper functions taking `func(*sql.Tx) error`.
- Migrations as versioned SQL files (golang-migrate, goose).
- Benchmark with real data sizes; `EXPLAIN ANALYZE` slow queries.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| API | database/sql | JDBC | DB-API (psycopg) | pg / mysql2 |
| Pooling | built into sql.DB | HikariCP etc. | external pool | library pool |
| Params | `$1`, `?` | `?` | `%s` | `$1` |
| NULL handling | sql.Null* types | getObject wrappers | None values | null |
| Transactions | BeginTx/Commit/Rollback | setAutoCommit | with block | BEGIN/COMMIT |

## 11. Practical Exercise

1. Spin up Postgres via Docker (`docker run -e POSTGRES_PASSWORD=app -p 5432:5432 postgres:16`), create the users table, run Example 1.
2. Convert `Get` to return `ErrNotFound`-style domain errors.
3. Add a `Search(name string)` using `ILIKE $1`.

## 12. Mini Project / Task

Swap Day 16's memory store for a Postgres store implementing the same interface. Schema with `created_at TIMESTAMPTZ DEFAULT now()`. Verify the whole API works unchanged — this proves your layering.

## 13. Interview Questions

### Easy
- Is `*sql.DB` a connection?
- How do you prevent SQL injection in Go?

### Medium
- `Query` vs `QueryRow` vs `Exec`?
- How do you handle NULL columns?

### Hard
- Walk through a transaction with defer rollback — what happens on commit vs error?
- How would you detect and fix an N+1 query problem in a Go service?

## 14. Daily Practice Questions

### Easy
1. Connect to Postgres and `SELECT version()`.
2. Insert a row and return its id with `RETURNING`.
3. Scan a single user with `QueryRow`; handle `ErrNoRows`.
4. Count rows in a table.
5. Update a row and print `RowsAffected`.

### Medium
6. List users with pagination (`LIMIT $1 OFFSET $2`).
7. Insert 100 rows in one transaction; time it vs per-row autocommit.
8. Use `sql.NullString` for an optional column.
9. Implement soft delete (`deleted_at`) and filter it everywhere.
10. Use `db.PingContext` with timeout for a health check.

### Hard
11. Implement an upsert (`INSERT ... ON CONFLICT`) and report whether it inserted or updated.
12. Build a migration runner that applies numbered SQL files in order, tracking applied versions in a table.
13. Implement a repository interface with an in-memory fake; unit-test the service without a DB.
14. Diagnose and fix a connection-pool exhaustion bug (simulate with `SetMaxOpenConns(1)` + parallel queries).
15. Implement optimistic locking with a `version` column and retry-on-conflict.

## 15. Solutions / Hints

- Q7 hint: transactions amortize commit cost; expect 10–100× difference.
- Q11 hint: `RETURNING xmax = 0` distinguishes insert from update in Postgres.
- Q14 hint: all pool slots held by slow queries → new queries block; check `db.Stats()`.

## 16. Day Summary

- `*sql.DB` = pool; one per app, context-aware APIs.
- Placeholders always; check `ErrNoRows` and `rows.Err()`.
- Transactions + `defer tx.Rollback()`; translate driver errors to domain errors at the repository.

## 17. What To Revise

- Query/Exec decision table; transaction skeleton.

## 18. What Comes Tomorrow

**Day 19 — MongoDB**: document databases with the official Go driver — CRUD, filters, and when documents beat tables.
