# Day 20 — Testing, Benchmarks, and Fuzzing

## Learning Objectives

- Write unit tests with `testing`; master table-driven tests.
- Test HTTP APIs in-process with `httptest`.
- Write benchmarks and read their output.
- Use Go's native fuzzing to find edge-case bugs.

## Prerequisites

- Day 4 functions; Day 16 API.

## 1. Concept Introduction

Testing is built into Go's toolchain — no framework needed:

```bash
go test ./...          # run all tests
go test -v ./...       # verbose
go test -run TestName  # single test
go test -bench=.       # benchmarks
go test -fuzz=FuzzX    # fuzzing
go test -cover         # coverage
go test -race ./...    # data race detection
```

Test files live next to the code, named `*_test.go`, in package `foo` (white-box) or `foo_test` (black-box).

## 2. Why This Concept Exists

Go's standard library was developed test-first; the tooling reflects that culture. Table-driven tests express "many inputs, one function" without framework magic; `httptest` spins real servers in-process; fuzzing (Go 1.18+) mutates inputs automatically to find crashes no human would think of. Tests in Go are compiled artifacts — they fail to compile if APIs change, which is itself a test.

## 3. Syntax

```go
func TestAdd(t *testing.T) {         // test: name must start with Test
	t.Helper()                        // mark helper; failures point to caller
	if got := Add(1, 2); got != 3 {
		t.Errorf("Add(1,2) = %d, want 3", got)
	}
}

func BenchmarkAdd(b *testing.B) {    // benchmark
	for i := 0; i < b.N; i++ {
		Add(1, 2)
	}
}

func FuzzReverse(f *testing.F) {     // fuzzer
	f.Add("hello")                    // seed corpus
	f.Fuzz(func(t *testing.T, s string) {
		if r := Reverse(s); len(r) != len(s) {
			t.Errorf("length changed for %q", s)
		}
	})
}
```

## 4. Detailed Explanation

- **Table-driven tests** — the Go idiom. Each case is a struct literal with a name; `t.Run(name, ...)` gives subtests with readable output and `-run Name/sub` filtering:

```go
tests := []struct {
	name  string
	input int
	want  int
}{ ... }
for _, tt := range tests {
	t.Run(tt.name, func(t *testing.T) { ... })
}
```

- **t.Helper()**: inside helpers, failure lines point to the *calling* test line.
- **t.Parallel()**: run subtests concurrently (careful with shared state; capture loop vars).
- **httptest**: `httptest.NewServer(handler)` gives a real URL; `httptest.NewRecorder()` + `ServeHTTP` tests a handler without any network at all.
- **Benchmarks**: the framework increases `b.N` until timing is stable; `-benchmem` shows allocations. Compare with `benchstat` between commits.
- **Fuzzing**: generates random/mutated inputs from seeds, hunting for panics/violations; failures are written to `testdata/fuzz/` as regression cases that `go test` replays forever after.

## 5. Example 1 — Table-driven unit tests

```go
// mathx.go
package mathx

func Add(a, b int) int { return a + b }

func Div(a, b int) (int, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}
```

```go
// mathx_test.go
package mathx

import (
	"errors"
	"testing"
)

func TestAdd(t *testing.T) {
	tests := []struct {
		name string
		a, b int
		want int
	}{
		{"positive", 1, 2, 3},
		{"negatives", -1, -2, -3},
		{"mixed", -1, 2, 1},
		{"zero", 0, 0, 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := Add(tt.a, tt.b); got != tt.want {
				t.Errorf("Add(%d,%d) = %d, want %d", tt.a, tt.b, got, tt.want)
			}
		})
	}
}

func TestDiv(t *testing.T) {
	got, err := Div(10, 2)
	if err != nil || got != 5 {
		t.Fatalf("Div(10,2) = %d, %v; want 5, nil", got, err)
	}

	_, err = Div(1, 0)
	if err == nil {
		t.Fatal("expected error for zero divisor")
	}
}
```

## 6. Example 2 — httptest for the tasks API

```go
package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"tasksapi/internal/store"
)

func TestCreateAndGetTask(t *testing.T) {
	h := &Handler{Store: store.NewMemory()}
	srv := httptest.NewServer(NewRouter(h))
	defer srv.Close()

	// POST
	resp, err := http.Post(srv.URL+"/tasks", "application/json",
		strings.NewReader(`{"title":"write tests"}`))
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, want 201", resp.StatusCode)
	}
	var created struct {
		ID int `json:"id"`
	}
	json.NewDecoder(resp.Body).Decode(&created)

	// GET
	res2, _ := http.Get(srv.URL + "/tasks/" + itoa(created.ID))
	if res2.StatusCode != http.StatusOK {
		t.Fatalf("get status = %d, want 200", res2.StatusCode)
	}
	res2.Body.Close()
}

func TestCreateValidation(t *testing.T) {
	rec := httptest.NewRecorder() // no network at all
	req := httptest.NewRequest("POST", "/tasks", strings.NewReader(`{"title":"  "}`))

	h := &Handler{Store: store.NewMemory()}
	h.create(rec, req)

	if rec.Code != http.StatusUnprocessableEntity {
		t.Errorf("status = %d, want 422", rec.Code)
	}
}

func itoa(n int) string {
	b, _ := json.Marshal(n)
	return string(b)
}
```

Two styles shown: a real server (`NewServer`) for integration flavor, and recorder-level for pure handler unit tests.

## 7. Real-World Example — benchmark + fuzz

