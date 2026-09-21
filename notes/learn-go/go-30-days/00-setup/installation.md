# Day 0 — Setup: Installing Go and Your Development Environment

## Learning Objectives

- Install the Go toolchain on Windows, macOS, or Linux.
- Understand what `GOROOT`, `GOPATH`, and `GOBIN` are (and why you mostly don't need to configure them anymore).
- Set up VS Code (or GoLand) with the Go extension.
- Verify your installation with `go version` and your first `hello world`.

## Prerequisites

- A computer with at least 4 GB RAM.
- Basic familiarity with a terminal/command prompt.

## 1. Installing Go

### Windows

1. Download the MSI installer from https://go.dev/dl/
2. Run it. It installs Go to `C:\Program Files\Go` and adds `go` to your `PATH`.
3. Open a **new** terminal and run:

```powershell
go version
```

### macOS

Option A — installer: download the `.pkg` from https://go.dev/dl/ and run it (installs to `/usr/local/go`).

Option B — Homebrew:

```bash
brew install go
```

### Linux

```bash
# Remove any old install first
sudo rm -rf /usr/local/go

# Download and extract (check go.dev/dl for the latest version)
wget https://go.dev/dl/go1.22.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.22.5.linux-amd64.tar.gz

# Add to PATH (in ~/.bashrc or ~/.zshrc)
export PATH=$PATH:/usr/local/go/bin
```

## 2. Environment variables: GOROOT, GOPATH, GOBIN

Modern Go hides most of this from you, but you should know the terms:

| Variable | Meaning | Default |
|----------|---------|---------|
| `GOROOT` | Where Go itself is installed | Set automatically; don't touch |
| `GOPATH` | Where downloaded modules and built binaries live | `~/go` on Unix, `%USERPROFILE%\go` on Windows |
| `GOBIN` | Where `go install` puts executables | `$GOPATH/bin` |

Check yours:

```bash
go env GOPATH
go env GOROOT
```

Recommended: add `$GOPATH/bin` to your `PATH` so tools installed with `go install` are runnable:

```bash
export PATH=$PATH:$(go env GOPATH)/bin
```

## 3. Editor setup (VS Code)

1. Install VS Code.
2. Install the **Go** extension (golang.go).
3. Command Palette (`Ctrl+Shift+P`) → **Go: Install/Update Tools** → select all → OK. This installs `gopls` (language server), `dlv` (debugger), `staticcheck`, and more.
4. Recommended settings (`.vscode/settings.json`):

```json
{
  "editor.formatOnSave": true,
  "[go]": { "editor.defaultFormatter": "golang.go" },
  "go.useLanguageServer": true
}
```

GoLand (JetBrains) is a paid alternative that works out of the box.

## 4. The Go toolchain — commands you'll use daily

| Command | Purpose |
|---------|---------|
| `go run file.go` | Compile and run immediately |
| `go build` | Compile into a binary |
| `go mod init <module>` | Create a new module (project) |
| `go test ./...` | Run all tests |
| `go fmt ./...` | Format code canonically |
| `go vet ./...` | Static analysis / suspicious code detection |
| `go get <pkg>` | Add a dependency |
| `go install <pkg>` | Build and install a binary |
| `go doc fmt.Println` | Read documentation from the terminal |

## 5. Verify: your first program

Create a folder, then a file `main.go`:

```go
package main

import "fmt"

func main() {
	fmt.Println("Hello, Go!")
}
```

Run it:

```bash
go run main.go
# Hello, Go!
```

Note the **tab** indentation — `gofmt` (Go's formatter) enforces tabs, not spaces. With the VS Code Go extension, formatting happens automatically on save.

## Common Mistakes

- Running `go version` in an old terminal after install (PATH not refreshed) — open a new terminal.
- Editing `GOROOT` manually — never needed.
- Confusing `go run` (compile+run, no binary kept) with `go build` (produces a binary).

## Best Practices

- Always organize real code as a **module**: `go mod init github.com/yourname/projectname`.
- Let `gofmt` decide all formatting; never argue about tabs/braces in Go.
- Run `go vet ./...` before committing.

## Practical Exercise

1. Install Go and print `go version` output.
2. Create a module `hello` (`go mod init hello`), write the program above, run it with both `go run` and `go build`, and execute the produced binary.
3. Run `go env` and record your `GOPATH`.

## Mini Project / Task

Print your name and today's date using the `time` package:

```go
package main

import (
	"fmt"
	"time"
)

func main() {
	fmt.Println("Started learning Go on", time.Now().Format("2006-01-02"))
}
```

## Interview Questions

### Easy
- What is `GOPATH`? Is it still important?
- What does `go run` do vs `go build`?

### Medium
- What is `gopls` and why does your editor need it?
- What is the difference between `go get` and `go install` (post Go 1.17)?

### Hard
- How does Go produce static binaries, and why is that valuable for Docker/DevOps?
- Explain reproducible builds in Go modules (`go.sum`).

## Daily Practice Questions

### Easy
1. Print your Go version.
2. Create and run a hello-world module.
3. Print `go env GOPATH`.
4. Format any Go file with `gofmt -l .` and report the result.
5. Install the VS Code Go extension and its tools.

### Medium
6. Write a program that prints its own filename using `os.Args[0]`.
7. Build a binary and run it from a different directory.
8. Use `go doc fmt` to list the `fmt` package docs.
9. Add `$GOPATH/bin` to PATH and install a tool with `go install golang.org/x/tools/gopls@latest`.
10. Explain (in writing) the difference between `GOROOT` and `GOPATH`.

### Hard
11. Set up a project with a `Makefile` providing `make run`, `make build`, `make test` targets.
12. Cross-compile a Linux binary from your OS using `GOOS=linux GOARCH=amd64 go build`.
13. Configure `GOBIN` to a custom directory and verify `go install` respects it.
14. Use `go env -w` to persist a custom `GOPRIVATE` value; explain what it affects.
15. Write a shell script that fails if `gofmt -l .` output is non-empty (CI-style formatting check).

## Solutions / Hints

- Q12: `GOOS=linux GOARCH=amd64 go build -o app-linux main.go` — verify with `file app-linux`.
- Q15 hint: `test -z "$(gofmt -l .)"` in bash; exit non-zero otherwise.

## Day Summary

- Go installs as a single toolchain; `go version` verifies it.
- `GOROOT` = Go itself, `GOPATH` = module/download cache + installed binaries.
- Core commands: `run`, `build`, `test`, `fmt`, `vet`, `mod init`, `get`, `install`, `doc`.

## What To Revise

- The command table above — memorize `go mod init`, `go run`, `go test ./...`, `gofmt`.

## What Comes Tomorrow

**Day 1 — Go fundamentals**: what kind of language Go is, why it exists, and a deep look at your first real program, line by line.
