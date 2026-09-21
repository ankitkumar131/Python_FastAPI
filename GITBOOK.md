# Publishing the Cognivolt Docs learning dashboard

## What readers see

```text
Cognivolt Docs
└── Dashboard
    ├── Python_FastAPI Notes → original FastAPI course (25 pages)
    ├── Node_Express Notes → course overview and 47 imported chapters
    ├── Understanding_React Notes → overview, 139 chapters and 10 reference pages
    ├── DSA-in-java Notes → overview and 85 course/practical/reference pages
    └── Springboot Notes → overview and 101 course/practical/reference pages
```

The landing page uses GitBook's documented card-table format, plus ordinary quick
links for Markdown readers. All five cards open **notes inside the same GitBook site**,
not GitHub source pages. The sidebar groups each course's chapters under its own
overview. The FastAPI overview remains at `notes/00-course-guide.md`; its contents
have not moved. The new homepage is `notes/README.md`.

There are **455 navigation pages**:

| Content | Pages |
|---|---:|
| Dashboard | 1 |
| Original FastAPI course | 25 |
| Imported course overviews (Node, React, DSA, Spring Boot) | 4 |
| Node/Express imported pages | 47 |
| React imported pages | 149 |
| DSA in Java imported pages | 85 |
| Spring Boot imported pages | 101 |
| Generated folder indexes (3 Node + 20 React + 16 DSA + 4 Spring Boot) | 43 |
| **Total** | **455** |

