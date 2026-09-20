# Day 11 — DTOs, API contracts, and mapping

## 🎯 Learning Objectives

By the end of this day you will understand:

- What a DTO is and why you must not expose entities
- Request DTO vs Response DTO vs entity
- Manual mapping (and where MapStruct would fit)
- Hiding passwordHash from JSON
- API contracts as a stability boundary

---

# 1. Concept — DTO

## What is it?

**DTO = Data Transfer Object.** A type built for going over the wire, not for the database.

- `UserRequest` — what the client **sends** (includes `password`, no `id`)
- `UserResponse` — what the client **receives** (includes `id`, **no password**)
- `User` — internal entity (includes `passwordHash`)

## Why not expose the entity?

1. **Leaks** — `passwordHash`, internals, lazy relations (later infinite JSON).
2. **Couples clients to the database** — rename a column, API breaks.
3. **Different shapes** — create vs response vs list vs admin.

## Real-world analogy

A restaurant **menu** is not the kitchen’s recipe card. Guests never see the supplier’s invoice (password hash).

## Backend example

```json
POST /api/users
{ "name": "Ada", "email": "ada@example.com", "password": "secret" }

201
{ "id": 1, "name": "Ada", "email": "ada@example.com" }
```

The password never comes back. The hash never leaves the server.

---

# 2. Mapping

Today: a `UserMapper` with static methods. Production often uses **MapStruct** (generated code). Don’t pull MapStruct until the team needs it. Manual mapping is honest and interview-friendly.

Never put mapping in the controller if it grows — keep it in mapper + service.

---

# 3. How It Works

```text
JSON UserRequest
  → Controller
  → Service
  → UserMapper.toEntity
  → User (password hashed — fake hash today)
  → Repository
  → UserMapper.toResponse
  → JSON UserResponse
```


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-11
cd ~/springboot-practice/day-11
```

Answer key: `java-springboot-backend/practical/day-11/`

Package `com.course.day11`. Type files in order: entity, records, mapper, repository, service, controller.

| # | File | Why it exists |
|---|---|---|
| 1 | `User.java` | internal entity with passwordHash |
| 2 | `UserRequest.java` | inbound record |
| 3 | `UserResponse.java` | outbound record |
| 4 | `UserMapper.java` | manual map |
| 5 | `InMemoryUserRepository.java` | store |
| 6 | `UserService.java` | uses mapper |
| 7 | `UserController.java` | Request/Response only |

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@example.com","password":"secret"}'
```

Confirm the response has **no** `password` or `passwordHash`. If you returned `User` from the controller, Jackson would serialize `passwordHash`. That is the whole point of today.

Records are perfect DTOs (Day 2). Entities remain classes.


---

# Common Mistakes

1. **Returning User from the controller.**
2. **Putting password on UserResponse.**
3. **Using the same DTO for create and update** when fields differ (update might not send password).
4. **Mapping in the controller** with 40 setters.
5. **Including JPA relations on a DTO accidentally** (Day 16).

---

# Practical Exercise

1. GET list and confirm no passwordHash.
2. Add UserUpdateRequest without password.
3. Break it on purpose: return User from GET and watch the hash leak; then fix.
4. Write mapper tests in main: toResponse never copies hash.
5. Read a MapStruct hello world (optional) — don’t add it yet.

---

# Mini Project

Add GET `/api/users/{id}` already in code; add a `PublicProfileResponse` with only name (no email) and an endpoint `/api/users/{id}/profile`.

---

# Interview Questions

## Easy

### Q1. What is a DTO?

**Difficulty:** Easy

**Answer:**

An object that carries data across a process boundary, here HTTP. Not a persistence entity.

**Simple Explanation:**

A suitcase for JSON.

**Example:**

UserRequest / UserResponse

**Interview Tip:**

Say request vs response.

**Common Follow-up Question:**

VO vs DTO?

### Q2. Why two DTOs?

**Difficulty:** Easy

**Answer:**

Inbound and outbound shapes differ (password vs id).

**Simple Explanation:**

Different doors.

**Example:**

password in, id out

**Interview Tip:**

One DTO often grows ugly.

**Common Follow-up Question:**

Record vs class.

### Q3. Why hide passwordHash?

**Difficulty:** Easy

**Answer:**

Security. Hashes in JSON leak to logs, XSS, shoulder surfing.

**Simple Explanation:**

Never return secrets.

**Example:**

UserResponse without hash

**Interview Tip:**

Also hide tokens.

**Common Follow-up Question:**

Is hashing Day 24? (Yes.)

### Q4. What is mapping?

**Difficulty:** Easy

**Answer:**

Copying fields between entity and DTO.

**Simple Explanation:**

Translation.

**Example:**

UserMapper

**Interview Tip:**

Manual is fine.

