# day-12-validation-exceptions

## Day 12 — Bean Validation and global exception handling

### 🎯 Learning Objectives

By the end of this day you will understand:

* Jakarta Bean Validation on DTOs (@NotBlank @Email @Size)
* @Valid vs @Validated
* Custom exceptions: ResourceNotFound, BadRequest, Conflict
* @RestControllerAdvice + @ExceptionHandler
* A standard error JSON body

***

## 1. Concept — validation

### What is it?

**Bean Validation** (Jakarta Validation) annotates fields/record components. Spring runs it when you put `@Valid` on `@RequestBody`.

### Why?

Garbage in → garbage stored. Fail at the edge with 400, not with a NullPointerException at 2am.

### Real-world analogy

Bouncer checks ID at the door. The kitchen does not have to.

### Backend example

```java
public record UserRequest(
    @NotBlank @Size(max = 80) String name,
    @NotBlank @Email String email
) {}
```

```java
public UserResponse create(@Valid @RequestBody UserRequest request)
```

Invalid → `MethodArgumentNotValidException` → our handler → 400 JSON.

***

## 2. Annotations

| Ann         | Meaning                               |
| ----------- | ------------------------------------- |
| `@NotBlank` | not null, not empty, not whitespace   |
| `@NotNull`  | not null (can be empty string)        |
| `@NotEmpty` | not null, not empty collection/string |
| `@Email`    | email shape                           |
| `@Size`     | length                                |
| `@Min @Max` | numbers                               |
| `@Pattern`  | regex                                 |

`@Valid` on a parameter triggers validation of that object. `@Validated` is Spring’s variant (group support) — use `@Valid` on controller bodies.

***

## 3. Global handler

`@RestControllerAdvice` is a `@ControllerAdvice` for REST: catch exceptions from any controller.

```json
{
  "timestamp": "2026-09-20T12:00:00Z",
  "status": 404,
  "error": "RESOURCE_NOT_FOUND",
  "message": "User 10 not found",
  "path": "/api/users/10"
}
```

Catch-all `Exception` → 500 with a **generic** message. Do not send stack traces to clients.

***

## 4. How It Works