Folder indexes are navigation pages, not extra lessons. Source directory README
pages are reused as folder landing pages and counted only once among imported pages.
The three existing courses were not refreshed while adding DSA and Spring Boot;
their chapters, manifests and indexes remain byte-for-byte unchanged. GitBook's own
re-export of the same space — 454 lower-cased, folder-nested copies of pages that are
already published here — was removed when the dashboard was reconciled; see
[Dashboard cards for DSA and Spring Boot](#dashboard-cards-for-dsa-and-spring-boot).
Every chapter is now published exactly once.

Node/Express retains its 29 previously recorded unavailable references. React's
existing copy retains one directory-only unavailable reference; all five forms
chapters are already present. The newer importer now resolves directory links to
selected/generated README pages on refresh, so that React reference can resolve
on a future refresh without changing the original source.

## Directory structure is preserved in navigation

The sidebar now mirrors each imported course's selected source directory tree,
not a flat list with a repeated prefix. GitBook reads the nested links in
`notes/SUMMARY.md`; keeping folders on disk alone does not override that file.

```text
Understanding_React Notes
└── react-notes
    ├── 01-prerequisites
    │   ├── 01 — HTML Basics …
    │   ├── 02 — CSS Basics …
    │   └── …
    ├── 02-typescript
    │   ├── 01 — Introduction to TypeScript
    │   └── …
    ├── 03-react-fundamentals
    ├── … (remaining numbered source folders, through 18-interview)
    ├── cheatsheets
    └── Common Errors — Decoded, Debugged, Fixed
```

- Folder names are literal source directory names by default, including the
  `react-notes` wrapper and numeric prefixes. Entries use sorted source path order.
- Each folder is a real parent page with its children nested beneath it. The tool
  generates a small marked `README.md` inside that folder, listing its direct children.
- If a directory `README.md` is already selected as a source file, it is reused
  as the parent page and not listed twice. The navigation generator leaves its
  published content untouched; documented link adaptations still apply during import. The course-root README remains
  reserved for the generated course overview.
- All imported lesson paths, lesson contents and source manifests are unchanged by
  this navigation update. Generated indexes are separate from source-file hashes.
- Node/Express uses the same folder-aware layout. FastAPI's flat numbered source
  chapters remain flat under their course overview.
- Only folders containing selected Markdown pages appear. Excluded application
  files, empty folders and other source material are not automatically published.
- Optional `group_titles` overrides use **full source-relative folder paths**, such
  as `react-notes/02-typescript`. They only rename labels, never flatten or reorder
  the tree. The active registry omits overrides to show your actual folder names.

Regenerate this structure offline with `python -X utf8 tools/sync_gitbook.py`.
Use `--refresh` when upstream source files have changed. Both commands regenerate
folder indexes and remove obsolete indexes bearing the tool's marker. They do not
remove unrelated local README files; generation refuses to overwrite an unmanaged
folder README. Do not manually maintain generated indexes or the sidebar in GitBook.

After Git Sync imports this update, expand the parent pages in GitBook's preview.
Check important public URLs and any redirects: GitBook can derive URLs from page
hierarchy, so unchanged source file paths do not guarantee unchanged hosted URLs.
The hosted UI, expansion state and public redirects have not been verified here.

## DSA in Java and Spring Boot: imported content

Both requested source branches are published with their actual folder names and
nesting. No display-label overrides flatten or rename those folders.

```text
DSA-in-java Notes
├── DSA-Java-30-Days
│   ├── 00-Roadmap
│   ├── 01-Java-Foundations
│   ├── … (remaining numbered source sections)
│   ├── 12-Cheat-Sheets
│   ├── 13-Patterns
│   ├── 14-Question-Bank
│   └── Progress Tracker
├── Course Index
└── practical
    ├── day-01
    └── … through day-30

Springboot Notes
└── java-springboot-backend
    ├── 00-roadmap
    ├── cheatsheets
    ├── day-01-java-for-springboot
    ├── … through day-30-final-capstone
    ├── interview
    ├── practical
    │   ├── day-01
    │   └── … through day-30 (including additional Markdown notes)
    └── projects
        ├── final-project
        └── project-01-crud-api … project-05-postgresql-employee-api
```

The trees abbreviate entries for readability; the actual sidebar includes every
selected file exactly once. Existing source READMEs are imported as content, not
replaced with generated lesson summaries. Navigation reuses their publication copies.

### Selection rules

- **DSA:** `DSA-Java-30-Days/*.md`, `practical/*/*.md`, and root `INDEX.md`.
  Python's `fnmatch` lets `*` match slashes, so the first pattern selects nested
  course files too. This imports 54 course/reference Markdown files, 30 practical
  READMEs and the root course index: **85 source pages**.
- **Spring Boot:** `java-springboot-backend/*.md`, including nested Markdown files:
  **101 source pages** covering all 30 days, roadmaps, cheatsheets, interviews,
  practical guides and project documentation.
- Both repositories' root `30-Day … Course.md` files are authoring requirements,
  not lessons, and are excluded. DSA's root README is replaced by the generated
  publication overview; its nested course README is included.
- Java source, Maven configuration, database scripts, environment files and other
  non-Markdown assets remain in the original repositories. No Java/Maven/Docker
  commands from the source were executed during this documentation import.

### Folder links and remaining unavailable references

GitHub permits `[Lab](practical/day-01)`. The importer now publishes that as
`[Lab](practical/day-01/README.md)` when a selected or generated landing page exists.
Trailing slashes, query strings and anchors are handled; inline/fenced code examples
are left unchanged. This is a publication-link adaptation, recorded in file hashes,
not an edit to the source repository.

Spring Boot has **zero unavailable references** in this publication. DSA has **31**:
30 links in `INDEX.md` point to excluded runnable `src/day-XX` directories, and one
points to an absent `DSA-Java-30-Days/PROGRESS.md`. They are marked unavailable instead
of leaving broken local links. The actual `progress-tracker.md` is imported and
accessible from the sidebar. Use the source-repository link for runnable Java files.

## Dashboard source repository links

The dashboard's **Source repositories** table links all five courses to their
GitHub repositories and configured study branches. These external links are
separate from the local GitBook course-card destinations. The generator reads the links from `gitbook-sources.json`; the local course now declares
its own `repository` and `branch`, just like the imported sources.

## Dashboard cards for DSA and Spring Boot

A card exists for every configured course, because the dashboard is generated from
`gitbook-sources.json` rather than hand-maintained. Two repository problems still kept the
**DSA-in-java** and **Springboot** cards from appearing under *Choose your learning path*:

1. **GitBook's re-export shadowed every published page.** After the five-course import,
   GitBook wrote the space back into this repository in its own serialization: lower-cased,
   folder-nested paths, where a page with children becomes `<page>/README.md`. The imported
   `courses/dsa-in-java/DSA-Java-30-Days/...` reappeared as `dsa-in-java/dsa-java-30-days/...`,
   the other courses reappeared the same way, and the local course reappeared as
   `notes/00-course-guide/` beside `notes/00-course-guide.md`. 454 such copies were tracked,
   and the exported dashboard pointed its card targets at them (`href="dsa-in-java/"`).
2. **A card is only rendered when its target resolves to a page.** While both layouts exist,
   a target such as `dsa-in-java/` or `00-course-guide/` is ambiguous — the same page is
   reachable at two paths, and for the FastAPI course a file page and a folder page compete
   for one path. Cards whose target cannot be resolved are dropped from the card view, which
   is why exactly the two newest courses disappeared from *Choose your learning path*.

### What was changed in this repository

| Change | Effect |
|---|---|
| Removed 454 GitBook re-exported copies | One published page per chapter; no competing page paths |
| Regenerated `notes/README.md` | Five cards, each targeting a real page: `00-course-guide.md`, `courses/node-express/README.md`, `courses/understanding-react/README.md`, `courses/dsa-in-java/README.md`, `courses/springboot/README.md` |
| Regenerated `notes/SUMMARY.md` | The sidebar lists all five courses with their nested chapters (455 unique pages) |
| Added `--prune-reexport` and stricter `--check` | Unmanaged pages and colliding page paths are detected instead of silently published |

Every file `--prune-reexport` removed already had a published counterpart with the same
GitBook page path (case-folded, `README` folded into its folder). A page that exists only in
GitBook is never deleted: the command lists it and stops. The imported source revisions were
not touched — DSA-in-java `150cce7` on `arena/01a0bf70-dsa-in-java` (85 published pages) and
Springboot `1cc8be4` on `arena/01a0bfa7-springboot` (101 published pages) are the current
branch tips, so no re-import was needed.

### Make the cards appear in the hosted space

A repository change cannot click Publish, and GitBook only shows content it has imported:

1. Push/merge the publishing branch so the GitBook-connected branch contains this commit.
   Use the branch configured in Git Sync — if Git Sync follows `arena/01a0b045-python-fastapi`,
   merge `arena/01a0c351-python-fastapi` into it (or select the new branch), then let Git Sync
   import the revision.
2. Confirm the sync direction. If the connection is set to **GitBook → GitHub** only, GitBook
   never receives repository changes: switch it to GitHub → GitBook (or bidirectional), or add
   the two missing cards in the GitBook editor instead.
3. Open **Cognivolt Docs** → **Git Sync** and verify repository, branch and project directory
   `notes/`.
4. Open the Dashboard in the preview, confirm **five** cards under *Choose your learning path*,
   then click **DSA-in-java Notes** and **Springboot Notes** and check their sidebar groups
   (`DSA-Java-30-Days`, `practical`, `INDEX`; `java-springboot-backend`, `cheatsheets`,
   `projects`).
5. Publish/merge the imported change if the site workflow stages change requests.

If only three cards still appear after the import, the space is serving an older revision:
re-check the synced commit, then the configured branch, before editing the cards by hand.

## GitBook settings: keep the existing connection

| Setting | Value |
|---|---|
| Repository | `ankitkumar131/Python_FastAPI` |
| Branch | the branch Git Sync follows; `arena/01a0b045-python-fastapi` when the space was connected, `arena/01a0c351-python-fastapi` for the reconciled dashboard |
| Project directory | `notes/` |
| Initial direction, if setting up again | **GitHub → GitBook** |
| Space mapping | `./` (relative to the `notes/` project directory) |

The branch in that table must be the branch that contains this commit. If Git Sync follows
an older publishing branch, merge this one into it or point Git Sync at this branch; the
dashboard, sidebar and one-page-per-chapter layout described above only reach the space
through the branch GitBook imports.

`notes/gitbook-docs.yaml` retains the original `python-fastapi` **key and path**.
Only the display title becomes **Learning library**. Do not rename the key merely
to match the new display name: GitBook uses it as persistent identity, and changing
it can replace the space and break links.

`notes/.gitbook.yaml` selects `README.md` as the entry page and `SUMMARY.md` as the
sidebar. After the push, let Git Sync import the revision, preview the dashboard,
click all five course cards and publish/merge the change as required by your GitBook
site workflow. This repository cannot authenticate or click Publish on your behalf.
If the old homepage remains, check the selected branch and last synced commit first.

## How the source repositories are published (important)

Node/Express source remains here:

- Repository: <https://github.com/ankitkumar131/Node_Express>
- Branch: `arena/01a0b31e-node-express`
- Initial imported commit: `1dbb069c54d4c5cfe63503118494afb532fab240`

React source remains here:

- Repository: <https://github.com/ankitkumar131/Understanding_React>
- Branch: `arena/01a0b8da-understanding-react`
- Imported commit: `bcc0871cf916fb19731e198f82dcf28daac209b9`
- Full walkthrough: [HOW-to-Upload.md](HOW-to-Upload.md)

DSA-in-java Notes source remains here:

- Repository: <https://github.com/ankitkumar131/DSA-in-java>
- Branch: `arena/01a0bf70-dsa-in-java`
- Imported commit: `150cce769a5671e37788a9dbb0a87e7112a41258`
- Publication overview: [Open DSA-in-java Notes](notes/courses/dsa-in-java/README.md)

Springboot Notes source remains here:

- Repository: <https://github.com/ankitkumar131/Springboot>
- Branch: `arena/01a0bfa7-springboot`
- Imported commit: `1cc8be4a573637619a9af4d640ea470e04888a40`
- Publication overview: [Open Springboot Notes](notes/courses/springboot/README.md)

This site contains a **revision-tracked publication copy**, not a second live
GitBook Git Sync connection. Updating a source repository alone does **not** update
this GitBook site. Refresh the copy and push this repository as described below.
Neither the source repository nor its branch is modified by the importer.

This deliberately uses one existing GitBook space so course links work immediately
as relative Markdown links. There are no guessed space IDs, broken placeholder
URLs, new GitBook account permissions or Git submodules to configure. The earlier
multi-space proposal remains an alternative, not the implementation now installed.

For independent two-way synchronization from separate repositories, create one
GitBook space per repository and connect each using Space Git Sync in GitBook's UI.
A separate dashboard space then needs real cross-space destination URLs/IDs. That
setup cannot be represented by pretending a GitHub URL is `content.directory` in
this repository's site configuration.

## Source registry and provenance

`gitbook-sources.json` defines the local course plus additional repositories. For
each source the importer reads only matching Markdown chapter/reference files. It does not
execute Java, Maven builds, JavaScript, npm scripts, shell commands or instructions found in the source.
The original root README is replaced in the publication copy by an honest index of
files actually available; executable project files stay in the source repository.

Each course's `notes/courses/<id>/source.json` records the immutable source commit, branch,
original and published SHA-256 hashes, and references to unavailable chapters.
Those missing links are rendered as explanatory text instead of broken links.
Fenced code examples and inline code are not rewritten. Future refreshes restore a
real link automatically if the referenced chapter has become available.

Do not edit generated imported chapters directly in GitBook or this repository.
Edit the original source repository, then refresh. The importer refuses to
silently overwrite imported files whose published hashes have changed locally.
Generated overviews, dashboard and sidebar are rebuilt from the registry; customize
the registry/rendering code rather than manually editing these generated files.
The original FastAPI chapter files are not regenerated by this tool.

## Refresh imported courses after source changes

Requirements: Python 3.11+ and the GitHub CLI (`gh`) with repository read access.
No additional Python packages are needed for the importer or its offline tests.
Run from this repository root:

```bash
python tools/sync_gitbook.py --refresh
python tools/sync_gitbook.py --check
python tools/check_course.py
python -m unittest discover -s tests -p 'test_gitbook_sync.py' -v
git diff --stat
git status --short
```

1. `--refresh` refreshes **all four imported courses**. For each it resolves the configured branch to a commit, downloads that exact
   archive through `gh`, imports the selected existing files and regenerates
   dashboard/navigation. It is explicit network activity, not a background job.
2. `--check` performs read-only, offline checks of generated files, sidebar coverage,
   card/local links, imported hashes, colliding GitBook page paths and unmanaged pages
   under `notes/`. It does not claim runtime correctness of the Java, Spring Boot,
   Node/Express or React code samples or test GitBook's hosted rendering.
3. The existing checker verifies the original FastAPI course and examples.
4. The unittest command checks importer/navigation behaviour without network calls.
5. Review the diff and status, including new or removed chapters. Commit the intended
   files and push the branch Git Sync follows. GitBook then imports that branch.

To regenerate just the dashboard/overviews/sidebar without fetching any repository:

```bash
python tools/sync_gitbook.py
```

If `--check` reports unmanaged pages under `notes/`, GitBook has written its own
re-serialized copy of the space back into this repository (lower-cased, folder-nested
paths). Review that list, then remove the copies whose pages are already published here:

```bash
python tools/sync_gitbook.py --prune-reexport
python tools/sync_gitbook.py --check
```

`--prune-reexport` refuses to delete anything that has no published counterpart, so a page
that only ever existed in GitBook is reported for manual review instead of being lost.

Refreshing downloads a bounded archive, accepts only regular Markdown files with
safe paths, preserves their relative hierarchy, and removes only obsolete files
listed in the previous managed manifest after checking for local edits. Very large
archives or unexpected assets require a reviewed extension of the importer.
Currently it is a Markdown-only importer: do not assume it also mirrors local image,
PDF, or downloadable source assets. The link checker flags missing referenced assets;
add explicit safe asset support before importing a course that needs them.

## Add another repository later

Add an entry to `imports` in `gitbook-sources.json` with:

- A unique lowercase `id` such as `python-basics` (used in `notes/courses/<id>/`).
- A reader-facing `title` and `description`.
- The exact GitHub `repository` (`owner/name`) and `branch`.
- `include` patterns matching that repository's real Markdown chapters. Patterns
  use Python's `fnmatch` syntax; `*` can match slashes. Do not include setup prompts,
  unrelated administrative files or the root `README.md`/`SUMMARY.md` as chapters.
- Optional `group_titles` mapping full source-relative directory paths to display
  labels; omit it to preserve literal folder names in the nested navigation.

Run `--refresh`, review the new index and validate. Another course card and sidebar
group will be generated without requiring a new GitBook space or guessed URLs.
A registry entry is publication configuration, not permission to copy unrelated
private content: publish only repositories you own or are authorized to redistribute.

## Verification for the five-course publication

The complete Python test suite passes **56 tests**, including 38 offline dashboard/importer
tests. Both documentation checkers pass: the original 25-page FastAPI course and the
five-course, 455-page GitBook navigation. All 186 DSA/Spring Boot source hashes
and fenced code examples match the pinned source archives. Every selected page
occurs exactly once in the sidebar, and `--check` also proves that no two published pages
share a GitBook page path and that no unmanaged page shadows the publication. Existing
courses and their manifests are byte-for-byte unchanged; all publication hashes and
local/card links validate. Tests cover deep nesting, folder ordering, reused source READMEs,
safe stale-index cleanup, unmanaged-file protection, encoded paths, directory-link
resolution, card targets that really exist, and the re-export prune that refuses to delete a
page with no published counterpart. The existing upstream Starlette/AnyIO deprecation
warning remains unrelated to the dashboard.

Run it with the pinned runtime packages installed:

```bash
pip install -r requirements.txt
python -m pytest tests -q
```


Hosted GitBook rendering/publishing was not executed from this session. After Git
Sync imports the publishing commit, verify all five cards and representative pages
from both new courses in the hosted preview, then publish/merge as required by the
site workflow.
The source repositories, their runnable projects and the stable GitBook YAML
configuration are unchanged. Imported upstream whitespace is preserved intentionally;
newly authored tooling/configuration pass `git diff --check`. Whitespace present in
imported source files is retained to preserve their code examples exactly. The full
staged whitespace check reports 38 upstream whitespace warnings across 35 imported
files (including terminal blank lines and Markdown hard breaks); authored files and
generated indexes pass the check.

## References

- [GitBook card blocks and target links](https://gitbook.com/docs/create-content/blocks/cards)
- [Content configuration and stable space keys](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration)
- [Individual space Git Sync for separate repositories](https://gitbook.com/docs/docs-as-code/git-sync/monorepos#use-individual-space-git-sync)
