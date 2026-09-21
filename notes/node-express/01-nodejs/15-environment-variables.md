# 15 — Environment Variables

> **Where this fits:** The difference between "runs on my laptop" and "runs in production" is usually configuration. This chapter covers `process.env`, `.env` files, validation at startup, secrets handling, the 12-factor principle, and the failure modes that cause 3am incidents.

***

## 1. What are environment variables?

An **environment variable** is a `KEY=value` pair that lives in the _process environment_ — a block of memory the operating system gives each process when it starts.

```bash
# Set for one command:
PORT=4000 node server.js

# Set for the rest of the shell session:
export DATABASE_URL="postgres://localhost:5432/app"

# Set for everything a docker container runs:
docker run -e NODE_ENV=production -e PORT=3000 my-api

# Set in a web platform's dashboard: RENDER/Railway/Vercel → Environment Variables
```

Reading them in Node:

```js
// File: read-env.mjs
console.log('NODE_ENV    :', process.env.NODE_ENV);        // undefined if unset
console.log('PORT        :', process.env.PORT);            // STRING or undefined
console.log('HOME        :', process.env.HOME);            // set by the OS
console.log('PATH entries:', process.env.PATH.split(':').length);

// Every value is a string. There are no booleans, numbers or objects.
const port = Number(process.env.PORT ?? 3000);
console.log('port as number + 1:', port + 1);              // arithmetic, not concatenation
```

### Why not a config file?

| Config file (`config.json`)                                      | Environment variables                                     |
| ---------------------------------------------------------------- | --------------------------------------------------------- |
| Committed to Git → secrets leak                                  | Injected at deploy time, never in the repo                |
| Same values in every environment unless you branch on `NODE_ENV` | Different values per environment, same code               |
| A file must exist on disk in production                          | Nothing to copy or to get wrong; provided by the platform |
| Cannot be changed without a deploy or editing files              | Rotate a secret by changing a variable and restarting     |
| Hard to keep out of a Docker image                               | Never baked into the image                                |

This is the **third factor of the Twelve-Factor App**: _store config in the environment_. The rule of thumb: **if a value differs between development, staging and production, it belongs in an environment variable. If it is the same everywhere and is not a secret, it can live in code.**

***

## 2. `.env` files for local development

Typing `PORT=3000 DATABASE_URL=... node server.js` every time is impractical. Instead, put those values in a `.env` file and load them at startup.

Given this `.env`:

```bash
# .env — NEVER commit this file
NODE_ENV=development
PORT=3000
DATABASE_URL=postgres://app_user:local_password@localhost:5432/notes_dev
JWT_SECRET=dev-only-secret-not-used-in-production
LOG_LEVEL=debug
CORS_ORIGINS=http://localhost:5173,http://localhost:3001
```

### Loading it

```bash
# Node 20.6+ — built in, no dependency, no code.
node --env-file=.env src/server.js

# Node 22+ — do not fail if the file is missing (nice for CI where it is absent).
node --env-file-if-exists=.env src/server.js
```

```json
// package.json (fragment)
{
  "scripts": {
    "dev": "node --watch --env-file-if-exists=.env src/server.js",
    "start": "node src/server.js"
  }
}
```

**Do not add `dotenv` to a new project.** Node has this built in, and `--env-file` has no runtime cost or dependency. (`dotenv` is still fine in an existing codebase, and `dotenv` remains useful if you need multiple files or programmatic loading.)

If you do use the library:

```js
// File: dotenv-preview.mjs
// import 'dotenv/config';        // side-effect import: loads .env into process.env
// or explicitly:
// import { config } from 'dotenv';
// config({ path: '.env.local' });
console.log('For new projects, prefer: node --env-file=.env src/server.js');
```

### Always commit a `.env.example`

```bash
# .env.example — COMMITTED. Documents every variable the app needs. No real secrets.
NODE_ENV=development
PORT=3000
DATABASE_URL=postgres://user:password@localhost:5432/dbname
JWT_SECRET=replace-me-with-a-64-character-random-string
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:5173
```

