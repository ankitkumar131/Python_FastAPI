# Day 19 — MongoDB

## Learning Objectives

- Connect to MongoDB with the official Go driver.
- Perform CRUD with filters, options, and BSON struct tags.
- Understand ObjectIDs, cursors, and error handling with MongoDB.
- Decide when a document store fits better than SQL.

## Prerequisites

- Day 18 (repository pattern); Day 14 (JSON — BSON is JSON-like).

## 1. Concept Introduction

MongoDB stores **documents** (BSON — binary JSON) in **collections** inside **databases**. No fixed schema: documents in one collection can differ. The official driver:

```bash
go get go.mongodb.org/mongo-driver
```

```go
client, err := mongo.Connect(ctx, options.Client().ApplyURI("mongodb://localhost:27017"))
coll := client.Database("app").Collection("users")
```

## 2. Why This Concept Exists

Not all data is tabular. Nested, evolving payloads (product catalogs, user profiles, event logs) fit documents naturally — one read gets the whole aggregate, and schema changes don't need migrations. MongoDB is the most used document DB in Go backends; interviews and real jobs expect familiarity.

## 3. Syntax

```go
type User struct {
	ID    primitive.ObjectID `bson:"_id,omitempty"`
	Name  string             `bson:"name"`
	Email string             `bson:"email,omitempty"`
	Age   int                `bson:"age,omitempty"`
}

// insert
res, err := coll.InsertOne(ctx, user)
id := res.InsertedID.(primitive.ObjectID)

// find one
err = coll.FindOne(ctx, bson.M{"_id": id}).Decode(&user) // mongo.ErrNoDocuments

// find many — cursor must be closed
cur, err := coll.Find(ctx, bson.M{"age": bson.M{"$gte": 18}})
defer cur.Close(ctx)
for cur.Next(ctx) {
	var u User
	cur.Decode(&u)
}
err = cur.Err()

// update
res, err = coll.UpdateOne(ctx,
	bson.M{"_id": id},
	bson.M{"$set": bson.M{"name": "Grace"}})

// delete
res, err = coll.DeleteOne(ctx, bson.M{"_id": id})
```

## 4. Detailed Explanation

- **`bson` tags** mirror `json` tags. `omitempty` skips zero values on insert; `_id` maps to the primary key. Without tags, field names are used as-is (lowercased by some conventions — always tag explicitly).
- **`primitive.ObjectID`** is MongoDB's 12-byte id (timestamp + random + counter). Generate with `primitive.NewObjectID()`; convert to string with `.Hex()`.
- **Filters** are BSON documents: `bson.M{"age": bson.M{"$gte": 18, "$lt": 65}}` — the query language in Go literals. `bson.D` preserves key order (needed for compound indexes hints); `bson.M` is a map.
- **Cursors** stream results — `defer cur.Close(ctx)`, iterate `cur.Next(ctx)`, then check `cur.Err()`. Forgetting Close leaks connections, exactly like `rows.Close` yesterday.
- **Errors**: `mongo.ErrNoDocuments` when nothing matched (the `ErrNoRows` equivalent). Duplicate key errors are `mongo.WriteException` with code 11000.
- **Context is mandatory** in every call — timeouts and cancellation propagate to the server.

