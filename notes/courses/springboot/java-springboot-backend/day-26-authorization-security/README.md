# Day 26 — Authorization, roles, CORS, CSRF, token hygiene

## 🎯 Learning Objectives

By the end of this day you will understand:

- hasRole vs hasAuthority
- Method security @PreAuthorize
- CORS preflight OPTIONS
- CSRF vs stateless
- Token expiration / password rules

---

# 1. Concept

Authorization is **after** authentication. `hasRole("ADMIN")` checks authority `ROLE_ADMIN`.

## CORS

Browsers block JS on `http://localhost:3000` from calling `http://localhost:8080` unless the API sends `Access-Control-Allow-Origin`. Preflight: `OPTIONS` with `Access-Control-Request-Method`.

Configure a `CorsConfigurationSource` bean (today) or `WebMvcConfigurer`. **Do not** `allowedOrigins("*")` with credentials.

## CSRF

Cookie session = CSRF protection ON. Bearer JWT = typically OFF.

## Token hygiene

Short access TTL, HTTPS, don’t log tokens, rotate secrets, don’t store JWT in localStorage if XSS is a concern (trade-offs with cookies).


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-26
cd ~/springboot-practice/day-26
```

Answer key: `java-springboot-backend/practical/day-26/`

Type SecurityConfig with CORS + roles. Test with two users.

| # | File | Why it exists |
|---|---|---|
| 1 | `SecurityConfig.java` | roles + CORS |
| 2 | `AdminController.java` | @PreAuthorize |

```bash
mvn spring-boot:run
curl -i -u user:password http://localhost:8080/api/admin/stats
curl -i -u admin:password http://localhost:8080/api/admin/stats
```

USER should get 403 on /api/admin/stats. ADMIN 200. OPTIONS preflight from a browser SPA is Day 26’s CORS lesson.

---

# Common Mistakes

1. hasRole('ROLE_ADMIN') doubling prefix.
2. CORS * with cookies.
3. permitAll after anyRequest.
4. Disabling security to 'fix' CORS.
5. XSS + JWT in localStorage without discussion.

---

# Practical Exercise

1. 403 as user, 200 as admin.
2. GET products public.
3. curl -X OPTIONS with Origin header.
4. Add @PreAuthorize on a service method.
5. List password rules (length, hash, not log).

---

# Mini Project

Restrict DELETE /api/products/** to ADMIN.

---

# Interview Questions

## Easy

### Q1. hasRole vs hasAuthority?

**Difficulty:** Easy

**Answer:**

hasRole prepends ROLE_; hasAuthority does not.

**Simple Explanation:**

hasRole prepends ROLE_; hasAuthority does not.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. 403 vs 401?

**Difficulty:** Easy

**Answer:**

Known user forbidden vs anonymous.

**Simple Explanation:**

Known user forbidden vs anonymous.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. What is CORS?

**Difficulty:** Easy

**Answer:**

Browser rule for cross-origin JS HTTP.

**Simple Explanation:**

Browser rule for cross-origin JS HTTP.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Preflight?

**Difficulty:** Easy

**Answer:**

OPTIONS before the real request.

**Simple Explanation:**

OPTIONS before the real request.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. @PreAuthorize?

**Difficulty:** Easy

**Answer:**

Method-level authorization.

**Simple Explanation:**

Method-level authorization.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. EnableMethodSecurity?

**Difficulty:** Medium

**Answer:**

Turns on those annotations.

**Simple Explanation:**

Turns on those annotations.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. CSRF when?

**Difficulty:** Medium

**Answer:**

Cookie-based session browsers.

**Simple Explanation:**

Cookie-based session browsers.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. allowedOrigins *?

**Difficulty:** Medium

**Answer:**

Illegal with allowCredentials true.

**Simple Explanation:**

Illegal with allowCredentials true.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Matcher order?

**Difficulty:** Medium

**Answer:**

First match wins.

**Simple Explanation:**

First match wins.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. XSS vs JWT storage?

**Difficulty:** Medium

**Answer:**

localStorage readable by JS; httpOnly cookies not, but CSRF appears.

**Simple Explanation:**

localStorage readable by JS; httpOnly cookies not, but CSRF appears.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Password policy?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Hash, min length, breach check, never log.

**Simple Explanation:**

Hash, min length, breach check, never log.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Token exp?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Access minutes; refresh longer.

**Simple Explanation:**

Access minutes; refresh longer.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Same-origin policy?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Scheme+host+port must match.

**Simple Explanation:**

Scheme+host+port must match.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. CORS vs Security?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

CORS is browser; postman ignores it.

**Simple Explanation:**

CORS is browser; postman ignores it.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Admin API design?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Separate /api/admin and role check, not hidden URLs.

**Simple Explanation:**

Separate /api/admin and role check, not hidden URLs.

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

1. 403 as user, 200 as admin.
2. GET products public.
3. curl -X OPTIONS with Origin header.
4. Add @PreAuthorize on a service method.
5. List password rules (length, hash, not log).

---

# Quick Revision

- Roles on matchers and methods.
- CORS for SPAs.
- CSRF depends on session style.
- 403 for wrong role.

---

# What You Should Be Able To Explain

- hasRole
- CORS preflight
- 403 as USER
- CSRF vs JWT
- token hygiene

**Next:** [Day 27](../day-27-testing/README.md)
