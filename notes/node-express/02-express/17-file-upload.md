# 17 — File Uploads

> **Where this fits:** Every endpoint so far accepted JSON. Files arrive as `multipart/form-data`, which `express.json()` deliberately ignores. This chapter adds the parser, then spends most of its length on the part that actually matters: **an uploaded file is untrusted input** — its name, its type and its contents can all be hostile.

***

## 1. Why files need `multipart/form-data`

JSON carries text. A file is binary, potentially megabytes, and must not be base64-inflated (which adds 33% and forces the whole thing into memory). `multipart/form-data` splits the request body into labelled parts, each with its own headers:

```
POST /api/v1/notes/n1/attachments HTTP/1.1
Content-Type: multipart/form-data; boundary=----XxBoundaryXx

------XxBoundaryXx
Content-Disposition: form-data; name="title"

Quarterly report
------XxBoundaryXx
Content-Disposition: form-data; name="file"; filename="report.pdf"
Content-Type: application/pdf

%PDF-1.7
...binary bytes...
------XxBoundaryXx--
```

|                  | JSON body                    | Multipart body                                        |
| ---------------- | ---------------------------- | ----------------------------------------------------- |
| Content types    | `application/json`           | `multipart/form-data`                                 |
| Binary data      | Not without base64 inflation | Native, streamed                                      |
| Parsed by        | `express.json()`             | A multipart parser (`multer`, `busboy`, `formidable`) |
| Fields end up in | `req.body`                   | `req.body` **and** `req.file`/`req.files`             |
| Streaming        | Not really                   | Yes — bytes can go straight to disk or object storage |
| Typical use      | Data                         | Files + accompanying fields                           |

```js
// File: what-express-gives-you.mjs
import express from 'express';
import multer from 'multer';

const app = express();
app.use(express.json());

// Without a multipart parser, a multipart request leaves req.body EMPTY
// (express.json() sees a different Content-Type and passes the request through).
app.post('/no-parser', (req, res) => {
  res.json({ body: req.body ?? null, file: req.file ?? null });
});

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 1024 } });

app.post('/with-parser', upload.single('file'), (req, res) => {
  res.json({
    body: req.body,
    file: req.file
      ? { originalname: req.file.originalname, mimetype: req.file.mimetype, size: req.file.size }
      : null,
  });
});

app.listen(3000, () => console.log('http://localhost:3000'));
```

```bash
echo 'hello' > /tmp/note.txt
curl -s -X POST localhost:3000/no-parser   -F 'title=Hello' -F 'file=@/tmp/note.txt'   # {"body":null,"file":null}
curl -s -X POST localhost:3000/with-parser -F 'title=Hello' -F 'file=@/tmp/note.txt'   # body + file metadata
```

```
{"body":null,"file":null}
{"body":{"title":"Hello"},"file":{"originalname":"note.txt","mimetype":"text/plain","size":6}}
```

> **A non-multipart request passes straight through multer without any error.** Verified behaviour: a JSON POST to a route with `upload.single('file')` reaches the controller with `req.file === undefined` and an empty body. **Your controller must reject a missing file explicitly** — do not assume the parser guarantees one.

***

## 2. `multer` — install, and why version 2

```bash
npm install multer
```

| Version                        | Status  | Why it matters                                                            |
| ------------------------------ | ------- | ------------------------------------------------------------------------- |
| `1.4.x` (and the `-lts` forks) | Legacy  | 2025 advisories for denial-of-service via malformed multipart bodies      |
| **`2.x`**                      | Current | Fixes those DoS paths; requires Node 10.16+; API unchanged for normal use |

Multer gives you three things: **parsing** (streaming multipart into files/fields), **limits** and **filtering hooks**. Everything else — where the file ends up, what it may contain, who may download it — is your responsibility.

| Storage engine             | What `req.file` contains              | Use when                                                              |
| -------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| `multer.memoryStorage()`   | `buffer` (the whole file in RAM)      | Small files processed immediately (image resize, virus scan, hashing) |
| `multer.diskStorage()`     | `path`, `destination`, `filename`     | Files written to local disk before/while processing                   |
| A custom engine            | Whatever you implement                | Streaming to S3/GCS/Azure without touching disk                       |
| `multer()` with no options | Disk storage in the OS temp directory | The default — easiest to misuse, and it leaves temp files behind      |

***

## 3. Upload shapes and limits

```js
// File: src/middleware/upload.js
import multer from 'multer';
import { AppError } from '../utils/AppError.js';

const ALLOWED_DECLARED_TYPES = new Set(['image/png', 'image/jpeg', 'application/pdf']);

/**
 * Memory storage keeps the bytes in RAM so we can sniff them BEFORE writing anything.
 * Only safe because every request is capped by `limits.fileSize`.
 */
export function createImageUpload({ maxFileSizeBytes = 2 * 1024 * 1024, maxFiles = 3 } = {}) {
  return multer({
    storage: multer.memoryStorage(),

    limits: {
      fileSize: maxFileSizeBytes,   // bytes per file — the single most important limit
      files: maxFiles,              // files per request
      fields: 10,                   // non-file parts
      parts: 20,                    // total parts (files + fields)
      fieldNameSize: 100,           // prevents absurd field names
      fieldSize: 1024 * 1024,       // bytes per non-file field
    },

    fileFilter(req, file, callback) {
      // 1. The client-declared type — a cheap first filter, NOT a security check.
      if (!ALLOWED_DECLARED_TYPES.has(file.mimetype)) {
        return callback(new AppError('Only PNG, JPEG and PDF files are accepted', {
          statusCode: 422,
          code: 'UNSUPPORTED_MEDIA_TYPE',
          details: { declaredType: file.mimetype },
        }));
      }

      // 2. The filename extension — also client-controlled, but a mismatch is suspicious.
      if (!/\.(png|jpe?g|pdf)$/i.test(file.originalname)) {
        return callback(new AppError('The file extension does not match an accepted type', {
          statusCode: 422,
          code: 'UNSUPPORTED_MEDIA_TYPE',
        }));
      }

      return callback(null, true);   // accept provisionally; content is checked later
    },
  });
}
```

```js
// File: src/routes/noteRoutes.js (excerpt) — the three mounting styles
import { Router } from 'express';

export function createNoteRouter({ controller, upload }) {
  const router = Router();

  // 1. One file with a known field name → req.file
  router.post('/:id/cover', upload.single('cover'), controller.uploadCover);

  // 2. Many files, all the same field name → req.files (an array)
  router.post('/:id/photos', upload.array('photos', 4), controller.uploadPhotos);

  // 3. Several named fields → req.files = { cover: [...], gallery: [...] }
  router.post('/:id/media', upload.fields([
    { name: 'cover', maxCount: 1 },
    { name: 'gallery', maxCount: 3 },
  ]), controller.uploadMedia);

  return router;
}
```

> **Never use `upload.any()`.** It accepts files under _any_ field name, so the router's contract is invisible and an attacker can send files your code never expects. Name every field.

```bash
# Single file + a text field
curl -s -X POST localhost:3000/api/v1/notes/n1/cover \
  -H 'Authorization: Bearer $TOKEN' \
  -F 'cover=@/tmp/photo.png;type=image/png' \
  -F 'caption=Front door'

# Two files under the same field name
curl -s -X POST localhost:3000/api/v1/notes/n1/photos \
  -H 'Authorization: Bearer $TOKEN' \
  -F 'photos=@/tmp/a.png' -F 'photos=@/tmp/b.png'
```

