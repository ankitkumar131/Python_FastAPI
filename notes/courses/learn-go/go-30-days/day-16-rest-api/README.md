# Day 16 — REST API

## Learning Objectives

- Build a complete CRUD REST API: routes, status codes, validation, JSON errors.
- Structure handlers → service → store separation.
- Understand REST conventions and idempotency.
- Test the API with `curl` and in-process tests.

## Prerequisites

- Days 14–15 (JSON, HTTP).

## 1. Concept Introduction

REST = resources addressed by URLs, manipulated via HTTP verbs:

| Verb | Path | Meaning | Success status |
|------|------|---------|----------------|
| GET | /tasks | list | 200 |
| POST | /tasks | create | 201 (+Location) |
| GET | /tasks/{id} | read | 200 / 404 |
| PUT | /tasks/{id} | full update | 200 / 404 |
| PATCH | /tasks/{id} | partial update | 200 / 404 |
| DELETE | /tasks/{id} | delete | 204 / 404 |

Today we build the whole thing with only the standard library.

## 2. Why This Concept Exists

REST won because it maps cleanly onto HTTP semantics that caches, proxies, and load balancers already understand. Verbs are meaningful (GET is safe, PUT/DELETE are idempotent), which lets infrastructure reason about retries. Learning to build one *properly* — correct status codes, consistent error bodies, validation — is 80% of backend Go work.

## 3. Syntax — project shape

```text
tasksapi/
├── go.mod
├── main.go
└── internal/
    ├── api/       handlers (transport)
    ├── task/      service + domain types + validation
    └── store/     in-memory store (swap for DB on Day 18)
```

Error JSON contract (consistent everywhere):

```json
{ "error": { "code": "not_found", "message": "task 42 not found" } }
```

## 4. Detailed Explanation

- **Handlers**: parse/validate input, call the service, write the response. No business logic here.
- **Service**: domain rules (e.g., "title required", "cannot complete an archived task"). Returns domain errors.
- **Store**: persistence. An interface (`TaskStore`) lets us start in-memory and swap Postgres later without touching handlers — interfaces doing their job (Day 10).
- **Status codes matter**: 400 (client sent garbage), 404 (missing), 409 (conflict), 422 (valid JSON, invalid semantics), 500 (our bug). Clients build retry logic around them.
- **Idempotency**: PUT with the same body twice = same result; POST is not idempotent (two creates).

## 5. Example 1 — Domain + store

```go
// internal/task/task.go
package task

import (
	"errors"
	"strings"
	"time"
)

var (
	ErrNotFound  = errors.New("task not found")
	ErrInvalid   = errors.New("invalid task")
	ErrDuplicate = errors.New("duplicate task")
)

type Task struct {
	ID        int       `json:"id"`
	Title     string    `json:"title"`
	Done      bool      `json:"done"`
	CreatedAt time.Time `json:"created_at"`
}

// Validate returns a per-field problem description, or "".
func (t Task) Validate() string {
	if strings.TrimSpace(t.Title) == "" {
		return "title is required"
	}
	if len(t.Title) > 100 {
		return "title must be at most 100 chars"
	}
	return ""
}
```

```go
// internal/store/memory.go
package store

import (
	"sync"

	"tasksapi/internal/task"
)

// Memory is a thread-safe in-memory TaskStore.
type Memory struct {
	mu    sync.RWMutex
	seq   int
	tasks map[int]task.Task
}

func NewMemory() *Memory {
	return &Memory{tasks: make(map[int]task.Task)}
}

func (m *Memory) List() []task.Task {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]task.Task, 0, len(m.tasks))
	for _, t := range m.tasks {
		out = append(out, t)
	}
	return out
}

func (m *Memory) Get(id int) (task.Task, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	t, ok := m.tasks[id]
	if !ok {
		return task.Task{}, task.ErrNotFound
	}
	return t, nil
}

func (m *Memory) Create(t task.Task) (task.Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.seq++
	t.ID = m.seq
	t.CreatedAt = time.Now().UTC()
	m.tasks[t.ID] = t
	return t, nil
}

func (m *Memory) Update(t task.Task) (task.Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.tasks[t.ID]; !ok {
		return task.Task{}, task.ErrNotFound
	}
	m.tasks[t.ID] = t
	return t, nil
}

func (m *Memory) Delete(id int) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.tasks[id]; !ok {
		return task.ErrNotFound
	}
	delete(m.tasks, id)
	return nil
}
```

