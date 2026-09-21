# 02 — How the Web Works

> **Where this fits:** You know the roles (client, server, database). This chapter is the transport between them: what happens in the \~100ms between pressing Enter on a URL and seeing a page. Understanding these layers is what lets you debug `ECONNREFUSED`, expired certificates, and "works locally, fails in production" problems.

***

## 1. The Internet in one paragraph

The **Internet** is a very large number of independent networks that all agreed to speak the same protocols (TCP/IP). There is no central computer. It works because every device that joins agrees to the same rules for addressing (IP addresses), routing (packets get forwarded hop by hop), and reliability (TCP re-sends what is lost).

The **Web** is one _application_ that runs on top of the Internet. It adds two things: URLs to name resources, and HTTP to request them. Email, SSH, DNS and video calls all use the same Internet without being part of the Web. ("Web" ⊂ "Internet", not "Web" = "Internet".)

***

## 2. The layers, from your keyboard to the server

```
Your code / browser            ← application layer  (HTTP, JSON, HTML)
        ↓
HTTP                           ← "what am I asking for?"  (GET /users/42)
        ↓
TLS (for HTTPS)                ← "encrypt the channel"    (handshake, certificates)
        ↓
TCP                            ← "reliably deliver a byte stream"  (ports, retries, ordering)
        ↓
IP                             ← "find a route across networks"    (IP addresses, hops)
        ↓
Ethernet / Wi-Fi / fibre       ← the physical link
        ↓
   … the same stack reversed on the server …
```

### Why you should care about each layer

| Layer       | Backend symptom when it breaks                                                     |
| ----------- | ---------------------------------------------------------------------------------- |
| DNS         | `getaddrinfo ENOTFOUND api.example.com` — name → IP lookup failed                  |
| TCP/IP      | `ECONNREFUSED` (nothing listening on that port), `ETIMEDOUT` (firewall dropped it) |
| TLS         | `UNABLE_TO_VERIFY_LEAF_SIGNATURE`, `certificate has expired`                       |
| HTTP        | `404`, `415 Unsupported Media Type`, `CORS` errors                                 |
| Application | `500`, a wrong field in a JSON body, a validation error                            |

**Debugging rule:** work _down_ the stack. If DNS fails, do not debug your Express routes. The error message tells you which layer to blame — learn to read it.

***

## 3. IP addresses and ports

An **IP address** identifies a machine on a network:

* IPv4: `142.250.190.78` — 32 bits, \~4.3 billion addresses (exhausted, hence NAT).
* IPv6: `2606:4700:4700::1111` — 128 bits, effectively unlimited.
* `127.0.0.1` = **loopback**: "this machine itself". `localhost` resolves to it.
* `0.0.0.0` = **all interfaces**: "listen on every network card". This matters for us — a Node server bound to `0.0.0.0:3000` is reachable from other machines/containers, one bound to `127.0.0.1:3000` is not. (Containers and the preview environment in this workspace both require `0.0.0.0`.)

An **IP address gets you to the machine. A port gets you to the program on it.**

A **port** is a 16-bit number (0–65535) that lets one machine run many servers at once:

| Port  | Usually used by                               |
| ----- | --------------------------------------------- |
| 80    | HTTP                                          |
| 443   | HTTPS                                         |
| 22    | SSH                                           |
| 3000  | Node dev servers (convention, not a standard) |
| 5432  | PostgreSQL                                    |
| 3306  | MySQL                                         |
| 27017 | MongoDB                                       |
| 6379  | Redis                                         |

So the "address" of a service is really `IP + port`: `142.250.190.78:443`. A **socket** is the combination of local IP+port and remote IP+port that identifies one conversation.

```bash
# Which programs are listening on which ports right now?
ss -tulpn            # Linux
lsof -i -P -n | grep LISTEN   # macOS/Linux
netstat -ano | findstr LISTENING   # Windows
```

This is the command you run first when you get `EADDRINUSE` (see common-errors _(not available in this published source revision)_).

***

