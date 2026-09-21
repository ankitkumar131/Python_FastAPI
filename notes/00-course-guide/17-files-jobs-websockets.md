# 17 — Files, streaming, background tasks and WebSockets

[Previous](16-middleware-and-cors.md) · [Course map](./) · [Next](18-testing.md)

## Part A: forms and files — what problem do they solve?

JSON describes structured values but is inefficient for raw binary uploads. **Multipart form data** splits one request into labelled parts, letting text fields and file content travel together. `Form()` declares a text form field; `UploadFile` represents an uploaded file with metadata and a spooled file (initially memory, potentially temporary disk for larger data). `bytes` input reads the whole content into memory; UploadFile allows chunk-oriented handling.

Use multipart when accepting browser forms with files. A request cannot simultaneously have an ordinary JSON body and a multipart body as independent encodings. If a multipart part contains JSON text, parse/validate that part explicitly and document the contract.

`python-multipart` is the parser dependency, included by our standard requirements. Install independently with `python -m pip install python-multipart` if needed. Do not install a different package merely named multipart.

### Security before uploading

A client-controlled filename can contain paths or deceptive extensions. A claimed MIME type (Multipurpose Internet Mail Extensions media type, such as image/png) is not proof of content. Generate server-owned storage names, enforce total/front-door limits, validate content signatures/formats, scan where appropriate and store outside executable/public paths. A route-level size check after multipart parsing does **not** prevent bandwidth or temporary-disk exhaustion during parsing. Production proxies/platforms need early request size limits too.

## Part B: background tasks — after response does not mean durable

`BackgroundTasks` collects small functions to run after the response has been sent. It exists so a client need not wait for a noncritical follow-up such as lightweight telemetry. Tasks still run in the web process. Synchronous task functions use the thread mechanism; async tasks must avoid blocking. Process crashes can lose work, exceptions cannot turn an already-sent 200 into a 500, and one failed task can prevent later tasks in the same sequence from running.

Use it only where this loss model is acceptable. Payments, guaranteed email delivery, video processing and long-running jobs need a durable queue/worker design. A **queue** durably holds work messages; a **worker** consumes them outside the web process. Systems such as Celery or a managed queue add retries and scheduling, but “exactly once” business effects still require idempotent processing and deduplication.

## Part C: streaming and WebSockets

A **streaming response** sends chunks over time rather than assembling the whole body first. `StreamingResponse` accepts an iterator/async iterator. `FileResponse` serves an existing file with file-specific handling; use server-controlled paths or strict access checks, never arbitrary filesystem paths from callers. Streaming errors after response headers cannot change the already-sent status code. Avoid holding a database session/transaction open for a very slow download unless necessary.

A **WebSocket** starts with an HTTP handshake and becomes a bidirectional, long-lived message connection. Use it for chat, collaboration or live control where both sides send messages. Ordinary HTTP is simpler for occasional reads/writes. **Server-Sent Events (SSE)** is another option for one-way server-to-browser text events over an HTTP stream; clients use EventSource and a documented reconnect strategy.

WebSocket `accept` agrees to the connection; `receive_text` waits for a message; `send_text` replies; `WebSocketDisconnect` indicates closure. WebSockets need their own authentication/authorization and Origin validation. Browser CORS middleware does not automatically protect WebSocket origins. Broadcast lists kept in memory are per worker; multi-worker chat needs shared pub/sub (publish/subscribe message distribution).

## Complete bounded teaching example

Run `python -m uvicorn examples.io_features:app --reload`. It accepts small text uploads, schedules noncritical logging, streams three numbers and provides an **unauthenticated local echo socket**. Do not expose the echo unchanged publicly. No upload is saved, avoiding accidental filesystem exposure.

## Example

### File: `examples/io_features.py`

```python
import asyncio
import logging
from typing import Annotated
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

app = FastAPI()
logger = logging.getLogger(__name__)
MAX_UPLOAD = 1024 * 1024

def record_upload(size: int):
    logger.info("upload accepted size=%s", size)

@app.post("/uploads")
async def upload(background: BackgroundTasks, file: Annotated[UploadFile, File()], label: Annotated[str, Form(min_length=1, max_length=80)]):
    size = 0
    try:
        if file.content_type != "text/plain":
            raise HTTPException(415, "Only text/plain accepted in this lesson")
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > MAX_UPLOAD:
                raise HTTPException(413, "File too large")
    finally:
        await file.close()
    background.add_task(record_upload, size)
    return {"label": label, "bytes": size}

async def number_chunks():
    for number in range(3):
        yield f"{number}\n"
        await asyncio.sleep(0.01)

@app.get("/numbers")
async def numbers():
    return StreamingResponse(number_chunks(), media_type="text/plain")

@app.websocket("/ws/echo")
async def echo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            if len(text) > 1000:
                await websocket.close(code=1009)
                return
            await websocket.send_text(f"echo: {text}")
    except WebSocketDisconnect:
        return
```

## Code Explanation

### Line 1

Provide cooperative timers for the stream.

### Line 2

Emit noncritical events without saving uploaded contents.

### Line 3

Attach multipart declarations to parameter types.

### Line 4

Import file/form parsing, background work and socket tools.

### Line 5

Send iterator-produced chunks as one HTTP response.

### Line 6

This blank line separates logical parts; Python does not execute it.

### Line 7

Create this lesson's app.

### Line 8

Use a named logger controlled by deployment configuration.

### Line 9

Accept at most one mebibyte of file content at the application layer.

### Line 10

This blank line separates logical parts; Python does not execute it.

### Line 11

Pass stable scalar data, not request-owned files or sessions, to background work.

### Line 12

