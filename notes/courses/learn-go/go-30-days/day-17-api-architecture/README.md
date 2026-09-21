# Day 17 — API Architecture

## Learning Objectives

- Write middleware (logging, recovery, auth) by composing `http.Handler`.
- Structure a growing service: routes, dependency injection, config.
- Add graceful shutdown and request timeouts.
- Know the standard production layout for Go backends.

## Prerequisites

- Day 16 REST API.

## 1. Concept Introduction

**Middleware** is a function that wraps a handler to add behavior before/after it:

```go
func withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s took %s", r.Method, r.URL.Path, time.Since(start))
	})
}
```

Because it's just `Handler → Handler`, middleware composes: `withLogging(withRecovery(withAuth(mux)))`.

## 2. Why This Concept Exists

Cross-cutting concerns — logging, auth, tracing, panic recovery, rate limiting — must apply to every endpoint. Copy-pasting them into every handler doesn't scale. The middleware pattern (native to Go's single `Handler` interface, no framework needed) centralizes them once, in order, testably.

## 3. Syntax — the middleware signature

```go
type Middleware func(http.Handler) http.Handler

func chain(h http.Handler, mw ...Middleware) http.Handler {
	for i := len(mw) - 1; i >= 0; i-- { // apply in listed order
		h = mw[i](h)
	}
	return h
}
```

## 4. Detailed Explanation

**Execution order**: `withLogging(withRecovery(handler))` → logging runs first, recovery inside it, handler innermost. Requests pass inward, responses bubble outward — an onion.

**Dependency injection, Go-style**: no framework. Build dependencies in `main`, pass via constructors:

```go
store := store.New(...)
svc := service.New(store)
h := api.New(svc)   // handler holds exactly what it needs behind interfaces
```

This keeps everything testable — tests construct a service with a fake store.

**Graceful shutdown**: on SIGTERM (what Kubernetes sends), stop accepting new requests, finish in-flight ones, then exit:

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()
go srv.ListenAndServe()
<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
srv.Shutdown(shutdownCtx)
```

**Config**: read from environment (12-factor): `os.Getenv("PORT")` with sane defaults; keep secrets out of code.

## 5. Example 1 — Recovery + logging + auth middleware

```go
package main

import (
	"log"
	"net/http"
	"time"
)

func withRecovery(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("panic recovered: %v", rec)
				http.Error(w, "internal error", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
	})
}

func withAuth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer secret-token" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /public", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("public"))
	})
	mux.Handle("GET /private", withAuth(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("private"))
	})))

	// global chain; per-route middleware applied selectively
	log.Fatal(http.ListenAndServe(":8080", withLogging(withRecovery(mux))))
}
```

Note: recovery must wrap the whole mux so a panic in any handler can't crash the server (Go's net/http already recovers per-connection, but explicit recovery lets you log and return clean 500s).

## 6. Example 2 — Production main with graceful shutdown

```go
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080" // sane default
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("ok"))
	})

	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		log.Println("listening on :", port)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatal("server:", err)
		}
	}()

	<-ctx.Done()
	log.Println("shutting down...")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("forced shutdown: %v", err)
	}
	log.Println("bye")
}
```

## 7. Real-World Example — full production layout

```text
service/
├── cmd/api/main.go           wiring + shutdown only
├── cmd/worker/main.go        (second binary, same module)
├── internal/
│   ├── api/                  handlers + middleware + routes
│   │   ├── middleware.go
│   │   └── routes.go
│   ├── config/config.go      env parsing, defaults, validation
│   ├── service/              business rules
│   ├── repository/           data access, interface + impls
│   └── models/               shared domain types
├── pkg/                      optional: reusable library code
├── migrations/               SQL schema versions
├── Dockerfile                (Day 28)
└── Makefile                  run/test/lint targets
```

Rules of thumb: `cmd` binaries are thin; `internal` holds everything private; the dependency arrow always points downward (api → service → repository → models); models import nothing above them.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Middleware that forgets `next.ServeHTTP` | Request hangs/never reaches handler |
| Wrong wrap order (recovery outermost) | Logging misses panics; think onion |
| God `main.go` with logic inside | `cmd` should only wire and run |
| No graceful shutdown | Kills in-flight requests on deploy |
| Global singletons for deps | Untestable; use constructor injection |
| Config via constants in code | Can't change per environment; use env/flags/files |

## 9. Best Practices

- Keep middleware small and single-purpose; compose, don't configure.
- Recover + log at the boundary; return sanitized 500s (never leak internals).
- Inject interfaces; construct concretes in `main`.
- Every binary: timeouts + graceful shutdown from day one.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Spring | FastAPI | Express |
|--------|----|--------|---------|---------|
| Middleware | plain functions | filters/interceptors | decorators | `app.use` |
| DI | manual constructors | IoC container | Depends | manual |
| Config | env + structs | profiles | settings | dotenv |
| Shutdown | srv.Shutdown | context close | uvicorn handles | server.close |

## 11. Practical Exercise

1. Write `withRequestID` middleware adding `X-Request-Id` (generate if absent).
2. Apply auth to a route group only (wrap a sub-mux).
3. Add graceful shutdown to Day 16's tasks API.

## 12. Mini Project / Task

Upgrade the tasks API: add logging + recovery + request-id middleware, env-based port, `/healthz`, and graceful shutdown. Verify with Ctrl+C that in-flight requests complete.

## 13. Interview Questions

### Easy
- What is middleware in Go?
- How do you apply middleware to only some routes?

### Medium
- Why does middleware order matter? Give a concrete example.
- What does graceful shutdown do and why does Kubernetes need it?

### Hard
- Explain how you'd propagate a request ID from middleware into logs and downstream calls (context preview).
- Design the dependency graph for a service with cache + DB + queue; what interfaces do you draw and where?

## 14. Daily Practice Questions

### Easy
1. Write a middleware that prints each request's path.
2. Wrap one handler with two middlewares; predict order.
3. Read PORT from env with a default.
4. Add `/version` returning a build string constant.
5. Write a middleware rejecting requests with bodies > 1 MB.

### Medium
6. Implement `chain(h, mw...)` helper and use it.
7. Middleware measuring and logging slow requests (>200ms).
8. Add per-route middleware: auth on `/admin/*` only.
9. Implement panic recovery that also logs a stack trace (`runtime/debug.Stack`).
10. Graceful shutdown: verify with `curl` during Ctrl+C that a 3-second handler completes.

### Hard
11. Build a timeout middleware using `context.WithTimeout` per request.
12. Implement a rate-limiter middleware (token bucket, per-IP, mutex-protected).
13. Write middleware storing user info into `r.Context()` and reading it in a handler (preview Day 23).
14. Design and implement a feature-flag middleware toggling routes via env vars.
15. Compose middlewares generically for any `func(http.Handler) http.Handler` and unit-test the ordering.

## 15. Solutions / Hints

- Q6 hint: iterate middleware in reverse so the first listed runs first.
- Q12 hint: bucket per IP in `map[string]*bucket`; refill lazily by elapsed time.
- Q13 hint: `context.WithValue(r.Context(), key, user)` then `r.Context().Value(key)`.

## 16. Day Summary

- Middleware = Handler→Handler functions, composed like an onion.
- Inject dependencies via constructors; keep `cmd/` thin.
- Production binary = timeouts + graceful shutdown + recovery + logging.

## 17. What To Revise

- The middleware chain order; the graceful-shutdown skeleton.

## 18. What Comes Tomorrow

**Day 18 — SQL databases**: `database/sql`, connection pools, CRUD with Postgres, and transactions.
