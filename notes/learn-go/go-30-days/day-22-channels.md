# Day 22 — Channels

## Learning Objectives

- Create and use unbuffered and buffered channels.
- Master `select`, channel directions, and closing semantics.
- Build worker pools, pipelines, and fan-in/fan-out patterns.
- Avoid deadlocks, goroutine leaks, and nil-channel traps.

## Prerequisites

- Day 21 goroutines.

## 1. Concept Introduction

A channel is a **typed conduit** for passing values between goroutines:

```go
ch := make(chan int)    // unbuffered: send blocks until a receiver is ready
ch := make(chan int, 5) // buffered: blocks only when full

ch <- 42     // send
v := <-ch    // receive
close(ch)    // no more sends
v, ok := <-ch // ok == false after close and drain
```

The Go proverb: *"Don't communicate by sharing memory; share memory by communicating."*

## 2. Why This Concept Exists

Mutexes protect shared memory, but ownership of data ("who may touch this?") stays murky. Channels transfer **ownership**: the sender hands a value to exactly one receiver, making data flow visible in the type system and code structure. Pipelines, worker pools, cancellation, and timeouts become composable patterns instead of ad-hoc lock choreography.

## 3. Syntax

```go
ch := make(chan T, cap)

ch <- v        // send (blocks if unbuffered/full)
v = <-ch       // receive (blocks if empty)
close(ch)

for v := range ch { }     // receives until closed

// directions — enforce at compile time
func produce(out chan<- int) { }
func consume(in <-chan int) { }

// select: wait on multiple channel ops
select {
case v := <-a:
case ch2 <- x:
case <-time.After(time.Second):
}
```

## 4. Detailed Explanation

- **Unbuffered** = synchronization point: send and receive rendezvous. Great for handoff/semantics.
- **Buffered** = decoupling with backpressure: blocks only when the buffer is full.
- **Closing**: only the **sender** closes. Receiving from a closed channel yields zero values with `ok == false`; `range` ends. Sending to a closed channel **panics**. Closing twice panics.
- **`select`**: waits on multiple operations; picks a ready one at random if several are ready; a `default` case makes it non-blocking. Combined with `time.After` and `ctx.Done()` it's how timeouts/cancellation work.
- **Nil channels block forever** — useful in `select` to disable a case by setting the channel to nil.
- **Deadlock**: all goroutines blocked → runtime panics with "all goroutines are asleep".
- **Goroutine leak**: a goroutine blocked on a channel nobody will ever receive from/send to — memory leak. Always provide an exit path (close, ctx cancellation).

## 5. Example 1 — Buffered vs unbuffered, range, close

```go
package main

import "fmt"

func producer(nums []int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // sender closes; defer ensures it even on early return
		for _, n := range nums {
			out <- n
		}
	}()
	return out
}

func main() {
	// unbuffered: send blocks until main receives
	sync := make(chan string)
	go func() { sync <- "handoff done" }()
	fmt.Println(<-sync)

	// buffered
	buf := make(chan int, 3)
	buf <- 1 // no receiver needed yet
	buf <- 2
	buf <- 3
	// buf <- 4 would block: buffer full
	fmt.Println(<-buf, <-buf, <-buf)

	// range until close
	ch := producer([]int{10, 20, 30})
	for v := range ch { // ends when producer closes ch
		fmt.Println("got", v)
	}

	// comma-ok after drain
	v, ok := <-ch
	fmt.Println(v, ok) // 0 false — closed and empty
}
```

## 6. Example 2 — select: timeouts + cancellation

```go
package main

import (
	"context"
	"fmt"
	"time"
)

func slowWork(ctx context.Context) <-chan string {
	out := make(chan string, 1)
	go func() {
		time.Sleep(2 * time.Second) // simulated slowness
		out <- "work finished"
	}()
	return out
}

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()

	select {
	case res := <-slowWork(ctx):
		fmt.Println(res)
	case <-ctx.Done():
		fmt.Println("timeout:", ctx.Err()) // fires first here
	}
}
```

## 7. Real-World Example — worker pool + fan-in

```go
package main

import (
	"fmt"
	"sync"
)

func worker(id int, jobs <-chan int, results chan<- string, wg *sync.WaitGroup) {
	defer wg.Done()
	for j := range jobs { // ends when jobs is closed
		results <- fmt.Sprintf("worker %d processed job %d", id, j)
	}
}

func main() {
	jobs := make(chan int)
	results := make(chan string)

	// fan-out: 3 workers share one jobs channel
	var wg sync.WaitGroup
	for w := 1; w <= 3; w++ {
		wg.Add(1)
		go worker(w, jobs, results, &wg)
	}

	// closer: feed jobs then close
	go func() {
		for j := 1; j <= 9; j++ {
			jobs <- j
		}
		close(jobs)
	}()

	// fan-in: collect results, finish when all workers exit
	go func() {
		wg.Wait()
		close(results)
	}()

	for r := range results {
		fmt.Println(r)
	}
}
```