```gitignore
# .gitignore
.env
.env.local
.env.*.local
!.env.example
```

**Why `.env.example` matters more than it looks:** it is the contract between the application and whoever deploys it. A new developer runs `cp .env.example .env` and knows exactly what to fill in; a deployment fails loudly at startup instead of mysteriously at request time.

***

## 3. Loading and validating configuration: the professional pattern

The worst way to read configuration is scattered `process.env.X` calls, because:

* Typos (`process.env.DATABSE_URL`) are silently `undefined`.
* Each use site decides its own defaults and coercion.
* Nothing fails at startup; failures appear later, on a user's request.
* The set of required variables is undocumented.

The good pattern: **read and validate everything once, at startup, in one module.**

```js
// File: src/config/env.js
/**
 * Central, validated configuration.
 *
 * Rules this module enforces:
 *  1. Fails FAST at startup, not at request time.
 *  2. Every value is coerced to the right type ONCE.
 *  3. Secrets never have development defaults in production.
 *  4. The list of required variables is the code itself.
 */

function required(name) {
  const value = process.env[name];
  if (value === undefined || value === '') {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function optional(name, fallback) {
  const value = process.env[name];
  return value === undefined || value === '' ? fallback : value;
}

function optionalInt(name, fallback, { min = -Infinity, max = Infinity } = {}) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const parsed = Number(raw);
  if (!Number.isInteger(parsed)) {
    throw new Error(`Environment variable ${name} must be an integer, received "${raw}"`);
  }
  if (parsed < min || parsed > max) {
    throw new Error(`${name} must be between ${min} and ${max}, received ${parsed}`);
  }
  return parsed;
}

function optionalBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const normalised = raw.toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(normalised)) return true;
  if (['0', 'false', 'no', 'off'].includes(normalised)) return false;
  throw new Error(`${name} must be a boolean (true/false), received "${raw}"`);
}

function optionalList(name, fallback = []) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  return raw.split(',').map((item) => item.trim()).filter(Boolean);
}

const NODE_ENV = optional('NODE_ENV', 'development');
const isProduction = NODE_ENV === 'production';

// Secrets must be provided in production; in development a clearly-labelled
// placeholder keeps local setup friction low without ever being deployable.
function secret(name, developmentFallback) {
  const value = process.env[name];
  if (value && value.length > 0) return value;
  if (isProduction) throw new Error(`${name} must be set in production`);
  return developmentFallback;
}

export const env = Object.freeze({
  nodeEnv: NODE_ENV,
  isProduction,
  isDevelopment: NODE_ENV === 'development',
  isTest: NODE_ENV === 'test',

  port: optionalInt('PORT', 3000, { min: 0, max: 65535 }),
  host: optional('HOST', '0.0.0.0'),

  databaseUrl: required('DATABASE_URL'),
  databasePoolSize: optionalInt('DATABASE_POOL_SIZE', 10, { min: 1, max: 100 }),

  jwtSecret: secret('JWT_SECRET', 'development-only-secret-do-not-deploy'),
  jwtAccessTtl: optional('JWT_ACCESS_TTL', '15m'),
  jwtRefreshTtl: optional('JWT_REFRESH_TTL', '7d'),

  corsOrigins: optionalList('CORS_ORIGINS', ['http://localhost:5173']),
  logLevel: optional('LOG_LEVEL', isProduction ? 'info' : 'debug'),

  rateLimitWindowMs: optionalInt('RATE_LIMIT_WINDOW_MS', 60_000),
  rateLimitMax: optionalInt('RATE_LIMIT_MAX', 100),

  trustProxy: optionalBool('TRUST_PROXY', isProduction),
});

/** Fail fast and loudly if the configuration is inconsistent. */
export function assertValidConfig() {
  if (env.isProduction && env.jwtSecret.length < 32) {
    throw new Error('JWT_SECRET must be at least 32 characters in production');
  }
  if (env.isProduction && env.corsOrigins.includes('*')) {
    throw new Error('CORS_ORIGINS must not be "*" in production');
  }
  return env;
}
```

