# Day 14 — JPA, Hibernate, and Spring Data repositories

## 🎯 Learning Objectives

By the end of this day you will understand:

- ORM, JPA, Hibernate — who does what
- @Entity @Id @GeneratedValue @Column @Table
- JpaRepository and query methods
- ddl-auto=update for learning vs production
- Persistence context at a high level

---

# 1. Concept — ORM / JPA / Hibernate

## What is it?

- **ORM** — map objects to tables
- **JPA** — the **specification** (annotations, EntityManager)
- **Hibernate** — the usual **implementation** Boot uses
- **Spring Data JPA** — you write an interface; Spring generates the impl

## Why?

JDBC SQL by hand is verbose. ORM is not magic SQL-free — you still must understand tables (Day 13).

## Real-world analogy

JPA is the electrical code. Hibernate is the wiring in your house. Spring Data is the light switch.

## Backend example

```java
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
}
```

No class body. `findByEmail` is parsed into `WHERE email = ?`.

---

# 2. Entity rules

- `@Entity` class
- `@Id`
- No-arg constructor (protected is fine) for Hibernate
- Don’t use a record

`GenerationType.IDENTITY` fits MySQL AUTO_INCREMENT.

---

# 3. JpaRepository vs CrudRepository

`JpaRepository` extends `PagingAndSortingRepository` extends `CrudRepository`. You get `save`, `findById`, `findAll`, `deleteById`, `flush`, pagination.

---

# 4. ddl-auto

| Value | Use |
|---|---|
| none | production with Flyway |
| validate | check entity vs schema |
| update | **learning only** — mutates schema |
| create-drop | tests |

**Never** `update` as your production migration strategy. Day 20 Flyway.

---

# 5. Persistence context (preview)

Hibernate tracks loaded entities. `save` on a new entity INSERT; on a loaded entity UPDATE. Day 17.

---

# 6. How It Works