This is THE production pattern: bounded parallelism, clean termination, no leaks. Job distribution is free — workers race to receive.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Sending on closed channel | Panic; only senders close, exactly once |
| Closing from the receiver side | Design smell; receivers detect close via `ok`/`range` |
| Unbuffered channel with no concurrent receiver | Deadlock |
| Leaked goroutine on abandoned channel | Ensure someone drains or ctx-cancels |
| `for { v := <-ch }` after close | Infinite zero values; use `range` or `ok` |
| Copying channels or misusing directions | Use `chan<-` / `<-chan` to document intent |

## 9. Best Practices

- Return **receive-only** channels from producers (`<-chan T`).
- Close channels via `defer` in the producer; never close in consumers.
- Every blocking receive needs an exit: ctx.Done(), time.After, or close.
- Structure programs as pipelines: generate → transform (bounded) → collect.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| Primitive | channel | BlockingQueue | queue.Queue | streams/callbacks |
| Select-like | `select` | — (CompletableFuture) | `select`/asyncio.wait | Promise.race |
| Buffered | sized channel | ArrayBlockingQueue | Queue(maxsize) | highWaterMark |
| Close semantics | explicit close + range | poison pill | sentinel values | end events |

## 11. Practical Exercise

1. Unbuffered handoff: main sends 5 values to a goroutine that prints them.
2. Buffered channel demonstrating blocking at capacity.
3. Sum numbers from a closed channel using `range`.

## 12. Mini Project / Task

`imageresize-sim.go`: producer generates 50 task IDs; pool of 4 workers "process" (sleep + format); results fan in; print summary + total duration. Add a 2-second `select` timeout for the whole batch.

## 13. Interview Questions

### Easy
- Buffered vs unbuffered channels?
- What happens when you receive from a closed channel?

### Medium
- Who closes a channel and why?
- What does `select` do when multiple cases are ready?

### Hard
- Explain a goroutine leak caused by channels and two ways to fix it.
- How do nil channels help in a `select` loop (dynamic case disabling)?

## 14. Daily Practice Questions

### Easy
1. Send 3 ints through an unbuffered channel to a printer goroutine.
2. Fill a buffered channel to capacity; show the blocking send.
3. Use `range` over a channel that a producer closes.
4. Use comma-ok to detect channel closure.
5. Demonstrate that sending to a closed channel panics.

### Medium
6. Implement `merge(cs ...<-chan int) <-chan int` (fan-in with WaitGroup).
7. Add a 1-second timeout to a receive using `select`.
8. Worker pool: 3 workers, 10 jobs, results channel, clean close.
9. Implement a non-blocking send attempt with `select` + `default`.
10. Orchestrate two goroutines racing; take the first result.

### Hard
11. Pipeline: generate → square (3 stages) → collect, with context cancellation mid-stream.
12. Implement a broadcast: one close() releases N listeners (`<-done`).
13. Rate-limit a channel consumer to 2 msgs/sec using `time.Tick` + select.
14. Or-done pattern: wrap a channel so it exits on either data or ctx.Done (from "Go Concurrency Patterns").
15. Use nil-channel disabling to multiplex two input channels that close at different times.

## 15. Solutions / Hints

- Q6 hint: start a WaitGroup'd copier per input channel, close the merged output when all finish.
- Q12 hint: closing a channel broadcasts — all receivers' receives unblock with ok=false.
- Q14 hint: `for { select { case v, ok := <-in: if !ok { return }; out <- v; case <-ctx.Done(): return } }` — with care for the send blocking too.
- Q15 hint: set `in1 = nil` when it closes; select ignores nil cases.

## 16. Day Summary

- Channels transfer ownership; unbuffered sync, buffered decouple.
- Sender closes; receivers use `range`/`ok`; select multiplexes with timeouts/cancellation.
- Worker pool + fan-in = the backbone production pattern.

## 17. What To Revise

- Close semantics table; the worker pool skeleton.

## 18. What Comes Tomorrow

**Day 23 — Context & synchronization deep dive**: cancellation, deadlines, values, and making whole request trees cancellable.
