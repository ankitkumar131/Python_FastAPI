# Day 13 — File Handling

## Learning Objectives

- Read and write files with `os` and `io`; choose whole-file vs streaming approaches.
- Use `bufio.Scanner` for line-by-line processing.
- Walk directories, check metadata, and build a real file-processing tool.
- Handle file errors correctly (EOF, not-exist, permissions).

## Prerequisites

- Day 11 error handling; Day 5 slices.

## 1. Concept Introduction

Go's file I/O centers on three ideas:

- `os.File` — an open file descriptor implementing `io.Reader`/`io.Writer`/`io.Closer`.
- `io` interfaces — most functions accept `io.Reader`/`io.Writer`, so the same code works on files, buffers, and network connections.
- `bufio` — buffered wrappers making line/token reads efficient.

## 2. Why This Concept Exists

Files are the lowest common denominator of computing: logs, configs, CSVs, images. Go's abstraction (small `io` interfaces) means you learn ONE reading API and can plug it into files, HTTP bodies, stdin, and in-memory buffers interchangeably. `defer file.Close()` (Day 4) makes resource cleanup nearly impossible to forget.

## 3. Syntax

```go
data, err := os.ReadFile("a.txt")          // whole small file (Go 1.16+)
err := os.WriteFile("a.txt", data, 0644)   // whole write

f, err := os.Open("big.log")               // streaming read
defer f.Close()

out, err := os.Create("out.txt")           // truncate/create for writing
defer out.Close()

scanner := bufio.NewScanner(f)             // line-by-line
for scanner.Scan() {
	line := scanner.Text()
}
if err := scanner.Err(); err != nil { }    // don't forget scanner's error!
```

## 4. Detailed Explanation

- **Whole-file vs streaming**: `ReadFile` is fine up to tens of MB; anything bigger or unbounded (logs!) must stream with a fixed buffer. `os.ReadFile` on a 10 GB file will exhaust memory.
- **`bufio.Scanner`** splits on lines by default (customizable via `SplitFunc`); default max token is 64 KB per line — extremely long lines need a bigger `Buffer`.
- **Permissions**: `os.WriteFile(path, data, 0644)` — mode applies only when creating; Unix-style octal. `0644` = owner rw, others r.
- **Error taxonomy**: `errors.Is(err, os.ErrNotExist)` (missing), `os.ErrPermission`, and `io.EOF` for read exhaustion (usually handled implicitly by scanners/`io.ReadAll`).
- **Directory ops**: `os.MkdirAll(path, 0755)` (like `mkdir -p`), `os.ReadDir(dir)` → sorted entries, `filepath.WalkDir` for recursion, `filepath.Join` for path building (never string-concat `/`).

## 5. Example 1 — Read, write, append

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	// whole-file write
	if err := os.WriteFile("notes.txt", []byte("line 1\nline 2\n"), 0644); err != nil {
		fmt.Println("write:", err)
		return
	}

	// whole-file read
	data, err := os.ReadFile("notes.txt")
	if err != nil {
		fmt.Println("read:", err)
		return
	}
	fmt.Print(string(data))

	// append (open for write, seek to end)
	f, err := os.OpenFile("notes.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		fmt.Println("open:", err)
		return
	}
	defer f.Close()
	if _, err := f.WriteString("line 3\n"); err != nil {
		fmt.Println("append:", err)
	}
}
```

## 6. Example 2 — Streaming lines + directory walk

```go
package main

import (
	"bufio"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	// stream a (potentially huge) file line by line
	f, err := os.Open("big.txt")
	if err != nil {
		fmt.Println("open:", err)
		return
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		if strings.Contains(scanner.Text(), "ERROR") {
			fmt.Printf("line %d: %s\n", lineNo, scanner.Text())
		}
	}
	if err := scanner.Err(); err != nil {
		fmt.Println("scan:", err)
	}

	// walk a directory tree
	filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err // report, don't silently skip
		}
		if !d.IsDir() && strings.HasSuffix(path, ".go") {
			fmt.Println("go file:", path)
		}
		return nil
	})
}
```

## 7. Real-World Example

A production-grade log analyzer: streaming (memory-safe), robust errors, and a CSV writer:

```go
package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"strconv"
	"strings"
)

type Request struct {
	Path  string
	Count int
}

