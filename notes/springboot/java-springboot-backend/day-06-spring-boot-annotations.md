# day-06-spring-boot-annotations

## Day 6 — Spring Boot Annotations

### 🎯 Learning Objectives

By the end of this day you will understand:

* Stereotype annotations and what Spring does with each
* @Component vs @Bean vs @Service vs @Repository
* @Controller vs @RestController
* How @Bean factory methods create objects you don’t own
* Constructor injection of a @Bean into a @Service into a @RestController

***

## 1. Concept — annotations are instructions to the container

### What is it?

An annotation is metadata. Spring **scans** for specific ones and **registers or wires** beans.

### Why do we need it?

Without annotations you would list every class in XML or in a giant `@Bean` config class.

### Real-world analogy

Name badges at a conference: `@Service` means speaker, `@Repository` means cloakroom, `@Controller` means front desk.

### Backend example

```java
@Service
public class GreetingService { }
```

***

## 2. Stereotype annotations

| Annotation        | Meaning                                                | Typical layer           |
| ----------------- | ------------------------------------------------------ | ----------------------- |
| `@Component`      | Generic bean                                           | utilities, filters      |
| `@Service`        | Business logic                                         | service                 |
| `@Repository`     | Persistence; also translates DB exceptions             | repository              |
| `@Controller`     | MVC controller, often returns view names               | web (Thymeleaf)         |
| `@RestController` | `@Controller` + `@ResponseBody`                        | REST JSON APIs          |
| `@Configuration`  | Class that contains `@Bean` methods                    | config                  |
| `@Bean`           | Method that **creates** an object Spring should manage | inside `@Configuration` |

`@Service` and `@Component` are almost the same for scanning. `@Repository` additionally enables persistence exception translation.

**Confused pair:** `@Component` vs `@Bean`

* `@Component` — you own the class; put the annotation **on the class**; Spring calls the constructor.
* `@Bean` — you do **not** annotate the class (maybe it comes from a library); a method **returns** the instance.

`Clock` in today’s code is an interface. We cannot put `@Component` on `Instant`. We write a `@Bean` method that returns a `Clock`.

**Confused pair:** `@Controller` vs `@RestController`

* `@Controller` — method return value is a **view name** unless `@ResponseBody`.
* `@RestController` — method return value is the **HTTP body**.

***

## 3. `@Autowired` vs constructor (again)

On a **single constructor**, skip `@Autowired`. Field `@Autowired` is the anti-pattern from Day 4.

***

## 4. `@Value` and `@ConfigurationProperties` (preview)

```java
@Value("${spring.application.name}")
private String appName;
```

Good for one property. For a group, Day 28 uses `@ConfigurationProperties`.

***

## 5. How It Works

```
@ComponentScan finds @Service GreetingService
@Bean method creates Clock
GreetingService constructor needs Clock → injected
@RestController GreetingController needs GreetingService → injected
GET /api/greet?name=Ada
```

```mermaid
flowchart TD
    Scan[scan] --> GS[GreetingService]
    Bean[@Bean Clock] --> GS
    GS --> Ctrl[GreetingController]
    HTTP[GET /api/greet] --> Ctrl
```

***

## 6. How Spring uses each annotation today

* `@SpringBootApplication` — scan + auto-config
* `@Configuration` — register `ClockConfig`
* `@Bean` — invoke `systemClock()`, store result as `Clock` bean
* `@Service` — construct `GreetingService(clock)`
* `@RestController` — construct `GreetingController(greetingService)` and register mappings
* `@GetMapping` — map GET `/api/greet`
* `@RequestParam` — bind `name` query parameter

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-06
cd ~/springboot-practice/day-06
```

Answer key: `java-springboot-backend/practical/day-06/`

Copy Day 5’s Maven layout, artifact `day06`, Java package `com.course.day06`.

| # | File                      | Why it exists              |
| - | ------------------------- | -------------------------- |
| 1 | `pom.xml`                 | Maven + starter-web        |
| 2 | `application.properties`  | server.port, app name      |
| 3 | `Day06Application.java`   | entry point                |
| 4 | `Clock.java`              | port for time — injectable |
| 5 | `ClockConfig.java`        | @Configuration + @Bean     |
| 6 | `GreetingService.java`    | @Service + constructor DI  |
| 7 | `GreetingController.java` | @RestController            |

```bash
mvn spring-boot:run
# other terminal:
curl 'http://localhost:8080/api/greet?name=Ada'
```

Type `pom.xml` from the answer key (same as Day 5, artifact `day06`).

### File — `Clock.java`

**Path:** `src/main/java/com/course/day06/Clock.java`

```java
package com.course.day06;

