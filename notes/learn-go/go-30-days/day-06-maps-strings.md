# Day 6 — Maps and Strings

## Learning Objectives

- Create, read, update, and delete in Go maps; master the comma-ok idiom.
- Understand map semantics: no ordering, not safe for concurrent writes, keys need comparability.
- Iterate strings as bytes vs runes; use the `strings` and `strconv` packages.

## Prerequisites

- Day 5: slices and range loops.

## 1. Concept Introduction

A **map** is Go's built-in hash table: `map[K]V` where `K` must be comparable (`==` works — so no slices/maps/functions as keys) and `V` is anything.

```go
ages := map[string]int{"ada": 36, "grace": 45}
counts := make(map[string]int) // empty, ready for writes
```

## 2. Why This Concept Exists

Almost every program needs key→value lookups: user sessions, config, indexes, word counts. Go built the hash map into the language so everyone uses one well-tested implementation instead of importing different ones. Its deliberate quirks — **random iteration order** and the **comma-ok** read — are design choices to prevent depending on order and to make "missing key" explicit.

## 3. Syntax

```go
m := map[string]int{"a": 1}   // literal
m := make(map[string]int)     // empty (writable)

v := m["a"]        // read (zero value 0 if missing!)
v, ok := m["a"]    // comma-ok: ok=false if missing
m["b"] = 2         // write
delete(m, "a")     // delete (safe even if absent)

len(m)             // number of entries
for k, v := range m { } // order is RANDOM
```

**Important**: a nil map (declared `var m map[string]int` without `make`) can be **read** from but not **written** — writing panics.

## 4. Detailed Explanation

- **Zero-value reads**: `m["missing"]` returns the zero value of V (`0`, `""`, `false`), never an error. Use comma-ok when absence matters.
- **Random iteration order**: intentional; Go even randomizes it to catch code that secretly depends on order. Sort keys when order matters.
- **Concurrency**: maps are **not** thread-safe. Concurrent writes cause a runtime crash (not a data race you can ignore). Use `sync.Mutex` (Day 23) or `sync.Map`.
- **Strings** are immutable UTF-8 byte sequences. `range` over a string yields **runes** (Unicode code points) with byte offsets; `s[i]` yields a single **byte**. This distinction is a favorite interview topic.
- `[]byte(s)` converts string↔bytes (copies); `[]rune(s)` decodes to code points.

## 5. Example 1 — Word frequency with comma-ok

```go
package main

import (
	"fmt"
	"sort"
	"strings"
)

func main() {
	text := "the quick brown fox the lazy dog the fox"
	counts := map[string]int{}

	for _, w := range strings.Fields(text) {
		counts[w]++ // zero-value read makes this safe and idiomatic
	}

	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, k := range keys {
		fmt.Printf("%-6s %d\n", k, counts[k])
	}
}
```

Note `counts[w]++` works even for a first-time word because a missing read returns 0.

## 6. Example 2 — Strings: bytes vs runes

```go
package main

import (
	"fmt"
	"strings"
	"unicode/utf8"
)

func main() {
	s := "héllo"

	fmt.Println(len(s))            // 6 bytes (é is 2 bytes)
	fmt.Println(utf8.RuneCountInString(s)) // 5 characters

	for i, b := range []byte(s) {
		fmt.Printf("byte %d: %x\n", i, b)
	}
	for i, r := range s { // i = BYTE offset, r = rune
		fmt.Printf("rune at byte %d: %c\n", i, r)
	}

	// common operations
	fmt.Println(strings.ToUpper(s))
	fmt.Println(strings.Repeat("ab", 3))
	fmt.Println(strings.Contains(s, "él"))
	parts := strings.Split("a,b,c", ",")
	fmt.Println(strings.Join(parts, "|"))
}
```

## 7. Real-World Example

Grouping API errors by status code — a map of slices, a ubiquitous production pattern:

