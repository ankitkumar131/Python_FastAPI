# Day 3 — Control Flow

## Learning Objectives

- Write `if` statements with init statements and understand Go's parenthesization rules.
- Master Go's **single loop keyword**: `for` in all its forms.
- Use `switch` (expression, no-condition, and type switches preview).
- Use `break`, `continue`, and labels.

## Prerequisites

- Days 1–2: variables, types, functions.

## 1. Concept Introduction

Go has remarkably few control-flow constructs on purpose:

- `if` / `else` / `else if`
- `for` (the **only** loop — no `while`, no `do-while`)
- `switch` / `case` / `default`
- `break`, `continue`, `goto` (rare), labels

Everything else — while-loops, until-loops, do-while — is expressed with `for`.

## 2. Why This Concept Exists

Fewer constructs = one obvious way to do things. Teams reading each other's code never debate loop styles. Also, Go removes classic C footguns: no `switch` fallthrough by default, no truthy integers, no parentheses around conditions (they're not needed, so they're forbidden by gofmt).

## 3. Syntax

```go
// if with optional init statement (scope limited to the if/else chain)
if x := compute(); x > 10 {
	fmt.Println("big")
} else {
	fmt.Println("small")
}

// for: three forms
for i := 0; i < 5; i++ { }   // C-style
for condition { }            // like "while condition"
for { }                      // infinite loop (use break)

// switch
switch day {
case "sat", "sun":
	fmt.Println("weekend")
default:
	fmt.Println("weekday")
}
```

## 4. Detailed Explanation

### if

- **No parentheses** around the condition; braces are **mandatory**.
- The init statement (`x := compute()`) is idiomatic Go: it scopes the variable to exactly where it's used and prevents leaking helper variables into outer scopes.

### for

The three-part form is `for init; condition; post { }`. The condition-only form is your `while`. The bare `for { }` is your infinite server loop, usually exited with `break` or `return`.

Range loops come on Day 5 (slices/maps), but here is the core shape: `for i, v := range collection { }`.

### switch

- **No fallthrough**: each `case` ends implicitly. `fallthrough` keyword exists but is rare.
- Multiple values per case: `case 1, 2, 3:`.
- A `switch` without an expression (`switch { case x > 10: ... }`) replaces long if/else chains — very idiomatic.
- Like `if`, `switch` supports an init statement: `switch n := f(); { ... }`.

## 5. Example 1 — FizzBuzz, idiomatic Go

```go
package main

import (
	"fmt"
	"strconv"
)

func main() {
	for i := 1; i <= 15; i++ {
		switch {
		case i%15 == 0:
			fmt.Println("FizzBuzz")
		case i%3 == 0:
			fmt.Println("Fizz")
		case i%5 == 0:
			fmt.Println("Buzz")
		default:
			fmt.Println(strconv.Itoa(i))
		}
	}
}
```

Note the **switch-true** pattern (`switch { case cond: }`) — cleaner than an if/else ladder.

## 6. Example 2 — if-init scoping and labels

```go
package main

import (
	"errors"
	"fmt"
)

func parse(s string) (int, error) {
	return strconvSimple(s)
}

// stand-in helper so the example compiles standalone
func strconvSimple(s string) (int, error) {
	n := 0
	for _, c := range []byte(s) {
		if c < '0' || c > '9' {
			return 0, errors.New("not a digit")
		}
		n = n*10 + int(c-'0')
	}
	return n, nil
}

func main() {
	if n, err := parse("42"); err != nil {
		fmt.Println("bad input:", err)
	} else {
		fmt.Println("parsed:", n)
	}
	// n and err are NOT visible here — exactly the intended scope.

outer:
	for i := 0; i < 3; i++ {
		for j := 0; j < 3; j++ {
			if i*j > 2 {
				break outer // exits BOTH loops
			}
			fmt.Println(i, j)
		}
	}
}
```

## 7. Real-World Example