public interface Clock {
    String now();
}

```

Interface so tests can pass a fake clock. We cannot `@Component` an interface.

### File — `ClockConfig.java`

**Path:** `src/main/java/com/course/day06/ClockConfig.java`

```java
package com.course.day06;

import java.time.Instant;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ClockConfig {
    @Bean
    Clock systemClock() {
        return () -> Instant.now().toString();
    }
}

```

`@Bean` method name `systemClock` becomes the default bean name.

### File — `GreetingService.java`

**Path:** `src/main/java/com/course/day06/GreetingService.java`

```java
package com.course.day06;

import org.springframework.stereotype.Service;

@Service
public class GreetingService {
    private final Clock clock;

    public GreetingService(Clock clock) {
        this.clock = clock;
    }

    public String greet(String name) {
        return "Hello, " + name + " @ " + clock.now();
    }
}

```

`@Service` is a `@Component` with a semantic name. Constructor injection of `Clock`.

### File — `GreetingController.java`

**Path:** `src/main/java/com/course/day06/GreetingController.java`

```java
package com.course.day06;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class GreetingController {
    private final GreetingService greetings;

    public GreetingController(GreetingService greetings) {
        this.greetings = greetings;
    }

    @GetMapping("/api/greet")
    public Map<String, String> greet(@RequestParam(defaultValue = "world") String name) {
        return Map.of("message", greetings.greet(name));
    }
}