func main() {
	in, err := os.Open("access.log")
	if err != nil {
		fmt.Fprintln(os.Stderr, "open:", err)
		os.Exit(1)
	}
	defer in.Close()

	counts := map[string]int{}
	sc := bufio.NewScannerWrap(in)
	for _, line := range sc {
		fields := strings.Fields(line)
		if len(fields) >= 3 {
			counts[fields[2]]++
		}
	}

	out, err := os.Create("summary.csv")
	if err != nil {
		fmt.Fprintln(os.Stderr, "create:", err)
		os.Exit(1)
	}
	defer out.Close()

	w := csv.NewWriter(out)
	defer w.Flush()
	for path, count := range counts {
		w.Write([]string{path, strconv.Itoa(count)})
	}
}

// bufio.NewScannerWrap is illustrative; in real code use bufio.Scanner directly:
func bufioNewScannerWrapDummy() {}
var bufioNewScannerWrap = func(f *os.File) [][]string { return nil }
```

(The wrap stub exists only so the snippet stays short — implement with a plain `bufio.Scanner` loop as in Example 2.)

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| `ReadFile` on unbounded input | Memory exhaustion; stream instead |
| Ignoring `scanner.Err()` | `Scan()` returning false can mean an error, not EOF |
| Not closing files | `defer f.Close()` right after a successful open |
| String-building paths with "/" | Use `filepath.Join` (portable, cleans paths) |
| Line longer than 64 KB | Scanner errors; raise with `scanner.Buffer(buf, max)` |
| Write without checking `w.Write`'s `(n, err)` | Short writes are silent data loss |

## 9. Best Practices

- Open → `defer Close()` immediately.
- Stream with `bufio` for logs/CSVs; `ReadFile` only for bounded config-ish files.
- Always check `scanner.Err()` after the loop.
- Use `filepath.WalkDir` (Go 1.16+) over the older `filepath.Walk`.
- For atomic writes: write to a temp file, then `os.Rename`.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java | Python | JavaScript (Node) |
|--------|----|------|--------|-------------------|
| Read all | `os.ReadFile` | `Files.readAllBytes` | `open().read()` | `fs.readFileSync` |
| Stream lines | `bufio.Scanner` | `BufferedReader` | file iteration | `readline` |
| Close | `defer f.Close()` | try-with-resources | `with` block | manual/streams |
| Path joining | `filepath.Join` | `Paths.get` | `os.path.join` | `path.join` |

## 11. Practical Exercise

1. Write 3 lines to a file, read it back, print with line numbers.
2. Append safely using `OpenFile` flags.
3. Count lines, words, and bytes of a file (mini `wc`).

## 12. Mini Project / Task

`filestats.go`: CLI that takes a directory, walks it, and prints per-extension totals (count of files, total bytes). Use `filepath.WalkDir`, `fs.DirEntry.Info()`, and handle per-file errors gracefully.

## 13. Interview Questions

### Easy
- `os.ReadFile` vs `os.Open` + scanner?
- How do you append to a file?

### Medium
- How do you handle a scanner that fails mid-file?
- Why `filepath.Join` instead of concatenation?

### Hard
- How would you tail a growing log file in Go (like `tail -f`)?
- How do you write a file atomically (crash-safe replace)?

## 14. Daily Practice Questions

### Easy
1. Create a file with 5 lines; read and print them.
2. Check if a file exists with `os.Stat` and `errors.Is(err, os.ErrNotExist)`.
3. Copy a file (read all + write).
4. List a directory's entries with `os.ReadDir`.
5. Get a file's size with `Info()`.

### Medium
6. Implement `tail(path string, n int) ([]string, error)`.
7. Write CSV of users with `encoding/csv` and `Flush`.
8. Find the 10 largest files under a directory.
9. Search files for a keyword, printing file:line matches (mini grep).
10. Delete all `.tmp` files in a tree (with confirmation dry-run flag).

### Hard
11. Implement atomic file save (temp + rename + fsync).
12. Build a line-oriented diff of two files.
13. Watch a directory for changes by polling `os.Stat` mtimes.
14. Parse a 1 GB log streaming, keeping only top-k paths (bounded memory).
15. Implement a tiny key-value store persisted as an append-only log with compaction.

## 15. Solutions / Hints

- Q6 hint: read all lines into memory for small files; stream backwards for huge ones.
- Q11 hint: `os.CreateTemp(dir, pattern)` → write → `f.Sync()` → `os.Rename(tmp, final)`.
- Q14 hint: min-heap of size k over (path, count).

## 16. Day Summary

- `os.ReadFile/WriteFile` for bounded data; `bufio.Scanner` + `Open/Create` for streams.
- Always `defer Close()`; always check `scanner.Err()`.
- `filepath` for paths; `WalkDir` for trees; atomic saves via rename.

## 17. What To Revise

- OpenFile flag combos; scanner error handling.

## 18. What Comes Tomorrow

**Day 14 — JSON**: marshaling/unmarshaling, struct tags, nesting, streaming with encoders, and API payloads.
