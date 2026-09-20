# Day 8 — REST APIs, HTTP methods, and status codes

## 🎯 Learning Objectives

By the end of this day you will understand:

- What REST means for HTTP APIs (resources, verbs, status codes)
- When to use GET POST PUT PATCH DELETE
- Idempotency
- Status codes 200 201 204 400 401 403 404 409 422 500
- JSON request/response bodies and Content-Type

---

# 1. Concept — REST

## What is it?

**REST** (Representational State Transfer) is an architectural style. In practice for this course:

- You model **resources** (`/api/users`, `/api/users/5`)
- You use HTTP **methods** as verbs
- You return proper **status codes**
- You speak **JSON**

REST is not “any JSON over HTTP”. A RPC-style `POST /getUser` is not resource-oriented.

## Why do we need it?

A shared language between frontend, mobile, and other backends.

## Real-world analogy

Library catalog: nouns are books; verbs are borrow/return. You don’t invent `/doBookThing`.

## Backend example

```text
GET    /api/widgets      list
GET    /api/widgets/1    one
POST   /api/widgets      create
PUT    /api/widgets/1    replace
PATCH  /api/widgets/1    partial update
DELETE /api/widgets/1    remove
```

---

# 2. Methods and idempotency

| Method | Intent | Body | Idempotent | Typical status |
|---|---|---|---|---|
| GET | Read | No | Yes | 200 |
| POST | Create | Yes | No | 201 + Location |
| PUT | Replace | Yes | Yes | 200 / 204 |
| PATCH | Partial | Yes | Usually | 200 |
| DELETE | Remove | Rare | Yes | 204 |

**Idempotent:** repeating the request leaves the same resource state. DELETE twice → still gone (second may be 404; that’s OK).

---

# 3. Status codes you must know

| Code | When |
|---|---|
| 200 OK | Successful GET/PUT/PATCH with body |
| 201 Created | POST created a resource |
| 204 No Content | Success, empty body (DELETE) |
| 400 Bad Request | Malformed JSON / binding |
| 401 Unauthorized | Not authenticated (you are a stranger) |
| 403 Forbidden | Authenticated but not allowed |
| 404 Not Found | No resource |
| 409 Conflict | Duplicate email, version conflict |
| 422 Unprocessable | JSON ok, validation failed (some APIs use 400) |
| 500 Internal | Your bug |

**401 vs 403:** 401 = we don’t know who you are. 403 = we know, and no.

---

# 4. JSON and headers

```http
POST /api/widgets HTTP/1.1
Content-Type: application/json

{"name":"gizmo"}
```

Missing Content-Type on POST with body often → 415.

---

# 5. Good vs bad API design

Bad: `GET /api/getWidgets`, `POST /api/deleteWidget?id=1`

Good: `GET /api/widgets`, `DELETE /api/widgets/1`

