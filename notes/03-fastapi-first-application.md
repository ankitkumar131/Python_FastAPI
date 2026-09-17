# 03 — FastAPI, its ecosystem and your first application

[Previous](02-web-http-rest.md) · [Course map](00-course-guide.md) · [Next](04-routing-and-inputs.md)

## What is FastAPI and why use it?

FastAPI is a Python web framework for building APIs. You describe operations with Python functions and type hints; it connects HTTP requests to those functions, validates inputs, prepares responses and generates machine-readable documentation. It addresses repeated work: manually parsing strings, checking request bodies, writing separate API specifications and wiring common needs into every endpoint.

It is not a database, a web server process, a frontend builder or a complete account-management system. “Fast” includes developer productivity as well as performance potential. A slow query is still slow inside FastAPI.

### Advantages, limitations and choices

| Choice | What it provides | When it fits / when not |
|---|---|---|
| FastAPI | Typed request/response contracts, automatic OpenAPI, dependency system, async-capable stack | Good for APIs and async integrations; not a batteries-included admin/content platform |
| Flask | Small extensible web core, traditionally WSGI-first | Good for small web apps and existing Flask expertise; typed API validation/docs usually require choices or extensions |
| Django | Integrated ORM, migrations, authentication, admin and web patterns | Good for large business/content applications needing those features; use Django REST Framework or other tools for rich APIs |

These are design trade-offs, not a universal speed ranking. Existing skills, maintenance and required features matter more than a hello-world benchmark. Django supports ASGI too; “Django cannot do async” is incorrect. Flask has async-related support with different execution constraints; it is not the same as an ASGI-native stack.

## Understand the stack before using it

**ASGI (Asynchronous Server Gateway Interface)** is a standard interface between Python servers and applications. A server provides a connection description and asynchronous receive/send operations; the app consumes and emits events. It supports HTTP, WebSockets and lifespan events. Its older relative **WSGI (Web Server Gateway Interface)** is a synchronous request/response interface. An interface is a contract; ASGI itself is not a process listening on port 8000.

**Uvicorn** is an ASGI server implementation. It listens on a network port, handles protocol details and invokes the application. We run Uvicorn to make our Python app reachable.

**Starlette** is a lower-level ASGI web toolkit. FastAPI is built on it and reuses routing foundations, requests, responses, middleware and WebSockets. FastAPI adds typed parameter handling, dependencies and API schema generation. These are collaborating layers, not separate network services.

**Pydantic** is a data validation/serialization library. Given a schema (a declared data shape), it checks and often converts inputs into typed Python values. It also supports output conversion. Chapter 05 teaches it thoroughly. It is not an ORM and does not save data.

**OpenAPI** is a standard document describing operations, parameters, security and responses. FastAPI serves its generated description at `/openapi.json`. **Swagger UI** is an interactive web interface reading that description, served at `/docs`. **ReDoc**, at `/redoc`, is another documentation interface. Neither page is a separate API implementation. Changing your typed route can change the generated specification and both views.

## Installation: do not mix Python environments

A **virtual environment** is an isolated package directory for a project. Without it, one project's upgrades can break another. A shell is the command interpreter in your terminal. Run the appropriate commands for your operating system, not both sets.

If starting outside this repository:

```bash
mkdir fastapi-project
cd fastapi-project
```

`mkdir` creates the directory; `cd` changes the shell's working directory. If you already have this repository, just open a terminal in its root instead.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "fastapi[standard]" "pydantic>=2,<3"
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "fastapi[standard]" "pydantic>=2,<3"
```

Line 1 creates `.venv` using Python's `venv` module. Line 2 activates it so `python` resolves to that environment. Line 3 updates the package installer in this interpreter. Line 4 installs FastAPI's standard optional dependencies (including Uvicorn and commonly needed API tooling) and Pydantic v2. Brackets select package **extras**: optional dependency groups. Quotes keep shells from interpreting brackets or comparison characters.

If PowerShell blocks activation, you can avoid changing security policy: use `.venv\Scripts\python.exe -m pip ...` and that interpreter for subsequent commands. On Linux/macOS `.venv/bin/python` works without activation too. `deactivate` leaves an activated environment; it does not delete installed packages.

For **all repository examples** instead install the provided bundle with `python -m pip install -r requirements.txt`. `-r` reads one requirement per line. Database servers and Docker are separate programs, not installed by pip.

## First application

When following from an empty project create an `examples` directory with `mkdir examples`. In this repository the file is already supplied. No database or account configuration is needed for this lesson.

## Example

### File: `examples/first.py`

```python
from fastapi import FastAPI

app = FastAPI(title="Product school")

@app.get("/")
def home():
    return {"message": "Hello World"}