A worker loop that runs until a shutdown channel closes (you'll see this in every real Go service — channels explained fully on Day 22):

```go
package main

import "fmt"

func main() {
	jobs := []int{1, 2, 3}
	done := true

	for {
		for _, j := range jobs {
			fmt.Println("processing", j)
		}
		if done {
			break
		}
	}
	fmt.Println("worker stopped cleanly")
}
```

## 8. Common Mistakes

| Mistake | Fix |
|---------|-----|
| Parentheses around `if` conditions | Remove them — gofmt does |
| Expecting `switch` fallthrough | Each case ends by itself; add `fallthrough` explicitly if ever needed |
| Declaring with `:=` in the loop body but meaning to update an outer var | Shadowing! Use `=` |
| `while` keyword | Doesn't exist — use `for cond { }` |
| Infinite `for { }` with no exit | Always pair with `break`, `return`, or cancellation |
| Trying to declare variables in a one-line `if` in Go like C99 | Use the if-init form |

## 9. Best Practices

- Prefer if-init/switch-init forms to keep helper variables narrowly scoped.
- Use `switch`-true instead of long `else if` chains.
- Early return instead of deep nesting: handle the error/edge case first, then continue.
- Avoid `goto` and `fallthrough` unless demonstrably clearer.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| While loop | `for cond {}` | `while` | `while` | `while` |
| Truthiness | None — condition must be `bool` | None | Yes | Yes |
| Switch fallthrough | Off by default | On without `break` | No switch pre-3.10 (match) | On without `break` |
| Parens on if | Forbidden by style | Required | Not used | Optional |
| Multi-value case | `case 1, 2:` | Separate cases | — | Separate cases |

## 11. Practical Exercise

1. Rewrite a `while` loop from another language as a Go `for`.
2. Print the multiplication table (1–10) using nested `for` with a labeled break at 5×5.
3. Classify a number: negative, zero, 1-digit, multi-digit — using `switch`-true.

## 12. Mini Project / Task

CLI `guess.go`: pick a secret number (`rand.Intn(100)`), read guesses from `os.Args` or stdin (`bufio`), loop until correct, print "higher"/"lower" hints. Uses loops, ifs, and early exits.

## 13. Interview Questions

### Easy
- How many loop keywords does Go have?
- Does Go's `switch` fall through?

### Medium
- What is the if-init statement and why is it useful?
- How do you break out of nested loops?

### Hard
- Why does Go forbid non-boolean conditions? What class of bugs does this prevent?
- Compare Go's `switch` with Python 3.10's `match` — structural vs value matching.

## 14. Daily Practice Questions

### Easy
1. Print even numbers 2–20 with a single `for`.
2. Sum 1–100 with a `for` loop.
3. Write an infinite loop that breaks after 3 iterations (counter).
4. Use `switch` on a string day name to print whether it's a weekend.
5. Use `continue` to skip multiples of 3 while printing 1–10.

### Medium
6. Implement FizzBuzz 1–100 with if/else, then rewrite with switch-true.
7. Reverse an integer (123 → 321) with a `for` loop.
8. Use if-init: `if v, ok := divide(10, 2); ok { ... }` — write `divide`.
9. Find the first prime > 100 using a labeled break.
10. Convert an if/else ladder grading system (90/80/70/60) into switch-true.

### Hard
11. Print Pascal's triangle with `n` rows using only `for` loops.
12. Implement bubble sort with early exit when no swaps occur.
13. Simulate a state machine (IDLE→RUNNING→PAUSED→STOPPED) with a `switch` inside an infinite loop.
14. Print a diamond pattern of stars for odd `n` using nested loops.
15. Implement binary search on a sorted slice using only `for` — no recursion.

## 15. Solutions / Hints

- Q7 hint: peel digits with `% 10` and `/ 10`; watch overflow.
- Q9 hint: label the outer loop; `break outer` when found.
- Q12 hint: track a `swapped bool`; `if !swapped { break }`.
- Q15 hint: classic `lo, hi, mid` loop with `for lo <= hi`.

## 16. Day Summary

- One loop: `for` (3 forms). One branch: `if` (+init). One multiway: `switch` (no fallthrough, switch-true idiom).
- Conditions must be booleans; braces mandatory; parens forbidden.
- Labels solve nested-loop exits.

## 17. What To Revise

- The three `for` forms; switch-true pattern; if-init scoping.

## 18. What Comes Tomorrow

**Day 4 — Functions**: multiple return values, named returns, variadics, closures, first-class functions, and `defer`.
