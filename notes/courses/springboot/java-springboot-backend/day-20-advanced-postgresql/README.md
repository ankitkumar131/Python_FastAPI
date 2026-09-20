# Day 20 — Indexes, transactions, and Flyway migrations

## 🎯 Learning Objectives

By the end of this day you will understand:

- Why indexes exist
- Why ddl-auto=update is not production
- Flyway versioned SQL
- Transactions and constraints
- Query optimization basics

---

# 1. Concept — schema evolution

`spring.jpa.hibernate.ddl-auto=update` mutates the DB silently. Production needs **versioned SQL** in git: Flyway (or Liquibase).

## Flyway

Files:

```text
src/main/resources/db/migration/V1__create_employees.sql
src/main/resources/db/migration/V2__add_department.sql
```

Naming: `V<version>__<description>.sql` (two underscores).

```properties
spring.jpa.hibernate.ddl-auto=validate
spring.flyway.enabled=true
```

On startup Flyway applies new versions, then Hibernate **validates** entities match.

## Indexes

```sql
CREATE INDEX idx_employees_email ON employees (email);
```

Speeds WHERE/JOIN; slows writes slightly. Unique constraints already index.

## EXPLAIN

```sql
EXPLAIN ANALYZE SELECT * FROM employees WHERE email = 'ada@example.com';
```

Look for Seq Scan vs Index Scan on large tables.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-20
cd ~/springboot-practice/day-20
```

Answer key: `java-springboot-backend/practical/day-20/`

Add Flyway dependency. Turn ddl-auto to validate after first migration.

| # | File | Why it exists |
|---|---|---|
| 1 | `pom.xml` | jpa + postgres + flyway |
| 2 | `application.properties` | validate + flyway |
| 3 | `V1__create_employees.sql` | versioned schema |

```bash
mvn spring-boot:run
# Flyway creates flyway_schema_history
```

Never edit V1 after it ran on an environment. Add V2 instead.

---

# Common Mistakes

1. Changing a applied migration checksum.
2. ddl-auto=update + Flyway together fighting.
3. Missing two underscores.
4. Indexing every column.
5. No unique constraint, only Java check.

---

# Practical Exercise

1. Start with empty DB; watch V1 apply.
2. Add V2 column; restart.
3. EXPLAIN a query.
4. Break checksum on purpose; read error.
5. Set ddl-auto=validate.

---

# Mini Project

V2__add_department.sql adding department TEXT.

---

# Interview Questions

## Easy

### Q1. Why not ddl-auto=update in prod?

**Difficulty:** Easy

**Answer:**

No history, unsafe diffs, not reviewable SQL.

**Simple Explanation:**

No history, unsafe diffs, not reviewable SQL.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. What is Flyway?

**Difficulty:** Easy

**Answer:**

Versioned migration tool that runs SQL on startup.

**Simple Explanation:**

Versioned migration tool that runs SQL on startup.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Naming convention?

**Difficulty:** Easy

**Answer:**

V1__description.sql with two underscores.

**Simple Explanation:**

V1__description.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. validate vs update?

**Difficulty:** Easy

**Answer:**

validate checks; update mutates.

**Simple Explanation:**

validate checks; update mutates.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. What is flyway_schema_history?

**Difficulty:** Easy

**Answer:**

Table of applied versions and checksums.

**Simple Explanation:**

Table of applied versions and checksums.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. Why indexes?

**Difficulty:** Medium

**Answer:**

Speed reads; trade write cost.

**Simple Explanation:**

Speed reads; trade write cost.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Unique vs index?

**Difficulty:** Medium

**Answer:**

Unique is a constraint that uses an index.

**Simple Explanation:**

Unique is a constraint that uses an index.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. EXPLAIN?

**Difficulty:** Medium

**Answer:**

Shows the query plan.

**Simple Explanation:**

Shows the query plan.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Can you edit V1?

**Difficulty:** Medium

**Answer:**

Not after apply; add V2.

**Simple Explanation:**

Not after apply; add V2.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Checksum mismatch?

**Difficulty:** Medium

**Answer:**

File changed after migrate; repair only with care.

**Simple Explanation:**

File changed after migrate; repair only with care.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Transactional DDL in PG?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Most DDL is transactional — unlike MySQL.

**Simple Explanation:**

Most DDL is transactional — unlike MySQL.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Partial index?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Index WHERE active = true — PG feature.

**Simple Explanation:**

Index WHERE active = true — PG feature.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Connection pool?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

HikariCP; size for workload.

**Simple Explanation:**

HikariCP; size for workload.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Lock timeout?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Long transactions block; keep tx short.

**Simple Explanation:**

Long transactions block; keep tx short.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Dev vs prod ddl?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

update or create-drop in tests; Flyway+validate in prod.

**Simple Explanation:**

update or create-drop in tests; Flyway+validate in prod.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.


---

# Day-End Practice

1. Start with empty DB; watch V1 apply.
2. Add V2 column; restart.
3. EXPLAIN a query.
4. Break checksum on purpose; read error.
5. Set ddl-auto=validate.

---

# Quick Revision

- Flyway V1__.
- ddl-auto=validate in prod.
- Indexes for reads.
- Don’t edit old migrations.

---

# What You Should Be Able To Explain

- Flyway
- why not update in prod
- index tradeoff
- EXPLAIN
- checksum

**Next:** [Day 21](../day-21-mongodb-fundamentals/README.md)
