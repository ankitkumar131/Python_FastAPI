# Day 26 — Advanced Go

## Learning Objectives

- Use reflection to inspect and manipulate values at runtime.
- Understand `unsafe` and when (rarely) it's justified.
- Embed static files with `go:embed`.
- Survey cgo, assembly, and linker flags.

## Prerequisites

- Day 7 structs/tags; Day 10 interfaces.

## 1. Concept Introduction

Advanced Go features trade safety/power:

| Feature | Power | Cost |
|---------|-------|------|
| `reflect` | runtime inspection (JSON, ORMs, DI) | slow, loses compile checks |
| `unsafe` | memory layout control | non-portable, dangerous |
| `go:embed` | bundle files into the binary | binary size |
| cgo | call C libraries | build complexity, performance |

## 2. Why This Concept Exists

Libraries like `encoding/json`, ORMs, and validators must work on *any* struct without knowing it ahead of time — only reflection can do that. `go:embed` solves static assets (templates, migrations, frontend builds) by making single-binary deployment complete. These exist so *users* of frameworks never need them — but reading framework code (interviews!) requires fluency.

## 3. Syntax

```go
// reflection
t := reflect.TypeOf(x)
v := reflect.ValueOf(x)
v.Kind()            // struct, slice, ptr...
t.NumField()
t.Field(i).Tag.Get("json")
v.Field(i).SetString("new") // needs addressability

// embed
//go:embed files/*
var content embed.FS

// unsafe
sizeof := unsafe.Sizeof(x)
p := unsafe.Pointer(&x)
```

## 4. Detailed Explanation

- **Reflection's laws** (from the docs): (1) reflection goes from interface value to reflection object; (2) from reflection object back to interface value; (3) to modify a value it must be **settable** — obtained through a pointer.
- **Cost**: reflection is 10–100× slower than direct code and fails at runtime instead of compile time. Hot paths use codegen instead (easyjson, protoc).
- **unsafe**: bypasses type safety; used in stdlib internals, serialization libraries, and zero-copy tricks. `unsafe.Sizeof/Alignof/Offsetof` are safe to read; pointer conversion is where dragons live. GC may move nothing today, but the contract is fragile — encapsulate it.
- **go:embed**: files become part of the binary; `embed.FS` implements `fs.FS`, feeding straight into `http.FileServer` or template parsing.
- **cgo**: `import "C"` lets Go call C — but breaks easy cross-compilation and adds call overhead. Modern answer for perf-critical paths: pure Go or WASM.

## 5. Example 1 — Reflection: struct inspector

```go
package main

import (
	"fmt"
	"reflect"
)

type User struct {
	Name  string `validate:"required" json:"name"`
	Age   int    `validate:"min=0" json:"age"`
	email string // unexported: visible to reflect, not settable cross-package
}

func inspect(v any) {
	t := reflect.TypeOf(v)
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	if t.Kind() != reflect.Struct {
		fmt.Println("not a struct")
		return
	}
	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)
		fmt.Printf("field=%s type=%s json=%q validate=%q exported=%v\n",
			f.Name, f.Type, f.Tag.Get("json"), f.Tag.Get("validate"),
			f.IsExported())
	}
}

func main() {
	inspect(User{})
	inspect(&User{}) // pointer handled
	inspect(42)
}
```

This is exactly what `encoding/json` and validators do to your structs.

## 6. Example 2 — go:embed + unsafe sizes

```go
package main

import (
	"embed"
	"fmt"
	"unsafe"
)

//go:embed assets/*
var assets embed.FS

type Point struct{ X, Y int64 }

func main() {
	// embedded FS
	entries, err := assets.ReadDir("assets")
	if err != nil {
		fmt.Println("no assets dir (expected in this snippet):", err)
	}
	for _, e := range entries {
		fmt.Println("embedded:", e.Name())
	}

	// safe uses of unsafe: introspection
	fmt.Println("size of Point:", unsafe.Sizeof(Point{}))   // 16
	fmt.Println("size of int:", unsafe.Sizeof(int(0)))       // 8 (64-bit)
	var s struct {
		a byte
		b int64
	}
	fmt.Println("offsets:", unsafe.Offsetof(s.a), unsafe.Offsetof(s.b)) // 0 8 — padding!
}
```

Struct field ordering affects size (padding) — why serialization libs care about layout.

## 7. Real-World Example

A tiny reflection-based validator — the core of libraries like `go-playground/validator`:

```go
package main

import (
	"fmt"
	"reflect"
	"strconv"
	"strings"
)

func Validate(v any) []string {
	var errs []string
	val := reflect.ValueOf(v)
	if val.Kind() == reflect.Ptr {
		val = val.Elem()
	}
	t := val.Type()
	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)
		rule := f.Tag.Get("validate")
		if rule == "" {
			continue
		}
		for _, r := range strings.Split(rule, ",") {
			switch {
			case r == "required" && val.Field(i).IsZero():
				errs = append(errs, f.Name+" is required")
			case strings.HasPrefix(r, "min="):
				min, _ := strconv.Atoi(strings.TrimPrefix(r, "min="))
				if val.Field(i).Int() < int64(min) {
					errs = append(errs, fmt.Sprintf("%s must be >= %d", f.Name, min))
				}
			}
		}
	}
	return errs
}

type Signup struct {
	Name string `validate:"required"`
	Age  int    `validate:"min=18"`
}

func main() {
	fmt.Println(Validate(Signup{Name: "", Age: 12}))
	// [Name is required Age must be >= 18]
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Reflection in hot paths | Massive slowdown; use type switches/codegen |
| Expecting to set unexported fields | `CanSet()` is false; by design |
| `unsafe.Pointer` round-trips through non-pointer types | Violates the unsafe rules; GC hazards |
| Embedding huge files | Binary bloat; embed only what's needed |
| cgo for trivial things | Cross-compilation pain; find pure-Go alternatives |

## 9. Best Practices

- Reflection: validate at startup (fail fast), not per-request, where possible.
- Keep `unsafe` confined to tiny, documented, tested packages.
- `go:embed` everything a deployment needs: templates, migrations, static UIs.
- Read stdlib source — `encoding/json` is the best reflection textbook.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JS |
|--------|----|------|--------|-----|
| Reflection | reflect pkg | rich, verbose | natives everywhere | proto-only |
| Unsafe memory | unsafe pkg | sun.misc.Unsafe | ctypes | — |
| Asset embedding | go:embed | resources in jar | importlib.resources | bundlers |
| Calling C | cgo | JNI | ctypes/cffi | N-API/wasm |

## 11. Practical Exercise

1. Print all struct tags of a type via reflection.
2. Modify a struct field through a pointer with `reflect`.
3. Embed a text file and serve it over HTTP.

## 12. Mini Project / Task

`structcli.go`: a `describe` command that takes a compiled-in registry of types and prints a markdown table of fields, types, and tags (mini doc-generator). Add a reflection-based equality checker for structs of scalars.

## 13. Interview Questions

### Easy
- What is `go:embed` for?
- What are the three laws of reflection?

### Medium
- Why is reflection slow? What do libraries do about it?
- What does `unsafe.Sizeof` return for a struct with mixed field types, and why?

### Hard
- How does `encoding/json` use reflection, and where does it fail (unexported fields, cycles)?
- Explain struct padding/alignment and its impact on memory and serialization.

## 14. Daily Practice Questions

### Easy
1. Print `Kind()` of int, slice, map, struct, ptr values.
2. Use reflect to count struct fields.
3. Embed a string constant vs a file — compare approaches.
4. Print `unsafe.Sizeof` of bool, int64, string.
5. Use `reflect.TypeOf` on an interface holding different types.

### Medium
6. Build a field-by-field struct printer using tags.
7. Set a field value via `reflect.ValueOf(&s).Elem()`.
8. Detect struct cycles with reflection (visited map of pointers).
9. Embed a directory and list its contents recursively (`fs.WalkDir`).
10. Measure the benchmark cost of reflection vs direct field access.

### Hard
11. Implement `DeepEqual` for scalar/nested structs without `reflect.DeepEqual`.
12. Build a reflection-based CSV unmarshaller driven by tags.
13. Write an `unsafe`-based fast string↔[]byte converter; explain the aliasing hazards.
14. Implement a tagged-union (sum type) with reflection-based visiting.
15. Use `-gcflags=-m` and explain inlining decisions you observe.

## 15. Solutions / Hints

- Q7 hint: `v := reflect.ValueOf(ptr).Elem(); v.FieldByName("Name").SetString("x")` — only if `CanSet`.
- Q13 hint: `unsafe.String(unsafe.SliceData(b), len(b))` (Go 1.20+) — the returned string aliases b's memory; mutating b mutates it.
- Q15 hint: look for `can inline` lines in the output.

## 16. Day Summary

- Reflection = runtime metaprogramming powering JSON/ORM/validators; costly, use deliberately.
- unsafe = precise memory tools, rarely needed, isolate carefully.
- go:embed = complete single-binary deployments.

## 17. What To Revise

- Settability rules; embed + `fs.FS` integration.

## 18. What Comes Tomorrow

**Day 27 — Performance & Debugging**: pprof, benchmarks in anger, memory tuning, and the debugger.
