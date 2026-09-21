# Day 25 — CLI Development

## Learning Objectives

- Parse flags with the stdlib `flag` package; design multi-command CLIs.
- Read stdin, write stdout/stderr with proper exit codes.
- Structure a professional CLI: help text, subcommands, env config.
- Know when to reach for cobra/urfave-cli.

## Prerequisites

- Day 15 HTTP (clients); Day 13 files.

## 1. Concept Introduction

Go is *the* language for CLIs: single static binary, fast startup, first-class stdlib (`flag`, `os`, `bufio`, `fmt`). Every Go tool you use — `go` itself, `kubectl`, `terraform`, `gh` — is structured the same way: parse args → dispatch to a command → run → exit with a meaningful code.

## 2. Why This Concept Exists

DevOps and cloud tooling needs installable-anywhere binaries. Go's cross-compilation (`GOOS=linux go build`) plus zero runtime deps means CLIs ship as one file per platform. The stdlib's `flag` covers simple tools; the subcommand pattern (like `git`/`go` themselves) covers complex ones — you'll build both today.

## 3. Syntax

```go
flags := flag.NewFlagSet("serve", flag.ExitOnError)
port := flags.Int("port", 8080, "listen port")
verbose := flags.Bool("v", false, "verbose output")
flags.Parse(os.Args[2:]) // after the subcommand

fmt.Fprintln(os.Stderr, "error: ...") // errors → stderr
os.Exit(1)                             // non-zero = failure
```

Stdin streaming:

```go
sc := bufio.NewScanner(os.Stdin)
for sc.Scan() { process(sc.Text()) }
```

## 4. Detailed Explanation

- **Exit codes**: 0 = success; non-zero = failure. Scripts and CI depend on this. `flag.ExitOnError` exits 2 on parse errors automatically.
- **stderr vs stdout**: results → stdout (pipe-able); diagnostics → stderr. `grep`-ability requires this discipline.
- **Subcommand dispatch**: `os.Args[1]` selects the command; each command gets its own `FlagSet` so flags are per-command (like `go build -o`, `go test -run`).
- **Flags after positionals**: stdlib `flag` stops at the first non-flag argument — for `tool file.txt -v` you need manual handling or a library. Design flags-first.
- **Libraries**: `spf13/cobra` (used by kubectl, gh) and `urfave/cli` add help generation, nested subcommands, completions. Learn stdlib first — cobra is the same pattern with more scaffolding.

## 5. Example 1 — Multi-command CLI with stdlib

```go
package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}

	switch cmd := os.Args[1]; cmd {
	case "greet":
		fs := flag.NewFlagSet("greet", flag.ExitOnError)
		name := fs.String("name", "world", "who to greet")
		upper := fs.Bool("upper", false, "shout it")
		_ = fs.Parse(os.Args[2:])

		msg := fmt.Sprintf("hello, %s!", *name)
		if *upper {
			msg = strings.ToUpper(msg)
		}
		fmt.Println(msg)

	case "sum":
		fs := flag.NewFlagSet("sum", flag.ExitOnError)
		_ = fs.Parse(os.Args[2:])
		total := 0
		for _, arg := range fs.Args() { // positional args
			var n int
			if _, err := fmt.Sscanf(arg, "%d", &n); err != nil {
				fmt.Fprintf(os.Stderr, "sum: %q is not a number\n", arg)
				os.Exit(1)
			}
			total += n
		}
		fmt.Println(total)

	case "help", "-h", "--help":
		usage()

	default:
		fmt.Fprintf(os.Stderr, "unknown command %q\n\n", cmd)
		usage()
		os.Exit(2)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, `usage: mytool <command> [flags]

commands:
  greet   print a greeting   flags: -name, -upper
  sum     sum integers       args: numbers
  help    show this help`)
}
```

```bash
go run . greet -name Ada -upper
# HELLO, ADA!
go run . sum 1 2 3
# 6
```

## 6. Example 2 — Unix-style filter reading stdin

```go
package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// Usage: cat file.log | greperr
// or:    greperr < file.log
func main() {
	sc := bufio.NewScanner(os.Stdin)
	lineNo := 0
	for sc.Scan() {
		lineNo++
		if strings.Contains(sc.Text(), "ERROR") {
			fmt.Printf("%d: %s\n", lineNo, sc.Text()) // matches → stdout
		}
	}
	if err := sc.Err(); err != nil {
		fmt.Fprintln(os.Stderr, "read error:", err) // diagnostics → stderr
		os.Exit(1)
	}
}
```

Test the composability — the Unix philosophy payoff:

```bash
cat app.log | greperr | wc -l
```

