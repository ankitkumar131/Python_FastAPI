# day-27-testing

## Day 27 — JUnit, Mockito, MockMvc

### 🎯 Learning Objectives

By the end of this day you will understand:

* Unit vs integration tests
* JUnit 5 @Test
* Mockito when/verify
* MockMvc for controllers
* What to mock and what not to

***

## 1. Concept

| Test             | How                     | Mock                    |
| ---------------- | ----------------------- | ----------------------- |
| Unit service     | `new DiscountService()` | none or collaborators   |
| Controller slice | `@WebMvcTest`           | `@MockitoBean` services |
| Integration      | `@SpringBootTest`       | none / testcontainers   |

**Don’t mock the class under test.** Mock **dependencies**.

Don’t write MockMvc for every getter if the service test already covers the rule — but do test HTTP mappings and validation.

`@MockBean` was renamed thinking in Boot 3.4: prefer `org.springframework.test.context.bean.override.mockito.MockitoBean`. If your version still has `@MockBean`, it works.

```bash
./mvnw test
```

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-27
cd ~/springboot-practice/day-27
```

Answer key: `java-springboot-backend/practical/day-27/`

starter-test is already in the parent. Put tests in src/test/java **same package**.

| # | File                          | Why it exists |
| - | ----------------------------- | ------------- |
| 1 | `DiscountService.java`        | pure logic    |
| 2 | `DiscountServiceTest.java`    | unit          |
| 3 | `DiscountController.java`     | HTTP          |
| 4 | `DiscountControllerTest.java` | MockMvc       |

```bash
mvn test
```

If MockitoBean import fails on older Boot, replace with @MockBean from org.springframework.boot.test.mock.mockito.

***

## Common Mistakes

1. Testing only through the UI.
2. Mocking the service under test.
3. @SpringBootTest for every unit (slow).
4. Ignoring assertions, only printing.
5. Not testing 400 validation.

***

## Practical Exercise

1. Run mvn test.
2. Add a test for non-VIP.
3. Break apply(); watch test fail.
4. Add MockMvc 400 case.
5. Explain slice vs full context.

***

## Mini Project

Test a repository with @DataJpaTest (needs JPA) OR extra MockMvc for missing param.

***

## Interview Questions

### Easy

#### Q1. Unit vs integration?

**Difficulty:** Easy

**Answer:**

One class vs several layers/real DB.

**Simple Explanation:**

One class vs several layers/real DB.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. JUnit 5 engine?

**Difficulty:** Easy

**Answer:**

jupiter.

**Simple Explanation:**

jupiter.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. What is Mockito?

**Difficulty:** Easy

**Answer:**

Library to fake collaborators.

**Simple Explanation:**

Library to fake collaborators.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. when().thenReturn?

**Difficulty:** Easy

**Answer:**

Stub a method.

**Simple Explanation:**

Stub a method.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. verify?

**Difficulty:** Easy

**Answer:**

Assert a mock was called.

**Simple Explanation:**

Assert a mock was called.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. MockMvc?

**Difficulty:** Medium

**Answer:**

Fake HTTP against DispatcherServlet without a port.

**Simple Explanation:**

Fake HTTP against DispatcherServlet without a port.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. @WebMvcTest?

**Difficulty:** Medium

**Answer:**

Slice: MVC only.

**Simple Explanation:**

Slice: MVC only.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. @SpringBootTest?

**Difficulty:** Medium

**Answer:**

Full context.

**Simple Explanation:**

Full context.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. What not to mock?

**Difficulty:** Medium

**Answer:**

The subject, simple value objects, sometimes repositories in slice tests you do mock.

**Simple Explanation:**

The subject, simple value objects, sometimes repositories in slice tests you do mock.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. AAA?

**Difficulty:** Medium

**Answer:**

Arrange Act Assert.

**Simple Explanation:**

Arrange Act Assert.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. Testcontainers?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Real DB in Docker for integration.

**Simple Explanation:**

Real DB in Docker for integration.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. @DataJpaTest?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Slice for repositories + in-memory DB.

**Simple Explanation:**

Slice for repositories + in-memory DB.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Why tests in same package?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Package-private access.

**Simple Explanation:**

Package-private access.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Flaky tests?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Time, order, shared state.

**Simple Explanation:**

Time, order, shared state.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. CI?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

mvn test on every push.

**Simple Explanation:**

mvn test on every push.

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

1. Run mvn test.
2. Add a test for non-VIP.
3. Break apply(); watch test fail.
4. Add MockMvc 400 case.
5. Explain slice vs full context.

***

## Quick Revision

* Unit new Service().
* MockMvc for HTTP.
* Mock collaborators not subject.
* mvn test.

***

## What You Should Be Able To Explain

* unit vs slice vs IT
* Mockito
* MockMvc
* what not to mock
* mvn test

**Next:** [Day 28](day-28-production-apis.md)
