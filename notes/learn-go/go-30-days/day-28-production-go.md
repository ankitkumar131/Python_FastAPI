# Day 28 — Production Go

## Learning Objectives

- Containerize Go apps with multi-stage Docker builds (distroless, tiny images).
- Add structured logging (slog), metrics, and health checks.
- Manage configuration via environment (12-factor), validated at startup.
- Assemble the production checklist: graceful shutdown, signals, resource limits.

## Prerequisites

- Day 17 (architecture/shutdown); Day 15 (HTTP).

## 1. Concept Introduction

"Production Go" = everything around your code that makes it operable: packaging (multi-stage Docker → ~15 MB distroless images), observability (structured logs, metrics, health endpoints), configuration (env-based), and lifecycle (graceful shutdown, readiness vs liveness).

## 2. Why This Concept Exists

Static binaries make Go ops-friendly, but a binary alone isn't a service. Kubernetes sends SIGTERM and expects graceful exits; SREs need logs and metrics; security teams want minimal images. The stdlib (`log/slog`) plus small conventions cover most of it without heavy frameworks.

## 3. Syntax

```dockerfile
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app ./cmd/api

FROM gcr.io/distroless/static-debian12
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
slog.SetDefault(logger)
slog.Info("request handled", "method", r.Method, "dur", elapsed)
```

## 4. Detailed Explanation

- **Multi-stage builds**: the build stage has the toolchain (~1 GB); the final stage copies only the static binary. `CGO_ENABLED=0` guarantees static linking (works on distroless/scratch). `-ldflags="-s -w"` strips debug info. Result: 10–20 MB images.
- **`log/slog`** (Go 1.21+): structured, leveled logging in stdlib; key-value pairs → parseable JSON in prod. Pass loggers via dependency injection.
- **Metrics**: Prometheus format via `prometheus/client_golang` at `/metrics` — Rate, Errors, Duration per endpoint.
- **Health**: `/healthz` (liveness: process alive?) vs `/readyz` (readiness: dependencies OK?). Never make liveness depend on flapping dependencies.
- **Config**: flags > env > file > defaults; validate at startup, fail fast.
- **Non-root + read-only**: distroless runs as non-root; pair with read-only filesystems.

## 5. Example 1 — Production-ready server skeleton

```go
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		// check dependencies; return 503 while starting up
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ready"))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		defer func() {
			slog.Info("request", "method", r.Method, "path", r.URL.Path,
				"dur_ms", time.Since(start).Milliseconds())
		}()
		w.Write([]byte("hello"))
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
		slog.Info("listening", "port", port)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("server", "err", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	slog.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		slog.Error("forced shutdown", "err", err)
	}
}
```

## 6. Example 2 — Build, containerize, verify

```bash
CGO_ENABLED=0 go build -ldflags="-s -w -X main.version=$(git describe --tags)" -o app ./cmd/api

docker build -t myapi:1.0.0 .
docker images myapi          # ~15 MB
docker run --rm -p 8080:8080 --read-only myapi:1.0.0
curl localhost:8080/healthz
docker logs -f <container>   # JSON logs streaming
```

## 7. Real-World Example — Kubernetes deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapi
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: myapi
          image: myapi:1.0.0
          ports: [{ containerPort: 8080 }]
          env: [{ name: PORT, value: "8080" }]
          resources:
            requests: { cpu: 100m, memory: 64Mi }
            limits: { cpu: 500m, memory: 128Mi }
          livenessProbe:
            httpGet: { path: /healthz, port: 8080 }
          readinessProbe:
            httpGet: { path: /readyz, port: 8080 }
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
```

Your Go app needs nothing special for k8s — SIGTERM handling, health endpoints, and env config cover the contract.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Single-stage Dockerfile | Ships a 1 GB build image to production |
| Logs to files inside the container | Log to stdout; the platform collects |
| `latest` image tags | Non-reproducible deploys; tag with versions |
| Readiness = liveness = always 200 | Broken instances keep receiving traffic |
| No graceful shutdown | Every deploy drops in-flight requests |
| Ignoring GOMEMLIMIT in containers | OOMKilled on memory spikes |

## 9. Best Practices

- Distroless/scratch final images, non-root, read-only fs.
- Structured JSON logs with request IDs.
- `/metrics`, `/healthz`, `/readyz` from day one.
- Version via ldflags; log it at startup.
- Set `GOMEMLIMIT` slightly below the container memory limit.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | Node |
|--------|----|------|--------|------|
| Image size | ~15 MB | ~200+ MB | ~150 MB | ~150 MB |
| Structured logging | slog (stdlib) | logback config | structlog | pino |
| Deployment unit | 1 static binary | jar + JRE | venv + code | node_modules |

## 11. Practical Exercise

1. Build your Day 16 API with a multi-stage Dockerfile; check image size.
2. Add slog JSON logging with request duration.
3. Add `/readyz` checking a dependency, returning 503 when down.

## 12. Mini Project / Task

Productionize the tasks API: distroless Dockerfile, version endpoint via ldflags, JSON logs with request IDs, graceful shutdown, health/readiness, env config, k8s manifest. Deploy locally with `kind` or `docker compose`.

## 13. Interview Questions

### Easy
- Why multi-stage Docker builds?
- stdout vs file logging in containers?

### Medium
- Liveness vs readiness probes?
- What does `CGO_ENABLED=0` change?

### Hard
- Design a zero-downtime deploy: app and platform responsibilities.
- GOMEMLIMIT/GOGC in memory-constrained containers?

## 14. Daily Practice Questions

### Easy
1. Multi-stage Dockerfile for any Go binary; report the final size.
2. `GET /version` printing an ldflags-injected version.
3. Log one JSON line with slog including a duration.
4. `/healthz` returning 200.
5. Run the container with `--read-only`; fix what breaks.

### Medium
6. Request-ID middleware included in all log lines.
7. Readiness returning 503 until a fake dependency check passes.
8. Graceful shutdown test: slow request + SIGTERM → verify completion.
9. Compose the app with Postgres; wait-for-ready before starting.
10. Set GOMEMLIMIT and observe GC behavior under load.

### Hard
11. Zero-downtime rolling deploy with readiness gates.
12. Prometheus metrics (request count/duration) and scraping.
13. Ship to `FROM scratch` — what breaks (certs, tzdata) and why?
14. OpenTelemetry tracing spans around handlers.
15. Smoke-test script validating a fresh deployment end-to-end.

## 15. Solutions / Hints

- Q8 hint: shutdown waits for in-flight requests; verify via logs.
- Q13 hint: scratch lacks CA certificates — copy them in, or use distroless.
- Q14 hint: `go.opentelemetry.io/otel` + middleware wrapping `r.Context()`.

## 16. Day Summary

- Multi-stage + distroless = tiny, secure images from static binaries.
- slog + /metrics + /healthz + /readyz = observable, orchestratable services.
- Graceful shutdown + env config = platform-friendly lifecycle.

## 17. What To Revise

- The Dockerfile skeleton; probe semantics.

## 18. What Comes Tomorrow

**Day 29 — Capstone project**: build a complete production-style URL shortener service tying together everything from Days 1–28.
