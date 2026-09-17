# 12 — PostgreSQL, MySQL and schema migrations

[Previous](11-sqlalchemy.md) · [Course map](00-course-guide.md) · [Next](13-mongodb.md)

## Why use a database server?

SQLite is embedded in your application process. **PostgreSQL** and **MySQL** are independent database server systems: multiple applications connect to them over a network. They provide sophisticated concurrency, users/permissions, replication and operational tooling. They require administration, connection limits, backups and upgrades. Do not switch databases merely to make a small prototype look more professional.

**PostgreSQL** is a strong general-purpose choice for transactional applications, rich queries and extensible types. **MySQL** is widely used for transactional web applications; use a transactional storage engine such as InnoDB. Their SQL dialects, collations (text comparison/sorting rules), types and defaults differ. SQLAlchemy smooths many differences, not every behavioural difference. Test migrations and constraints against the actual deployment database.

A **connection URL** tells SQLAlchemy which dialect/driver to use and where to connect. `postgresql+psycopg://user:password@host:5432/catalog` means PostgreSQL via Psycopg, at host/port, database catalog. `mysql+pymysql://...` selects PyMySQL. Neither URL starts a database server. Special characters in credentials need correct URL escaping; for dynamically built URLs prefer SQLAlchemy's `URL.create` rather than manual concatenation.

## Local servers: exact commands and their limits

**Docker**, explained fully in chapter 21, runs packaged programs in isolated processes called containers. For this optional lab you need Docker installed/running; use an existing local/managed database if not. These are disposable **local-development** credentials, never production secrets. Ports are bound to loopback so the database is not publicly exposed.

```bash
docker run --name fastapi-pg -e POSTGRES_USER=school -e POSTGRES_PASSWORD=local-only -e POSTGRES_DB=catalog -p 127.0.0.1:5432:5432 -d postgres:17
docker run --name fastapi-mysql -e MYSQL_DATABASE=catalog -e MYSQL_USER=school -e MYSQL_PASSWORD=local-only -e MYSQL_ROOT_PASSWORD=local-root-only -p 127.0.0.1:3306:3306 -d mysql:8.4
python -m pip install 'psycopg[binary]>=3,<4' 'pymysql>=1.1,<2' 'alembic>=1.14,<2'
```

Each `docker run` starts a named container. `-e` supplies an environment variable, `-p` maps a host port to a container port, `-d` detaches from the terminal, and the final name selects an image/version family. The selected database versions are supported teaching baselines, not claims of newest releases. These commands omit durable external volumes: deleting the container loses its local data. Chapter 21 teaches volume ownership.

The pip command installs Psycopg's binary distribution, the pure-Python MySQL driver and Alembic. Some MySQL authentication configurations require `pymysql[rsa]`; install that extra if your server/driver requires it rather than weakening server authentication. Database startup takes time. Inspect `docker logs fastapi-pg` or `docker logs fastapi-mysql` if connection attempts initially fail. `docker stop fastapi-pg` stops that lab container without deleting it; `docker start fastapi-pg` restarts it.

## Configure the chapter 11 app for another database

An **environment variable** is a named text setting supplied to a process. It keeps deployment choices out of source code. `os.environ` reads those settings; `os.getenv` reads with an optional default. Secrets require additional controls, discussed in chapter 20.

For `examples/sqlalchemy_app.py`, add `import os` to its imports and replace the one engine assignment with these complete lines:

```python
database_url = os.getenv("DATABASE_URL", "sqlite:///./products.db")
engine = create_engine(database_url, pool_pre_ping=True, connect_args={"check_same_thread": False} if database_url.startswith("sqlite:") else {})
```

Line 1 reads configuration with a local SQLite default. Line 2 builds the chosen engine, checks pooled connection liveness on checkout (`pool_pre_ping`), and supplies the SQLite-only argument only for SQLite. Pre-ping reduces failures from stale idle connections; it does not rescue an in-flight transaction after database failure.

Linux/macOS, choose one:

```bash
export DATABASE_URL='postgresql+psycopg://school:local-only@127.0.0.1:5432/catalog'
python -m uvicorn examples.sqlalchemy_app:app --reload
```

