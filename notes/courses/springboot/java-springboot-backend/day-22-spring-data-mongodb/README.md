# Day 22 — Spring Data MongoDB CRUD Blog API

## 🎯 Learning Objectives

By the end of this day you will understand:

- @Document @Id @Field
- MongoRepository
- CRUD + search + pagination
- String ids (ObjectId hex)

---

# 1. Concept

Spring Data MongoDB mirrors JPA’s repository style:

```java
public interface PostRepository extends MongoRepository<Post, String> {}
```

`@Document(collection="posts")` not `@Entity`. Id is usually `String`.

```properties
spring.data.mongodb.uri=mongodb://localhost:27017/app_db
```

No `ddl-auto`. Collections appear when you insert.


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-22
cd ~/springboot-practice/day-22
```

Answer key: `java-springboot-backend/practical/day-22/`

Mongo running. starter-data-mongodb + web.

| # | File | Why it exists |
|---|---|---|
| 1 | `Post.java` | @Document |
| 2 | `PostRepository.java` | MongoRepository |
| 3 | `PostController.java` | CRUD |

```bash
mvn spring-boot:run
curl -s -X POST http://localhost:8080/api/posts -H 'Content-Type: application/json' -d '{"title":"Hello","body":"...","authorName":"Ada","tags":["java"]}'
```

Open Compass and watch the document appear. Id is a 24-char hex string.

---

# Common Mistakes

1. Using Long id.
2. @Entity on a document.
3. MySQL properties left in.
4. Unbounded comments array without thought.
5. Exposing internal fields without DTO (exercise).

---

# Practical Exercise

1. POST a post.
2. GET by id.
3. search?q=He.
4. Page list.
5. Compass inspect.

---

# Mini Project

Add Comment embedded class List<Comment> on Post.

---

# Interview Questions

## Easy

### Q1. @Document vs @Entity?

**Difficulty:** Easy

**Answer:**

Mongo mapping vs JPA.

**Simple Explanation:**

Mongo mapping vs JPA.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. MongoRepository?

**Difficulty:** Easy

**Answer:**

Spring Data interface for Mongo.

**Simple Explanation:**

Spring Data interface for Mongo.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Id type?

**Difficulty:** Easy

**Answer:**

String ObjectId hex typically.

**Simple Explanation:**

String ObjectId hex typically.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. URI property?

**Difficulty:** Easy

**Answer:**

spring.data.mongodb.uri

**Simple Explanation:**

spring.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. findByTags?

**Difficulty:** Easy

**Answer:**

Query method on array field.

**Simple Explanation:**

Query method on array field.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. No schema migration?

**Difficulty:** Medium

**Answer:**

Collections are implicit; still version your app.

**Simple Explanation:**

Collections are implicit; still version your app.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. @Field?

**Difficulty:** Medium

**Answer:**

Rename JSON/BSON field vs Java name.

**Simple Explanation:**

Rename JSON/BSON field vs Java name.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Pageable?

**Difficulty:** Medium

**Answer:**

Works like JPA.

**Simple Explanation:**

Works like JPA.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. save semantics?

**Difficulty:** Medium

**Answer:**

Insert or replace by id.

**Simple Explanation:**

Insert or replace by id.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. When @DBRef?

**Difficulty:** Medium

**Answer:**

Reference other documents — use carefully.

**Simple Explanation:**

Reference other documents — use carefully.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Indexes?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

@Indexed on fields.

**Simple Explanation:**

@Indexed on fields.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Validation?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Still Bean Validation on DTOs.

**Simple Explanation:**

Still Bean Validation on DTOs.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Transactions?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Need replica set for multi-doc tx.

**Simple Explanation:**

Need replica set for multi-doc tx.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Why Blog on Mongo?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Nested comments/tags fit documents.

**Simple Explanation:**

Nested comments/tags fit documents.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. DTO?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Still recommended; this sample returns Post for brevity.

**Simple Explanation:**

Still recommended; this sample returns Post for brevity.

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

1. POST a post.
2. GET by id.
3. search?q=He.
4. Page list.
5. Compass inspect.

---

# Quick Revision

- @Document.
- MongoRepository<Post,String>.
- URI 27017.
- Search + page.

---

# What You Should Be Able To Explain

- @Document
- String id
- query methods
- no ddl-auto
- Compass check

**Next:** [Day 23](../day-23-advanced-mongodb/README.md)
