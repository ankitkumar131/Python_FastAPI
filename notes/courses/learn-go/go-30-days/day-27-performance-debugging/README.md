# Day 27 — Performance, Profiling, and Debugging

## Learning Objectives

- Profile CPU and memory with `pprof`; read flame graphs.
- Write benchmarks that find real bottlenecks; avoid common measurement traps.
- Reduce allocations (escaping, pooling, preallocation).
- Debug with `delve` and reason about GC behavior.

## Prerequisites

- Day 20 benchmarks; Day 5 slices.

## 1. Concept Introduction

Go ships profiling in the stdlib:

```bash
go test -bench=. -cpuprofile=cpu.out
go tool pprof -http=:8080 cpu.out     # flame graph UI

import _ "net/http/pprof"             // live profiling endpoint
```

Plus the GC and scheduler expose stats via `runtime`, and `delve` (`dlv debug`) is the standard debugger.

## 2. Why This Concept Exists

Optimization without measurement is superstition. Go's integrated profiling means every binary can answer "where is my CPU going? what allocates?" — in tests *and* in production (pprof over HTTP). Combined with the escape analyzer's reports, you tune with evidence, not vibes. This tooling maturity is a big reason Go services hit tight latency SLOs.

## 3. Syntax

```bash
go test -bench=BenchmarkX -benchmem          # ns/op, B/op, allocs/op
go test -cpuprofile=c.out -bench=.           # CPU profile
go test -memprofile=m.out -bench=.           # heap profile
go tool pprof -http=:8080 c.out              # web UI / flame graph
go build -gcflags="-m" ./...                 # escape analysis report
GODEBUG=gctrace=1 ./app                      # GC traces
dlv debug ./cmd/api                          # debugger
```

```go
import _ "net/http/pprof" // registers /debug/pprof/* on your mux
```

## 4. Detailed Explanation

- **Benchmarks**: `b.N` auto-scales; use `b.ResetTimer()` after setup, `b.ReportAllocs()` for allocs/op. Compare revisions with `benchstat` — single runs lie (CPU frequency, thermal noise).
- **CPU profile**: shows cumulative time per function; flat view lists self-time. Flame graphs show call stacks width = time.
- **Heap profile**: `-memprofile` shows live/allocated bytes by allocation site — attack the biggest allocator first.
- **Escape analysis**: `go build -gcflags="-m"` prints `escapes to heap` / `moved to heap`. Stack allocations are free; heap allocations feed the GC. Common culprits: returning pointers to freshly built structs, interface boxing, closures capturing loop vars.
- **Common wins**:
  - Preallocate slices/maps with known capacity (Day 5).
  - `strings.Builder` instead of `+=`.
  - `sync.Pool` for reusable buffers.
  - Avoid `interface{}` boxing in hot loops (use generics, Day 24).
- **GOMAXPROCS** defaults to core count; in containers, match CPU limits (modern runtimes handle this, older ones need `automaxprocs`).

## 5. Example 1 — Benchmarking allocation strategies

```go
package main

import (
	"strconv"
	"strings"
	"testing"
)

// BAD: += concatenation — O(n²) allocations
func concatLoop(items []string) string {
	s := ""
	for _, it := range items {
		s += it + ","
	}
	return s
}

// GOOD: Builder — single growing buffer
func concatBuilder(items []string) string {
	var b strings.Builder
	for _, it := range items {
		b.WriteString(it)
		b.WriteByte(',')
	}
	return b.String()
}

func BenchmarkConcatLoop(b *testing.B) {
	items := make([]string, 100)
	for i := range items {
		items[i] = strconv.Itoa(i)
	}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = concatLoop(items)
	}
}

func BenchmarkConcatBuilder(b *testing.B) {
	items := make([]string, 100)
	for i := range items {
		items[i] = strconv.Itoa(i)
	}
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = concatBuilder(items)
	}
}
```

Typical result: ~10–50× faster and far fewer allocs for the Builder version.

## 6. Example 2 — pprof endpoint + GC tuning

```go
package main

import (
	"fmt"
	"net/http"
	_ "net/http/pprof" // side-effect import: /debug/pprof endpoints
	"runtime"
	"runtime/debug"
)

func main() {
	// read GC behavior at runtime
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	fmt.Printf("heap alloc: %d KB, gc cycles: %d\n",
		m.HeapAlloc/1024, m.NumGC)

	// soften GC aggressiveness (trade memory for CPU)
	debug.SetGCPercent(200) // default 100

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "hello")
	})
	// In production, protect or separate /debug/pprof (auth/internal-only):
	http.ListenAndServe(":8080", nil)
}
```

Capture live: `go tool pprof http://localhost:8080/debug/pprof/profile?seconds=30`