```js
// File: src/server.js (fragment)
import { env, assertValidConfig } from './config/env.js';

try {
  assertValidConfig();
} catch (error) {
  // Print to stderr and exit non-zero: the orchestrator will show the message and stop restarting
  // a process that can never become healthy.
  console.error(`Configuration error: ${error.message}`);
  process.exit(1);
}

console.log(`Starting in ${env.nodeEnv} mode on ${env.host}:${env.port}`);
console.log(`Database configured: ${env.databaseUrl.replace(/:\/\/[^@]*@/, '://***@')}`);
console.log(`CORS origins: ${env.corsOrigins.join(', ')}`);
```

**Why failure at startup is so valuable:** a misconfigured deployment crashes immediately, the platform marks the release unhealthy, and you roll back in seconds. The alternative — a missing `JWT_SECRET` discovered when the first user tries to log in — is far more expensive.

### Bonus: schema validation with Zod

If you already use Zod for request validation ([02-express/12-validation.md](../02-express/12-validation.md)), use it for the environment too:

```js
// File: src/config/env-zod.mjs
import { z } from 'zod';

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DATABASE_URL: z.string().url().startsWith('postgres'),
  JWT_SECRET: z.string().min(32, 'JWT_SECRET must be at least 32 characters'),
  CORS_ORIGINS: z
    .string()
    .default('http://localhost:5173')
    .transform((value) => value.split(',').map((origin) => origin.trim())),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

// Simulate a valid environment for this example (process.env is read-only-ish in practice).
const candidate = {
  NODE_ENV: 'development',
  PORT: '3000',
  DATABASE_URL: 'postgres://localhost:5432/app',
  JWT_SECRET: 'a'.repeat(40),
  LOG_LEVEL: 'debug',
};

const result = envSchema.safeParse(candidate);

if (!result.success) {
  console.error('Invalid configuration:');
  for (const issue of result.error.issues) {
    console.error(`  ${issue.path.join('.')}: ${issue.message}`);
  }
  process.exitCode = 1;
} else {
  const env = result.data;
  console.log('validated config:', { ...env, JWT_SECRET: '[redacted]' });
  console.log('PORT type is now:', typeof env.PORT);             // number — coerced
  console.log('origins is now an array:', Array.isArray(env.CORS_ORIGINS));
}
```

This gives you: coercion, defaults, enums, a complete list of every issue at once (instead of crashing on the first one), and a typed object to import.

***

## 4. `NODE_ENV` and what it is actually for

```js
// File: node-env-usage.mjs
const isProduction = process.env.NODE_ENV === 'production';
const isTest = process.env.NODE_ENV === 'test';

console.log({ isProduction, isTest, value: process.env.NODE_ENV ?? 'undefined' });

// Legitimate uses:
// 1. Error verbosity — never leak stack traces in production.
const errorResponse = (error) =>
  isProduction
    ? { error: { code: 'INTERNAL_ERROR', message: 'Something went wrong' } }
    : { error: { message: error.message, stack: error.stack } };

console.log(errorResponse(new Error('db is down')));

// 2. Cookie security flags.
const cookieOptions = {
  httpOnly: true,
  secure: isProduction,     // HTTPS-only in production
  sameSite: 'lax',
  maxAge: 1000 * 60 * 60 * 24,
};
console.log('cookie secure flag:', cookieOptions.secure);

// 3. Log format — pretty in development, JSON when aggregated.
console.log('log format:', isProduction ? 'json' : 'pretty');

// 4. Test behaviour: fake services instead of real ones.
if (isTest) {
  console.log('would use a fake mailer / in-memory database');
}
```

### What `NODE_ENV` should **not** be used for

