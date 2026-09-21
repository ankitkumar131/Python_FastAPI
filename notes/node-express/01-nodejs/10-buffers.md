# 10 — Buffers

> **Where this fits:** Streams move bytes; this chapter is about what those bytes _are_ in Node. `Buffer` is the type you meet whenever data is not text: file contents, network packets, image uploads, hashes, encryption, binary protocols. Understanding encodings here prevents an entire class of "the file got corrupted" and "the password hash doesn't match" bugs later.

***

## 1. Why a separate type for binary data?

JavaScript strings are **UTF-16 sequences of characters**, not bytes. That is fine for text, but it is wrong for binary data:

* An image, a PDF, or a zip file is a sequence of arbitrary bytes (0–255), not characters.
* Converting arbitrary bytes to a JS string (and back) can be **lossy** — invalid UTF-8 sequences do not round-trip.
* Sizes are misleading: a 1 MB UTF-8 file is a \~2 MB JS string in memory (UTF-16).

So Node provides **`Buffer`**: a fixed-length sequence of raw bytes, implemented as a subclass of `Uint8Array` (since Node 4), with helpers for encodings and numeric reading/writing.

```js
// File: why-buffer.mjs
import { Buffer } from 'node:buffer';

// This looks like a string, but the bytes are not what you think.
const text = 'हिन्दी';

console.log('string length (UTF-16 code units):', text.length);        // 6
console.log('byte length (UTF-8):', Buffer.byteLength(text, 'utf8'));  // 18

const buf = Buffer.from(text, 'utf8');
console.log('buffer length:', buf.length);          // 18
console.log('round trip:', buf.toString('utf8') === text);  // true

// Now for real binary data:
const pngSignature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
console.log('PNG signature as UTF-8 is meaningless:', pngSignature.toString('utf8'));
```

```
string length (UTF-16 code units): 6
byte length (UTF-8): 18
buffer length: 18
round trip: true
PNG signature as UTF-8 is meaningless: �PNG
```

**The rule:** _text_ is a string; _bytes_ are a Buffer. Convert at the edges (when reading/writing), and be explicit about the encoding. `'utf8'` is the default, and the default being invisible is where bugs hide.

***

## 2. Creating buffers

```js
// File: create-buffers.mjs
import { Buffer } from 'node:buffer';

// 1. From a string, with an encoding
const utf8 = Buffer.from('Hello, Node!', 'utf8');
const latin1 = Buffer.from('Hello', 'latin1');
const hex = Buffer.from('48656c6c6f', 'hex');          // hex digits → bytes
const base64 = Buffer.from('SGVsbG8=', 'base64');

console.log(utf8.toString());        // Hello, Node!
console.log(hex.toString('utf8'));   // Hello
console.log(base64.toString('utf8')); // Hello

// 2. From an array of bytes
const bytes = Buffer.from([72, 101, 108, 108, 111]);
console.log(bytes.toString());       // Hello

// 3. From a Uint8Array / ArrayBuffer (for interop with web APIs)
const uint8 = new Uint8Array([1, 2, 3, 4]);
const fromUint8 = Buffer.from(uint8);
console.log(fromUint8, Buffer.isBuffer(fromUint8));   // <Buffer 01 02 03 04> true

// 4. Allocated, zero-filled — the SAFE way to create an empty buffer
const safe = Buffer.alloc(8);
console.log(safe);                   // <Buffer 00 00 00 00 00 00 00 00>

// 5. Allocated, NOT zeroed — faster, and may contain data from previous allocations
const unsafe = Buffer.allocUnsafe(8);
console.log('allocUnsafe length:', unsafe.length);   // 8 (contents are undefined — never log them)
```

> **Security note:** `Buffer.allocUnsafe` can expose **stale memory from your own process** (parts of previously used buffers: old request bodies, tokens, database rows). It is fast and legitimate when you immediately overwrite every byte — e.g. a read into a buffer. It is a vulnerability when you send the buffer without fully writing it. **`Buffer.alloc` is the default choice.**

```js
// File: unsafe-pattern.mjs
import { Buffer } from 'node:buffer';

// ❌ Leaks whatever was in memory before.
// const header = Buffer.allocUnsafe(64);
// header.write('OK');       // only 2 of 64 bytes written
// socket.write(header);     // 62 bytes of old memory are sent to the client!

// ✅ Safe: allocate zeroed, or track exactly how many bytes you wrote.
const header = Buffer.alloc(64);
const written = header.write('OK');
console.log('bytes actually written:', written);      // 2
console.log('send exactly this many bytes:', header.subarray(0, written).toString()); // OK
```

