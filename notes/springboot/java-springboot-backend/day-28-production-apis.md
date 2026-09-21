# day-28-production-apis

## Day 28 — OpenAPI, logging, Actuator, profiles, config

### 🎯 Learning Objectives

By the end of this day you will understand:

* springdoc Swagger UI
* SLF4J levels and secrets in logs
* Actuator health/info
* profiles dev/test/prod
* env vars instead of passwords in git

***

## 1. Concept

Production APIs need **docs, logs, health, config**.

### OpenAPI

`springdoc-openapi-starter-webmvc-ui` → http://localhost:8080/swagger-ui.html

### Logging

```java
private static final Logger log = LoggerFactory.getLogger(HelloController.class);
log.info("hello requested");
```

Levels: TRACE DEBUG INFO WARN ERROR. Never log passwords, tokens, full card numbers.

### Actuator

```properties
management.endpoints.web.exposure.include=health,info
management.endpoint.health.show-details=when_authorized
```

`/actuator/health` for orchestrators.

### Profiles

`application-dev.properties`, `application-prod.properties`.

```bash
java -jar app.jar --spring.profiles.active=prod
```

### Secrets

```properties
spring.datasource.password=${DB_PASSWORD}
```

Set `DB_PASSWORD` in the environment. Not in git.

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-28
cd ~/springboot-practice/day-28
```

Answer key: `java-springboot-backend/practical/day-28/`

Add actuator + springdoc. Type HelloController with a logger.

| # | File                          | Why it exists        |
| - | ----------------------------- | -------------------- |
| 1 | `pom.xml`                     | actuator + springdoc |
| 2 | `application.properties`      | exposure             |
| 3 | `application-prod.properties` | prod profile         |
| 4 | `HelloController.java`        | log.info             |

```bash
mvn spring-boot:run
curl http://localhost:8080/api/hello
curl http://localhost:8080/actuator/health
```

Open Swagger UI in a browser. Switch profile with SPRING\_PROFILES\_ACTIVE=prod.

***

## Common Mistakes

1. Exposing all actuator endpoints to the internet.
2. Logging Authorization headers.
3. Hardcoding prod passwords.
4. No health check.
5. Swagger without security in prod (protect it).

***

## Practical Exercise

1. Hit health.
2. Open swagger-ui.
3. Change log level via properties.
4. Add APP\_SECRET env in a dummy @Value.
5. Create application-dev.properties.

***

## Mini Project

Document /api/hello with @Operation (springdoc).

***

## Interview Questions

### Easy

#### Q1. What is OpenAPI?

**Difficulty:** Easy

**Answer:**

Spec for describing HTTP APIs; Swagger UI visualizes it.

**Simple Explanation:**

Spec for describing HTTP APIs; Swagger UI visualizes it.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Actuator?

**Difficulty:** Easy

**Answer:**

Production-ready endpoints: health, metrics, info.

**Simple Explanation:**

Production-ready endpoints: health, metrics, info.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Why not expose env actuator?

**Difficulty:** Easy

**Answer:**

Leaks secrets.

**Simple Explanation:**

Leaks secrets.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. SLF4J?

**Difficulty:** Easy

**Answer:**

Logging facade; Logback implementation in Boot.

**Simple Explanation:**

Logging facade; Logback implementation in Boot.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Log levels?

**Difficulty:** Easy

**Answer:**

TRACE to ERROR.

**Simple Explanation:**

TRACE to ERROR.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. Profiles?

**Difficulty:** Medium

**Answer:**

Named sets of properties.

**Simple Explanation:**

Named sets of properties.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Externalized config order?

**Difficulty:** Medium

**Answer:**

Defaults < properties < env < args (simplified).

**Simple Explanation:**

Defaults < properties < env < args (simplified).

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. @ConfigurationProperties?

**Difficulty:** Medium

**Answer:**

Typed config beans vs many @Value.

**Simple Explanation:**

Typed config beans vs many @Value.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Health vs ready?

**Difficulty:** Medium

**Answer:**

liveness vs readiness in k8s.

**Simple Explanation:**

liveness vs readiness in k8s.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Structured logging?

**Difficulty:** Medium

**Answer:**

JSON logs for aggregators.

**Simple Explanation:**

JSON logs for aggregators.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. Why env vars?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

12-factor secrets; no rebuild.

**Simple Explanation:**

12-factor secrets; no rebuild.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. springdoc vs springfox?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

springfox is legacy on Boot 3; use springdoc.

**Simple Explanation:**

springfox is legacy on Boot 3; use springdoc.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. MDC?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Per-request log context (request id).

**Simple Explanation:**

Per-request log context (request id).

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Info endpoint?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Build version from MANIFEST.

**Simple Explanation:**

Build version from MANIFEST.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Protect swagger in prod?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Auth or disable.

**Simple Explanation:**

Auth or disable.

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

1. Hit health.
2. Open swagger-ui.
3. Change log level via properties.
4. Add APP\_SECRET env in a dummy @Value.
5. Create application-dev.properties.

***

## Quick Revision

* Swagger UI.
* log.info no secrets.
* /actuator/health.
* profiles + env vars.

***

## What You Should Be Able To Explain

* OpenAPI
* Actuator exposure
* profiles
* env passwords
* bad logs

**Next:** [Day 29](day-29-docker-deployment.md)
