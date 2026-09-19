# 05 — npm and package.json

> **Where this fits:** You can write modules; now you need everybody else's. npm is how Node
> packages are installed, versioned, scripted and published. This chapter covers the commands
> you will type every day, plus the parts people skip (semver, lockfiles, scripts, supply
> chain) that later cause "it works on my machine" incidents and CVEs.

---

## 1. What is npm?

**npm** (Node Package Manager) is three things at once, which is why it confuses people:

| Meaning | What it is | How you use it |
| --- | --- | --- |
| **The registry** | A public database of ~3.5 million packages at `registry.npmjs.org` | `npm install express` downloads from it |
| **The CLI** | The `npm` command, bundled with Node | `npm install`, `npm test`, `npm run dev` |
| **The company** | npm Inc. (acquired by GitHub/Microsoft in 2020) | Historical context |

It solves the oldest problem in software: **using code other people wrote, without copying it
into your repository**. `npm install express` gives you a web framework, its 28 dependencies,
and a lockfile pinning exact versions — in one command.

Alternatives you should know exist: **pnpm** (fast, disk-efficient, strict about undeclared
dependencies), **yarn** (classic alternative, Berry for PnP), **bun install** (extremely
fast), and **Deno's** built-in registry. All read the same `package.json`. Every command in
this chapter has an equivalent. Use npm until you have a specific reason not to.

---

## 2. `package.json` — the project's identity card

Created by `npm init`:

```bash
mkdir my-api && cd my-api
npm init -y      # -y accepts every default, giving you this:
```

```json
{
  "name": "my-api",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "keywords": [],
  "author": "",
  "license": "ISC"
}
```

A realistic production `package.json`:

```json
{
  "name": "employee-api",
  "version": "1.0.0",
  "description": "Employee management REST API",
  "type": "module",
  "main": "src/server.js",
  "engines": {
    "node": ">=22.0.0"
  },
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch --env-file=.env src/server.js",
    "test": "node --test tests/",
    "test:watch": "node --test --watch tests/",
    "lint": "eslint .",
    "format": "prettier --write .",
    "migrate": "node scripts/migrate.js"
  },
  "dependencies": {
    "bcrypt": "^6.0.0",
    "express": "^5.2.1",
    "helmet": "^8.1.0",
    "pino": "^10.0.0",
    "zod": "^4.1.11"
  },
  "devDependencies": {
    "eslint": "^9.30.0",
    "prettier": "^3.6.0",
    "supertest": "^7.1.0"
  },
  "private": true
}
```

### Every important field explained

| Field | Required? | Meaning | Practical notes |
| --- | --- | --- | --- |
| `name` | ✅ | Package name | Lowercase, no spaces, max 214 chars; must be unique on npm *if you publish* |
| `version` | ✅ | The package's semver version | Bump it before publishing; with `private: true` it is just bookkeeping |
| `description` | — | One line | Shown on npm; use it |
| `type` | — | `"module"` or `"commonjs"` | Decides whether `.js` files are ESM ([04](04-modules.md)) |
| `main` | — | Entry point | Used by `require('your-package')` |
| `exports` | — | Modern entry map; restricts deep imports | See [04 §8](04-modules.md) |
| `engines` | — | Required Node/npm versions | `npm install` warns; some hosts enforce it |
| `scripts` | — | Named shell commands | `npm run <name>`; the real productivity feature |
| `dependencies` | — | Needed at **runtime** | Installed in production |
| `devDependencies` | — | Needed only for **development** | **Not** installed with `npm ci --omit=dev` |
| `peerDependencies` | — | "You must install this too" | Used by plugins/frameworks |
| `optionalDependencies` | — | Install if possible; failure is not fatal | Native/OS-specific addons |
| `bundledDependencies` | — | Ship inside the tarball | Rare, for vendoring |
| `private` | — | `true` prevents accidental publishing | **Always set it for applications** |
| `license` | — | SPDX id | `MIT`, `ISC`, `UNLICENSED` for closed source |
| `workspaces` | — | Monorepo package globs | See §9 |

> **`dependencies` vs `devDependencies` — get this right.** A single misplaced package
> (`eslint`, `nodemon`, or worse a *build* step like `typescript`) in `dependencies` bloats
> your production image and increases your attack surface; a misplaced runtime package
> (`express`, a database driver) in `devDependencies` means your deploy crashes with
> `Cannot find module`. Rule: **if the app imports it at runtime, it is a dependency;
> everything else is a devDependency.**