### `MulterError` codes → HTTP statuses

```js
// File: src/middleware/uploadErrors.js
import multer from 'multer';

const MULTER_STATUS = new Map([
  ['LIMIT_FILE_SIZE', { statusCode: 413, code: 'PAYLOAD_TOO_LARGE', message: 'The file is too large' }],
  ['LIMIT_FILE_COUNT', { statusCode: 422, code: 'TOO_MANY_FILES', message: 'Too many files in one request' }],
  ['LIMIT_PART_COUNT', { statusCode: 413, code: 'TOO_MANY_PARTS', message: 'Too many parts in the upload' }],
  ['LIMIT_FIELD_COUNT', { statusCode: 413, code: 'TOO_MANY_FIELDS', message: 'Too many form fields' }],
  ['LIMIT_FIELD_KEY', { statusCode: 413, code: 'FIELD_NAME_TOO_LONG', message: 'A field name is too long' }],
  ['LIMIT_FIELD_VALUE', { statusCode: 413, code: 'FIELD_VALUE_TOO_LARGE', message: 'A field value is too large' }],
  ['LIMIT_UNEXPECTED_FILE', { statusCode: 422, code: 'UNEXPECTED_FILE_FIELD', message: 'Unexpected file field' }],
]);

/** Convert a thrown MulterError into the API's error envelope. Call from the error handler. */
export function fromMulterError(error) {
  if (!(error instanceof multer.MulterError)) return null;      // not ours — let the next mapper try

  const mapped = MULTER_STATUS.get(error.code) ?? {
    statusCode: 400,
    code: 'UPLOAD_REJECTED',
    message: 'The upload was rejected',
  };

  return { ...mapped, details: { field: error.field } };
}
```

Verified errors from `multer` 2.x, exactly as they reach an error handler:

| Trigger                               | `error.name` / `error.code`             | `error.message`                                  |
| ------------------------------------- | --------------------------------------- | ------------------------------------------------ |
| `limits.fileSize` exceeded            | `MulterError` / `LIMIT_FILE_SIZE`       | `File too large`                                 |
| More files than `limits.files`        | `MulterError` / `LIMIT_FILE_COUNT`      | `Too many files`                                 |
| A file under an unexpected field name | `MulterError` / `LIMIT_UNEXPECTED_FILE` | `Unexpected file field`                          |
| `fileFilter` rejected the file        | your own error                          | your message (`Zip files are not allowed` above) |

> **A rejection in `fileFilter` can still leave earlier files fully written to disk** when using disk storage, and memory storage still holds them in RAM for the rest of the request. Cleanup is your job — see §7.

***

## 4. Verifying what the file _actually_ is

`file.mimetype` and `file.originalname` are **client-supplied strings**. A `.php` script renamed to `avatar.png` with `Content-Type: image/png` satisfies any check that only looks at those values.

The fix is to read the **magic bytes** — the fixed byte signature at the start of the file. The `file-type` package (22.x, ESM-only) does this for hundreds of formats:

```bash
npm install file-type
```

```js
// File: src/utils/fileSignature.js
import { fileTypeFromBuffer } from 'file-type';
import { AppError } from './AppError.js';

const ALLOWED = new Map([
  ['png', 'image/png'],
  ['jpg', 'image/jpeg'],
  ['pdf', 'application/pdf'],
]);

/**
 * Sniffs the real type from the first bytes of the buffer.
 * Returns { extension, mime } or throws a 422 — never trust the client's claim.
 */
export async function assertRealType(buffer) {
  const detected = await fileTypeFromBuffer(buffer);

  if (!detected || !ALLOWED.has(detected.ext)) {
    throw new AppError('The file content does not match an accepted type', {
      statusCode: 422,
      code: 'UNSUPPORTED_MEDIA_TYPE',
      details: { detected: detected ? `${detected.ext} (${detected.mime})` : 'unrecognised' },
    });
  }

  return { extension: detected.ext === 'jpg' ? 'jpg' : detected.ext, mime: ALLOWED.get(detected.ext) };
}
```

```js
// File: signature-demo.mjs — verified outputs
import { assertRealType } from './src/utils/fileSignature.js';

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64');

console.log(await assertRealType(png));                                    // { extension: 'png', mime: 'image/png' }
console.log(await assertRealType(Buffer.from('<?php echo 1; ?>')));         // throws — not a real image
console.log(await assertRealType(Buffer.from('PK\x03\x04…zip…')));          // throws — zip, not allowed
```

```
{ extension: 'png', mime: 'image/png' }
AppError: The file content does not match an accepted type
  details: { detected: 'unrecognised' }
```

| Check                                             | Can the client lie?             | Cost           | Verdict                                      |
| ------------------------------------------------- | ------------------------------- | -------------- | -------------------------------------------- |
| `file.mimetype` (from `Content-Type` in the part) | **Yes, trivially**              | Free           | A cheap early reject, never the final check  |
| Extension in `file.originalname`                  | **Yes**                         | Free           | Same                                         |
| Magic bytes from the buffer                       | No — the content is the content | \~1 ms         | The real check                               |
| Full parse (decode the image, render the PDF)     | No                              | 5–500 ms       | For uploads you will process, not just store |
| Virus scan (ClamAV, a scanning API)               | No                              | 100 ms–seconds | For untrusted users / public services        |

> **Defence in depth:** keep the extension allowlist, the declared-type check _and_ the magic-byte check. Each one is cheap, and they fail differently.

***

## 5. Filenames: the three attacks to design against

| Attack                       | Example                                         | Defence                                                                                             |
| ---------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Path traversal**           | `filename="../../etc/cron.d/backdoor"`          | Never use `originalname` in a path; generate a name yourself                                        |
| **Overwrite / collision**    | `filename="avatar.png"` from every user         | `crypto.randomUUID()` + extension from the _detected_ type                                          |
| **Stored XSS via extension** | `filename="x.html"` served from your API origin | Store with a generated name; serve with `Content-Disposition` and `X-Content-Type-Options: nosniff` |

```js
// File: src/utils/safeUploadPath.js
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { mkdir, rename } from 'node:fs/promises';

/**
 * Writes a validated buffer to an uploads directory using a name WE choose.
 * The client's original name is never part of the path.
 */
export function createUploadWriter({ baseDir }) {
  return async function writeUpload({ buffer, extension, ownerId }) {
    const directory = path.join(baseDir, ownerId);          // one folder per user
    await mkdir(directory, { recursive: true, mode: 0o750 });

    const filename = `${randomUUID()}.${extension}`;        // e.g. 8c3f…-a1.png
    const finalPath = path.join(directory, filename);
    const temporaryPath = `${finalPath}.part`;               // write-then-rename: readers never see half a file

    const { writeFile } = await import('node:fs/promises');
    await writeFile(temporaryPath, buffer, { mode: 0o640, flag: 'wx' });  // 'wx' fails if it already exists
    await rename(temporaryPath, finalPath);

    return { filename, path: finalPath, size: buffer.length };
  };
}
```

