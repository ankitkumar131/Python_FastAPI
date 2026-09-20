# day-13-mysql-fundamentals

## Day 13 — Database fundamentals and MySQL

### 🎯 Learning Objectives

By the end of this day you will understand:

* What a relational database is (tables, rows, columns, keys)
* Primary keys, foreign keys, unique constraints
* CRUD in SQL, INNER JOIN, indexes at a glance
* Normalization in one page
* How Spring Boot will connect tomorrow (JDBC URL)

***

## 1. Concept — relational databases

### What is it?

Data in **tables** with typed columns. Rows are records. Relationships use **keys**, not nested documents.

### Why backends need it?

Durable, queryable, multi-user data with transactions (ACID). Your HashMap was none of those.

### Real-world analogy

Spreadsheets that refuse invalid cells and can lock a row while you edit.

### Backend example

`users.id` is referenced by `orders.user_id`.

***

## 2. Keys and constraints

* **PRIMARY KEY** — unique identity, never null
* **FOREIGN KEY** — must point at an existing parent (or be null if allowed)
* **UNIQUE** — email
* **NOT NULL**, **CHECK** (MySQL 8 has CHECK)

***

## 3. SQL you must type

See `practical/day-13/schema.sql`. Type it in MySQL Workbench or `mysql` client.

```
INSERT → create
SELECT → read
UPDATE → update
DELETE → delete
JOIN   → combine tables
```

***

## 4. JDBC URL (for tomorrow)

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/app_db
spring.datasource.username=root
spring.datasource.password=secret
```

| Part           | Meaning         |
| -------------- | --------------- |
| jdbc:mysql     | driver protocol |
| localhost:3306 | host/port       |
| app\_db        | database name   |

**Do not commit real passwords.** `secret` is a local learning password.

***

## 5. Access denied / connection refused

| Error              | Meaning           | Fix                 |
| ------------------ | ----------------- | ------------------- |
| Connection refused | MySQL not running | start Docker/native |
| Access denied      | bad user/password | match container env |
| Unknown database   | no app\_db        | CREATE DATABASE     |

Docker from the setup guide:

```bash
docker run --name course-mysql -e MYSQL_ROOT_PASSWORD=secret -e MYSQL_DATABASE=app_db -p 3306:3306 -d mysql:8.4
```

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-13
cd ~/springboot-practice/day-13
```

Answer key: `java-springboot-backend/practical/day-13/`

You do **not** need Maven today. Create `~/springboot-practice/day-13/` and a file `schema.sql`. Run it against MySQL.

| # | File         | Why it exists                |
| - | ------------ | ---------------------------- |
| 1 | `schema.sql` | tables, FK, sample CRUD/join |
| 2 | `notes.md`   | JDBC URL reminder            |

```bash
mysql -h 127.0.0.1 -u root -psecret app_db < schema.sql
```

Type `schema.sql` from the answer key **by hand**. Read every clause. Then run `SELECT` yourself.

**Normalization:** don’t store `user_email` on every order row if you already have `user_id`. One source of truth.

**Index:** `UNIQUE` on email already creates an index. Extra indexes speed `WHERE`/`JOIN` and slow `INSERT`. Day 20.

***

## Common Mistakes

1. **Selecting \* in production APIs without need.**
2. **No UNIQUE on email** — duplicates until you notice.
3. **Missing FK** — orphan orders.
4. **Using MySQL reserved words as table names.**
5. **Hardcoding production passwords.**

***

## Practical Exercise

1. Create app\_db and run schema.sql.
2. Insert two users; join their orders.
3. Try inserting an order with user\_id=999; observe FK error.
4. Try two users with the same email; observe unique error.
5. Write a SELECT that lists users without orders (LEFT JOIN).

***

## Mini Project

Add table `profiles` (user\_id PK/FK, bio TEXT) one-to-one with users. Insert a profile for Ada.

***

## Interview Questions

### Easy

#### Q1. What is a primary key?

**Difficulty:** Easy

**Answer:**

A unique identifier for a row, not null.

**Simple Explanation:**

The row’s id.

**Example:**

id BIGINT PRIMARY KEY

**Interview Tip:**

Usually surrogate BIGINT/UUID.

**Common Follow-up Question:**

Natural vs surrogate?

#### Q2. What is a foreign key?

**Difficulty:** Easy

**Answer:**

A column that references a primary key in another table.

**Simple Explanation:**

A pointer that the DB enforces.

**Example:**

orders.user\_id

**Interview Tip:**

Prevents orphans.

**Common Follow-up Question:**

ON DELETE CASCADE?

#### Q3. What is SQL?

**Difficulty:** Easy

**Answer:**

Language to define and query relational data.

**Simple Explanation:**

Talk to tables.

**Example:**

SELECT \* FROM users

**Interview Tip:**

Not Java.

**Common Follow-up Question:**

DDL vs DML?

#### Q4. What does UNIQUE do?