---

## 3. The commands you will actually use

### Installing

```bash
npm install                     # install everything in package.json (respecting the lockfile)
npm install express             # add express to dependencies
npm install -D nodemon          # add nodemon to devDependencies (-D = --save-dev)
npm install express@5.2.1       # an exact version
npm install express@^5          # the newest 5.x
npm install express@latest      # the newest, ignoring semver ranges (be deliberate!)
npm install -g typescript       # install globally — for CLI tools only, not project libs
npm ci                          # clean, reproducible install from package-lock.json
```

**`npm install` vs `npm ci`** — know the difference cold:

| | `npm install` | `npm ci` |
| --- | --- | --- |
| Reads | `package.json` (+ lockfile as a hint) | The lockfile, **exactly** |
| May modify the lockfile | ✅ yes | ❌ never |
| Deletes `node_modules` first | ❌ no | ✅ yes |
| Speed | Slower | Faster |
| Use it for | Development, adding packages | **CI/CD, Docker builds, production deploys** |
| Fails if `package.json` and lock disagree | ❌ no | ✅ yes — which is the point |

The lockfile is not optional. `package.json` says `^5.2.1` (a *range*); the lockfile records
the exact resolved version **and the integrity hash of every transitive dependency**. Without
it, two builds a week apart can produce different dependency trees.

### Removing and updating

```bash
npm uninstall express              # remove from dependencies and node_modules
npm update                         # update within the semver ranges in package.json
npm outdated                       # what is behind, and how far
npm audit                          # known vulnerabilities in your tree
npm audit fix                      # apply compatible fixes (stays within your ranges)
npm audit fix --force              # ⚠️ may install BREAKING versions — review the diff
npm ls express                     # why is this version installed? (shows the dependency path)
npm ls --all --depth=3 | head -40  # inspect the whole tree
```

`npm outdated` output:

```text
Package  Current  Wanted  Latest  Location          Depended by
express   5.1.0    5.2.1   5.2.1  node_modules/express  my-api
zod       4.0.1    4.1.11  4.1.11 node_modules/zod      my-api
```

- **Current** — what is actually installed.
- **Wanted** — the newest version that satisfies your semver range (what `npm update` gives).
- **Latest** — the newest published version, possibly outside your range.

```bash
npm install express@latest         # moving to "Latest" explicitly
```

### Running scripts

```bash
npm run dev            # any script in package.json
npm start              # shorthand for `npm run start`
npm test               # shorthand for `npm run test`
npm run                # list all available scripts
npm run dev -- --port 4000    # pass extra arguments after --
npm run lint && npm test      # chain commands like any shell
```

### `npm init` and `npx`

```bash
npm init                 # interactive
npm init -y              # all defaults
npm init node-package    # use a starter template (create-* package)
npx create-vite@latest   # download and run a CLI without installing it globally
npx cowsay "hello"
```

**`npx`** runs a package's binary, downloading it temporarily if needed. Use it for one-off
tools (scaffolding, `npx eslint`, `npx prettier`) and prefer local `devDependencies` for
anything the project depends on — installing globally makes builds depend on the machine.

---

## 4. Semantic versioning (semver)

A version is `MAJOR.MINOR.PATCH`:

```text
        5   .   2   .   1
        │       │       │
        │       │       └── PATCH: backward-compatible bug fixes
        │       └────────── MINOR: backward-compatible new features
        └────────────────── MAJOR: breaking changes
```

Rule from semver.org: **once a version is released, its contents must not change.** A "bug fix
release" that secretly changes behaviour breaks every consumer's ability to trust ranges.

### Ranges and how they resolve

| Syntax | Meaning | Example resolves to |
| --- | --- | --- |
| `1.2.3` | Exactly this version | `1.2.3` |
| `^1.2.3` | Compatible with 1.x — do not change the leftmost non-zero digit | `>=1.2.3 <2.0.0` |
| `~1.2.3` | Patch-level changes | `>=1.2.3 <1.3.0` |
| `1.2.x` | Any patch | `>=1.2.0 <1.3.0` |
| `*` or `x` | Anything | the newest version (dangerous) |
| `>1.2.3`, `<=2.0.0` | Comparisons | as written |
| `1.2.3 - 2.3.4` | Inclusive range | as written |
| `>=1.2.3 <2.0.0 \|\| >=3.0.0` | Union of ranges | either |
| `npm:other-package@1.2.3` | Alias | install `other-package` under a different name |

