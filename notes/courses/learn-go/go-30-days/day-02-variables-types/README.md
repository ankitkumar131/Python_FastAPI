# Day 2 — Variables, Constants, and Types

## Learning Objectives

- Declare variables three ways: `var`, short declaration `:=`, and `var` blocks.
- Know Go's core types: `int`, `float64`, `bool`, `string`, and sized variants.
- Understand **zero values** and why Go has no uninitialized variables.
- Use constants, `iota`, and understand when conversion (`T(x)`) is required.

## Prerequisites

- Day 1: you can build and run a Go program.

## 1. Concept Introduction

Go is statically typed: every value has a type known at compile time. But Go reduces typing burden with **type inference** — the compiler often figures types out for you:

```go
var age int = 30   // explicit
var name = "Ada"   // inferred string
city := "Pune"     // short declaration, inferred (only inside functions)
```

## 2. Why This Concept Exists

Dynamic languages (Python/JS) catch type bugs at runtime — often in production. Full manual typing (Java pre-10, C) is verbose. Go's compromise: **static safety + inference**. Also, Go guarantees every variable starts at a known **zero value**, eliminating a whole class of "garbage value" bugs that plague C.

## 3. Syntax

```go
var x int              // declaration only, x == 0
var y = 10             // inferred int
z := 3.14              // inferred float64 (inside functions only)
var a, b string = "a", "b"
c, d := 1, 2

const Pi = 3.14159     // constant (compile-time)
const (
	StatusOK    = 0
	StatusError = 1
)
```

Rules:

- `:=` **declares and initializes**; it only works inside functions.
- `var` works everywhere, including package level.
- Re-declaring with `:=` fails unless **at least one** variable on the left is new: `a, e := 5, 6` is legal (e is new).

## 4. Detailed Explanation: the core type system

### Numbers

| Type | Range / notes |
|------|---------------|
| `int`, `uint` | Platform-dependent (64-bit on modern machines); default for integers |
| `int8/16/32/64` | Fixed-size signed integers |
| `uint8/16/32/64` | Unsigned; `byte` = `uint8`, `rune` = `int32` (a Unicode code point) |
| `float32`, `float64` | IEEE-754 floats; default is `float64` |
| `complex64/128` | Complex numbers (rare in practice) |

**Critical rule**: Go has **no implicit conversion**. `int` + `float64` is a compile error; you must convert explicitly:

```go
i := 10
f := 3.5
// sum := i + f        // compile error: mismatched types
sum := float64(i) + f  // OK: 13.5
```

### Strings and booleans

- `string`: immutable UTF-8 byte sequence. `len(s)` = **bytes**, not characters.
- `bool`: only `true`/`false`. There is **no truthiness** — `if 1` is a compile error (unlike Python/JS/C).

### Zero values

| Type | Zero value |
|------|-----------|
| `int`/floats | `0` |
| `bool` | `false` |
| `string` | `""` (empty string) |
| pointers, slices, maps, funcs, interfaces, channels | `nil` |

## 5. Example 1 — Declarations and zero values

```go
package main

import "fmt"

func main() {
	var i int      // 0
	var f float64  // 0
	var s string   // ""
	var b bool     // false
	fmt.Println(i, f, s == "", b) // 0 0 true false

	x, y := 10, "ten"
	fmt.Println(x, y)
}
```

## 6. Example 2 — Constants and iota

```go
package main

import "fmt"

type Weekday int

const (
	Sunday Weekday = iota // 0
	Monday                // 1 (iota increments automatically)
	Tuesday               // 2
	Wednesday
	Thursday
	Friday
	Saturday
)

func main() {
	fmt.Println(Monday, Saturday) // 1 6
	const KB = 1 << 10
	fmt.Println(KB) // 1024
}
```

`iota` is Go's idiom for enumerations. Each `const` line after the first repeats the previous expression with `iota` incremented.

## 7. Real-World Example

Config struct with typed constants used across a service:

```go
package main

import "fmt"

const (
	ReadTimeoutSeconds  = 30
	WriteTimeoutSeconds = 30
)

type Env string

const (
	Dev  Env = "dev"
	Prod Env = "prod"
)

func main() {
	env := Dev
	fmt.Printf("timeouts: %ds/%ds, env: %s\n",
		ReadTimeoutSeconds, WriteTimeoutSeconds, env)
}
```

