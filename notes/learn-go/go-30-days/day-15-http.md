# Day 15 — HTTP

## Learning Objectives

- Build an HTTP server with `net/http` (handlers, ServeMux, Go 1.22 method patterns).
- Make HTTP calls as a client with timeouts and proper resource cleanup.
- Read/write JSON over HTTP end-to-end.
- Understand `http.Handler` and `http.HandlerFunc` — the base of all Go web frameworks.

## Prerequisites

- Day 14 JSON; Day 10 interfaces.

## 1. Concept Introduction

`net/http` is in the standard library — no framework needed:

- **Server**: `http.ListenAndServe(addr, mux)` with handlers registered on a `*http.ServeMux`.
- **Client**: `http.Get`, or `http.Client` with explicit timeouts (always!).

Everything is built on one interface:

```go
type Handler interface {
	ServeHTTP(ResponseWriter, *Request)
}
```

## 2. Why This Concept Exists

Go was built for Google-scale servers; the authors bet that HTTP *is* the platform. By putting a production-grade HTTP stack in the stdlib (single binary, goroutine per connection, TLS built in), Go made frameworks optional. Docker, Kubernetes, and etcd all serve HTTP with little more than what you'll write today.

## 3. Syntax

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /users/{id}", getUser)   // Go 1.22+ method + path patterns
mux.HandleFunc("POST /users", createUser)

server := &http.Server{
	Addr:              ":8080",
	Handler:           mux,
	ReadHeaderTimeout: 5 * time.Second, // always set
}

client := &http.Client{Timeout: 10 * time.Second}
resp, err := client.Get("https://example.com")
defer resp.Body.Close()
```

## 4. Detailed Explanation

- **Handler vs HandlerFunc**: any type with `ServeHTTP` is a handler; `http.HandlerFunc(f)` adapts a plain function. Both are the same interface — this is middleware's foundation (Day 17).
- **Request**: `r.Method`, `r.URL.Path`, `r.PathValue("id")` (Go 1.22), `r.Header`, query via `r.URL.Query()`, body via `r.Body` (an `io.Reader` — stream it).
- **Response**: write status + headers BEFORE body: `w.Header().Set(...)`, `w.WriteHeader(code)`, then `w.Write(...)`. `http.Error(w, msg, code)` is the quick helper; `http.Error` sets text/plain.
- **Client hygiene**: always set `Client.Timeout` (default is **zero = no timeout!**), always `defer resp.Body.Close()`, and read/drain the body even for errors to enable connection reuse.
- **Concurrency**: the server runs each request in its own goroutine — handler code must be safe for concurrent use (Day 21+).

## 5. Example 1 — JSON API server (Go 1.22 patterns)

```go
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
)

type User struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

var users = map[int]User{1: {ID: 1, Name: "Ada"}}

func getUser(w http.ResponseWriter, r *http.Request) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		http.Error(w, "invalid id", http.StatusBadRequest)
		return
	}
	u, ok := users[id]
	if !ok {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(u)
}