```
@Valid fails → MethodArgumentNotValidException
missing user → ResourceNotFoundException
duplicate → ConflictException
        ↓
GlobalExceptionHandler
        ↓
ApiError JSON + status
```

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-12
cd ~/springboot-practice/day-12
```

Answer key: `java-springboot-backend/practical/day-12/`

Add `spring-boot-starter-validation`. Package `com.course.day12`.

| # | File                          | Why it exists            |
| - | ----------------------------- | ------------------------ |
| 1 | `pom.xml`                     | web + validation         |
| 2 | `UserRequest.java`            | @NotBlank @Email         |
| 3 | `UserResponse.java`           | out                      |
| 4 | `exceptions`                  | three RuntimeExceptions  |
| 5 | `ApiError.java`               | standard body            |
| 6 | `GlobalExceptionHandler.java` | @RestControllerAdvice    |
| 7 | `UserService.java`            | throws domain exceptions |
| 8 | `UserController.java`         | @Valid                   |

```bash
mvn spring-boot:run
curl -i -X POST http://localhost:8080/api/users -H 'Content-Type: application/json' -d '{"name":"","email":"nope"}'
curl -i http://localhost:8080/api/users/99
```

**Must use `@Valid`.** Without it, annotations are ignored and empty names are stored.

`jakarta.validation` (Boot 3), not `javax.validation` (Boot 2).

Type every exception class — they are tiny and you will reuse them until Day 30.

***

## Common Mistakes

1. **Forgetting `@Valid`.**
2. **`javax.validation` imports on Boot 3.**
3. **Returning stack traces in 500 bodies.**
4. **Using @ControllerAdvice without @ResponseBody** — use @RestControllerAdvice.
5. **Validating the entity instead of the DTO.**
6. **Catching Exception in the controller.**

***

## Practical Exercise

1. POST invalid email; read the JSON error.
2. GET missing id; 404 body matches ApiError.
3. POST two same emails; 409.
4. Remove @Valid, observe the bad data; put it back.
5. Add @Size(min=3) on name.

***

## Mini Project

Add `BadRequestException` usage if name equals 'admin' (reserved). Return 400 via the existing handler.

***

## Interview Questions

### Easy

#### Q1. What is @Valid?

**Difficulty:** Easy

**Answer:**

Tells Spring to run Bean Validation on that argument.

**Simple Explanation:**

Check this object.

**Example:**

@Valid @RequestBody UserRequest

**Interview Tip:**

Without it, annotations do nothing.

**Common Follow-up Question:**

@Validated?

#### Q2. @NotBlank vs @NotNull?

**Difficulty:** Easy

**Answer:**

@NotNull allows "". @NotBlank rejects null, empty, whitespace.

**Simple Explanation:**

Blank is not a name.

**Example:**

@NotBlank String name

**Interview Tip:**

Use @NotBlank for strings.

**Common Follow-up Question:**

@NotEmpty.

#### Q3. What is @RestControllerAdvice?

**Difficulty:** Easy

**Answer:**

A global component that handles exceptions for @RestController and writes bodies.

**Simple Explanation:**

A safety net.

**Example:**

GlobalExceptionHandler

**Interview Tip:**

One per app usually.

**Common Follow-up Question:**

@ExceptionHandler on a controller?

#### Q4. Why custom exceptions?

**Difficulty:** Easy

**Answer:**

To map domain failures to statuses without HTTP types in the service.

**Simple Explanation:**

Named problems.

**Example:**

ResourceNotFoundException

**Interview Tip:**

Unchecked.

**Common Follow-up Question:**

Checked? (No.)

#### Q5. Typical 400 body?

**Difficulty:** Easy

**Answer:**

timestamp, status, error code, message, path.

**Simple Explanation:**

A standard envelope.

**Example:**

ApiError record

**Interview Tip:**

Don’t invent 12 formats.

**Common Follow-up Question:**

RFC 9457 Problem Details.

### Medium

#### Q1. @Valid vs @Validated?

**Difficulty:** Medium

**Answer:**

@Valid is Jakarta. @Validated is Spring, supports groups. For a request body, @Valid. For query objects on GET, @Validated on class.

**Simple Explanation:**

Body: @Valid.

**Example:**

@Valid UserRequest

**Interview Tip:**

Groups are rare.

**Common Follow-up Question:**

Method validation.

#### Q2. MethodArgumentNotValidException vs ConstraintViolationException?

**Difficulty:** Medium

**Answer:**

The first is @Valid on @RequestBody/@ModelAttribute. The second is method-level or @Validated on params.

**Simple Explanation:**

Two exception types for validation.

**Example:**

Handler for both if needed

**Interview Tip:**

Today we handle MethodArgumentNotValidException.

**Common Follow-up Question:**

BindingResult.

#### Q3. Why not try/catch in every controller method?

**Difficulty:** Medium

**Answer:**

Duplication, missed cases, inconsistent bodies. Advice centralizes.

**Simple Explanation:**

One bouncer.

**Example:**

@ExceptionHandler

**Interview Tip:**

Controllers stay thin.

**Common Follow-up Question:**

Filter-level errors.

#### Q4. Should services throw HTTP exceptions?

**Difficulty:** Medium

**Answer:**

Prefer domain exceptions. ResponseStatusException couples services to web.

**Simple Explanation:**

HTTP is the adapter.

**Example:**

ResourceNotFoundException

**Interview Tip:**

We used it on Day 10 as a shortcut.

**Common Follow-up Question:**

GraphQL same service.

#### Q5. Catch-all Exception handler risks?

**Difficulty:** Medium

**Answer:**

Hides bugs, returns 500 for everything including programming errors. Log the exception server-side.

**Simple Explanation:**

Log internally, lie generically to clients.

**Example:**

handler other()

**Interview Tip:**

Never send ex.getMessage() for unknown errors (leaks).

**Common Follow-up Question:**

Alerting on 500.

### Hard

#### Q1. How does @Valid run in the MVC lifecycle?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

RequestResponseBodyMethodProcessor deserializes then validates via LocalValidatorFactoryBean. Failure throws before the controller method runs.

**Simple Explanation:**

Validation is an argument resolver concern.

**Example:**

DispatcherServlet → resolver → @Valid

**Interview Tip:**

That’s why the method isn’t called.

**Common Follow-up Question:**

Filters cannot see @Valid.

#### Q2. How would you localize validation messages?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

ValidationMessages.properties, interpolator, Accept-Language. Keep error codes stable; translate messages.

**Simple Explanation:**

Codes over prose.

**Example:**

error=VALIDATION\_ERROR

**Interview Tip:**

Clients can map codes.

**Common Follow-up Question:**

i18n later.

#### Q3. Validate path variables?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

@Min on @PathVariable with @Validated on the controller class. Or parse and throw BadRequestException.

**Simple Explanation:**

IDs can be negative.

**Example:**

@PathVariable @Min(1) Long id

**Interview Tip:**

Don’t overdo it.

**Common Follow-up Question:**

MethodValidationPostProcessor.

#### Q4. Advice order when multiple handlers match?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Most specific exception type wins. Exception is last. @Order on advice classes if several.

**Simple Explanation:**

Specific beats generic.

**Example:**

ResourceNotFoundException vs Exception

**Interview Tip:**

Don’t write overlapping handlers.

**Common Follow-up Question:**

Inheritance of exceptions.

#### Q5. 400 vs 422 for validation?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Pick a house standard. This course: 400 + VALIDATION\_ERROR. 422 is also defensible. Consistency > pedantry.

**Simple Explanation:**

Document it.

**Example:**

ApiError status 400

**Interview Tip:**

Interviews accept either with a reason.

**Common Follow-up Question:**

Problem+json.

***

## Day-End Practice

1. POST invalid email; read the JSON error.
2. GET missing id; 404 body matches ApiError.
3. POST two same emails; 409.
4. Remove @Valid, observe the bad data; put it back.
5. Add @Size(min=3) on name.

***

## Quick Revision

* @Valid on bodies.
* jakarta.validation in Boot 3.
* Domain exceptions + advice.
* Standard ApiError JSON.
* Don’t leak stacks.

***

## What You Should Be Able To Explain

* @Valid
* @RestControllerAdvice
* ApiError shape
* 404 vs 409 vs 400
* Why services throw RuntimeException

**Next:** [Day 13](day-13-mysql-fundamentals.md)
