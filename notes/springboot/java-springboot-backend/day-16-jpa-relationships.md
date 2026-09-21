# day-16-jpa-relationships

## Day 16 — JPA relationships: 1-1, 1-N, N-N

### 🎯 Learning Objectives

By the end of this day you will understand:

* @OneToOne User↔Profile
* @OneToMany / @ManyToOne User↔Orders
* @ManyToMany Student↔Course and join table
* owning side, mappedBy, @JoinColumn
* Why returning entities causes infinite JSON — DTOs fix it
* LAZY vs EAGER

***

## 1. Concept — associations

### What is it?

How tables point at each other, expressed as Java fields.

| Relation   | Example        | FK lives on                |
| ---------- | -------------- | -------------------------- |
| OneToOne   | User–Profile   | profiles.user\_id (owning) |
| OneToMany  | User–Orders    | orders.user\_id            |
| ManyToOne  | Order–User     | same                       |
| ManyToMany | Student–Course | join table student\_course |

### Owning vs inverse

The **owning side** has the FK (`@JoinColumn`). The inverse has `mappedBy`. You **must set the owning side** in Java (`order.setUser(user)`). Helper methods `addOrder` keep both sides in sync.

### Infinite JSON

If a controller returns `User` with `orders` and each `Order` has `user`, Jackson recurses until the stack explodes. **DTOs flatten the graph.** Never `@JsonIgnore` as your only strategy.

### LAZY vs EAGER

Default: ManyToOne EAGER (historical), OneToMany LAZY. Prefer **LAZY everywhere** and fetch what you need (Day 17). Accessing a lazy field outside a transaction → `LazyInitializationException`.

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-16
cd ~/springboot-practice/day-16
```

Answer key: `java-springboot-backend/practical/day-16/`

Same MySQL. Package `com.course.day16`. Seed runner creates Ada + profile + order.

| # | File                | Why it exists         |
| - | ------------------- | --------------------- |
| 1 | `User.java`         | OneToOne + OneToMany  |
| 2 | `Profile.java`      | owning OneToOne       |
| 3 | `Order.java`        | ManyToOne LAZY        |
| 4 | `Student/Course`    | ManyToMany join table |
| 5 | `RelationSeed.java` | how to set both sides |

```bash
mvn spring-boot:run
# inspect tables: users, profiles, orders, student_course
```

Do **not** add a REST controller that returns User. If you want HTTP, return a DTO without nested back-references.

***

## Common Mistakes

1. **mappedBy on both sides.**
2. **Forgetting to set the owning side.**
3. **EAGER OneToMany** loading the universe.
4. **Returning entities from REST.**
5. **CascadeType.ALL from Order to User** (wrong direction).

***

## Practical Exercise

1. Run seed; SELECT join users/profiles/orders.
2. Draw owning vs inverse.
3. Add a second order via addOrder.
4. Explain LazyInitializationException.
5. Sketch a UserResponse without orders cycle.

***

## Mini Project

Add Category–Product ManyToOne. Product owns category\_id.

***

## Interview Questions

### Easy

#### Q1. What is mappedBy?

**Difficulty:** Easy

**Answer:**

Names the field on the owning side; this side is inverse and has no FK.

**Simple Explanation:**

Names the field on the owning side; this side is inverse and has no FK.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Where is the FK for OneToMany?

**Difficulty:** Easy

**Answer:**

On the many side (@JoinColumn on @ManyToOne).

**Simple Explanation:**

On the many side (@JoinColumn on @ManyToOne).

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. What is a join table?

**Difficulty:** Easy

**Answer:**

Extra table holding two FKs for ManyToMany.

**Simple Explanation:**

Extra table holding two FKs for ManyToMany.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Owning side?

**Difficulty:** Easy

**Answer:**

The side JPA uses to persist the relationship.

**Simple Explanation:**

The side JPA uses to persist the relationship.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Default fetch OneToMany?

**Difficulty:** Easy

**Answer:**

LAZY.

**Simple Explanation:**

LAZY.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. Infinite JSON cause?

**Difficulty:** Medium

**Answer:**

Bidirectional entity serialization.

**Simple Explanation:**

Bidirectional entity serialization.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Fix infinite JSON?

**Difficulty:** Medium

**Answer:**

DTOs (or carefully @JsonIgnore, worse).

**Simple Explanation:**

DTOs (or carefully @JsonIgnore, worse).

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. orphanRemoval?

**Difficulty:** Medium

**Answer:**

Remove child from collection → DELETE row.

**Simple Explanation:**

Remove child from collection → DELETE row.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. CascadeType.ALL danger?

**Difficulty:** Medium

**Answer:**

Deletes/propagates too much, especially toward User.

**Simple Explanation:**

Deletes/propagates too much, especially toward User.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Why helper addOrder?

**Difficulty:** Medium

**Answer:**

Sets both sides so memory model matches DB.

**Simple Explanation:**

Sets both sides so memory model matches DB.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. LazyInitializationException?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Lazy proxy hit after session closed.

**Simple Explanation:**

Lazy proxy hit after session closed.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Why LAZY ManyToOne?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Avoid extra joins when you only need order total.

**Simple Explanation:**

Avoid extra joins when you only need order total.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. Student-course owning side?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

The side without mappedBy — Course.students here.

**Simple Explanation:**

The side without mappedBy — Course.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. JoinColumn vs JoinTable?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Direct FK vs extra table.

**Simple Explanation:**

Direct FK vs extra table.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Serialization vs persistence?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Jackson ≠ Hibernate. DTOs separate them.

**Simple Explanation:**

Jackson ≠ Hibernate.

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

1. Run seed; SELECT join users/profiles/orders.
2. Draw owning vs inverse.
3. Add a second order via addOrder.
4. Explain LazyInitializationException.
5. Sketch a UserResponse without orders cycle.

***

## Quick Revision

* Owning side has FK.
* mappedBy inverse.
* LAZY + DTO.
* Sync both sides in Java.
* ManyToMany needs join table.

***

## What You Should Be Able To Explain

* mappedBy
* owning side
* infinite JSON
* LAZY
* cascade direction

**Next:** [Day 17](day-17-advanced-jpa.md)
