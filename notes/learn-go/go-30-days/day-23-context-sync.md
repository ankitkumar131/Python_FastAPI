# Day 23 — Context and Synchronization

## Learning Objectives

- Create and propagate contexts: cancellation, deadlines, timeouts.
- Read context values (request IDs, auth users) correctly.
- Make goroutines, HTTP calls, and DB queries cancellable.
- Know the full `sync` toolkit: Once, Pool, Cond, ErrGroup.

## Prerequisites

- Days 21–22.

## 1. Concept Introduction

`context.Context` carries **cancellation signals, deadlines, and request-scoped values** across API boundaries and goroutine trees:

```go
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel() // always!

select {
case <-ctx.Done():
	return ctx.Err() // DeadlineExceeded or Canceled
case res := <-work:
	return res
}
```

Every blocking function in Go takes `ctx` as its **first parameter**. The stdlib's HTTP, SQL, and Mongo APIs all honor it.

## 2. Why This Concept Exists

When a user closes a browser tab mid-request, the server should stop *everything* that request started: DB queries, downstream calls, goroutines. Without a cancellation tree, servers waste resources on dead work. Context threads one cancellation signal through the entire call tree — parent cancels, all children observe. It's Go's answer to thread interruption done right: cooperative, typed, and composable.

## 3. Syntax

```go
context.Background()                     // root (main, tests)
context.TODO()                           // placeholder
ctx, cancel := context.WithCancel(parent)
ctx, cancel := context.WithTimeout(parent, d)
ctx, cancel := context.WithDeadline(parent, t)
ctx = context.WithValue(parent, key, val) // request-scoped data

ctx.Done()    // <-chan struct{} closed on cancel
ctx.Err()     // context.Canceled | context.DeadlineExceeded
ctx.Value(k)
```

## 4. Detailed Explanation

- **Tree semantics**: children inherit cancellation from parents; cancelling a parent cancels all descendants; cancelling a child doesn't affect siblings or the parent.
- **`defer cancel()` is mandatory** — with timeouts it releases the timer; with cancels it prevents leaks. Lint (contextcheck) flags missing ones.
- **Values**: use a private, unexported type as the key; values are for request-scoped metadata (request ID, auth user), **never** for optional function parameters.
- **sync deep dive**:
  - `sync.Once` — one-time init under concurrency.
  - `sync.Pool` — reusable object cache to reduce GC pressure (used by encoders, buffers).
  - `sync.Cond` — wait/broadcast on a condition (rare; channels usually better).
  - `golang.org/x/sync/errgroup` — WaitGroup + first-error propagation + ctx cancellation: the workhorse for parallel fan-out with failures.

## 5. Example 1 — Timeout + cancellation propagation

```go
package main

import (
	"context"
	"fmt"
	"time"
)

func slowQuery(ctx context.Context, name string) (string, error) {
	select {
	case <-time.After(2 * time.Second): // pretend query
		return name + ": done", nil
	case <-ctx.Done():
		return "", ctx.Err() // cooperative: check ctx at blocking points
	}
}

func main() {
	// request arrives with 1s budget
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	res, err := slowQuery(ctx, "users")
	fmt.Printf("res=%q err=%v\n", res, err)
	// res="" err="context deadline exceeded" after ~1s
}
```

## 6. Example 2 — errgroup: parallel fetch, first error wins

```go
package main

import (
	"context"
	"fmt"
	"time"

	"golang.org/x/sync/errgroup"
)

func fetch(ctx context.Context, url string, delay time.Duration) (string, error) {
	select {
	case <-time.After(delay):
		return url + " ok", nil
	case <-ctx.Done():
		return "", ctx.Err()
	}
}

func main() {
	g, ctx := errgroup.WithContext(context.Background())
	results := make([]string, 3)

	urls := []struct {
		name  string
		delay time.Duration
	}{{"a", 100 * time.Millisecond}, {"b", 300 * time.Millisecond}, {"c", 50 * time.Millisecond}}

	for i, u := range urls {
		i, u := i, u // per-iteration copies (explicit for clarity)
		g.Go(func() error {
			res, err := fetch(ctx, u.name, u.delay)
			results[i] = res
			return err
		})
	}
	if err := g.Wait(); err != nil {
		fmt.Println("failed:", err)
	}
	fmt.Println(results)
}
```

When one goroutine fails, `errgroup` cancels `ctx` — the others see `ctx.Done()` and unwind promptly. Try replacing a delay with an error to see early abort.

## 7. Real-World Example

HTTP middleware storing request metadata + a handler that cancels downstream work when the client disconnects:

```go
package main

import (
	"context"
	"fmt"
	"net/http"
)

type ctxKey int

const requestIDKey ctxKey = 1

func withRequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-Id")
		if id == "" {
			id = fmt.Sprintf("req-%d", time.Now().UnixNano())
		}
		ctx := context.WithValue(r.Context(), requestIDKey, id)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func handler(w http.ResponseWriter, r *http.Request) {
	id := r.Context().Value(requestIDKey).(string)
	// r.Context() is cancelled automatically if the client disconnects:
	select {
	case <-r.Context().Done():
		fmt.Println("client went away:", id)
		return
	case <-time.After(3 * time.Second):
		fmt.Fprintf(w, "finished %s\n", id)
	}
}

func main() {
	http.Handle("/", withRequestID(http.HandlerFunc(handler)))
	http.ListenAndServe(":8080", nil)
}
```

Kill the client mid-request (Ctrl+C on curl) and watch the server log the abandonment — cancellation for free.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Forgetting `defer cancel()` | Timer/memory leak |
| Storing ctx in a struct field | Anti-pattern; pass explicitly per call |
| Using context values for business params | Hidden dependencies; pass as args |
| Ignoring `ctx.Done()` in long loops | Cancellation never propagates |
| `WithValue` with a string key | Collisions across packages; use private typed keys |
| Detaching: `context.Background()` mid-request | Loses cancellation; derive from parent |

## 9. Best Practices

- `ctx` first param, named `ctx`, passed through unchanged.
- Check `ctx.Err()` in loops/before expensive work.
- Prefer `errgroup` over bare WaitGroup for parallel ops that can fail.
- HTTP handlers: use `r.Context()` for all downstream calls.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| Cancellation | context.Context | Thread.interrupt / Future.cancel | asyncio tasks / events | AbortSignal |
| Deadline | built-in | timeouts per call | asyncio.wait_for | setTimeout race |
| Values | WithValue | request attributes | contextvars | AsyncLocalStorage |

## 11. Practical Exercise

1. Add a 2s timeout to a 5s fake query; observe `DeadlineExceeded`.
2. Cancel from a signal: Ctrl+C cancels a running worker.
3. Propagate a request ID through three function layers via context.

## 12. Mini Project / Task

`crawler.go`: crawl a list of URLs with errgroup (limit 5), global 10s budget via context, per-request cancellation on failure. Print results and elapsed time; verify Ctrl+C aborts cleanly.

## 13. Interview Questions

### Easy
- What does `ctx.Done()` return?
- `WithTimeout` vs `WithDeadline`?

### Medium
- Why must `cancel` be deferred even with timeouts?
- What are context values for, and what not for?

### Hard
- Explain how cancellation propagates and how a goroutine can ignore it.
- How does errgroup cancel siblings on first error? Reimplement its core.

## 14. Daily Practice Questions

### Easy
1. Create a WithTimeout and print `ctx.Err()` after expiry.
2. Pass a value via WithValue and read it.
3. Cancel explicitly; observe Done channel closing.
4. Use `ctx.Err()` to distinguish Canceled vs DeadlineExceeded.
5. Add ctx to a `time.Sleep`-based worker so it exits early.

### Medium
6. Implement a cancellable worker pool (Day 22 pool + ctx).
7. Pass `r.Context()` into a DB query and cancel the HTTP request mid-flight.
8. Use sync.Pool to reuse byte buffers in a hot function; benchmark.
9. Write middleware that enforces a per-route timeout.
10. Chain: parent ctx → child WithTimeout(1s) → cancel parent; what does the child see?

### Hard
11. Reimplement `errgroup` core (WaitGroup + ctx cancel on first error).
12. Implement a `Ticker`-based heartbeat goroutine stopped via ctx.
13. Build a request-scoped logger: WithValue + a Logger that reads the ID.
14. Propagate cancellation through a 3-stage pipeline (Day 22 Q11) and prove no goroutine leaks (`runtime.NumGoroutine`).
15. Explain and demonstrate `context.AfterFunc` (Go 1.21+) for running code on cancellation.

## 15. Solutions / Hints

- Q10 hint: cancelling the parent cancels ALL children; child's Done fires with Canceled.
- Q11 hint: track first non-nil error; cancel ctx; Wait returns it.
- Q14 hint: after cancellation, poll NumGoroutine until it returns to baseline.

## 16. Day Summary

- Context = cancellation tree + deadlines + request values; first parameter everywhere.
- Always `defer cancel()`; always honor `Done()` in blocking work.
- errgroup = structured concurrency for parallel fallible work.

## 17. What To Revise

- The context creation table; errgroup skeleton.

## 18. What Comes Tomorrow

**Day 24 — Generics**: type parameters, constraints, and writing type-safe reusable code (Go 1.18+).