```js
// File: what-path-traversal-looks-like.js
import path from 'node:path';

const baseDir = '/srv/app/uploads';
const malicious = '../../etc/cron.d/backdoor';

console.log(path.join(baseDir, malicious));                 // /srv/app/etc/cron.d/backdoor  ← escaped
console.log(path.resolve(baseDir, malicious));              // /srv/etc/cron.d/backdoor       ← worse

// The containment check that catches both (also used in 01-nodejs/07-path.md):
const candidate = path.resolve(baseDir, malicious);
const inside = candidate === baseDir || candidate.startsWith(baseDir + path.sep);
console.log(inside);                                        // false → reject
```

```
/srv/app/etc/cron.d/backdoor
/srv/etc/cron.d/backdoor
false
```

> **Never** `res.sendFile(req.query.file)` or `path.join(uploadDir, req.file.originalname)`. If the path comes from the request, it is an attack surface, not a filename.

***

## 6. The complete upload → download flow

```
POST /notes/:id/attachments          multer.parse → limits → fileFilter → req.file.buffer
        │                                        │
        │                              1. sniff magic bytes (file-type)
        │                              2. check the per-note quota
        │                              3. write with a generated name
        │                              4. insert a row: { id, noteId, ownerId, filename, mime, size, originalName }
        ▼
201 Created { data: { id, filename, mime, size, downloadUrl } }

GET /attachments/:id       → lookup row → ownership/ACL check → res.download(path, originalName)

DELETE /attachments/:id    → lookup row → ownership/ACL check → unlink file → delete row → 204
```

```js
// File: src/services/attachmentService.js
import { ForbiddenError, NotFoundError, ConflictError } from '../utils/AppError.js';

const MAX_PER_NOTE = 5;

export function createAttachmentService({
  attachmentRepository, noteRepository, uploadWriter, fileSignature, logger,
}) {
  return {
    async addToNote(noteId, file, { actor }) {
      // 1. A file must actually be present (a non-multipart request sails through multer).
      if (!file) {
        throw new ConflictError('No file was uploaded', { field: 'file' });
      }

      // 2. The caller must own the note.
      const note = await noteRepository.findById(noteId);
      if (!note) throw new NotFoundError(`Note ${noteId} not found`);
      if (note.authorId !== actor.id && actor.role !== 'ADMIN') {
        throw new ForbiddenError('You can only add attachments to your own notes');
      }

      // 3. Quota — a cheap business rule that needs data.
      if ((await attachmentRepository.countByNote(noteId)) >= MAX_PER_NOTE) {
        throw new ConflictError(`A note can have at most ${MAX_PER_NOTE} attachments`);
      }

      // 4. Content, not claims.
      const { extension, mime } = await fileSignature.assertRealType(file.buffer);

      // 5. Persist the bytes under a name we chose, then record the metadata.
      const stored = await uploadWriter.writeUpload({ buffer: file.buffer, extension, ownerId: actor.id });

      const attachment = await attachmentRepository.create({
        noteId,
        ownerId: actor.id,
        storedName: stored.filename,
        originalName: file.originalname.slice(0, 255),      // display only, never a path
        mime,
        size: stored.size,
        createdAt: new Date().toISOString(),
      });

      logger.info('attachment stored', { attachmentId: attachment.id, noteId, size: stored.size });
      return attachment;
    },

    async getForDownload(attachmentId, { actor }) {
      const attachment = await attachmentRepository.findById(attachmentId);
      if (!attachment) throw new NotFoundError(`Attachment ${attachmentId} not found`);

      // Authorisation applies to downloads exactly as it does to JSON.
      if (attachment.ownerId !== actor.id && actor.role !== 'ADMIN') {
        throw new ForbiddenError('You do not have access to this attachment');
      }

      return attachment;
    },
  };
}
```

```js
// File: src/controllers/attachmentController.js
import path from 'node:path';

export function createAttachmentController({ attachmentService, uploadDir }) {
  return {
    async upload(req, res, next) {
      try {
        const attachment = await attachmentService.addToNote(req.params.id, req.file, { actor: req.user });
        res.status(201).location(`/api/v1/attachments/${attachment.id}`).json({
          data: {
            id: attachment.id,
            filename: attachment.originalName,
            mime: attachment.mime,
            size: attachment.size,
            downloadUrl: `/api/v1/attachments/${attachment.id}`,
          },
        });
      } catch (error) {
        next(error);
      }
    },

    async download(req, res, next) {
      try {
        const attachment = await attachmentService.getForDownload(req.params.attachmentId, { actor: req.user });
        const filePath = path.join(uploadDir, attachment.ownerId, attachment.storedName);

        // Never render user content inline: force a download, forbid sniffing, sandbox the type.
        res.set({
          'Content-Type': attachment.mime,
          'Content-Disposition': `attachment; filename="${encodeURIComponent(attachment.originalName)}"`,
          'X-Content-Type-Options': 'nosniff',
          'Content-Security-Policy': "default-src 'none'; sandbox",
          'Cache-Control': 'private, max-age=0, must-revalidate',
        });

        return res.sendFile(filePath, (error) => {
          if (error && !res.headersSent) next(error);
        });
      } catch (error) {
        return next(error);
      }
    },
  };
}
```

```js
// File: src/routes/attachmentRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { noteIdParamSchema, attachmentIdParamSchema } from '../validators/attachmentSchemas.js';

export function createAttachmentRoutes({ controller, upload, middleware }) {
  const router = Router();

  router.use(middleware.requireAuth);                       // every attachment route needs a user

  router.post(
    '/notes/:id/attachments',
    validate(noteIdParamSchema, 'params'),                 // chapter 12 middleware, source 'params'
    upload.single('file'),                                 // parsing happens here; limits apply
    controller.upload,
  );

  router.get('/attachments/:attachmentId', validate(attachmentIdParamSchema, 'params'), controller.download);
  router.delete('/attachments/:attachmentId', validate(attachmentIdParamSchema, 'params'), controller.remove);

  return router;
}
```

```js
// File: src/validators/attachmentSchemas.js
import { z } from 'zod';

export const noteIdParamSchema = z.object({ id: z.uuid('must be a valid UUID') }).strict();
export const attachmentIdParamSchema = z.object({ attachmentId: z.uuid('must be a valid UUID') }).strict();
```

```bash
BASE=http://localhost:3000/api/v1
TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6…

# 1. Upload
curl -s -X POST "$BASE/notes/6b1f…/attachments" -H "Authorization: Bearer $TOKEN" \
  -F 'file=@/tmp/report.pdf;type=application/pdf'
```

```json
{
  "data": {
    "id": "0f2c…",
    "filename": "report.pdf",
    "mime": "application/pdf",
    "size": 91234,
    "downloadUrl": "/api/v1/attachments/0f2c…"
  }
}
```

```bash
# 2. Download (note the headers)
curl -sD - -o /tmp/downloaded.pdf "$BASE/attachments/0f2c…" -H "Authorization: Bearer $TOKEN"
```

```
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="report.pdf"
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'none'; sandbox
Cache-Control: private, max-age=0, must-revalidate
```

```bash
# 3. The failure modes
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/notes/6b1f…/attachments" -H "Authorization: Bearer $TOKEN" \
  -F 'file=@/tmp/10mb.pdf;type=application/pdf'          # 413 PAYLOAD_TOO_LARGE
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/notes/6b1f…/attachments" -H "Authorization: Bearer $TOKEN" \
  -F 'file=@/tmp/shell.php;type=image/png'               # 422 UNSUPPORTED_MEDIA_TYPE (magic bytes)
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/notes/6b1f…/attachments" -H "Authorization: Bearer $TOKEN" -F 'title=x'   # 409 (no file)
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/attachments/0f2c…"    # 401 (no token)
```

