# Day 4 — Functions

## Learning Objectives

- Define functions with multiple return values and named results.
- Use variadic parameters and anonymous/closure functions.
- Understand functions as first-class values (callbacks, function types).
- Use `defer` correctly and know its evaluation rules.

## Prerequisites

- Days 1–3.

## 1. Concept Introduction

Functions in Go are the primary unit of composition:

```go
func add(a, b int) int {
	return a + b
}
```

Signature shape: `func name(params) (results) { body }`. Results are declared **after** parameters, and a function may return **multiple values** — the feature that makes Go's error handling possible (Day 11).

## 2. Why This Concept Exists

C uses out-parameters and error codes; Java throws exceptions. Go instead made **multiple returns** a first-class feature so the idiomatic pattern `result, err := f()` works everywhere without exceptions, tuples-as-objects, or mutable out-params. Combined with closures and `defer`, Go covers resource management and callbacks with tiny syntax.

## 3. Syntax

```go
// single return
func square(x int) int { return x * x }

// multiple returns (idiomatic: value, error)
func divide(a, b float64) (float64, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}

// named returns
func split(sum int) (x, y int) {
	x = sum * 4 / 9
	y = sum - x
	return // "naked" return — returns current x, y
}

// variadic
func total(nums ...int) int { /* nums is []int */ return 0 }

// function type & anonymous function
var op func(int, int) int = func(a, b int) int { return a + b }
```

## 4. Detailed Explanation

- **Multiple return values** are the norm; `nil` + error is the standard failure shape.
- **Named returns** document results and help with `defer`-based error wrapping (Day 11), but "naked returns" in long functions hurt readability — use sparingly.
- **Variadic** `...T` becomes a slice `[]T` inside. Pass an existing slice with `f(s...)` (spread).
- **Closures**: anonymous functions capture surrounding variables **by reference**. This is how Go does callbacks, middleware, and event handlers.
- **`defer`** schedules a function call to run when the enclosing function returns — LIFO order for multiple defers. Arguments are evaluated **at defer time**, not at execution time. Defers run even during a panic — the standard mechanism for cleanup (`file.Close()`, `mu.Unlock()`, `resp.Body.Close()`).

## 5. Example 1 — Multiple returns and errors

```go
package main

import (
	"errors"
	"fmt"
)

func divide(a, b float64) (float64, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}

func main() {
	v, err := divide(10, 2)
	if err != nil {
		fmt.Println("error:", err)
		return
	}
	fmt.Println(v) // 5

	if _, err := divide(1, 0); err != nil {
		fmt.Println("caught:", err)
	}
}
```

## 6. Example 2 — Closures and defer

```go
package main

import "fmt"

// makeCounter returns a closure with its own private state.
func makeCounter() func() int {
	count := 0
	return func() int {
		count++
		return count
	}
}

func main() {
	c := makeCounter()
	fmt.Println(c(), c(), c()) // 1 2 3

	// defer: LIFO, args evaluated now
	defer fmt.Println("deferred with arg:", sum(1, 2)) // prints 3 inside
	fmt.Println("main body")

	// classic loop gotcha (fixed)
	for i := 1; i <= 3; i++ {
		i := i // capture a per-iteration copy
		defer func() { fmt.Print(i, " ") }() // prints 3 2 1 at exit
	}
}

func sum(a, b int) int { return a + b }
```

Note: since **Go 1.22**, loop variables are per-iteration, so the classic closure bug is largely fixed — but copying (`i := i`) is still common in older codebases.

## 7. Real-World Example

HTTP middleware is a function that takes and returns a handler — pure function composition (full version on Day 16/17):

```go
package main

import "fmt"

type handler func(string) string

func withLogging(h handler) handler {
	return func(name string) string {
		fmt.Println("[log] calling with", name)
		return h(name)
	}
}

func main() {
	greet := func(name string) string { return "Hello, " + name }
	logged := withLogging(greet)
	fmt.Println(logged("Ada"))
}
```

## 8. Common Mistakes

| Mistake | Fix |
|---------|-----|
| Ignoring a returned error | Handle it, or explicitly `_` it with a comment |
| Naked returns in long functions | Return values explicitly |
| Assuming defer runs immediately | It runs when the *enclosing function* returns, LIFO |
| Capturing loop variables expecting snapshots | Bind a copy (`v := v`) or pass as an arg |
| Recursion without a base case → stack overflow | Always define the terminating condition first |

## 9. Best Practices

- Return `(T, error)`, never `(T, error, somethingElse)` — the two-value shape is the ecosystem contract.
- Keep functions small and single-purpose; name them verb-ially (`parseConfig`, `sendEmail`).
- `defer` cleanup immediately after acquiring the resource.
- Pass interfaces/funcs for behavior instead of booleans like `useCache`.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Multiple returns | Native | Objects/records/tuples | Tuples | Arrays/objects |
| Exceptions | No (error values) | Yes | Yes | Yes |
| Closures | Yes | Lambdas (effectively final) | Yes | Yes |
| Default/named args | No | No | Yes | Simulated |
| finally/cleanup | `defer` | try/finally | with/finally | try/finally |

## 11. Practical Exercise

1. Write `min, max` returning both from one call over a slice.
2. Implement `fibonacci(n)` recursively, then iteratively.
3. Write `makeAdder(base int) func(int) int` closure.

## 12. Mini Project / Task

Build `calc.go`: a function `apply(a, b float64, op func(float64, float64) float64) float64`, plus add/sub/mul/div functions, and a CLI that picks the operation from `os.Args`.

## 13. Interview Questions

### Easy
- How does Go return multiple values?
- What does `defer` do?

### Medium
- What are the defer evaluation rules (arguments, order, panic behavior)?
- What is a closure? Show a counter example.

### Hard
- How can named returns + defer implement error wrapping?
- Explain how variadic `...T` relates to slices, and what `f(s...)` does.

## 14. Daily Practice Questions

### Easy
1. Write a function returning the area and perimeter of a rectangle.
2. Sum any number of int arguments (variadic).
3. Write a function with two named returns and an explicit return.
4. Defer a `Println` and predict the output order.
5. Write `isEven(n int) bool`.

### Medium
6. Write `swap(a, b int) (int, int)` and use it.
7. Implement a closure-based accumulator that keeps a running total.
8. Write `contains(s []string, target string) (int, bool)` returning index and found flag.
9. Defer three prints; predict LIFO order; verify.
10. Write `safeDiv` returning `(float64, error)` and use it in a loop over a divisor list.

### Hard
11. Implement memoized fibonacci using a closure-captured map.
12. Write a retry helper `retry(times int, f func() error) error` using `defer` to log attempts.
13. Implement function composition: `compose(f, g func(int) int) func(int) int`.
14. Write a variadic `maxInt(nums ...int) (int, error)` handling the empty case.
15. Use defer + named return to convert a panic into an error (`recover` — preview Day 11/26).

## 15. Solutions / Hints

- Q11: `cache := map[int]int{}` captured by the closure; check cache before recursion.
- Q13: `return func(x int) int { return f(g(x)) }`.
- Q15 hint: `defer func() { if r := recover(); r != nil { err = fmt.Errorf("recovered: %v", r) } }()`.

## 16. Day Summary

- Functions: `func name(params) (results)`; multiple returns are the error-handling foundation.
- Closures capture by reference; functions are values.
- `defer` = LIFO cleanup with arguments evaluated at defer time.

## 17. What To Revise

- `(T, error)` pattern; defer rules; closure counter.

## 18. What Comes Tomorrow

**Day 5 — Arrays & slices**: Go's most important data structure, the slice header, `append`, copying, and pitfalls of shared backing arrays.