**Common Follow-up Question:**

MapStruct?

### Q5. Can Jackson serialize records?

**Difficulty:** Easy

**Answer:**

Yes, via accessors name()/email().

**Simple Explanation:**

Records work as JSON.

**Example:**

public record UserResponse

**Interview Tip:**

Boot 3 + Jackson.

**Common Follow-up Question:**

Need extra modules? (No.)

## Medium

### Q1. Why not @JsonIgnore on the entity instead of DTOs?

**Difficulty:** Medium

**Answer:**

You mix persistence with API. Different endpoints need different shapes. Relations still bite. DTOs scale.

**Simple Explanation:**

One annotation is not an API design.

**Example:**

@JsonIgnore passwordHash

**Interview Tip:**

Still use DTOs.

**Common Follow-up Question:**

@JsonView as alternative — usually worse.

### Q2. Entity on the controller and infinite JSON?

**Difficulty:** Medium

**Answer:**

Bidirectional JPA relations recurse. DTOs flatten. Day 16.

**Simple Explanation:**

A graph vs a tree.

**Example:**

User.orders.user.orders…

**Interview Tip:**

DTOs prevent it.

**Common Follow-up Question:**

@JsonManagedReference hack — prefer DTO.

### Q3. Where should mapping live?

**Difficulty:** Medium

**Answer:**

Mapper class or service. Not repository. Not entity methods that know HTTP names.

**Simple Explanation:**

A translator booth.

**Example:**

UserMapper

**Interview Tip:**

Keep entities ignorant of DTOs.

**Common Follow-up Question:**

Anti-corruption layer.

### Q4. Is it OK to use Map<String,Object> as DTO?

**Difficulty:** Medium

**Answer:**

For truly dynamic payloads. Otherwise you lose validation, OpenAPI, and safety.

**Simple Explanation:**

Maps are untyped JSON.

**Example:**

Day 5 hello

**Interview Tip:**

Prefer records.

**Common Follow-up Question:**

GraphQL?

### Q5. Request DTO with id field?

**Difficulty:** Medium

**Answer:**

Clients could overwrite ids. Ignore id on create; path id on update.

**Simple Explanation:**

Don’t let clients pick PK unless that’s the design.

**Example:**

POST body without id

**Interview Tip:**

PUT uses path id.

**Common Follow-up Question:**

Mass assignment.

## Hard

### Q1. How do DTOs relate to API compatibility?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

The DTO is the contract. You can change entities/tables if you still fill the same DTO. Additive JSON fields are usually compatible; removals are breaking.

**Simple Explanation:**

Contract vs storage.

**Example:**

Add middleName internally only

**Interview Tip:**

Version when breaking.

**Common Follow-up Question:**

Consumer-driven contracts.

### Q2. Mapping performance?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Negligible vs IO. Don’t skip DTOs for speed. MapStruct is compile-time.

**Simple Explanation:**

Your DB is slower.

**Example:**

Manual mapper

**Interview Tip:**

Premature optimization.

**Common Follow-up Question:**

Projection DTOs in JPQL Day 17.

### Q3. Should entities have toDto()?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

It couples the entity to a particular API. Multiple APIs (admin vs public) then pollute the entity. Prefer external mappers.

**Simple Explanation:**

Entities shouldn’t know JSON.

**Example:**

UserMapper

**Interview Tip:**

Hexagonal: adapters map.

**Common Follow-up Question:**

Domain vs application DTO.

### Q4. Password in logs via toString()?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Records include all components in toString. Don’t record the password field; or override toString. Never log UserRequest blindly.

**Simple Explanation:**

Logs leak too.

**Example:**

UserRequest without password in toString

**Interview Tip:**

Log email only.

**Common Follow-up Question:**

Structured logging Day 28.

### Q5. How will OpenAPI use DTOs?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

springdoc reads parameter and return types. Entities pollute the swagger with hashes and relations. DTOs keep the doc honest.

**Simple Explanation:**

Swagger is the DTO photo.

**Example:**

Day 28

**Interview Tip:**

That’s why types matter.

**Common Follow-up Question:**

@Schema annotations.


---

# Day-End Practice

1. GET list and confirm no passwordHash.
2. Add UserUpdateRequest without password.
3. Break it on purpose: return User from GET and watch the hash leak; then fix.
4. Write mapper tests in main: toResponse never copies hash.
5. Read a MapStruct hello world (optional) — don’t add it yet.

---

# Quick Revision

- Entity ≠ JSON.
- Request vs Response.
- Mapper copies fields.
- Never return passwordHash.
- Records as DTOs.

---

# What You Should Be Able To Explain

- Why DTOs
- passwordHash leak
- mapper placement
- records as JSON
- contract vs table

**Next:** [Day 12](../day-12-validation-exceptions/README.md)
