# 02 — The web, HTTP, REST, JSON and CRUD

[Previous](01-python-prerequisites.md) · [Course map](00-course-guide.md) · [Next](03-fastapi-first-application.md)

## Backend, client, server and API: what are they?

Imagine a restaurant. The **client** is the diner asking for something. The **server** is the kitchen accepting requests and producing results. A browser, mobile app, command-line program or another backend can be a client. “Server” can mean the program accepting connections or the computer running it; context matters. Both programs can run on the same computer during development.

The **frontend** is the user-facing part, such as product cards and buttons. The **backend** is the trusted server-side part that validates actions, enforces permissions and stores/retrieves data. It exists because browsers cannot safely hold database passwords or decide whether a payment succeeded. Never trust a frontend's price calculation just because your own interface produced it.

An **API (Application Programming Interface)** is a defined way for software to use another component. Think of the restaurant menu: the diner need not know how the stove works. A Python library has an API too; not all APIs use the web. Here we build an HTTP API: clients send structured messages over a network and get structured replies.

Use a backend when clients need shared durable state, secret credentials or centrally enforced rules. A static personal page may not need one. Use an API when programs need to communicate; a human-only report may be better served as a file. Do not expose the database directly to every browser.

## Request versus response

A **request** asks the server to perform an operation. It contains a method, a target, headers and sometimes a body. A **response** contains a status code, headers and often a body. These are messages, not function calls shared across computers. Networks can lose connections: the server may finish a write even when the client never receives the response. That fact explains why retry safety matters.

**HTTP (Hypertext Transfer Protocol)** defines the message semantics. A protocol is an agreed set of communication rules. HTTP/1.1 below is readable for teaching; HTTP/2 and HTTP/3 use different framing while preserving methods, status codes and headers. Do not assume one request always means a new network connection.

**HTTPS** is HTTP protected using **TLS (Transport Layer Security)**. TLS encrypts traffic in transit and authenticates the server using a certificate. It prevents a network observer simply reading passwords. It does not fix a weak password, insecure endpoint or leaked database. Use HTTPS outside isolated local development. Never disable certificate verification to “fix” a production connection.

## URL, path, query, endpoint and route

A **URL (Uniform Resource Locator)** identifies where a resource is available:

```text
https://api.example.com:443/products/42?currency=INR&include_stock=true
└scheme └────host─────┘port└───path──┘└────────query────────────────┘
```

- Scheme chooses the protocol. Host identifies the destination; a domain name is resolved to a network address through **DNS (Domain Name System)**.
- Port identifies the service on that host. HTTPS normally uses 443, so it is usually omitted.
- Path identifies the resource or operation within the server.
- Query carries additional named options after `?`; `&` separates entries. Encode reserved characters properly rather than concatenating arbitrary text.
- A `#fragment` is interpreted by the client and normally is not sent in the HTTP request.

A **route** is the server's matching rule, such as `GET /products/{product_id}`. An **endpoint** is an exposed operation clients can call; people also use the word for the URL or handler. In these notes, an endpoint means method + path + behaviour. `GET /products` and `POST /products` are different operations even though their path is identical.

A **path parameter** fills a placeholder: `/products/42` supplies product ID 42. Use it to identify a specific resource. A **query parameter** is an option such as `/products?limit=10`; use it for filtering, searching, ordering and pagination (retrieving a large collection in bounded pages). Do not put passwords or tokens in URLs: URLs often enter histories and logs.

## HTTP methods: why several verbs?

Without conventions every API might invent `doThing1` and `doThing2`. Methods tell clients and intermediaries the intended semantics. **Safe** means the requested operation does not change application state; incidental logging is allowed. **Idempotent** means repeating the same request has the same intended effect as sending it once. It does not require identical response codes.