Log only metadata; this follow-up is not guaranteed to survive a process crash.

### Line 13

This blank line separates logical parts; Python does not execute it.

### Line 14

Accept multipart form input, not a separate JSON body.

### Line 15

Parse the file/text parts and receive a task collection.

### Line 16

Track actual content bytes.

### Line 17

Ensure resource closure on success or failure.

### Line 18

Apply a preliminary declared-media-type policy; this does not verify actual file contents.

### Line 19

Reject unsupported declarations.

### Line 20

Read 64 KiB chunks; the assignment expression binds each chunk and stops on empty bytes.

### Line 21

Accumulate actual content size.

### Line 22

Enforce the accepted-file limit; earlier multipart parsing still needs front-door limits.

### Line 23

Reject oversized content.

### Line 24

Cleanup occurs regardless of the branch taken.

### Line 25

Release the request-owned spooled file.

### Line 26

Schedule the callable with a scalar argument, without invoking it yet.

### Line 27

Return metadata before best-effort follow-up runs.

### Line 28

This blank line separates logical parts; Python does not execute it.

### Line 29

Define an async generator producing response chunks.

### Line 30

Iterate zero, one and two.

### Line 31

Yield one newline-terminated chunk, pausing the generator.

### Line 32

Cooperatively simulate waiting without blocking the loop.

### Line 33

This blank line separates logical parts; Python does not execute it.

### Line 34

Register a normal HTTP streaming operation.

### Line 35

Construct the response without collecting all chunks first.

### Line 36

Consume and send the async iterator incrementally.

### Line 37

This blank line separates logical parts; Python does not execute it.

### Line 38

Register a socket operation, not a JSON GET route.

### Line 39

Receive the handshake and connection object.

### Line 40

Accept this explicitly unauthenticated local teaching connection.

### Line 41

Treat normal client disconnect as lifecycle completion.

### Line 42

Receive multiple messages on one connection.

### Line 43

Wait cooperatively for a text message.

### Line 44

Apply an application limit after receipt; configure server limits to protect allocation too.

### Line 45

Close with message-too-big status.

### Line 46

Stop this handler.

### Line 47

Reply on the same connection.

### Line 48

Catch expected closure.

### Line 49

Exit without retaining connection state.

## Test it

```bash
printf 'hello' > sample.txt
curl -i -F 'label=notes' -F 'file=@sample.txt;type=text/plain' http://127.0.0.1:8000/uploads
curl -N http://127.0.0.1:8000/numbers
```

Line 1 writes five bytes. Line 2 uses `-F` for multipart parts; `@` reads file content and `type` declares media type. Expect `{"label":"notes","bytes":5}`. Line 3 disables curl buffering so lines 0, 1, 2 appear incrementally. PowerShell users can create the file in an editor; encoding/newline choices can change its byte count.

`/docs` provides an upload chooser, but WebSockets are not ordinary OpenAPI request/response operations. Use the automated socket test in chapter 18, or run in the browser console on the app's own origin:

```javascript
const scheme = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(`${scheme}://${location.host}/ws/echo`);
socket.onopen = () => socket.send("hello");
socket.onmessage = (event) => console.log(event.data);
```

Line 1 chooses encrypted wss on HTTPS. Line 2 uses the current browser host rather than the server's localhost. Line 3 sends only after handshake. Line 4 prints `echo: hello`. `const` declares a JavaScript binding; arrow functions are callbacks invoked when events occur. Close using `socket.close()`.

## What happens internally / production boundaries

Multipart parsing creates a spooled file; the handler reads bounded chunks, checks its policy and closes it. It returns metadata, then its task collection runs the logging function. Streaming consumes yielded chunks over time. WebSockets retain connection state until closure.

For production WebSockets validate an exact Origin allowlist, authenticate the handshake using an appropriate session or short-lived one-time ticket, authorize every room/action, and set frame/message/rate/idle limits. The browser WebSocket constructor cannot freely set an Authorization header; do not solve that by putting long-lived tokens in URLs. Proxies must forward upgrades. Use **backpressure**, slowing production to match consumption, instead of building unbounded message queues for slow clients.

For guaranteed jobs use a transactionally stored **outbox**: write the business change and a pending event in one database transaction, then have a relay publish pending events to a durable queue. Consumers deduplicate event IDs. This closes the “database committed but enqueue failed” gap; it does not make external effects automatically exactly-once.

## When to use / not use; common mistakes and best practices

Do not use `background.add_task(send_email())`; pass the function and arguments. Do not lend a closed UploadFile or request session to a later task. Avoid BackgroundTasks for hours of CPU work. `await file.read()` without a bound can materialize an enormous upload. Extensions, MIME claims and Content-Length are untrusted. Do not choose WebSockets for a rarely changing status page if polling or SSE is simpler.

## Practice

**Beginner:** Upload hello and verify five bytes. **Intermediate:** Upload a text file exceeding one MiB and expect 413; declared image type should give 415. **Challenge:** Guarantee order-confirmation work survives a web-process crash after the order commits.

## Expected Result / Solution

The complete endpoint implements the first two tasks. Create oversized content with `python -c "from pathlib import Path; Path('large.txt').write_bytes(b'x' * (1024 * 1024 + 1))"` and substitute large.txt in curl. This writes exactly one byte over the limit; do not commit this local artifact.

Challenge: write order and outbox rows in one transaction, commit before returning success, publish through a retrying relay and deduplicate in the consumer by event ID. Expose a status resource for progress. A BackgroundTasks callback cannot satisfy the durability requirement.

## Summary

Request uploads, streaming responses, best-effort tasks, durable jobs and bidirectional sockets have different ownership and reliability guarantees. Choose by those guarantees, not by novelty.
