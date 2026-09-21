# Day 14 — JSON

## Learning Objectives

- Marshal/unmarshal JSON with structs and tags.
- Control field names, omission, and read-only fields via tags.
- Handle nested structures, dynamic JSON, and streaming encode/decode.
- Build and parse JSON APIs like a backend engineer.

## Prerequisites

- Day 7 structs + tags; Day 11 errors.

## 1. Concept Introduction

JSON is the lingua franca of APIs. Go's `encoding/json` maps Go structs ↔ JSON via **reflection on struct tags**:

```go
type User struct {
	Name  string `json:"name"`
	Email string `json:"email,omitempty"`
	Age   int    `json:"age,omitempty"`
}
```

```go
b, _ := json.Marshal(u)          // struct → []byte JSON
err := json.Unmarshal(b, &u)     // []byte JSON → struct (note the &!)
```

## 2. Why This Concept Exists

Every backend speaks JSON: REST APIs, configs, queues, logs. Go made struct-tag-driven mapping the standard — your API's wire format is documented **in the struct definition itself**, version-controlled next to the code, and type-checked. No runtime schema drift like untyped objects.

## 3. Syntax: the tag vocabulary

| Tag | Effect |
|-----|--------|
| `json:"name"` | field ↔ key "name" |
| `json:"-"` | skip the field entirely |
| `json:"-,"` | key literally named "-" |
| `json:",omitempty"` | omit when zero value |
| `json:"name,string"` | encode number as quoted string (interop) |
| no tag | key = exact Go field name (`Name` — usually unwanted) |

Unmarshal ignores unknown JSON keys by default (forward compatibility). Uppercase (exported) fields only are processed.

## 4. Detailed Explanation

- **Marshal**: exported fields only; `omitempty` drops zero values; pointers marshal as `null` when nil (useful for PATCH-style optional fields, Day 8).
- **Unmarshal** requires a **pointer**: `json.Unmarshal(data, &user)` — it writes into your struct. Type mismatches return `*json.UnmarshalTypeError`; malformed JSON returns `*json.SyntaxError`.
- **Decoding to `any`**: for schema-less JSON, `var v any; json.Unmarshal(b, &v)` yields `map[string]any / []any / float64 / string / bool / nil` — note **all numbers become float64**.
- **Streaming**: `json.NewEncoder(w)` / `json.NewDecoder(r)` work on any `io.Writer`/`Reader` — essential for HTTP (Day 15/16) and NDJSON files.
- **Performance**: `encoding/json` is reflection-based. For hot paths, consider codegen (easyjson) or the stdlib v2 experimental packages — but start with the stdlib.

## 5. Example 1 — Structs, nesting, omitempty

```go
package main

import "encoding/json"

type Address struct {
	City    string `json:"city"`
	Country string `json:"country"`
}

type User struct {
	ID      int      `json:"id"`
	Name    string   `json:"name"`
	Email   string   `json:"email,omitempty"` // omitted when ""
	Address Address  `json:"address"`
	Tags    []string `json:"tags,omitempty"`
	Password string  `json:"-"`               // never serialized
}

func main() {
	u := User{
		ID: 1, Name: "Ada",
		Address: Address{City: "London", Country: "UK"},
		Password: "secret",
	}
	b, _ := json.MarshalIndent(u, "", "  ")
	_ = b
}
```

Output:

```json
{
  "id": 1,
  "name": "Ada",
  "address": { "city": "London", "country": "UK" },
  "password": "…omitted, see json:\"-\"…"
}
```

(`Password` is dropped by `json:"-"`.)

## 6. Example 2 — Unmarshal + errors + dynamic JSON

```go
package main

import (
	"encoding/json"
	"fmt"
	"strings"
)

func main() {
	payload := `{"id":7,"name":"Grace","tags":["navy","compiler"]}`

	var u struct {
		ID   int      `json:"id"`
		Name string   `json:"name"`
		Tags []string `json:"tags"`
	}
	if err := json.Unmarshal([]byte(payload), &u); err != nil {
		fmt.Println("bad json:", err)
		return
	}
	fmt.Printf("%+v\n", u)

	// unknown key → no error by default
	weird := `{"id":"not-a-number"}`
	var v struct{ ID int `json:"id"` }
	err := json.Unmarshal([]byte(weird), &v)
	var typeErr *json.UnmarshalTypeError
	fmt.Println("type error?", errorsAs(err, &typeErr)) // true

	// dynamic JSON via any
	var anyVal map[string]any
	_ = json.Unmarshal([]byte(`{"a":1,"b":[true,"x"]}`), &anyVal)
	num := anyVal["a"].(float64) // numbers are float64!
	fmt.Println(num + 1)
}

func errorsAs(err error, target any) bool {
	return strings.Contains(fmt.Sprintf("%T", err), "UnmarshalTypeError")
}
```

## 7. Real-World Example