func createUser(w http.ResponseWriter, r *http.Request) {
	var u User
	if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
		http.Error(w, "bad json", http.StatusBadRequest)
		return
	}
	u.ID = len(users) + 1
	users[u.ID] = u
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(u)
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /users/{id}", getUser)
	mux.HandleFunc("POST /users", createUser)

	log.Println("listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}
```

## 6. Example 2 — HTTP client with JSON

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type User struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

func main() {
	client := &http.Client{Timeout: 10 * time.Second}

	// POST JSON
	body, _ := json.Marshal(User{Name: "Grace"})
	resp, err := client.Post("http://localhost:8080/users",
		"application/json", bytes.NewReader(body))
	if err != nil {
		fmt.Println("post:", err)
		return
	}
	defer resp.Body.Close()

	var created User
	if err := json.NewDecoder(resp.Body).Decode(&created); err != nil {
		fmt.Println("decode:", err)
		return
	}
	fmt.Println("created:", created, "status:", resp.StatusCode)

	// GET with context/timeout per request alternative:
	resp2, err := client.Get(fmt.Sprintf("http://localhost:8080/users/%d", created.ID))
	if err != nil {
		fmt.Println("get:", err)
		return
	}
	defer resp2.Body.Close()
	fmt.Println("status:", resp2.StatusCode)
}
```

## 7. Real-World Example

Health-check endpoints + graceful patterns you'll deploy on day one of any job:

```go
package main

import (
	"log"
	"net/http"
	"time"
)

func health(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("ok"))
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", health)

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	log.Fatal(srv.ListenAndServe())
}
```

Kubernetes probes hit `/healthz`; the timeouts protect against slow-loris style resource exhaustion.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| No client timeout | Default `http.Client` waits forever |
| Not closing `resp.Body` | Connection/socket leak |
| Writing body before `WriteHeader` | Status is auto-200; too late to change |
| Handler shared state without locks | Concurrent requests → data races |
| Ignoring `w.Write`'s error | Client disconnects are common |
| Using `http.DefaultClient` in prod | No timeout, no transport tuning |

## 9. Best Practices

- Always construct `&http.Server{}` with timeouts; never bare `ListenAndServe` in prod.
- Set `Content-Type` explicitly; encode JSON straight into the writer.
- Check `r.Method` (or use Go 1.22 pattern prefixes).
- Reuse one `http.Client` per service (it pools connections).

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java (Spring) | Python (Flask) | Node (Express) |
|--------|----|---------------|----------------|----------------|
| Server | stdlib net/http | framework + servlets | framework | framework |
| Routing | ServeMux patterns | annotations | decorators | strings |
| Handler shape | `func(w, r)` | method w/ annotations | function(req) | `(req, res)` |
| Concurrency | goroutine/request | thread pool | worker model | event loop |

## 11. Practical Exercise

1. Serve "hello" on `/` and your name on `/me`.
2. Add a `POST /echo` that returns the request body unchanged.
3. Write a client that hits your server and prints status + body.

## 12. Mini Project / Task

`urlshortener.go`: `POST /shorten {url}` → `{"short":"abc123"}`; `GET /{short}` → 302 redirect. Store in a map with mutex. Add GET `/list` returning all mappings as JSON.

## 13. Interview Questions

### Easy
- What is `http.HandlerFunc` vs `http.Handler`?
- How do you read a JSON body in a handler?

### Medium
- Why must you close `resp.Body`, and what leaks otherwise?
- What timeouts should a production server set, and what attacks do they mitigate?

### Hard
- How does Go's server schedule requests (goroutine per connection/request)?
- Explain connection reuse in the default transport and why draining the body matters.

## 14. Daily Practice Questions

### Easy
1. Serve JSON `{"status":"ok"}` on `/status`.
2. Read a query param `?name=x` and greet.
3. Return 404 with `http.Error` for unknown ids.
4. Make a GET request with a 5s timeout and print the status.
5. Print all request headers on `/headers`.

### Medium
6. Build `POST /sum` accepting `{"nums":[1,2,3]}` returning `{"sum":6}`.
7. Limit request body size with `http.MaxBytesReader`.
8. Implement basic rate limiting per IP (map + mutex).
9. Follow a redirect manually: disable `CheckRedirect` and print the chain.
10. Upload a file via `multipart` and save it server-side.

### Hard
11. Implement graceful shutdown: catch SIGINT, `srv.Shutdown(ctx)` with timeout.
12. Build a reverse proxy with `httputil.NewSingleHostReverseProxy`.
13. Write a middleware timing logger (preview Day 17) measuring request duration.
14. Implement a tiny load-balancer that round-robins between two upstream URLs.
15. Stream a large generated CSV response without buffering it fully (flusher pattern).

## 15. Solutions / Hints

- Q7: `r.Body = http.MaxBytesReader(w, r.Body, 1<<20)`.
- Q9 hint: `client.CheckRedirect = func(req *http.Request, via []*http.Request) error { return http.ErrUseLastResponse }`.
- Q11 hint: `signal.NotifyContext` + `srv.Shutdown(context.Background())` after draining.
- Q15 hint: type-assert `w.(http.Flusher)` and `Flush()` per row.

## 16. Day Summary

- One interface (`Handler`) powers the server; ServeMux routes (Go 1.22 method patterns).
- Client: explicit timeouts, close bodies, reuse the client.
- JSON in/out via `Encoder`/`Decoder` directly on streams.

## 17. What To Revise

- The handler interface; the client checklist (timeout, close, drain).

## 18. What Comes Tomorrow

**Day 16 — REST API**: a full CRUD service with proper status codes, validation, routing, and structure.
