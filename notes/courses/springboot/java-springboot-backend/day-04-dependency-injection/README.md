# Day 4 — Dependency Injection Deeply

## 🎯 Learning Objectives

By the end of this day you will understand:

- Constructor, setter, and field injection — and why constructor injection is the default
- How interfaces make DI useful
- Bean lifecycle callbacks (`@PostConstruct`, `@PreDestroy`)
- What happens when two beans implement the same interface
- Circular dependencies and why constructor injection surfaces them early
- How to write the same designs in plain Java today, then annotate them tomorrow

**Prerequisite:** Day 3 `SimpleContainer`.

---

# 1. Concept — Dependency Injection is a delivery method

## What is it?

**Dependency Injection (DI)** is how a class **receives** objects it needs, instead of constructing them.

Three delivery methods:

| Style | How the dependency arrives |
|---|---|
| Constructor | Parameters of the constructor |
| Setter | `setX(...)` after construction |
| Field | Framework writes a field via reflection |

## Why do we need it?

Without DI, every class is a factory. With DI, every class is a worker. Tests pass fakes. Production passes real implementations.

## Real-world analogy

Constructor injection: you cannot open the shop until the espresso machine is installed.  
Setter injection: you open, then someone wheels the machine in. You might serve empty cups first.  
Field injection: a technician unscrews the wall and bolts a machine inside overnight. You never saw it arrive.

## Backend example

```java
@Service
public class InvoiceService {
    private final TaxCalculator tax;

    public InvoiceService(TaxCalculator tax) {
        this.tax = tax;
    }
}
```

Spring calls this constructor. You never write `new`.

---

# 2. Constructor injection (preferred)

## What is it?

Dependencies are constructor parameters, stored in `private final` fields.

## Why prefer it?

1. **Required dependencies are obvious** — they are in the signature.
2. **`final` fields** — cannot be swapped later, cannot be forgotten.
3. **Easy tests** — `new InvoiceService(fakeTax)`.
4. **Fails at startup** if a bean is missing.
5. **No reflection** into fields; works with records too.
6. **Circular dependencies fail fast** instead of hiding with setters.

Spring Boot: if a class has **one** constructor, you do **not** need `@Autowired` on it. Boot 2.2+ / Spring 4.3+ autowire that constructor.

## Simple example

```java
public class Notifier {
    private final EmailSender email;
    public Notifier(EmailSender email) {
        this.email = email;
    }
}
```

## Spring Boot-related example

Same code plus `@Service`. That is the whole difference tomorrow.

## Common mistake

Two constructors without `@Autowired` on one of them. Spring does not know which to call.

---

# 3. Setter injection

## What is it?

A setter method is annotated `@Autowired`. Spring constructs the object with a no-arg constructor, then calls the setter.

## Why it exists

Optional dependencies, or legacy code with no-arg constructors. Rarely needed in new APIs.

## Backend example

```java
private EmailSender email;

@Autowired
public void setEmail(EmailSender email) {
    this.email = email;
}
```

Problems: field cannot be `final`; object exists in a half-ready state; easy to forget the setter in tests (`NullPointerException`).

---

# 4. Field injection (avoid in application code)

## What is it?

```java
@Autowired
private EmailSender email;
```

Spring uses reflection to set a private field. Looks short. Costs you `final`, costs you honest constructors, costs you easy unit tests (you need reflection or Spring to build the class).

**Use in this course:** never on services/controllers. Tests sometimes use `@MockitoBean` / `@MockBean` instead.

Interviewers often ask: “Why is field injection bad?” Answer with `final` + testability + hidden dependencies.

---

# 5. Bean lifecycle

```text
constructor
  → inject remaining setters/fields
  → BeanNameAware / ApplicationContextAware (rare)
  → @PostConstruct
  → bean in use
  → @PreDestroy
  → object discarded
```

```java
@PostConstruct
void openPool() { /* after injection */ }

@PreDestroy
void closePool() { /* on shutdown */ }
```

Prefer constructor work when possible. Use `@PostConstruct` only if you need injected collaborators first (with setter/field — another reason constructor is simpler: you can do the work in the constructor).

---

