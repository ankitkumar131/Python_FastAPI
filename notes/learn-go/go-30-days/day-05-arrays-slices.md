# Day 5 — Arrays and Slices

## Learning Objectives

- Understand fixed-size arrays vs dynamic slices.
- Master the slice header (pointer, length, capacity) and how `append` works.
- Slice, copy, iterate, and pass slices safely.
- Avoid the classic shared-backing-array bugs.

## Prerequisites

- Days 1–4 (especially functions and ranges).

## 1. Concept Introduction

- **Array**: fixed-size, value type: `[3]int{1, 2, 3}`. Size is part of the type — `[3]int` and `[4]int` are different types. Rarely used directly.
- **Slice**: a dynamic view over an array: `[]int{1, 2, 3}`. This is what Go programs use 95% of the time.

## 2. Why This Concept Exists

C arrays carry no length information (the source of countless buffer overflows). Java/Python lists are heap objects with overhead and indirection. Go's slice is a small **struct of three words** — pointer, length, capacity — giving you C-like memory efficiency plus bounds checking and easy growth. Understanding it is *the* key to writing correct, fast Go.

## 3. Syntax

```go
a := [3]int{1, 2, 3}       // array (size fixed)
s := []int{1, 2, 3}        // slice literal
s := make([]int, 3)        // len 3, cap 3, all zeros
s := make([]int, 0, 10)    // len 0, cap 10 — pre-allocated

s = append(s, 4)           // grow (may reallocate)
sub := s[1:3]              // slicing: [low:high) — half-open
n := len(s)                // elements visible
c := cap(s)                // room before reallocation
```

## 4. Detailed Explanation: the slice header

A slice is:

```go
type slice struct {
	ptr *element // points into a backing array
	len int      // number of visible elements
	cap int      // number of elements before reallocating
}
```

Consequences you must internalize:

1. **Slicing shares memory.** `sub := s[1:3]` does **not** copy; `sub[0]` and `s[1]` are the same memory.
2. **`append` may or may not reallocate.** If `cap` allows, it writes into the *same* backing array — and any other slice sharing it sees the change. If capacity is exceeded, Go allocates a new, larger array and copies.
3. **Passing slices to functions is cheap** (three words), but mutations are visible to the caller — slices are reference-like.
4. **Growth**: doubling below 1024 elements, ~1.25× beyond (implementation detail; never rely on exact capacity).

## 5. Example 1 — append and aliasing

```go
package main

import "fmt"

func main() {
	s := make([]int, 3, 5) // [0 0 0], cap 5
	s[0], s[1], s[2] = 1, 2, 3

	sub := s[1:3]      // [2 3] — shares backing array
	sub[0] = 99        // modifies s too!
	fmt.Println(s, sub) // [1 99 3] [99 3]

	t := append(s[:2], 7) // may overwrite s[2]!
	fmt.Println(s, t)     // [1 99 7] [1 99 7] — gotcha demonstrated

	// Safe: force a copy
	u := append([]int(nil), s[:2]...)
	u[0] = 100
	fmt.Println(s, u) // s unchanged
}
```

## 6. Example 2 — copy, filtering, iterating

```go
package main

import "fmt"

func filterEven(nums []int) []int {
	out := make([]int, 0, len(nums)) // pre-allocate
	for _, v := range nums {
		if v%2 == 0 {
			out = append(out, v)
		}
	}
	return out
}

func main() {
	nums := []int{1, 2, 3, 4, 5, 6}
	evens := filterEven(nums)
	fmt.Println(evens) // [2 4 6]

	// full slice copy
	dst := make([]int, len(nums))
	copy(dst, nums)

	// iterate with index
	for i, v := range nums {
		fmt.Printf("nums[%d]=%d ", i, v)
	}
	fmt.Println()

	// remove element at index 2 (order-preserving)
	i := 2
	nums = append(nums[:i], nums[i+1:]...)
	fmt.Println(nums) // [1 2 4 5 6]
}
```

## 7. Real-World Example

