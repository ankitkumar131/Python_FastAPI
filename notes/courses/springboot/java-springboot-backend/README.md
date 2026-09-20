# 30-Day Java + Spring Boot Backend Mastery Course

A complete, self-study course that takes you from **zero Spring Boot knowledge** to a **production-oriented Java backend developer**.

You already know Java. This course does **not** reteach Java from scratch. It teaches the Java you actually use in Spring Boot, then builds Spring, Spring Boot, REST APIs, databases, security, testing, and production practices — one day at a time.

```text
Java Refresh
      ↓
Spring + IoC / DI
      ↓
Spring Boot + Spring MVC
      ↓
REST APIs + Layered Architecture
      ↓
DTO + Validation + Exception Handling
      ↓
MySQL + JPA + Hibernate
      ↓
PostgreSQL
      ↓
MongoDB
      ↓
Spring Security + JWT
      ↓
Testing + Swagger + Actuator
      ↓
Docker + Production Practices
      ↓
E-Commerce Capstone + Interview Prep
```

---

## What this course teaches

After 30 days you will be able to:

- Create Spring Boot applications from Spring Initializr
- Explain IoC, dependency injection, beans, and the Spring container
- Build REST APIs with proper HTTP methods and status codes
- Design controller / service / repository layers
- Use request/response DTOs instead of exposing entities
- Validate requests and return standardized error responses
- Connect **MySQL**, **PostgreSQL**, and **MongoDB**
- Use Spring Data JPA, Hibernate, JPQL, pagination, sorting, and relationships
- Implement JWT authentication and role-based authorization
- Write unit and integration tests with JUnit, Mockito, and MockMvc
- Document APIs with OpenAPI / Swagger UI
- Use Actuator, logging, profiles, and Flyway
- Containerize a backend with Docker Compose
- Explain your project in a backend interview

**Stack used throughout this course**

| Tool | Version / notes |
|---|---|
| Java | 21 LTS (minimum 17) |
| Spring Boot | 3.4.x (Jakarta namespace, Spring Security 6) |
| Build | Maven |
| Relational DBs | MySQL 8, PostgreSQL 16 |
| Document DB | MongoDB 7 |
| Testing | JUnit 5, Mockito, MockMvc, Spring Boot Test |
| Docs | springdoc-openapi |
| Containers | Docker + Docker Compose |

Spring Boot 3.x is the production standard most interviewers still expect. Spring Boot 4.x exists; APIs in this course stay on the 3.4 line so examples compile against the ecosystem you will actually join. Differences are called out where they matter.

---

## Prerequisites

You should already be comfortable with:

- Java syntax, classes, methods, and basic OOP
- Compiling and running a Java program
- Using an IDE (IntelliJ IDEA or VS Code)
- Basic command-line usage

You do **not** need:

- Spring or Spring Boot
- Dependency injection knowledge
- REST / HTTP expertise
- JPA, Hibernate, or any database experience
- Docker, JWT, or testing frameworks

If Java is rusty, Days 1–2 are a targeted refresher aimed at Spring Boot — not a beginner Java textbook.

Full details: [00-roadmap/prerequisites.md](00-roadmap/prerequisites.md)

---

## Required software

Install these before Day 5 (project creation). Day 1–4 can be followed with Java + an IDE only.

| Software | Why |
|---|---|
| JDK 21 | Compile and run the course apps |
| Maven 3.9+ (or Maven Wrapper) | Build tool |
| IntelliJ IDEA Community or VS Code | Editor |
| Postman (or curl) | Call APIs |
| Git | Version control |
| MySQL 8 | Days 13–17 |
| PostgreSQL 16 | Days 18–20 |
| MongoDB 7 + Compass | Days 21–23 |
| Docker Desktop | Day 29 |

Step-by-step install, verification commands, and common failures: [00-roadmap/setup-guide.md](00-roadmap/setup-guide.md)

---

## How to use this course

1. Open **one day folder**. Start with [`day-01-java-for-springboot/README.md`](day-01-java-for-springboot/README.md).
2. Read the theory. Type the code yourself — do not copy-paste blindly.
3. Complete the **Practical Exercise** and **Mini Project**.
4. Answer the **Interview Questions** out loud before reading the answers.
5. Do the **Day-End Practice** tasks.
6. Tick the checklist below.
7. Move to the next day. Do not skip Days 3–4 (IoC/DI). Everything else sits on them.

**Recommended daily workload**

```text
1–2 hours theory
2–3 hours coding
1 hour exercises
30–60 minutes interview preparation
```

Every day follows the same shape:

```text
Theory → Example → Code → Hands-on exercise → Mini project → Interview questions → Revision
```

---

## 30-day roadmap

