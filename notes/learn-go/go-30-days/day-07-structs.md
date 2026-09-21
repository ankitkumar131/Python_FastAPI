# Day 7 — Structs

## Learning Objectives

- Define and initialize structs; understand field-by-field zero values.
- Compare structs, copy them, and choose value vs pointer semantics.
- Use embedded structs (Go's composition) and struct tags.
- Know when to use structs vs maps.

## Prerequisites

- Days 1–6.

## 1. Concept Introduction

A **struct** groups related fields into one named type:

```go
type User struct {
	ID    int
	Name  string
	Email string
	Admin bool
}
```

Structs are Go's equivalent of classes (data part) — but with **no inheritance**; behavior is added via methods (Day 9) and composition via embedding.

## 2. Why This Concept Exists

Go has no classes, yet real systems need named data shapes. Structs give you: compile-time-checked fields (vs stringly-typed maps), guaranteed zero values, cheap value copies, and — via tags — declarative metadata that powers `encoding/json`, ORMs, and validation libraries.

## 3. Syntax

```go
type Point struct{ X, Y int }

// construction styles
p1 := Point{1, 2}          // positional — discouraged after edits
p2 := Point{X: 1, Y: 2}    // keyed — preferred
p3 := Point{}              // zero value {0, 0}
var p4 Point               // same zero value

// access & mutation
p2.X = 10

// anonymous structs (one-off shapes)
cfg := struct {
	Host string
	Port int
}{Host: "localhost", Port: 8080}
```

## 4. Detailed Explanation

- **Value semantics**: assigning or passing a struct **copies it** (shallow copy — pointer/slice fields share targets). Two struct values are equal (`==`) iff all comparable fields are equal. Structs containing slices/maps are NOT comparable.
- **Empty struct** `struct{}` occupies zero bytes — used as a set value (`map[string]struct{}`) or a signal channel (Day 22).
- **Embedding**: putting one struct inside another without a field name promotes its fields/methods upward — Go's replacement for inheritance (composition, not "is-a").

```go
type Base struct{ ID int }
type Post struct {
	Base          // embedded
	Title string
}
p := Post{}
p.ID = 7 // promoted from Base
```

- **Tags**: string metadata after fields, read via reflection:

```go
type APIUser struct {
	Name  string `json:"name" validate:"required"`
	Email string `json:"email,omitempty"`
}
```

## 5. Example 1 — Structs in action

```go
package main

import "fmt"

type Rectangle struct {
	Width, Height float64
}

func area(r Rectangle) float64 {
	return r.Width * r.Height
}

func main() {
	r := Rectangle{Width: 3, Height: 4}
	fmt.Println(area(r)) // 12

	r2 := r // full copy
	r2.Width = 100
	fmt.Println(r.Width, r2.Width) // 3 100 — independent copies

	fmt.Println(r == Rectangle{3, 4}) // true — comparable
}
```

## 6. Example 2 — Embedding and tags

```go
package main

import (
	"encoding/json"
	"fmt"
)

type Timestamps struct {
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

type Article struct {
	ID    int    `json:"id"`
	Title string `json:"title"`
	Timestamps  // embedded: its fields appear in Article's JSON
	Draft bool   `json:"draft,omitempty"`
}

func main() {
	a := Article{ID: 1, Title: "Go", Timestamps: Timestamps{CreatedAt: "today"}}
	b, _ := json.Marshal(a)
	fmt.Println(string(b))
	// {"id":1,"title":"Go","created_at":"today","updated_at":"","draft" omitted}
}
```

## 7. Real-World Example

Every Go API has structs like this — the request/response contract:

```go
package main

import "fmt"

type CreateUserRequest struct {
	Name     string `json:"name"`
	Email    string `json:"email"`
	Password string `json:"-"` // never serialized
}

type UserResponse struct {
	ID    int    `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}

func toResponse(id int, req CreateUserRequest) UserResponse {
	return UserResponse{ID: id, Name: req.Name, Email: req.Email}
}