Note: `sync.RWMutex` (Day 23 preview) — many readers, exclusive writers. A map alone is not concurrency-safe.

## 6. Example 2 — Handlers with proper status codes

```go
// internal/api/handlers.go
package api

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"tasksapi/internal/store"
	"tasksapi/internal/task"
)

type Handler struct {
	Store *store.Memory
}

func NewRouter(h *Handler) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /tasks", h.list)
	mux.HandleFunc("POST /tasks", h.create)
	mux.HandleFunc("GET /tasks/{id}", h.get)
	mux.HandleFunc("PUT /tasks/{id}", h.update)
	mux.HandleFunc("DELETE /tasks/{id}", h.delete)
	return mux
}

// writeError emits our consistent error envelope.
func writeError(w http.ResponseWriter, status int, code, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(map[string]any{
		"error": map[string]string{"code": code, "message": msg},
	})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func pathID(r *http.Request) (int, error) {
	return strconv.Atoi(r.PathValue("id"))
}

func (h *Handler) list(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, h.Store.List())
}

func (h *Handler) create(w http.ResponseWriter, r *http.Request) {
	var in task.Task
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "bad_json", err.Error())
		return
	}
	if msg := in.Validate(); msg != "" {
		writeError(w, http.StatusUnprocessableEntity, "invalid", msg)
		return
	}
	created, err := h.Store.Create(in)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal", err.Error())
		return
	}
	w.Header().Set("Location", "/tasks/"+strconv.Itoa(created.ID))
	writeJSON(w, http.StatusCreated, created)
}

func (h *Handler) get(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_id", "id must be an integer")
		return
	}
	t, err := h.Store.Get(id)
	if errors.Is(err, task.ErrNotFound) {
		writeError(w, http.StatusNotFound, "not_found", "task not found")
		return
	}
	writeJSON(w, http.StatusOK, t)
}

func (h *Handler) update(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_id", "id must be an integer")
		return
	}
	var in task.Task
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "bad_json", err.Error())
		return
	}
	in.ID = id
	if msg := in.Validate(); msg != "" {
		writeError(w, http.StatusUnprocessableEntity, "invalid", msg)
		return
	}
	updated, err := h.Store.Update(in)
	if errors.Is(err, task.ErrNotFound) {
		writeError(w, http.StatusNotFound, "not_found", "task not found")
		return
	}
	writeJSON(w, http.StatusOK, updated)
}

func (h *Handler) delete(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_id", "id must be an integer")
		return
	}
	if err := h.Store.Delete(id); errors.Is(err, task.ErrNotFound) {
		writeError(w, http.StatusNotFound, "not_found", "task not found")
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
```

`main.go`:

```go
package main

import (
	"log"
	"net/http"
	"time"

	"tasksapi/internal/api"
	"tasksapi/internal/store"
)

func main() {
	h := &api.Handler{Store: store.NewMemory()}

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           api.NewRouter(h),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Println("tasks API on :8080")
	log.Fatal(srv.ListenAndServe())
}
```

## 7. Real-World Example — exercise it with curl

