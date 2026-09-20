# day-24-spring-security

## Day 24 — Spring Security fundamentals

### 🎯 Learning Objectives

By the end of this day you will understand:

* Authentication vs authorization
* SecurityFilterChain
* Password hashing (BCrypt)
* Roles vs authorities
* Why CSRF is disabled for stateless APIs (carefully)

***

## 1. Concept

### Authentication

Who are you? (login, basic auth, JWT)

### Authorization

What may you do? (roles)

### Filter chain

Servlet filters wrap every request **before** the controller. Spring Security’s `SecurityFilterChain` is a bean you configure in Boot 3 (the old `WebSecurityConfigurerAdapter` is **gone**).

```
Request → Security filters → DispatcherServlet → Controller
```

### Password hashing

Never store raw passwords. `BCryptPasswordEncoder` hashes with salt. `{noop}password` is for demos only — not today.

### HTTP Basic (today)

```bash
curl -u ada:password http://localhost:8080/api/private/me
```

JWT is tomorrow. Today you feel the filter chain.

### CSRF

Browser cookie sessions need CSRF tokens. **Stateless Bearer JWT APIs** typically disable CSRF. Don’t disable CSRF if you use cookie sessions.

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-24
cd ~/springboot-practice/day-24
```

Answer key: `java-springboot-backend/practical/day-24/`

starter-security. Without SecurityFilterChain, Boot’s default requires auth on every URL with a random password in logs.

| # | File                  | Why it exists                          |
| - | --------------------- | -------------------------------------- |
| 1 | `SecurityConfig.java` | filter chain + BCrypt + in-memory user |
| 2 | `DemoController.java` | public vs private                      |

```bash
mvn spring-boot:run
curl -i http://localhost:8080/api/public/ping
curl -i http://localhost:8080/api/private/me
curl -u ada:password http://localhost:8080/api/private/me
```

Public ping is 200 without credentials. Private me is 401 then 200 with -u.

***

## Common Mistakes

1. Leaving default generated password.
2. Storing plain passwords.
3. csrf.disable on a cookie session app.
4. WebSecurityConfigurerAdapter tutorials (Boot 2).
5. permitAll on /api/\*\* by accident.

***

## Practical Exercise

1. Hit public and private.
2. Wrong password 401.
3. Change role to ADMIN and require it (preview Day 26).
4. Read filter chain log.
5. Encode a password in main with BCrypt.

***

## Mini Project

Add /api/public/health returning UP.

***

## Interview Questions

### Easy

#### Q1. AuthN vs AuthZ?

**Difficulty:** Easy

**Answer:**

Identity vs permission.

**Simple Explanation:**

Identity vs permission.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. What is SecurityFilterChain?

**Difficulty:** Easy

**Answer:**

The Boot 3 bean that configures HTTP security.

**Simple Explanation:**

The Boot 3 bean that configures HTTP security.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Why BCrypt?

**Difficulty:** Easy

**Answer:**

Slow salted hash; not reversible.

**Simple Explanation:**

Slow salted hash; not reversible.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Default Boot security?

**Difficulty:** Easy

**Answer:**

All URLs authenticated; password printed once.

**Simple Explanation:**

All URLs authenticated; password printed once.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. 401 vs 403?

**Difficulty:** Easy

**Answer:**

Not authenticated vs not allowed.

**Simple Explanation:**

Not authenticated vs not allowed.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. CSRF for JWT APIs?

**Difficulty:** Medium

**Answer:**

Usually disable; no cookie session.

**Simple Explanation:**

Usually disable; no cookie session.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Roles vs authorities?

**Difficulty:** Medium

**Answer:**

ROLE\_ prefix vs fine-grained strings.

**Simple Explanation:**

ROLE\_ prefix vs fine-grained strings.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Where do filters sit?

**Difficulty:** Medium

**Answer:**

Before DispatcherServlet.

**Simple Explanation:**

Before DispatcherServlet.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. In-memory users?

**Difficulty:** Medium

**Answer:**

Fine for class; prod uses DB.

**Simple Explanation:**

Fine for class; prod uses DB.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. httpBasic?

**Difficulty:** Medium

**Answer:**

Authorization: Basic base64 user:pass.

**Simple Explanation:**

Authorization: Basic base64 user:pass.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. Deprecated adapter?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

WebSecurityConfigurerAdapter removed in Security 6.

**Simple Explanation:**

WebSecurityConfigurerAdapter removed in Security 6.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. PasswordEncoder bean missing?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

DelegatingPasswordEncoder required.

**Simple Explanation:**

DelegatingPasswordEncoder required.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. permitAll matcher order?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

First match wins; order matters.

**Simple Explanation:**

First match wins; order matters.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Principal?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

The authenticated identity.

**Simple Explanation:**

The authenticated identity.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Why not MD5?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Fast, unsalted historically; cracked.

**Simple Explanation:**

Fast, unsalted historically; cracked.

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

1. Hit public and private.
2. Wrong password 401.
3. Change role to ADMIN and require it (preview Day 26).
4. Read filter chain log.
5. Encode a password in main with BCrypt.

***

## Quick Revision

* Filter chain before MVC.
* BCrypt.
* permitAll vs authenticated.
* CSRF vs stateless.
* Security 6 API.

***

## What You Should Be Able To Explain

* AuthN vs AuthZ
* SecurityFilterChain
* BCrypt
* 401 on private
* CSRF note

**Next:** [Day 25](day-25-jwt-authentication.md)