Typing `env` as `Env` (not a raw string) means only valid environments compile — a constant-level type safety net.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Mixing `int` and `float64` without conversion | No implicit conversion in Go |
| `:=` at package level | Not allowed; use `var` |
| Assuming `len(s)` counts characters | It counts **bytes**; Unicode chars can be multi-byte |
| Using `:=` to reassign an existing var | Use plain `=` for assignment |
| Shadowing inside blocks | `x := 5` inside an `if` creates a **new** x, hiding the outer one |
| Untyped constant overflow | `const big = 1 << 40; var i int8 = big` — compile error |

## 9. Best Practices

- Prefer `:=` inside functions; use `var` for package-level and when you want the zero value.
- Group related constants with `iota` instead of scattered magic numbers.
- Keep types minimal: use `int` unless a protocol/format demands a fixed size.
- Watch for shadowing; `go vet -shadow` (via `golang.org/x/tools/go/analysis/passes/shadow/cmd/shadow`) can help.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Declaration | `x := 10` / `var x int` | `int x = 10;` | `x = 10` | `let x = 10` |
| Implicit conversion | Never | Widening only | Yes | Yes (coercion) |
| Default value | Zero value guaranteed | Fields only, locals must init | Unbound/None | `undefined` |
| Enum | `iota` constants | `enum` keyword | Enum class / constants | Frozen objects |
| Integer overflow | Wraps for fixed sizes; `int` is platform-sized | Defined wrap | Arbitrary precision | Float64 for all numbers |

## 11. Practical Exercise

1. Declare one variable of each core type using both `var` and `:=`; print all with `%v`.
2. Convert a `string` to `float64` with `strconv.ParseFloat` and print the error when input is bad.
3. Build a `Level` type with `iota` constants `Debug, Info, Warn, Error`; print `Info`.

## 12. Mini Project / Task

Write `units.go`: define `const` values for MB, GB, TB using bit shifts, take a byte count from `os.Args`, convert with `strconv.ParseInt`, and print the value in GB with two decimals.

## 13. Interview Questions

### Easy
- What are Go's zero values?
- Difference between `var x = 10` and `x := 10`?

### Medium
- Why doesn't Go allow implicit type conversion?
- What is `iota` and how does it work?

### Hard
- Explain untyped constants and how they can be any size until assigned.
- What is variable shadowing and how can it cause bugs in Go?

## 14. Daily Practice Questions

### Easy
1. Swap two integers without a temp variable (`a, b = b, a`).
2. Print the zero value of `int`, `string`, `bool` without initializing them.
3. Convert `"42"` to an int with `strconv.Atoi`.
4. Declare a `byte` and a `rune`; print their types.
5. Compute `7 / 2` and `7.0 / 2`; explain the results in a comment.

### Medium
6. Write a function that converts Celsius to Fahrenheit using `float64` throughout.
7. Parse `os.Args[1]` as an int and print its square; handle the parse error.
8. Build an `iota` set of HTTP-like status constants (100..) with a `String()` mapping via a slice.
9. Demonstrate shadowing: an outer and inner `x`; print both.
10. Show that `const` arithmetic (like `1 << 20`) happens at compile time by using it to size an array.

### Hard
11. Implement safe integer addition detecting overflow using `math.MaxInt64` checks.
12. Write a program that prints the byte length and rune count of `"héllo wörld"` and explains the difference.
13. Demonstrate that `int8(200)` wraps; predict the value, then verify.
14. Use `unsafe.Sizeof` to compare sizes of `int8/int32/int64/float64` on your machine.
15. Write a parser for a color hex string `#RRGGBB` into three `uint8` values using `strconv.ParseUint(s, 16, 8)`.

## 15. Solutions / Hints

- Q1: `a, b = b, a` — tuple assignment, a favorite Go feature.
- Q5: `7 / 2 == 3` (integer division); `7.0 / 2 == 3.5`.
- Q12 hint: `len(s)` vs `utf8.RuneCountInString(s)` (or `len([]rune(s))`).
- Q13: `int8(200)` wraps to `-56` (200 - 256).
- Q15 hint: trim `#`, then `s[0:2], s[2:4], s[4:6]` → three `ParseUint` calls.

## 16. Day Summary

- Three declaration styles: `var`, `:=`, `const`.
- Zero values make all variables safe from day one.
- No implicit conversion — explicit `T(x)` always.
- `iota` is the Go enum; `int` is the everyday integer.

## 17. What To Revise

- Zero-value table; the `int8(200)` wrap example; `iota` pattern.

## 18. What Comes Tomorrow

**Day 3 — Control flow**: `if` with init statements, Go's `for` (the only loop), `switch` without fallthrough, and labeled breaks.