***

## 3. Reading and writing binary data

```js
// File: read-write.mjs
import { Buffer } from 'node:buffer';

const buf = Buffer.alloc(16);

// Integers (the write methods return how many bytes were written)
buf.writeUInt8(255, 0);            // 0..255
buf.writeInt8(-1, 1);              // -128..127
buf.writeUInt16BE(0x1234, 2);      // big-endian (network byte order)
buf.writeUInt16LE(0x1234, 4);      // little-endian
buf.writeInt32BE(-123456, 6);
buf.writeFloatBE(3.14159, 10);

console.log(buf);                                  // <Buffer ff ff 12 34 34 12 ff fe 1d c0 40 49 0f d0 00 00>
console.log(buf.readUInt8(0));                     // 255
console.log(buf.readInt8(1));                      // -1
console.log(buf.readUInt16BE(2).toString(16));     // 1234
console.log(buf.readUInt16LE(4).toString(16));     // 1234
console.log(buf.readInt32BE(6));                   // -123456
console.log(buf.readFloatBE(10).toFixed(5));       // 3.14159

// Strings into a buffer
buf.write('END', 12, 'utf8');
console.log(buf.toString('utf8', 12));             // END
```

**Endianness** (byte order) matters when talking to other systems. Network protocols and most file formats use **big-endian (BE)**; x86 CPUs are little-endian. `writeUInt16BE` vs `writeUInt16LE` is not a detail you can guess — read the specification of whatever format you are parsing.

### The bounds-check behaviour worth knowing

```js
// File: bounds.mjs
import { Buffer } from 'node:buffer';

const buf = Buffer.alloc(4);

// Writing beyond the end silently truncates (partial write) for strings…
const written = buf.write('abcdefgh');
console.log('bytes written:', written);            // 4 — "abcd" only

// …but numeric writes THROW when out of range:
try {
  buf.writeUInt8(300, 0);                          // 300 > 255
} catch (error) {
  console.log(error.name, '-', error.message);     // RangeError - The value of "value" is out of range…
}

try {
  buf.readUInt32BE(2);                             // needs 4 bytes from offset 2, only 2 available
} catch (error) {
  console.log(error.name, '-', error.message);     // RangeError - Attempt to access memory outside buffer bounds
}
```

***

## 4. Encodings you will actually use

```js
// File: encodings.mjs
import { Buffer } from 'node:buffer';

const original = 'Ankit says: héllo 世界 🚀';
const buf = Buffer.from(original, 'utf8');

console.log('utf8      :', buf.toString('utf8'));
console.log('hex       :', buf.toString('hex'));
console.log('base64    :', buf.toString('base64'));
console.log('base64url :', buf.toString('base64url'));
console.log('latin1    :', buf.toString('latin1'));   // lossy for non-Latin1 text

// base64 round trip — the transport encoding for binary data inside JSON/URLs/emails
const b64 = buf.toString('base64');
console.log('round trip ok:', Buffer.from(b64, 'base64').equals(buf));   // true

// base64url: URL-safe (uses - and _ instead of + and /) — what JWTs use
const b64url = buf.toString('base64url');
console.log('base64url has no + or /:', !/[+/]/.test(b64url));           // true
```

| Encoding            | Alphabet        | Use it for                                                  |
| ------------------- | --------------- | ----------------------------------------------------------- |
| `utf8`              | Multi-byte      | **Everything textual.** The default, and what HTTP/JSON use |
| `hex`               | `0-9a-f`        | Hashes, binary ids, debugging byte dumps (2 chars per byte) |
| `base64`            | `A-Za-z0-9+/`   | Embedding binary in JSON, email attachments, data URLs      |
| `base64url`         | `A-Za-z0-9-_`   | **JWT segments**, URLs, filenames (no `+`, `/`, `=`)        |
| `latin1` / `binary` | 1 byte per char | Legacy formats, byte-exact manipulation                     |
| `ascii`             | 7-bit           | Legacy; usually you want utf8                               |
| `utf16le`           | 2 or 4 bytes    | Windows APIs, some legacy file formats                      |

> **Common bug:** `buf.toString('base64')` is fine, but jamming base64 into a URL without converting to `base64url` breaks as soon as the data contains `+` or `/` (the `+` becomes a space when decoded as a query parameter). JWTs use base64url for exactly this reason.

***