```

## Code Explanation

### Line 1

Import the application class from the installed FastAPI package.

### Line 2

This blank line separates logical parts; Python does not execute it.

### Line 3

Create one application object. Uvicorn will import this object. The title appears in the API documentation.

### Line 4

This blank line separates logical parts; Python does not execute it.

### Line 5

`@` applies a decorator. `app.get` registers the following function for HTTP GET at the root path `/`.

### Line 6

Define the handler named `home`. It has no request arguments. Registration connects a URL/method to this callable; its Python name need not equal the URL.

### Line 7

Return a Python dictionary. FastAPI prepares a JSON response; do not manually JSON-encode it.

## How to run it

```bash
python -m uvicorn examples.first:app --reload
```

`python -m` runs the installed module through the active interpreter. `uvicorn` is the server. `examples.first` is the import path: folder `examples`, file `first.py`, without `.py`. The colon selects the variable `app`. `--reload` watches source changes and restarts during development. It is not a production option. Press Ctrl+C to stop the server.

If you named the file `main.py` in the current directory instead, the matching command is `python -m uvicorn main:app --reload`. Do not mix filenames from two layouts.

For a remote live preview:

```bash
python -m uvicorn examples.first:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` listens on all container/network interfaces; it is a bind address, not a browser destination. `--port 8000` chooses the listening port. Open the forwarded public URL offered by your environment. Do not expose development services containing secrets to an untrusted network.

## Test it

On your own computer open `http://127.0.0.1:8000/`. `127.0.0.1` is the local loopback address. Expect HTTP 200 and `{"message":"Hello World"}`. JSON whitespace may differ without changing meaning.

Open `http://127.0.0.1:8000/docs`. Expand GET `/`, click **Try it out**, then **Execute**. Swagger UI sends an actual request and shows its response. `/redoc` presents another view. `/openapi.json` shows the underlying specification.

Or run in a second terminal:

```bash
curl -i http://127.0.0.1:8000/
```

`curl` is an HTTP command-line client. `-i` includes response headers and status. In PowerShell use `curl.exe` if `curl` is an alias for another command. Subsequent curl commands assume a POSIX-compatible shell; Swagger UI is the cross-platform alternative for JSON bodies.

## What happens internally?

1. Uvicorn imports the module. Python creates the app and function, and the decorator registers a route. The function body has not handled a request yet.
2. A client connects and sends GET `/`. Uvicorn translates the network request into ASGI events.
3. The FastAPI/Starlette middleware and routing stack matches path and method. Starlette is part of this stack, not an extra HTTP hop after FastAPI.
4. FastAPI resolves declared dependencies and validates request inputs before invoking the endpoint. Here there are none.
5. A normal `def` endpoint is run through the framework's worker-thread mechanism, keeping blocking synchronous handler work off the event loop (chapter 09).
6. The function returns a dictionary. FastAPI prepares JSON-compatible output; when a response model is declared it also validates and filters it. It builds a response with status, headers and encoded body.
7. ASGI send events return to Uvicorn, which sends the HTTP response. The client displays or parses it.

Do not memorize a diagram claiming **all** Pydantic validation happens after the endpoint. Request validation happens before your endpoint; response-model validation happens afterwards.

## Real-world use / when not to use it

The same route mechanism can return a catalogue, create an order or report health. Use FastAPI when typed HTTP contracts fit your service. Do not assume it provides transaction design, account recovery, rate limiting or database migrations automatically. These remain application responsibilities.

## Common Mistakes and Best Practices

- `ModuleNotFoundError: fastapi`: check the interpreter with `python -c "import sys; print(sys.executable)"`, then install using that interpreter's pip.
- `Could not import module`: run from the correct root and match the module path, including letter case.
- `Address already in use`: stop the earlier server or use `--port 8001`, then change the browser URL too.
- `/users` returns 404: only `/` exists so far. A working server cannot invent routes.
- Defining two handlers for the same method/path is ambiguous; give each operation one intentional registration.
- Returning a JSON string instead of a dictionary can produce double encoding: the response is then a JSON string containing JSON, not an object.

Keep reload local, use isolated environments, and prove the first app works before adding databases.

## Practice

Create GET `/products` returning three product names.

## Expected Result

`["Notebook","Pen","Pencil"]`, HTTP 200, visible in `/docs`.

## Solution

### File: `examples/practice_first.py`

```python
from fastapi import FastAPI
app = FastAPI()
@app.get("/products")
def products():
    return ["Notebook", "Pen", "Pencil"]
```

Line 1 imports the class. Line 2 creates the app. Line 3 registers a GET route. Line 4 defines its handler. Line 5 returns a Python list, serialized to a JSON array. Save it; stop the previous server and run `python -m uvicorn examples.practice_first:app --reload`. Open `/products` and `/docs` on port 8000.

## Summary

You now have a complete request-to-response cycle. Next we will ask the caller for information rather than always returning the same answer.
