# Day 11 — Error Handling

## Learning Objectives

- Create and return errors; understand the `error` interface.
- Wrap errors with `%w` and inspect them with `errors.Is` and `errors.As`.
- Define custom error types with rich context.
- Know when `panic` is appropriate (rarely) and how `recover` works.

## Prerequisites

- Day 10: interfaces (errors are just an interface).

## 1. Concept Introduction

Errors are **values**. Functions return them as the last result:

```go
result, err := doWork()
if err != nil {
	return err // or handle
}
// use result
```

`error` is a tiny interface: `type error interface { Error() string }`. No exceptions in normal flow — you see exactly where failures are handled.

## 2. Why This Concept Exists

Exceptions hide control flow: any line may throw, and unwinding jumps are invisible. Go's designers chose visible, explicit error returns: you can read a function top-to-bottom and see every failure path. The cost is verbosity (`if err != nil` everywhere); the benefit is reliability and locally-verifiable code — a big reason Go services have predictable failure behavior.

## 3. Syntax

```go
errors.New("bad input")            // static error
fmt.Errorf("user %d: %w", id, err) // wrap, preserving the chain
errors.Is(err, ErrNotFound)        // sentinel comparison (unwraps chain)
errors.As(err, &myErr)             // extract a concrete type from the chain
panic("unrecoverable")             // crash path — not for normal errors
recover()                          // inside a deferred func: stop a panic
```

## 4. Detailed Explanation

### Three error patterns

1. **Sentinel errors** — predefined package-level values: `var ErrNotFound = errors.New("not found")`. Callers check with `errors.Is`.
2. **Custom error types** — a struct implementing `Error() string`, carrying context fields. Callers extract with `errors.As`.
3. **Opaque wrapped errors** — `fmt.Errorf("...: %w", err)` adds context while keeping the cause checkable.

**Wrapping rule**: add context at each layer ("what were you doing") with `%w`; check causes at the boundary with `Is`/`As`. Never wrap with `%v` if callers need to inspect (that erases the chain).

**panic vs error**: panics are for programmer bugs (impossible states) and init-time failures; not for missing files, bad input, or network issues. Libraries should convert panics to errors where possible.

**recover**: only effective inside a deferred function during a panic; returns the panic value and stops unwinding. Used by HTTP servers (per-request panic recovery) and goroutine supervisors.

## 5. Example 1 — Sentinels, wrapping, errors.Is

```go
package main

import (
	"errors"
	"fmt"
	"os"
)

var ErrUserNotFound = errors.New("user not found")

func findUser(id int) (string, error) {
	if id != 42 {
		return "", fmt.Errorf("findUser(id=%d): %w", id, ErrUserNotFound)
	}
	return "Ada", nil
}

func main() {
	_, err := findUser(7)
	if errors.Is(err, ErrUserNotFound) {
		fmt.Println("handled: 404 for user") // true despite wrapping
	}
	fmt.Println(err) // findUser(id=7): user not found

	// errors.Is also matches stdlib sentinels:
	_, openErr := os.Open("definitely-missing.txt")
	fmt.Println(errors.Is(openErr, os.ErrNotExist)) // true
}
```

## 6. Example 2 — Custom error types with errors.As

```go
package main

import (
	"errors"
	"fmt"
)

type ValidationError struct {
	Field  string
	Reason string
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("invalid %s: %s", e.Field, e.Reason)
}

func register(name, email string) error {
	if name == "" {
		return &ValidationError{Field: "name", Reason: "empty"}
	}
	if !contains(email, "@") {
		return &ValidationError{Field: "email", Reason: "missing @"}
	}
	return nil
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (func() bool {
		for i := 0; i+len(sub) <= len(s); i++ {
			if s[i:i+len(sub)] == sub {
				return true
			}
		}
		return false
	})()
}

func main() {
	err := register("", "x")
	var ve *ValidationError
	if errors.As(err, &ve) { // extracts concrete type from chain
		fmt.Printf("field=%s reason=%s\n", ve.Field, ve.Reason)
	}
}
```

(In real code use `strings.Contains(email, "@")`.)

## 7. Real-World Example

Layered service with wrap-and-inspect — the production pattern:

```go
package main

import (
	"errors"
	"fmt"
)

var ErrRateLimited = errors.New("rate limited")

func callAPI() error { return fmt.Errorf("api call: %w", ErrRateLimited) }

func service() error {
	if err := callAPI(); err != nil {
		return fmt.Errorf("fetching dashboard: %w", err)
	}
	return nil
}

func main() {
	err := service()
	// Boundary logic: react to *cause*, log the *chain*.
	switch {
	case errors.Is(err, ErrRateLimited):
		fmt.Println("retry later (429)")
	default:
		fmt.Println("unexpected:", err)
	}
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Ignoring returned errors | `_` without comment hides failures; vet/lint flags it |
| Wrapping with `%v` | Breaks the chain — `errors.Is/As` stop working |
| `err == ErrX` instead of `errors.Is` | Misses wrapped causes |
| Panic for expected failures | Reserve for bugs; use errors otherwise |
| Checking `err != nil` then still using the value | Always return after handling |
| Logging AND returning the same error | Duplicates in logs; do one or the other per layer |

## 9. Best Practices

- Return `error` as the last value; return zero values with the error.
- Add context when wrapping: `fmt.Errorf("loading config %s: %w", path, err)`.
- Handle each error exactly once (handle OR propagate, not both).
- Sentinel errors: name `ErrXxx`; custom types: name `XxxError`.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Mechanism | error values | try/catch exceptions | try/except | try/catch |
| Checked visibility | Explicit returns | Checked exceptions | None | None |
| Wrapping | `%w` + Is/As | cause in Exception | `raise ... from` | `cause` option |
| Stack traces | Manual (debug.Stack) | Automatic | Automatic | Automatic |

## 11. Practical Exercise

1. Write `parsePort(s string) (int, error)` handling non-numeric and out-of-range.
2. Define `ErrTimeout` sentinel; wrap it twice; check with `errors.Is`.
3. Create `HTTPError{Code int, Msg string}` implementing `error`; extract with `errors.As`.

## 12. Mini Project / Task

`validator.go`: `ValidateUser(name, email, age)` returning wrapped, typed errors per field. Main function prints a field-specific message by switching on `errors.As`.

## 13. Interview Questions

### Easy
- What is the `error` interface?
- `errors.New` vs `fmt.Errorf`?

### Medium
- `%w` vs `%v` in `fmt.Errorf`?
- When do you use `errors.Is` vs `errors.As`?

### Hard
- When is `panic/recover` justified? How does `net/http` use recover?
- Design an error strategy for a multi-layer service: sentinels vs types vs wrapping — trade-offs?

## 14. Daily Practice Questions

### Easy
1. Return an error from a divide function on zero.
2. Create a sentinel and compare with `==` and `errors.Is`.
3. Wrap an error with a filename context.
4. Print an error and its `Error()` string.
5. Use `errors.Is` with `os.ErrNotExist`.

### Medium
6. Implement `ValidationError` with multiple fields and extract it.
7. Write a function that retries 3 times, returning the last wrapped error.
8. Convert a `panic` into an `error` using `recover` in a deferred func.
9. Chain three function calls, wrapping at each layer; print the chain.
10. Join multiple errors with `errors.Join` and inspect with `errors.Is`.

### Hard
11. Implement an error type supporting `errors.Is` via an `Is(target error) bool` method (e.g., matching by HTTP status class).
12. Build a small error-aggregation middleware that collects errors from multiple goroutines (sync + errors.Join).
13. Explain and demonstrate why wrapping erases or preserves `errors.As` capability depending on `%w`.
14. Implement a transaction-style helper: run steps, roll back completed ones on error, return joined error.
15. Write a fuzz-friendly parser whose errors include the exact failing position.

## 15. Solutions / Hints

- Q8 hint: `defer func() { if r := recover(); r != nil { err = fmt.Errorf("panic: %v", r) } }()` with named return `err`.
- Q11 hint: `func (e *HTTPError) Is(target error) bool { h, ok := target.(*HTTPError); return ok && h.Code/100 == e.Code/100 }`.
- Q14 hint: slice of cleanup funcs; run in reverse on failure; `errors.Join(collected...)`.

## 16. Day Summary

- Errors are values returned explicitly; `error` = one-method interface.
- Wrap with `%w`; inspect with `errors.Is` (sentinels) / `errors.As` (types).
- Panic = bugs only; recover = defensive boundary.

## 17. What To Revise

- The three error patterns; wrap-once-handle-once rule.

## 18. What Comes Tomorrow

**Day 12 — Packages & modules**: organizing real projects, `go.mod`, import paths, visibility, internal packages, and versioning.
