# Day 21 — Concurrency: Goroutines and sync

## Learning Objectives

- Launch and coordinate goroutines; understand `WaitGroup`.
- Protect shared state with `sync.Mutex`/`RWMutex`.
- Use `sync.Once`, `atomic` operations, and detect races.
- internalize Go's concurrency philosophy.

## Prerequisites

- Day 4 functions/closures; Day 20 (race detector).

## 1. Concept Introduction

A **goroutine** is a lightweight, independently scheduled function — `go f()`. Millions can exist (each starts with ~2 KB stack). Unlike OS threads, goroutines are multiplexed onto threads by Go's runtime scheduler.

```go
go doWork()          // returns immediately!
go func(x int) { ... }(42)
```

`main` exiting kills all goroutines — coordination is your job (WaitGroup, channels, context).

## 2. Why This Concept Exists

Threads cost ~1 MB and context-switch in microseconds; goroutines cost ~2 KB and switch in nanoseconds. This makes the "one task = one goroutine" style natural — every HTTP request, every connection, every job. Combined with channels (Day 22), Go made concurrent servers writable by ordinary humans. This is *the* reason Go dominates cloud infrastructure.

## 3. Syntax

```go
var wg sync.WaitGroup
for i := 0; i < 5; i++ {
	wg.Add(1)
	go func(n int) {
		defer wg.Done()
		work(n)
	}(i)
}
wg.Wait() // blocks until all Done

var mu sync.Mutex
mu.Lock(); defer mu.Unlock() // guard shared data

var count atomic.Int64
count.Add(1) // lock-free counter

var once sync.Once
once.Do(initOnce) // exactly once, ever
```

## 4. Detailed Explanation

- **Race conditions**: two goroutines writing the same variable concurrently = undefined behavior. Fix with (a) mutexes around shared state, (b) atomics for counters, or (c) channels transferring ownership (Day 22). **Always** verify with `go test -race` / `go run -race`.
- **Mutex vs RWMutex**: `Mutex` = one exclusive accessor. `RWMutex` = many readers OR one writer — good when reads vastly outnumber writes.
- **WaitGroup**: counter-based joining. `Add` before `go`, `Done` via defer, `Wait` to join. Never pass the group by copy.
- **Data flow rule**: the closure captures variables by reference — the loop-variable copy pattern (`go func(n int){}(i)`) or per-iteration variables (default since Go 1.22) avoid surprises.
- **No free lunch**: goroutines don't make CPU-bound code faster beyond your cores (GOMAXPROCS); they excel at waiting (I/O) and structuring independent work.

## 5. Example 1 — WaitGroup fan-out

```go
package main

import (
	"fmt"
	"sync"
	"time"
)

func fetch(id int, results *[]string, mu *sync.Mutex) {
	defer mu.Unlock()
	time.Sleep(time.Duration(id%3) * 10 * time.Millisecond) // fake I/O
	mu.Lock()
	*results = append(*results, fmt.Sprintf("result-%d", id))
}

func main() {
	var (
		wg      sync.WaitGroup
		mu      sync.Mutex
		results []string
	)
	for i := 1; i <= 5; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			fetch(id, &results, &mu)
		}(i)
	}
	wg.Wait()
	fmt.Println(results) // order is nondeterministic!
}
```

Note the mutex: `append` to a shared slice from multiple goroutines is a data race without it. (Day 22 replaces this mutex+slice dance with a channel — compare!)

## 6. Example 2 — Mutex, RWMutex, Once, atomic

```go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

type Counter struct {
	mu sync.Mutex
	n  map[string]int
}

func (c *Counter) Inc(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.n[key]++
}

func (c *Counter) Get(key string) int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.n[key]
}

type Config struct {
	mu   sync.RWMutex
	data map[string]string
}

func (c *Config) Get(k string) string { // many concurrent readers
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.data[k]
}

func (c *Config) Set(k, v string) { // exclusive writer
	c.mu.Lock()
	defer c.mu.Unlock()
	c.data[k] = v
}

func main() {
	// atomic counter — no lock needed
	var hits atomic.Int64
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			hits.Add(1)
		}()
	}
	wg.Wait()
	fmt.Println(hits.Load()) // 100, always

	// sync.Once — init exactly once even under races
	var once sync.Once
	var heavy string
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			once.Do(func() { heavy = "expensive init done" })
		}()
	}
	wg.Wait()
	fmt.Println(heavy)
}
```

## 7. Real-World Example

Concurrent URL health-checker — the canonical goroutine fan-out with bounded parallelism:

```go
package main

import (
	"fmt"
	"net/http"
	"sync"
	"time"
)

func check(client *http.Client, url string) (string, error) {
	resp, err := client.Get(url)
	if err != nil {
		return url, err
	}
	defer resp.Body.Close()
	return url, nil
}

func main() {
	urls := []string{
		"https://go.dev", "https://pkg.go.dev",
		"https://invalid.example", "https://httpbin.org/status/500",
	}
	client := &http.Client{Timeout: 3 * time.Second}

	var (
		wg   sync.WaitGroup
		mu   sync.Mutex
		fail []string
	)
	for _, u := range urls {
		wg.Add(1)
		go func(url string) {
			defer wg.Done()
			if _, err := check(client, url); err != nil {
				mu.Lock()
				fail = append(fail, fmt.Sprintf("%s: %v", url, err))
				mu.Unlock()
			}
		}(u)
	}
	wg.Wait()
	for _, f := range fail {
		fmt.Println("DOWN:", f)
	}
}
```

All URLs checked in ~max(individual latency) instead of the sum — that's goroutine payoff.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Sharing a map/slice without a lock | Race → crash ("concurrent map writes") |
| `wg.Add` inside the goroutine | Race with `Wait`; Add before `go` |
| Deadlock: Lock without Unlock on all paths | Use `defer mu.Unlock()` |
| Copying a struct containing a mutex | Vet flags it; pass pointers |
| Spawning unbounded goroutines | Memory/fd exhaustion; use worker pools or semaphores |
| Believing `-race` passing means thread-safe in all schedules | It explores many, not all; design matters too |

## 9. Best Practices

- Share memory by communicating (channels) when ownership transfers; use mutexes for shared caches/state.
- Keep critical sections tiny; never do I/O while holding a lock.
- Bound concurrency (worker pools, `golang.org/x/sync/semaphore`).
- Run `-race` in tests and CI, always.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| Unit | goroutine (~2 KB) | thread (~1 MB) | thread / asyncio | event loop |
| Scheduler | M:N runtime | OS | OS / event loop | libuv |
| Shared state | mutex/atomic/channels | synchronized | GIL/locks | single-threaded |
| Race detection | built-in `-race` | external tools | limited | limited |

## 11. Practical Exercise

1. Launch 10 goroutines printing their number; add WaitGroup joining.
2. Fix a data race on a shared counter three ways: mutex, atomic, channel (preview).
3. Demonstrate a race with `-race` and read the report.

## 12. Mini Project / Task

`sitemap.go`: fetch 20 URLs concurrently (max 5 at a time — semaphore via buffered channel), print status codes with the total elapsed time. Compare vs sequential timing.

## 13. Interview Questions

### Easy
- What is a goroutine? How is it different from a thread?
- What does `sync.WaitGroup` do?

### Medium
- Mutex vs RWMutex — when?
- What is a data race? How do you find one?

### Hard
- How does Go's scheduler (GMP) multiplex goroutines on threads?
- Why is `sync.Once` safe under concurrent calls? What does it cost?

## 14. Daily Practice Questions

### Easy
1. Print "hello" from 3 goroutines; ensure all print (WaitGroup).
2. Increment a shared counter 1000× with a mutex; verify the total.
3. Use `atomic.Int64` for the same; compare code size.
4. Run any program with `-race`; fix one reported race.
5. Use `sync.Once` to lazily initialize a map.

### Medium
6. Fan out 10 HTTP GETs concurrently, collect status codes.
7. Implement a read-heavy config with RWMutex; benchmark vs Mutex.
8. Bound concurrency to 3 workers using a buffered channel as a semaphore.
9. Demonstrate a deadlock (lock twice) and explain the output.
10. Copy a struct containing a mutex; read the vet error.

### Hard
11. Implement a worker pool (N workers, M jobs, results slice) with WaitGroup.
12. Implement concurrent-safe LRU cache (map + list, mutex) and race-test it.
13. Explain and demonstrate false sharing / cache-line effects with atomic counters (GOMAXPROCS experiments).
14. Build a parallel pipeline stage that transforms a slice with bounded workers, preserving order.
15. Instrument a program to find the maximum concurrent goroutines (`runtime.NumGoroutine` polling).

## 15. Solutions / Hints

- Q8 hint: `sem := make(chan struct{}, 3)`; acquire with `sem <- struct{}{}`, release with `<-sem`.
- Q11 hint: jobs channel, done WaitGroup, results collected under mutex or via results channel (Day 22).
- Q14 hint: assign each result to `out[i]` by index — order preserved without locks on the output slice.

## 16. Day Summary

- `go f()` launches; WaitGroup joins; mutexes guard; atomics count; Once initializes.
- Races are the #1 Go bug class — the `-race` detector is your best friend.
- Bounded concurrency beats unbounded spawning.

## 17. What To Revise

- WaitGroup pattern; mutex best practices; race detector usage.

## 18. What Comes Tomorrow

**Day 22 — Channels**: typed pipes between goroutines, select, worker pools, and pipelines — Go's signature feature.