Pre-release versions (`2.0.0-beta.1`) are **excluded** from every range unless you ask for them
explicitly (`^2.0.0-beta.1`). That is deliberate: you do not want a beta pulled in by a range.

The default when you `npm install express` is `^`:

```json
"dependencies": {
  "express": "^5.2.1"
}
```

**What `^` really means for you:** a fresh `npm install` (with no lockfile) can pull in
`5.9.0` later, including behaviour changes nobody reviewed. That is a *feature* (you get fixes)
and a *risk* (you get surprises). The industry's answer is the lockfile plus a deliberate
upgrade process:

```bash
npm outdated                 # see what is available
npm install express@5.2.1    # pin if you must
npm update                   # take the whole tree forward, then run your tests
```

**For applications, commit the lockfile. For libraries, also commit it but expect consumers to
resolve their own trees.**

### Zero-major versions behave differently

In `0.x.y`, the *minor* number is the breaking one. `^0.2.1` means `>=0.2.1 <0.3.0` — because
at `0.x`, anything may change. Many packages stay at `0.x` for years, which is why you see so
many `^0.x` ranges.

---

## 5. Lockfiles

`package-lock.json` records:

- The exact version of **every** package in the tree, including transitive ones.
- The `resolved` URL for each tarball.
- An `integrity` hash (SHA-512) — if the contents do not match, the install fails.

Snippet:

```json
{
  "name": "employee-api",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "node_modules/express": {
      "version": "5.2.1",
      "resolved": "https://registry.npmjs.org/express/-/express-5.2.1.tgz",
      "integrity": "sha512-…",
      "dependencies": { "router": "^2.2.0", … },
      "engines": { "node": ">= 18" }
    }
  }
}
```

Why this file is critical:

| Without a lockfile | With a lockfile |
| --- | --- |
| `npm install` may resolve different versions on different days | Identical tree everywhere |
| "Works on my machine" dependency drift | Reproducible builds |
| No integrity checking | Tampering is detected |
| `npm ci` impossible | `npm ci` works |

Rules:

1. **Commit `package-lock.json`.**
2. **Never edit it by hand.** Use npm commands.
3. **Use `npm ci` in CI and Docker.**
4. If two branches conflict on the lockfile, do not merge by hand — take either side,
   re-run `npm install`, and commit the result.
5. `npm ci` honours `--omit=dev` (or the older `--production`) to skip devDependencies.

---

## 6. Node's built-in tooling: fewer dependencies

Before adding a dev dependency, check whether Node already does it (Node 24):

| Need | Dependency people install | Built into Node |
| --- | --- | --- |
| Auto-restart on change | `nodemon` | ✅ `node --watch` |
| Load `.env` | `dotenv` | ✅ `node --env-file=.env` |
| Run tests | `jest`/`mocha` | ✅ `node --test` (plus `node:assert`) |
| TypeScript execution | `ts-node` | ✅ `node --experimental-strip-types` (v22+) — improving every release |
| HTTP client | `axios`/`node-fetch` | ✅ global `fetch` |
| UUID generation | `uuid` | ✅ `crypto.randomUUID()` |
| Argument parsing | `yargs`/`commander` | ✅ `node:util`'s `parseArgs` |
| Watch a directory | `chokidar` | ✅ `fs.watch` (less featureful but fine for scripts) |

```json
{
  "scripts": {
    "dev": "node --watch --env-file=.env src/server.js",
    "test": "node --test"
  }
}
```

A modern Node project can have **zero devDependencies** and still have watch mode, env files
and tests. Libraries like `pino`, `zod` and `supertest` still earn their place — but do not
install what the platform gives you for free.

---

## 7. Dependencies in production

```bash
# Production installs: no linters, no test frameworks, no bundlers.
npm ci --omit=dev

# Or, equivalently, with the env var:
NODE_ENV=production npm ci
```

Then in code:

```js
// File: env-check.mjs
if (process.env.NODE_ENV === 'production' && !process.env.DATABASE_URL) {
  console.error('FATAL: DATABASE_URL must be set in production');
  process.exit(1);
}
```

> **A trap worth knowing:** some packages decide behaviour from `NODE_ENV`. A common incident is
> `NODE_ENV=production` being set during `npm install` in a Docker build, which silently skips
> devDependencies *and* can change how packages install themselves. Set `NODE_ENV` at **runtime**
> (`docker run -e NODE_ENV=production` or in your compose/service config), and use
> `npm ci --omit=dev` for the build stage if you need to skip dev packages.

---

