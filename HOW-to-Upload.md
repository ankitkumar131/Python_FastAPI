# How to upload Understanding_React to your GitBook dashboard

**A complete worked guide for your actual repositories, starting on a new PC.**

Verified against the repository contents and publishing tool on **20 September 2026**.

> This file is a publishing guide, not a React lesson. It belongs at the root of
> `Python_FastAPI`, alongside `gitbook-sources.json`. It is not automatically added
> as a page in the GitBook course sidebar.
>
> **Implementation update:** React is now imported into this publishing repository: **149
> selected pages** (139 chapters, 9 cheatsheets and one common-errors page), with **455
> total navigation pages** (including 43 generated folder indexes) across five courses.
> DSA in Java and Spring Boot are now included too; see [GITBOOK.md](GITBOOK.md).
> The registry corrections below are already applied. Pull the publishing branch on a new PC; use this guide to understand
> the configuration and refresh future updates. GitBook account-side sync, preview and
> publication still need verification; a repository import is not hosted-site confirmation.

> **Later GitBook export:** the current dashboard/sidebar were reorganized by
> GitBook after the five-course import. This guide describes the generator
> configuration; do not run a full regeneration just to add repository links.
> See [the export compatibility note](GITBOOK.md#dashboard-source-repository-links)
> before replacing the current exported navigation.

## Contents

1. [The exact result you are building](#1-the-exact-result-you-are-building)
2. [Understand the two repositories and branches](#2-understand-the-two-repositories-and-branches)
3. [What actually exists in Understanding_React](#3-what-actually-exists-in-understanding_react)
4. [Prepare a new PC](#4-prepare-a-new-pc)
5. [Clone the correct publishing branch](#5-clone-the-correct-publishing-branch)
6. [Exactly which files change](#6-exactly-which-files-change)
7. [Edit gitbook-sources.json: complete replacement](#7-edit-gitbook-sourcesjson-complete-replacement)
8. [Keep the GitBook configuration unchanged](#8-keep-the-gitbook-configuration-unchanged)
9. [Generate the React course and dashboard](#9-generate-the-react-course-and-dashboard)
10. [Inspect the generated files](#10-inspect-the-generated-files)
11. [Validate before uploading](#11-validate-before-uploading)
12. [Commit and push to GitHub](#12-commit-and-push-to-github)
13. [Finish in GitBook](#13-finish-in-gitbook)
14. [Refresh React notes in the future](#14-refresh-react-notes-in-the-future)
15. [Troubleshooting](#15-troubleshooting)
16. [Importer compatibility fix for this React repository](#16-importer-compatibility-fix-for-this-react-repository)
17. [Final checklist and command reference](#17-final-checklist-and-command-reference)

---

## 1. The exact result you are building

Your GitBook homepage contains five course cards:

```text
Cognivolt Docs
└── Dashboard
    ├── Python_FastAPI Notes
    ├── Node_Express Notes
    ├── Understanding_React Notes
    │   └── React + TypeScript lessons and reference pages
    ├── DSA-in-java Notes
    └── Springboot Notes
```

Clicking **Understanding_React Notes** opens its overview **inside GitBook**.
Readers then select its chapters from the sidebar. Clicking a course card does not
send the reader to GitHub; source-repository links are provided separately for
people who want the original files.

You are **not** deploying a running React website, a Node server or a FastAPI API.
You are publishing Markdown documentation. There is no `npm install`, `npm run
build`, Uvicorn command or Docker build required for this workflow.

### Important: these are publication copies

The installed dashboard uses **one GitBook space backed by one publishing
repository**. Additional repositories are imported as revision-tracked copies.
It does not automatically establish independent live GitBook connections to them.

```text
Understanding_React source repository
  branch: arena/01a0b8da-understanding-react
             │
             │ Run the importer from Python_FastAPI
             ▼
Python_FastAPI publishing repository
  branch: arena/01a0b045-python-fastapi
  generated content: notes/courses/understanding-react/
             │
             │ Commit and push
             ▼
GitBook imports the publishing branch
             │
             ▼
Dashboard card + React overview + React chapters
```

Updating the source React repository alone does **not** refresh its GitBook copy.
You must run the importer and push the publishing repository afterwards.

## 2. Understand the two repositories and branches

| Role | Repository | Branch | What you do here |
|---|---|---|---|
| Publishing/dashboard repository | `ankitkumar131/Python_FastAPI` | `arena/01a0b045-python-fastapi` | Clone this repository; edit the registry; run import/checks; commit/push generated content |
| React source repository | `ankitkumar131/Understanding_React` | `arena/01a0b8da-understanding-react` | The importer reads these notes; no source changes are required to publish them |

Repository links:

- [Publishing branch](https://github.com/ankitkumar131/Python_FastAPI/tree/arena/01a0b045-python-fastapi)
- [React source branch](https://github.com/ankitkumar131/Understanding_React/tree/arena/01a0b8da-understanding-react)

**Do not mix up the branches.** The React branch belongs in its source registry
entry. The FastAPI branch is the branch you push and GitBook watches.

There is no need to clone `Understanding_React` onto the new PC just to publish its
notes. The importer uses GitHub CLI to download the specified source revision.

### Your React registry entry already exists on GitHub

At inspection, publishing commit `46b3e3e` had already added a React entry, but it
needed three corrections. They are now applied; the table documents the old mistakes:

| Existing value | Problem | Correct value |
|---|---|---|
| `"id": "Understanding_react"` | The importer permits lowercase letters, digits and hyphens only; uppercase/underscore fail validation | `"id": "understanding-react"` |
| `"include": ["[0-9][0-9]-*/*.md", ...]` | This looks for numbered folders at repository root, but React's folders are inside `react-notes/` | `"include": ["react-notes/[0-9][0-9]-*/*.md"]` |
| Group keys such as `"01-prerequisites"` | Nested label overrides need the full source-relative folder path | Omit `group_titles` for literal folder names, or use a key such as `"react-notes/01-prerequisites"` |

**On an older checkout, replace the existing React entry; do not append a duplicate.** Section 7 supplies
the complete corrected file for the currently known five-course setup.

If you have added more courses since this guide was written, preserve their entries
and replace only the React entry. Do not erase newer configuration by blindly
pasting an older full-file example.

## 3. What actually exists in Understanding_React

The imported source commit is:

```text
bcc0871cf916fb19731e198f82dcf28daac209b9
```

The source now includes all 18 numbered course sections, nine cheatsheets, a
common-errors page, and a runnable `react-lab/` project. The publication preserves
the `react-notes/` hierarchy. The selected documentation is:

| Source directory/file | Pages verified |
|---|---:|
| `react-notes/01-prerequisites/` | 11 |
| `react-notes/02-typescript/` | 11 |
| `react-notes/03-react-fundamentals/` | 12 |
| `react-notes/04-state-and-hooks/` | 10 |
| `react-notes/05-react-concepts/` | 9 |
| `react-notes/06-routing/` | 8 |
| `react-notes/07-api-integration/` | 11 |
| `react-notes/08-forms-validation/` | 5 |
| `react-notes/09-state-management/` | 6 |
| `react-notes/10-advanced-react/` | 9 |
| `react-notes/11-modern-react/` | 8 |
| `react-notes/12-styling/` | 5 |
| `react-notes/13-testing/` | 5 |
| `react-notes/14-authentication/` | 6 |
| `react-notes/15-production/` | 8 |
| `react-notes/16-build-tools/` | 4 |
| `react-notes/17-projects/` | 7 |
| `react-notes/18-interview/` | 4 |
| `react-notes/cheatsheets/` | 9 |
| `react-notes/common-errors.md` | 1 |
| **Total selected React pages** | **149** |

The include patterns select the 139 numbered-section chapters plus the ten reference
pages. They deliberately exclude:

- `Instruction.md`: course-writing instructions, not a student lesson.
- The root README and `react-notes/README.md`: source overviews; the importer builds
  an index of the pages actually selected.
- `react-notes/react-roadmap.md`: a roadmap rather than a selected chapter.
- `react-lab/`: runnable source, environment files, assets and evidence remain in
  the original repository. No source code is executed or environment file published.

One source link targets the directory `../08-forms-validation/`, not a Markdown
page. The importer marks that link unavailable. **All five forms/validation chapters
are included** and accessible through the React overview and sidebar. No lesson is
missing because of this directory-only reference.

The first version of this guide tested an older 44-chapter revision. The branch has
since advanced. Treat the current counts and SHA as a verified baseline, not a
permanent expectation: the manifest records the revision each refresh actually imports.

## 4. Prepare a new PC

You already have Git installed and configured. You also need:

| Tool | Why it is needed |
|---|---|
| Python **3.11 or newer** | Runs the existing import and checking scripts |
| GitHub CLI, executable name **`gh`** | Reads repository metadata and downloads the source archive |
| A text editor | Edits `gitbook-sources.json`; VS Code or any plain-text editor is fine |

You do **not** need to install the FastAPI project's requirements for the publishing
commands in this guide. The importer and its isolated unittest suite use Python's
standard library. Running the full application test suite is a separate activity
that does require the project's dependencies.

### Windows

You can install Python from [python.org](https://www.python.org/downloads/) and
GitHub CLI from [cli.github.com](https://cli.github.com/). Enable Python's PATH
option in the installer when offered.

If Windows Package Manager is installed, these PowerShell commands are another
option:

```powershell
winget install --id Python.Python.3.12 --exact
winget install --id GitHub.cli --exact
```

The first installs a supported Python version. The second installs GitHub CLI.
`--id` selects the package identifier; `--exact` prevents an ambiguous name match.
Close and reopen the terminal afterwards so it sees updated PATH entries.

Check the tools:

```powershell
git --version
python --version
gh --version
```

If Python is available only as `py`, use `py -3.12` in place of `python` below.
If `python` opens the Microsoft Store or reports an older version, correct the
Python installation/PATH first.

### macOS

Install Python and GitHub CLI using their official installers, or, if Homebrew is
already installed:

```bash
brew install python gh
python3 --version
gh --version
```

Use `python3` instead of `python` in later commands if that is your interpreter's
name. Verify the reported Python version is at least 3.11.

### Linux

Use your distribution's supported Python and GitHub CLI installation instructions.
For a Debian/Ubuntu release that provides sufficiently recent packages:

```bash
sudo apt update
sudo apt install python3 gh
python3 --version
gh --version
```

`apt update` refreshes package information; `apt install` installs the requested
programs. Some older releases supply Python older than 3.11 or do not package gh;
use a supported newer Python installation and the official GitHub CLI installation
instructions in that case. Do not proceed merely because an old `python3` exists.

### Why later commands use `-X utf8`

The notes contain arrows, non-ASCII names and other Unicode text. The current
publishing script uses some text operations whose default encoding depends on the
computer. `python -X utf8 ...` enables Python's UTF-8 mode for that invocation and
avoids common Windows encoding failures without changing global settings.

On macOS/Linux the equivalent is `python3 -X utf8 ...` when using `python3`.

### Authenticate GitHub CLI

Git's configured name/email is **not** the same as authentication to GitHub.

```bash
gh auth login
```

In the prompts choose GitHub.com, HTTPS and browser-based sign-in. Complete the
sign-in using the GitHub account that can read the source and write to the publishing
repository. Then run:

```bash
gh auth setup-git
gh auth status
```

`setup-git` configures Git's authentication helper to use GitHub CLI where
appropriate. `status` checks the active login. Do not store tokens in JSON, paste
credentials into chat or commit them with the notes.

The React source is public at the time of inspection. For future private courses,
your account must have read access. Public GitBook publication also makes copied
private notes public; review that decision before importing anything sensitive.

## 5. Clone the correct publishing branch

Run these commands from a directory where you keep projects:

```bash
git clone --config core.autocrlf=false --branch arena/01a0b045-python-fastapi --single-branch https://github.com/ankitkumar131/Python_FastAPI.git
cd Python_FastAPI
git branch --show-current
git status --short
```

Line by line:

1. `git clone` creates the local checkout. `--branch` selects the existing publishing
   branch. `--single-branch` limits the initial branch history fetched.
   `--config core.autocrlf=false` stores a **local repository setting** before checkout
   so the imported publication files keep their committed line endings.
2. `cd` enters that checkout. All remaining repository commands run from here.
3. The branch command should print `arena/01a0b045-python-fastapi`.
4. On a fresh clone, status should print nothing, meaning no local changes.

### Why line endings matter

The publication manifest hashes the imported files' exact bytes. Automatic LF-to-CRLF
conversion on Windows can make an unchanged imported file appear locally edited.
The clone setting avoids that without changing your global Git configuration or
other repositories. Leave imported course files alone in editors that would
normalize their line endings.

If you already cloned this repository, do not clone into the same nonempty folder.
Enter the existing checkout, confirm the correct branch and start from a clean
working tree:

```bash
git branch --show-current
git status --short
git pull --ff-only origin arena/01a0b045-python-fastapi
```

Do not discard unrelated work to make status empty. Commit/preserve it or use a
separate clean clone. If an existing Windows clone has converted imported file line
endings, a fresh clone using the command above is simpler than destructive cleanup.
Changing `core.autocrlf` after checkout alone does not rewrite existing working files.

If a previous guide checkout lacks the link-handling fix described in section 16,
pull the latest publishing branch **before** adding React.

### Optional: confirm the React branch is readable

```bash
gh repo view ankitkumar131/Understanding_React
gh api "repos/ankitkumar131/Understanding_React/commits/arena%2F01a0b8da-understanding-react" --jq .sha
```

The first displays the repository. The second returns the current commit SHA for
the exact source branch. `%2F` encodes the slash in the branch name inside the API
path. This is a read-only check; it does not change that repository.

## 6. Exactly which files change

| File in Python_FastAPI | Your action | Purpose |
|---|---|---|
| `gitbook-sources.json` | **Manually correct the React entry** using section 7 | Declares repository, source branch, chapter selection and card metadata |
| `notes/.gitbook.yaml` | Keep unchanged; verify section 8 | Selects dashboard homepage and sidebar |
| `notes/gitbook-docs.yaml` | Keep unchanged; verify section 8 | Maps the existing GitBook space to notes/ |
| `tools/sync_gitbook.py` | Use the latest version; no React-specific manual edits needed | Imports source files and generates navigation; compatibility fix is included |
| `tests/test_gitbook_sync.py` | Use the shipped tests; no content edit needed | Tests archive handling, links and generation |
| `notes/README.md` | **Generated**; do not paste a card manually | Dashboard with five cards |
| `notes/SUMMARY.md` | **Generated**; do not handwrite the React list | Course groups and all selected chapter links |
| `notes/courses/understanding-react/README.md` | **Generated** | React overview and chapter index |
| `notes/courses/understanding-react/source.json` | **Generated** | Source commit, file hashes and unavailable-reference record |
| `notes/courses/understanding-react/react-notes/...` | **Generated** | Publication copies of the selected source chapters |
| Existing `notes/courses/node-express/...` | May be refreshed automatically | `--refresh` updates every configured import, not just React |
| `notes/courses/<course>/<source-folder>/README.md` | **Generated**, unless already selected from the source | Folder landing pages support the nested sidebar; do not edit by hand |
| Existing numbered FastAPI chapter files | No manual course changes needed | The local FastAPI course remains in place |

In short: **the only content-configuration file you manually edit is
`gitbook-sources.json`**. The other published files are produced by the importer or
already configured correctly.

Do not create `notes/courses/understanding-react/` manually with unrelated files. The
importer owns that directory and expects its generated manifest if it already exists.

## 7. Edit gitbook-sources.json: complete replacement

Open **`Python_FastAPI/gitbook-sources.json`**, not a file inside Understanding_React.
With VS Code available, run `code gitbook-sources.json`; otherwise open the file in
your editor through its Open File dialog.

For the current five-course setup, the following **complete file contents** preserve
FastAPI, Node/Express, React, DSA in Java and Spring Boot. The original incorrect
React entry has already been corrected. If you have since added other courses, retain those additional entries.

### File: `gitbook-sources.json`

```json
{
  "site_title": "Cognivolt Docs",
  "local": {
    "title": "Python_FastAPI Notes",
    "description": "Learn FastAPI from Python and HTTP fundamentals to databases, authentication, testing and deployment.",
    "entry": "00-course-guide.md",
    "chapter_glob": "[0-9][0-9]-*.md",
    "repository": "ankitkumar131/Python_FastAPI",
    "branch": "arena/01a0b045-python-fastapi"
  },
  "imports": [
    {
      "id": "node-express",
      "title": "Node_Express Notes",
      "description": "Study web fundamentals, Node.js and Express with detailed explanations, practical examples and projects.",
      "repository": "ankitkumar131/Node_Express",
      "branch": "arena/01a0b31e-node-express",
      "include": [
        "[0-9][0-9]-*/*.md",
        "cheatsheets/*.md",
        "common-errors/*.md"
      ]
    },
    {
      "id": "understanding-react",
      "title": "Understanding_React Notes",
      "description": "Learn React and TypeScript from web prerequisites through hooks, routing, APIs, testing, authentication and production projects.",
      "repository": "ankitkumar131/Understanding_React",
      "branch": "arena/01a0b8da-understanding-react",
      "include": [
        "react-notes/[0-9][0-9]-*/*.md",
        "react-notes/cheatsheets/*.md",
        "react-notes/common-errors.md"
      ]
    },
    {
      "id": "dsa-in-java",
      "title": "DSA-in-java Notes",
      "description": "Study data structures and algorithms in Java with a 30-day course, problem-solving patterns, a question bank and practical exercises.",
      "repository": "ankitkumar131/DSA-in-java",
      "branch": "arena/01a0bf70-dsa-in-java",
      "include": [
        "DSA-Java-30-Days/*.md",
        "practical/*/*.md",
        "INDEX.md"
      ]
    },
    {
      "id": "springboot",
      "title": "Springboot Notes",
      "description": "Learn Java and Spring Boot backend development through 30 days of lessons, databases, security, testing, practical exercises and projects.",
      "repository": "ankitkumar131/Springboot",
      "branch": "arena/01a0bfa7-springboot",
      "include": [
        "java-springboot-backend/*.md"
      ]
    }
  ]
}
```

### Explanation of the React entry

- **`id`** is `understanding-react`. It is the stable identifier used in the output
  path `notes/courses/understanding-react/`. It must be unique, lowercase and
  hyphen-separated. Do not later rename it casually; that would change paths.
- **`title`** is the visible card/course title. You may change display text without
  changing the id.
- **`description`** appears on the dashboard and course overview. It is ordinary
  descriptive text, not a URL or file pattern.
- **`repository`** is exactly `ankitkumar131/Understanding_React`. Do not put a full
  HTTPS URL, `.git` suffix or local filesystem path here.
- **`branch`** is exactly `arena/01a0b8da-understanding-react`. This is the **source**
  branch. It does not change the publishing repository's checked-out branch.
- **`include`** selects real chapter paths relative to the source repository root.
  `react-notes/` is therefore required; the numbered folders are not at root.
  `[0-9][0-9]` matches the two-digit part prefix, `-*` matches the rest of the folder
  path and `*.md` selects Markdown chapter files. Python's fnmatch treats `*` as
  able to match slashes, so matching deeper chapter paths are included too. The
  other two patterns include the cheatsheets and the exact common-errors page.
- **`group_titles`** is optional and omitted here to preserve literal folder names.
  Navigation automatically mirrors every selected source folder at its original
  depth, in sorted path order. To rename a folder label, use its full source-relative
  path, for example `"react-notes/02-typescript": "TypeScript"`. This changes only
  the display label; the folders still appear as nested pages in the same space.

JSON uses double quotes, has commas **between** objects, and does not support
comments or trailing commas. The Node/Express object and React object must be two
members of the same `imports` array—not two separate JSON documents.

### Validate the JSON syntax immediately

```bash
python -X utf8 -m json.tool gitbook-sources.json
```

This reads and pretty-prints valid JSON. It does not overwrite the file. If it
reports an error, correct the indicated line before continuing. Passing this check
only proves JSON syntax; the importer will still check IDs, branches and content.

## 8. Keep the GitBook configuration unchanged

You are adding a course **within the existing space**, not a new GitBook space.
Therefore the two files below require no course-specific changes.

### File: `notes/.gitbook.yaml`

```yaml
root: ./

structure:
  readme: README.md
  summary: SUMMARY.md
```

- `root: ./` means this space reads from its mapped directory.
- `structure.readme: README.md` chooses the dashboard at `notes/README.md`.
- `structure.summary: SUMMARY.md` chooses the generated sidebar.

Do not change readme to the React overview or a React source README. That would
make one course the homepage instead of the dashboard.

### File: `notes/gitbook-docs.yaml`

```yaml
$schema: https://api.gitbook.com/gitbook-docs.yaml

site:
  title: Cognivolt Docs
  structure:
    - type: space
      key: python-fastapi
      # Keep this existing key and path stable so GitBook preserves the space.
      title: Learning library
      path: python-fastapi
      default: true
      content:
        # Relative to the GitBook project directory: notes/
        directory: ./
        language: en
```

- `$schema` identifies GitBook's site-configuration contract.
- `site.title` keeps the site name **Cognivolt Docs**.
- `type: space` declares the existing single content space.
- `key: python-fastapi` is the persistent identifier already used by GitBook.
  Although the library now contains more than Python, **do not rename this key**.
- `title: Learning library` is its display name and can differ from the stable key.
- `path: python-fastapi` also remains unchanged to avoid unnecessary URL changes.
- `default: true` makes this the site's default space.
- `content.directory: ./` resolves to `notes/` because your GitBook **Project
  directory is notes/**. Setting it to `./notes` here would mistakenly target
  `notes/notes/`.
- `language: en` describes the content language.

Do not add a `repository:` property for React to this YAML. This site's Git Sync
connection is to Python_FastAPI; the Python importer, configured by
`gitbook-sources.json`, handles reading the additional source repository.

## 9. Generate the React course and dashboard

From the **Python_FastAPI repository root**, run:

```bash
python -X utf8 tools/sync_gitbook.py --refresh
```

What happens:

1. The tool reads the corrected registry.
2. It refreshes **all four source repositories**, not just React, because all are
   configured in `imports`. Review changes to every imported course before pushing.
3. For each repository it resolves the requested branch to an immutable commit SHA.
4. It downloads that exact revision through GitHub CLI, selects matching existing
   Markdown chapter files and checks archive safety limits.
5. It writes publication copies under `notes/courses/<id>/` and records hashes.
6. It marks references to unavailable/excluded chapters rather than publishing
   fictional pages. Fenced examples are not executed or rewritten.
7. It generates every course overview, folder index, dashboard and nested sidebar.
8. It validates generated content and local navigation.

No npm package installation or source code execution happens as part of the import.

### Expected baseline output

The current offline publication check reads:

```text
GitBook dashboard verified: 5 courses, 455 unique pages; local/card links and imported-file hashes valid.
```

A refresh also prints an import message for each of the four source repositories. Future commits can legitimately
change these numbers, the SHA and the number of unavailable references. Success of
the validation matters more than matching a historical count exactly.

The 455-page baseline is:

```text
1 dashboard
25 FastAPI pages
1 Node/Express overview + 47 Node/Express chapters
1 React overview + 149 React chapter/reference pages
1 DSA overview + 85 DSA course/practical/reference pages
1 Spring Boot overview + 101 course/practical/reference pages
43 folder indexes (3 Node + 20 React + 16 DSA + 4 Spring Boot)
-----------------------------------------------
455 navigation pages
```

A missing-reference message is not the same as an import failure. The existing React
copy retains one directory-only reference from the earlier importer. All five forms
chapters are already available. The updated importer resolves directory links to
folder READMEs on refresh, so that reference can resolve in the next refresh.
DSA records 31 references to excluded/absent targets; Spring Boot records none.
See GITBOOK.md for their exact selection and remaining-reference details. The CLI
calls all selected Markdown files “chapters”; React's 149 files include 139 lessons
and ten reference pages.

**If the command exits with an error, do not push the partial result.** It can have
written some files before a later check fails. Resolve the error, rerun the command
and complete section 11 first.

## 10. Inspect the generated files

The generated structure for this React selection is:

```text
Python_FastAPI/
├── gitbook-sources.json                  # Your one manual config edit
└── notes/
    ├── .gitbook.yaml                     # Unchanged
    ├── gitbook-docs.yaml                 # Unchanged
    ├── README.md                        # Regenerated five-card dashboard
    ├── SUMMARY.md                       # Regenerated combined sidebar
    └── courses/
        ├── dsa-in-java/                  # Imported Java DSA course
        ├── node-express/                 # Existing copy; may be refreshed
        ├── springboot/                   # Imported Spring Boot course
        └── understanding-react/
            ├── README.md                # Generated React overview
            ├── source.json              # Generated provenance and hashes
            └── react-notes/              # Source hierarchy is preserved
                ├── README.md            # Generated wrapper-folder index
                ├── 01-prerequisites/     # Folder README + 11 chapters
                ├── 02-typescript/        # Folder README + 11 chapters
                ├── 03-react-fundamentals/ # Folder README + 12 chapters
                ├── 04-state-and-hooks/   # 10 chapters
                ├── ...                  # Parts 05–17; see section 3 for counts
                ├── 18-interview/         # 4 chapters
                ├── cheatsheets/          # 9 reference pages
                └── common-errors.md     # 1 reference page
```

### File: `notes/README.md` — complete expected generated dashboard

The importer writes the following for the configuration in section 7. This is
provided so you can understand and recognize the result, **not as a file you need
to paste manually**. Manual dashboard edits would be replaced on regeneration.

````markdown
# Cognivolt Docs

## Choose your learning path

Pick a course below to read its notes, examples and exercises. Each course opens here in GitBook.

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>
<tr><td><strong>Python_FastAPI Notes</strong></td><td>Learn FastAPI from Python and HTTP fundamentals to databases, authentication, testing and deployment.</td><td><a href="00-course-guide.md">Open course</a></td></tr>
<tr><td><strong>Node_Express Notes</strong></td><td>Study web fundamentals, Node.js and Express with detailed explanations, practical examples and projects.</td><td><a href="courses/node-express/README.md">Open course</a></td></tr>
<tr><td><strong>Understanding_React Notes</strong></td><td>Learn React and TypeScript from web prerequisites through hooks, routing, APIs, testing, authentication and production projects.</td><td><a href="courses/understanding-react/README.md">Open course</a></td></tr>
<tr><td><strong>DSA-in-java Notes</strong></td><td>Study data structures and algorithms in Java with a 30-day course, problem-solving patterns, a question bank and practical exercises.</td><td><a href="courses/dsa-in-java/README.md">Open course</a></td></tr>
<tr><td><strong>Springboot Notes</strong></td><td>Learn Java and Spring Boot backend development through 30 days of lessons, databases, security, testing, practical exercises and projects.</td><td><a href="courses/springboot/README.md">Open course</a></td></tr>
</tbody></table>

### Quick links

- [Python_FastAPI Notes](00-course-guide.md)
- [Node_Express Notes](courses/node-express/README.md)
- [Understanding_React Notes](courses/understanding-react/README.md)
- [DSA-in-java Notes](courses/dsa-in-java/README.md)
- [Springboot Notes](courses/springboot/README.md)

### Source repositories

These links open the original GitHub repositories and their study branches. Use the course cards above to read the notes here in GitBook.

| Course | GitHub repository | Study branch |
|---|---|---|
| Python_FastAPI Notes | [ankitkumar131/Python_FastAPI](https://github.com/ankitkumar131/Python_FastAPI) | [arena/01a0b045-python-fastapi](https://github.com/ankitkumar131/Python_FastAPI/tree/arena/01a0b045-python-fastapi) |
| Node_Express Notes | [ankitkumar131/Node_Express](https://github.com/ankitkumar131/Node_Express) | [arena/01a0b31e-node-express](https://github.com/ankitkumar131/Node_Express/tree/arena/01a0b31e-node-express) |
| Understanding_React Notes | [ankitkumar131/Understanding_React](https://github.com/ankitkumar131/Understanding_React) | [arena/01a0b8da-understanding-react](https://github.com/ankitkumar131/Understanding_React/tree/arena/01a0b8da-understanding-react) |
| DSA-in-java Notes | [ankitkumar131/DSA-in-java](https://github.com/ankitkumar131/DSA-in-java) | [arena/01a0bf70-dsa-in-java](https://github.com/ankitkumar131/DSA-in-java/tree/arena/01a0bf70-dsa-in-java) |
| Springboot Notes | [ankitkumar131/Springboot](https://github.com/ankitkumar131/Springboot) | [arena/01a0bfa7-springboot](https://github.com/ankitkumar131/Springboot/tree/arena/01a0bfa7-springboot) |

### How to use this library

Start with a course overview, then follow its chapters in the sidebar. Each course stays grouped together. Choose **Dashboard** in the sidebar whenever you want to switch courses.

Python/FastAPI is maintained in this documentation repository. Other repositories are published here as attributed, revision-tracked documentation copies; their original repositories remain the source of truth.
````

`data-view="cards"` selects GitBook's card-table representation. The hidden
`data-card-target` column supplies each card's destination. React points to
`courses/understanding-react/README.md`, which is a real page in the same content
space. The ordinary quick links make the file useful in Markdown viewers too.

There are no guessed GitBook space IDs or hardcoded site domains. That is why this
same file works with your current GitBook site address or a later custom domain.

### File: `notes/SUMMARY.md` — generated navigation

The React overview is a top-level course item. Every selected source folder becomes
a parent page, with deeper folders and chapters indented beneath it. For example:

```markdown
* [Understanding_React Notes](courses/understanding-react/README.md)
  * [react-notes](courses/understanding-react/react-notes/README.md)
    * [01-prerequisites](courses/understanding-react/react-notes/01-prerequisites/README.md)
      * [01 — HTML Basics (the HTML React Actually Produces)](courses/understanding-react/react-notes/01-prerequisites/01-html-basics.md)
    * [02-typescript](courses/understanding-react/react-notes/02-typescript/README.md)
      * [01 — Introduction to TypeScript](courses/understanding-react/react-notes/02-typescript/01-typescript-introduction.md)
```

This is an **illustrative excerpt**, not the complete sidebar. Chapter titles come
from their first Markdown H1 headings. The full file retains Dashboard, FastAPI,
Node/Express, DSA, Spring Boot and every selected React chapter. Do not replace it with this excerpt.

### Generated folder indexes: `<source-folder>/README.md`

For example, `notes/courses/understanding-react/react-notes/02-typescript/README.md`
is a generated parent page listing that folder's chapters. Its header contains a
marker identifying it as generated navigation. The source lesson files and manifest
hashes are not changed to add these indexes. If a folder README is itself selected
from the source, the tool uses it unchanged rather than generating over it.

Generation rejects an unrelated local README rather than silently overwriting it.
Obsolete folder indexes are removed only when they carry the generator marker and
are not selected source files. Re-run the tool instead of editing generated pages.

The default labels retain literal directory names and the `react-notes` wrapper.
This works for future repositories and deeper folders automatically. Only selected
Markdown content appears; the runnable project and excluded source files stay out.

### File: `notes/courses/understanding-react/README.md`

The generated overview includes:

- A link back to the dashboard.
- The course title and description from the registry.
- The actual imported chapter count.
- Links to the original repository and immutable source commit.
- Links to every imported chapter.
- An explanation of publication copies and unavailable references, if any.

You do not need to manually copy the source README or write another index.

### File: `notes/courses/understanding-react/source.json`

This is a machine-generated **manifest**: a record of what was imported. It contains
`repository`, `branch`, `commit`, per-file `source_sha256`/`published_sha256`, and
`unavailable_links`. Hashes detect accidental edits to generated copies.

Do not invent hashes, change the commit to claim a newer revision, or edit this file
to bypass an integrity failure. Refresh from the original source instead.

Check the recorded commit and chapter count with this cross-platform one-line command:

```bash
python -X utf8 -c "import json; from pathlib import Path; m=json.loads(Path('notes/courses/understanding-react/source.json').read_text()); print(m['repository']); print(m['branch']); print(m['commit']); print('Chapters:', len(m['files']))"
```

Expected at the baseline: the requested repository and branch, the source SHA shown
above, and `Chapters: 149`.

### Files under `notes/courses/understanding-react/react-notes/`

These are imported chapter copies, not files to retype. Their source directory
hierarchy is preserved so relative links between selected chapters remain useful.
Open a few to verify that you imported the intended material.

If a lesson needs correction later, update it in Understanding_React through that
repository's normal editing workflow, push the source change there, then refresh
this publishing repository. Do not edit its generated copy as your primary source.

## 11. Validate before uploading

Run these commands from the publishing repository root, in this order:

```bash
python -X utf8 tools/sync_gitbook.py --check
python -X utf8 tools/check_course.py
python -X utf8 -m unittest discover -s tests -p test_gitbook_sync.py -v
```

1. `--check` validates the generated dashboard/sidebar, source hashes and local/card
   links without calling GitHub or changing files.
2. `check_course.py` confirms the original FastAPI sequence, printed examples and
   local links still work. It is not a React runtime test.
3. The unittest command runs the importer/navigation regression tests. `-s tests`
   selects the test directory, `-p` selects the file and `-v` shows individual names.
   The current importer suite has 32 tests; later versions may have more.

These commands do not run React/TypeScript examples in a browser and cannot
publish or visually preview the hosted GitBook site. That check comes after sync.

Review your changes:

```bash
git status --short
git diff --stat
git diff -- gitbook-sources.json notes/README.md notes/SUMMARY.md
```

- `status` includes new untracked files, including the new React directory.
- `diff --stat` summarizes modifications to tracked files; it does **not** include
  untracked files yet.
- The final command shows the actual registry and navigation changes.

It is normal for an importer that refreshes every source to also update Node/Express
if its selected branch advanced. Review those changes instead of assuming every
changed file must belong to React.

Do not commit `.env`, credentials, virtual environments or unrelated local files.
The existing ignore rules help, but reviewing staged changes is still necessary.

## 12. Commit and push to GitHub

Stage the configuration and generated publishing files:

```bash
git add gitbook-sources.json notes/README.md notes/SUMMARY.md notes/courses/
```

Why these paths:

- The registry change tells future refreshes to continue including React.
- The dashboard contains the new card.
- The sidebar contains the new course and chapter links.
- `notes/courses/` includes the new overview, manifest, chapter files and any
  legitimate updates to previously imported courses.

Uploading only `gitbook-sources.json` is **not enough**. GitBook does not run the
Python importer for you. Uploading just the dashboard also is not enough: the card
would point at pages that were never committed.

Review exactly what is staged:

```bash
git diff --cached --stat
git diff --cached --name-only
git diff --cached -- gitbook-sources.json notes/README.md notes/SUMMARY.md
```

`--cached` means staged changes: what the next commit will contain. Unlike the
earlier unstaged diff, this now includes newly staged React files.

Once the selection is correct:

```bash
git commit -m "Add Understanding React notes to the GitBook dashboard"
git push origin arena/01a0b045-python-fastapi
```

`commit` records the reviewed files locally. `push` uploads that commit to the
existing publishing branch on GitHub. It does **not** push to the React source
repository or to main.

Confirm:

```bash
git status --short
git log -1 --oneline
```

If all intended changes were committed, status is empty. The log shows your new
publishing commit. You can inspect the same branch in GitHub to verify that
`notes/courses/understanding-react/` is present.

If GitHub refuses the push because remote commits appeared while you were working,
do not force-push over them. Fetch/reconcile those changes, preserve any GitBook
editor changes, rerun the checks, then push normally. If GitBook edited generated
copies, resolve the source-of-truth conflict before allowing the importer to replace
them; do not blindly bypass its hash checks.

## 13. Finish in GitBook

For the existing dashboard, **keep the current connection**:

| GitBook field | Exact value |
|---|---|
| Source repository | `ankitkumar131/Python_FastAPI` |
| Branch | `arena/01a0b045-python-fastapi` |
| Project directory | `notes/` |
| Site configuration | `notes/gitbook-docs.yaml` |
| Space content directory | `./` relative to the notes/ project directory |
| Initial direction, only if connecting/reconnecting | **GitHub → GitBook** |

Do not replace this site's source repository with Understanding_React. That would
replace the central dashboard connection rather than add a course to it. Do not
create a second site or space merely to follow this single-space workflow.

### If the site is already connected

1. Open **Cognivolt Docs** in GitBook.
2. Open **Git Sync** and check that it has imported your new publishing commit.
3. If it has not updated, refresh the interface and check the sync status/error
   details. Verify the selected repository, branch and project directory before
   changing content mappings.
4. Open the site preview and its Dashboard page.
5. Confirm all five course cards exist.
6. Click Understanding_React Notes, then a prerequisites page, a TypeScript page and
   a state/hooks page.
7. Expand `react-notes` and the numbered folder pages. Verify chapters are children
   of the correct folders. Return to Dashboard and test the FastAPI and Node cards too.
   Check important public URLs/redirects; GitBook may derive URLs from page hierarchy.
8. If your GitBook workflow stages a change request or requires publication,
   merge/publish the reviewed change through the offered controls. If your existing
   configuration publishes synced changes automatically, verify the live result.

The exact final buttons can vary with your GitBook workflow. A successful Git push
proves the files reached GitHub, not that hosted GitBook rendering or publication
has already completed.

### If you are setting up the site again

Connect GitHub in GitBook's Git Sync UI, authorize the GitBook GitHub app for the
publishing repository, select the settings in the table, and review the mapping
before the initial import.

**Initial GitHub → GitBook sync replaces destination content/structure.** Do not use
it to overwrite an unrelated live site. This guide targets your existing Cognivolt
Docs dashboard, not another organization's content.

After import, follow the preview checklist above. GitHub CLI authentication on your
PC and GitBook's GitHub-app authorization are separate connections; configuring one
does not automatically authorize the other.

## 14. Refresh React notes in the future

After new chapters/corrections have been committed to the original React branch:

```bash
cd Python_FastAPI
git branch --show-current
git status --short
git pull --ff-only origin arena/01a0b045-python-fastapi
python -X utf8 tools/sync_gitbook.py --refresh
python -X utf8 tools/sync_gitbook.py --check
python -X utf8 tools/check_course.py
python -X utf8 -m unittest discover -s tests -p test_gitbook_sync.py -v
git status --short
git add notes/README.md notes/SUMMARY.md notes/courses/
git diff --cached --stat
git commit -m "Refresh imported course notes"
git push origin arena/01a0b045-python-fastapi
```

Enter the directory only if your terminal is outside it. Confirm the branch and a
clean starting state before pulling. Stop at any failed step; do not paste the
entire sequence blindly and ignore errors.

The registry does not need another React entry each time. The existing corrected
entry continues selecting the configured branch. New numbered parts under
`react-notes/` match the pattern automatically when actually present.

If you intentionally edit repository/branch/include/title settings during a refresh,
also stage `gitbook-sources.json` before committing. If nothing changed, Git reports
nothing to commit; that is not an error requiring a new empty commit.

### Three tool modes: do not confuse them

| Command | Network? | Purpose |
|---|---|---|
| `python -X utf8 tools/sync_gitbook.py --refresh` | Yes | Import source revisions and regenerate publication files |
| `python -X utf8 tools/sync_gitbook.py` | No | Regenerate overviews/dashboard/sidebar from existing imported manifests |
| `python -X utf8 tools/sync_gitbook.py --check` | No | Verify current publication files without modifying them |

For a brand-new course, running without `--refresh` cannot work until its imported
files/manifest exist. `--check` does not create missing content or refresh outdated
content for you.

### Publication limitations

The importer currently selects Markdown chapter files, not local images, PDFs,
downloadable source archives, or an application build. The verified React selection
passed its local-link checks. If future chapters add local assets, extend the
importer's asset support deliberately rather than pushing broken image references.

Imported files must remain under the tool's safety limits: individual chapters up
to 3 MB, selected Markdown content up to 25 MB, and a compressed archive up to 25 MB;
there is also an archive member-count limit. Large future courses require a reviewed
change, not quietly removing protections.

## 15. Troubleshooting

| Error or symptom | Cause / what to do |
|---|---|
| `python` or `gh` not found | Install the missing tool and reopen the terminal; check PATH and the version commands |
| Python is older than 3.11 | Install a supported interpreter and use that command consistently |
| `UnicodeDecodeError` / Unicode cannot be encoded on Windows | Use `python -X utf8 ...` as shown; save edited JSON as UTF-8 |
| GitHub returns 404 or cannot read the branch | Check repository spelling, exact source branch and `gh auth status`; verify private-repository access if applicable |
| `Course IDs must be lowercase URL slugs` | Replace `Understanding_react` with `understanding-react`; changing only title does not fix id validation |
| `No existing Markdown chapters matched...` | Correct the pattern to `react-notes/[0-9][0-9]-*/*.md`; copying the Node pattern misses the React path prefix |
| JSON parse error | Fix commas/double quotes/trailing commas; rerun `python -X utf8 -m json.tool gitbook-sources.json` |
| Duplicate React card or duplicate course ID | Replace the existing incorrect entry; do not append another entry for the same course |
| `source.json` is missing | Use `--refresh` first for a new course; do not pre-create its directory without a manifest |
| `was edited locally; preserve that edit before refreshing` | A generated chapter's bytes changed; preserve the edit and move the real correction upstream. On Windows also check automatic CRLF conversion. Do not fake the stored hash |
| Flat chapter list / missing folder hierarchy | Pull the updated importer, run `python -X utf8 tools/sync_gitbook.py`, commit the generated folder indexes and sidebar, then confirm GitBook synced that commit. Label overrides use full source-relative paths |
| Broken link to `../05-react-concepts/01-component-communication.md` | An older importer missed code-formatted Markdown labels; pull the fixed tool described in section 16, then refresh and check |
| `--check` reports stale dashboard/sidebar | Regenerate after changing titles/settings; for new source content use `--refresh`, not only regeneration |
| GitBook still displays two cards | Verify you committed generated dashboard/sidebar/course files, pushed the connected branch, and GitBook imported that commit |
| GitBook cannot find `notes/gitbook-docs.yaml` | Confirm branch and project directory are exactly as section 13; the file belongs under notes/ |
| GitBook looks for notes/notes/ | You combined project directory notes/ with content directory ./notes; content directory should remain ./ |
| New card appears but pages do not | Check that `notes/courses/understanding-react/` was staged and pushed; committing only JSON/card markup is insufficient |
| Push rejected as non-fast-forward | Preserve remote changes, reconcile history and rerun checks; do not force-push over GitBook/user commits |
| Imported source whitespace warnings | Some upstream fenced diagrams contain blank lines with spaces. Preserve source blocks intentionally; distinguish these from newly authored code errors |

A private source repository becoming readable does not mean it is safe to publish
all of its contents publicly. Always review selected files and the destination
site's visibility before committing publication copies.

## 16. Importer compatibility fix for this React repository

### Why a small fix was necessary

At the original 44-chapter inspection, the final hooks chapter used a real Markdown
link with a code-formatted label:

```markdown
[`../05-react-concepts/01-component-communication.md`](../05-react-concepts/01-component-communication.md)
```

The target did not exist at that older revision; it exists in the current import.
The older importer split prose around inline backticks before examining links. That split accidentally
broke this real link into pieces and prevented the unavailable-target replacement.
The later link checker correctly rejected the remaining broken destination.

A test import exposed the problem before this guide recommended publishing.
The repository now includes a targeted fix and three regression tests. A fresh
clone/pull of the branch containing this guide includes that fix; **you normally
should not manually edit the importer just to add React**.

### File: `tools/sync_gitbook.py` — relevant complete function

If you are comparing an older copy, locate the function beginning
`def adapt_links(path: str, text: str, available: set[str])`. The corrected function
is below. Prefer pulling the tested version rather than modifying it by hand.

The current module also uses `publication_paths()` to include generated folder
indexes when resolving links. Pull the complete tested tool, not just this function.
Its URL utility import includes:

```python
from urllib.parse import quote, unquote, urlsplit, urlunsplit
```
This is a complete **function replacement**, not the contents of the entire script.

```python
def adapt_links(path: str, text: str, available: set[str]) -> tuple[str, list[dict]]:
    """Mark absent upstream chapters as unavailable, rather than inventing pages/404 links."""
    missing = []

    def rewrite(prose):
        # Ignore links written INSIDE inline code, but still process real links
        # whose LABEL contains inline code, such as [`next.md`](next.md).
        code_spans = [(match.start(), match.end())
                      for match in re.finditer(r'`+[^`\n]*`+', prose)]

        def replace(match):
            if any(start <= match.start() < end for start, end in code_spans):
                return match[0]
            label, href = match.groups()
            target = local_target(path, href)
            if target is None or target in available:
                return match[0]
            # GitHub accepts folder links; GitBook navigation needs a Markdown page.
            if posixpath.join(target, 'README.md') in available:
                parsed = urlsplit(href)
                href = urlunsplit(parsed._replace(path=posixpath.join(parsed.path, 'README.md')))
                return f'[{label}]({href})'
            missing.append({'file': path, 'target': href})
            return f'{label} *(not available in this published source revision)*'

        return LINK.sub(replace, prose)

    return prose_map(text, rewrite), missing
```

How it works:

1. It finds inline-code spans within prose without breaking the prose apart.
2. If a Markdown link itself starts **inside** an inline-code span, it is an example
   string, so the tool leaves it alone.
3. If a link starts outside inline code, its label may contain code formatting and
   the link is still processed normally.
4. Existing selected destinations and external URLs are retained.
5. Missing destinations become explanatory text and a manifest record.
6. `prose_map` keeps fenced examples out of this transformation entirely.

### File: `tests/test_gitbook_sync.py` — regression coverage

The shipped tests verify:

- A missing destination with a code-formatted label is marked unavailable.
- An existing destination with that label style remains unchanged.
- A literal Markdown example inside inline code is not mistaken for real navigation.

Run them with the unittest command in section 11. You do not need to write or
modify a test file for each newly configured repository.

### What was actually verified for this guide

- The source repository is public, and the requested branch was read successfully.
- The configured patterns selected 139 lessons and ten reference pages at the recorded commit.
- The actual repository import produced five course groups and 455 unique sidebar pages,
  with local/card links and imported-file hashes passing validation.
- The existing React copy retains one unavailable reference; its contents were not
  refreshed while adding DSA and Spring Boot. Directory-link resolution now has
  regression coverage and is applied on future source refreshes.
- The importer regression suite passed 32 tests including nested navigation checks. The full Python test
  suite also passed **50 tests**, with the previously documented upstream
  Starlette/AnyIO deprecation warning. No dependency changes were required.
- The registry corrections, React publication copies, dashboard and sidebar are now
  applied to this publishing repository, not just an isolated rehearsal.
- Hosted GitBook rendering/publication was **not** performed by this test; your
  post-sync preview remains necessary.

## 17. Final checklist and command reference

### Before importing

- [ ] Python is 3.11+ and GitHub CLI works.
- [ ] GitHub CLI is authenticated to the correct account.
- [ ] I cloned/pulled **Python_FastAPI's publishing branch**, not its main branch.
- [ ] I preserved imported file line endings and use UTF-8 commands.
- [ ] I have the updated importer with the code-label link fix.
- [ ] I corrected the existing React object instead of duplicating it.
- [ ] `id` is `understanding-react`.
- [ ] The source repository and source branch exactly match the requested React repo.
- [ ] The include pattern starts with `react-notes/`.

### Before pushing

- [ ] Refresh completed successfully.
- [ ] Publication checks and importer tests passed.
- [ ] The React overview, manifest and chapter copies exist locally.
- [ ] The dashboard has a React card and the sidebar contains its chapters.
- [ ] I reviewed staged files, including any Node/Express refresh.
- [ ] No credentials or unrelated files are staged.

### After pushing

- [ ] I pushed `arena/01a0b045-python-fastapi`.
- [ ] GitBook imported that commit using project directory `notes/`.
- [ ] All five cards work in the preview.
- [ ] React chapter pages open and the other courses still work.
- [ ] I completed any publication step required by my GitBook workflow.

### Short command reference — after installing tools, cloning and editing JSON

Run one line at a time; stop on failure. All commands below run from the publishing
repository root.

```bash
python -X utf8 -m json.tool gitbook-sources.json
python -X utf8 tools/sync_gitbook.py --refresh
python -X utf8 tools/sync_gitbook.py --check
python -X utf8 tools/check_course.py
python -X utf8 -m unittest discover -s tests -p test_gitbook_sync.py -v
git status --short
git add gitbook-sources.json notes/README.md notes/SUMMARY.md notes/courses/
git diff --cached --stat
git diff --cached --name-only
git commit -m "Add Understanding React notes to the GitBook dashboard"
git push origin arena/01a0b045-python-fastapi
```

Then open GitBook, verify sync, preview and publish as needed.

## Related files and references

- [Existing publishing overview](GITBOOK.md)
- [Source registry to edit](gitbook-sources.json)
- [Importer](tools/sync_gitbook.py)
- [Importer tests](tests/test_gitbook_sync.py)
- [Current dashboard](notes/README.md)
- [GitBook configuration](notes/.gitbook.yaml)
- [Site configuration](notes/gitbook-docs.yaml)
- [GitBook GitHub Sync setup](https://gitbook.com/docs/docs-as-code/git-sync/enabling-github-sync)
- [GitBook content configuration](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration)

**Remember the order: correct the registry → import → validate → review → commit →
push → verify GitBook. Editing JSON alone does not publish a course.**
