# Day 9 — Methods

## Learning Objectives

- Define methods with value and pointer receivers.
- Understand method sets and why receiver choice matters for interfaces.
- Attach behavior to any local type, not just structs.
- Follow Go's constructor and receiver conventions.

## Prerequisites

- Day 8: pointers.

## 1. Concept Introduction

A **method** is a function with a **receiver** — a named argument that the method is "called on":

```go
type Rectangle struct{ W, H float64 }

func (r Rectangle) Area() float64 { return r.W * r.H }   // value receiver

func (r *Rectangle) Scale(f float64) { r.W *= f; r.H *= f } // pointer receiver
```

Call: `rect.Area()`, `rect.Scale(2)`. Go has no `this`/`self` keyword — you name the receiver (convention: short, lowercase, consistent, e.g. `r`, `u`, `s`).

## 2. Why This Concept Exists

Methods attach behavior to data so calling code reads as intent (`order.Total()` not `ComputeTotal(order)`), and they enable interfaces (Day 10) — Go's entire polymorphism story is "a type satisfies an interface if it has those methods". Unlike Java, Go lets you define methods on **any type declared in your package** — including `type Celsius float64`.

## 3. Syntax

```go
func (recv Type) Method(args) results  { }  // value receiver — gets a copy
func (recv *Type) Method(args) results { }  // pointer receiver — can mutate
```

Rules:

- One receiver per method; it may be a value or a pointer.
- **Never mix** value and pointer receivers on the same type (go vet/lint warns).
- Only types declared in the same package can have methods — you can't add methods to `int` or `http.Client` from outside.

## 4. Detailed Explanation: method sets (the part interviews probe)

- `Type`'s method set = all **value-receiver** methods.
- `*Type`'s method set = value **and** pointer-receiver methods.

Consequence: if a method has a pointer receiver, only `*Type` satisfies interfaces that require it. If you store values of `Type` in an interface but methods use pointer receivers, the compiler rejects it — this is the #1 beginner interface error, so internalize it now.

Addressability saves you at call sites: calling `rect.Scale(2)` on an addressable variable auto-takes `&rect`. But a non-addressable value (e.g., a map value or a function return) cannot.

## 5. Example 1 — Value vs pointer receivers

```go
package main

import "fmt"

type Counter struct{ n int }

func (c Counter) Value() int { return c.n }       // read-only: value receiver

func (c *Counter) Inc() { c.n++ }                 // mutation: pointer receiver

func main() {
	c := Counter{}
	c.Inc()          // syntactic sugar for (&c).Inc()
	c.Inc()
	fmt.Println(c.Value()) // 2

	// through a pointer variable:
	p := &c
	p.Inc()
	fmt.Println(p.Value()) // 3
}
```

## 6. Example 2 — Methods on non-struct types + String()

```go
package main

import "fmt"

type Celsius float64
type Fahrenheit float64

func (c Celsius) ToF() Fahrenheit {
	return Fahrenheit(c*9/5 + 32)
}

func (f Fahrenheit) String() string {
	return fmt.Sprintf("%.1f°F", float64(f))
}

func main() {
	body := Celsius(37.0)
	fmt.Println(body.ToF()) // 98.6°F — String() called automatically
}
```

`String() string` is special: any type with it satisfies `fmt.Stringer` and prints nicely — Go's `toString()`.

## 7. Real-World Example

A thread-safe in-memory store (the shape appears in countless services):

```go
package main

import (
	"fmt"
	"sync"
)

type Store struct {
	mu sync.Mutex
	users map[int]string
}

func NewStore() *Store {
	return &Store{users: make(map[int]string)}
}

func (s *Store) Add(id int, name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.users[id] = name
}

func (s *Store) Get(id int) (string, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	name, ok := s.users[id]
	return name, ok
}

func main() {
	s := NewStore()
	s.Add(1, "Ada")
	if name, ok := s.Get(1); ok {
		fmt.Println(name)
	}
}
```