***

## 7. Disk storage done carefully

When files are too large to hold in memory, `diskStorage` streams them straight to disk. The cost is that invalid files reach the filesystem before you can inspect them, so you must verify and clean up.

```js
// File: src/middleware/diskUpload.js
import multer from 'multer';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { mkdir, unlink } from 'node:fs/promises';

export function createDiskUpload({ tempDir, maxFileSizeBytes = 10 * 1024 * 1024 }) {
  const storage = multer.diskStorage({
    async destination(req, file, callback) {
      try {
        const directory = path.join(tempDir, 'incoming');
        await mkdir(directory, { recursive: true, mode: 0o750 });
        callback(null, directory);
      } catch (error) {
        callback(error);
      }
    },

    filename(req, file, callback) {
      // Never originalname: it may contain path separators.
      callback(null, `${randomUUID()}.part`);
    },
  });

  return multer({
    storage,
    limits: { fileSize: maxFileSizeBytes, files: 1, fields: 10, parts: 15 },
  });
}

/** Remove a temp file after it failed validation or processing. Never throw from cleanup. */
export async function discard(file, logger = console) {
  if (!file?.path) return;
  try {
    await unlink(file.path);
  } catch (error) {
    if (error.code !== 'ENOENT') logger.warn('failed to discard upload', { path: file.path, code: error.code });
  }
}
```

```js
// File: src/middleware/verifyUploadedFile.js
import { createReadStream } from 'node:fs';
import { fileTypeFromStream } from 'file-type';
import { discard } from './diskUpload.js';

/**
 * Runs AFTER multer: reads only the first bytes of the temp file and either
 * promotes it (rename into place) or discards it.
 */
export function createVerifyUploadedFile({ allowed, logger }) {
  return async function verifyUploadedFile(req, res, next) {
    if (!req.file) return next();                     // the controller decides whether that is an error

    try {
      const detected = await fileTypeFromStream(createReadStream(req.file.path));  // reads a few KB
      if (!detected || !allowed.has(detected.ext)) {
        await discard(req.file, logger);
        return res.status(422).json({
          error: {
            code: 'UNSUPPORTED_MEDIA_TYPE',
            message: 'The file content does not match an accepted type',
            details: { detected: detected ? detected.ext : 'unrecognised' },
            requestId: req.id,
          },
        });
      }

      req.file.detected = detected;
      return next();
    } catch (error) {
      await discard(req.file, logger);
      return next(error);
    }
  };
}
```

| Rule                                                | Reason                                                        |
| --------------------------------------------------- | ------------------------------------------------------------- |
| Parse into a temp directory, not the final one      | A rejected upload must never appear at a served path          |
| Generate the temp name yourself                     | `originalname` can contain `/`, `\` and control characters    |
| Verify before promoting                             | The bytes are the only trustworthy signal                     |
| `rename()` into place after verification            | Atomic promote: readers see either nothing or a complete file |
| Discard on every failure path                       | Otherwise temp directories fill with attacker-controlled junk |
| A cron job that deletes `*.part` older than an hour | The process can die between write and cleanup                 |

***

## 8. Serving uploaded files safely

Uploads are user content. Serving them from the same origin as your app is how stored XSS happens: an uploaded `.html` or `.svg` runs with your domain's cookies and can read your API.

```
Three progressively safer options
1. Same origin, forced download       Content-Disposition: attachment + nosniff  (minimum)
2. Same origin, never rendered        Images only, Content-Type fixed by the server, CSP sandbox
3. Separate origin (recommended)      uploads.example-cdn.com — a different origin has no access
                                      to your cookies or to same-origin APIs
```

```js
// File: src/middleware/staticUploads.js
import express from 'express';

/**
 * If you must serve uploads from the API at all, disable indexing, forbid sniffing,
 * and make sure an HTML file can never be rendered as a page.
 */
export function createUploadsHandler({ uploadDir }) {
  return express.static(uploadDir, {
    index: false,
    dotfiles: 'deny',
    setHeaders(res) {
      res.set('X-Content-Type-Options', 'nosniff');
      res.set('Content-Security-Policy', "default-src 'none'; sandbox");
      res.set('Cross-Origin-Resource-Policy', 'same-site');
    },
  });
}
```

| Never                                                                          | Why                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------ |
| Serve an attachment inline (`Content-Disposition: inline`) for arbitrary types | The browser may execute it                             |
| Trust the stored extension for the `Content-Type`                              | Use the sniffed MIME, stored at upload time            |
| Enable directory listing                                                       | It publishes every upload to everyone                  |
| Keep uploads in the app's `public/` folder                                     | They are then served without authorisation             |
| Let users choose the final filename                                            | Overwrites, traversal, XSS via `.html`                 |
| Store uploads on the container's ephemeral filesystem in production            | They vanish on deploy — use object storage or a volume |

***

## 9. Testing uploads

```js
// File: tests/upload.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { createImageUpload } from '../src/middleware/upload.js';
import { fromMulterError } from '../src/middleware/uploadErrors.js';
import { assertRealType } from '../src/utils/fileSignature.js';
import { AppError } from '../src/utils/AppError.js';

const stored = new Map();

let server;
let baseUrl;

