# Day 19 — Employee Management API on PostgreSQL

## 🎯 Learning Objectives

By the end of this day you will understand:

- Connect Boot to Postgres
- UUID primary keys with Hibernate
- Employee CRUD + pagination
- Same layered ideas as MySQL days

---

# 1. Concept

Same architecture as Day 15, different database.

```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/app_db
spring.datasource.username=app
spring.datasource.password=secret
spring.jpa.hibernate.ddl-auto=update
```

Driver: `org.postgresql:postgresql` (starter pulls it if listed).

`@UuidGenerator` (Hibernate 6) fills UUID ids. Paths use `UUID id`.

**This is simplified:** exceptions should be Day 12 types; wire them as an exercise.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-19
cd ~/springboot-practice/day-19
```

Answer key: `java-springboot-backend/practical/day-19/`

Postgres running. Maven JPA + postgres + validation. Package com.course.day19.

| # | File | Why it exists |
|---|---|---|
| 1 | `Employee.java` | UUID id |
| 2 | `EmployeeRequest/Response` | DTOs |
| 3 | `EmployeeRepository` | JpaRepository<Employee,UUID> |
| 4 | `EmployeeController` | CRUD+page |

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/employees -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@example.com"}'
```

Copy the UUID from POST into GET /api/employees/{id}.

---

# Common Mistakes

1. Using Long id with uuid column.
2. MySQL driver on Postgres URL.
3. Not quoting UUID in curl.
4. ddl-auto on prod.
5. Returning entity.

---

# Practical Exercise

1. POST employee.
2. GET by UUID.
3. GET page.
4. Duplicate email.
5. psql SELECT.

---

# Mini Project

Add JSONB `attrs` mapped with `@JdbcTypeCode(SqlTypes.JSON)` (optional stretch).

---

# Interview Questions

## Easy

### Q1. JpaRepository second type param?

**Difficulty:** Easy

**Answer:**

The id type — UUID here, Long on MySQL users.

**Simple Explanation:**

The id type — UUID here, Long on MySQL users.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. How is UUID generated?

**Difficulty:** Easy

**Answer:**

Hibernate @UuidGenerator / DB default.

**Simple Explanation:**

Hibernate @UuidGenerator / DB default.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. URL difference vs MySQL?

**Difficulty:** Easy

**Answer:**

jdbc:postgresql and port 5432.

**Simple Explanation:**

jdbc:postgresql and port 5432.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Why DTO still?

**Difficulty:** Easy

**Answer:**

Same leak/coupling reasons.

**Simple Explanation:**

Same leak/coupling reasons.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Page on employees?

**Difficulty:** Easy

**Answer:**

Pageable works independently of DB vendor.

**Simple Explanation:**

Pageable works independently of DB vendor.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. existsByEmail?

**Difficulty:** Medium

**Answer:**

Query method; unique constraint still required.

**Simple Explanation:**

Query method; unique constraint still required.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Can we reuse Day 15 service?

**Difficulty:** Medium

**Answer:**

Yes with id type changes.

**Simple Explanation:**

Yes with id type changes.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Hibernate dialect?

**Difficulty:** Medium

**Answer:**

Boot 3 picks PostgreSQLDialect from URL/driver.

**Simple Explanation:**

Boot 3 picks PostgreSQLDialect from URL/driver.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. UUID in path?

**Difficulty:** Medium

**Answer:**

Spring converts string to UUID; invalid → 400.

**Simple Explanation:**

Spring converts string to UUID; invalid → 400.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Why not serialize password?

**Difficulty:** Medium

**Answer:**

N/A here; still never expose secrets.

**Simple Explanation:**

N/A here; still never expose secrets.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Flyway next why?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

ddl-auto is not a migration history.

**Simple Explanation:**

ddl-auto is not a migration history.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. JSONB mapping?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Hypersistence / @JdbcTypeCode.

**Simple Explanation:**

Hypersistence / @JdbcTypeCode.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Connection refused 5432?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Container not running.

**Simple Explanation:**

Container not running.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Case of table names?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Postgres folds unquoted to lowercase.

**Simple Explanation:**

Postgres folds unquoted to lowercase.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Interview demo?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

POST, copy UUID, GET, show psql.

**Simple Explanation:**

POST, copy UUID, GET, show psql.

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

1. POST employee.
2. GET by UUID.
3. GET page.
4. Duplicate email.
5. psql SELECT.

---

# Quick Revision

- Postgres JDBC.
- UUID ids.
- Same layers.
- Pagination works the same.

---

# What You Should Be Able To Explain

- UUID PK in JPA
- Postgres URL
- id type on JpaRepository
- path UUID conversion
- reuse of layers

**Next:** [Day 20](../day-20-advanced-postgresql/README.md)
