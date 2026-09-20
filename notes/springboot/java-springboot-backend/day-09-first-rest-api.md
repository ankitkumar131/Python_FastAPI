# day-09-first-rest-api

## Day 9 — First REST API (in-memory CRUD)

### 🎯 Learning Objectives

By the end of this day you will understand:

* Build GET/POST/PUT/DELETE /api/users against a Map
* Use Postman and curl for every verb
* Return 201, 200, 204, 404 correctly
* See why putting a Map in a controller is only a stepping stone

***

## 1. Concept — an API without a database

### What is it?

A **CRUD API** (Create, Read, Update, Delete) over HTTP. Today the “database” is a `LinkedHashMap<Long, User>` inside the controller.

### Why start in memory?

You learn HTTP, JSON, and status codes **without** fighting MySQL. Day 15 replaces the map with JPA. Same URLs.

### Real-world analogy

A whiteboard of users in the office. Tomorrow you move the list into a filing cabinet (MySQL). The receptionist script (HTTP) stays.

### Backend example

```
POST /api/users   { "name": "Ada", "email": "ada@example.com" }  → 201
GET  /api/users                                                 → 200 list
GET  /api/users/1                                               → 200 or 404
PUT  /api/users/1 { "name": "Ada Lovelace", "email": "..." }    → 200
DELETE /api/users/1                                             → 204
```

***

## 2. How data flows today

```
Client JSON
  → Jackson binds @RequestBody User
  → Controller stores in Map
  → Jackson writes User as JSON
```

**This is simplified for learning.** Production never keeps data in a controller field (singleton + lost on restart + not shared across instances).

***

## 3. Postman / curl cheat sheet

```bash
curl -s -X POST http://localhost:8080/api/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada","email":"ada@example.com"}'

curl -s http://localhost:8080/api/users
curl -s http://localhost:8080/api/users/1
curl -s -X PUT http://localhost:8080/api/users/1 \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada Lovelace","email":"ada@example.com"}'
curl -i -X DELETE http://localhost:8080/api/users/1
```