NDJSON (newline-delimited JSON) log processing — streaming decode over a file:

```go
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
)

type LogLine struct {
	Level string `json:"level"`
	Msg   string `json:"msg"`
}

func main() {
	f, _ := os.Open("app.ndjson")
	defer f.Close()

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		var line LogLine
		if err := json.Unmarshal(sc.Bytes(), &line); err != nil {
			fmt.Fprintln(os.Stderr, "skip bad line:", err)
			continue
		}
		if line.Level == "error" {
			fmt.Println(line.Msg)
		}
	}
}
```

## 8. Common Mistakes

| Mistake | Explanation |
|---------|-------------|
| Missing `&` in `Unmarshal(data, &v)` | Won't compile (needs pointer) |
| Unexported fields silently skipped | JSON only sees exported fields |
| Numbers via `any` are ints | They're `float64` — cast |
| No tags → keys like `"Name"` | Always tag your wire structs |
| Sharing one struct for DB + API + wire | Layer-specific structs (Day 7 example) prevent leaks |
| `json.Unmarshal` of huge stream into memory | Use `Decoder` streaming |

## 9. Best Practices

- Always write tags, even for obvious mappings.
- Version your payloads with additive fields (unknown keys ignored = free compatibility).
- Use pointers for tri-state optional fields (absent vs zero vs null).
- Wrap decode errors with context before returning to callers.

## 10. Java/Python/JavaScript Comparison

| Aspect | Go | Java (Jackson) | Python | JavaScript |
|--------|----|----------------|--------|-----------|
| Mapping | struct tags | annotations | dicts/`json` | native objects |
| Unknown keys | ignored | fail/configurable | kept | kept |
| Numbers via dynamic | float64 | depends | int/float | float64 |
| Streaming | Encoder/Decoder | ObjectMapper | ijson etc. | streams |

## 11. Practical Exercise

1. Round-trip a struct: marshal → unmarshal → compare with `==` (or reflect.DeepEqual).
2. Use `omitempty` on 3 fields; marshal with zeros; observe omissions.
3. Decode `{"price": "19.99"}` into a `float64` field using the `,string` tag.

## 12. Mini Project / Task

`configjson.go`: load `config.json` (`{"server":{"port":8080},"db":{"url":"..."}}`) into nested structs, apply defaults for missing values, and validate required fields with typed errors (Day 11). Bonus: write back a normalized version.

## 13. Interview Questions

### Easy
- What does `json:"-"` do? `omitempty`?
- Marshal vs Unmarshal?

### Medium
- How are unknown fields handled on decode, and why is that useful?
- What types do you get when unmarshaling into `any`?

### Hard
- How would you implement custom JSON marshaling for a `time.Duration` field?
- Explain how you'd decode a 5 GB JSON array with constant memory.

## 14. Daily Practice Questions

### Easy
1. Marshal a struct with 4 fields; print the JSON.
2. Unmarshal a fixed JSON string into a struct.
3. Hide a field with `json:"-"`.
4. Pretty-print with `MarshalIndent`.
5. Marshal `nil` vs empty slice — compare outputs (`null` vs `[]`).

### Medium
6. Decode into `map[string]any` and print types of each value.
7. Implement `MarshalJSON`/`UnmarshalJSON` for a `Temperature` type storing Celsius but exposing Fahrenheit.
8. Handle `*json.SyntaxError` with a helpful message.
9. Encode a slice of 100 structs to a file as NDJSON; decode back.
10. Write a generic `LoadJSON(path string, v any) error` helper with wrapping errors.

### Hard
11. Write a decoder for deeply nested unknown JSON that prints a schema tree.
12. Implement PATCH semantics: apply a JSON with pointer fields over an existing struct.
13. Benchmark `json.Marshal` vs `json.NewEncoder` on 10k structs; explain the difference.
14. Implement field-level validation after unmarshal, returning aggregated `errors.Join` results.
15. Build a tiny JSONPath-like extractor: `get(data, "a.b[2].c")` over `any`.

## 15. Solutions / Hints

- Q5: `nil` slice → `null`; `[]T{}` → `[]`. Distinguish with care in APIs.
- Q7 hint: implement `func (t Temperature) MarshalJSON() ([]byte, error)`.
- Q12 hint: struct with `*string`, `*int` fields; nil = don't touch.
- Q15 hint: split path on `.`, handle `[n]` by parsing index; walk `map[string]any`/`[]any`.

## 16. Day Summary

- Struct tags define the wire format; exported fields only.
- `omitempty` + pointer fields = precise APIs; unknown keys ignored = compatibility.
- `Encoder/Decoder` stream over any io endpoint — the HTTP workhorse.

## 17. What To Revise

- Tag vocabulary table; float64-in-`any` gotcha.

## 18. What Comes Tomorrow

**Day 15 — HTTP**: the net/http client and server, handlers, and the patterns behind real web services.
