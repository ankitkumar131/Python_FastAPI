# Day 10 — Interfaces

## Learning Objectives

- Understand implicit interface satisfaction ("if it quacks like a duck").
- Master the two interfaces you'll meet daily: `error` and `io.Writer`/`io.Reader`.
- Use type assertions and type switches.
- Compose small interfaces; know the empty interface `any` and its trade-offs.

## Prerequisites

- Day 9: methods and method sets.

## 1. Concept Introduction

An interface is a **contract of methods**:

```go
type Speaker interface {
	Speak() string
}
```

Any type with a `Speak() string` method **automatically** satisfies `Speaker` — no `implements` keyword, no declaration. This is **structural (duck) typing, checked at compile time**.

## 2. Why This Concept Exists

Java/C# demand explicit `implements` — meaning you must own the type or write adapters. Go's implicit satisfaction means **you can define interfaces for types you don't own** and make old code fit new abstractions with zero changes. The Go proverb: *"The bigger the interface, the weaker the abstraction."* Standard library interfaces are tiny — often one method.

## 3. Syntax

```go
type Writer interface {
	Write(p []byte) (n int, err error)
}

type ReadWriter interface { // interface composition
	Reader
	Writer
}

var w Writer = myType{}        // implicit satisfaction
s, ok := w.(ConcreteType)      // type assertion (comma-ok)
switch v := w.(type) {         // type switch
case ConcreteA:
	...
default:
	_ = v
}

var anything any = 42          // any == interface{} — matches everything
```

## 4. Detailed Explanation

**Internals (interview favorite)**: an interface value is a pair *(dynamic type, dynamic value)*. `var s Speaker = Dog{}` stores `(Dog, Dog{})`. A nil interface has **no type**; an interface holding a nil `*Dog` pointer is NOT nil — a famous gotcha:

```go
type Speaker interface{ Speak() string }
type Dog struct{}
func (d *Dog) Speak() string { return "woof" }

func main() {
	var d *Dog          // nil pointer
	var s Speaker = d   // s != nil! type=*Dog, value=nil
	fmt.Println(s == nil) // false
	_ = s.Speak()       // works — method handles nil receiver
}
```

**Design rule**: define interfaces where they're **consumed**, not where implemented. Accept interfaces, return concrete types (mostly).

**`error`** is just `interface{ Error() string }` — your custom errors are ordinary types satisfying it (Day 11).

**`any`** (`interface{}`) matches all types but loses type safety; with generics (Day 24) its use is shrinking. Type switches recover the concrete type.

## 5. Example 1 — Implicit satisfaction and polymorphism

```go
package main

import "fmt"

type Shape interface {
	Area() float64
}

type Circle struct{ R float64 }
type Square struct{ Side float64 }

func (c Circle) Area() float64 { return 3.14159 * c.R * c.R }
func (s Square) Area() float64 { return s.Side * s.Side }

// totalArea works on ANY Shape — no knowledge of Circle/Square.
func totalArea(shapes []Shape) float64 {
	sum := 0.0
	for _, s := range shapes {
		sum += s.Area()
	}
	return sum
}

func main() {
	shapes := []Shape{
		Circle{R: 1},
		Square{Side: 2},
		// Add a Triangle later; totalArea needs NO change.
	}
	fmt.Println(totalArea(shapes))
}
```

## 6. Example 2 — Type assertion and type switch

```go
package main

import (
	"fmt"
	"strings"
)

type Logger interface {
	Log(msg string)
}

type ConsoleLogger struct{}
type PrefixLogger struct{ Prefix string }

func (ConsoleLogger) Log(msg string) { fmt.Println(msg) }
func (p PrefixLogger) Log(msg string) { fmt.Println(p.Prefix, msg) }

func describe(l Logger) string {
	switch v := l.(type) {
	case ConsoleLogger:
		return "plain console"
	case PrefixLogger:
		return "prefixed with " + v.Prefix
	default:
		return "unknown logger"
	}
}

func main() {
	var l Logger = PrefixLogger{Prefix: "[api]"}
	l.Log("started") // [api] started

	if pl, ok := l.(PrefixLogger); ok {
		fmt.Println("asserted:", strings.ToUpper(pl.Prefix))
	}
	fmt.Println(describe(l))
}
```

## 7. Real-World Example

`io.Writer` — the most important interface in Go. Everything accepts it: files, HTTP responses, buffers, hashes, compression streams:

