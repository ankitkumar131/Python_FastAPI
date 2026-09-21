# Prerequisites

## What you already know

This course assumes you can:

- Write a Java class with fields, constructors, and methods
- Use `if`, loops, and `switch`
- Create and use objects
- Read a stack trace well enough to find a line number
- Install software and use a terminal

You do **not** need Spring, REST, SQL, MongoDB, Docker, or JWT.

## Java version

Use **Java 21 LTS**. Java 17 also works. Java 8 / 11 will **not** work with Spring Boot 3 (Jakarta EE 10, records in examples, `var` in some snippets).

Verify:

```bash
java -version
```

Expected (any 21.x build is fine):

```text
openjdk version "21.0.x" ...
```

## What Days 1–2 will refresh

Only the Java that Spring Boot leans on:

- Interfaces (Spring injects by type)
- Annotations (almost every Spring feature)
- Generics (`List<User>`, `Optional<User>`, `JpaRepository<User, Long>`)
- Collections and Streams (mapping entities to DTOs)
- Optional (repository `findById`)
- Records (compact DTOs)
- Exceptions (API error handling)
- `equals` / `hashCode` (JPA entities)

If a Java topic is not used in backend work, it is not in this course.

## Time and mindset

- Plan **4–6 hours per day** if you want to finish in 30 calendar days.
- Type the code. Reading is not the same as building.
- When an interview question appears, answer it **out loud** first.

## Hardware

A laptop with 8 GB RAM is enough. 16 GB is more comfortable once Docker runs MySQL + Postgres + Mongo together on Day 29.