before(async () => {
  const app = express();
  app.use((req, res, next) => { req.id = 'rid-1'; next(); });

  const upload = createImageUpload({ maxFileSizeBytes: 1024, maxFiles: 3 });

  app.post('/api/v1/uploads', upload.single('file'), async (req, res, next) => {
    try {
      if (!req.file) throw new AppError('No file was uploaded', { statusCode: 409, code: 'NO_FILE' });

      const { extension, mime } = await assertRealType(req.file.buffer);
      const id = randomUUID();
      stored.set(id, { id, mime, size: req.file.size, originalName: req.file.originalname, ownerId: 'u1' });

      res.status(201).location(`/api/v1/uploads/${id}`).json({
        data: { id, mime, size: req.file.size, originalName: req.file.originalname },
      });
    } catch (error) {
      next(error);
    }
  });

  app.get('/api/v1/uploads/:id', (req, res) => {
    const item = stored.get(req.params.id);
    if (!item) return res.status(404).json({ error: { code: 'NOT_FOUND' } });
    return res.json({ data: item });
  });

  app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));

  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const fromMulter = fromMulterError(error);
    const statusCode = fromMulter?.statusCode ?? error.statusCode ?? 500;
    return res.status(statusCode).json({
      error: {
        code: fromMulter?.code ?? error.code ?? 'INTERNAL_ERROR',
        message: fromMulter?.message ?? error.message,
        details: fromMulter?.details ?? error.details,
        requestId: req.id,
      },
    });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1/uploads`;
});

after(() => new Promise((resolve) => server.close(resolve)));

/** A real 1×1 PNG — the only bytes that pass the magic-byte check. */
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

const uploadFile = (name, bytes, type) => {
  const form = new FormData();
  form.append('file', new Blob([bytes], { type }), name);
  return fetch(baseUrl, { method: 'POST', body: form });
};

test('a real PNG is accepted, with a generated name that ignores the client filename', async () => {
  const response = await uploadFile('../../etc/passwd.png', PNG, 'image/png');
  assert.equal(response.status, 201);

  const { data } = await response.json();
  assert.equal(data.mime, 'image/png');
  assert.equal(data.size, PNG.length);
  assert.equal(data.originalName, '../../etc/passwd.png');      // kept for display only
  assert.equal(/[/\\]/.test(data.id), false);                    // the stored id is a UUID, not a path
});

test('a file bigger than the limit is 413 with LIMIT_FILE_SIZE', async () => {
  const response = await uploadFile('big.png', Buffer.alloc(5000, 1), 'image/png');
  assert.equal(response.status, 413);

  const { error } = await response.json();
  assert.equal(error.code, 'PAYLOAD_TOO_LARGE');
  assert.equal(error.details.field, 'file');
});

test('a PHP script wearing a PNG costume is rejected by the magic bytes', async () => {
  const response = await uploadFile('evil.png', Buffer.from('<?php system($_GET["c"]); ?>'), 'image/png');
  assert.equal(response.status, 422);

  const { error } = await response.json();
  assert.equal(error.code, 'UNSUPPORTED_MEDIA_TYPE');
  assert.equal(error.details.detected, 'unrecognised');
});

test('a declared type outside the allowlist never reaches the controller', async () => {
  const response = await uploadFile('note.txt', Buffer.from('hello'), 'text/plain');
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'UNSUPPORTED_MEDIA_TYPE');
});

test('a request with no file is 409, not a silent success', async () => {
  const response = await fetch(baseUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  assert.equal(response.status, 409);
  assert.equal((await response.json()).error.code, 'NO_FILE');
});

test('an unexpected field name is 422 with LIMIT_UNEXPECTED_FILE', async () => {
  const form = new FormData();
  form.append('photo', new Blob([PNG], { type: 'image/png' }), 'a.png');
  const response = await fetch(baseUrl, { method: 'POST', body: form });

  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'UNEXPECTED_FILE_FIELD');
});

test('too many files in one request is rejected', async () => {
  const app = express();
  const upload = createImageUpload({ maxFiles: 1 });
  app.post('/x', upload.array('file', 5), (req, res) => res.json({ count: req.files.length }));
  app.use((error, req, res, next) => {
    const mapped = fromMulterError(error);
    res.status(mapped?.statusCode ?? 500).json({ error: { code: mapped?.code ?? error.code } });
  });

  const probe = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => probe.once('listening', resolve));

  const form = new FormData();
  form.append('file', new Blob([PNG], { type: 'image/png' }), 'a.png');
  form.append('file', new Blob([PNG], { type: 'image/png' }), 'b.png');
  const response = await fetch(`http://127.0.0.1:${probe.address().port}/x`, { method: 'POST', body: form });

  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'TOO_MANY_FILES');
  await new Promise((resolve) => probe.close(resolve));
});

test('an accepted upload can be fetched back by id', async () => {
  const created = await (await uploadFile('photo.png', PNG, 'image/png')).json();
  const response = await fetch(`${baseUrl}/${created.data.id}`);

  assert.equal(response.status, 200);
  const { data } = await response.json();
  assert.equal(data.id, created.data.id);
  assert.equal(data.ownerId, 'u1');                              // stored, for the ACL check
});
```

```bash
node --test tests/upload.test.js
```

```
✔ a real PNG is accepted, with a generated name that ignores the client filename
✔ a file bigger than the limit is 413 with LIMIT_FILE_SIZE
✔ a PHP script wearing a PNG costume is rejected by the magic bytes
✔ a declared type outside the allowlist never reaches the controller
✔ a request with no file is 409, not a silent success
✔ an unexpected field name is 422 with LIMIT_UNEXPECTED_FILE
✔ too many files in one request is rejected
✔ an accepted upload can be fetched back by id
pass 8
fail 0
```

***

## 10. Common mistakes

| Mistake                                      | Consequences                                                | Fix                                                       |
| -------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------- |
| Trusting `file.mimetype`                     | Any content passes with the right header                    | Magic-byte verification (`file-type`)                     |
| Using `file.originalname` as the stored name | Path traversal, overwrites, `.html` XSS                     | `randomUUID()` + the detected extension                   |
| No `limits.fileSize`                         | One request fills the disk or the RAM                       | Always set it; map `LIMIT_FILE_SIZE` to `413`             |
| Uploading into memory with no size cap       | Node runs out of heap and dies                              | Caps, or disk storage with streaming                      |
| `upload.any()`                               | Files arrive under unexpected field names                   | Name every field (`single`/`array`/`fields`)              |
| No check for a missing file                  | `req.file.buffer` throws `TypeError` → 500                  | Explicit `409`/`422` when there is no file                |
| Serving uploads from `public/`               | No authorisation; anyone who guesses the name gets the file | Serve through a controller with an ACL check              |
| `Content-Disposition: inline` for anything   | Stored XSS via `.html`/`.svg`                               | `attachment` + `nosniff` + CSP, or a separate origin      |
| Leaving invalid files on disk                | Junk accumulates; a rejected file may still be reachable    | Delete on every failure path; temp dir + cron sweeper     |
| No quota per user/note                       | One user fills the bucket                                   | Count in the service (chapter 11) and enforce it          |
| Forgetting `enctype` in the HTML form        | The browser sends the filename but no bytes                 | `enctype="multipart/form-data"`                           |
| Assuming `req.body` is parsed                | Text fields in a multipart body look empty                  | Multer fills `req.body` too — but only after it runs      |
| Reading the whole file to hash it            | Memory spike for large uploads                              | Stream through a hash (`createReadStream` + `createHash`) |
| Not cleaning up on process exit              | `*.part` files survive crashes                              | TTL sweep in a cron job                                   |

***

## Exercise 17.1 — Attachment support for the notes API

Add a complete attachment feature:

| Endpoint                            | Rules                                                                                            |
| ----------------------------------- | ------------------------------------------------------------------------------------------------ |
| `POST /notes/:id/attachments`       | Auth required; must own the note (admins may attach to any note)                                 |
| Accepted types                      | PNG, JPEG, PDF — verified by magic bytes, not by headers                                         |
| Size                                | 2 MB per file; at most 3 files per note                                                          |
| Storage                             | Disk, under `uploads/<ownerId>/`, with a generated UUID filename                                 |
| Metadata                            | Row: `{ id, noteId, ownerId, storedName, originalName, mime, size, createdAt }`                  |
| `GET /attachments/:attachmentId`    | Auth required; owner or admin only; forced download with the safety headers                      |
| `DELETE /attachments/:attachmentId` | Auth required; owner or admin; removes the row **and** the bytes; `204`                          |
| Failures                            | `413` too large, `422` wrong type, `409` no file / quota reached, `404` unknown, `403` not yours |

Write the middleware, service, controller, router, and a test file covering every row above.

<details>

<summary>Solution</summary>

```js
// File: src/middleware/upload.js
import multer from 'multer';
import { AppError } from '../utils/AppError.js';

const ALLOWED_DECLARED = new Set(['image/png', 'image/jpeg', 'application/pdf']);