| Anti-pattern                                  | Why it is wrong                                                                       |
| --------------------------------------------- | ------------------------------------------------------------------------------------- |
| Feature flags (`if (NODE_ENV === 'staging')`) | Staging is not an environment Node knows about; use explicit flags (`FEATURE_X=true`) |
| Selecting the database                        | Use `DATABASE_URL`; the URL already says which database                               |
| Distinguishing staging from production        | They are both "production-like"; use explicit `APP_ENV`/`ENVIRONMENT` if you need it  |
| Putting business logic behind it              | Configuration is not behaviour; it becomes untestable                                 |

Many libraries (React, Express's error behaviour, various ORMs) read `NODE_ENV` and change their behaviour. Always set it explicitly: `NODE_ENV=development` locally, `test` in tests, `production` when deployed.

> **Docker trap:** setting `NODE_ENV=production` as a **build-time** variable makes `npm install` skip devDependencies — so build tooling (TypeScript, bundlers) disappears mid-build. Set it at **runtime** (`docker run -e NODE_ENV=production`) or use a multi-stage build with `npm ci --omit=dev` in the final stage only.

***

## 5. Secrets: handling them like a professional

Environment variables are better than a config file, but they are not magic. Rules that prevent the most common incidents:

| Rule                                                                                                                                       | Why                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| **Never commit secrets** — not in `.env`, not in code, not in Dockerfiles, not in CI YAML                                                  | Git history is forever, and it is often public                   |
| **Never log them** — redact before logging                                                                                                 | Logs are copied into tickets, dashboards and third-party tools   |
| **Never send them to the client** — no secret in a JSON response, a URL, or client-side code                                               | The client is untrusted                                          |
| **Use different secrets per environment**                                                                                                  | A leaked dev secret must not open production                     |
| **Rotate on exposure, not just deletion**                                                                                                  | Removing a line from a file does not un-leak it                  |
| **Prefer a secret manager in production** (AWS Secrets Manager, GCP Secret Manager, Vault, Doppler, or your platform's encrypted env vars) | Auditable, rotatable, access-controlled                          |
| **Use high-entropy values**                                                                                                                | `JWT_SECRET=dev123` is brute-forceable; use ≥32 random bytes     |
| **Give secrets the shortest life that works**                                                                                              | Rotate on a schedule; short-lived DB credentials where supported |

### Generate strong secrets

```bash
# 32 random bytes as hex (64 characters) — use for JWT_SECRET, sessions, etc.
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

```bash
# Or with openssl
openssl rand -hex 32
```

### Redacting secrets in logs

```js
// File: redact.mjs
const SECRET_PATTERNS = [
  /(authorization|cookie|set-cookie|x-api-key)":\s*"[^"]*"/gi,
  /(password|secret|token|apiKey|api_key)":\s*"[^"]*"/gi,
  /:\/\/[^:@/]+:[^@/]+@/g,                      // credentials inside a connection URL
];

export function redact(value) {
  if (typeof value === 'string') {
    return SECRET_PATTERNS.reduce((acc, pattern) => acc.replace(pattern, (match) => {
      const [key] = match.split('":');
      return key ? `${key}":"[REDACTED]"` : '[REDACTED]';
    }), value);
  }
  if (value instanceof Error) {
    return { name: value.name, message: redact(value.message), stack: value.stack };
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, val]) => [
        key,
        /password|secret|token|apikey|authorization|cookie/i.test(key) ? '[REDACTED]' : redact(val),
      ])
    );
  }
  return value;
}

console.log(
  redact({
    user: 'ankit',
    password: 'hunter2',
    nested: { apiKey: 'sk_live_abc123' },
    url: 'postgres://app:dbpassword@localhost:5432/app',
  })
);