`export` makes the variable available to child processes. For MySQL replace the URL with `mysql+pymysql://school:local-only@127.0.0.1:3306/catalog?charset=utf8mb4`. `utf8mb4` supports full Unicode including emoji.

PowerShell equivalent:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://school:local-only@127.0.0.1:5432/catalog'
python -m uvicorn examples.sqlalchemy_app:app --reload
```

These are explicitly a modification lab; the checked-in chapter 11 app keeps its simple SQLite baseline. Do not expect setting DATABASE_URL to affect code that never reads it.

## What is a migration and why was it introduced?

A **migration** is a versioned transformation of a database schema (and sometimes data). After deployment, adding a field to a Python class does not add a column to existing databases. `create_all` skips existing tables. Deleting the database loses user data. A migration records the intentional change so each environment can apply the same sequence.

**Alembic** is SQLAlchemy's migration tool. `upgrade` applies forward changes, `downgrade` defines reversal when safe, and a revision ID identifies one step. The `alembic_version` table tracks the applied revision. **Autogeneration** compares model metadata with the database and proposes a revision; it cannot safely infer every rename, data transformation or deployment ordering decision. Review generated code.

## Complete minimal migration project

```text
alembic.ini                    # Configuration/locations, no password
examples/migrations/env.py    # Read URL and run migrations
examples/migrations/versions/0001_products.py  # Explicit initial schema
```

The existing chapter 11 `Base` provides model metadata. The following three files are complete for applying this initial revision to a **fresh** database. Stop the chapter 11 app first and use a new SQLite filename so `create_all` has not created the table already.

### File: `alembic.ini`

```ini
[alembic]
script_location = examples/migrations
prepend_sys_path = .
```

Line 1 starts Alembic's configuration section. Line 2 locates revision files and environment setup. Line 3 puts the repository root on Python's import search path. No logging setup or secrets are required for this minimal environment.

## Example

### File: `examples/migrations/env.py`

```python
import os
from alembic import context
from sqlalchemy import create_engine, pool
from examples.sqlalchemy_app import Base

url = os.getenv("DATABASE_URL", "sqlite:///./migration-demo.db")
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
```

## Code Explanation

### Line 1

Read deployment configuration without putting a database password in this file.

### Line 2

Access Alembic's current migration execution context.

### Line 3

Construct a one-off migration engine without retaining a long-lived pool.

### Line 4

Import mapped metadata for schema comparison; importing the app does not run its lifespan/create_all.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

Use a fresh local migration database unless an explicit URL is supplied.

### Line 7

Offline mode generates SQL rather than opening a database connection.

### Line 8

Configure SQL generation and model metadata.

### Line 9

Delimit migration output as a transaction where the dialect supports it.

### Line 10

Execute revision functions through the offline context.

### Line 11

Normal online mode applies changes to a real database.

### Line 12

Avoid retaining pooled connections for this short-lived migration process.

### Line 13

Open and reliably close one connection.

### Line 14

Bind revisions and autogeneration comparison to this connection.

### Line 15

Use the dialect's transactional migration behaviour.

### Line 16

Apply the pending revision operations.

### Line 17

Release any remaining engine resources.

## Example

### File: `examples/migrations/versions/0001_products.py`

```python
from alembic import op
import sqlalchemy as sa

revision = "0001_products"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.UniqueConstraint("name", name="uq_products_name"),
        sa.CheckConstraint("price_minor >= 0", name="ck_products_price"),
    )

def downgrade():
    op.drop_table("products")
```

## Code Explanation

### Line 1

Alembic operations express schema changes through the configured database connection.

### Line 2

Use SQLAlchemy's column and constraint types under a short namespace.

### Line 3

This blank line separates logical parts; Python does not execute it.

### Line 4

Identify this migration uniquely.

### Line 5

This is the root revision, with no predecessor.

### Line 6

No separate migration branch is defined.

### Line 7

No extra cross-branch revision dependency exists.

### Line 8

This blank line separates logical parts; Python does not execute it.

### Line 9

Describe the forward schema change.

### Line 10

Ask Alembic to create the table using the target dialect.

### Line 11

Match the ORM table's name.

### Line 12

Add a generated integer primary key.

### Line 13

Store a required bounded name.

### Line 14

Store a required integer price.

### Line 15

Enforce duplicate-name protection.

### Line 16

Enforce nonnegative price at the storage boundary.

### Line 17

Finish the table definition.

### Line 18

This blank line separates logical parts; Python does not execute it.

### Line 19

Define reversal for a disposable lab; this is destructive for real data.

### Line 20

Remove the table and all rows; never run casually against production.

## Commands and expected result

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history
```