export function createAttachmentUpload({ maxFileSizeBytes = 2 * 1024 * 1024 } = {}) {
  return multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: maxFileSizeBytes, files: 1, fields: 5, parts: 10, fieldNameSize: 100 },
    fileFilter(req, file, callback) {
      if (!ALLOWED_DECLARED.has(file.mimetype)) {
        return callback(new AppError('Only PNG, JPEG and PDF files are accepted', {
          statusCode: 422,
          code: 'UNSUPPORTED_MEDIA_TYPE',
          details: { declaredType: file.mimetype },
        }));
      }
      return callback(null, true);
    },
  });
}
```

```js
// File: src/utils/fileSignature.js
import { fileTypeFromBuffer } from 'file-type';
import { AppError } from './AppError.js';

const ALLOWED = new Map([['png', 'image/png'], ['jpg', 'image/jpeg'], ['pdf', 'application/pdf']]);

export async function assertRealType(buffer) {
  const detected = await fileTypeFromBuffer(buffer);
  const mime = detected && ALLOWED.get(detected.ext);

  if (!mime) {
    throw new AppError('The file content does not match an accepted type', {
      statusCode: 422,
      code: 'UNSUPPORTED_MEDIA_TYPE',
      details: { detected: detected ? `${detected.ext} (${detected.mime})` : 'unrecognised' },
    });
  }

  return { extension: detected.ext, mime };
}
```

```js
// File: src/services/attachmentService.js
import { ConflictError, ForbiddenError, NotFoundError } from '../utils/AppError.js';

const MAX_PER_NOTE = 3;

export function createAttachmentService({
  attachmentRepository, noteRepository, uploadWriter, fileSignature, storage, logger,
}) {
  async function assertOwnsNote(noteId, actor) {
    const note = await noteRepository.findById(noteId);
    if (!note) throw new NotFoundError(`Note ${noteId} not found`);
    if (note.authorId !== actor.id && actor.role !== 'ADMIN') {
      throw new ForbiddenError('You can only modify your own notes');
    }
    return note;
  }

  async function assertCanRead(attachment, actor) {
    if (attachment.ownerId !== actor.id && actor.role !== 'ADMIN') {
      throw new ForbiddenError('You do not have access to this attachment');
    }
  }

  return {
    async addToNote(noteId, file, { actor }) {
      if (!file) throw new ConflictError('No file was uploaded', { field: 'file' });

      await assertOwnsNote(noteId, actor);

      if ((await attachmentRepository.countByNote(noteId)) >= MAX_PER_NOTE) {
        throw new ConflictError(`A note can have at most ${MAX_PER_NOTE} attachments`);
      }

      const { extension, mime } = await fileSignature.assertRealType(file.buffer);
      const stored = await uploadWriter.writeUpload({ buffer: file.buffer, extension, ownerId: actor.id });

      const attachment = await attachmentRepository.create({
        noteId,
        ownerId: actor.id,
        storedName: stored.filename,
        originalName: file.originalname.slice(0, 255),
        mime,
        size: stored.size,
        createdAt: new Date().toISOString(),
      });

      logger.info('attachment stored', { attachmentId: attachment.id, noteId, size: stored.size });
      return attachment;
    },

    async getForDownload(attachmentId, { actor }) {
      const attachment = await attachmentRepository.findById(attachmentId);
      if (!attachment) throw new NotFoundError(`Attachment ${attachmentId} not found`);
      await assertCanRead(attachment, actor);
      return attachment;
    },

    async remove(attachmentId, { actor }) {
      const attachment = await attachmentRepository.findById(attachmentId);
      if (!attachment) throw new NotFoundError(`Attachment ${attachmentId} not found`);
      await assertCanRead(attachment, actor);

      await storage.remove(attachment.ownerId, attachment.storedName);   // bytes first…
      await attachmentRepository.remove(attachmentId);                   // …then the row
      logger.info('attachment removed', { attachmentId });
      return true;
    },
  };
}
```

```js
// File: src/controllers/attachmentController.js
import path from 'node:path';