console.log(redact('Connecting with token=eyJhbGciOiJIUzI1NiJ9.secret.value'));
```

```
{
  user: 'ankit',
  password: '[REDACTED]',
  nested: { apiKey: '[REDACTED]' },
  url: 'postgres://app:dbpassword@localhost:5432/app'
}
Connecting with token=[REDACTED]
```

_(Note that the connection URL needs the URL-specific pattern to be caught — which is exactly why you should log a redacted form of the URL, or better, log the host and database name separately rather than the raw URL.)_

***

## 6. Full worked example: the config module in use

```
project/
├── .env                 ← local only, gitignored
├── .env.example         ← committed template
├── .gitignore
├── package.json         ← "dev": "node --watch --env-file-if-exists=.env src/server.js"
└── src/
    ├── config/
    │   └── env.js       ← reads + validates everything once
    └── server.js
```

```js
// File: src/server.mjs — a complete, runnable demonstration
import { env, assertValidConfig } from './config/env.js';

function main() {
  assertValidConfig();

  // Every consumer imports `env` and gets typed, validated, frozen values.
  const serverConfig = {
    port: env.port,
    host: env.host,
    mode: env.nodeEnv,
    corsOrigins: env.corsOrigins,
    logLevel: env.logLevel,
    cookieSecure: env.isProduction,
    db: {
      // Never log this raw — see the redaction section.
      host: new URL(env.databaseUrl).host,
      poolSize: env.databasePoolSize,
    },
  };

  console.log('Effective configuration:');
  console.log(JSON.stringify(serverConfig, null, 2));

  // At this point the application is SAFE to start: every value it needs exists
  // and has the right type. Any later failure is a genuine runtime failure.
}

main();
```

```bash
# Local development (reads .env)
npm run dev

# Production (values come from the platform; no .env file exists)
NODE_ENV=production \
PORT=8080 \
DATABASE_URL="postgres://u:p@db.internal:5432/prod" \
JWT_SECRET="$(openssl rand -hex 32)" \
node src/server.mjs
```

***

## 7. Common mistakes

| Mistake                                                                             | Symptom                                        | Fix                                                    |
| ----------------------------------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| Committing `.env`                                                                   | Secrets in Git history forever                 | `.gitignore` + `.env.example`; rotate anything exposed |
| `process.env` scattered across the codebase                                         | Silent typos, inconsistent defaults            | One `config/env.js`                                    |
| Treating env values as numbers/booleans                                             | `"3000" + 1 === "30001"`; `"false"` is truthy  | Coerce explicitly in the config module                 |
| No validation                                                                       | App starts, then fails on the first request    | Validate and exit(1) at startup                        |
| Development defaults for secrets in production                                      | Deployable with `JWT_SECRET=dev-secret`        | Throw in production when unset; check length           |
| Logging the whole `process.env`                                                     | Every secret in your logs                      | Never log it; log specific redacted values             |
| Putting config in a committed `config.json`                                         | Secrets in the repo; no per-environment values | Environment variables                                  |
| `NODE_ENV=production` at Docker build time                                          | Build dependencies disappear mid-build         | Set it at runtime, multi-stage builds                  |
| Changing an env var and expecting hot reload                                        | The value is read once at startup              | Restart/redeploy (or read it deliberately)             |
| Using `dotenv` when Node has `--env-file`                                           | Unnecessary dependency                         | Built-in flag                                          |
| Forgetting that `.env` values do **not** override real env vars (with `--env-file`) | Confusing precedence                           | Understand the precedence order; document it           |

**Precedence:** real environment variables set by the platform are what `process.env` contains at startup; `--env-file` fills in _additional_ variables. In practice, do not rely on subtle precedence: make the platform's variables authoritative and treat `.env` as a local convenience only.

***

## Exercise 15.1 — Write a config module and prove it fails fast

Requirements:

1. Variables: `PORT` (int, 1–65535, default 3000), `DATABASE_URL` (required), `JWT_SECRET` (required, ≥32 chars in production, dev fallback allowed), `LOG_LEVEL` (enum: debug/info/warn/error, default info), `RATE_LIMIT_MAX` (int, default 100), `ENABLE_METRICS` (boolean, default false).
2. Collect **all** problems and report them together, not one at a time.
3. Never print a secret value.
4. Show three scenarios: valid, missing required vars, and an invalid type.

<details>

<summary>Solution</summary>

```js
// File: config.mjs
const LEVELS = ['debug', 'info', 'warn', 'error'];