| Method | Meaning and practical example | Safe? | Idempotent by semantics? | Common mistake |
|---|---|---|---|---|
| GET | Read `/products/42` | Yes | Yes | Deleting data from a GET link |
| POST | Submit data; `POST /products` creates a server-assigned ID | No | Not generally | Automatically retrying payments without deduplication |
| PUT | Replace the state of `/products/42` according to the representation contract | No | Yes | Treating omitted fields as unchanged without documenting different semantics |
| PATCH | Apply a partial change, e.g. change only the name | No | Not guaranteed | Assuming “increment stock” can be retried safely |
| DELETE | Remove `/products/42` | No | Yes | Thinking a second 404 means DELETE is not idempotent |
| HEAD | GET-like headers without the response body | Yes | Yes | Assuming every FastAPI GET automatically has a HEAD route |
| OPTIONS | Ask about communication options; used in browser CORS preflight | Yes | Yes | Mistaking preflight for a failed business request |

Setting a price to 200 with PATCH can be idempotent; incrementing it by 20 is not. POST can be made retry-safe with an application-level **idempotency key**, a unique operation identifier stored with the result. We return to that in production practices.

Use GET to fetch, not POST just because you prefer request bodies. Avoid depending on GET request bodies: many clients and tools do not support them consistently. Use PUT when clients truly send a complete replacement; use PATCH for independently editable fields. DELETE does not necessarily mean physically erase immediately: retention rules may require a documented soft-delete state.

## Headers and body

**Headers** are named message metadata. `Content-Type: application/json` describes the body's format. `Accept: application/json` tells the server the client's preferred response formats. `Authorization: Bearer ...` carries credentials (chapter 15). Header names are case-insensitive. Header values are not universally case-insensitive.

The **body** is the payload. A POST creating a product can put its properties in a JSON body. File uploads usually use multipart form data, taught in chapter 17. A body is not automatically trustworthy because it is structured. The server still validates it.

### Complete request example: conceptual HTTP message

```http
POST /products HTTP/1.1
Host: api.example.com
Content-Type: application/json
Accept: application/json

{"name":"Notebook","price_minor":12000}
```

Line 1 chooses creation and the target collection. Line 2 names the target host. Line 3 declares JSON input. Line 4 requests JSON output. Line 5 separates headers from the body. Line 6 carries product values. Actual HTTP/1.1 clients add message-length framing such as `Content-Length`; use a real client rather than sending this teaching representation byte for byte.

### Response example

```http
HTTP/1.1 201 Created
Content-Type: application/json
Location: /products/42

{"id":42,"name":"Notebook","price_minor":12000}
```

Line 1 says creation succeeded. Line 2 identifies the response format. Line 3 points to the created resource. Line 4 is the separator. Line 5 is the representation, now with a server-assigned ID.

## JSON: what, why and syntax

**JSON (JavaScript Object Notation)** is a text data format, not executable JavaScript and not a Python dictionary. It makes messages readable across languages. It supports objects, arrays, strings, numbers, booleans and null. Objects use double-quoted keys; strings also use double quotes. JSON booleans are `true`/`false`, while Python uses `True`/`False`; JSON `null` becomes Python `None`.

Valid: `{"tags":["paper"],"active":true,"description":null}`.
Invalid: `{'active': True,}` because single quotes, Python boolean spelling and a trailing comma are not JSON syntax.

**Serialization** converts program values into a transport/storage representation. **Deserialization** reconstructs values from that representation. JSON parsing establishes syntax, not business correctness: `{"price_minor":-100}` is valid JSON but an invalid product in our application. JSON has no native date or bytes type; APIs use a documented string convention or another format.

### File: `examples/json_roundtrip.py`

```python
import json
product = {"name": "Notebook", "active": True}
text = json.dumps(product)
restored = json.loads(text)
print(text)
print(restored["active"])
```

Line 1 imports Python's JSON library. Line 2 builds Python data. Line 3 encodes it as JSON text. Line 4 parses that text back to Python values. Line 5 prints JSON containing `true`; line 6 prints Python `True`. Save and run with `python examples/json_roundtrip.py`. FastAPI later performs the relevant response conversion, so normally return data rather than calling `json.dumps` yourself.

