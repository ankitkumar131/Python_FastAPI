# Day 1 — Go Fundamentals

## Learning Objectives

- Understand what Go is, why it was created, and what problems it solves.
- Dissect a Go program line by line: `package`, `import`, `func main`.
- Run and build programs; understand compilation vs interpretation.

## Prerequisites

- Day 0 setup complete; `go version` works.

## 1. Concept Introduction

Go (Golang) is a **statically typed, compiled** language created at Google in 2007 (released 2009, 1.0 in 2012) by Robert Griesemer, Rob Pike, and Ken Thompson. Design goals:

- **Simple**: ~25 keywords (Java has ~50+, C++ has ~95).
- **Fast compilation**: huge codebases build in seconds.
- **Built-in concurrency**: goroutines and channels are language features.
- **Static single binaries**: easy to deploy — no JVM, no interpreter.
- **Garbage collected**: memory safety without manual `free()`.

## 2. Why This Concept Exists

Before Go, Google struggled with huge C++/Java/Python codebases: slow builds, complex dependency management, and difficulty writing concurrent servers. Go was designed for **large-scale server software** — that's why you see Go in Docker, Kubernetes, Terraform, and Prometheus.

## 3. Syntax: anatomy of a program

```go
package main

import "fmt"

func main() {
	fmt.Println("Hello, Go!")
}
```

Line by line:

| Line | Meaning |
|------|---------|
| `package main` | Every file declares its package. `main` is special: it produces an **executable**, not a library. |
| `import "fmt"` | Import the standard library's formatted-I/O package. |
| `func main()` | Entry point. The OS/runtime calls it. No arguments, no return value. |
| `fmt.Println(...)` | Package-qualified call: `package.Function`. |

Key rules:

- The opening brace `{` **must** be on the same line (compiler inserts semicolons automatically; a brace on the next line is a compile error).
- Unused imports or unused variables are **compile errors**.
- Only exported (capitalized) identifiers are visible outside a package.

## 4. Detailed Explanation: compiled, statically typed, with a runtime

**Compiled**: `go build` produces a native machine-code binary. There is no VM you ship — the binary contains the GC, scheduler, and your code. That's why Go apps are usually tiny Docker images.

**Statically typed**: every variable has a type fixed at compile time; type errors are caught before the program runs (unlike Python/JavaScript).

**Has a runtime, not a VM**: unlike Java (JVM + bytecode), Go compiles to native code but links in a small runtime managing goroutines, the garbage collector, and stack growth.

**One entry point**: exactly one `func main` in `package main`. Libraries never have `main`.

## 5. Example 1 — Printing and formatting

```go
package main

import "fmt"

func main() {
	fmt.Println("count:", 3, "ok")                   // adds spaces + newline
	fmt.Printf("hex=%x float=%.2f\n", 255, 3.14159) // C-style formatting
	fmt.Print("no newline")
	fmt.Println()
}
```

Output:

```text
count: 3 ok
hex=ff float=3.14
no newline
```

`Printf` uses **verbs**: `%s` string, `%d` int, `%v` any value, `%+v` struct with field names, `%T` type, `%t` bool.

## 6. Example 2 — Multiple functions

```go
package main

import "fmt"

func greet(name string) {
	fmt.Printf("Hello, %s!\n", name)
}

func main() {
	greet("Ada")
	greet("Grace")
}
```

Function declarations: `func name(param type) { ... }`. Parameter types come **after** names — this reads better left-to-right and is consistent everywhere in Go.

## 7. Real-World Example

Every Go CLI starts exactly like this — a minimal "echo" tool:

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	// os.Args[0] is the program name; the rest are user arguments.
	if len(os.Args) < 2 {
		fmt.Println("usage: echo2 <message>")
		os.Exit(1)
	}
	fmt.Println(os.Args[1])
}
```

## 8. Common Mistakes

| Mistake | Fix |
|---------|-----|
| `{` on its own line | Keep the brace on the declaration line (gofmt enforces this) |
| Unused import/variable | Delete it or use `_` (blank identifier) where allowed |
| Calling `Println` without importing `fmt` | Import what you use |
| Two `func main()` in one package | Only one entry point per program |

## 9. Best Practices

- Run `go fmt ./...` always; formatting is not a style debate in Go.
- Keep `main()` small — parse input, call other functions.
- Let the compiler help: "declared and not used" errors are design feedback.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Typing | Static, inferred | Static | Dynamic | Dynamic |
| Execution | Compiled to native | JVM bytecode | Interpreted | JIT/interpreted |
| Entry point | `func main` | `public static void main` | module top-level | script top-level |
| Unused import | Compile error | Warning | No error | No error |

## 11. Practical Exercise

1. Write a program printing three lines using `Println`, `Printf`, and `Print`.
2. Intentionally leave an unused import; read the compiler error; fix it.
3. Write `greet(name string)` that prints `Hello, <name>!` and call it with names from `os.Args`.

## 12. Mini Project / Task

Build `banner.go`: takes a name argument and prints a boxed banner:

```text
**************
*  Hi, Ada!  *
**************
```

Hint: use width verbs, e.g. `fmt.Printf("* %-*s *\n", width, text)`.

## 13. Interview Questions

### Easy
- What is the entry point of a Go program?
- Is Go interpreted or compiled?

### Medium
- Why does Go make unused imports a compile error?
- What is the difference between Go's runtime and the JVM?

### Hard
- Explain automatic semicolon insertion and why braces must stay on the same line.
- What does it mean that Go produces static binaries, and why does it matter for containers?

## 14. Daily Practice Questions

### Easy
1. Print your full name, age, and favorite number on one line.
2. Print the type of `42`, `3.14`, `"hi"` using `%T`.
3. Make a program with two functions; call both from `main`.
4. Print `true` and `false` using the `%t` verb.
5. Print a multi-line message using one `Println` with `\n`.

### Medium
6. Write a program that exits with status code 1 when no arguments are given.
7. Print all command-line arguments, one per line, numbered.
8. Use `Printf` to print a float to exactly 3 decimal places.
9. Print the string `100%` correctly (hint: `%%`).
10. Compare `fmt.Sprint` vs `fmt.Println`; when would you use `Sprint`?

### Hard
11. Build a program that formats a table of products (name, price) with aligned columns using `%-*s` and `%8.2f`.
12. Use `runtime.Version()` to print the Go version at runtime.
13. Write a program that panics with a custom message, then rewrite it to exit gracefully with an error message instead.
14. Explain what happens between `go build` and running the binary — lexing, parsing, type check, codegen, linking.
15. Print `runtime.GOMAXPROCS(0)`; explain what it means.

## 15. Solutions / Hints

- Q2: `fmt.Printf("%T %T %T\n", 42, 3.14, "hi")` → `int float64 string`.
- Q9: `fmt.Printf("100%%\n")`.
- Q11 hint: compute the max name length first, then use it as the width.
- Q13: `panic("boom")` vs `fmt.Fprintln(os.Stderr, "error:", msg); os.Exit(1)`.

## 16. Day Summary

- Go = simple, statically typed, compiled, concurrency-first.
- `package main` + `func main` = executable; everything else is a library.
- `fmt` verbs: `%v %T %d %s %t %x`.
- The compiler is strict — strictness is a feature.

## 17. What To Revise

- The anatomy table of a Go program; the verb list for `Printf`.

## 18. What Comes Tomorrow

**Day 2 — Variables, constants, and types**: declarations (`:=` vs `var`), Go's numeric types, strings, zero values, and how Go's type system differs from what you know.