/** Collect every configuration problem rather than failing on the first. */
export function loadConfig(source = process.env) {
  const problems = [];
  const nodeEnv = source.NODE_ENV ?? 'development';
  const isProduction = nodeEnv === 'production';

  const readInt = (name, fallback, { min, max } = {}) => {
    const raw = source[name];
    if (raw === undefined || raw === '') return fallback;
    if (!/^-?\d+$/.test(raw.trim())) {
      problems.push(`${name} must be an integer (received "${raw}")`);
      return fallback;
    }
    const value = Number(raw);
    if (min !== undefined && value < min) problems.push(`${name} must be >= ${min} (received ${value})`);
    if (max !== undefined && value > max) problems.push(`${name} must be <= ${max} (received ${value})`);
    return value;
  };

  const readString = (name, { required = false, fallback, minLength } = {}) => {
    const raw = source[name];
    if (raw === undefined || raw === '') {
      if (required) problems.push(`${name} is required and must not be empty`);
      return fallback;
    }
    if (minLength !== undefined && raw.length < minLength) {
      problems.push(`${name} must be at least ${minLength} characters (received ${raw.length})`);
    }
    return raw;
  };

  const readBool = (name, fallback) => {
    const raw = source[name];
    if (raw === undefined || raw === '') return fallback;
    const normalised = raw.toLowerCase();
    if (['1', 'true', 'yes', 'on'].includes(normalised)) return true;
    if (['0', 'false', 'no', 'off'].includes(normalised)) return false;
    problems.push(`${name} must be a boolean like true/false (received "${raw}")`);
    return fallback;
  };

  const readEnum = (name, allowed, fallback) => {
    const raw = source[name];
    if (raw === undefined || raw === '') return fallback;
    if (!allowed.includes(raw)) {
      problems.push(`${name} must be one of ${allowed.join(' | ')} (received "${raw}")`);
      return fallback;
    }
    return raw;
  };

  const databaseUrl = readString('DATABASE_URL', { required: true });
  if (databaseUrl !== undefined && !/^postgres(ql)?:\/\//.test(databaseUrl)) {
    problems.push('DATABASE_URL must be a postgres:// connection string');
  }

  let jwtSecret = readString('JWT_SECRET', {
    required: isProduction,
    minLength: isProduction ? 32 : undefined,
    fallback: isProduction ? undefined : 'development-only-secret-change-me',
  });

  const config = {
    nodeEnv,
    isProduction,
    port: readInt('PORT', 3000, { min: 1, max: 65535 }),
    databaseUrl,
    jwtSecret,
    logLevel: readEnum('LOG_LEVEL', LEVELS, 'info'),
    rateLimitMax: readInt('RATE_LIMIT_MAX', 100, { min: 1, max: 1_000_000 }),
    enableMetrics: readBool('ENABLE_METRICS', false),
  };

  if (!isProduction && config.jwtSecret === undefined) {
    config.jwtSecret = 'development-only-secret-change-me';
  }

  return { config, problems };
}

/** Throwing variant, for use at startup. */
export function loadConfigOrThrow(source) {
  const { config, problems } = loadConfig(source);
  if (problems.length > 0) {
    throw new Error(`Invalid configuration:\n  - ${problems.join('\n  - ')}`);
  }
  return config;
}

/** Print the effective config with secrets redacted. */
export function describeConfig(config) {
  return {
    ...config,
    databaseUrl: config.databaseUrl?.replace(/:\/\/[^@]*@/, '://***:***@'),
    jwtSecret: config.jwtSecret ? `[redacted, ${config.jwtSecret.length} chars]` : undefined,
  };
}

// ---------------------------------------------------------------------------
// Scenario 1: valid
// ---------------------------------------------------------------------------
const validSource = {
  NODE_ENV: 'development',
  PORT: '3000',
  DATABASE_URL: 'postgres://app:secret@localhost:5432/notes',
  LOG_LEVEL: 'debug',
  ENABLE_METRICS: 'true',
};