```go
package main

import "fmt"

func groupByStatus(codes []int) map[int][]int {
	grouped := map[int][]int{}
	for _, c := range codes {
		grouped[c/100*100] = append(grouped[c/100*100], c)
	}
	return grouped
}

func main() {
	fmt.Println(groupByStatus([]int{200, 404, 201, 500, 403}))
	// map[200:[200 201] 400:[404 403] 500:[500]]
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Writing to a nil map | `var m map[string]int; m["x"]=1` → panic; always `make` it |
| Relying on map iteration order | It's randomized; sort keys first |
| Using maps concurrently | Needs mutex or `sync.Map` |
| `len(string)` for character count | Counts bytes; use `utf8.RuneCountInString` |
| Mutating a map during range | Deleting during range is OK; **inserting** new keys during range is unspecified |
| String concatenation in loops | O(n²); use `strings.Builder` |

## 9. Best Practices

- Use the zero-value-read to simplify counters; use comma-ok when absence is meaningful.
- For ordered output: collect keys → `sort.Strings(keys)` → iterate.
- Build strings with `strings.Builder` in loops.
- Prefer `slices.Contains`/`maps.Keys` (Go 1.21+) over hand-rolled loops.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Hash map | `map[K]V` | `HashMap` | `dict` | `Map`/object |
| Missing key | Zero value (no error) | `null` | `KeyError` | `undefined` |
| Ordered | Never | `LinkedHashMap` | Yes (insertion) | Map: insertion |
| Thread-safe | No | `ConcurrentHashMap` | GIL-ish, no | No |
| Strings | Immutable UTF-8 bytes | Immutable UTF-16 | Immutable Unicode | Immutable UTF-16 |

## 11. Practical Exercise

1. Build a map of 3 country→capital pairs; print sorted by country.
2. Detect if a word is an anagram of another using one map.
3. Convert `[]byte` → string → `[]rune` and print lengths of each for `"日本語"`.

## 12. Mini Project / Task

`contacts.go`: `map[string]string` of name→phone. CLI commands via `os.Args`: `add name phone`, `get name` (comma-ok!), `list` (sorted), `del name`, `count`.

## 13. Interview Questions

### Easy
- What does reading a missing key return?
- How do you delete a map entry?

### Medium
- What is the comma-ok idiom?
- Why is map iteration order random in Go?

### Hard
- Why are map keys required to be comparable? What breaks otherwise?
- How would you make concurrent map access safe? Compare `sync.Mutex` vs `sync.Map`.

## 14. Daily Practice Questions

### Easy
1. Create a map of 3 fruits→prices; print all.
2. Use comma-ok to check for a missing key.
3. Delete a key that doesn't exist (verify no panic).
4. Print the rune count of `"golang ☕"`.
5. Split a CSV line and rejoin with ` | `.

### Medium
6. Count vowel frequencies in a sentence.
7. Invert a map (values become keys).
8. Find the first non-repeating character in a string.
9. Check whether two strings are anagrams using maps.
10. Build a string of 100 comma-separated numbers using `strings.Builder`.

### Hard
11. Implement a word ladder check: two words differing by exactly one letter, using maps.
12. Group anagrams: `[]string` → `[][]string` (classic LeetCode 49) using a canonical key.
13. Implement a tiny LRU cache with a map + slice (no external libs).
14. Parse `"key1=value1;key2=value2"` into a map, handling URL-style escapes via `net/url`.
15. Implement `GroupBy[T any, K comparable]` logic for a slice of structs by a chosen key — with maps and closures.

## 15. Solutions / Hints

- Q7: careful — Go map keys must be comparable; only invert when values are unique.
- Q12 hint: sort each word's letters to make the map key.
- Q13 hint: store order in a slice; evict index 0 when over capacity.
- Q15 hint: `func groupBy[T any, K comparable](items []T, key func(T) K) map[K][]T`.

## 16. Day Summary

- Maps: `make` before writing, comma-ok for presence, random order, not concurrent-safe.
- Strings: bytes vs runes, `strings` + `strconv` packages, `strings.Builder` for loops.

## 17. What To Revise

- Zero-value read vs comma-ok; byte/rune iteration.

## 18. What Comes Tomorrow

**Day 7 — Structs**: defining your own types, embedding, tags, and comparison — the foundation for methods, interfaces, JSON, and databases.
