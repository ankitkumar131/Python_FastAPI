# Day 23 — Indexes, aggregation, embed vs ref, Mongo vs SQL

## 🎯 Learning Objectives

By the end of this day you will understand:

- Mongo indexes and text search
- Aggregation pipeline
- Embed vs reference in a blog
- Honest comparison MySQL vs Postgres vs Mongo

---

# 1. Concept

## Aggregation

```js
db.posts.aggregate([
  { $unwind: "$tags" },
  { $group: { _id: "$tags", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

Stages: `$match` `$unwind` `$group` `$sort` `$project`. This is Mongo’s “GROUP BY”.

## Indexes

```java
@Indexed
private String authorName;
@TextIndexed
private String body;
```

## Comparison (none is “best”)

| | MySQL | PostgreSQL | MongoDB |
|---|---|---|---|
| Model | tables | tables | documents |
| Schema | strict | strict | flexible |
| Relations | FK | FK | embed/ref |
| Transactions | mature | mature | replica-set multi-doc |
| Joins | SQL | SQL | $lookup |
| Spring | JPA | JPA | MongoRepository |
| Use | CRUD apps | complex SQL/JSONB | hierarchical / logs / reviews |

Capstone: **Postgres for orders**; **Mongo for reviews** (write-heavy, nested, no joins needed).


---

# Write this on your machine (file by file)

Do **not** copy-paste the whole answer-key folder. Create each file on your laptop, in order.

Suggested folder:

```bash
mkdir -p ~/springboot-practice/day-23
cd ~/springboot-practice/day-23
```

Answer key: `java-springboot-backend/practical/day-23/`

Continue Day 22 app or run JS in mongosh. Package optional Java index example.

| # | File | Why it exists |
|---|---|---|
| 1 | `aggregate.js` | pipeline |
| 2 | `comparison.md` | table you should memorize |

```bash
mongosh app_db aggregate.js
```

Write the comparison table from memory after reading.

---

# Common Mistakes

1. $lookup everywhere instead of designing documents.
2. No index on search fields.
3. Declaring Mongo best.
4. Embedding millions of comments.

---

# Practical Exercise

1. Run aggregation.
2. Explain three rows of the comparison table.
3. Add @Indexed on authorName in Day 22.
4. Sketch capstone data placement.
5. Text search experiment.

---

# Mini Project

Document why product reviews belong in Mongo in the capstone.

---

# Interview Questions

## Easy

### Q1. What is aggregation?

**Difficulty:** Easy

**Answer:**

A pipeline of stages transforming documents.

**Simple Explanation:**

A pipeline of stages transforming documents.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. $group?

**Difficulty:** Easy

**Answer:**

SQL GROUP BY analog.

**Simple Explanation:**

SQL GROUP BY analog.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. $unwind?

**Difficulty:** Easy

**Answer:**

Flattens arrays into documents.

**Simple Explanation:**

Flattens arrays into documents.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. When $lookup?

**Difficulty:** Easy

**Answer:**

Rare join; often a modeling smell.

**Simple Explanation:**

Rare join; often a modeling smell.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. @Indexed?

**Difficulty:** Easy

**Answer:**

Declares a Mongo index.

**Simple Explanation:**

Declares a Mongo index.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Medium

### Q1. Text index?

**Difficulty:** Medium

**Answer:**

Full-text search on string fields.

**Simple Explanation:**

Full-text search on string fields.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. MySQL vs PG vs Mongo one line?

**Difficulty:** Medium

**Answer:**

Default relational vs advanced relational vs documents.

**Simple Explanation:**

Default relational vs advanced relational vs documents.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Transactions in Mongo?

**Difficulty:** Medium

**Answer:**

Need replica set; not the first reason to pick it.

**Simple Explanation:**

Need replica set; not the first reason to pick it.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. 16MB limit?

**Difficulty:** Medium

**Answer:**

Document size cap; don’t embed unbounded lists.

**Simple Explanation:**

Document size cap; don’t embed unbounded lists.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Repository difference?

**Difficulty:** Medium

**Answer:**

JpaRepository vs MongoRepository; id types differ.

**Simple Explanation:**

JpaRepository vs MongoRepository; id types differ.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

## Hard

### Q1. Schema validation in Mongo?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

JSON Schema validator on collection.

**Simple Explanation:**

JSON Schema validator on collection.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q2. Capstone split?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Orders relational; reviews documents.

**Simple Explanation:**

Orders relational; reviews documents.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q3. Pagination Mongo?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Pageable or cursor on _id.

**Simple Explanation:**

Pageable or cursor on _id.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q4. Collation?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Locale-aware string compare.

**Simple Explanation:**

Locale-aware string compare.

**Example:**

```text
See today's practical code.
```

**Interview Tip:**

Tie it to today's files.

**Common Follow-up Question:**

Ask for a real example.

### Q5. Change streams?

**Difficulty:** Hard

**Why?** Relevant to today's topic.

**How?** See answer.

**When?** In production backends and interviews.

**Trade-offs:** Discussed in the answer.

**Real-world example:** This course's practical code.

**Answer:**

Watch collection changes — out of scope but name it.

**Simple Explanation:**

Watch collection changes — out of scope but name it.

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

1. Run aggregation.
2. Explain three rows of the comparison table.
3. Add @Indexed on authorName in Day 22.
4. Sketch capstone data placement.
5. Text search experiment.

---

# Quick Revision

- Aggregation pipeline.
- Indexes.
- Honest DB comparison.
- Reviews→Mongo, orders→SQL.

---

# What You Should Be Able To Explain

- aggregation
- embed vs lookup
- comparison table
- capstone split
- indexes

**Next:** [Day 24](../day-24-spring-security/README.md)
