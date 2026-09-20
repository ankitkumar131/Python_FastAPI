# Day 30 — E-Commerce backend capstone + interview revision

## 🎯 Learning Objectives

By the end of this day you will understand:

- Combine every layer into one e-commerce API
- Auth JWT roles
- Products categories cart orders
- Postgres + optional Mongo reviews
- Explain the project in an interview

---

# 1. Concept — capstone

Build **E-Commerce Backend API**.

```text
Client → REST → Controller → Service → Repository → PostgreSQL
                                      ↘ Mongo (reviews)
```

## Features you must implement

### Auth
Register, login, JWT, roles USER/ADMIN

### Users
CRUD + profile (USER self, ADMIN all)

### Products
CRUD (ADMIN write), search, filter, pagination, sorting

### Categories
CRUD ADMIN

### Cart
Add/remove/update quantity, get cart (per user)

### Orders
Create from cart, list mine, ADMIN update status

### Cross-cutting
Validation, ApiError, DTOs, Flyway, tests for service+controller, swagger, docker compose

## Suggested packages

```text
com.course.shop
  config security controller service repository
  entity dto mapper exception
```

## Mongo optional

`reviews` collection: productId, userId, stars, body. Explain: reviews are write-heavy, schema-flexible, not joined into payments.

## Interview script

> I built a layered Spring Boot API. Controllers speak DTOs. Services own transactions. Postgres holds orders; Mongo holds reviews. Auth is stateless JWT. Flyway migrates. Tests use Mockito and MockMvc. Docker Compose runs app + DBs.

## 30-day revision checklist

- IoC / constructor injection
- REST status codes
- DTO vs entity
- JPA N+1
- JWT filter
- ddl-auto vs Flyway

Resume line: “Designed and implemented a production-style e-commerce REST API in Java 21 / Spring Boot 3 with JWT, PostgreSQL, and Docker.”


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-30
cd ~/springboot-practice/day-30
```

Answer key: `java-springboot-backend/practical/day-30/`

Create ~/springboot-practice/shop from Initializr (web, validation, security, data-jpa, postgres, flyway, actuator). Copy patterns from practical days 15, 17, 19, 20, 25, 26, 27, 28, 29.

| # | File | Why it exists |
|---|---|---|
| 1 | `README-SHOP.md` | feature list |
| 2 | `domain.md` | entities |
| 3 | `http-examples.md` | sample calls |

```bash
# You build this. Use previous practical folders as a cookbook.
```

Type **your** shop. The answer key is a blueprint, not a 200-class dump. Implement vertically: auth → products → cart → orders.

File-by-file suggested order:

1. Entity Category, Product, ShopUser, CartItem, ShopOrder, OrderLine
2. Flyway V1 schema
3. Repositories
4. DTOs + mappers
5. Services + @Transactional
6. Controllers
7. Security + JWT from Day 25
8. Advice from Day 12
9. Tests from Day 27
10. Dockerfile from Day 29


---

# Common Mistakes

1. Starting with Docker before a working local API.
2. No DTOs.
3. God service class.
4. Skipping tests.
5. Cannot explain N+1 or JWT in the interview.

---

# Practical Exercise

1. Write the interview paragraph aloud.
2. ERD on paper.
3. List 10 endpoints with status codes.
4. Pick 5 hard questions from earlier days.
5. Record a 3-minute project walkthrough.

---

# Mini Project

Ship MVP: register/login, product list, add to cart, place order.

---

# Interview Questions

## Easy

### Q1. Walk me through your project.

**Difficulty:** Easy

**Answer:**

Layers, JWT, Postgres orders, optional Mongo reviews, Flyway, Docker.

**Simple Explanation:**

Layers, JWT, Postgres orders, optional Mongo reviews, Flyway, Docker.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Why DTO?

**Difficulty:** Easy

**Answer:**

Hide internals, stable contract, avoid JSON cycles.

**Simple Explanation:**

Hide internals, stable contract, avoid JSON cycles.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. How is cart stored?

**Difficulty:** Easy

**Answer:**

CartItem table user_id+product_id+qty, not in HTTP session.

**Simple Explanation:**

CartItem table user_id+product_id+qty, not in HTTP session.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Order creation transaction?

**Difficulty:** Easy

**Answer:**

@Transactional: decrement stock, insert order+lines, clear cart.

**Simple Explanation:**

@Transactional: decrement stock, insert order+lines, clear cart.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Idempotent order POST?

**Difficulty:** Easy

**Answer:**

Idempotency key header or client order uuid.

**Simple Explanation:**

Idempotency key header or client order uuid.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. How do you paginate products?

**Difficulty:** Medium

**Answer:**

Pageable + indexes on category.

**Simple Explanation:**

Pageable + indexes on category.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. N+1 on order lines?

**Difficulty:** Medium

**Answer:**

join fetch or DTO query.

**Simple Explanation:**

join fetch or DTO query.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. How JWT authorized?

**Difficulty:** Medium

**Answer:**

Filter sets SecurityContext; hasRole on admin.

**Simple Explanation:**

Filter sets SecurityContext; hasRole on admin.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Secret management?

**Difficulty:** Medium

**Answer:**

Env vars, not git.

**Simple Explanation:**

Env vars, not git.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. How tested?

**Difficulty:** Medium

**Answer:**

Service unit tests; MockMvc for controllers; one IT with testcontainers if possible.

**Simple Explanation:**

Service unit tests; MockMvc for controllers; one IT with testcontainers if possible.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Why Mongo reviews?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Nested, high write, no relational integrity needed.

**Simple Explanation:**

Nested, high write, no relational integrity needed.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Failure 500 debug?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Logs, actuator, SQL logs, exception advice.

**Simple Explanation:**

Logs, actuator, SQL logs, exception advice.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Scale bottleneck?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

DB indexes, N+1, payload size, pool size.

**Simple Explanation:**

DB indexes, N+1, payload size, pool size.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Version API?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Don’t until breaking; then /v2.

**Simple Explanation:**

Don’t until breaking; then /v2.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. What would you add next?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Outbox, payments adapter, Redis cart — not before MVP quality.

**Simple Explanation:**

Outbox, payments adapter, Redis cart — not before MVP quality.

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

1. Write the interview paragraph aloud.
2. ERD on paper.
3. List 10 endpoints with status codes.
4. Pick 5 hard questions from earlier days.
5. Record a 3-minute project walkthrough.

---

# Quick Revision

- Build the shop.
- Explain it in 8 sentences.
- Revise injection, JPA, JWT.
- Docker compose the stack.

---

# What You Should Be Able To Explain

- end-to-end architecture
- order transaction
- JWT in this app
- why two databases
- interview story