## 7. Real-World Example

Debugging workflow with delve:

```bash
dlv debug ./cmd/api
(dlv) break main.go:42
(dlv) continue
(dlv) print user
(dlv) goroutines            # all goroutines + states
(dlv) bt                    # stack trace
(dlv) watch -w user.Name    # watchpoints
```

And the production triage checklist for a slow endpoint:

```bash
curl -o cpu.out "http://svc:8080/debug/pprof/profile?seconds=30"
curl -o heap.out "http://svc:8080/debug/pprof/heap"
go tool pprof -http=:6060 cpu.out   # flame graph → find the fat stack
go tool pprof -http=:6060 heap.out  # inuse_space → find the leak
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Optimizing without a profile | Almost always the wrong spot |
| Single benchmark runs | Noise dominates; use `benchstat` with ≥10 runs |
| Setup inside `b.N` loop | Measures your setup, not your code |
| Micro-benchmarks of trivially-inlined funcs | Compiler optimizes the work away; use `runtime.KeepAlive`/sink |
| Ignoring allocs/op | GC pressure causes tail latency, not just throughput |
| Exposing pprof publicly | Information disclosure; bind to internal interface/auth |

## 9. Best Practices

- Establish a benchmark before refactoring; prove the improvement.
- Profile in production-like conditions (real data shapes).
- Keep `allocs/op` on your dashboard for hot paths.
- `GODEBUG=gctrace=1` occasionally in staging to sanity-check GC cadence.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| CPU profiler | built-in pprof | async-profiler/JFR | cProfile | inspector |
| Heap profiler | pprof heap | JFR/hprof | tracemalloc | heap snapshot |
| Debugger | delve | IDEA/JDWP | pdb | inspector |
| GC tuning | GOGC/SetGCPercent | many flags | n/a (refcount) | --max-old-space |

## 11. Practical Exercise

1. Benchmark the two concat functions; record ns/op and B/op.
2. Run with `-cpuprofile` and find the hot function in pprof's web UI.
3. Print escape analysis for a function returning `&Struct{}`; explain the report.

## 12. Mini Project / Task

Optimize a slow JSON-lines processor: profile it, find allocation hotspots (likely string conversions + unbuffered reads), fix with buffered scanning + preallocation, and prove the before/after with `benchstat`.

## 13. Interview Questions

### Easy
- What is pprof?
- How do you run benchmarks?

### Medium
- What is escape analysis? Name two things that force heap allocation.
- How do you find a memory leak in Go?

### Hard
- Explain GOGC and the trade-off of raising/lowering it.
- A service has p99 latency spikes every 2 minutes — walk through your diagnosis (GC? cron? profiling evidence?).

## 14. Daily Practice Questions

### Easy
1. Run a benchmark with `-benchmem`; explain each output column.
2. Print `runtime.NumGoroutine()` and `NumCPU()`.
3. Run a program with `GODEBUG=gctrace=1`; summarize one line.
4. View a CPU profile in the terminal (`top` view).
5. Use `b.ResetTimer()` in a benchmark with setup.

### Medium
6. Preallocate a map vs not — benchmark both.
7. Compare `strings.Builder` vs `fmt.Sprintf` in a loop.
8. Find what forces an interface value to escape with `-gcflags=-m`.
9. Use `sync.Pool` for a buffer; benchmark with `-benchmem`.
10. Profile a function dominated by JSON encoding; reduce allocations.

### Hard
11. Diagnose a goroutine leak via `/debug/pprof/goroutine` deltas.
12. Benchmark on an overloaded machine; show why benchstat matters.
13. Reduce a function's allocs from 5 to 0 (returning fixed-size arrays, avoiding boxing).
14. Use execution traces (`go test -trace`) to explain scheduler latency.
15. Tune GOGC/GOMEMLIMIT for a memory-capped container; measure the effects.

## 15. Solutions / Hints

- Q9 hint: `pool.Get()`/`pool.Put()` around buffer use; watch for returning pooled memory to callers.
- Q14 hint: `go test -trace=trace.out` then `go tool trace trace.out` — check "Scheduler latency profile".
- Q15 hint: `GOMEMLIMIT=100MiB` soft limit; watch GC frequency vs OOM risk.

## 16. Day Summary

- Measure first: benchmarks + pprof + benchstat.
- Allocation reduction (prealloc, Builder, Pool, generics-over-interface) is the top Go optimization lever.
- delve for interactive debugging; pprof-over-HTTP for production triage.

## 17. What To Revise

- Benchmark hygiene rules; the escape-analysis flags.

## 18. What Comes Tomorrow

**Day 28 — Production Go**: Docker, graceful degradation, structured logging, metrics, and deployment concerns.
