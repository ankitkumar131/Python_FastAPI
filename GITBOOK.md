# Publishing the Cognivolt Docs learning dashboard

## What readers see

```text
Cognivolt Docs
└── Dashboard
    ├── Python_FastAPI Notes → original FastAPI course (25 pages)
    ├── Node_Express Notes → course overview and 47 imported chapters
    └── Understanding_React Notes → overview, 139 chapters and 10 reference pages
```

The landing page uses GitBook's documented card-table format, plus ordinary quick
links for Markdown readers. All three cards open **notes inside the same GitBook site**,
not GitHub source pages. The sidebar groups each course's chapters under its own
overview. The FastAPI overview remains at `notes/00-course-guide.md`; its contents
have not moved. The new homepage is `notes/README.md`.

There are **247 navigation pages**: one dashboard, 25 FastAPI pages, one Node/Express
overview plus 47 chapters, and one React overview plus 149 chapter/reference pages,
plus **23 generated folder indexes** (3 Node/Express and 20 React). These indexes
are navigation pages, not additional lessons copied from the source.
React includes all 18 numbered sections (139 lessons), nine cheatsheets and one
common-errors page. Its source revision is recorded in the generated manifest.

One React link points at `../08-forms-validation/` rather than a Markdown page;
it is marked unavailable instead of producing a broken navigation link. All five
forms/validation chapters are available through the course overview and sidebar.
Node/Express retains its 29 unavailable references; no fictional chapters are added.

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
  unchanged as the parent page and not listed twice. The course-root README remains
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

## GitBook settings: keep the existing connection

| Setting | Value |
|---|---|
| Repository | `ankitkumar131/Python_FastAPI` |
| Branch | `arena/01a0b045-python-fastapi` |
| Project directory | `notes/` |
| Initial direction, if setting up again | **GitHub → GitBook** |
| Space mapping | `./` (relative to the `notes/` project directory) |

`notes/gitbook-docs.yaml` retains the original `python-fastapi` **key and path**.
Only the display title becomes **Learning library**. Do not rename the key merely
to match the new display name: GitBook uses it as persistent identity, and changing
it can replace the space and break links.

`notes/.gitbook.yaml` selects `README.md` as the entry page and `SUMMARY.md` as the
sidebar. After the push, let Git Sync import the revision, preview the dashboard,
click all three course cards and publish/merge the change as required by your GitBook
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

This site contains a **revision-tracked publication copy**, not a second live
GitBook Git Sync connection. Updating either source repository alone does **not** update
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
execute JavaScript, npm scripts, shell commands or instructions found in the source.
The original root README is replaced in the publication copy by an honest index of
files actually available; executable project files stay in the source repository.

Each course's `source.json` (`notes/courses/node-express/source.json` or
`notes/courses/understanding-react/source.json`) records the immutable source commit, branch,
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

## Refresh Node/Express and React after source changes

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

1. `--refresh` resolves the configured branch to a commit, downloads that exact
   archive through `gh`, imports the selected existing files and regenerates
   dashboard/navigation. It is explicit network activity, not a background job.
2. `--check` performs read-only, offline checks of generated files, sidebar coverage,
   card/local links and imported hashes. It does not claim runtime correctness of
   the Node/Express or React code samples or test GitBook's hosted rendering.
3. The existing checker verifies the original FastAPI course and examples.
4. The unittest command checks importer/navigation behaviour without network calls.
5. Review the diff and status, including new or removed chapters. Commit the intended
   files and push **`arena/01a0b045-python-fastapi`**. GitBook then imports this branch.

To regenerate just the dashboard/overviews/sidebar without fetching any repository:

```bash
python tools/sync_gitbook.py
```

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

## Verification for this dashboard change

The complete Python test suite passes **46 tests**, including 28 offline dashboard/importer
tests. Both documentation checkers pass: the original 25-page FastAPI course and the
three-course, 247-page GitBook navigation. All imported chapter files and
source manifests are byte-for-byte unchanged by the navigation update; hashes and
local/card links validate. Tests cover deep nesting, folder ordering, reused source
READMEs, safe stale-index cleanup, unmanaged-file protection and encoded paths. The existing
upstream Starlette/AnyIO deprecation warning remains unrelated to the dashboard.

Hosted GitBook rendering/publishing was not executed from this session. After Git
Sync imports the publishing commit, verify all three cards and representative React
pages in the hosted preview, then publish/merge as required by the site workflow.
The source repositories, their runnable projects and the stable GitBook YAML
configuration are unchanged. Imported upstream whitespace is preserved intentionally;
newly authored tooling/configuration pass `git diff --check`. The new React import
retains one upstream trailing space in the fenced example at
`react-notes/04-state-and-hooks/01-state.md:97`; the full staged whitespace check
reports that line intentionally rather than silently modifying source code.

## References

- [GitBook card blocks and target links](https://gitbook.com/docs/create-content/blocks/cards)
- [Content configuration and stable space keys](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration)
- [Individual space Git Sync for separate repositories](https://gitbook.com/docs/docs-as-code/git-sync/monorepos#use-individual-space-git-sync)