Note: methods on `*Store` (must share state, so pointer receiver), plus a `NewStore()` constructor — the standard Go idiom (Go lacks constructors).

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Value receiver that "should" mutate | The mutation happens on a copy and is lost |
| Mixing receiver kinds on one type | Breaks method sets and reader expectations |
| Naming receiver `this`/`self` | Un-idiomatic; use a short type-based name |
| Methods on types from other packages | Compile error — define your own wrapper type |
| Giant methods on god-structs | Split types/responsibilities |

## 9. Best Practices

- Pointer receiver if the method mutates, the struct is large, or it must stay consistent across all methods of the type.
- Keep the receiver name the same across all methods of a type.
- Provide `New<Type>()` constructors that validate and return `(*T, error)` when needed.
- Implement `String()` for debuggable types.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Definition | receiver param in signature | inside class | inside class (self) | class methods |
| this/self | named receiver, no keyword | `this` | `self` explicit | `this` |
| Methods on primitives | Yes, via named types (`type MyInt int`) | No (wrappers) | Yes (monkeypatching banned for builtins) | Yes (prototype) |
| Constructors | `NewX()` functions | constructor | `__init__` | constructor |
| Inheritance | No (embedding + interfaces) | Yes | Yes | Yes |

## 11. Practical Exercise

1. `type Stack []int` with `Push`, `Pop`, `Len` methods (mix of receiver kinds — decide which).
2. Give a `User` type a `String()` method.
3. Implement `NewQueue()` + `Enqueue/Dequeue` with pointer receivers.

## 12. Mini Project / Task

`todo.go`: `type Todos struct{ items []Item }` where `Item{Text string, Done bool}`. Methods: `Add`, `Complete(i int) error`, `List() []Item`, `Pending() int`. CLI front-end with `add/list/done` commands.

## 13. Interview Questions

### Easy
- What is a receiver?
- Value vs pointer receiver — when to use which?

### Medium
- What is a method set, and how does it affect interfaces?
- Why can't you add methods to types from other packages?

### Hard
- Explain why calling a pointer-receiver method on a map value fails to compile.
- How do embedding and method promotion interact with interface satisfaction?

## 14. Daily Practice Questions

### Easy
1. Add an `Area()` method to `Rectangle`.
2. Add `String()` to a `Color` struct.
3. Write a value-receiver method that prints; verify it can't mutate.
4. Write a pointer-receiver `Reset()` that zeroes a struct.
5. Define methods on `type Temperature float64`.

### Medium
6. Implement `Stack` with `Push/Pop/Peek` and errors for empty pops.
7. Implement a `Matrix` type with `At(r, c int) (float64, error)` and `Transpose()`.
8. Implement `String()` on a linked list to print `a -> b -> c`.
9. Show the method-set problem: value stored in an interface with pointer-receiver method — read the error, fix it.
10. Implement `defer`-free `Close()` with idempotency (safe to call twice).

### Hard
11. Implement a `Ring` (circular buffer) type with pointer receivers.
12. Implement an iterator method `Next() (T, bool)` over a custom collection.
13. Build a `Cache` with `Get/Set` and TTL expiry using `time`.
14. Embed a `Base` with methods into `Derived`; override one; call both explicitly.
15. Explain (in comments) exactly which methods exist on `T` vs `*T` for a type with two value and two pointer methods.

## 15. Solutions / Hints

- Q1: `func (r Rectangle) Area() float64`.
- Q6: `Pop` must be pointer receiver (`*Stack`) since it mutates the slice header.
- Q10 hint: `closed bool` guard field.
- Q11 hint: fixed slice + head index; wrap with `% len`.

## 16. Day Summary

- Methods = functions with receivers; receiver choice = semantics choice.
- Method sets: `*T` has both; `T` has only value methods — critical for interfaces.
- `New<T>()` constructors + `String()` are ecosystem conventions.

## 17. What To Revise

- Method-set rules; when each receiver kind is right.

## 18. What Comes Tomorrow

**Day 10 — Interfaces**: implicit satisfaction, the `error` and `io.Writer` types you'll see everywhere, empty interface, and composition.