## 5. Example 1 — Full CRUD

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type User struct {
	ID    primitive.ObjectID `bson:"_id,omitempty" json:"id"`
	Name  string             `bson:"name" json:"name"`
	Email string             `bson:"email" json:"email"`
	Age   int                `bson:"age,omitempty" json:"age,omitempty"`
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI("mongodb://localhost:27017"))
	if err != nil {
		panic(err)
	}
	defer func() { _ = client.Disconnect(context.Background()) }()

	coll := client.Database("app").Collection("users")

	// CREATE
	u := User{Name: "Ada", Email: "ada@example.com", Age: 36}
	res, err := coll.InsertOne(ctx, u)
	if err != nil {
		panic(err)
	}
	oid := res.InsertedID.(primitive.ObjectID)
	fmt.Println("inserted:", oid.Hex())

	// READ one
	var got User
	err = coll.FindOne(ctx, bson.M{"_id": oid}).Decode(&got)
	if errors.Is(err, mongo.ErrNoDocuments) {
		fmt.Println("not found")
		return
	}
	fmt.Printf("%+v\n", got)

	// UPDATE
	_, err = coll.UpdateOne(ctx,
		bson.M{"_id": oid},
		bson.M{"$set": bson.M{"age": 37}})
	fmt.Println("updated:", err)

	// READ many with filter + sort + limit
	cur, err := coll.Find(ctx,
		bson.M{"age": bson.M{"$gte": 18}},
		options.Find().SetSort(bson.M{"name": 1}).SetLimit(10))
	if err != nil {
		panic(err)
	}
	defer cur.Close(ctx)
	for cur.Next(ctx) {
		var u2 User
		if err := cur.Decode(&u2); err != nil {
			panic(err)
		}
		fmt.Println("found:", u2.Name)
	}
	if err := cur.Err(); err != nil {
		panic(err)
	}

	// DELETE
	_, err = coll.DeleteOne(ctx, bson.M{"_id": oid})
	fmt.Println("deleted:", err)
}
```

Run MongoDB locally: `docker run -d -p 27017:27017 mongo:7`

## 6. Example 2 — Projection, count, unique index, duplicate handling

```go
package main