## 8. Supply chain security

Your app trusts ~500 transitive packages you have never read. Reality check: typosquatting,
maintainer account takeovers, and malicious postinstall scripts are all real and common.

The defences, in order of value:

```bash
npm audit                      # known CVEs in your tree
npm audit --omit=dev           # only what ships to production
npm audit --json | jq '.metadata.vulnerabilities'
```

| Practice | Why |
| --- | --- |
| Commit the lockfile | Pins and integrity-checks the whole tree |
| `npm ci`, never `npm install`, in CI | Cannot silently rewrite versions |
| `npm audit` in CI | A failing build on a new CVE is a feature |
| Dependabot / Renovate | Automated, reviewed upgrade PRs |
| `--ignore-scripts` where possible | Blocks postinstall script execution from packages you do not trust |
| Read the diff when adding a dependency | `npm install x` is running code you did not write |
| Prefer fewer, well-maintained packages | Every dependency is an attack surface and a future migration |
| Check the package before installing | Downloads, last publish date, repository link, maintainer count |

```bash
# Inspect a package before installing it
npm view express version time.modified maintainers repository.url
npm view some-suspicious-package dist.tarball
```

Red flags: a package name one character off a popular one, no repository link, published
yesterday, a postinstall script that curls a URL, or a sudden new maintainer on a dormant
package.

### `overrides` — forcing a patched transitive version

When a vulnerable package is not a direct dependency, you cannot fix it by upgrading your own
dependency. Use `overrides`:

```json
{
  "overrides": {
    "minimist@<1.2.6": "1.2.8"
  }
}
```

Then `npm install` again and commit the new lockfile. Use this sparingly and document why —
overrides can break a package that relied on the old behaviour.

---

## 9. Workspaces (monorepos)

When one repository contains several packages that share code:

```json
// package.json (root)
{
  "name": "acme-platform",
  "private": true,
  "workspaces": ["packages/*", "apps/*"],
  "scripts": {
    "test": "npm run test --workspaces --if-present"
  }
}
```

```text
acme-platform/
├── package.json          ← workspaces root, one lockfile, one node_modules
├── apps/
│   ├── api/              ← the Express backend
│   └── worker/
└── packages/
    ├── shared-types/
    └── validation/       ← reused by both apps
```

```bash
npm install -w apps/api express     # install into one workspace
npm run dev -w apps/api             # run a script in one workspace
npm run test --workspaces           # run everywhere
```

Benefits: one `npm install`, one lockfile, and `packages/validation` can be imported by
`apps/api` without publishing. Cost: hoisting subtleties (a package can accidentally import
something it did not declare) and a more complex build. Do not reach for workspaces until you
actually have two packages to share — with npm, the cost is real and the benefit is zero until
then.

---

## 10. Common mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Installing a runtime package with `-D` | `Cannot find module 'express'` in production | Move it to `dependencies` |
| Installing a dev tool as a dependency | Bloated images, extra CVEs | `npm uninstall x && npm install -D x` |
| Not committing the lockfile | Different versions per machine/CI run | Commit `package-lock.json` |
| `npm install` in CI | Silently different trees | `npm ci` |
| Hand-editing the lockfile | Corrupt, unreproducible tree | Delete and regenerate: `rm -rf node_modules package-lock.json && npm install` |
| Using `*` or `latest` ranges | Unreviewed breaking upgrades | Use `^` plus a lockfile; pin when needed |
| `npm audit fix --force` blindly | Major version jumps break your app | Review the diff, then test |
| Global installs for project tools | Builds depend on the developer's machine | Local `devDependencies` + `npx` |
| Committing `node_modules` | Gigabytes in Git, merge pain | `.gitignore` |
| Secrets in `package.json` scripts | They end up in logs and CI output | Env vars, never inline |
| Installing a package before reading it | Supply chain compromise | Check the repo, downloads, publish date |

A minimal `.gitignore` for a Node backend:

```gitignore
node_modules/
.env
.env.*
!.env.example
dist/
coverage/
*.log
.DS_Store
```

---

## Exercise 5.1 — Set up a project properly

Create a project `notes-api` with the following, without looking at the solution until you
have typed it yourself:

1. `package.json` with ESM, Node 22+, and `/bin` if that feels right.
2. Scripts: `start` (production), `dev` (watch + env file), `test` (built-in runner), `lint`.
3. Runtime dependencies: `express`, `zod`, `helmet`.
4. Dev dependencies: `supertest`, `eslint`.
5. A `.gitignore` that excludes `node_modules` and `.env` but keeps `.env.example`.
6. A `.env.example` documenting `PORT`, `NODE_ENV`, `DATABASE_URL`, `JWT_SECRET`.
7. A `.nvmrc`.