Use JSON for structured API documents. Do not embed enormous files as JSON strings when an upload or object-storage transfer is more appropriate. Never use `eval` to parse a request: it executes code.

## Status codes: the outcome before the details

The first digit groups the result: 1xx informational, 2xx success, 3xx redirection, 4xx a request-side problem, 5xx a server-side failure. A 4xx response does not imply a malicious client; a typo can cause one.

| Code | Meaning in this course |
|---|---|
| 200 | Successful read/update with a body |
| 201 | Resource created |
| 202 | Accepted for later processing, not completed |
| 204 | Successful operation with **no body** |
| 301/308 | Permanent redirect; 308 preserves the request method |
| 307 | Temporary redirect preserving method; commonly a trailing-slash redirect |
| 304 | Cached representation remains usable, no new response body |
| 400 | Malformed operation or application-defined bad request |
| 401 | Missing/invalid authentication; usually a `WWW-Authenticate` challenge |
| 403 | Authenticated but forbidden (also usable for other refusals) |
| 404 | Resource or route not found |
| 405 | Path exists but method is not allowed |
| 409 | Conflict with current state, such as duplicate unique name |
| 413/415 | Payload too large / unsupported media type |
| 422 | FastAPI's usual input validation failure |
| 429 | Rate limit exceeded |
| 500/502/503/504 | Internal error / invalid upstream reply / unavailable / upstream timeout |

Do not return HTTP 200 with `{"error":"not found"}` for every failure: clients and monitoring use the status to decide what happened. Do not send a JSON message with 204. Not every failure should be retried: resending invalid input will not correct it.

## REST and CRUD: related but not identical

**REST (Representational State Transfer)** is an architectural style. It emphasizes resources and representations, a uniform interface, client/server separation, stateless requests, cacheability and layered systems. **Stateless** means each request carries the information needed to understand it; it does not mean “never use a database.” Strict REST also uses links in representations to guide available actions. Many practical “REST APIs” are resource-oriented HTTP JSON APIs without implementing every REST constraint. FastAPI does not force either design.

**CRUD** means Create, Read, Update, Delete: four common data operations. Map them to POST, GET, PUT/PATCH and DELETE. CRUD is not all an API can do: searching, calculating shipping and submitting a payment have behaviours beyond row editing.

Use resource-oriented APIs when clients work with identifiable entities. Do not contort a command such as “approve invoice” into a misleading generic field update if it has significant workflow rules; `POST /invoices/42/approvals` can represent the approval resource clearly.

## What happens internally: connect everything

Clicking “Save product” makes the frontend serialize data, choose POST, add headers, and send an HTTPS request. DNS/network/TLS connect to the server. The HTTP server reads the request. The framework matches POST `/products`, parses JSON, checks the schema, then calls our function. The function creates data. The framework encodes the returned object and sends a 201 response. The frontend parses it and displays the new product. Failures can happen at every step, which is why browser errors, HTTP errors and database errors are not interchangeable.

## Practice

**Beginner:** Choose the method and URL for reading product 8 and changing only its price.

**Intermediate:** Write a JSON creation body with name, price and two tags. Identify headers needed to describe it.

**Challenge:** The client times out after POST `/payments`. Should it immediately send the same POST again? Explain.

## Expected Result and Solution

Beginner: `GET /products/8`; `PATCH /products/8` with `{"price_minor":2500}`. GET retrieves; PATCH changes only a supplied field.

Intermediate: `{"name":"Pen","price_minor":2500,"tags":["blue","ink"]}` and `Content-Type: application/json`; optionally request JSON with `Accept: application/json`. Each string uses double quotes, price is a number, tags are an array.

Challenge: not blindly. The payment might already have succeeded. Use the same documented idempotency key for a safe retry or query the operation's status. A timeout tells you the response was not received, not that the operation did not occur.

## Summary / best practices

Treat the HTTP interface as a contract, not an implementation accident. Choose meaningful verbs, bounded collections, correct codes, valid JSON and HTTPS. Next we will turn this contract into Python functions.