# 6. Multiple implementations

```java
public interface EmailSender {
    void send(String to, String body);
}
```

Two `@Component` classes: `SmtpEmailSender`, `ConsoleEmailSender`.

Injecting `EmailSender` fails: `NoUniqueBeanDefinitionException`.

Fixes:

| Annotation | Meaning |
|---|---|
| `@Primary` | Default choice |
| `@Qualifier("smtpEmailSender")` | Pick by name |
| Inject `List<EmailSender>` | Get all |

Default bean name: decapitalized class name (`smtpEmailSender`).

---

# 7. Circular dependencies

```text
A(B b)
B(A a)
```

Constructor injection: Spring cannot instantiate either. App **fails at startup**. Good.

Setter injection might create a half-built cycle. Boot 2.6+ sets `spring.main.allow-circular-references=false`.

**Fix the design:** extract `C` that both use, or use events, not a cycle.

---

# 8. How It Works

```mermaid
flowchart TD
    Scan[Bean definitions] --> Graph[Dependency graph]
    Graph --> Leaf[Create beans with no deps]
    Leaf --> Ctor[Call constructors]
    Ctor --> Post[@PostConstruct]
    Post --> Ready[Singletons ready]
```

If two beans share a type, the graph node is ambiguous until `@Primary`/`@Qualifier`.

---

# 9. Write this on your machine (file by file)

Answer key: `java-springboot-backend/practical/day-04/`

```bash
mkdir -p ~/springboot-practice/day-04/src/com/course/day04
cd ~/springboot-practice/day-04
```

| # | File | Why it exists |
|---|---|---|
| 1 | `EmailSender.java` | Port — the abstraction |
| 2 | `ConsoleEmailSender.java` | Implementation A |
| 3 | `LoggingEmailSender.java` | Implementation B |
| 4 | `Notifier.java` | Constructor injection consumer |
| 5 | `BrokenFieldNotifier.java` | Anti-pattern demo |
| 6 | `Day04App.java` | Wire by hand like Spring would |

```bash
javac -d out src/com/course/day04/*.java
java -cp out com.course.day04.Day04App
```

---

## File 1 — `EmailSender.java`

**Path:** `src/com/course/day04/EmailSender.java`

```java
package com.course.day04;

public interface EmailSender {
    void send(String to, String body);
}
```

---

## File 2 — `ConsoleEmailSender.java`

**Path:** `src/com/course/day04/ConsoleEmailSender.java`

```java
package com.course.day04;

public class ConsoleEmailSender implements EmailSender {
    @Override
    public void send(String to, String body) {
        System.out.println("[console] to=" + to + " body=" + body);
    }
}
```

---

## File 3 — `LoggingEmailSender.java`

**Path:** `src/com/course/day04/LoggingEmailSender.java`

```java
package com.course.day04;

public class LoggingEmailSender implements EmailSender {
    private final EmailSender delegate;

    public LoggingEmailSender(EmailSender delegate) {
        this.delegate = delegate;
    }

    @Override
    public void send(String to, String body) {
        System.out.println("[log] sending to " + to);
        delegate.send(to, body);
    }
}
```

Decorator + constructor injection. Spring AOP proxies are this idea automated.

---

## File 4 — `Notifier.java`

**Path:** `src/com/course/day04/Notifier.java`

```java
package com.course.day04;

public class Notifier {
    private final EmailSender email;

    public Notifier(EmailSender email) {
        this.email = email;
    }

    public void welcome(String to) {
        email.send(to, "Welcome to the course");
    }
}
```

---

## File 5 — `BrokenFieldNotifier.java`

**Path:** `src/com/course/day04/BrokenFieldNotifier.java`

```java
package com.course.day04;

/** Anti-pattern: dependency is invisible. Tests must poke the field. */
public class BrokenFieldNotifier {
    public EmailSender email; // pretend a framework set this

    public void welcome(String to) {
        email.send(to, "Welcome");
    }
}
```

In `main` you will call `welcome` **before** setting `email` and watch the NPE. Constructor injection cannot forget.

---

## File 6 — `Day04App.java`

**Path:** `src/com/course/day04/Day04App.java`