```go
package stringutil

import "strings"

// Reverse reverses a UTF-8 string by runes.
func Reverse(s string) string {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}

func JoinUpper(parts []string) string {
	var b strings.Builder
	for _, p := range parts {
		b.WriteString(strings.ToUpper(p))
	}
	return b.String()
}
```

```go
package stringutil

import "testing"

func BenchmarkReverse(b *testing.B) {
	s := strings.Repeat("go", 100)
	for i := 0; i < b.N; i++ {
		Reverse(s)
	}
}

func BenchmarkJoinUpper(b *testing.B) {
	parts := []string{"a", "b", "c", "d"}
	for i := 0; i < b.N; i++ {
		JoinUpper(parts)
	}
}

func FuzzReverse(f *testing.F) {
	f.Add("hello")
	f.Add("héllo ☕")
	f.Add("")
	f.Fuzz(func(t *testing.T, s string) {
		rev := Reverse(s)
		if back := Reverse(rev); back != s {
			t.Errorf("Reverse(Reverse(%q)) = %q", s, back)
		}
	})
}
```

```bash
go test -bench=. -benchmem
# BenchmarkReverse-8      2000000    612 ns/op    1232 B/op    2 allocs/op
go test -fuzz=FuzzReverse -fuzztime=30s
```

The fuzz property (double-reverse is identity) catches invalid-UTF-8 and multi-byte bugs in byte-based implementations instantly.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| `t.Fatal` in subtest goroutines | Use `t.Fatal` only on the test goroutine; `t.Error` elsewhere |
| Loop-variable capture in parallel subtests | `tt := tt` (pre-1.22) before `t.Parallel()` |
| Testing implementation, not behavior | Assert outputs/HTTP responses, not internal calls |
| Benchmarks with setup inside the loop | Move setup out; use `b.ResetTimer()` |
| Sharing one store/DB across tests | Isolate state per test or order-dependence appears |
| Ignoring `go test -race` | Races hide until production |

## 9. Best Practices

- Table-driven by default; subtests named clearly.
- Keep tests fast (ms range); mark slow/integration tests and gate them (`testing.Short()`).
- Aim for meaningful coverage (`go test -cover`), not 100% theater.
- Add a fuzz target for every parser/encoder you write.
- Run `go test -race ./...` in CI.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java (JUnit) | Python (pytest) | JS (Jest) |
|--------|----|--------------|-----------------|-----------|
| Runner | `go test` built-in | JUnit+Gradle | pytest | npx jest |
| Parametrized | table-driven | @ParameterizedTest | parametrize | test.each |
| Mocking | interfaces by hand | Mockito | unittest.mock | jest.mock |
| Fuzzing | native | external (Jazzer) | external | external |
| Benchmarks | native `testing` | JMH | external | benchmark.js |

## 11. Practical Exercise

1. Table-driven test for `Div` covering the error case.
2. Test Day 16's create endpoint with `httptest.NewRecorder` (no network).
3. Benchmark `strings.Builder` vs `+=` concatenation with `-benchmem`.

## 12. Mini Project / Task

Bring test coverage to the tasks API: handler tests (all 5 verbs, success + error paths), a store race test (`go test -race` with parallel goroutines hammering Create/Get), and a fuzz target for your validation/parse functions.

## 13. Interview Questions

### Easy
- How do you run a single test in Go?
- What is a table-driven test?

### Medium
- `t.Fatal` vs `t.Error`?
- What does `-race` detect?

### Hard
- Explain how Go fuzzing works: seeds, corpus, and `testdata/fuzz` regressions.
- How would you benchmark two implementations rigorously (benchstat, b.ReportAllocs, controlled env)?

## 14. Daily Practice Questions

### Easy
1. Write a test for `Add` failing intentionally; read the output.
2. Run only subtests matching a name with `-run`.
3. Print test coverage for a package.
4. Write a benchmark printing ns/op.
5. Use `t.Helper()` in a custom assertion function.

### Medium
6. Table-driven tests with subtests for string utilities.
7. Test an HTTP handler with `httptest.NewRecorder`.
8. Write a test asserting an error message with `errors.Is`.
9. Use `t.Cleanup` for temp files.
10. Run the race detector on code with an intentional race; read the report.

### Hard
11. Write a fuzz target for a CSV parser; fix whatever it finds.
12. Benchmark JSON marshal vs manual encoding; analyze allocations.
13. Test concurrent-safe store: N goroutines × M ops, then assert consistency.
14. Use golden files for API response testing (with `-update` flag pattern).
15. Implement `TestMain` for global setup/teardown (e.g., test DB container).

## 15. Solutions / Hints

- Q3: `go test -cover ./...`; `-coverprofile=c.out` + `go tool cover -html=c.out`.
- Q11 hint: `f.Fuzz(func(t *testing.T, line string) { recs, err := ParseCSV(line); if err == nil { validate(recs) } })`.
- Q14 hint: write expected output to `testdata/golden.txt`; `-update` regenerates.

## 16. Day Summary

- `go test` + `testing` covers unit, benchmark, fuzz, coverage, race — zero dependencies.
- Table-driven tests + subtests are the house style.
- `httptest` tests handlers and APIs in-process; fuzzers guard parsers.

## 17. What To Revise

- Test function naming rules; the benchmark output fields.

## 18. What Comes Tomorrow

**Day 21 — Concurrency**: goroutines, the `sync` package, and the mindset of "don't communicate by sharing memory; share memory by communicating."
