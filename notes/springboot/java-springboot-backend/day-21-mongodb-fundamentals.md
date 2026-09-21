# day-21-mongodb-fundamentals

## Day 21 — MongoDB and documents from zero

### 🎯 Learning Objectives

By the end of this day you will understand:

* NoSQL vs relational
* database, collection, document, BSON, ObjectId
* embed vs reference
* when Mongo vs SQL
* connection URI

***

## 1. Concept — document database

MongoDB stores **BSON documents** in **collections**. No fixed schema required (you should still design one).

```json
{ "_id": "ObjectId(...)", "title": "Hello", "tags": ["java", "mongo"], "author": { "name": "Ada" } }
```

### Vocabulary

| Mongo      | Rough SQL analog |
| ---------- | ---------------- |
| database   | database         |
| collection | table            |
| document   | row (but nested) |
| field      | column           |
| ObjectId   | surrogate key    |

### Embed vs reference

* **Embed** comments inside a post if you always load them together and they don’t explode in size.
* **Reference** (`authorId`) if you would duplicate a large author or many-to-many.

### When Mongo

Flexible shape, hierarchical data, high write volume of similar docs (reviews, logs).

### When not

Heavy multi-row transactions/joins as the core of the domain (orders+inventory+payments) — Postgres/MySQL.

```properties
spring.data.mongodb.uri=mongodb://localhost:27017/app_db
```

***

## Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-21
cd ~/springboot-practice/day-21
```

Answer key: `java-springboot-backend/practical/day-21/`

Docker mongo:7. mongosh. No Java required today.

| # | File        | Why it exists          |
| - | ----------- | ---------------------- |
| 1 | `sample.js` | insert/find in mongosh |

```bash
mongosh app_db sample.js
```

Type the JS into mongosh line by line if you prefer.

***

## Common Mistakes

1. Treating Mongo as schema-less chaos.
2. Embedding unbounded arrays.
3. Using Mongo because it's trendy for orders+payments.
4. Forgetting \_id is ObjectId not Long.
5. Connection refused 27017.

***

## Practical Exercise

1. insertOne a post.
2. find by tag.
3. update a nested field.
4. Draw embed vs ref.
5. Explain BSON.

***

## Mini Project

Model a blog post with embedded comments (max a few dozen).

***

## Interview Questions

### Easy

#### Q1. What is a document?

**Difficulty:** Easy

**Answer:**

A BSON object stored in a collection.

**Simple Explanation:**

A BSON object stored in a collection.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. BSON?

**Difficulty:** Easy

**Answer:**

Binary JSON with extra types (ObjectId, Date, Decimal128).

**Simple Explanation:**

Binary JSON with extra types (ObjectId, Date, Decimal128).

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. ObjectId?

**Difficulty:** Easy

**Answer:**

12-byte default \_id.

**Simple Explanation:**

12-byte default \_id.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Collection?

**Difficulty:** Easy

**Answer:**

A group of documents, like a table without fixed columns.

**Simple Explanation:**

A group of documents, like a table without fixed columns.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Embed vs ref?

**Difficulty:** Easy

**Answer:**

Nested vs pointing at another collection.

**Simple Explanation:**

Nested vs pointing at another collection.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Medium

#### Q1. When Mongo?

**Difficulty:** Medium

**Answer:**

Flexible hierarchical data, logs, reviews.

**Simple Explanation:**

Flexible hierarchical data, logs, reviews.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. When not?

**Difficulty:** Medium

**Answer:**

Complex relational constraints and joins.

**Simple Explanation:**

Complex relational constraints and joins.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. URI?

**Difficulty:** Medium

**Answer:**

mongodb://localhost:27017/app\_db

**Simple Explanation:**

mongodb://localhost:27017/app\_db.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. No schema?

**Difficulty:** Medium

**Answer:**

Driver/app still enforce a schema; JSON Schema exists too.

**Simple Explanation:**

Driver/app still enforce a schema; JSON Schema exists too.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Transactions?

**Difficulty:** Medium

**Answer:**

Exist (replica set) but not the historic sweet spot.

**Simple Explanation:**

Exist (replica set) but not the historic sweet spot.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Hard

#### Q1. Index in Mongo?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Yes, including compound and text.

**Simple Explanation:**

Yes, including compound and text.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q2. Unbounded array?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Document 16MB limit; pagination pain.

**Simple Explanation:**

Document 16MB limit; pagination pain.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q3. SQL join analog?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

$lookup — use sparingly.

**Simple Explanation:**

$lookup — use sparingly.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q4. Primary key?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

\_id unique per collection.

**Simple Explanation:**

\_id unique per collection.

**Example:**

```
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

#### Q5. Compass?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

GUI to inspect documents.

**Simple Explanation:**

GUI to inspect documents.

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

1. insertOne a post.
2. find by tag.
3. update a nested field.
4. Draw embed vs ref.
5. Explain BSON.

***

## Quick Revision

* Documents not rows.
* Embed vs ref.
* ObjectId.
* URI 27017.
* Not a silver bullet.

***

## What You Should Be Able To Explain

* document
* embed vs reference
* when Mongo
* ObjectId
* URI

**Next:** [Day 22](day-22-spring-data-mongodb.md)