## 5. The `slice`/`subarray` aliasing trap

```js
// File: slicing.mjs
import { Buffer } from 'node:buffer';

const original = Buffer.from('Hello, World!');

// ⚠️ subarray() and slice() create a VIEW over the same memory — they do not copy!
const view = original.subarray(0, 5);
view[0] = 0x4a;                        // 'J'
console.log('original after mutating the view:', original.toString());  // Jello, World!

// ✅ To get an independent copy, copy explicitly:
const copy = Buffer.from(original.subarray(0, 5));
copy[0] = 0x48;                        // 'H'
console.log('original unchanged:', original.toString());                // Jello, World!
console.log('copy independent  :', copy.toString());                    // Hello

// Practical implication: when you hand a buffer view to another function, that function
// can mutate your data. Copy at the boundaries where that matters.
```

`Buffer.prototype.slice` is deprecated in favour of `subarray` precisely because the shared-memory behaviour surprised people. Both still create views; use `Buffer.from(view)` (or `Buffer.copyBytesFrom`) when you need a copy.

***

## 6. Concatenating, comparing, searching

```js
// File: buffer-ops.mjs
import { Buffer } from 'node:buffer';

// Concatenate — the correct way to join chunks you collected
const chunks = [Buffer.from('Hello'), Buffer.from(', '), Buffer.from('World')];
const combined = Buffer.concat(chunks);
console.log(combined.toString());                        // Hello, World
console.log('total length:', combined.length);           // 12

// With a known total size, Buffer.concat is a single allocation — pass it for efficiency.
const withTotal = Buffer.concat(chunks, 13);
console.log(withTotal.length);                           // 13 (padded with a zero byte)

// Compare: -1 / 0 / 1 (lexicographic by byte)
console.log(Buffer.compare(Buffer.from('abc'), Buffer.from('abd')));   // -1
console.log(Buffer.from('abc').equals(Buffer.from('abc')));            // true

// Searching
const haystack = Buffer.from('The quick brown fox jumps over the lazy dog');
console.log('index of "brown":', haystack.indexOf('brown'));            // 10
console.log('includes "lazy"  :', haystack.includes('lazy'));           // true

// Iterating bytes
const small = Buffer.from([104, 105]);
for (const byte of small) console.log('byte:', byte);                   // 104, 105
console.log('as array:', [...small]);                                   // [ 104, 105 ]
```

> **Timing-safe comparison (security):** for secrets (tokens, MACs, password hashes), a normal `===` or `Buffer.compare` leaks information through _how long_ the comparison takes. Use `crypto.timingSafeEqual`:
>
> ```js
> import { timingSafeEqual } from 'node:crypto';
> const a = Buffer.from('expected-token');
> const b = Buffer.from('provided-token');
> // Lengths must match, so compare lengths first (this leak is unavoidable and harmless).
> const equal = a.length === b.length && timingSafeEqual(a, b);
> console.log(equal);   // false
> ```

***

## 7. Buffers in the wild

### Detecting a file type from its magic bytes

```js
// File: magic-bytes.mjs
import { readFile } from 'node:fs/promises';

const SIGNATURES = [
  { type: 'png', bytes: [0x89, 0x50, 0x4e, 0x47] },
  { type: 'jpg', bytes: [0xff, 0xd8, 0xff] },
  { type: 'gif', bytes: [0x47, 0x49, 0x46, 0x38] },
  { type: 'pdf', bytes: [0x25, 0x50, 0x44, 0x46] },
  { type: 'zip', bytes: [0x50, 0x4b, 0x03, 0x04] },
];

/** Read the first bytes of a file and identify it — never trust the extension alone. */
export async function sniffFileType(filePath) {
  const handle = await readFile(filePath);              // fine for small files
  const head = handle.subarray(0, 8);
  const match = SIGNATURES.find((sig) =>
    sig.bytes.every((byte, index) => head[index] === byte)
  );
  return match?.type ?? 'unknown';
}

// Create a tiny file to test with, then sniff it.
import { writeFile } from 'node:fs/promises';
import { Buffer } from 'node:buffer';
await writeFile('./sample.bin', Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]));
console.log('detected type:', await sniffFileType('./sample.bin'));   // png
```

This is real validation: a user uploading `invoice.pdf` that actually starts with `MZ` (a Windows executable) is a security event, not a file-type quirk.

### Hashing (used for passwords, checksums, ETags)