```

Controller does **no** time logic. It delegates. That is the seed of Day 10.

### File — `Day06Application.java`

Same pattern as Day 5. Path: `src/main/java/com/course/day06/Day06Application.java`

***

## Common Mistakes

1. **Putting `@Service` on a controller.** Wrong layer; mappings may still work if you also add `@RestController`, but don’t.
2. **`@Autowired` on fields** after we banned it.
3. **`@Bean` on a `@Service` class.** Pick one style.
4. **Annotating the interface** instead of the implementation.
5. **Main class in a subpackage** so `ClockConfig` is not scanned.
6. **Assuming `@Service` starts a transaction.**

***

## Practical Exercise

1. Add `@Value("${spring.application.name}")` to the greeting message via the service (inject into service constructor using a `@Bean` String or `@Value` on constructor param).
2. Write a second `@Bean` Clock named `fixedClock` returning a constant; use `@Primary` on `systemClock` so the app still runs.
3. Unit-test `GreetingService` with `new GreetingService(() -> "T")` in a small `main` or JUnit if you already know it.
4. Rename `systemClock` and fix the app if you added a `@Qualifier`.
5. Explain `@Repository` exception translation out loud.

***

## Mini Project

Add `FarewellService` and GET `/api/bye?name=` that uses the same `Clock`. Do not duplicate clock logic in the controller.

***

## Interview Questions

### Easy

#### Q1. What is `@Component`?

**Difficulty:** Easy

**Answer:**

Generic stereotype that marks a class as a bean candidate for component scanning.

**Simple Explanation:**

A badge that says “Spring, please manage me”.

**Example:**

```java
@Component
public class TokenParser {}
```

**Interview Tip:**

Specializations: @Service @Repository @Controller.

**Common Follow-up Question:**

Can you put it on an interface? (No useful effect unless a class implements it with its own stereotype.)

#### Q2. `@Service` vs `@Component`?

**Difficulty:** Easy

**Answer:**

Both register a bean. @Service documents “this is business logic”. No extra behavior in core Spring (unlike @Repository).

**Simple Explanation:**

Same engine, clearer name.

**Example:**

```java
@Service
public class GreetingService {}
```

**Interview Tip:**

Use @Service on services anyway — interviews expect it.

**Common Follow-up Question:**

What extra does @Repository do?

#### Q3. What extra does `@Repository` do?

**Difficulty:** Easy

**Answer:**

It is a @Component and enables persistence exception translation to Spring’s DataAccessException hierarchy.

**Simple Explanation:**

A repository badge plus exception translator.

**Example:**

```java
@Repository
public class JdbcUserRepository {}
```

**Interview Tip:**

Important when you write JDBC yourself; Spring Data already sits behind a proxy.

**Common Follow-up Question:**

DataAccessException checked or unchecked? (Unchecked.)

#### Q4. `@Controller` vs `@RestController`?

**Difficulty:** Easy

**Answer:**

@RestController = @Controller + @ResponseBody. Return values are the body, not view names.

**Simple Explanation:**

HTML page vs JSON body.

**Example:**

```java
@RestController
```

**Interview Tip:**

This course uses @RestController everywhere.

**Common Follow-up Question:**

Can you mix them? (Yes, but don’t.)

#### Q5. What is `@Bean`?

**Difficulty:** Easy

**Answer:**

A method (on a @Configuration class) whose return value is registered as a bean.

**Simple Explanation:**

A factory method Spring calls.

**Example:**

```java
@Bean Clock systemClock() { return () -> Instant.now().toString(); }
```

**Interview Tip:**

Use when you cannot annotate the class.

**Common Follow-up Question:**

@Bean vs @Component?

### Medium

#### Q1. When do you choose `@Bean` over `@Component`?

**Difficulty:** Medium

**Answer:**

When the class is third-party, an interface, or needs custom construction (several constructor args from properties).

**Simple Explanation:**

You don’t own the class, or construction is non-trivial.

**Example:**

ObjectMapper, DataSource, Clock.

**Interview Tip:**

Don’t wrap your own services in @Bean without reason.

**Common Follow-up Question:**

Can @Bean methods call each other? (Yes, through proxies on @Configuration.)

#### Q2. What is `@Configuration` vs a plain class with `@Bean` methods (`@Component` lite mode)?

**Difficulty:** Medium

**Answer:**

Full @Configuration is subclassed (CGLIB) so @Bean methods called from other @Bean methods hit the container (singletons). @Component lite mode does not intercept those calls — you might get two instances.

**Simple Explanation:**

Full config is a proxy; lite is not.

**Example:**

```java
@Configuration
public class ClockConfig {}
```

**Interview Tip:**

Always use @Configuration for @Bean classes.

**Common Follow-up Question:**

Why CGLIB?

#### Q3. Does `@Service` change transaction behavior?

**Difficulty:** Medium

**Answer:**

No. @Transactional does. @Service is documentation + scan.

**Simple Explanation:**

The name is not a transaction.

**Example:**

```java
@Service
public class BankService { @Transactional public void transfer() {} }
```

**Interview Tip:**

Don’t assume @Service = transactional.

**Common Follow-up Question:**

Where should @Transactional live? (Service, Day 17.)

#### Q4. `@RequestParam` vs `@PathVariable`.

**Difficulty:** Medium

**Answer:**

Query string vs path segment. /api/greet?name=Ada vs /api/users/5.

**Simple Explanation:**

Filter vs identity.

**Example:**

```java
@GetMapping("/api/greet") Map greet(@RequestParam String name)
```

**Interview Tip:**

required=false and defaultValue matter.

**Common Follow-up Question:**

What if the name is missing? (400 unless default/required false.)

#### Q5. Can you annotate a constructor parameter with `@Qualifier`?

**Difficulty:** Medium

**Answer:**

Yes — that is the clean way to pick among multiple beans while keeping constructor injection.

**Simple Explanation:**

Nametag on the parameter.

**Example:**

```java
public GreetingService(@Qualifier("systemClock") Clock clock) {}
```

**Interview Tip:**

Prefer this over field injection + qualifier.

**Common Follow-up Question:**

Bean name of @Bean method? (The method name.)

### Hard

#### Q1. How does Spring detect @Service if the annotation itself is not listed in the scanner?

**Difficulty:** Hard

**Why?** Meta-annotations.

**How?** @Service is annotated with @Component. The scanner looks for @Component including meta-presence.

**When?** Every scan.

**Trade-offs:** Custom stereotypes work the same way.

**Real-world example:** Your own @UseCase from Day 2 if you meta-annotate with @Component.

**Answer:**

Stereotype annotations are meta-annotated with @Component.

**Simple Explanation:**

A badge that contains another badge.

**Example:**

```java
@Component
public @interface Service {}
```

**Interview Tip:**

This is how @RestController also gets scanned.

**Common Follow-up Question:**

Composed annotations in Spring Boot 3.

#### Q2. @Bean method calling another @Bean method on the same class — what happens?

**Difficulty:** Hard

**Why?** Lite vs full config.

**How?** On @Configuration, the call is intercepted; you get the singleton from the container. On a @Component class, it is a plain Java call — new instance.

**When?** When factoring config.

**Trade-offs:** Surprise duplicates in lite mode.

**Real-world example:** dataSource() used by jdbcTemplate().

**Answer:**

Always @Configuration so self-invocation of @Bean methods is container-aware.

**Simple Explanation:**

Don’t new the DataSource twice.

**Example:**

```java
@Bean JdbcTemplate jdbc(DataSource ds) { return new JdbcTemplate(ds); }
```

**Interview Tip:**

Better: inject parameters instead of calling sibling methods.

**Common Follow-up Question:**

Why @Configuration classes are CGLIB subclassed.

#### Q3. Why might a @RestController not be registered?

**Difficulty:** Hard

**Why?** 404 debugging.

**How?** Outside scan, missing stereotype, created with new, or component-scan exclude.

**When?** When an endpoint 404s but the class exists.

**Trade-offs:** Scan is silent — no error, just missing mapping.

**Real-world example:** Controller in com.other while app is com.course.day06.

**Answer:**

If scan doesn’t see it, it is not a bean, so no mapping.

**Simple Explanation:**

No bean, no route.

**Example:**

```
No mapping for GET /api/greet
```

**Interview Tip:**

Enable DEBUG logging for RequestMappingHandlerMapping.

**Common Follow-up Question:**

spring-boot-starter-web missing — no DispatcherServlet.

#### Q4. Is @Autowired required on a single constructor in Boot 3?

**Difficulty:** Hard

**Why?** Version accuracy.

**How?** No, since Spring 4.3. Multiple constructors need @Autowired on the one to use.

**When?** Every modern Boot app.

**Trade-offs:** People copy old tutorials with field injection.

**Real-world example:** GreetingService(Clock clock).

**Answer:**

Single constructor is autowired implicitly.

**Simple Explanation:**

One door — Spring uses it.

**Example:**

```java
public GreetingService(Clock clock) {}
```

**Interview Tip:**

Say “since Spring 4.3”.

**Common Follow-up Question:**

Kotlin primary constructors.

#### Q5. How would you replace systemClock in a test without Spring Boot Test?

**Difficulty:** Hard

**Why?** DI payoff.

**How?** GreetingService is a normal class: new GreetingService(() -> "FIXED").

**When?** Unit tests of services.

**Trade-offs:** You don’t need Mockito for a functional interface.

**Real-world example:** Clock lambda.

**Answer:**

Constructor injection makes the service testable with a fake Clock.

**Simple Explanation:**

Pass a lambda.

**Example:**

```java
var s = new GreetingService(() -> "2026-01-01T00:00:00Z");
```

**Interview Tip:**

This is why Clock is an interface.

**Common Follow-up Question:**

When do you still use @SpringBootTest? (Integration, Day 27.)

***

## Day-End Practice

1. Add `@Value("${spring.application.name}")` to the greeting message via the service (inject into service constructor using a `@Bean` String or `@Value` on constructor param).
2. Write a second `@Bean` Clock named `fixedClock` returning a constant; use `@Primary` on `systemClock` so the app still runs.
3. Unit-test `GreetingService` with `new GreetingService(() -> "T")` in a small `main` or JUnit if you already know it.
4. Rename `systemClock` and fix the app if you added a `@Qualifier`.
5. Explain `@Repository` exception translation out loud.

***

## Quick Revision

* Stereotypes mark beans.
* @Bean is a factory method.
* @RestController returns JSON.
* Single constructor needs no @Autowired.
* @Service ≠ @Transactional.

***

## What You Should Be Able To Explain

* The difference between @Component and @Bean
* Why @Repository exists besides scanning
* The injection chain Clock → Service → Controller
* Why Clock is an interface
* What happens if ClockConfig is not scanned

**Tomorrow:** Spring MVC, DispatcherServlet, request lifecycle.

**Next:** [Day 7](day-07-spring-mvc.md)
