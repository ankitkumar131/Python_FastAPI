# Day 29 — Capstone Project: URL Shortener

## Learning Objectives

- Build a complete production-style service: a URL shortener.
- Apply Days 1-28: layered architecture, REST, validation, middleware, storage, tests, Docker.

## 1. Project Overview

Build goshr, a URL shortener service:

- POST /api/shorten with {"url":"https://example.com/long/path"} returns 201 + {"code":"aB3xK9", ...}
- GET /{code} redirects (302) to the target; 404 if unknown
- GET /api/stats/{code} returns click stats
- DELETE /api/{code} returns 204
- GET /healthz returns 200

## 2. Architecture

```text
goshr/
├── cmd/goshr/main.go     wiring + graceful shutdown (Day 17/28)
├── internal/
│   ├── api/              handlers + middleware + router (Day 16/17)
│   ├── shortener/        domain: Link, Service, validation (Day 7/11)
│   └── store/            Store interface + memory + postgres (Day 10/16/18)
├── Dockerfile            multi-stage distroless (Day 28)
└── Makefile
```

Dependencies point downward: api -> shortener -> store (interfaces only).

## 3. Domain and Store interface

```go
package shortener

import (
	"context"
	"errors"
	"math/rand"
	"net/url"
	"time"
)

var (
	ErrNotFound = errors.New("short link not found")
	ErrInvalid  = errors.New("invalid url")
)

type Link struct {
	Code      string    `json:"code"`
	Target    string    `json:"target"`
	CreatedAt time.Time `json:"created_at"`
	Clicks    int64     `json:"clicks"`
}

type Store interface {
	Save(ctx context.Context, l Link) error
	Get(ctx context.Context, code string) (Link, error)
	IncrementClicks(ctx context.Context, code string) error
	Delete(ctx context.Context, code string) error
}

func Validate(target string) error {
	u, err := url.Parse(target)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" {
		return ErrInvalid
	}
	return nil
}

const alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

func NewCode(n int) string {
	b := make([]byte, n)
	for i := range b {
		b[i] = alphabet[rand.Intn(len(alphabet))]
	}
	return string(b)
}
```

Service wraps the store: Shorten validates and saves; Resolve fetches and increments clicks (best effort).

## 4. In-memory store

Implement the interface with map[string]Link guarded by sync.RWMutex (Day 21): reads under RLock, writes under Lock, ErrNotFound when missing. Write a Postgres version with the same interface so handlers never change (Day 16/18 pattern).

## 5. HTTP handlers

- POST /api/shorten: decode JSON (400 bad json), validate (422 ErrInvalid), create (201)
- GET /{code}: resolve, then http.Redirect(w, r, target, http.StatusFound); 404 with the error envelope on ErrNotFound
- GET /api/stats/{code} and DELETE /api/{code} (204): straightforward
- Consistent error envelope: {"error":{"code","message"}} (Day 16)

## 6. Middleware + main

Day 17 chain: request-ID, logging, recovery around the router; signal.NotifyContext + srv.Shutdown in main; store selected via STORE=memory|postgres.

## 7. Tests

- Table-driven validation tests (Day 20)
- httptest.NewServer integration: shorten, then follow with redirects disabled, assert 302 + Location
- Race test: parallel clicks with go test -race
- Benchmark Resolve (Day 27)

## 8. Docker

Multi-stage build (Day 28): golang:1.22-alpine build stage, CGO_ENABLED=0 go build -ldflags="-s -w", distroless final image. Compose with postgres:16; env STORE=postgres, DATABASE_URL.

## 9. Definition of Done

- Correct status codes + error envelope everywhere
- gofmt/go vet clean, go test -race ./... green
- 70%+ coverage on shortener + api
- Graceful shutdown verified; image under 25 MB, non-root
- README with API docs

## 10. Stretch Goals

Custom aliases (409 on collision), token-bucket rate limiting, Prometheus metrics, link expiry with a cancellable cleanup goroutine, per-day analytics.

## 11. Interview Questions

### Easy
- Why 302 instead of 301? (Lets you track clicks; 301 is cached by browsers.)

### Medium
- Safe click counting under high concurrency? (Atomic increments, sharded counters, async batching.)
- Memory vs Postgres store: service-layer changes? (None, thanks to the interface.)

### Hard
- Design for 10k redirects/sec: cache hot codes, unique index on code, shard by hash.
- Preventing malicious targets: allowlists, domain reputation, scan-on-create.

## 12. Daily Practice Questions

1. Run the suite with -race; fix all reports.
2. Add custom aliases with 409 on collision.
3. Integration test against compose Postgres.
4. Add a Prometheus metrics endpoint.
5. Benchmark Resolve in both stores.
6. Add link expiry with a cancellable cleanup goroutine.
7. Load test with hey; profile with pprof; fix the top hotspot.
8. Make DELETE idempotent.
9. Switch to crypto/rand; benchmark the cost.
10. Write the README API reference.

## 13. Day Summary

You built a complete Go service: layered architecture, interface-backed storage, proper REST, middleware, three levels of tests, race-clean concurrency, and a production container. Portfolio-ready.

## 14. What To Revise

Re-read your code critically: every error handled once, every goroutine has an exit, every lock is minimal.

## 15. What Comes Tomorrow

Day 30 - Interview preparation: consolidating everything into interview-ready knowledge.