```js
// File: hashing.mjs
import { createHash, randomBytes, scryptSync, timingSafeEqual } from 'node:crypto';

// 1. Fast hashes (checksums, ETags, integrity) — NOT for passwords.
const sha256 = createHash('sha256').update('hello').digest('hex');
console.log('sha256:', sha256);
console.log('length:', sha256.length);                 // 64 hex chars = 32 bytes

// 2. Integrity check of a file-like buffer
const content = Buffer.from('the file contents');
const etag = createHash('sha256').update(content).digest('base64url').slice(0, 16);
console.log('etag:', etag);

// 3. Password hashing — slow by design (see 04-authentication/02)
const salt = randomBytes(16);                          // unique per user
const derived = scryptSync('user-password', salt, 64);
const stored = `${salt.toString('hex')}:${derived.toString('hex')}`;
console.log('stored credential length:', stored.length);

// Verification:
function verifyPassword(password, storedCredential) {
  const [saltHex, hashHex] = storedCredential.split(':');
  const salt2 = Buffer.from(saltHex, 'hex');
  const expected = Buffer.from(hashHex, 'hex');
  const actual = scryptSync(password, salt2, expected.length);
  return timingSafeEqual(expected, actual);
}

console.log('correct password:', verifyPassword('user-password', stored));   // true
console.log('wrong password  :', verifyPassword('user-password!', stored));  // false
```

Note what the Buffer API enabled here: hex encoding to store binary in a string column, and `timingSafeEqual` for a comparison that does not leak. Password hashing in depth: 04-authentication/02-password-hashing.md _(not available in this published source revision)_.

### Receiving binary in an Express route

```js
// File: binary-route.example.js
// Express gives you a Buffer for raw bodies — needed for webhooks with binary payloads.
app.post(
  '/webhooks/binary',
  express.raw({ type: 'application/octet-stream', limit: '5mb' }),
  (req, res) => {
    // req.body is a Buffer here, not an object.
    if (!Buffer.isBuffer(req.body)) {
      return res.status(415).json({ error: { code: 'UNSUPPORTED_MEDIA_TYPE' } });
    }

    // Verify a signature over the EXACT bytes (never over a re-serialised object).
    const signature = req.get('x-signature') ?? '';
    const expected = createHash('sha256').update(req.body).digest('hex');

    if (
      signature.length !== expected.length ||
      !timingSafeEqual(Buffer.from(signature), Buffer.from(expected))
    ) {
      return res.status(401).json({ error: { code: 'INVALID_SIGNATURE' } });
    }

    return res.status(204).end();
  }
);
```

***

## 8. Common mistakes

| Mistake                                                         | Symptom                                                 | Fix                                                         |
| --------------------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| Treating a binary file as UTF-8 text                            | Corrupted output, replacement characters (`�`)          | Work with Buffers; only decode when the data really is text |
| Using `Buffer.allocUnsafe` and sending the whole buffer         | Stale memory (secrets) leaked to clients                | `Buffer.alloc`, or send only the bytes you wrote            |
| `buf.slice()` expecting a copy                                  | Unexpected mutations elsewhere                          | `Buffer.from(view)` for a real copy                         |
| `buf.toString()` with the wrong encoding                        | `UnicodeDecodeError`-style garbage                      | Be explicit: `toString('utf8')`                             |
| Comparing secrets with `===`                                    | Timing side channel                                     | `crypto.timingSafeEqual`                                    |
| Byte length computed from `string.length`                       | Multi-byte characters miscounted (Content-Length wrong) | `Buffer.byteLength(str)`                                    |
| Building a large body by `+=` on strings                        | Slow, memory-heavy                                      | Collect chunks in an array, `Buffer.concat` once            |
| Forgetting that numeric writes throw but string writes truncate | Silent data loss vs surprise crash                      | Bounds-check; assert `written === expected`                 |
| Assuming a chunk boundary is a message boundary                 | Protocol parsing bugs                                   | Frame your data (length prefixes/delimiters)                |
| Base64 in URLs without `base64url`                              | `+` becomes a space; 404s                               | `toString('base64url')`                                     |

***

## Exercise 10.1 — Build a binary file header reader

Write `readPngHeader(filePath)` that reads only the first 33 bytes of a PNG and returns `{ width, height, bitDepth, colorType }`. PNG layout: 8-byte signature, then a chunk length (4 bytes BE), the ASCII type `IHDR` (4 bytes), then width (4 bytes BE), height (4 bytes BE), bit depth (1 byte), colour type (1 byte).

<details>

<summary>Solution</summary>