## 7. Real-World Example

A polished tool with env fallbacks and version flag — the pattern real CLIs ship with:

```go
package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"
)

var version = "dev" // set via -ldflags "-X main.version=1.2.3" at build time

func main() {
	// precedence: flag > env > default
	defaultPort, _ := strconv.Atoi(orEnv("MYTOOL_PORT", "8080"))

	showVersion := flag.Bool("version", false, "print version and exit")
	port := flag.Int("port", defaultPort, "port (env MYTOOL_PORT)")
	flag.Parse()

	if *showVersion {
		fmt.Println("mytool", version)
		return
	}
	fmt.Printf("serving on :%d (v%s)\n", *port, version)
}

func orEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
```

Build with version injection: `go build -ldflags "-X main.version=1.0.0" -o mytool`

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Diagnostics to stdout | Breaks piping; errors go to stderr |
| Exit code 0 on failure | CI reports success wrongly |
| Global flags mixed per-command | Use one FlagSet per subcommand |
| Ignoring flag parse errors | Use `flag.ExitOnError` or handle explicitly |
| No help text | CLIs are their own docs; usage() is mandatory |
| Hardcoding config | Flags + env + files, in that precedence |

## 9. Best Practices

- Flags first, positionals after; document both in usage.
- Support `-h/--help` and `--version`.
- Stream stdin/stdout — never buffer unbounded input.
- Keep commands thin: parse → call a library function → print.
- Cross-compile and test on all target platforms.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java (picocli) | Python (argparse) | Node (commander) |
|--------|----|----------------|-------------------|------------------|
| Distribution | one static binary | JRE + jar | interpreter + deps | node_modules |
| Startup | ~ms | ~100s of ms | ~50ms | ~50ms |
| Subcommands | manual/flag sets | annotations | subparsers | .command() |
| Exit codes | os.Exit | System.exit | sys.exit | process.exit |

## 11. Practical Exercise

1. Extend the multi-command tool with a `count` command counting lines from stdin.
2. Add `-v/--verbose` logging to stderr.
3. Add a `version` subcommand with ldflags injection.

## 12. Mini Project / Task

`todoctl`: a task CLI with subcommands `add <title>`, `list [--done]`, `done <id>`, `rm <id>`, persisting to `~/.todo.json` (JSON + file handling + CLI in one). Include help, exit codes, and stderr errors.

## 13. Interview Questions

### Easy
- stdout vs stderr — what belongs where?
- What exit code should a failing CLI return?

### Medium
- How does stdlib `flag` handle `cmd -flag positional`? What's the limitation?
- How do you inject the version at build time?

### Hard
- Design a CLI framework from scratch: how would FlagSets dispatch and compose help text?
- When do cobra's features (completions, nested subcommands) justify the dependency over stdlib?

## 14. Daily Practice Questions

### Easy
1. Print `--help` when run with no args, exit 2.
2. Accept `-n` count flag and print n stars.
3. Read a file argument; error to stderr if missing, exit 1.
4. Print version with a `--version` flag.
5. Read all of stdin and print it uppercased.

### Medium
6. Two subcommands with separate FlagSets.
7. Grep-like tool: pattern flag + stdin, print matching lines.
8. Support env-var fallbacks for two flags.
9. Word-count tool (`wc` clone): lines, words, bytes.
10. Composable pipeline: write a tool that reads JSON lines and outputs CSV.

### Hard
11. Build a `todoctl` with file persistence and atomic saves (Day 13).
12. Add shell tab-completion output for bash (emit a completion script).
13. Implement a progress bar on stderr while processing stdin (carriage-return updates).
14. Write integration tests executing the built binary via `os/exec` and asserting exit codes/output.
15. Cross-compile your CLI for linux/darwin/windows in a build script with version injection.

## 15. Solutions / Hints

- Q9 hint: count via scanner; words via `strings.Fields`; bytes via `os.Stat` or accumulated len.
- Q12 hint: emit a bash function listing subcommands for `complete -W`.
- Q14 hint: `cmd := exec.Command(bin, args...); out, _ := cmd.Output(); cmd.Run()` and check `cmd.ProcessState.ExitCode()`.

## 16. Day Summary

- `flag` + FlagSets + subcommand switch = stdlib CLI.
- stdout = data, stderr = diagnostics, exit codes = contract.
- Env fallbacks + ldflags versioning = production polish.

## 17. What To Revise

- The precedence rule (flag > env > default); exit-code conventions.

## 18. What Comes Tomorrow

**Day 26 — Advanced Go**: reflection, unsafe, cgo, embed, and the deep-runtime features you'll meet in frameworks.
