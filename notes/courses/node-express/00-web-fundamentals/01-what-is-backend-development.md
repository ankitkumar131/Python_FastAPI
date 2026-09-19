# 01 — What Is Backend Development?

> **Where this fits:** This is the very first chapter. Before we write a single line of
> Node.js, we need to agree on the vocabulary — client, server, frontend, backend,
> database, API — and understand how the pieces connect. Everything later in these
> notes is an elaboration of the picture drawn here.

---

## 1. The problem: a website is not one program

You already know JavaScript. When you write JavaScript for a web page, you write
something like this:

```js
document.querySelector('#add').addEventListener('click', () => {
  const name = document.querySelector('#name').value;
  const list = document.querySelector('#list');
  list.insertAdjacentHTML('beforeend', `<li>${name}</li>`);
});
```

This code runs **inside the user's browser**, on the user's machine. It can only see
what is already in that page: the DOM, the values the user typed, and network requests
it explicitly makes.

Now imagine the page has to show a list of *all* employees in the company, with
salaries. Problems appear immediately:

1. **The browser does not have that data.** It is not in the HTML you sent.
2. **If you did send all the data in the HTML, everyone could read everyone's salary.**
   The browser is fully controlled by the user — they can open DevTools, read the
   JavaScript, change variables, and call your code however they want.
3. **The data has to live somewhere permanent.** Closing the tab must not delete it.
4. **The rules must be enforced by someone trustworthy.** "Only a manager can change a
   salary" cannot be enforced in a browser, because the user owns the browser.

That set of problems is exactly what **backend development** exists to solve.

> **Backend development** is building the programs that run on *your* servers: the
> programs that own the data, enforce the rules, and answer requests coming from
> browsers and mobile apps.

---

## 2. The cast of characters

### Client

A **client** is any program that asks another program for something.

- A browser (Chrome, Firefox) — the most familiar client.
- A mobile app (a React Native or Flutter app).
- Another server (this is how microservices talk to each other).
- `curl`, Postman, or a test file (`request(app).get('/users')`).

Note what this implies: **the client is not always a browser, and it is not always
something you control.** A well-designed backend assumes every request might come from
an attacker.

### Server

A **server** is a program that listens for requests and sends back responses.

The word is overloaded, so be precise:

| Term | Meaning |
| --- | --- |
| "The server" (software) | A long-running process, e.g. your `node server.js` |
| "The server" (hardware) | The machine/VPS/container the process runs on |
| "A server" in architecture diagrams | A logical role: "this thing answers requests" |

When someone says "the request never reached the server", they usually mean the
*process*. When they say "the server is down", they might mean the machine.

> **Internally:** a server is just a loop. It waits for a TCP connection, reads bytes
> off the socket, parses them as HTTP, calls your handler function, writes bytes back,
> and waits for the next connection. Node.js is popular precisely because its
> event loop makes thousands of these waits nearly free (see
> [01-nodejs/14-event-loop.md](../01-nodejs/14-event-loop.md)).

### Frontend vs backend

| | Frontend | Backend |
| --- | --- | --- |
| Runs on | The user's device (browser/app) | Your server |
| Language (typical) | JavaScript/TypeScript, HTML, CSS | JavaScript (Node), Python, Java, Go, PHP, Ruby, C# |
| Trust level | **Untrusted** — the user can read and modify everything | **Trusted** — users cannot see or change the code |
| Can it keep a secret? | No (never put an API key in frontend code) | Yes, in environment variables |
| Talks to | The backend, via HTTP | The database, other services, the frontend |
| Typical job | Render UI, handle clicks, call APIs | Validate input, authorise, run business rules, read/write the database |

A **full-stack developer** works in both, and — importantly — designs the boundary
between them: the API.

### Database

A **database** is a program dedicated to storing data reliably and finding it fast.

Why not just use a file? Because a real backend needs:

- **Concurrent access** — 500 users creating orders at the same moment.
- **Fast lookups** — find the 1 user out of 10 million with this email.
- **Safety** — if the process is killed mid-write, the data must not be half-written.
- **Relationships** — this order belongs to that user who belongs to that company.
- **Atomic multi-step operations** — debit one account and credit another, or neither.

