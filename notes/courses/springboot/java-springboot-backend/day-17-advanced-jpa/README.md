# Day 17 — Advanced JPA: JPQL, pagination, N+1, transactions

## 🎯 Learning Objectives

By the end of this day you will understand:

- JPQL vs native queries
- Pageable / Page vs Slice
- LAZY N+1 and join fetch
- @Transactional and flush
- Locking basics

---

# 1. Concept

Pagination, query language, and the N+1 problem are what separate tutorial CRUD from production APIs.

## Pagination

```text
GET /api/products?page=0&size=10&sort=name,asc
GET /api/products?category=electronics
GET /api/products?q=key
```

Spring binds `page`, `size`, `sort` to `Pageable`. Return `Page<T>` includes total count (extra COUNT query). `Slice` skips the count.

## JPQL

JPQL uses **entity names and fields**, not tables:

```java
@Query("SELECT p FROM Product p WHERE LOWER(p.name) LIKE ...")
```

Native SQL: `@Query(value="SELECT * FROM product WHERE ...", nativeQuery=true)` — use when you need DB-specific features.

## N+1

1 query for parents + N queries for children. Fix: `JOIN FETCH`, `@EntityGraph`, DTO projections. Symptom: log full of `SELECT ... FROM orders`.

## Transactions

`@Transactional` on the service: session open, dirty checking, atomic writes. Self-invocation (`this.save()`) skips the proxy.

## Locking

`@Version` optimistic lock → `OptimisticLockException` on stale updates. Pessimistic: `PESSIMISTIC_WRITE` rare, blocks rows.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-17
cd ~/springboot-practice/day-17
```

Answer key: `java-springboot-backend/practical/day-17/`

MySQL + JPA. Package com.course.day17. Returning entity here is simplified for pagination teaching — use DTOs in real code.

| # | File | Why it exists |
|---|---|---|
| 1 | `Product.java` | entity |
| 2 | `ProductRepository.java` | JPQL + Page |
| 3 | `ProductController.java` | Pageable |

```bash
mvn spring-boot:run
curl 'http://localhost:8080/api/products?page=0&size=5&sort=name,asc'
```

POST a few products first. Then page/filter/search. Read SQL logs for COUNT + SELECT.

---

# Common Mistakes

1. Returning Page<Entity> in production APIs (use DTO).
2. N+1 ignored because 'it works on 3 rows'.
3. Native query with wrong column aliases.
4. Missing @Param.
5. Huge size=100000.

---

# Practical Exercise

1. POST 15 products.
2. Page through them.
3. Filter category.
4. Search q=.
5. Count SELECT vs COUNT in logs.

---

# Mini Project

Add `findByPriceCentsLessThan(int, Pageable)`.

---

# Interview Questions

## Easy

### Q1. What is Pageable?

**Difficulty:** Easy

**Answer:**

An object with page index, size, and sort that Spring binds from query params.

**Simple Explanation:**

An object with page index, size, and sort that Spring binds from query params.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Page vs Slice?

**Difficulty:** Easy

**Answer:**

Page runs COUNT for totals; Slice only knows if next exists.

**Simple Explanation:**

Page runs COUNT for totals; Slice only knows if next exists.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. What is JPQL?

**Difficulty:** Easy

**Answer:**

Object query language using entities, translated to SQL by Hibernate.

**Simple Explanation:**

Object query language using entities, translated to SQL by Hibernate.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Native query?

**Difficulty:** Easy

**Answer:**

Raw SQL; loses some portability.

**Simple Explanation:**

Raw SQL; loses some portability.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. What is N+1?

**Difficulty:** Easy

**Answer:**

One query plus one per child.

**Simple Explanation:**

One query plus one per child.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. How to fix N+1?

**Difficulty:** Medium

**Answer:**

join fetch, entity graph, batch size, DTO query.

**Simple Explanation:**

join fetch, entity graph, batch size, DTO query.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Default page size?

**Difficulty:** Medium

**Answer:**

You should set @PageableDefault; don't trust clients.

**Simple Explanation:**

You should set @PageableDefault; don't trust clients.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. @Transactional self-invocation?

**Difficulty:** Medium

**Answer:**

Bypasses proxy; no new transaction.

**Simple Explanation:**

Bypasses proxy; no new transaction.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Optimistic lock?

**Difficulty:** Medium

**Answer:**

@Version column; update if version matches.

**Simple Explanation:**

@Version column; update if version matches.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. When pessimistic?

**Difficulty:** Medium

**Answer:**

High contention short critical sections.

**Simple Explanation:**

High contention short critical sections.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Why COUNT on Page?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

To fill totalElements for UI paginators.

**Simple Explanation:**

To fill totalElements for UI paginators.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. JOIN FETCH + Page pitfall?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

HHibernate can paginate in memory incorrectly with collections; use two queries or blazes.

**Simple Explanation:**

HHibernate can paginate in memory incorrectly with collections; use two queries or blazes.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. flush vs commit?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Flush syncs SQL; commit ends transaction.

**Simple Explanation:**

Flush syncs SQL; commit ends transaction.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. readOnly transaction?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Optimization hint; no writes expected.

**Simple Explanation:**

Optimization hint; no writes expected.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. How would you sort safely?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Whitelist sort properties; don't pass raw client column names to native SQL.

**Simple Explanation:**

Whitelist sort properties; don't pass raw client column names to native SQL.

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

1. POST 15 products.
2. Page through them.
3. Filter category.
4. Search q=.
5. Count SELECT vs COUNT in logs.

---

# Quick Revision

- Pageable query params.
- JPQL uses entities.
- N+1 is extra SELECTs.
- @Transactional on services.
- @Version for optimistic lock.

---

# What You Should Be Able To Explain

- Pageable
- JPQL vs SQL
- N+1
- join fetch
- @Version

**Next:** [Day 18](../day-18-postgresql-fundamentals/README.md)