Restart the app — data is gone. That is the lesson of in-memory storage.

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-09
cd ~/springboot-practice/day-09
```

Answer key: `java-springboot-backend/practical/day-09/`

Package `com.course.day09`. Two Java files besides main.

| # | File                    | Why it exists           |
| - | ----------------------- | ----------------------- |
| 1 | `pom.xml`               | starter-web             |
| 2 | `Day09Application.java` | main                    |
| 3 | `User.java`             | JSON-bound POJO         |
| 4 | `UserController.java`   | all CRUD mappings + Map |

```bash
mvn spring-boot:run
# then the curl commands in the lesson
```

### File 1 — `User.java`

**Path:** `src/main/java/com/course/day09/User.java`

Jackson needs a **no-arg constructor** and **getters/setters** (or records). We use a mutable class so you see the JavaBean pattern JPA will also need.

### File 2 — `UserController.java`

**Path:** `src/main/java/com/course/day09/UserController.java`

Type the whole class from the answer key.

**Line by line:**

* `Map<Long, User> store` — the table. `LinkedHashMap` keeps insertion order for GET list.
* `AtomicLong seq` — id generator (`@GeneratedValue` later).
* `create` assigns id, 201 + Location.
* `findById` 404 if missing.
* `delete` 204 or 404.

**What Spring does:** one singleton controller; every HTTP request shares the same map. Fine for homework; wrong for production.

***

## Common Mistakes

1. **Forgetting Content-Type** on POST → 415.
2. **Using GET to create.**
3. **Not copying the id on PUT** — you would insert a second user.
4. **Returning 200 on DELETE.**
5. **Thinking data survives restart.**
6. **Leaving CRUD in the controller after Day 10.**

***

## Practical Exercise

1. Create three users; GET the list; DELETE the middle one; GET list again.
2. GET a missing id; confirm 404.
3. Restart; confirm empty list.
4. Add duplicate-email rejection in create (409). You will move this to the service tomorrow.
5. Import the curl into Postman as a collection.

***

## Mini Project

Add PATCH `/api/users/{id}` that updates only non-null fields from the body. Keep it in the controller for today only.

***

## Interview Questions

### Easy

#### Q1. What is CRUD?

**Difficulty:** Easy

**Answer:**

Create Read Update Delete — the four persistence operations exposed as POST GET PUT/PATCH DELETE.

**Simple Explanation:**

The basic API verbs.

**Example:**

```
POST GET PUT DELETE /api/users
```

**Interview Tip:**

Say it maps to HTTP.

**Common Follow-up Question:**

Is PATCH CRUD? (Update.)

#### Q2. Why 201 on create?

**Difficulty:** Easy

**Answer:**

A new resource exists; 201 signals creation; Location points to it.

**Simple Explanation:**

We made a thing.

**Example:**

Location: /api/users/1

**Interview Tip:**

Body can include the user.

**Common Follow-up Question:**

200 vs 201.

#### Q3. Why does data disappear after restart?

**Difficulty:** Easy

**Answer:**

The Map lives in heap memory of the JVM process.

**Simple Explanation:**

RAM, not a disk.

**Example:**

LinkedHashMap in the controller

**Interview Tip:**

That’s why databases exist.

**Common Follow-up Question:**

Multiple app instances?

#### Q4. What does @RequestBody do?

**Difficulty:** Easy

**Answer:**

Reads the HTTP body and Jackson-deserializes into the parameter type.

**Simple Explanation:**

JSON → Java.

**Example:**

```java
create(@RequestBody User incoming)
```

**Interview Tip:**

Needs Content-Type application/json.

**Common Follow-up Question:**

@ResponseBody?

#### Q5. How do you test this API?

**Difficulty:** Easy

**Answer:**

Postman, curl, or later MockMvc.

**Simple Explanation:**

Call the HTTP endpoint.

**Example:**

curl examples in the lesson

**Interview Tip:**

Save a Postman collection.

**Common Follow-up Question:**

What is a 404 here?

### Medium

#### Q1. Why is a Map in the controller a problem?

**Difficulty:** Medium

**Answer:**

Mixes HTTP with persistence; hard to test business rules; not transactional; not shared across nodes; lost on restart.

**Simple Explanation:**

Wrong drawer.

**Example:**

Day 10 moves it.

**Interview Tip:**

Singleton mutable state.

**Common Follow-up Question:**

Thread safety of HashMap vs ConcurrentHashMap.

#### Q2. PUT vs creating with a client-chosen id?

**Difficulty:** Medium

**Answer:**

Some APIs PUT /users/{id} as upsert. This course: POST creates, PUT replaces existing only, 404 if missing.

**Simple Explanation:**

Be consistent.

**Example:**

replace() checks containsKey

**Interview Tip:**

Document upsert if you do it.

**Common Follow-up Question:**

Idempotent create with PUT.

#### Q3. How does Jackson bind User?

**Difficulty:** Medium

**Answer:**

No-arg constructor + setters, or a single constructor with matching JSON keys (records). Unknown properties are ignored by default in Boot.

**Simple Explanation:**

JSON keys match getters.

**Example:**

{"name":"Ada","email":"a@b.c"}

**Interview Tip:**

Fail on unknown: spring.jackson.deserialization.fail-on-unknown-properties.

**Common Follow-up Question:**

Date formats.

#### Q4. AtomicLong vs ++ long?

**Difficulty:** Medium

**Answer:**

++ on a long field is not atomic under concurrent requests. AtomicLong is.

**Simple Explanation:**

Two POSTs at once could share an id.

**Example:**

seq.getAndIncrement()

**Interview Tip:**

Still not a database sequence.

**Common Follow-up Question:**

Controllers are singleton — concurrency is real.

#### Q5. Why LinkedHashMap not HashMap?

**Difficulty:** Medium

**Answer:**

Stable iteration order for GET list, nicer demos. Not required for correctness.

**Simple Explanation:**

Predictable list.

**Example:**

Insertion order

**Interview Tip:**

Don’t rely on order in APIs without sort params.

**Common Follow-up Question:**

HashMap is O(1) lookup too.

### Hard

#### Q1. Would this controller be thread-safe?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

LinkedHashMap is not. Concurrent creates can corrupt the map. ConcurrentHashMap or synchronize, or don’t share mutable state (use a DB).

**Simple Explanation:**

One singleton, many threads.

**Example:**

Two POST at once

**Interview Tip:**

This is why we leave memory ASAP.

**Common Follow-up Question:**

CopyOnWriteArrayList trade-offs.

#### Q2. How will Day 15 replace the Map without changing URLs?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Extract a repository interface; controller (or service) depends on it. JPA impl tomorrow; URLs stay /api/users.

**Simple Explanation:**

Stable contract, swap guts.

**Example:**

UserRepository

**Interview Tip:**

That’s API as a contract.

**Common Follow-up Question:**

DTO change vs URL change.

#### Q3. Should create reject missing name now?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Yes eventually (validation). Doing if-null in the controller explodes. Day 12 @NotBlank on a DTO.

**Simple Explanation:**

Don’t grow ifs in the controller.

**Example:**

@Valid later

**Interview Tip:**

Fail loud vs 200 with null name.

**Common Follow-up Question:**

Bean Validation vs manual.

#### Q4. Location URI should be absolute or relative?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

RFC allows both; Spring’s ServletUriComponentsBuilder can build absolute from the request. Relative /api/users/1 is fine for this course.

**Simple Explanation:**

Tell the client where it is.

**Example:**

URI.create("/api/users/"+id)

**Interview Tip:**

Absolute helps some clients.

**Common Follow-up Question:**

Forwarded headers behind a proxy.

#### Q5. Why not return Map\<String,Object> instead of User?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Untyped JSON is easy to break. A class is a contract. Records/DTOs even better (Day 11).

**Simple Explanation:**

Types are documentation.

**Example:**

class User

**Interview Tip:**

Map is OK for hello world only.

**Common Follow-up Question:**

OpenAPI generation needs types.

***

## Day-End Practice

1. Create three users; GET the list; DELETE the middle one; GET list again.
2. GET a missing id; confirm 404.
3. Restart; confirm empty list.
4. Add duplicate-email rejection in create (409). You will move this to the service tomorrow.
5. Import the curl into Postman as a collection.

***

## Quick Revision

* In-memory CRUD teaches HTTP.
* Map in controller is temporary.
* 201/404/204.
* Data dies with the JVM.
* Postman every endpoint.

***

## What You Should Be Able To Explain

* CRUD mapping
* Why 404 on GET missing
* Why not keep Map in controller
* How Jackson binds User
* How to curl POST

**Next:** [Day 10](day-10-service-layer.md)