```js
// File: png-header.mjs
import { open } from 'node:fs/promises';
import { Buffer } from 'node:buffer';

/**
 * Read a PNG's IHDR chunk by reading only the first 33 bytes of the file.
 * Demonstrates: precise byte offsets, big-endian reads, and why we do not
 * read the whole file (a 40 MB image would be pointless to load just for a header).
 */
export async function readPngHeader(filePath) {
  const fileHandle = await open(filePath, 'r');
  try {
    const header = Buffer.alloc(33);                 // 8 + 4 + 4 + 4 + 4 + 1 + 1 = 26…
    const { bytesRead } = await fileHandle.read(header, 0, 26, 0);
    if (bytesRead < 26) throw new Error('File is too small to be a PNG');

    const signature = header.subarray(0, 8);
    const expected = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
    if (!signature.equals(expected)) {
      throw new Error('Not a PNG file (bad signature)');
    }

    const chunkLength = header.readUInt32BE(8);
    const chunkType = header.toString('ascii', 12, 16);
    if (chunkType !== 'IHDR') {
      throw new Error(`Expected IHDR as the first chunk, found ${chunkType}`);
    }

    return {
      chunkLength,                                   // should be 13 for IHDR
      width: header.readUInt32BE(16),
      height: header.readUInt32BE(20),
      bitDepth: header.readUInt8(24),
      colorType: header.readUInt8(25),
      colorTypeName: COLORS[header.readUInt8(25)] ?? 'unknown',
    };
  } finally {
    await fileHandle.close();                        // ALWAYS close the handle
  }
}

const COLORS = {
  0: 'grayscale',
  2: 'truecolor (RGB)',
  3: 'indexed (palette)',
  4: 'grayscale + alpha',
  6: 'truecolor + alpha (RGBA)',
};

// ---------------------------------------------------------------------------
// Build a valid 1×1 RGBA PNG so this runs with no external files.
// ---------------------------------------------------------------------------
import { writeFile } from 'node:fs/promises';
import { deflateSync, crc32 } from 'node:zlib';

function crcChunk(type, data) {
  const typeBuf = Buffer.from(type, 'ascii');
  const body = Buffer.concat([typeBuf, data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body) >>> 0, 0);

  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  return Buffer.concat([length, body, crc]);
}

const ihdrData = Buffer.alloc(13);
ihdrData.writeUInt32BE(1, 0);      // width
ihdrData.writeUInt32BE(1, 4);      // height
ihdrData.writeUInt8(8, 8);         // bit depth
ihdrData.writeUInt8(6, 9);         // colour type: RGBA
ihdrData.writeUInt8(0, 10);        // compression
ihdrData.writeUInt8(0, 11);        // filter
ihdrData.writeUInt8(0, 12);        // interlace

const rawScanline = Buffer.from([0x00, 0xff, 0x00, 0x00, 0xff]); // filter byte + RGBA pixel
const idatData = deflateSync(rawScanline);

const png = Buffer.concat([
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
  crcChunk('IHDR', ihdrData),
  crcChunk('IDAT', idatData),
  crcChunk('IEND', Buffer.alloc(0)),
]);

await writeFile('./tiny.png', png);
console.log('created tiny.png:', png.length, 'bytes');

console.log(await readPngHeader('./tiny.png'));
```

Expected output:

```
created tiny.png: 70 bytes
{
  chunkLength: 13,
  width: 1,
  height: 1,
  bitDepth: 8,
  colorType: 6,
  colorTypeName: 'truecolor + alpha (RGBA)'
}
```

**Points worth remembering**

| Detail                                              | Why                                                                           |
| --------------------------------------------------- | ----------------------------------------------------------------------------- |
| `fileHandle.read(buffer, offset, length, position)` | Reads _exactly_ the bytes you need — no full-file load                        |
| `try/finally` to close the handle                   | File descriptors leak; `EMFILE` lurks                                         |
| `readUInt32BE`                                      | PNG is big-endian, per its specification — you must verify this, never assume |
| Signature check first                               | Rejecting a non-PNG before parsing offsets is cheap and safe                  |
| `subarray` for the signature                        | A view is enough; no need to copy 8 bytes                                     |
| The CRC32 helper                                    | Shows how checksums are embedded in real formats (PNG uses CRC-32 per chunk)  |

**Sanity check to run yourself:** `file tiny.png` should report `PNG image data, 1 x 1, 8-bit/color RGBA`. This is the habit that matters — after doing binary parsing, verify with an independent tool.

