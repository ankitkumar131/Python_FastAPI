# Day 12 — Packages and Modules

## Learning Objectives

- Organize a project into packages; understand import paths and visibility.
- Master `go.mod`, semantic versioning, and dependency management.
- Use `internal/` to enforce privacy at module level.
- Structure a realistic multi-package Go service.

## Prerequisites

- Day 11.

## 1. Concept Introduction

- **Package** = a directory of Go files compiled together, sharing one namespace. The unit of compilation and privacy.
- **Module** = a versioned collection of packages, defined by `go.mod` at the root. The unit of dependency management.

```text
myapp/                 ← module root (go.mod lives here)
├── go.mod
├── main.go            ← package main
├── internal/
│   └── auth/          ← importable only within myapp
│       └── auth.go    ← package auth
└── pkg/
    └── strutil/       ← importable by anyone
        └── strutil.go
```

## 2. Why This Concept Exists

Go needed reproducible, fast dependency management for huge codebases. Modules (Go 1.13+, default 1.16+) solved the old GOPATH chaos: any directory can be a module, versions come from Git tags (semver), and `go.sum` locks exact content hashes — reproducible builds by default. Packages enforce encapsulation at compile time: lowercase = private to the package, with no reflection-free way around it.

## 3. Syntax

```bash
go mod init github.com/you/myapp   # create module
go get github.com/google/uuid      # add dependency
go get github.com/google/uuid@v1.6.0
go mod tidy                        # add missing / remove unused
go list -m all                     # show dependency tree
```

```go
import (
	"fmt"                                        // stdlib
	"github.com/google/uuid"                     // external
	"github.com/you/myapp/internal/auth"         // your own package
)
```

Visibility: identifiers starting with an **uppercase** letter are exported; lowercase are package-private. There is no `public/private/protected` keyword.

## 4. Detailed Explanation

- **Import paths = URLs-ish names**, not file paths relative to anything. The compiler maps `github.com/you/myapp/internal/auth` to the `internal/auth` directory via `go.mod`.
- **`internal/` rule**: code under `internal/` can only be imported by packages rooted at the parent of `internal/`. This is enforced by the toolchain — the standard way to hide implementation.
- **Cyclic imports are compile errors** — forcing layered architecture (this is a feature).
- **`package main` + `func main`** = one executable per module (you can have several, in subdirectories).
- **Semver**: `vX.Y.Z`. Modules v2+ need a `/v2` suffix in the import path. Unversioned clones act as `v0`/`v1` pseudo-versions.
- **Package naming**: short, lowercase, singular, no underscores (`strutil`, `auth`, not `stringUtils_pkg`).

## 5. Example 1 — A multi-package module

```bash
mkdir myapp && cd myapp
go mod init github.com/you/myapp
mkdir -p internal/strutil
```

`internal/strutil/strutil.go`:

```go
package strutil

import "strings"

// Reverse is exported (capital R).
func Reverse(s string) string {
	r := []rune(s)
	for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
		r[i], r[j] = r[j], r[i]
	}
	return string(r)
}

// normalize is private — usable only inside package strutil.
func normalize(s string) string {
	return strings.ToLower(strings.TrimSpace(s))
}

// Slug exports behavior that uses the private helper.
func Slug(s string) string {
	return strings.ReplaceAll(normalize(s), " ", "-")
}
```

`main.go`:

```go
package main

import (
	"fmt"

	"github.com/you/myapp/internal/strutil"
)

func main() {
	fmt.Println(strutil.Reverse("hello")) // olleh
	fmt.Println(strutil.Slug("  Go Is Fun ")) // go-is-fun
	// fmt.Println(strutil.normalize("x")) // compile error: unexported
}
```

## 6. Example 2 — Using a third-party dependency

```bash
go get github.com/google/uuid
```

```go
package main

import (
	"fmt"

	"github.com/google/uuid"
)

func main() {
	id := uuid.New()
	fmt.Println(id.String())
}
```

`go.mod` now records `require github.com/google/uuid v1.6.0` and `go.sum` pins its hashes. Commit both files — that's your reproducible build.

## 7. Real-World Example — production layout

```text
shopapi/
├── go.mod                    module shopapi
├── cmd/
│   └── api/main.go           thin entry point
├── internal/
│   ├── handler/              HTTP handlers (transport layer)
│   ├── service/              business logic
│   ├── repository/           data access
│   └── models/               shared types
├── pkg/                      (optional) code safe for others to import
└── migrations/               SQL files
```