| Days | Focus |
|---|---|
| 1–2 | Java for Spring Boot (OOP, collections, streams, Optional, records, annotations) |
| 3–4 | Spring fundamentals, IoC, dependency injection, beans |
| 5–7 | Spring Boot, Maven, annotations, Spring MVC |
| 8–12 | REST, first API, service layer, DTOs, validation, exceptions |
| 13–17 | MySQL, JPA, Hibernate, relationships, N+1, transactions |
| 18–20 | PostgreSQL, UUID, JSONB, indexing, Flyway |
| 21–23 | MongoDB, Spring Data MongoDB, aggregation |
| 24–26 | Spring Security, JWT, roles, CORS, CSRF |
| 27–28 | Testing, OpenAPI, logging, Actuator, profiles |
| 29 | Docker + Compose |
| 30 | E-Commerce capstone + full revision + interview prep |

Detailed maps:

- [00-roadmap/learning-roadmap.md](00-roadmap/learning-roadmap.md)
- [00-roadmap/backend-development-roadmap.md](00-roadmap/backend-development-roadmap.md)

---

## Daily lessons

| Day | Folder | Topic |
|---|---|---|
| 01 | [day-01-java-for-springboot](day-01-java-for-springboot/README.md) | Backend fundamentals + Java refresher |
| 02 | [day-02-java-for-springboot](day-02-java-for-springboot/README.md) | Java concepts Spring actually uses |
| 03 | [day-03-spring-fundamentals](day-03-spring-fundamentals/README.md) | Spring, IoC, beans, ApplicationContext |
| 04 | [day-04-dependency-injection](day-04-dependency-injection/README.md) | Constructor / setter / field injection |
| 05 | [day-05-spring-boot-fundamentals](day-05-spring-boot-fundamentals/README.md) | Spring Boot, Initializr, Maven, config |
| 06 | [day-06-spring-boot-annotations](day-06-spring-boot-annotations/README.md) | Core stereotype and config annotations |
| 07 | [day-07-spring-mvc](day-07-spring-mvc/README.md) | DispatcherServlet and request lifecycle |
| 08 | [day-08-rest-apis](day-08-rest-apis/README.md) | HTTP, REST, status codes, JSON |
| 09 | [day-09-first-rest-api](day-09-first-rest-api/README.md) | In-memory CRUD API + Postman |
| 10 | [day-10-service-layer](day-10-service-layer/README.md) | Layered architecture |
| 11 | [day-11-dtos](day-11-dtos/README.md) | Request/response DTOs and mapping |
| 12 | [day-12-validation-exceptions](day-12-validation-exceptions/README.md) | Bean Validation + global errors |
| 13 | [day-13-mysql-fundamentals](day-13-mysql-fundamentals/README.md) | SQL, tables, keys, joins |
| 14 | [day-14-spring-data-jpa](day-14-spring-data-jpa/README.md) | JPA, Hibernate, repositories |
| 15 | [day-15-mysql-crud-jpa](day-15-mysql-crud-jpa/README.md) | User Management API on MySQL |
| 16 | [day-16-jpa-relationships](day-16-jpa-relationships/README.md) | OneToOne, OneToMany, ManyToMany |
| 17 | [day-17-advanced-jpa](day-17-advanced-jpa/README.md) | JPQL, N+1, pagination, locking |
| 18 | [day-18-postgresql-fundamentals](day-18-postgresql-fundamentals/README.md) | Postgres, UUID, JSONB, schemas |
| 19 | [day-19-springboot-postgresql](day-19-springboot-postgresql/README.md) | Employee Management API |
| 20 | [day-20-advanced-postgresql](day-20-advanced-postgresql/README.md) | Indexes, transactions, Flyway |
| 21 | [day-21-mongodb-fundamentals](day-21-mongodb-fundamentals/README.md) | Documents, collections, BSON |
| 22 | [day-22-spring-data-mongodb](day-22-spring-data-mongodb/README.md) | MongoRepository CRUD |
| 23 | [day-23-advanced-mongodb](day-23-advanced-mongodb/README.md) | Aggregation, embed vs reference |
| 24 | [day-24-spring-security](day-24-spring-security/README.md) | AuthN, AuthZ, filter chain |
| 25 | [day-25-jwt-authentication](day-25-jwt-authentication/README.md) | Register, login, JWT |
| 26 | [day-26-authorization-security](day-26-authorization-security/README.md) | Roles, CORS, CSRF, token hygiene |
| 27 | [day-27-testing](day-27-testing/README.md) | JUnit, Mockito, MockMvc |
| 28 | [day-28-production-apis](day-28-production-apis/README.md) | OpenAPI, logging, Actuator, profiles |
| 29 | [day-29-docker-deployment](day-29-docker-deployment/README.md) | Dockerfile + Compose |
| 30 | [day-30-final-capstone](day-30-final-capstone/README.md) | E-Commerce backend + interview |

---

## Progress checklist