A file gives you none of these; a database gives you all of them. We cover them in
03-databases *(not available in this published source revision)*.

The backend never lets a client talk to the database directly. The client asks the
backend; the backend asks the database. That single rule is the source of most backend
security.

### API

**API** stands for **Application Programming Interface**: a contract that describes how
one piece of software asks another one to do something.

- A **library API**: `fs.readFile(path, callback)` — you call it, it does something.
- A **web API / HTTP API**: `GET https://api.example.com/v1/users/42` — you send a
  request over the network, you get data back.

In these notes, "API" almost always means the second kind: an HTTP API. The API is the
**front door of your backend** — the only supported way in. Everything behind it
(database schema, table names, internal services) can change freely, as long as the API
contract stays stable.

### REST API

**REST** (Representational State Transfer) is a *style* for designing HTTP APIs around
**resources** (nouns) and **HTTP methods** (verbs):

```text
GET    /users        → list users
GET    /users/42     → fetch one user
POST   /users        → create a user
PUT    /users/42     → replace user 42
PATCH  /users/42     → partially update user 42
DELETE /users/42     → delete user 42
```

Versus a "RPC style" API where the URL is a verb:

```text
POST /getUserById
POST /createUser
POST /deleteUserById
```

REST is not a law of physics; it is a widely understood convention. We go deep on it in
[05-rest-and-api-design.md](05-rest-and-api-design.md). The *real* REST (Fielding's
dissertation) also requires things like HATEOAS and full statelessness that most
"REST APIs" do not implement — that is fine and normal, but you should know the
distinction so you do not freeze in an interview.

---

## 3. How everything connects

Here is the whole system in one diagram. Read it slowly — every chapter in these notes
is an expansion of one arrow.

```text
┌──────────────────────────────────────────────────────────────┐
│ CLIENT (browser / mobile app / curl / another server)        │
│ untrusted: the user can read and change all of this          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  ① HTTP request
                            │     GET /api/v1/employees?page=2
                            │     Headers: Authorization: Bearer …
                            │     Body (for POST/PUT/PATCH): JSON
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ BACKEND API (this is what we are going to build)             │
│ trusted: users cannot see or modify this code                │
│                                                              │
│  ② Routing          → which handler matches this URL+method? │
│  ③ Middleware       → logging, auth, rate limit, validation  │
│  ④ Controller       → translate HTTP into a function call    │
│  ⑤ Service          → business rules ("a manager may …")     │
│  ⑥ Data access      → build the query                        │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  ⑦ query / insert / update
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ DATABASE (MongoDB / MySQL / PostgreSQL / Redis)              │
│ owns persistence, indexes, transactions, concurrency         │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  ⑧ rows / documents
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ BACKEND API                                                  │
│  ⑨ shape the data into a response (usually JSON)             │
│  ⑩ status code + headers                                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  ⑪ HTTP response
                            │     200 OK, application/json
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ CLIENT renders the result; the user sees the page            │
└──────────────────────────────────────────────────────────────┘
```

Two rules are hidden in that diagram, and they are the two most common beginner
mistakes:

1. **The client never talks to the database.** The database is not exposed to the
   internet. If a browser can reach your MongoDB, you have a data breach.
2. **Never trust the client.** Steps ③ and ⑤ exist because anything arriving from step
   ① could be malicious. `page=2` might arrive as `page=-1`, or `page=DROP TABLE`, or a
   2MB string instead of a number.

---

## 4. What a backend developer actually does all day

The job is not "writing routes". Routes are the easy part. Real work looks like:

| Activity | Example question you are answering |
| --- | --- |
| Designing the data model | Should orders embed line items, or reference them? |
| Designing the API contract | What does `POST /orders` accept, and what does `201` return? |
| Implementing business rules | Can a user cancel an order after it shipped? |
| Validating input | Is this an email? Is this an allowed enum value? |
| Authorising | Is this user allowed to see *this* order? |
| Handling failure | What happens when the payment provider times out? |
| Performance | This endpoint takes 2s; which of the 6 queries is slow? |
| Observability | When a user says "it's broken", how do you find out why? |
| Safety | What happens if this whole process is killed right now? |

Notice how few of those are about `if` statements in JavaScript. Backend engineering is
mostly about **state, trust, and failure**.

