# day-15-mysql-crud-jpa

## Day 15 — User Management API on MySQL + JPA

### 🎯 Learning Objectives

By the end of this day you will understand:

* Replace the in-memory Map with JpaRepository
* Keep the same /api/users URLs as Days 9–12
* Use DTOs + @Valid + global errors against a real table
* @Transactional on service methods
* Prove data survives restart

***

## 1. Concept — same API, real database

### What is it?

The User Management API from memory, now on MySQL.

### Why?

Restart the process: users are still there. Two Postman creates = two rows you can `SELECT`.

### Real-world analogy

The receptionist script (HTTP) did not change. The filing cabinet replaced the whiteboard.

### Flow

```
HTTP → Controller → Service (@Transactional) → JpaRepository → Hibernate → MySQL
```

***

## 2. @Transactional

On `create/update/delete`: one unit of work. On read methods: `readOnly = true` (hint).

If you `new UserService` yourself, **there is no proxy** — transactions won’t start (Day 4).

***

## 3. Write on your machine

Start MySQL (`app_db`). Type every class. Run POST then `SELECT * FROM users;`.

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-15
cd ~/springboot-practice/day-15
```

Answer key: `java-springboot-backend/practical/day-15/`

Package `com.course.day15`. pom: web + validation + jpa + mysql.

| # | File                   | Why it exists  |
| - | ---------------------- | -------------- |
| 1 | `User.java`            | @Entity        |
| 2 | `UserRequest/Response` | DTOs           |
| 3 | `UserRepository.java`  | JpaRepository  |
| 4 | `UserService.java`     | @Transactional |
| 5 | `UserController.java`  | HTTP           |
| 6 | `exceptions + advice`  | 404/409        |

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@example.com"}'
```

Restart the app and GET `/api/users` — Ada must still exist. That is the victory condition for Day 15.

***

## Common Mistakes

1. **Returning Entity from the controller.**
2. **Forgetting unique email until MySQL error.**
3. **ddl-auto=create-drop** wiping data.
4. **Calling repository from controller.**
5. **No MySQL running** and blaming JPA.

***

## Practical Exercise

1. Create, get, list, update, delete via Postman.
2. Duplicate email 409.
3. Restart persistence check.
4. Watch SQL logs.
5. GET missing → 404 JSON.

***

## Mini Project

Add GET `/api/users/by-email?email=` using `findByEmail` on the repository.

***

## Interview Questions

### Easy

#### Q1. What changed vs Day 9?

**Difficulty:** Easy

**Answer:**

Persistence: JpaRepository + MySQL instead of Map. URLs and DTOs stay.

**Simple Explanation:**

Persistence: JpaRepository + MySQL instead of Map.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Why @Transactional on the service?

**Difficulty:** Easy

**Answer:**

Defines the unit of work and enables dirty checking/flush; repository calls share one session.

**Simple Explanation:**

Defines the unit of work and enables dirty checking/flush; repository calls share one session.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. existsByEmail vs unique constraint?

**Difficulty:** Easy

**Answer:**

Both: check for friendly 409, constraint for races.

**Simple Explanation:**

Both: check for friendly 409, constraint for races.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Does data survive restart?

**Difficulty:** Easy

**Answer:**

Yes, it is in MySQL, not the heap.

**Simple Explanation:**

Yes, it is in MySQL, not the heap.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. What does save do on a new entity?

**Difficulty:** Easy

**Answer:**

INSERT because id is null / new.

**Simple Explanation:**

INSERT because id is null / new.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. Why DTO still?

**Difficulty:** Medium

**Answer:**

Don’t leak entities; same reasons as Day 11.

**Simple Explanation:**

Don’t leak entities; same reasons as Day 11.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. readOnly = true?

**Difficulty:** Medium

**Answer:**

Hint to the provider: no dirty checks / flush optimizations.

**Simple Explanation:**

Hint to the provider: no dirty checks / flush optimizations.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. What SQL do you expect on GET list?

**Difficulty:** Medium

**Answer:**

SELECT from users.

**Simple Explanation:**

SELECT from users.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. 409 mapping?

**Difficulty:** Medium

**Answer:**

ConflictException → advice → 409.

**Simple Explanation:**

ConflictException → advice → 409.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Who opens the JDBC connection?

**Difficulty:** Medium

**Answer:**

HikariCP pool auto-configured by Boot.

**Simple Explanation:**

HikariCP pool auto-configured by Boot.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. Race on two POSTs same email?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Unique index wins; catch DataIntegrityViolationException too.

**Simple Explanation:**

Unique index wins; catch DataIntegrityViolationException too.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Why IDENTITY with MySQL?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Matches AUTO\_INCREMENT.

**Simple Explanation:**

Matches AUTO\_INCREMENT.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Can we drop ddl-auto later?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Yes — Flyway Day 20.

**Simple Explanation:**

Yes — Flyway Day 20.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Service without interface?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Fine with one impl; repository still an interface because Spring Data.

**Simple Explanation:**

Fine with one impl; repository still an interface because Spring Data.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. How to prove JPA in an interview?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Walk POST → INSERT log → SELECT in mysql client.

**Simple Explanation:**

Walk POST → INSERT log → SELECT in mysql client.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

***

## Day-End Practice

1. Create, get, list, update, delete via Postman.
2. Duplicate email 409.
3. Restart persistence check.
4. Watch SQL logs.
5. GET missing → 404 JSON.

***

## Quick Revision

* Same URLs, MySQL behind.
* @Transactional on services.
* Unique email + 409.
* Data survives restart.

***

## What You Should Be Able To Explain

* Request flow to MySQL
* @Transactional
* Why restart keeps data
* DTO mapping
* 409 vs constraint

**Next:** [Day 16](day-16-jpa-relationships.md)