Nouns in paths, verbs in methods. Plural resource names. Don’t leak `.json` in the path — use `Accept`.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-08
cd ~/springboot-practice/day-08
```

Answer key: `java-springboot-backend/practical/day-08/`

Package `com.course.day08`. These endpoints are **teaching stubs** (no real store yet). Day 9 adds memory.

| # | File | Why it exists |
|---|---|---|
| 1 | `pom.xml` | web starter |
| 2 | `Day08Application.java` | main |
| 3 | `WidgetController.java` | all six REST verbs |
| 4 | `application.properties` | port |

```bash
mvn spring-boot:run
curl http://localhost:8080/api/widgets
curl -i -X POST http://localhost:8080/api/widgets -H 'Content-Type: application/json' -d '{"name":"gizmo"}'
curl -i -X DELETE http://localhost:8080/api/widgets/1
```

## File — `WidgetController.java`

**Path:** `src/main/java/com/course/day08/WidgetController.java`

Type every method. Notice:

- POST returns **201** and `Location` via `ResponseEntity.created`.
- DELETE returns **204** via `@ResponseStatus(NO_CONTENT)` and `void`.
- PUT vs PATCH documented in the JSON `mode` field (real PATCH would apply partial fields — Day 9+).

Postman: create a collection “Day 8 Widgets” with the six requests.


---

# Common Mistakes

1. **POST for everything** including reads and deletes.
2. **Returning 200 on create** — use 201.
3. **Returning 200 with empty body on delete** — prefer 204.
4. **Using 401 when you meant 403.**
5. **`GET /api/createUser`.**
6. **Putting verbs in URLs.**

---

# Practical Exercise

1. Call each method from Postman; screenshot status codes.
2. POST without Content-Type and record what happens.
3. Write a table of method → status for your future User API.
4. Explain idempotency of PUT vs POST to a rubber duck.
5. Rename a bad endpoint from a blog (`/addWidget`) to a REST path.

---

# Mini Project

Document on paper the User API you will build tomorrow with methods and status codes. No code required beyond today’s stubs.

---

# Interview Questions

## Easy

### Q1. What is REST?

**Difficulty:** Easy

**Answer:**

An architectural style using resources, HTTP verbs, and representations (JSON).

**Simple Explanation:**

Resources + verbs.

**Example:**

```text
GET /api/users/1
```

**Interview Tip:**

Not a Spring feature.

**Common Follow-up Question:**

REST vs SOAP?

### Q2. When is POST used?

**Difficulty:** Easy

**Answer:**

Non-idempotent create or triggering a process.

**Simple Explanation:**

Create.

**Example:**

```http
POST /api/widgets
```

**Interview Tip:**

201 + Location.

**Common Follow-up Question:**

Can POST be used to login? (Common, still RPC-ish.)

### Q3. What does 404 mean?

**Difficulty:** Easy

**Answer:**

No resource (or no mapping) at that URL.

**Simple Explanation:**

Not found.

**Example:**

GET /api/widgets/999

**Interview Tip:**

Don’t use 404 for validation errors.

**Common Follow-up Question:**

404 vs 400.

### Q4. What does 201 mean?

**Difficulty:** Easy

**Answer:**

Created. Response should point to the new resource.

**Simple Explanation:**

We made it.

**Example:**

Location: /api/widgets/1

**Interview Tip:**

Pair with POST.

**Common Follow-up Question:**

Body optional but useful.

### Q5. JSON Content-Type?

**Difficulty:** Easy

**Answer:**

application/json

**Simple Explanation:**

The envelope label.

**Example:**

```http
Content-Type: application/json
```

**Interview Tip:**

Clients and servers both set it.

**Common Follow-up Question:**

What is 415?

## Medium

### Q1. PUT vs PATCH?

**Difficulty:** Medium

**Answer:**

PUT replaces the whole resource; PATCH applies a partial update. PUT is idempotent by definition.

**Simple Explanation:**

Replace vs nibble.

**Example:**

PUT {all fields} vs PATCH {name only}

**Interview Tip:**

Clients must send full PUT bodies.

**Common Follow-up Question:**

JSON Patch vs ad-hoc PATCH.

### Q2. Why is GET not supposed to have a body?

**Difficulty:** Medium

**Answer:**

Spec and caches assume GET is safe and body-less. Some servers ignore GET bodies.

**Simple Explanation:**

GET is a read.

**Example:**

Use query params.

**Interview Tip:**

Don’t design GET with JSON body.

**Common Follow-up Question:**

Safe vs idempotent.

### Q3. 401 vs 403?

**Difficulty:** Medium

**Answer:**

401 unauthenticated; 403 unauthorized (known identity, insufficient permission).

**Simple Explanation:**

Stranger vs not invited.

**Example:**

Missing token vs user role USER hitting /admin

**Interview Tip:**

Security Day 24.

**Common Follow-up Question:**

WWW-Authenticate header.

### Q4. What is idempotency?

**Difficulty:** Medium

**Answer:**

Repeating the request has the same effect on resource state as doing it once.

**Simple Explanation:**

Replay-safe.

**Example:**

DELETE /widgets/1

**Interview Tip:**

POST is not.

**Common Follow-up Question:**

Idempotency keys for payments.

### Q5. 409 Conflict examples?

**Difficulty:** Medium

**Answer:**

Duplicate unique key, editing a stale version, state machine forbids the transition.

**Simple Explanation:**

The resource disagrees.

**Example:**

Second POST same email

**Interview Tip:**

Pair with unique indexes.

**Common Follow-up Question:**

412 Precondition Failed vs 409.

## Hard

### Q1. How would you version an API?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

URL /v1/, header Accept, or no version until breaking change. URL is simple; headers are purer REST.

**Simple Explanation:**

Plan for change.

**Example:**

/api/v1/widgets

**Interview Tip:**

Don’t version for fun.

**Common Follow-up Question:**

Deprecation policy.

### Q2. Is POST /api/users/search REST?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

It’s RPC-ish. Prefer GET /api/users?email= with filters. POST search is used when queries are huge.

**Simple Explanation:**

Nouns over verbs, with pragmatic exceptions.

**Example:**

GET /api/users?q=ada

**Interview Tip:**

Be honest about trade-offs.

**Common Follow-up Question:**

GraphQL as alternative.

### Q3. When 422 vs 400?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

400 malformed syntax; 422 semantically invalid but well-formed (Bean Validation). Many APIs collapse to 400. Pick one and document.

**Simple Explanation:**

Broken JSON vs broken business fields.

**Example:**

{"email":"not-an-email"}

**Interview Tip:**

This course uses 400 for validation on Day 12 unless noted.

**Common Follow-up Question:**

RFC 9110 vs older 422.

### Q4. Why Location header on 201?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

So the client knows the canonical URL of the created resource without guessing ids.

**Simple Explanation:**

Here is the new thing.

**Example:**

```java
ResponseEntity.created(URI.create("/api/widgets/1"))
```

**Interview Tip:**

HATEOAS is optional; Location is enough.

**Common Follow-up Question:**

Relative vs absolute URIs.

### Q5. How would you design pagination URLs?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

GET /api/widgets?page=0&size=20&sort=name,asc plus metadata in the body. Don’t GET /api/widgets/page/0 as a resource.

**Simple Explanation:**

Collection filters, not child resources.

**Example:**

Spring Data Page (Day 17)

**Interview Tip:**

Stable sort for pages.

**Common Follow-up Question:**

Offset vs cursor pagination.


---

# Day-End Practice

1. Call each method from Postman; screenshot status codes.
2. POST without Content-Type and record what happens.
3. Write a table of method → status for your future User API.
4. Explain idempotency of PUT vs POST to a rubber duck.
5. Rename a bad endpoint from a blog (`/addWidget`) to a REST path.

---

# Quick Revision

- Resources are nouns.
- Verbs are HTTP methods.
- 201 create, 204 delete, 409 conflict.
- 401 vs 403.
- Idempotent: GET PUT DELETE.

---

# What You Should Be Able To Explain

- REST resource
- PUT vs PATCH
- Idempotency
- Status code set
- Why POST /deleteUser is bad

**Next:** [Day 9](../day-09-first-rest-api/README.md)