```text
UserRepository.findByEmail
  → Spring Data proxy
  → JPQL / Criteria
  → Hibernate SQL
  → MySQL
```


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-14
cd ~/springboot-practice/day-14
```

Answer key: `java-springboot-backend/practical/day-14/`

Maven with starter-web + data-jpa + mysql driver. MySQL must be running with `app_db`.

| # | File | Why it exists |
|---|---|---|
| 1 | `pom.xml` | JPA + MySQL |
| 2 | `application.properties` | datasource + ddl-auto |
| 3 | `User.java` | @Entity |
| 4 | `UserRepository.java` | JpaRepository |
| 5 | `DemoRunner.java` | CommandLineRunner seed |
| 6 | `Day14Application.java` | main |

```bash
mvn spring-boot:run
# watch SQL in the console, then:
mysql -u root -psecret -e 'SELECT * FROM app_db.users'
```

If the app fails with connection refused, fix MySQL first (Day 13).

Hibernate will **create/update** the `users` table because `ddl-auto=update`.

`CommandLineRunner` runs after the context is up — a teaching seed, not a production migrator.


---

# Common Mistakes

1. **Record as @Entity.**
2. **Forgetting no-arg constructor.**
3. **ddl-auto=create-drop** on a DB with real data.
4. **Thinking JpaRepository is JDBC.** It’s a proxy.
5. **findByEmailIgnoreCase** typos — method names must match properties.

---

# Practical Exercise

1. Run the app twice; confirm seed doesn’t duplicate (existsByEmail).
2. Add findByName; call it from the runner.
3. Set show-sql true (already) and read INSERT/SELECT.
4. Change ddl-auto to validate after first run; restart.
5. Explain IDENTITY vs UUID out loud.

---

# Mini Project

Add `active` boolean column on User with default true; save one inactive user.

---

# Interview Questions

## Easy

### Q1. What is JPA?

**Difficulty:** Easy

**Answer:**

Jakarta Persistence API — spec for ORM in Java.

**Simple Explanation:**

The standard annotations.

**Example:**

@Entity @Id

**Interview Tip:**

Hibernate implements it.

**Common Follow-up Question:**

JPA vs JDBC?

### Q2. What is Hibernate?

**Difficulty:** Easy

**Answer:**

The most common JPA provider. Boot uses it by default.

**Simple Explanation:**

The engine.

**Example:**

ddl-auto, SQL logs

**Interview Tip:**

Don’t say JPA = Hibernate.

**Common Follow-up Question:**

EclipseLink?

### Q3. What is Spring Data JPA?

**Difficulty:** Easy

**Answer:**

A layer that implements repository interfaces from method names and @Query.

**Simple Explanation:**

You write the interface.

**Example:**

JpaRepository<User,Long>

**Interview Tip:**

Proxy at runtime.

**Common Follow-up Question:**

Mongo analog?

### Q4. What is @Entity?

**Difficulty:** Easy

**Answer:**

Marks a class as a persistent type mapped to a table.

**Simple Explanation:**

This class is a table.

**Example:**

@Entity @Table(name="users")

**Interview Tip:**

Needs @Id.

**Common Follow-up Question:**

@Document is Mongo.

### Q5. findById return type?

**Difficulty:** Easy

**Answer:**

Optional<T> on CrudRepository.

**Simple Explanation:**

Maybe missing.

**Example:**

users.findById(1L)

**Interview Tip:**

orElseThrow.

**Common Follow-up Question:**

getById deprecated.

## Medium

### Q1. JPA vs Hibernate vs Spring Data?

**Difficulty:** Medium

**Answer:**

Spec vs implementation vs repository convenience.

**Simple Explanation:**

Three layers.

**Example:**

Lesson analogy

**Interview Tip:**

Draw it.

**Common Follow-up Question:**

Can you use JPA without Spring Data? (Yes, EntityManager.)

### Q2. How does findByEmail work?

**Difficulty:** Medium

**Answer:**

Subject + property path parsed into a query.

**Simple Explanation:**

Name is the query.

**Example:**

findByEmail

**Interview Tip:**

Nested: findByAddressCity.

**Common Follow-up Question:**

And/Or keywords.

### Q3. IDENTITY vs SEQUENCE?

**Difficulty:** Medium

**Answer:**

IDENTITY: DB generates on insert (MySQL). SEQUENCE: prefetch ids (Oracle/Postgres). TABLE: old, avoid.

**Simple Explanation:**

Match the database.

**Example:**

GenerationType.IDENTITY

**Interview Tip:**

Postgres often SEQUENCE or IDENTITY.

**Common Follow-up Question:**

Batch inserts + IDENTITY limitations.

### Q4. What is ddl-auto=update danger?

**Difficulty:** Medium

**Answer:**

Hibernate may add columns but won’t do safe renames/drops well. No history. Prod uses Flyway.

**Simple Explanation:**

Auto-migrate is not a plan.

**Example:**

update vs none

**Interview Tip:**

Dev convenience.

**Common Follow-up Question:**

validate in staging.

### Q5. Why protected no-arg constructor?

**Difficulty:** Medium

**Answer:**

Hibernate instantiates then sets fields. Public no-arg invites empty invalid objects.

**Simple Explanation:**

A door for Hibernate only.

**Example:**

protected User() {}

**Interview Tip:**

Day 2 interview.

**Common Follow-up Question:**

Bytecode enhancement.

## Hard

### Q1. What is the persistence context?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

A first-level cache of entities for a unit of work (often the transaction). Identity guarantee: same row = same object.

**Simple Explanation:**

A tracking room.

**Example:**

find twice = one SELECT

**Interview Tip:**

Day 17

**Common Follow-up Question:**

Extended persistence context.

### Q2. How is the repository proxy created?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Spring Data sees JpaRepository, creates JDK proxy, routes calls to SimpleJpaRepository or query execution.

**Simple Explanation:**

A fake class that talks JPA.

**Example:**

UserRepository bean

**Interview Tip:**

You never implement it.

**Common Follow-up Question:**

Custom fragments.

### Q3. N+1 preview?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

findAll users then get orders lazily each → 1 + N queries.

**Simple Explanation:**

Chatty SQL.

**Example:**

Day 16–17

**Interview Tip:**

join fetch / entity graph

**Common Follow-up Question:**

Looks fine in dev with 2 rows.

### Q4. Dirty checking?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Loaded entities are snapshotted; at flush, differences become UPDATE. You may not call save.

**Simple Explanation:**

Hibernate notices field changes.

**Example:**

user.setName inside @Transactional

**Interview Tip:**

save() still useful for new entities.

**Common Follow-up Question:**

No @Transactional = no flush sometimes.

### Q5. BeanCreationException on datasource?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

URL/driver/MySQL down. Read the root cause, not only the top.

**Simple Explanation:**

Startup fail-fast.

**Example:**

connection refused

**Interview Tip:**

Better than 500 later.

**Common Follow-up Question:**

HikariCP pool errors.


---

# Day-End Practice

1. Run the app twice; confirm seed doesn’t duplicate (existsByEmail).
2. Add findByName; call it from the runner.
3. Set show-sql true (already) and read INSERT/SELECT.
4. Change ddl-auto to validate after first run; restart.
5. Explain IDENTITY vs UUID out loud.

---

# Quick Revision

- JPA spec, Hibernate impl, Spring Data repo.
- @Entity + @Id.
- Query methods.
- ddl-auto=update is for class, not prod.
- Optional findById.

---

# What You Should Be Able To Explain

- JPA vs Hibernate
- JpaRepository
- IDENTITY
- ddl-auto
- query methods

**Next:** [Day 15](../day-15-mysql-crud-jpa/README.md)
