# Day 24 — Generics

## Learning Objectives

- Write functions and types with type parameters.
- Use constraints: `comparable`, `any`, and custom (union) constraints.
- Recognize when generics help vs when interfaces are better.
- Build generic data structures (Stack, Map/Filter/Reduce).

## Prerequisites

- Day 10 interfaces; Day 9 methods.

## 1. Concept Introduction

Since Go 1.18, functions and types can take **type parameters**:

```go
func Max[T cmp.Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

x := Max[int](3, 7) // explicit
y := Max(3.5, 1.2)  // inferred: float64
```

The `[T constraint]` declares a placeholder type; the constraint limits what operations the body may use.

## 2. Why This Concept Exists

Before generics, reusable code needed either duplication (one `MaxInt`, `MaxFloat64`...) or `interface{}` (runtime type assertions, no safety, boxing). Generics give compile-time-safe reuse with zero runtime overhead — the compiler generates specialized code. They complete Go's type system for containers and algorithms without changing Go's simple runtime model.

## 3. Syntax

```go
// constraint = interface listing required operations
type Number interface {
	~int | ~int64 | ~float64 // ~ = include named types with this underlying type
}

func Sum[T Number](nums []T) T {
	var s T
	for _, n := range nums {
		s += n
	}
	return s
}

// generic type
type Stack[T any] struct{ items []T }

func (s *Stack[T]) Push(v T) { s.items = append(s.items, v) }
func (s *Stack[T]) Pop() (T, bool) {
	var zero T
	if len(s.items) == 0 {
		return zero, false
	}
	last := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return last, true
}
```

Built-in constraints: `any` (no restrictions), `comparable` (supports `==`, usable as map keys).

## 4. Detailed Explanation

- **Constraints are interfaces**: any interface works, but type sets matter. `interface{ C() string }` requires methods; union `int | string` allows only those types (and `~T` includes defined types with underlying `T`).
- **The `cmp.Ordered` stdlib constraint** covers all types with `<`.
- **Inference**: usually you omit `[T]` at call sites; specify it when inference fails (untyped nil, ambiguous cases).
- **No methods on generic parameters**: you can't call arbitrary methods on `T any` — only what the constraint guarantees. Need methods → use an interface parameter instead.
- **Generics vs interfaces**: generics = same code, many types, decided at compile time. Interfaces = many code paths, one call site, decided at runtime (dynamic dispatch). Containers/algorithms → generics; pluggable behavior → interfaces.

## 5. Example 1 — Generic functions

```go
package main

import (
	"cmp"
	"fmt"
)

func Max[T cmp.Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

func Sum[T ~int | ~float64](nums []T) T {
	var total T
	for _, n := range nums {
		total += n
	}
	return total
}

// Map/Filter/Reduce — the functional trio, type-safe
func Map[T, U any](in []T, f func(T) U) []U {
	out := make([]U, 0, len(in))
	for _, v := range in {
		out = append(out, f(v))
	}
	return out
}

func Filter[T any](in []T, pred func(T) bool) []T {
	out := make([]T, 0, len(in))
	for _, v := range in {
		if pred(v) {
			out = append(out, v)
		}
	}
	return out
}

func Reduce[T, U any](in []T, init U, f func(U, T) U) U {
	acc := init
	for _, v := range in {
		acc = f(acc, v)
	}
	return acc
}

func main() {
	fmt.Println(Max(3, 7), Max("go", "gopher"))           // 7 gopher
	fmt.Println(Sum([]int{1, 2, 3}), Sum([]float64{1.5, 2.5})) // 6 4

	names := Map([]int{1, 2, 3}, func(n int) string {
		return fmt.Sprintf("id-%d", n)
	})
	fmt.Println(names) // [id-1 id-2 id-3]

	evens := Filter([]int{1, 2, 3, 4}, func(n int) bool { return n%2 == 0 })
	fmt.Println(evens) // [2 4]

	total := Reduce([]int{1, 2, 3}, 0, func(acc, n int) int { return acc + n })
	fmt.Println(total) // 6
}
```

## 6. Example 2 — Generic types

```go
package main

import "fmt"

type Stack[T any] struct{ items []T }

func (s *Stack[T]) Push(v T)         { s.items = append(s.items, v) }
func (s *Stack[T]) Len() int         { return len(s.items) }
func (s *Stack[T]) Pop() (T, bool) {
	var zero T
	if len(s.items) == 0 {
		return zero, false
	}
	v := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return v, true
}

type Set[T comparable] map[T]struct{}

func NewSet[T comparable](items ...T) Set[T] {
	s := make(Set[T], len(items))
	for _, it := range items {
		s[it] = struct{}{}
	}
	return s
}
func (s Set[T]) Has(v T) bool { _, ok := s[v]; return ok }
func (s Set[T]) Add(v T)      { s[v] = struct{}{} }

func main() {
	s := &Stack[string]{}
	s.Push("a")
	s.Push("b")
	for s.Len() > 0 {
		v, _ := s.Pop()
		fmt.Println(v) // b a
	}

	set := NewSet(1, 2, 3)
	set.Add(4)
	fmt.Println(set.Has(2), set.Has(9)) // true false
}
```

## 7. Real-World Example

A generic in-memory cache used by any service:

```go
package main

import (
	"fmt"
	"sync"
	"time"
)

type entry[V any] struct {
	value     V
	expiresAt time.Time
}

type Cache[K comparable, V any] struct {
	mu   sync.RWMutex
	data map[K]entry[V]
	ttl  time.Duration
}

func NewCache[K comparable, V any](ttl time.Duration) *Cache[K, V] {
	return &Cache[K, V]{data: make(map[K]entry[V]), ttl: ttl}
}

func (c *Cache[K, V]) Set(k K, v V) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.data[k] = entry[V]{value: v, expiresAt: time.Now().Add(c.ttl)}
}

func (c *Cache[K, V]) Get(k K) (V, bool) {
	c.mu.RLock()
	e, ok := c.data[k]
	c.mu.RUnlock()
	if !ok || time.Now().After(e.expiresAt) {
		var zero V
		return zero, false
	}
	return e.value, true
}

func main() {
	users := NewCache[string, string](50 * time.Millisecond)
	users.Set("u1", "Ada")
	if name, ok := users.Get("u1"); ok {
		fmt.Println("hit:", name)
	}
	time.Sleep(60 * time.Millisecond)
	if _, ok := users.Get("u1"); !ok {
		fmt.Println("expired — refetch from DB")
	}
}
```

One implementation, type-safe for any key/value — before generics this needed codegen or `interface{}` casts.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| `T any` then calling methods on it | `any` guarantees nothing; constrain or take an interface |
| Forgetting `~` in unions | `int | MyIntNamed` without `~int` excludes defined types |
| Generic when a simple interface suffices | Adds complexity without payoff |
| Generics + methods on the type parameter | Not supported; design around it |
| Using `comparable` types as map keys with slice fields | Compile error — good, that's the point |

## 9. Best Practices

- Start concrete; genericize only on the second or third duplication.
- Prefer stdlib constraints (`cmp.Ordered`, `comparable`); name custom ones clearly (`Number`, `Hashable`).
- Keep generic functions small; inference works best with simple signatures.
- Place type params left-to-right: inputs `T`, outputs `U`.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JS/TS |
|--------|----|------|--------|-------|
| Mechanism | GC-shape stenciling | erasure | duck typing | erased |
| Constraints | type sets/interfaces | bounds | none (runtime) | extends |
| Runtime cost | ~zero | boxing for primitives | n/a | n/a |
| Since | 1.18 (2022) | 5 | always | TS only |

## 11. Practical Exercise

1. Write generic `Min` and use it on ints and strings.
2. Implement `Keys[K comparable, V any](m map[K]V) []K`.
3. Build a generic `Queue[T]` with `Enqueue/Dequeue`.

## 12. Mini Project / Task

`genericslib.go`: implement `Chunk`, `Unique`, `GroupBy` (returns `map[K][]T`), and a generic BST with `Insert`/`Contains` constrained by `cmp.Ordered`. Table-driven tests for each (Day 20 style).

## 13. Interview Questions

### Easy
- What are type parameters?
- What does `comparable` constrain?

### Medium
- `~int` in a union — what does `~` mean?
- Generics vs interfaces — how do you choose?

### Hard
- Explain Go's implementation approach (GC shape stenciling + dictionaries) and its performance trade-offs.
- Why can't Go methods have their own type parameters?

## 14. Daily Practice Questions

### Easy
1. Write `Max`/`Min` for ordered types.
2. `Sum` over int and float64 slices.
3. `Contains[T comparable](s []T, v T) bool`.
4. Instantiate `Stack[int]` and push/pop.
5. Write `Zero[T any]() T` returning the zero value.

### Medium
6. `Map`/`Filter` with closures.
7. `Keys` and `Values` for maps.
8. Generic `Set[T comparable]` with union operation.
9. `Clamp[T cmp.Ordered](v, lo, hi T) T`.
10. `First[T any](s []T) (T, bool)` handling empty slices.

### Hard
11. Generic `Heap[T cmp.Ordered]` (container/heap-free implementation).
12. `Zip[T, U any](a []T, b []U) [](struct{T; U})`-style pair slice.
13. Implement a generic `Either[L, R any]` type with `IsLeft/Unwrap`.
14. Write `SortBy[T any](s []T, key func(T) K)` with `cmp.Ordered K`, using slices.SortFunc.
15. Explain in comments why `func (s *Stack[T]) Map[U any](f func(T) U) *Stack[U]` is legal but methods can't declare NEW type parameters beyond the receiver's.

## 15. Solutions / Hints

- Q9: `return min(max(v, lo), hi)`.
- Q11 hint: slice-backed heap; `up/down` sift operations.
- Q15 hint: methods may only use the receiver's type parameters; `Map` works because `U` is declared on the method itself — wait, it must be a plain function or use receiver params only — explore why the method form actually does NOT compile and produce the function form `MapStack[T, U any](s *Stack[T], f func(T) U) *Stack[U]`.

## 16. Day Summary

- `[T constraint]` = compile-time-safe reuse; unions + `~` define type sets.
- Generic types (Stack, Set, Cache) replace codegen and `interface{}` casts.
- Rule: generics for data structures/algorithms, interfaces for behavior.

## 17. What To Revise

- Constraint syntax; when NOT to use generics.

## 18. What Comes Tomorrow

**Day 25 — CLI development**: flag parsing, stdin/stdout, exit codes, and building professional command-line tools.