- [ ] Day 1 — Backend fundamentals + Java refresher
- [ ] Day 2 — Java concepts required for Spring
- [ ] Day 3 — Introduction to Spring
- [ ] Day 4 — Dependency Injection deeply
- [ ] Day 5 — Spring Boot fundamentals
- [ ] Day 6 — Spring Boot annotations
- [ ] Day 7 — Spring MVC
- [ ] Day 8 — REST APIs
- [ ] Day 9 — First REST API (in-memory)
- [ ] Day 10 — Service layer
- [ ] Day 11 — DTOs
- [ ] Day 12 — Validation + exception handling
- [ ] Day 13 — MySQL fundamentals
- [ ] Day 14 — Spring Data JPA
- [ ] Day 15 — MySQL CRUD with JPA
- [ ] Day 16 — JPA relationships
- [ ] Day 17 — Advanced JPA
- [ ] Day 18 — PostgreSQL fundamentals
- [ ] Day 19 — Spring Boot + PostgreSQL
- [ ] Day 20 — Advanced PostgreSQL + migrations
- [ ] Day 21 — MongoDB fundamentals
- [ ] Day 22 — Spring Data MongoDB
- [ ] Day 23 — Advanced MongoDB
- [ ] Day 24 — Spring Security fundamentals
- [ ] Day 25 — JWT authentication
- [ ] Day 26 — Authorization + security practices
- [ ] Day 27 — Testing
- [ ] Day 28 — Production APIs
- [ ] Day 29 — Docker + deployment
- [ ] Day 30 — Capstone + interview revision

---

## Projects

Theory without code does not stick. You will build these:

| Project | Stack | Folder |
|---|---|---|
| 1. User Management CRUD API | In-memory → MySQL, validation, exceptions | [projects/project-01-crud-api](projects/project-01-crud-api/README.md) |
| 2. Product Management API | MySQL, JPA, DTO, pagination, filter, sort | [projects/project-02-product-api](projects/project-02-product-api/README.md) |
| 3. Authentication API | Register, login, JWT, roles | [projects/project-03-authentication-api](projects/project-03-authentication-api/README.md) |
| 4. Blog API | MongoDB, posts, authors, comments, search | [projects/project-04-mongodb-blog-api](projects/project-04-mongodb-blog-api/README.md) |
| 5. Employee Management | PostgreSQL, JPA, JWT, pagination | [projects/project-05-postgresql-employee-api](projects/project-05-postgresql-employee-api/README.md) |
| Capstone | E-Commerce backend (users, products, cart, orders) | [projects/final-project](projects/final-project/README.md) |

Each project folder contains **complete, copy-ready Java example code**, `pom.xml`, configuration, and HTTP examples.

---

## Practical code (type this on your machine)

Every lesson has a matching runnable folder:

```text
java-springboot-backend/practical/day-01
java-springboot-backend/practical/day-02
...
java-springboot-backend/practical/day-30
```

**How to study each day**

1. Open that day's `README.md` and read the theory.
2. Follow **Write this on your machine (file by file)** — create each file locally yourself.
3. When you get stuck, compare with `practical/day-XX/` (the finished reference).
4. Do not copy-paste the whole folder first. Typing is the point.

Suggested local workspace:

```bash
mkdir -p ~/springboot-practice
cd ~/springboot-practice
```

Create `day-01`, `day-02`, … there as the lesson instructs. The `practical/` folder in this repo is the answer key, not a substitute for writing the files.

---

## Databases

This course covers all three. None of them is “best”.

| Database | Use in this course |
|---|---|
| MySQL | First relational backend, User + Product APIs |
| PostgreSQL | UUID, JSONB, Employee API, capstone relational data |
| MongoDB | Blog API, optional product reviews in the capstone |

Comparison is taught on Day 23 and in [cheatsheets](cheatsheets/README.md).

---

## Interview preparation

Every day includes **15 interview questions** (5 Easy, 5 Medium, 5 Hard) with answers, examples, tips, and follow-ups.

Dedicated files in [`interview/`](interview/README.md):

- Java, Spring, Spring Boot, Spring MVC
- REST APIs, JPA, Hibernate
- MySQL, PostgreSQL, MongoDB
- Spring Security, JWT, Testing, Docker
- Backend architecture + coding questions

Cheat sheets in [`cheatsheets/`](cheatsheets/README.md):

- Annotations, REST, JPA, MySQL, PostgreSQL, MongoDB, debugging

---

## Expected outcome

By Day 30 you should be able to sit in a backend interview and:

1. Draw the request flow from HTTP → Controller → Service → Repository → Database.
2. Explain why constructor injection and DTOs exist.
3. Walk through a JWT login on a whiteboard.
4. Diagnose `LazyInitializationException` and N+1 queries.
5. Describe a real project (the capstone) with trade-offs.

That is the bar this course is written against.

---

## Repository layout

```text
java-springboot-backend/
├── README.md
├── 00-roadmap/
├── day-01-java-for-springboot/ ... day-30-final-capstone/
├── projects/
├── interview/
└── cheatsheets/
```

Start here: [Day 1](day-01-java-for-springboot/README.md)