## 4. DNS: from a name to an IP

Computers use IP addresses; humans use names. **DNS (Domain Name System)** translates one to the other. It is a distributed, hierarchical database.

```
You ask: "where is api.shop.example.com?"
        ↓
Browser cache → OS cache → router → your ISP's resolver
        ↓
Root nameserver        ".com"                        "who handles .com?"
        ↓
TLD nameserver         "example.com"                 "who handles example.com?"
        ↓
Authoritative NS       "api.shop.example.com"        "A record = 203.0.113.10"
        ↓
Answer, cached for the record's TTL (e.g. 300 seconds)
```

### Record types you will actually touch as a backend developer

| Type    | Meaning                             | Where you use it                        |
| ------- | ----------------------------------- | --------------------------------------- |
| `A`     | name → IPv4 address                 | pointing a domain at your server        |
| `AAAA`  | name → IPv6 address                 | same, over IPv6                         |
| `CNAME` | name → another name (alias)         | `www.example.com → example.com`         |
| `MX`    | mail server for the domain          | transactional email (Resend, SES)       |
| `TXT`   | arbitrary text                      | domain verification, SPF/DKIM for email |
| `NS`    | which nameservers are authoritative | changing DNS provider                   |

Directly relevant to deployment: when you put your API behind a platform (Render, Railway, Fly.io, a load balancer), you get a hostname, and you point a `CNAME`/`A` record at it. **DNS changes are cached**, so after a change you may wait minutes to hours. That is expected, not a bug.

```bash
dig api.github.com +short       # ask DNS directly
nslookup example.com            # cross-platform
curl -v https://example.com     # shows DNS, TCP, TLS and HTTP steps
```

> **Internally:** the _hosts file_ (`/etc/hosts` on Unix, `C:\Windows\System32\drivers\etc\hosts`) is consulted before DNS. That is how `localhost` works offline, and how developers fake a domain in tests.

***

## 5. TCP: the reliable byte stream

HTTP needs to send bytes reliably, in order, without gaps. **TCP (Transmission Control Protocol)** provides exactly that: an ordered, error-checked stream of bytes between two programs.

TCP's work:

1. **Connection setup** — the three-way handshake (`SYN` → `SYN/ACK` → `ACK`). This costs one full round trip _before_ any data is sent.
2. **Segmentation and reassembly** — your JSON body is split into packets and put back together in order.
3. **Retransmission** — a lost packet is re-sent.
4. **Flow control** — the receiver says "slow down, I'm full".
5. **Teardown** — connection closed cleanly when done.

```
   CLIENT                                      SERVER
     │  ──────── SYN (seq=x) ─────────────────▶   "can we talk?"
     │  ◀─────── SYN-ACK (seq=y, ack=x+1) ────    "yes, and I can talk too"
     │  ──────── ACK (ack=y+1) ──────────────▶    "let's go"
     │  ──────── GET / HTTP/1.1 ─────────────▶
     │  ◀─────── 200 OK …  ────────────────────
     │  ──────── FIN / ACK … ────────────────▶    close
```

Two consequences you will feel in practice:

* **Latency matters more than bandwidth** for API calls. Each round trip is \~10–100ms. Making ten sequential HTTP calls instead of one batched call can add a second of delay.
* **Connections are expensive to create**, which is why servers use **keep-alive** and why databases use **connection pools** (03-databases/03-mysql/12-connection-pooling.md _(not available in this published source revision)_).

### UDP, for contrast

**UDP** sends datagrams with no handshake, no ordering, no retransmission — fast but lossy. It is used for DNS queries, video streaming, games, and **HTTP/3 (QUIC)**. If you are building a REST API, you are building on TCP.

***

## 6. TLS and HTTPS

**TLS (Transport Layer Security)** wraps TCP in encryption, integrity checking, and identity verification. **HTTPS is simply HTTP sent over a TLS connection.** Without TLS, any router between the client and the server can read and modify the traffic.

The handshake, conceptually:

```
1. Client → "hello, I support TLS 1.3, these ciphers, and I want to talk to example.com"
2. Server → "here is my certificate (issued by a CA) and my parameters"
3. Client verifies: is this certificate signed by a trusted CA? is it still valid?
   does the name match? was it revoked?
4. Both derive a shared session key (Diffie-Hellman) — the key is never sent
5. All following bytes are encrypted with that symmetric key
```

Three things a backend developer must know:

1. **Certificates chain to a trusted Certificate Authority (CA).** Browsers/clients ship with a list of trusted CAs. Self-signed certificates are not in that list, hence the scary warning. In production, **Let's Encrypt** or your platform will issue certificates for free and renew them automatically.
2. **TLS is terminated somewhere.** In production it is usually terminated at a reverse proxy or load balancer (nginx, Caddy, Cloudflare, your cloud's LB), which then forwards plain HTTP to your Node process on a private network. That is why Express apps need `app.set('trust proxy', 1)` ([02-express/20-production-architecture.md](../02-express/20-production-architecture.md)) — otherwise `req.ip` and `req.secure` report the proxy's values, not the user's.
3. **HTTPS is not optional for auth.** Cookies marked `Secure` are only sent over HTTPS. Passwords sent over plain HTTP are readable on the wire.

```bash
# Inspect a live certificate: issuer, validity, chain
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -subject -dates
```

***

## 7. What actually happens when you press Enter

Take `https://api.shop.example.com/v1/products?page=2` and follow it end to end. This is the single most useful thing to internalise from this chapter.

```
 1. Browser checks its cache and the app's service worker.
 2. Parse the URL:  scheme=https  host=api.shop.example.com  path=/v1/products  query=page=2
 
 3. If api.shop.example.com is not "preconnected", open a connection:
    a. DNS:      ask the OS resolver → returns 203.0.113.10     (~1–50 ms, cached)
    b. TCP:      three-way handshake to 203.0.113.10:443        (1 round trip)
    c. TLS:      handshake, certificate verification, key       (1–2 round trips)
 
 4. Build and send the HTTP request over the encrypted socket:
 
    GET /v1/products?page=2 HTTP/1.1
    Host: api.shop.example.com
    User-Agent: Mozilla/5.0 …
    Accept: application/json
    Authorization: Bearer eyJhbGciOi…
    Accept-Encoding: gzip, br
 
 5. The request arrives at the server's port 443, where a reverse proxy
    (nginx/Caddy/LB) is listening. It terminates TLS and forwards plain HTTP
    to Node on 127.0.0.1:3000 (or a container IP).
 
 6. Node's event loop hands the socket to your HTTP server, which parses the
    bytes into a request object.
 
 7. Express finds a matching route; middleware runs in order:
       requestLogger → rateLimiter → authenticate → validateQuery
 
 8. The controller asks the service, the service asks the database:
       SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 20;
 
 9. The database returns rows (from an index, ideally — see indexes).
 
10. The backend shapes JSON, chooses a status code, adds headers:
 
    HTTP/1.1 200 OK
    Content-Type: application/json; charset=utf-8
    Cache-Control: private, max-age=30
 
    {"data":[…20 products…],"meta":{"page":2,"total":137}}
 
11. The response travels back over the same TCP connection.
12. The client parses JSON and renders. The connection stays open for reuse
    (keep-alive) for a while.
```

### Reproduce it yourself

```bash
curl -v https://api.github.com/rate_limit
```

`-v` prints every step: DNS resolution, `Connected to … port 443`, the TLS handshake, the request headers, the response headers, and the body. If you have never read this output carefully, do it once now — you will use this exact tool for the rest of your career.

<details>

<summary>Annotated fragment of real <code>curl -v</code> output</summary>

```
* Trying 140.82.121.6:443...                  ← DNS done, connecting (TCP)
* Connected to api.github.com (140.82.121.6) port 443   ← TCP handshake complete
* ALPN: curl offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello   ← TLS started
* Server certificate:
*  subject: CN=*.github.com                   ← the name on the certificate
*  start date: Mar  6 00:00:00 2026 GMT
*  expire date: Jun  3 23:59:59 2026 GMT      ← expired certs break everything
*  issuer: C=GB; O=Sectigo Limited; CN=Sectigo…
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
> GET /rate_limit HTTP/2                       ← our request
> Host: api.github.com
> accept: application/json
< HTTP/2 200                                    ← response status
< content-type: application/json; charset=utf-8
{ "resources": { … } }                          ← body
```

</details>

***

## 8. Where this shows up in backend code

You do not implement TCP or DNS, but you _configure_ them constantly:

```js
// Bind to all interfaces so containers/proxies can reach us.
// 127.0.0.1 would only be reachable from inside this same machine.
const server = app.listen(3000, '0.0.0.0', () => {
  console.log('Listening on http://0.0.0.0:3000');
});

// Behind a reverse proxy that terminates TLS, Express must trust exactly
// one hop of X-Forwarded-* headers, or req.ip / req.protocol lie to you.
app.set('trust proxy', 1); // snippet: partial

// Ports come from the platform in production (Heroku/Render/Railway-style).
const PORT = process.env.PORT || 3000; // snippet: partial
```

And when things break, the layer tells you what to look at:

| Error                       | Layer        | First thing to check                                         |
| --------------------------- | ------------ | ------------------------------------------------------------ |
| `ENOTFOUND` / `getaddrinfo` | DNS          | Typo in hostname, wrong DNS record, no internet in container |
| `ECONNREFUSED`              | TCP          | Is the server running? Right port? Bound to 0.0.0.0?         |
| `ETIMEDOUT`                 | TCP/firewall | Security group, firewall, wrong subnet                       |
| `CERT_HAS_EXPIRED`          | TLS          | Certificate renewal job                                      |
| `EADDRINUSE`                | local        | Another process already bound that port                      |
| `413 Payload Too Large`     | HTTP         | Body parser limit vs uploaded file size                      |
| `504 Gateway Timeout`       | proxy        | Your handler is slower than the proxy's timeout              |

***

## Exercise 2.1 — Follow the packet

`curl http://localhost:4000/health` prints `curl: (7) Failed to connect to localhost port 4000: Connection refused`. List the layers you have already _successfully_ passed, and what the error rules out.

<details>

<summary>Solution</summary>

**Passed successfully:**

1. **URL parsing** — `curl` understood the scheme, host and port.
2. **DNS / hosts file** — `localhost` resolved to `127.0.0.1` (if this had failed you would see `Could not resolve host`, not "connection refused").
3. **IP layer** — the address is valid and local; no routing needed.

**Ruled out:** HTTP, TLS, application logic, routing, middleware, database — the request never got that far. Nothing on `127.0.0.1:4000` is accepting TCP connections.

**What to check, in order:**

```bash
ss -tulpn | grep 4000       # is anything listening on that port at all?
node server.js              # start the server (the usual cause in development)
```

If a server _is_ listening but on `127.0.0.1:4000` while you connect from a container or another host, you get the same error: the listener is not on the interface you are reaching. That is the `0.0.0.0` lesson.

</details>

## Exercise 2.2 — HTTPS in three sentences

Explain to a non-technical colleague why the company's API must use HTTPS even for "internal" traffic between two servers in the same cloud.

<details>

<summary>Solution</summary>

"Without HTTPS, every message — including passwords and API keys — travels in plain text, and anyone who can see network traffic (another compromised service in the same network, a misconfigured router, a cloud provider's internal tap) can read it _and silently modify it_. HTTPS also proves you are talking to the real server and not to something impersonating it, which prevents an attacker from sitting in the middle and collecting credentials. The same reasoning applies inside a private network, because 'private' only means 'harder to reach', not 'safe to read' — and one compromised machine changes everything."

</details>

***

## What's next

You have the transport. Now the actual language the client and server speak over it: **HTTP** — methods, headers, status codes, and the shape of requests and responses.

→ [03 — HTTP Basics](03-http-basics.md)