</details>

## Exercise 10.2 — Compare buffers correctly

Given two buffers that should be identical, explain why `a === b` and `a == b` are both `false`, and write a function `buffersEqual(a, b)` that handles the edge cases.

<details>

<summary>Solution</summary>

```js
// File: buffer-equality.mjs
import { Buffer } from 'node:buffer';

const a = Buffer.from('hello');
const b = Buffer.from('hello');

// `===` compares object REFERENCES, not contents: two different objects are never ===.
console.log(a === b);                       // false
// `==` does the same for objects (no coercion happens between two objects).
console.log(a == b);                        // false

// Even `JSON.stringify` is a trap: it serialises a Buffer as { type: 'Buffer', data: [...] },
// which is both verbose and slow — avoid it for comparisons.
console.log(a.toString('utf8') === b.toString('utf8'));   // true (works, but allocates strings)

// The correct primitive:
console.log(a.equals(b));                   // true — length-aware byte comparison, no allocation

/**
 * Content equality for Buffers/typed arrays, with the edge cases handled.
 *  - Accepts Buffer, Uint8Array, or a hex/utf8 string for convenience.
 *  - Returns false (never throws) for mismatched lengths during a timing-safe comparison.
 *  - Uses crypto.timingSafeEqual when both sides are Buffers of equal length, so the
 *    function is safe to use with secrets.
 */
import { timingSafeEqual } from 'node:crypto';

function toBuffer(value, encoding = 'utf8') {
  if (Buffer.isBuffer(value)) return value;
  if (value instanceof Uint8Array) return Buffer.from(value);
  if (typeof value === 'string') return Buffer.from(value, encoding);
  throw new TypeError('buffersEqual expects Buffer, Uint8Array or string');
}

export function buffersEqual(a, b, { secure = false, encoding = 'utf8' } = {}) {
  const left = toBuffer(a, encoding);
  const right = toBuffer(b, encoding);

  // Length differences can be short-circuited (length is not usually secret).
  if (left.length !== right.length) return false;
  if (left.length === 0) return true;                 // two empty buffers are equal

  return secure ? timingSafeEqual(left, right) : left.equals(right);
}

console.log(buffersEqual('hello', 'hello'));                          // true
console.log(buffersEqual('hello', 'hellO'));                          // false
console.log(buffersEqual('', ''));                                    // true
console.log(buffersEqual(Buffer.alloc(0), Buffer.alloc(0)));          // true
console.log(buffersEqual(Buffer.from([1, 2]), Buffer.from([1, 2, 3]))); // false
console.log(buffersEqual('48656c6c6f', 'hello', { encoding: 'hex' })); // true
console.log(buffersEqual('secret-token', 'secret-token', { secure: true })); // true
console.log(buffersEqual('secret-token', 'secret-tokeN', { secure: true })); // false

// Why `secure: true` exists:
console.log(buffersEqual('aaaa', 'aaab'));                       // false (fast, but leaks position)
console.log(buffersEqual('aaaa', 'aaab', { secure: true }));     // false (constant time)
```

**Edge cases the function covers, and why each matters**

| Case                              | Naive code                                     | Correct behaviour                |
| --------------------------------- | ---------------------------------------------- | -------------------------------- |
| Same content, different objects   | `a === b` → false                              | Compare bytes                    |
| Different lengths                 | `timingSafeEqual` **throws** if lengths differ | Return `false` before calling it |
| Empty buffers                     | Some libraries throw                           | Return `true` (both empty)       |
| `Uint8Array` from the web APIs    | `Buffer.isBuffer(uint8)` is false              | Accept `Uint8Array` too          |
| Strings with an explicit encoding | Hex/base64 comparisons fail silently           | `encoding` parameter             |
| Secrets                           | `equals()` is fast (and leaks timing)          | `secure: true`                   |

**The transferable lessons**

1. **`===` on objects compares references.** For Buffers, use `.equals()`; for `Date`s, compare `.getTime()`; for plain objects, compare the fields you care about.
2. **`timingSafeEqual` throws on length mismatch** — check lengths first. That is a real crash you would otherwise ship into your token-verification path.
3. **Never `JSON.stringify` a Buffer** to compare or store it — use hex/base64.

</details>

***

## What's next

You now know how bytes work. Time to put them on the wire: building an HTTP server with Node's built-in `http` module — by hand, so that Express's convenience becomes visible instead of magical.

→ [11 — The http Module](11-http-module.md)