const scenario1 = loadConfig(validSource);
console.log('Scenario 1 — valid');
console.log('  problems:', scenario1.problems);            // []
console.log('  config:', describeConfig(scenario1.config));

// ---------------------------------------------------------------------------
// Scenario 2: missing required variables (production)
// ---------------------------------------------------------------------------
const scenario2 = loadConfig({ NODE_ENV: 'production', PORT: '8080' });
console.log('\nScenario 2 — missing required in production');
console.log('  problems:');
for (const problem of scenario2.problems) console.log(`    - ${problem}`);

// ---------------------------------------------------------------------------
// Scenario 3: invalid types and enum values
// ---------------------------------------------------------------------------
const scenario3 = loadConfig({
  NODE_ENV: 'production',
  PORT: 'not-a-port',
  DATABASE_URL: 'mysql://wrong-db/app',
  JWT_SECRET: 'too-short',
  LOG_LEVEL: 'verbose',
  RATE_LIMIT_MAX: '-5',
  ENABLE_METRICS: 'maybe',
});

console.log('\nScenario 3 — invalid values (ALL reported at once)');
for (const problem of scenario3.problems) console.log(`    - ${problem}`);

// Demonstrate the throwing variant used at startup.
try {
  loadConfigOrThrow({ NODE_ENV: 'production' });
} catch (error) {
  console.log('\nStartup guard message:');
  console.log(error.message);
}
```

Expected output:

```
Scenario 1 — valid
  problems: []
  config: {
    nodeEnv: 'development',
    isProduction: false,
    port: 3000,
    databaseUrl: 'postgres://***:***@localhost:5432/notes',
    jwtSecret: '[redacted, 33 chars]',
    logLevel: 'debug',
    rateLimitMax: 100,
    enableMetrics: true
  }

Scenario 2 — missing required in production
  problems:
    - DATABASE_URL is required and must not be empty
    - JWT_SECRET is required and must not be empty

Scenario 3 — invalid values (ALL reported at once)
    - PORT must be an integer (received "not-a-port")
    - DATABASE_URL must be a postgres:// connection string
    - JWT_SECRET must be at least 32 characters (received 9)
    - LOG_LEVEL must be one of debug | info | warn | error (received "verbose")
    - RATE_LIMIT_MAX must be >= 1 (received -5)
    - ENABLE_METRICS must be a boolean like true/false (received "maybe")

Startup guard message:
Invalid configuration:
  - DATABASE_URL is required and must not be empty
  - JWT_SECRET is required and must not be empty
```

**Why this design is worth the 90 lines**

| Decision                         | Benefit                                                                |
| -------------------------------- | ---------------------------------------------------------------------- |
| Collect all problems, then throw | One deploy fixes everything, instead of one issue per deploy cycle     |
| Coercion in one place            | The rest of the codebase never sees a string where it expects a number |
| Enum and range checks            | Prevents `LOG_LEVEL=verbose` silently falling back to a default        |
| Production-only requirements     | Local development stays frictionless; production stays safe            |
| `describeConfig` redaction       | You can log the effective configuration in every environment safely    |
| `loadConfigOrThrow` at startup   | Failures happen at boot, when rollback is cheap                        |

**Follow-up challenges**

* Replace the hand-written checks with a Zod schema and compare the ergonomics.
* Add `CORS_ORIGINS` (a comma-separated list) and reject `*` in production.
* Add a check that `DATABASE_URL` contains `sslmode=require` when `NODE_ENV=production`.
* Write tests for the loader: valid, each failure mode, and both fallback behaviours.

</details>

***

## What's next

Configuration is handled. Next: error handling — the topic that separates code that works in a demo from code you can operate. Custom error classes, `async` errors, and the central error-handling strategy you will use in every Express app.

→ [16 — Error Handling](16-error-handling.md)