```java
package com.course.day04;

public class Day04App {
    public static void main(String[] args) {
        EmailSender smtp = new ConsoleEmailSender();
        EmailSender logged = new LoggingEmailSender(smtp);
        Notifier notifier = new Notifier(logged);
        notifier.welcome("ada@example.com");

        BrokenFieldNotifier broken = new BrokenFieldNotifier();
        try {
            broken.welcome("ada@example.com");
        } catch (NullPointerException ex) {
            System.out.println("Field injection forgot the dependency: " + ex);
        }
        broken.email = smtp;
        broken.welcome("ada@example.com");
    }
}
```

---

# 10. Common Mistakes

1. Field `@Autowired` on every service.
2. Optional constructor args without `Optional<Foo>` or `@Autowired(required = false)` (prefer splitting classes).
3. Injecting the concrete class `ConsoleEmailSender` instead of `EmailSender`.
4. Using `@Qualifier` with a random string that does not match the bean name.
5. Allowing circular references instead of fixing the design.
6. Doing I/O in the constructor of a bean that is created at startup and might not need that I/O yet — lazy collaborators are a later topic; don’t open network connections unless you must.

---

# 11. Practical Exercise

1. Add `SmsSender` and `AlertService(EmailSender, SmsSender)` with two constructor args.
2. Write a unit test style `main` that passes anonymous `EmailSender` implementations (lambdas).
3. Draw constructor vs field injection from memory.

---

# 12. Mini Project

Build `OrderService` that needs `Inventory` and `EmailSender`. Fail the order if stock is 0, otherwise send email. All constructor injected. No Spring.

---

# Interview Questions

## Easy

### Q1. What is dependency injection?

**Difficulty:** Easy

**Answer:**

A technique where an object receives its collaborators from the outside rather than constructing them.

**Simple Explanation:**

Someone hands you the tool; you don’t build the tool.

**Example:**

```java
public Notifier(EmailSender email) { this.email = email; }
```

**Interview Tip:**

Say constructor injection is the default in Spring.

**Common Follow-up Question:**

IoC vs DI?

### Q2. Why is constructor injection preferred?

**Difficulty:** Easy

**Answer:**

Required deps are explicit, fields can be final, tests are easy, missing beans fail at startup, cycles are visible.

**Simple Explanation:**

The object cannot exist half-wired.

**Example:**

```java
private final EmailSender email;
```

**Interview Tip:**

Mention you omit `@Autowired` when there is a single constructor.

**Common Follow-up Question:**

When would you use a setter?

### Q3. What does `@Autowired` do?

**Difficulty:** Easy

**Answer:**

It marks a constructor, setter, or field as a place Spring should inject a bean. On a single constructor it is optional.

**Simple Explanation:**

A sticker that says “fill this in”.

**Example:**

```java
public UserService(UserRepository users) {}
```

**Interview Tip:**

Prefer constructor; don’t sprinkle `@Autowired` on fields.

**Common Follow-up Question:**

Difference vs `@Inject`? (JSR-330, almost the same.)

### Q4. What is `@Qualifier`?

**Difficulty:** Easy

**Answer:**

Disambiguates when multiple beans share a type by picking one by name (or custom qualifier).

**Simple Explanation:**

Nametag on a bean.

**Example:**

```java
public Notifier(@Qualifier("smtpEmailSender") EmailSender email) {}
```

**Interview Tip:**

Default name is decapitalized class name.

**Common Follow-up Question:**

What is `@Primary`?

### Q5. What is `@Primary`?

**Difficulty:** Easy

**Answer:**

Marks one bean as the default candidate when several implement the same interface.

**Simple Explanation:**

The understudy who goes on unless you ask for someone else.

**Example:**

```java
@Primary
@Component
class ConsoleEmailSender implements EmailSender {}
```

**Interview Tip:**

You can still override with `@Qualifier`.

**Common Follow-up Question:**

Can two beans both be `@Primary`? (No — still ambiguous.)


## Medium

### Q1. Why is field injection hard to unit test?

**Difficulty:** Medium

**Answer:**