```go
package main

import (
	"bytes"
	"fmt"
	"os"
)

// Works with ANY Writer: file, buffer, HTTP response, gzip...
func report(w interface{ Write([]byte) (int, error) }, msg string) {
	fmt.Fprintf(w, "%s\n", msg)
}

func main() {
	report(os.Stdout, "to stdout")

	var buf bytes.Buffer
	report(&buf, "to buffer")
	fmt.Print("buffer contains: ", buf.String())
}
```

One function, zero changes, works with every sink in the ecosystem — that is interface-driven design.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Storing value where pointer methods are required | `T` doesn't satisfy the interface; store `&T` (method sets, Day 9) |
| Confusing "interface holding nil pointer" with nil interface | The `(type, value)` pair makes them differ |
| Giant interfaces (many methods) | Split into single-method interfaces |
| Overusing `any` | Loses type safety; prefer generics or concrete types |
| Defining interfaces next to implementations only | Define at the consumer for real decoupling |

## 9. Best Practices

- Keep interfaces small (1–3 methods); compose them when you need more.
- Accept interfaces, return structs.
- Name single-method interfaces after the method: `Reader`, `Closer`, `Stringer`.
- Use `errors.As/Is` for interface-based error handling (Day 11).

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Declaration of intent | Implicit | `implements` | Protocol (typing) | None (duck at runtime) |
| Check time | Compile | Compile | Runtime (mypy) | Runtime |
| Multiple inheritance of contract | Yes (compose) | Multiple interfaces | Mixins | — |
| Default methods | No | Yes | No | — |

## 11. Practical Exercise

1. Add a `Triangle` to Example 1 without touching `totalArea`.
2. Implement `fmt.Stringer` for a `Money{Cents int}` type (print `$1.23`).
3. Type-switch over `[]any{1, "a", true, 3.14}` and print each type name.

## 12. Mini Project / Task

`notifier.go`: define `interface{ Notify(subject, body string) error }`. Implement `EmailNotifier` and `LogNotifier`. A `Broadcast(notifiers []Notifier, ...)` function fans out — proving the abstraction works for future SMS/Slack notifiers without changes.

## 13. Interview Questions

### Easy
- How does a type satisfy a Go interface?
- What is `any`?

### Medium
- Explain the interface `(type, value)` pair and the nil-interface gotcha.
- What are type assertions and type switches?

### Hard
- Why does Go prefer many small interfaces? Give stdlib examples.
- Explain interface method sets: why must a value receiver type be used differently from a pointer receiver type when stored in interfaces?

## 14. Daily Practice Questions

### Easy
1. Define an interface `Greeter` with `Greet() string`; satisfy it with two types.
2. Print a custom type using `fmt.Stringer`.
3. Perform a safe type assertion with comma-ok.
4. Compose two one-method interfaces into a third.
5. Show that an empty struct with no methods satisfies NO non-empty interface.

### Medium
6. Implement `sort.Interface` (`Len/Less/Swap`) for a custom slice; sort with `sort.Sort`.
7. Write a function accepting `io.Writer` and write to both a file and a buffer.
8. Demonstrate the nil-pointer-in-interface gotcha and explain the output.
9. Implement `error` on a custom type (preview of Day 11).
10. Write a generic `firstNonNil` over `[]error` using interface checks.

### Hard
11. Build a plugin registry: `map[string]Handler` where `Handler` is an interface; register/unregister at runtime.
12. Explain (with a diagram-in-comments) how an interface call is dispatched at runtime (itab).
13. Refactor a function taking `*os.File` to take `io.Reader`; verify with `strings.NewReader`.
14. Implement `interface{ M() }` satisfaction through embedding only.
15. Write a type-switch-based JSON-ish value printer over `any` handling nil, numbers, strings, slices, maps.

## 15. Solutions / Hints

- Q6: implement the three methods; `sort.Sort(byTitle Books)`.
- Q8: `var p *T = nil; var i I = p; i == nil` is false.
- Q13 hint: `strings.NewReader` satisfies `io.Reader`; callers pass files, buffers, or network streams.

## 16. Day Summary

- Interfaces = implicit method contracts; satisfaction is compile-time duck typing.
- Interface values are (type, value) pairs — the nil gotcha.
- Small interfaces + composition = Go's power (`io.Writer`, `error`, `fmt.Stringer`).

## 17. What To Revise

- The nil-in-interface gotcha; accept-interfaces-return-structs.

## 18. What Comes Tomorrow

**Day 11 — Error handling**: the `error` interface, wrapping with `%w`, `errors.Is/As`, custom error types, and why Go rejects exceptions.