import (
	"context"
	"strings"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func examples(ctx context.Context, coll *mongo.Collection) {
	// projection: only name+email
	cur, _ := coll.Find(ctx, bson.M{},
		options.Find().SetProjection(bson.M{"name": 1, "email": 1, "_id": 0}))
	defer cur.Close(ctx)

	// count
	n, _ := coll.CountDocuments(ctx, bson.M{"age": bson.M{"$gte": 18}})
	_ = n

	// unique index on email
	_, _ = coll.Indexes().CreateOne(ctx, mongo.IndexModel{
		Keys:    bson.M{"email": 1},
		Options: options.Index().SetUnique(true),
	})

	// duplicate detection
	_, err := coll.InsertOne(ctx, bson.M{"name": "x", "email": "ada@example.com"})
	if err != nil {
		var we mongo.WriteException
		if asWriteException(err, &we) {
			for _, e := range we.WriteErrors {
				if e.Code == 11000 {
					println("duplicate email!")
				}
			}
		}
		_ = strings.TrimSpace // placeholder to keep imports tidy
	}
}

func asWriteException(err error, target **mongo.WriteException) bool {
	we, ok := err.(mongo.WriteException)
	if ok {
		*target = &we
	}
	return ok
}
```

(Production code would use `errors.As`-style helpers from the driver's `mongo` package utilities.)

## 7. Real-World Example

Repository behind the same interface as Day 16/18 — proving the abstraction again:

```go
package repository

import (
	"context"
	"errors"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"tasksapi/internal/task"
)

type Mongo struct{ coll *mongo.Collection }

func NewMongo(db *mongo.Database) *Mongo {
	return &Mongo{coll: db.Collection("tasks")}
}

func (m *Mongo) Get(ctx context.Context, idHex string) (task.Task, error) {
	oid, err := primitive.ObjectIDFromHex(idHex)
	if err != nil {
		return task.Task{}, task.ErrNotFound // malformed id → treat as missing
	}
	var doc struct {
		ID    primitive.ObjectID `bson:"_id"`
		Title string             `bson:"title"`
		Done  bool               `bson:"done"`
	}
	err = m.coll.FindOne(ctx, bson.M{"_id": oid}).Decode(&doc)
	if errors.Is(err, mongo.ErrNoDocuments) {
		return task.Task{}, task.ErrNotFound
	}
	if err != nil {
		return task.Task{}, err
	}
	return task.Task{ID: int(doc.ID.Timestamp().Unix()), Title: doc.Title, Done: doc.Done}, nil
}
```

Note the pattern: **translate driver errors into domain errors** at the repository boundary — identical to the SQL day.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Forgetting `defer cur.Close(ctx)` | Connection leak |
| Missing `bson` tags | Fields stored as Go names; `_id` never populated |
| Ignoring `mongo.ErrNoDocuments` | Treating "not found" as a server error |
| Storing ObjectID as string in structs | Type mismatch on decode |
| Not creating indexes | Full scans on every query |
| Using `bson.M` where order matters | Use `bson.D` for ordered documents |

## 9. Best Practices

- Define your structs (with both `bson` and `json` tags) in one models package.
- Create indexes at startup (idempotent `CreateOne`).
- Always bound operations with `context.WithTimeout`.
- Translate driver errors → domain errors in repositories.
- Use `SetProjection` to avoid hauling unneeded fields over the network.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python (pymongo) | Node |
|--------|----|------|------------------|------|
| Driver | mongo-driver | mongodb-driver-sync | pymongo | mongodb |
| Documents | bson.M/D structs | Document | dict | plain objects |
| Ids | ObjectID | ObjectId | ObjectId | ObjectId |
| Errors | ErrNoDocuments/WriteException | MongoException | PyMongoError | MongoError |

## 11. Practical Exercise

1. Docker-run Mongo; insert and read a user.
2. Query with `$gte`/`$lte` age filters.
3. Create a unique email index; trigger and detect a duplicate error.

## 12. Mini Project / Task

Port the tasks API store to MongoDB: `InsertOne`, `Find` with `done` filter, `UpdateOne` with `$set`, `DeleteOne`. Keep the same handler layer — only the repository changes.

## 13. Interview Questions

### Easy
- What is BSON? What is `bson.M` vs `bson.D`?
- How do you find one document or detect "not found"?

### Medium
- Why must cursors be closed? What leaks otherwise?
- How do ObjectIDs compare with auto-increment ids?

### Hard
- How would you model a many-to-many relation in MongoDB vs SQL, and what are the trade-offs?
- Explain write concern and read concern in the Go driver context.

## 14. Daily Practice Questions

### Easy
1. Connect and ping the server.
2. Insert 3 documents; list them all.
3. Find one by `_id` from a hex string.
4. Delete one document; print `DeletedCount`.
5. Project only `name` in a find.

### Medium
6. Update all documents matching a filter with `UpdateMany`.
7. Sort by two fields; limit to 5.
8. Count documents in an age range.
9. Replace a whole document with `ReplaceOne`.
10. Upsert with `options.Update().SetUpsert(true)`.

### Hard
11. Implement pagination with skip/limit AND with range-based (last _id) cursors; compare performance.
12. Use a transaction (requires replica set) to update two collections atomically.
13. Build an aggregation pipeline (`$match`, `$group`, `$sort`) via `mongo.Pipeline`.
14. Design schema for blog posts + comments (embedded vs referenced); justify.
15. Implement a repository with an interface + mstruct fake for unit tests without Mongo.

## 15. Solutions / Hints

- Q10 hint: upsert result reports `MatchedCount`/`UpsertedCount`.
- Q11 hint: range-based cursors avoid skip cost on deep pages: `bson.M{"_id": bson.M{"$gt": lastID}}`.
- Q13 hint: `mongo.Pipeline{bson.D{{Key: "$match", Value: ...}}, ...}`.

## 16. Day Summary

- Documents in, documents out — with BSON tags mapping structs.
- Filters are BSON; cursors stream and must be closed; `ErrNoDocuments` = not found.
- Same repository pattern as SQL: interface + error translation keeps layers clean.

## 17. What To Revise

- Filter operators table; cursor lifecycle.

## 18. What Comes Tomorrow

**Day 20 — Testing**: table-driven tests, `httptest`, benchmarks, and fuzzing — the tools that make Go famous for testability.
