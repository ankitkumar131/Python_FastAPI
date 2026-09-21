# Day 8 — Pointers

## Learning Objectives

- Understand `&` (address-of) and `*` (dereference) in Go.
- Know why Go has pointers but no pointer arithmetic.
- Decide between value and pointer receivers/parameters.
- Handle `nil` pointers safely; understand the escape analysis basics.

## Prerequisites

- Day 7: structs.

## 1. Concept Introduction

A pointer holds the **memory address** of a value:

```go
x := 10
p := &x   // p is *int, pointing to x
*p = 20   // dereference: sets x to 20
```

Go has pointers (so functions can mutate caller data, and large structs needn't be copied) but **no pointer arithmetic** and a garbage collector — most of C's pointer danger is designed out.

## 2. Why This Concept Exists

Day 7 showed structs copy by value. That's great for safety, but two problems need pointers: (1) mutation — a function can't change the caller's variable unless given its address; (2) performance — copying a 2 KB struct on every call is wasteful; passing 8 bytes (an address) is not. Go's compromise: pointers exist and are explicit, but there is no arithmetic, no manual free, and nil is checked at runtime.

## 3. Syntax

```go
var p *int            // nil pointer
x := 5
p = &x                // & takes the address

fmt.Println(*p)       // * dereferences: 5
*p = 7                // writes through the pointer

type User struct{ Name string }
u := &User{Name: "Ada"}  // struct literal address; Go auto-derefs:
u.Name = "Grace"         // same as (*u).Name

new(int)               // allocates zeroed int, returns *int (rarely needed)
```

## 4. Detailed Explanation

- **Value vs pointer semantics**: small, immutable-ish values (ints, strings, time.Time) → copy. Large structs or mutation-required values → pointer. Rule of thumb used across the stdlib.
- **No arithmetic**: `p++` or `p+1` on pointers is a compile error. This kills whole bug classes (buffer overruns, wild pointers).
- **Escape analysis**: the compiler decides heap vs stack. If a pointer escapes the function (returned, stored in a global), the value moves to the heap and the GC manages it. You usually don't think about this — but it's why returning `&local` is safe in Go (unlike C).
- **`nil` pointers**: calling a method on a nil pointer receiver can be legal (methods can check), but dereferencing nil panics. Always check before dereferencing data from external sources (JSON, DB).

## 5. Example 1 — Mutation through pointers

```go
package main

import "fmt"

func bump(p *int) {
	*p++ // modifies caller's variable
}

func setName(u *User, name string) {
	u.Name = name // auto-deref
}

type User struct{ Name string }

func main() {
	n := 10
	bump(&n)
	fmt.Println(n) // 11

	u := &User{Name: "Ada"}
	setName(u, "Grace")
	fmt.Println(u.Name) // Grace

	// Without pointer: no effect
	setNameValue(*u, "Bob")
	fmt.Println(u.Name) // still Grace

	// nil pointer panic demo (guarded)
	var p *User
	if p != nil {
		fmt.Println(p.Name)
	} else {
		fmt.Println("p is nil — safe")
	}
}

func setNameValue(u User, name string) { u.Name = name }
```

## 6. Example 2 — Linked list with pointers

```go
package main

import "fmt"

type Node struct {
	Val  int
	Next *Node // pointer = the link itself
}

func push(head *Node, v int) *Node {
	return &Node{Val: v, Next: head} // prepend; returns new head
}

func main() {
	var head *Node // nil initially
	for i := 1; i <= 3; i++ {
		head = push(head, i*10)
	}
	for n := head; n != nil; n = n.Next {
		fmt.Print(n.Val, " ") // 30 20 10
	}
	fmt.Println()
}
```

Note: `var head *Node` is nil, and `push` handles it naturally — pointers enable recursive data structures.

## 7. Real-World Example

JSON decoding **requires** pointers (both for addressability and for optional/absent fields):

```go
package main

import (
	"encoding/json"
	"fmt"
)

type UpdateRequest struct {
	Name  *string `json:"name"`  // nil = not provided
	Email *string `json:"email"`
}

func main() {
	var req UpdateRequest
	json.Unmarshal([]byte(`{"email":"new@x.com"}`), &req)

	if req.Name != nil { // PATCH semantics: update only provided fields
		fmt.Println("update name to", *req.Name)
	}
	if req.Email != nil {
		fmt.Println("update email to", *req.Email)
	}
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Dereferencing nil | Panic; check `if p != nil` for external data |
| Returning a pointer to a loop variable expecting aliasing | Pre-1.22 aliasing bug; now per-iteration, but know the history |
| Using pointers for everything | Copies of small structs are cheap and safer |
| Mixing value/pointer receivers on one type | Pick one per type (details Day 9) |
| Thinking `&x` allocates | It doesn't; `new`/`make` allocate |

## 9. Best Practices

- Default to value receivers/params; switch to pointers for mutation or big structs.
- Accept pointers from external input (JSON) as *optional* fields.
- Let escape analysis work — returning `&local` is fine in Go.
- Run `go vet`; it catches several pointer misuse patterns.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Pointers | Explicit (`*T`) | Hidden (references) | Hidden (references) | Hidden (references) |
| Pointer arithmetic | None | — | — | — |
| Null safety | `nil`, runtime panic | NPE | AttributeError | TypeError |
| Primitives vs objects | All values; pointer is a choice | Primitives vs objects | Everything is an object | Primitives vs objects |

## 11. Practical Exercise

1. Write `swap(a, b *int)` that mutates through pointers.
2. Show that a value parameter cannot mutate the caller's struct.
3. Build a 3-node linked list and count its length iteratively.

## 12. Mini Project / Task

`bank.go`: `type Account struct{ Balance float64 }` with `Deposit(a *Account, amt float64) error` and `Withdraw` (error when insufficient). Keep balances in a `map[string]*Account` — notice **why** the map needs pointers (map values aren't addressable!).

## 13. Interview Questions

### Easy
- What do `&` and `*` do?
- What is a nil pointer?

### Medium
- When should a function take a pointer vs a value?
- Why is returning a pointer to a local variable safe in Go?

### Hard
- Explain escape analysis and its performance implications.
- Why aren't map values addressable, and how do pointers solve it?

## 14. Daily Practice Questions

### Easy
1. Declare an `int` and a pointer to it; modify via the pointer.
2. Print a pointer's value and its dereferenced value.
3. Create a struct with `&Struct{...}` and mutate a field.
4. Safely dereference a possibly-nil pointer.
5. Use `new(map[int]int)` — then explain why it's wrong and what to use instead (`make`).

### Medium
6. Implement `increment(p *int)`; use it in a loop.
7. Store structs in a map and mutate a field — explain the compile error without pointers.
8. Write a function returning `*string` that returns nil for empty input.
9. Reverse a linked list iteratively (LeetCode 206).
10. Demonstrate aliasing: two pointers to the same struct.

### Hard
11. Implement a binary tree insert + in-order print using pointer nodes.
12. Detect a cycle in a linked list (Floyd's algorithm).
13. Explain and demonstrate with `-gcflags="-m"` which variables escape to the heap.
14. Implement `optional` semantics: `Config` with pointer fields and an `Apply(defaults Config)` merge.
15. Build a generic doubly-linked list where removal is O(1) using pointers both ways.

## 15. Solutions / Hints

- Q5: `new(map[int]int)` gives a nil map pointer; dereferencing to write panics. Use `make(map[int]int)`.
- Q7: `m["k"].Field = x` fails — map values aren't addressable; store `*T` in the map.
- Q13: `go build -gcflags="-m" .` prints `escapes to heap` / `does not escape`.

## 16. Day Summary

- `&` takes an address, `*` dereferences; nil-check before deref.
- Pointers for mutation and big structs; values for small data.
- No arithmetic, GC-managed — C's power without C's danger.

## 17. What To Revise

- Value vs pointer decision table; the map-values-aren't-addressable gotcha.

## 18. What Comes Tomorrow

**Day 9 — Methods**: methods with value and pointer receivers, method sets, and how receivers interact with interfaces.