`cmd/api/main.go` stays tiny — it wires dependencies:

```go
package main

import (
	"log"
	"net/http"

	"shopapi/internal/handler"
	"shopapi/internal/repository"
	"shopapi/internal/service"
)

func main() {
	repo := repository.NewUserRepo()
	svc := service.NewUserService(repo)
	h := handler.NewUserHandler(svc)

	log.Fatal(http.ListenAndServe(":8080", h.Routes()))
}
```

Dependency direction: handler → service → repository. Import cycles are impossible if you respect the layers.

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| One giant `main` package | Split by responsibility; keep `main` thin |
| Import cycles | Restructure: extract shared types to a lower package |
| Forgetting `go mod tidy` | Broken/unused deps in `go.mod` |
| `utils` grab-bag packages | Name packages by what they provide, not "misc" |
| Committing without `go.sum` | Non-reproducible builds |
| Assuming `pkg/` is required | It's a convention, not a rule; `internal/` is the enforced one |

## 9. Best Practices

- Start every project with `go mod init <repo-url>`.
- Keep `main.go` minimal; put logic under `internal/`.
- Run `go mod tidy` and `go vet ./...` before every commit.
- Use `internal/` aggressively — public surface is an API commitment.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript |
|--------|----|------|--------|-----------|
| Unit | package (dir) | package/jar | module | module/npm pkg |
| Manifest | go.mod | pom.xml/build.gradle | pyproject.toml | package.json |
| Lockfile | go.sum | gradle lock | poetry.lock | package-lock.json |
| Privacy | capitalized = exported | keywords | `_` convention | none/enforced via exports |
| Circular imports | Error | Error | Allowed (dangerous) | Allowed (cycle bugs) |

## 11. Practical Exercise

1. Create a module with `internal/mathx` exposing `Add`, `Max`; call from `main`.
2. Try importing an unexported function; read the compiler error.
3. Add `github.com/google/uuid`, use it, run `go mod tidy`, inspect `go.mod`/`go.sum`.

## 12. Mini Project / Task

Restructure your Day 11 validator into a module: `internal/validate` (logic), `internal/models` (types), `cmd/app/main.go` (CLI). Ensure `go build ./...` works and no import cycles exist.

## 13. Interview Questions

### Easy
- Difference between a package and a module?
- How does Go mark something as exported?

### Medium
- What does `internal/` enforce and how?
- What do `go.mod` and `go.sum` each contain?

### Hard
- How do you consume v2+ of a module, and why the path suffix?
- Explain how minimal version selection (MVS) picks dependency versions.

## 14. Daily Practice Questions

### Easy
1. `go mod init` a project and print its `go.mod`.
2. Create two packages; import one from the other.
3. Use `go list ./...` to list your packages.
4. Make a private function and prove it's not importable.
5. Run `go mod tidy` and note what changed.

### Medium
6. Add two external deps; print `go list -m all`.
7. Build a `cmd/server` + `internal/` layout that compiles.
8. Vendor dependencies with `go mod vendor`; explain when you'd commit it.
9. Downgrade a dependency to a specific version with `go get pkg@vX.Y.Z`.
10. Create a package with an `init()` function; explain when it runs (and why to avoid it).

### Hard
11. Create a multi-module workspace with `go.work` spanning two modules.
12. Publish flow dry-run: tag a module v1.0.0 and fetch it from a local path with a `replace` directive.
13. Explain and demonstrate MVS by requiring two modules with a shared dependency.
14. Set up `GOPRIVATE`/`GONOSUMDB` for a private module path.
15. Refactor a package that caused an import cycle into three acyclic packages; document the dependency direction.

## 15. Solutions / Hints

- Q8: `go mod vendor` copies deps into `vendor/` — useful for hermetic CI builds.
- Q11: `go work init ./moduleA ./moduleB` lets local modules reference each other without publishing.
- Q12 hint: `replace github.com/you/x => ../x` for local dev.

## 16. Day Summary

- Package = directory + namespace + privacy boundary (capitalization).
- Module = versioned unit with `go.mod`/`go.sum`; MVS resolves versions.
- `internal/` hides code; layered layout prevents cycles.

## 17. What To Revise

- The production layout tree; visibility rules.

## 18. What Comes Tomorrow

**Day 13 — File handling**: reading/writing files, `bufio` scanning, directory walking, and safe error handling on real filesystems.