Line 1 applies all pending revisions; `head` means latest revision in this simple linear history. Line 2 shows the current database revision, expected `0001_products (head)`. Line 3 lists revision history. If DATABASE_URL remains set from the earlier server lab, these commands use that database; unset it with `unset DATABASE_URL` in bash or `Remove-Item Env:DATABASE_URL` in PowerShell to use `migration-demo.db`.

For generating future revisions, the repository includes Alembic's standard `script.py.mako` template beside `env.py`. A **template** is a file used to generate a new revision's boilerplate. After changing models run:

```bash
python -m alembic revision --autogenerate -m "describe the schema change"
python -m alembic upgrade head
```

The first command compares schema and creates a revision file; `-m` supplies its human description. **Read and edit that file before the second command.** Do not create an empty revision merely to pretend a model change was migrated. `alembic init` is unnecessary for this already supplied environment; for a new project `python -m alembic init migrations` generates the initial environment/template for you.

## What happens internally / production use

Alembic loads config, runs env.py, connects using the chosen driver, reads the revision table, executes pending upgrade functions, and records progress. Dialect-specific DDL (Data Definition Language, commands changing schema) may have different transactional guarantees; do not assume rollback can reverse every MySQL schema operation.

In production run migrations once as a deployment step, not from every web worker. Use **expand/contract** changes: add a compatible column, deploy code supporting old/new states, backfill existing rows in bounded batches, switch readers, then remove obsolete schema in a later release. A backfill populates existing records; adding `NOT NULL` immediately to a populated table can fail or block traffic.

## When to use / not use; common mistakes and best practices

Use migrations for any database whose data matters across releases. `create_all` is enough for disposable tests, not existing production schemas. Never use `stamp head` to conceal a mismatch: stamping records a revision without applying its changes. Avoid credentials in committed URLs, public database ports, unreviewed autogeneration and destructive downgrades mistaken for a safe rollback plan. Back up, test restores and rehearse migrations on production-like data sizes.

## Practice / Solution

**Beginner:** Apply the supplied migration to fresh migration-demo.db; `current` shows 0001_products.

**Intermediate:** Run upgrade head twice. Expected: the second run makes no duplicate table because the revision is already recorded.

**Challenge:** Add nullable `description` without losing products. The migration's upgrade operation is `op.add_column("products", sa.Column("description", sa.String(500), nullable=True))`; downgrade would `op.drop_column("products", "description")`, which loses descriptions. Add the matching ORM field, generate/review the revision, apply it once and read preexisting rows. The new field is null until backfilled. For SQLite changes requiring table recreation, use Alembic's batch migration facilities rather than assuming all ALTER operations exist.

## Summary

Changing database engines requires the correct driver/configuration and integration tests. Changing schemas requires reviewed, ordered migrations—not deleting user data.

## Complete revision-generation template

### File: `examples/migrations/script.py.mako`

```mako
"""${message}"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
```

This is a Mako template, **not executable Python until Alembic renders it**. Line 1 inserts the revision message as a docstring. Lines 2–3 import migration operations/types into generated files. Line 4 inserts optional generated imports. Line 5 is spacing. Lines 6–9 render revision identity, predecessor, branch labels and extra dependencies using valid Python representations. Lines 10–11 separate definitions. Line 12 declares upgrade; line 13 inserts generated forward operations, or pass when none exist. Lines 14–15 separate functions. Line 16 declares downgrade; line 17 inserts reverse operations. The template is supplied so the revision command works without an undocumented initialization step. Review the resulting Python; a code generator cannot understand all business-safe migrations.