The class has no constructor parameter to pass a mock. You must use reflection, Spring, or make the field non-private. Hidden deps also mean you cannot see what to mock.

**Simple Explanation:**

There is no door; you pick the lock.

**Example:**

```java
@Autowired private EmailSender email;
```

**Interview Tip:**

This answer scores well in interviews.

**Common Follow-up Question:**

Is field injection ever OK? (Framework tests, not production services.)

### Q2. How does Spring choose a constructor?

**Difficulty:** Medium

**Answer:**

If one constructor, it is used. If several, the one annotated `@Autowired` is used. If several `@Autowired(required = false)`, the greediest matching one wins. Otherwise startup fails.

**Simple Explanation:**

One door, or a labeled door.

**Example:**

Keep a single constructor — simplest rule.

**Interview Tip:**

Don’t add a no-arg constructor “just in case” on services.

**Common Follow-up Question:**

Records as Spring beans? (Yes, compact constructor.)

### Q3. What is a circular dependency?

**Difficulty:** Medium

**Answer:**

Bean A needs B and B needs A. Constructor injection cannot create either. Setter injection may build a cycle of unfinished objects. The right fix is to redesign.

**Simple Explanation:**

Two friends who refuse to enter a room until the other is inside.

**Example:**

```java
class A { A(B b) {} }
class B { B(A a) {} }
```

**Interview Tip:**

Do not set `allow-circular-references=true` to “fix” it.

**Common Follow-up Question:**

How can events or a third class break the cycle?

### Q4. Singleton beans and mutable fields.

**Difficulty:** Medium

**Answer:**

One instance serves all requests. An instance field that stores “current user” leaks data across requests. Dependencies should be final; request data should be method parameters.

**Simple Explanation:**

One espresso machine, many customers — don’t store the customer on the machine.

**Example:**

```java
private User current; // NEVER on a singleton
```

**Interview Tip:**

Same lesson as Day 2 static state.

**Common Follow-up Question:**

Prototype scope — when? (Rare in web APIs.)

### Q5. Inject `List<EmailSender>` — what happens?

**Difficulty:** Medium

**Answer:**

Spring injects all beans of that type, ordered by `@Order` / `Ordered`. Useful for pipelines.

**Simple Explanation:**

You asked for the whole team.

**Example:**

```java
public Notifier(List<EmailSender> senders) {}
```

**Interview Tip:**

Empty list vs missing bean: a list injection does not fail if zero beans (it injects empty).

**Common Follow-up Question:**

Map<String, EmailSender>? (Yes, bean name → instance.)


## Hard

### Q1. Explain how Spring resolves dependencies when multiple beans implement the same interface.

**Difficulty:** Hard

**Why?** Ambiguity is a real production error.

**How?** Match by type, then @Primary, then @Qualifier / parameter name (if compiler flag is on), else fail.

**When?** Startup, when creating the dependent bean.

**Trade-offs:** Qualifiers couple you to names; @Primary can surprise people.

**Real-world example:** Smtp vs Console email senders.

**Answer:**

Type matching first. If one — inject it. If many — @Primary or @Qualifier. Else NoUniqueBeanDefinitionException.

**Simple Explanation:**

Spring needs a unique answer.

**Example:**

```java
NoUniqueBeanDefinitionException
```

**Interview Tip:**

Name the exception.

**Common Follow-up Question:**

Parameter name injection and `-parameters` compiler flag.

### Q2. Why do transactional proxies require container-managed beans, not `new`?

**Difficulty:** Hard

**Why?** Connects DI to later @Transactional.

**How?** Spring wraps the bean in a JDK or CGLIB proxy. `new` skips the proxy, so @Transactional on a self-called method or a `new` instance does nothing.

**When?** Whenever you expect AOP (tx, security, caching).

**Trade-offs:** Proxies have limitations (self-invocation).

**Real-world example:** OrderService created with new inside a controller — no transaction.

**Answer:**

Only beans from the container get proxies. DI is how you receive the proxy.

**Simple Explanation:**

If you `new` it, Spring never sees it.

**Example:**

```java
// wrong
return new OrderService(repo).place(order);
```

**Interview Tip:**

Preview of Day 17 transactions.