Reading a file in chunks — the standard "buffer" pattern:

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	buf := make([]byte, 64) // reusable buffer
	f, err := os.Open("data.txt")
	if err != nil {
		fmt.Println("open:", err)
		return
	}
	defer f.Close()
	for {
		n, err := f.Read(buf)
		if n > 0 {
			fmt.Print(string(buf[:n])) // only the filled part!
		}
		if err != nil {
			break // EOF or real error (checked properly on Day 11)
		}
	}
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Thinking slicing copies | It doesn't — mutating a sub-slice mutates the original |
| `append` result ignored | `append` may return a **new** slice; always reassign: `s = append(s, x)` |
| Slicing with `[:high]` beyond len but within cap | Exposes hidden elements / causes overwrite surprises |
| Comparing slices with `==` | Only allowed against `nil`; use `slices.Equal` |
| Growing in a hot loop with no pre-allocation | Use `make([]T, 0, knownSize)` |
| `for i := range` then using `v` expecting copy semantics | `v` IS a copy, but `i` may surprise in closures pre-1.22 |

## 9. Best Practices

- Pre-allocate with capacity when the size is known.
- Use the stdlib `slices` package (Go 1.21+): `slices.Contains`, `slices.Sort`, `slices.Equal`, `slices.Clone`.
- When returning a sub-slice of a huge slice, `slices.Clone` if the huge array should be garbage collected.
- Delete-while-iterating carefully — build a new slice instead when unsure.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Fixed array | `[3]int` (value type) | `int[3]` | — | — |
| Dynamic list | slice | `ArrayList` | `list` | `Array` |
| Slicing shares memory | Yes (must copy) | No (subList is a view!) | View (`a[1:3]` is a view) | `slice()` copies |
| Bounds check | Runtime panic | Exception | Exception | `undefined` access |

## 11. Practical Exercise

1. Create a slice of 5 ints, append 3 more, print len/cap after each append.
2. Demonstrate slice aliasing by mutating through a sub-slice.
3. Reverse a slice in place.

## 12. Mini Project / Task

`topk.go`: read numbers from `os.Args`, keep the top 3 largest using only slices (no sorting libs), print them. Practice pre-allocation and appends.

## 13. Interview Questions

### Easy
- Array vs slice?
- What are `len` and `cap`?

### Medium
- Explain the slice header.
- When does `append` allocate a new backing array?

### Hard
- Demonstrate a bug caused by `append` sharing a backing array; fix it.
- Why are slices passed by "reference-like" semantics although Go is pass-by-value?

## 14. Daily Practice Questions

### Easy
1. Make a slice with `make([]int, 5)`; print it.
2. Append 10 numbers to an empty slice; print final len/cap.
3. Print a slice's middle three elements with slicing.
4. Copy one slice into another with `copy`.
5. Check if a slice is empty using `len`.

### Medium
6. Remove all zeros from a slice in one pass.
7. Merge two sorted slices into one sorted slice.
8. Compute the sum and average of a slice.
9. Implement `indexOf` without `slices.Index`.
10. Rotate a slice left by k positions.

### Hard
11. Implement insertion sort in place on a slice.
12. Write `chunk(s []int, size int) [][]int` splitting a slice into chunks.
13. Demonstrate and fix the memory-retention problem of keeping a small sub-slice of a huge slice.
14. Implement `dedupAdjacent` (remove consecutive duplicates) in place.
15. Given `s := make([]int, 0, 10)`, predict len/cap after 5 appends, then 7 appends. Verify and explain.

## 15. Solutions / Hints

- Q3: `s[1:4]` for a 5-element slice.
- Q10 hint: `append(append(s[k:], s[:k]...))` — mind aliasing.
- Q12: `s[i:min(i+size, len(s))]` per chunk.
- Q13: `sub := slices.Clone(big[0:5])`.

## 16. Day Summary

- Slices = pointer + len + cap over a backing array.
- `append` reassigns; slicing shares memory; `copy`/`slices.Clone` detach.
- Pre-allocate; prefer `slices` stdlib helpers.

## 17. What To Revise

- Example 1's aliasing output — be able to reproduce it on paper.

## 18. What Comes Tomorrow

**Day 6 — Maps & strings**: hash maps, the comma-ok idiom, string iteration, runes vs bytes, and `strings`/`strconv` packages.