---

## 5. Where Node.js and Express fit

JavaScript was originally a browser-only language. **Node.js** took Google's V8 engine
(which compiles JavaScript to machine code) plus a set of libraries for talking to the
operating system, and produced a runtime you can run outside the browser.

```text
JavaScript code
      ↓
V8 engine          ← compiles and executes JS (the same engine inside Chrome)
      ↓
Node.js runtime    ← adds fs, http, net, crypto, timers, event loop
      ↓
Operating system   ← files, sockets, threads, processes
```

**Express** is a small library on top of Node's built-in `http` module. Node can serve
HTTP by itself, but it makes you do everything manually — parse the URL, match the
method, read the body, set headers. Express gives you a routing table and a middleware
pipeline instead:

```text
Node.js  : you manually write "if method is GET and url starts with /users, then…"
Express  : app.get('/users/:id', (req, res) => { … })
```

This is why we build a server with the raw `http` module *before* learning Express (in
[01-nodejs/11-http-module.md](../01-nodejs/11-http-module.md)) and then rebuild it in
Express: you should know what Express is doing for you, not just that it "works".

---

## 6. Common mistakes at this stage

| Mistake | Why it hurts | What to do instead |
| --- | --- | --- |
| Learning Express before understanding HTTP | You cannot debug anything; errors look random | Read `00-web-fundamentals` fully first |
| Putting secrets in frontend code | Tokens/keys are public within seconds | Secrets live only in backend env vars |
| Thinking "validation is optional because the frontend validates" | Anyone can `curl` your API | Validate on the server, always |
| Letting the client decide permissions | `{ "role": "admin" }` in a request body = instant admin | Read roles from the database, never from the request |
| Believing tutorials that only show the happy path | Production is 80% failure paths | Always ask "what if this fails?" |
| Jumping between frameworks | You learn syntax, not concepts | Finish one path (this one) end to end |

---

## Exercise 1.1 — Identify the layers

You open a shopping site and click "Buy". The following things happen. Classify each as
**frontend**, **backend**, **database**, or **network**, and put them in order:

```text
A. The cart total is recalculated.
B. A row is inserted into `orders`.
C. The browser sends POST /api/v1/orders.
D. The server checks that the user is logged in.
E. The server replies with 201 Created and the new order id.
F. The browser shows "Order placed #1042".
G. The server checks stock in the `products` table.
```

<details>
<summary>Solution</summary>

1. **A — frontend.** The running total can be recomputed in the browser for instant
   feedback. (It must *also* be recomputed on the backend, because the browser total
   can be tampered with.)
2. **C — network** (initiated by the frontend). The request travels over the internet.
3. **D — backend** (middleware/auth step). The server does not trust any claim from the
   client.
4. **G — database**, triggered by backend logic. Stock lives in the database.
5. **B — database**, triggered by backend logic.
6. **E — backend** (response) over the **network**.
7. **F — frontend.**

The important observation: the client's opinion is never the final answer. A is a
*convenience*; D, G and B are the *truth*.

</details>

## Exercise 1.2 — Split the responsibilities

A junior developer proposes this design: "The mobile app will query MongoDB directly for
the product list, and the web app will call our API. It's faster because there's no
middle layer."

Explain, in your own words, three concrete problems with this.

<details>
<summary>Solution</summary>

1. **Security.** To query MongoDB the app must hold database credentials. Anyone who
   decompiles the mobile app gets full read/write access to your database. There is no
   way to hide credentials inside a client.
2. **Business rules cannot be enforced.** Only published products should be visible.
   Pricing should include regional tax. Those rules would have to be duplicated in every
   client — and a client can simply skip them.
3. **Change becomes impossible.** Renaming a collection or changing the schema would
   break every installed app version. With an API you can change the storage layer
   freely and keep the API contract stable.
4. *(bonus)* **No caching, rate limiting, or logging control.** The API layer is where you
   add those. Also: mobile networks are unreliable; a database driver expects a stable
   connection.

</details>

---

## What's next

You now know the *roles*. Next we look at the *transport*: what actually happens between
the click and the JSON response — DNS, TCP, TLS, and the request/response cycle.

→ [02 — How the Web Works](02-how-the-web-works.md)