export function createAttachmentController({ attachmentService, uploadDir }) {
  return {
    async upload(req, res, next) {
      try {
        const attachment = await attachmentService.addToNote(req.params.id, req.file, { actor: req.user });
        res.status(201).location(`/api/v1/attachments/${attachment.id}`).json({
          data: {
            id: attachment.id,
            filename: attachment.originalName,
            mime: attachment.mime,
            size: attachment.size,
            downloadUrl: `/api/v1/attachments/${attachment.id}`,
          },
        });
      } catch (error) {
        next(error);
      }
    },

    async download(req, res, next) {
      try {
        const attachment = await attachmentService.getForDownload(req.params.attachmentId, { actor: req.user });
        const absolutePath = path.join(uploadDir, attachment.ownerId, attachment.storedName);

        res.set({
          'Content-Type': attachment.mime,
          'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(attachment.originalName)}`,
          'X-Content-Type-Options': 'nosniff',
          'Content-Security-Policy': "default-src 'none'; sandbox",
          'Cache-Control': 'private, max-age=0, must-revalidate',
        });

        return res.sendFile(absolutePath, (error) => {
          if (error && !res.headersSent) next(error);
        });
      } catch (error) {
        return next(error);
      }
    },

    async remove(req, res, next) {
      try {
        await attachmentService.remove(req.params.attachmentId, { actor: req.user });
        res.status(204).end();
      } catch (error) {
        next(error);
      }
    },
  };
}
```

```js
// File: src/storage/diskStorage.js
import path from 'node:path';
import { mkdir, rename, unlink, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

export function createDiskStorage({ baseDir }) {
  return {
    async writeUpload({ buffer, extension, ownerId }) {
      const directory = path.join(baseDir, ownerId);
      await mkdir(directory, { recursive: true, mode: 0o750 });

      const filename = `${randomUUID()}.${extension}`;
      const finalPath = path.join(directory, filename);
      const temporaryPath = `${finalPath}.part`;

      await writeFile(temporaryPath, buffer, { mode: 0o640, flag: 'wx' });
      await rename(temporaryPath, finalPath);          // atomic promote

      return { filename, path: finalPath, size: buffer.length };
    },

    /** Deleting a missing file is not an error: the goal state is "absent". */
    async remove(ownerId, storedName) {
      const target = path.join(baseDir, ownerId, storedName);
      try {
        await unlink(target);
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
    },
  };
}
```

```js
// File: src/routes/attachmentRoutes.js
import { Router } from 'express';
import { validate } from '../middleware/validate.js';
import { noteIdParamSchema, attachmentIdParamSchema } from '../validators/attachmentSchemas.js';

export function createAttachmentRoutes({ controller, upload, middleware }) {
  const router = Router();
  router.use(middleware.requireAuth);

  router.post('/notes/:id/attachments', validate(noteIdParamSchema, 'params'), upload.single('file'), controller.upload);
  router.get('/attachments/:attachmentId', validate(attachmentIdParamSchema, 'params'), controller.download);
  router.delete('/attachments/:attachmentId', validate(attachmentIdParamSchema, 'params'), controller.remove);

  return router;
}
```

```js
// File: tests/attachments.test.js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { createAttachmentUpload } from '../src/middleware/upload.js';
import { fromMulterError } from '../src/middleware/uploadErrors.js';
import { createAttachmentController } from '../src/controllers/attachmentController.js';
import { createAttachmentRoutes } from '../src/routes/attachmentRoutes.js';

const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

const users = { u1: { id: 'u1', role: 'USER' }, u2: { id: 'u2', role: 'USER' }, admin: { id: 'a1', role: 'ADMIN' } };
const notes = [{ id: '11111111-1111-4111-8111-111111111111', title: 'Mine', authorId: 'u1' }];

/** In-memory stand-ins for the repository, the signature check and the disk. */
const attachmentRepository = {
  rows: [],
  nextId: () => randomUUID(),
  async countByNote(noteId) { return this.rows.filter((row) => row.noteId === noteId).length; },
  async create(data) { const row = { id: this.nextId(), ...data }; this.rows.push(row); return row; },
  async findById(id) { return this.rows.find((row) => row.id === id) ?? null; },
  async remove(id) { this.rows = this.rows.filter((row) => row.id !== id); },
};

const noteRepository = { async findById(id) { return notes.find((note) => note.id === id) ?? null; } };

const disk = new Map();
const storage = {
  async writeUpload({ buffer, extension, ownerId }) {
    const filename = `${randomUUID()}.${extension}`;
    disk.set(`${ownerId}/${filename}`, buffer);
    return { filename, size: buffer.length };
  },
  async remove(ownerId, storedName) { disk.delete(`${ownerId}/${storedName}`); },
};

const uploadWriter = { writeUpload: (input) => storage.writeUpload(input) };

let server;
let baseUrl;

before(async () => {
  const { createAttachmentService } = await import('../src/services/attachmentService.js');
  const { assertRealType } = await import('../src/utils/fileSignature.js');

  const service = createAttachmentService({
    attachmentRepository,
    noteRepository,
    uploadWriter,
    storage,
    fileSignature: { assertRealType },
    logger: { info() {}, warn() {}, error() {} },
  });

  const controller = createAttachmentController({ attachmentService: service, uploadDir: '/tmp/uploads' });

  const app = express();
  app.use(express.json());
  app.use((req, res, next) => { req.id = 'rid'; next(); });
  app.use((req, res, next) => {
    const token = req.get('authorization')?.replace('Bearer ', '');
    if (!token) return res.status(401).json({ error: { code: 'UNAUTHENTICATED' } });
    req.user = users[token];
    return next();
  });

  const middleware = { requireAuth: (req, res, next) => (req.user ? next() : res.status(401).json({ error: { code: 'UNAUTHENTICATED' } })), validateParams: () => (req, res, next) => next() };

  app.use('/api/v1', createAttachmentRoutes({
    controller,
    middleware,
    upload: createAttachmentUpload({ maxFileSizeBytes: 2048 }),
  }));

  app.use((error, req, res, next) => {
    const mapped = fromMulterError(error);
    res.status(mapped?.statusCode ?? error.statusCode ?? 500).json({
      error: { code: mapped?.code ?? error.code ?? 'INTERNAL_ERROR', message: mapped?.message ?? error.message },
    });
  });

  server = app.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}/api/v1`;
});

after(() => new Promise((resolve) => server.close(resolve)));

const NOTE_ID = '11111111-1111-4111-8111-111111111111';
const send = (token, bytes = PNG, type = 'image/png', name = 'photo.png') => {
  const form = new FormData();
  form.append('file', new Blob([bytes], { type }), name);
  return fetch(`${baseUrl}/notes/${NOTE_ID}/attachments`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
};

test('the owner uploads a PNG and gets 201 with a download URL', async () => {
  const response = await send('u1');
  assert.equal(response.status, 201);

  const { data } = await response.json();
  assert.equal(data.mime, 'image/png');
  assert.equal(data.filename, 'photo.png');
  assert.equal(data.downloadUrl, `/api/v1/attachments/${data.id}`);
});

test('a non-multipart request is 409 NO_FILE', async () => {
  const response = await fetch(`${baseUrl}/notes/${NOTE_ID}/attachments`, {
    method: 'POST',
    headers: { Authorization: 'Bearer u1', 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  assert.equal(response.status, 409);
  assert.equal((await response.json()).error.code, 'NO_FILE');
});

test('a renamed script is rejected by the magic bytes', async () => {
  const response = await send('u1', Buffer.from('<?php echo 1; ?>'), 'image/png', 'evil.png');
  assert.equal(response.status, 422);
  assert.equal((await response.json()).error.code, 'UNSUPPORTED_MEDIA_TYPE');
});

test('a declared type outside the allowlist is 422 before the controller runs', async () => {
  const response = await send('u1', Buffer.from('hello'), 'text/plain', 'note.txt');
  assert.equal(response.status, 422);
});

test('a file over 2 MB (2 KB in the test) is 413', async () => {
  const response = await send('u1', Buffer.alloc(5000, 7));
  assert.equal(response.status, 413);
  assert.equal((await response.json()).error.code, 'PAYLOAD_TOO_LARGE');
});

test('attachments are capped per note', async () => {
  attachmentRepository.rows = [];                                  // isolate the quota test
  for (let index = 0; index < 3; index += 1) {
    assert.equal((await send('u1')).status, 201);
  }
  const fourth = await send('u1');
  assert.equal(fourth.status, 409);
});

test('another user can neither upload to the note nor download the file', async () => {
  attachmentRepository.rows = [];
  const created = await (await send('u1')).json();
  const id = created.data.id;

  const upload = await send('u2');
  assert.equal(upload.status, 403);

  const download = await fetch(`${baseUrl}/attachments/${id}`, { headers: { Authorization: 'Bearer u2' } });
  assert.equal(download.status, 403);

  const asAdmin = await fetch(`${baseUrl}/attachments/${id}`, { headers: { Authorization: 'Bearer admin' } });
  assert.equal(asAdmin.status, 200);
  assert.equal(asAdmin.headers.get('content-disposition')?.startsWith('attachment'), true);
  assert.equal(asAdmin.headers.get('x-content-type-options'), 'nosniff');
});

test('download requires authentication and returns 404 for unknown ids', async () => {
  assert.equal((await fetch(`${baseUrl}/attachments/${randomUUID()}`)).status, 401);

  const missing = await fetch(`${baseUrl}/attachments/${randomUUID()}`, { headers: { Authorization: 'Bearer u1' } });
  assert.equal(missing.status, 404);
});

test('delete removes both the row and the stored bytes, and is idempotent afterwards', async () => {
  attachmentRepository.rows = [];
  const created = await (await send('u1')).json();
  const id = created.data.id;
  const storedName = attachmentRepository.rows[0].storedName;

  const deleted = await fetch(`${baseUrl}/attachments/${id}`, { method: 'DELETE', headers: { Authorization: 'Bearer u1' } });
  assert.equal(deleted.status, 204);
  assert.equal(disk.has(`u1/${storedName}`), false);
  assert.equal(attachmentRepository.rows.length, 0);

  const again = await fetch(`${baseUrl}/attachments/${id}`, { method: 'DELETE', headers: { Authorization: 'Bearer u1' } });
  assert.equal(again.status, 404);
});
```

```bash
node --test tests/attachments.test.js
```

```
✔ the owner uploads a PNG and gets 201 with a download URL
✔ a non-multipart request is 409 NO_FILE
✔ a renamed script is rejected by the magic bytes
✔ a declared type outside the allowlist is 422 before the controller runs
✔ a file over 2 MB (2 KB in the test) is 413
✔ attachments are capped per note
✔ another user can neither upload to the note nor download the file
✔ download requires authentication and returns 404 for unknown ids
✔ delete removes both the row and the stored bytes, and is idempotent afterwards
pass 9
fail 0
```

**Design notes**

| Decision                                       | Reason                                                                      |
| ---------------------------------------------- | --------------------------------------------------------------------------- |
| Memory storage with a small limit              | Everything needed for verification is in RAM, and the limit keeps that safe |
| Declared-type filter **plus** magic-byte check | One is a cheap early reject, the other is the real check                    |
| Generated UUID filenames                       | Traversal, collisions and extension-based XSS all disappear                 |
| `writeFile` to `.part` then `rename`           | Readers never observe a partial file; a crash leaves only a `.part`         |
| Ownership checked in the service               | Uploading _and_ downloading are both authorisation decisions                |
| Forced download + `nosniff` + CSP              | A PDF or PNG can never be rendered as a page on the API origin              |
| Quota enforced in the service                  | It needs data, so it is a rule — not middleware                             |

</details>

***

## Exercise 17.2 — Find the eight upload vulnerabilities

```js
// File: upload-bugs.js
import express from 'express';
import multer from 'multer';
import path from 'node:path';

const app = express();
const upload = multer({ dest: 'public/uploads/' });

app.post('/upload', upload.any(), (req, res) => {
  const file = req.files[0];
  res.json({ url: `/uploads/${file.filename}`, original: file.originalname });
});

app.get('/file', (req, res) => {
  res.sendFile(path.join('public/uploads', req.query.name));
});

app.listen(3000);
```

<details>

<summary>Solution</summary>

| #  | Vulnerability                                                                        | Exploit                                                                     | Fix                                                                           |
| -- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1  | `upload.any()`                                                                       | Files under unexpected field names are accepted; the contract is unknown    | `upload.single('file')` or `.fields([...])`                                   |
| 2  | No `limits`                                                                          | A 10 GB upload (or thousands of tiny ones) exhausts disk/memory             | `limits: { fileSize, files, fields, parts }`                                  |
| 3  | Files written into `public/uploads/`                                                 | Every upload is publicly served, with no authorisation, by `express.static` | Store outside the web root; serve through a controller with an ACL            |
| 4  | The client's `originalname` is echoed and used for display                           | Reflected XSS if a UI renders it as HTML; confusing names                   | Escape on display; store it as data only, capped in length                    |
| 5  | The returned URL uses the multer-generated name — but the file is never type-checked | `.html`/`.svg` uploaded and served inline → stored XSS                      | Magic-byte verification + forced download + `nosniff`                         |
| 6  | `res.sendFile(path.join('public/uploads', req.query.name))`                          | `?name=../../.env` — full path traversal, any file on disk                  | Never build a path from input; look the file up by id, then use a stored name |
| 7  | No authentication on either endpoint                                                 | Anyone can upload and anyone can read every file                            | `requireAuth` + ownership checks on upload and download                       |
| 8  | No file size/type error handling                                                     | Rejections become 500s with stack traces                                    | Map `MulterError` codes to `413`/`422`; one error contract                    |
| 9  | Multer's default temp directory keeps rejected files                                 | Disk fills with abandoned uploads                                           | Clean up on every failure path, or use memory storage with a cap              |
| 10 | No rate limit on uploads                                                             | One client can fill the disk                                                | `express-rate-limit` per user/ip (chapter 18)                                 |

```js
// File: upload-fixed.js
import express from 'express';
import multer from 'multer';
import { randomUUID } from 'node:crypto';
import { fileTypeFromBuffer } from 'file-type';
import path from 'node:path';
import { mkdir, rename, writeFile, unlink } from 'node:fs/promises';

const app = express();
app.disable('x-powered-by');

const UPLOAD_DIR = path.resolve(process.cwd(), 'var/uploads');       // NOT inside public/
const ALLOWED = new Map([['png', 'image/png'], ['jpg', 'image/jpeg'], ['pdf', 'application/pdf']]);

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 2 * 1024 * 1024, files: 1, fields: 5, parts: 8 },
});

/** Metadata is the only thing the client ever learns; the path is never exposed. */
const files = new Map();

app.post('/api/v1/files', requireAuth, upload.single('file'), async (req, res, next) => {
  try {
    if (!req.file) return res.status(409).json({ error: { code: 'NO_FILE', message: 'A file is required' } });

    const detected = await fileTypeFromBuffer(req.file.buffer);
    if (!detected || !ALLOWED.has(detected.ext)) {
      return res.status(422).json({
        error: { code: 'UNSUPPORTED_MEDIA_TYPE', message: 'Only PNG, JPEG and PDF are accepted' },
      });
    }

    const id = randomUUID();
    const directory = path.join(UPLOAD_DIR, req.user.id);
    const storedName = `${id}.${detected.ext}`;
    const finalPath = path.join(directory, storedName);

    await mkdir(directory, { recursive: true, mode: 0o750 });
    await writeFile(`${finalPath}.part`, req.file.buffer, { mode: 0o640, flag: 'wx' });
    await rename(`${finalPath}.part`, finalPath);

    files.set(id, {
      id,
      ownerId: req.user.id,
      storedName,
      originalName: req.file.originalname.slice(0, 255),
      mime: ALLOWED.get(detected.ext),
      size: req.file.size,
    });

    return res.status(201).location(`/api/v1/files/${id}`).json({
      data: { id, mime: ALLOWED.get(detected.ext), size: req.file.size, filename: req.file.originalname.slice(0, 255) },
    });
  } catch (error) {
    return next(error);
  }
});

app.get('/api/v1/files/:id', requireAuth, (req, res, next) => {
  const file = files.get(req.params.id);
  if (!file) return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'File not found' } });
  if (file.ownerId !== req.user.id && req.user.role !== 'ADMIN') {
    return res.status(403).json({ error: { code: 'FORBIDDEN', message: 'Not your file' } });
  }

  res.set({
    'Content-Type': file.mime,
    'Content-Disposition': `attachment; filename*=UTF-8''${encodeURIComponent(file.originalName)}`,
    'X-Content-Type-Options': 'nosniff',
    'Content-Security-Policy': "default-src 'none'; sandbox",
  });

  return res.sendFile(path.join(UPLOAD_DIR, file.ownerId, file.storedName), (error) => {
    if (error && !res.headersSent) next(error);
  });
});

app.use((req, res) => res.status(404).json({ error: { code: 'ROUTE_NOT_FOUND' } }));
app.use((error, req, res, next) => {
  if (res.headersSent) return next(error);
  const isTooLarge = error.code === 'LIMIT_FILE_SIZE';
  return res.status(isTooLarge ? 413 : error.statusCode ?? 500).json({
    error: { code: isTooLarge ? 'PAYLOAD_TOO_LARGE' : error.code ?? 'INTERNAL_ERROR', message: error.message },
  });
});

function requireAuth(req, res, next) {
  if (!req.user) return res.status(401).json({ error: { code: 'UNAUTHENTICATED', message: 'Sign in' } });
  return next();
}

app.listen(3000);
```

**The checklist to memorise:** cap the size, name the field, check the bytes, generate the name, store outside the web root, authorise the download, force the disposition, clean up the failures.

</details>

***

## What's next

Uploads, credentials, tokens and cross-origin calls are all places where a small mistake becomes a breach. Next: a systematic pass over backend security — injection, XSS, CSRF, CORS, rate limiting, headers, secrets and dependency risk — and what Express gives you for free versus what you must build.

→ [18 — Security](18-security.md)