```bash
# create
curl -s -X POST localhost:8080/tasks -d '{"title":"learn REST"}'
# {"id":1,"title":"learn REST","done":false,"created_at":"2026-09-21T12:00:00Z"}

# list
curl -s localhost:8080/tasks

# get one
curl -s localhost:8080/tasks/1

# full update
curl -s -X PUT localhost:8080/tasks/1 -d '{"title":"learn REST deeply","done":true}'

# delete
curl -s -X DELETE -i localhost:8080/tasks/1 | head -1
# HTTP/1.1 204 No Content

# error shape
curl -s localhost:8080/tasks/999
# {"error":{"code":"not_found","message":"task not found"}}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Returning 200 for everything | Clients can't distinguish success classes; caches misbehave |
| Business logic in handlers | Untestable, duplicated; keep handlers thin |
| Sharing the domain struct for input AND output | Leaks fields (e.g., clients setting `id`, `created_at`) — use input DTOs |
| In-memory store without mutex | Data race under concurrent requests — guaranteed crash on the race detector |
| No 404 distinction from 400 | 404 = missing resource; 400 = malformed request |
| Missing `Content-Type` header | Clients misparse responses |

## 9. Best Practices

- Consistent error envelope for every failure.
- Validate at the edge (handler) AND in the service (defense in depth).
- Design store as an interface from day one — DB swap becomes trivial (Day 18).
- Write in-process tests using `httptest` (Day 20 covers this fully).

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Spring Boot | FastAPI | Express |
|--------|----|-------------|---------|---------|
| Routing | stdlib patterns | annotations | decorators | strings |
| Serialization | struct tags | Jackson | pydantic | manual/middleware |
| Validation | manual/libraries | Bean Validation | pydantic | libraries |
| DI | constructor params | Spring container | Depends() | manual |

## 11. Practical Exercise

1. Add `PATCH /tasks/{id}` supporting partial updates using pointer fields.
2. Add a `GET /tasks?done=true` filter reading query params.
3. Add 405 handling verification — try `DELETE /tasks` and observe ServeMux's response.

## 12. Mini Project / Task

Extend the API into `notes` (title, body, tags): add tag filtering (`?tag=go`), a `POST /notes/{id}/tags` to append tags, and pagination (`?limit=10&offset=0`) with a `X-Total-Count` header.

## 13. Interview Questions

### Easy
- What status code for successful creation? For deletion?
- GET vs PUT semantics?

### Medium
- Why separate handler/service/store layers?
- 400 vs 404 vs 422 — when?

### Hard
- How would you make POST idempotent (Idempotency-Key pattern)?
- How does the in-memory store design change when moving to Postgres? What stays the same?

## 14. Daily Practice Questions

### Easy
1. Serve a fixed task list on GET /tasks.
2. Return 201 with a Location header on create.
3. Return your consistent error JSON for a bad id.
4. Add DELETE returning 204.
5. Parse `?limit=` and echo it back.

### Medium
6. Implement PUT semantics: replace the whole task or 404.
7. Implement validation with per-field error messages.
8. Add `GET /tasks/stats` returning counts by done/undone.
9. Sort list output by a `?sort=title|created` query param.
10. Add basic auth middleware checking a fixed token (preview Day 17).

### Hard
11. Implement ETag-based optimistic concurrency on PUT (If-Match).
12. Add pagination with cursor tokens instead of offsets.
13. Make POST idempotent using an Idempotency-Key header with a keyed store.
14. Write in-process tests for all endpoints using httptest (no network).
15. Swap the memory store for a file-backed JSON store implementing the same behavior — no handler changes.

## 15. Solutions / Hints

- Q1 hint: partial update struct `type patch struct{ Title *string; Done *bool }`.
- Q11 hint: compute `hash(body)`; compare with `If-Match`; return 412 Precondition Failed on mismatch.
- Q12 hint: cursor = base64 of last id; `LIMIT` in SQL later.
- Q14 hint: `srv := httptest.NewServer(api.NewRouter(h)); defer srv.Close()` then hit `srv.URL`.

## 16. Day Summary

- REST = resources + verbs + meaningful status codes.
- Layered design: thin handlers, domain service, swappable store behind an interface.
- Thread-safe stores are mandatory — the server is concurrent by default.

## 17. What To Revise

- The verb/status table; the error envelope.

## 18. What Comes Tomorrow

**Day 17 — API architecture**: middleware, routing at scale, dependency injection, config, and project structure for services that grow.