**Common Follow-up Question:**

Self-invocation: this.method() inside the same class.

### Q3. Compare constructor injection with a service locator (`ctx.getBean`).

**Difficulty:** Hard

**Why?** Architecture interviews.

**How?** DI lists needs in the constructor. Service locator pulls from a global context. Tests, visibility, and compile-time safety all suffer with locator.

**When?** Any time someone wants a static ApplicationContext holder.

**Trade-offs:** Locator can resolve optional/late beans; that flexibility is usually a trap.

**Real-world example:** Legacy servlets looking up EJB homes.

**Answer:**

Prefer DI. Locator hides dependencies and requires a live container in tests.

**Simple Explanation:**

Don’t ask the building for a plumber on every leak; hire one.

**Example:**

```java
UserService s = ApplicationContextHolder.get().getBean(UserService.class); // smell
```

**Interview Tip:**

Call it an anti-pattern politely.

**Common Follow-up Question:**

Is a FactoryBean a locator? (No — it is a bean that creates another bean.)

### Q4. How would you inject a prototype bean into a singleton?

**Difficulty:** Hard

**Why?** Scope mismatch.

**How?** A singleton is created once, so a constructor-injected prototype is also created once — not what you wanted. Use ObjectFactory<T>, Provider<T>, or @Lookup.

**When?** When each use needs a fresh instance (rare).

**Trade-offs:** Prototypes in web apps are often a design smell; prefer passing data as method args.

**Real-world example:** Per-operation stateful worker.

**Answer:**

Injecting prototype into singleton constructor does not give you a new instance per call.

**Simple Explanation:**

The singleton captured the prototype forever.

**Example:**

```java
public Worker(ObjectFactory<Task> tasks) { tasks.getObject(); }
```

**Interview Tip:**

Most juniors miss this.

**Common Follow-up Question:**

Request scope proxy `proxyMode = TARGET_CLASS`.

### Q5. Walk through creating Notifier with a logging decorator in Spring terms.

**Difficulty:** Hard

**Why?** Shows composition + DI.

**How?** Define EmailSender. ConsoleEmailSender @Component. A @Bean method takes EmailSender and returns new LoggingEmailSender(delegate) marked @Primary. Notifier constructor gets the logger.

**When?** Cross-cutting logging without AOP.

**Trade-offs:** Manual decorator vs @Aspect.

**Real-world example:** Today’s LoggingEmailSender.

**Answer:**

Decorators are ordinary constructor injection. @Bean factory methods are how you wrap without touching the delegate class.

**Simple Explanation:**

Wrap, then inject the wrap.

**Example:**

```java
@Bean @Primary EmailSender logging(ConsoleEmailSender inner) {
  return new LoggingEmailSender(inner);
}
```

**Interview Tip:**

You will write @Bean on Day 6.

**Common Follow-up Question:**

Does @Primary on the decorator hide the inner bean from List<EmailSender>? (No — both exist unless you don’t expose inner as a bean.)


---

# 13. Day-End Practice

1. Recite three injection styles and one drawback each.
2. Write `Notifier` from memory with `private final`.
3. Cause a fake `NoUniqueBeanDefinitionException` by passing two senders and pretending to pick none.
4. Explain circular dependency with two class names.
5. Refactor one `new` from Day 1 into constructor injection (already done — re-read it).

---

# 14. Quick Revision

- DI = receiving collaborators.
- Constructor + `final` = default.
- Field injection hides deps and breaks `final`.
- `@Primary` / `@Qualifier` / `List<T>` for multiple beans.
- Cycles: fix design, don’t enable the flag.
- `@PostConstruct` after injection; constructor is enough if all deps are constructor-injected.

---

# 15. What You Should Be Able To Explain

- Why constructor injection is safer than field injection
- What `@Autowired` on a single constructor means (nothing extra in Boot)
- How Spring chooses among multiple implementations
- Why `new Service()` skips transactions later
- Bean lifecycle in six steps

**Tomorrow:** Spring Boot, Initializr, Maven, `pom.xml`, `application.properties`, first runnable app.

**Next:** [Day 5](../day-05-spring-boot-fundamentals/README.md)