func main() {
	req := CreateUserRequest{Name: "Ada", Email: "ada@example.com", Password: "secret"}
	fmt.Printf("%+v\n", toResponse(42, req))
}
```

Separating request/response/user structs is a core production pattern (Day 17 expands this).

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Positional literals `Point{1, 2}` | Breaks when fields are added; use keyed fields |
| Assuming struct copies deep-copy pointer fields | Slice/map/pointer fields still share memory |
| Comparing structs with slice/map fields with `==` | Compile error — compare field-wise or reflect.DeepEqual |
| Field names must be unique-ish with embedding | Ambiguous promoted fields are compile errors |
| Forgetting exported-field rule for JSON | Lowercase fields are invisible to `encoding/json` outside the package |

## 9. Best Practices

- Always use keyed struct literals.
- Keep structs small; split by responsibility.
- Use `struct{}{} for sets: `set := map[string]struct{}{}`.
- Put validation in constructors: `NewUser(...) (User, error)`.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Data class | struct | class/record | dataclass/TypedDict | object/class |
| Inheritance | None — embedding | extends | inheritance | prototype chain |
| Equality | Field-wise `==` if comparable | equals() | `__eq__` | reference/`===` |
| Metadata | struct tags | annotations | decorators | none standard |

## 11. Practical Exercise

1. Define `Book` (title, author, pages); create 3 books; find the longest.
2. Demonstrate value-copy independence between two struct variables.
3. Embed `Address` in `Customer`; set promoted fields directly.

## 12. Mini Project / Task

`inventory.go`: `map[string]Item` where `Item` is a struct (qty, price). CLI: `add name qty price`, `update name qty`, `show name`, `total` (sum of qty×price over all items).

## 13. Interview Questions

### Easy
- What is the zero value of a struct?
- How do you copy a struct?

### Medium
- What is struct embedding and how does it differ from inheritance?
- What are struct tags used for?

### Hard
- When is `==` legal between two struct values, and why?
- Why is `struct{}` zero-size, and what are two idiomatic uses of it?

## 14. Daily Practice Questions

### Easy
1. Define a `Point` struct and print its zero value.
2. Create a struct with a constructor function returning `(Struct, error)`.
3. Make an anonymous struct for config and print it with `%+v`.
4. Compare two equal structs with `==`.
5. Embed one struct in another and access a promoted field.

### Medium
6. Write `distance(p1, p2 Point) float64`.
7. Build a slice of structs and sort by a field with `slices.SortFunc`.
8. Show shallow-copy sharing: a struct with a slice field, copied and mutated.
9. Use a struct tag with `encoding/json` and marshal a struct.
10. Implement a `set` backed by `map[string]struct{}` with add/has/remove.

### Hard
11. Write `deepEqual(a, b any) bool` for nested structs of scalars (recursion, no reflect).
12. Demonstrate why an unexported field breaks JSON marshaling from another package.
13. Implement a constructor with validation (non-empty name, valid email regex).
14. Build a doubly linked list of struct nodes with insert/delete.
15. Use reflection to read struct tags and print them (`reflect.TypeOf(...).Field(i).Tag`).

## 15. Solutions / Hints

- Q7: `slices.SortFunc(books, func(a, b Book) int { return b.Pages - a.Pages })` (mind overflow for huge ints — use `cmp.Compare`).
- Q10 hint: `if _, ok := set[k]; ok { ... }`.
- Q15 hint: `t := reflect.TypeOf(u); f, _ := t.FieldByName("Name"); fmt.Println(f.Tag.Get("json"))`.

## 16. Day Summary

- Structs = named, typed, zero-valued data groups; value semantics.
- Embedding = composition; tags = metadata for JSON/ORMs.
- Keyed literals always; comparable only if all fields are.

## 17. What To Revise

- Value-copy semantics; embedding vs inheritance; `omitempty`/`json:"-"` tags.

## 18. What Comes Tomorrow

**Day 8 — Pointers**: `&` and `*`, when Go uses pointer receivers, nil checks, and escaping the "everything copies" value semantics.