<details>
<summary>Solution</summary>

```bash
mkdir notes-api && cd notes-api
npm init -y
npm pkg set type=module
npm pkg set engines.node=">=22.0.0"
npm pkg set private=true
npm pkg set scripts.start="node src/server.js"
npm pkg set scripts.dev="node --watch --env-file=.env src/server.js"
npm pkg set scripts.test="node --test tests/"
npm pkg set scripts.lint="eslint ."
npm install express zod helmet
npm install -D supertest eslint
printf '24\n' > .nvmrc
```

> Tip: `npm pkg set` writes correct JSON for you — it is much less error-prone than hand-editing
> `package.json`, and it is a good habit to have.

Resulting `package.json` (dependencies will carry the versions that were current when you ran
it — yours will differ, and that is expected):

```json
{
  "name": "notes-api",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch --env-file=.env src/server.js",
    "test": "node --test tests/",
    "lint": "eslint ."
  },
  "engines": { "node": ">=22.0.0" },
  "private": true,
  "type": "module",
  "dependencies": {
    "express": "^5.2.1",
    "helmet": "^8.1.0",
    "zod": "^4.1.11"
  },
  "devDependencies": {
    "eslint": "^9.30.0",
    "supertest": "^7.1.0"
  }
}
```

`.gitignore`:

```gitignore
node_modules/
.env
.env.*
!.env.example
coverage/
*.log
.DS_Store
```

`.env.example`:

```bash
# Copy to .env and fill in real values. NEVER commit .env.
NODE_ENV=development
PORT=3000
DATABASE_URL=postgres://user:password@localhost:5432/notes
JWT_SECRET=replace-with-a-long-random-string
```

`.nvmrc`:

```text
24
```

```bash
nvm use          # reads .nvmrc
npm run dev      # starts with watch + env file loaded
```

**Checks worth doing:** `git status` must **not** list `node_modules/` or `.env`.
`npm ci && npm test` must work on a clean clone — that is the real definition of "setup
complete". Verify with:

```bash
rm -rf node_modules
npm ci
npm run test
```

</details>

## Exercise 5.2 — Diagnose the dependency problem

Your CI pipeline fails with:

```text
Error: Cannot find module 'helmet'
Require stack:
- /app/src/app.js
```

`package.json` shows `"helmet": "^8.1.0"` under **devDependencies**, and the Dockerfile runs
`npm ci --omit=dev`. Explain what happened, give two possible fixes, and say which is correct.

<details>
<summary>Solution</summary>

**What happened:** `helmet` is imported by `src/app.js`, which runs in production. But it is
declared as a *development* dependency, and the production install explicitly omits dev
dependencies (`npm ci --omit=dev`), so it is not present in the container. The install was
correct; the **classification** was wrong.

**Fix A — move it to `dependencies` (correct):**

```bash
npm uninstall helmet          # removes it from devDependencies
npm install helmet            # adds it to dependencies
npm ci --omit=dev             # now works
```

**Fix B — stop omitting dev dependencies (wrong, but it "works"):**

```dockerfile
RUN npm ci        # instead of npm ci --omit=dev
```

**Why A is correct:** `helmet` is imported at runtime — its presence is a *functional
requirement* of the application, not a convenience for developers. Installing dev dependencies
in production would ship your linter, test framework and their transitive trees into the
running container: larger images, slower deploys, and a bigger attack surface (a vulnerability
in a dev-only tool would suddenly affect production).

**The generalisation:**

| Question | Answer |
| --- | --- |
| Is it imported by code that runs in production? | → `dependencies` |
| Is it used only while developing, testing, linting, building? | → `devDependencies` |
| Does it need to be present for a *build step* but not at runtime? | → `devDependencies`, and do the build in a separate Docker stage |

To catch this class of bug early, add a CI step that installs exactly what production installs
and then starts the app:

```bash
npm ci --omit=dev
node -e "import('./src/app.js').then(() => console.log('app module loads'))"
```

If the module graph has a missing dependency, that command fails in CI instead of in
production.

</details>

---

## What's next

You have your library of packages. Now let's use Node's own — starting with the file system,
the module every backend developer reaches for when they need persistence, config, logs or
uploads.

→ [06 — The fs Module](06-filesystem.md)
