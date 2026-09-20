# Day 29 — Docker, Dockerfile, Compose

## 🎯 Learning Objectives

By the end of this day you will understand:

- Image vs container
- Write a Dockerfile for Boot
- Environment variables in Compose
- Run API + Postgres + Mongo together
- Bind 0.0.0.0 (default in Boot)

---

# 1. Concept

- **Image** — recipe snapshot
- **Container** — running instance
- **Dockerfile** — how to build the image
- **Compose** — multi-container (api + db)

```bash
mvn -DskipTests package
docker compose up --build
```

Inside Compose, the JDBC URL host is **`db`**, not localhost. Localhost inside the api container is itself.

**This is simplified:** real prod uses non-root user, layered jars, secrets manager, not compose on one VM forever. No Kubernetes in this course.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-29
cd ~/springboot-practice/day-29
```

Answer key: `java-springboot-backend/practical/day-29/`

Docker Desktop. Package the jar first. Compose file next to Dockerfile.

| # | File | Why it exists |
|---|---|---|
| 1 | `Dockerfile` | JRE 21 + jar |
| 2 | `compose.yaml` | api+postgres+mongo |
| 3 | `HelloController.java` | sanity endpoint |

```bash
mvn -DskipTests package
docker compose up --build
curl http://localhost:8080/api/hello
```

If port 5432 busy, stop local Postgres. The app must use SPRING_DATASOURCE_URL from compose.

---

# Common Mistakes

1. jdbc:...localhost from inside a container (should be service name).
2. Copying source instead of jar without a build stage.
3. Running as root forever (note it).
4. Committing secrets in compose for real prod.
5. Forgetting EXPOSE doesn't publish — ports: does.

---

# Practical Exercise

1. Build image.
2. compose up.
3. curl hello.
4. Change env and recreate.
5. Add mysql service as extra (optional).

---

# Mini Project

Multi-stage Dockerfile: maven build then jre runtime.

---

# Interview Questions

## Easy

### Q1. Image vs container?

**Difficulty:** Easy

**Answer:**

Immutable template vs running process.

**Simple Explanation:**

Immutable template vs running process.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. ENTRYPOINT?

**Difficulty:** Easy

**Answer:**

Default process in the container.

**Simple Explanation:**

Default process in the container.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Why not localhost for DB?

**Difficulty:** Easy

**Answer:**

That's the container itself; use service name.

**Simple Explanation:**

That's the container itself; use service name.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. EXPOSE vs ports?

**Difficulty:** Easy

**Answer:**

EXPOSE is docs; ports publishes to host.

**Simple Explanation:**

EXPOSE is docs; ports publishes to host.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Compose depends_on?

**Difficulty:** Easy

**Answer:**

Start order, not readiness.

**Simple Explanation:**

Start order, not readiness.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. Env vars in Boot?

**Difficulty:** Medium

**Answer:**

SPRING_DATASOURCE_URL maps to spring.datasource.url.

**Simple Explanation:**

SPRING_DATASOURCE_URL maps to spring.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Layered jar?

**Difficulty:** Medium

**Answer:**

Boot layers for better Docker cache.

**Simple Explanation:**

Boot layers for better Docker cache.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Non-root user?

**Difficulty:** Medium

**Answer:**

Security hardening.

**Simple Explanation:**

Security hardening.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Healthcheck?

**Difficulty:** Medium

**Answer:**

Compose/k8s use actuator health.

**Simple Explanation:**

Compose/k8s use actuator health.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. .dockerignore?

**Difficulty:** Medium

**Answer:**

Don't send target/ unnecessarily if using build stage.

**Simple Explanation:**

Don't send target/ unnecessarily if using build stage.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Bind 0.0.0.0?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Boot does; don't set server.address=127.0.0.1.

**Simple Explanation:**

Boot does; don't set server.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Secrets?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Not in git; compose env files gitignored.

**Simple Explanation:**

Not in git; compose env files gitignored.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Why JRE not JDK in runtime?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Smaller image.

**Simple Explanation:**

Smaller image.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. K8s?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Out of scope; compose is enough now.

**Simple Explanation:**

Out of scope; compose is enough now.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Rebuild after Java change?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

mvn package then compose build.

**Simple Explanation:**

mvn package then compose build.

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

1. Build image.
2. compose up.
3. curl hello.
4. Change env and recreate.
5. Add mysql service as extra (optional).

---

# Quick Revision

- Dockerfile jar.
- compose api+db.
- Host is service name.
- Env for secrets.

---

# What You Should Be Able To Explain

- image vs container
- service DNS
- env mapping
- ports
- simplified prod

**Next:** [Day 30](../day-30-final-capstone/README.md)