**Difficulty:** Easy

**Answer:**

Rejects duplicate values (except multiple nulls in some DBs).

**Simple Explanation:**

Only one of these.

**Example:**

email UNIQUE

**Interview Tip:**

Backs existsByEmail.

**Common Follow-up Question:**

Index?

#### Q5. What is a JOIN?

**Difficulty:** Easy

**Answer:**

Combine rows from tables using a related column.

**Simple Explanation:**

Zip two lists by id.

**Example:**

users JOIN orders

**Interview Tip:**

INNER vs LEFT.

**Common Follow-up Question:**

When Mongo instead?

### Medium

#### Q1. INNER vs LEFT JOIN?

**Difficulty:** Medium

**Answer:**

INNER: only matches. LEFT: all left rows, nulls on the right if no match.

**Simple Explanation:**

Keep users without orders? LEFT.

**Example:**

LEFT JOIN orders

**Interview Tip:**

NULLs in right columns.

**Common Follow-up Question:**

RIGHT/FULL.

#### Q2. What is normalization?

**Difficulty:** Medium

**Answer:**

Reduce redundancy by splitting tables and relating them with keys. 3NF as a practical target.

**Simple Explanation:**

One fact, one place.

**Example:**

email not copied onto orders

**Interview Tip:**

Denormalize for read speed carefully.

**Common Follow-up Question:**

When to denormalize.

#### Q3. Why indexes?

**Difficulty:** Medium

**Answer:**

B-trees (usually) speed lookups/sorts. UNIQUE is an index. Too many hurt writes.

**Simple Explanation:**

A book index.

**Example:**

INDEX(email)

**Interview Tip:**

EXPLAIN your query.

**Common Follow-up Question:**

Day 20.

#### Q4. ACID?

**Difficulty:** Medium

**Answer:**

Atomicity Consistency Isolation Durability — transaction guarantees.

**Simple Explanation:**

All or nothing, survives crash.

**Example:**

Transfer money

**Interview Tip:**

JPA @Transactional.

**Common Follow-up Question:**

Isolation levels.

#### Q5. JDBC URL pieces?

**Difficulty:** Medium

**Answer:**

protocol, host, port, database, params.

**Simple Explanation:**

The address of MySQL.

**Example:**

jdbc:mysql://localhost:3306/app\_db

**Interview Tip:**

timezone params sometimes needed.

**Common Follow-up Question:**

useSSL=false old tutorials — prefer TLS in prod.

### Hard

#### Q1. What happens on FK violation from Spring?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

MySQL error 1452 → connector → Spring DataIntegrityViolationException. Map to 409/400.

**Simple Explanation:**

The DB is the last guard.

**Example:**

insert orphan order

**Interview Tip:**

Don’t rely only on service checks.

**Common Follow-up Question:**

Race on unique email.

#### Q2. AUTO\_INCREMENT vs UUID?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Long ids are small and sequential (page friendly). UUIDs distribute, hide counts, work offline. MySQL 8 UUID functions exist; sequential still wins for clustered PK.

**Simple Explanation:**

Pick for access pattern.

**Example:**

BIGINT PK today

**Interview Tip:**

Postgres UUID Day 18.

**Common Follow-up Question:**

Hot page contention.

#### Q3. Why not store lists as comma-separated strings?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Can’t join/index/validate elements. That’s 1NF violation. Use a table or JSON column with eyes open.

**Simple Explanation:**

Don’t smash lists into a cell.

**Example:**

roles table or JSON

**Interview Tip:**

Mongo embeds lists naturally.

**Common Follow-up Question:**

CSV columns in legacy apps.

#### Q4. Connection refused vs access denied?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Network/process vs credentials. Debug in that order.

**Simple Explanation:**

Is it up? Then am I allowed?

**Example:**

docker ps

**Interview Tip:**

Day 5 port-in-use analog.

**Common Follow-up Question:**

Firewall.

#### Q5. How would you design users↔orders?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

1:N orders.user\_id FK. Index user\_id. Don’t put order ids on users.

**Simple Explanation:**

Parent has many children via FK on child.

**Example:**

schema.sql

**Interview Tip:**

Owning side in JPA Day 16.

**Common Follow-up Question:**

Cascade delete caution.

***

## Day-End Practice

1. Create app\_db and run schema.sql.
2. Insert two users; join their orders.
3. Try inserting an order with user\_id=999; observe FK error.
4. Try two users with the same email; observe unique error.
5. Write a SELECT that lists users without orders (LEFT JOIN).

***

## Quick Revision

* Tables, PK, FK, UNIQUE.
* SQL CRUD + JOIN.
* JDBC URL.
* DB enforces rules Java might miss.
* Docker MySQL for local.

***

## What You Should Be Able To Explain

* PK vs FK
* UNIQUE email
* INNER vs LEFT
* JDBC URL
* Why HashMap is not enough

**Next:** [Day 14](day-14-spring-data-jpa.md)
