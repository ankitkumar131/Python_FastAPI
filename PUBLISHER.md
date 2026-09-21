# The publisher app: a form for adding a course to the GitBook library

`publisher/` is a small FastAPI app that turns one form into a published GitBook course. Give it
a repository, a branch, the notes directory inside that repository, a name and a description;
press **Push to GitBook** and it imports the Markdown, regenerates the dashboard and sidebar,
validates everything, commits and pushes to the branch GitBook reads.

It is the same pipeline documented in [GITBOOK.md](GITBOOK.md), with a user interface instead of
a JSON file and a shell history. `tools/sync_gitbook.py` remains the only code that reads or
writes imported chapters; the app drives it.

```text
Cognivolt Docs — publisher
┌──────────────────────────────────────────────┬────────────────────────────────────────┐
│ Add or update a course                       │ Source check                           │
│  Course name, Description                    │  revision: 150cce7  chapters: 54       │
│  Repository  https://github.com/…/DSA-in-java│  unavailable links: 0                  │
│  Source branch  arena/01a0bf70-dsa-in-java    │  ┌──────────────────────────────────┐  │
│  Notes directory  DSA-Java-30-Days            │  │ 00-Roadmap/roadmap.md → /…/roadmap│  │
│  [ Check source ]  [ Push to GitBook ]        │  └──────────────────────────────────┘  │
├──────────────────────────────────────────────┤ Run log                                │
│ Library  (5 courses, pages, commits, Remove)  │  Imported 54 chapter(s) from 150cce7   │
│  [ Publish library ]                          │  Pushed 4f2a1c9 to origin/arena/…       │
└──────────────────────────────────────────────┴────────────────────────────────────────┘
```

## Run it

From the repository root, with `gh` authenticated and the runtime packages installed:

```bash
pip install -r requirements.txt          # FastAPI, uvicorn, and the app's dependencies
python -m publisher.app                  # http://127.0.0.1:8765
```

On a shared or hosted machine, serve it on a network interface **with a token**. The app
generates one when the host is not loopback and prints it at startup:

```bash
python -m publisher.app --host 0.0.0.0 --port 8765 --token "pick-something-long"
```

| Flag / variable | Meaning |
|---|---|
| `--host` / `PUBLISHER_HOST` | Interface to bind (default `127.0.0.1`) |
| `--port` / `PUBLISHER_PORT` | Port (default `8765`) |
| `--token` / `PUBLISHER_TOKEN` | Shared secret required for **Check source**, **Push to GitBook**, **Publish library** and **Remove** |

Without a token the app is read-mostly: `/api/state` and the page load, but anything that can
change the repository answers `401`.

## The form

| Field | Meaning |
|---|---|
| **Course name** | Reader-facing title, used in the dashboard card and the sidebar |
| **Description** | One or two sentences, shown under the card title |
| **Repository** | `https://github.com/owner/repo`, `git@github.com:owner/repo.git` or bare `owner/repo` |
| **Source branch** | The branch in the **source** repository (`main`, `arena/01a0bf70-dsa-in-java`, …) |
| **Notes directory** | Directory inside the source repository that holds the Markdown, e.g. `DSA-Java-30-Days`. Blank imports every Markdown file in the repository |
| **Course ID** | URL slug for `notes/courses/<id>/`. Derived from the name when left blank; must be lowercase with single hyphens |
| **Publishing branch** | Branch in **this** repository that GitBook reads. Defaults to the currently checked-out branch |
| **Include patterns** (advanced) | One glob per line, replacing the patterns derived from the notes directory (for example `practical/*/*.md`) |
| **Folder labels** (advanced) | JSON object mapping source-relative directories to sidebar labels, for example `{"DSA-Java-30-Days": "30-Day Course"}` |
| **Commit message** | Overrides the generated message |
| **dry run** | Runs the whole pipeline with the source check but writes, commits and pushes nothing |

## The buttons

| Button | What it does |
|---|---|
| **Check source** | Read-only. Resolves the branch to an immutable commit with `gh`, downloads that revision, and lists every chapter with the GitBook page path it would get, the unavailable external links, and any warnings. Nothing is written. |
| **Push to GitBook** | The full pipeline: remove GitBook's re-exported copies, import the course at the resolved commit, regenerate the dashboard and sidebar, validate, write `gitbook-sources.json`, commit and push. |
| **Publish library** | Same pipeline without importing anything — use it after removing a course or editing the registry. |
| **Remove** | Drops a course from the registry and from `notes/courses/<id>/`, regenerates navigation, and stops. Nothing is pushed until you press **Publish library**. |

**Push to GitBook**, in order:

1. Validate the form and check the source (as **Check source** does).
2. Remove pages GitBook re-exported into `notes/` (`--prune-reexport`), which is what keeps one
   page per chapter and keeps card targets unambiguous.
3. Import the selected Markdown at the resolved commit and write
   `notes/courses/<id>/source.json` with the source and published hashes.
4. Add or update the entry in `gitbook-sources.json` and regenerate `notes/README.md`,
   `notes/SUMMARY.md` and the generated folder indexes.
5. Run the strict check: stale generated files, unmanaged pages, colliding page paths, sidebar
   coverage, local and card links, imported hashes.
6. Stage only `notes/` and `gitbook-sources.json`, commit, and `git push origin
   HEAD:refs/heads/<publishing branch>`.

## Safety guarantees

* **No force push, ever.** If the remote moved (for example GitBook exported to the same branch),
  the push fails and the log shows the real git error; nothing is rewritten.
* **Nothing is committed before validation passes.** A failed check leaves the working tree
  changed but uncommitted, so you can inspect or discard it.
* **Only the publication is staged.** `git add -A -- notes gitbook-sources.json`, so unrelated
  local edits are never swept into a publication commit.
* **Deletion is conservative.** `--prune-reexport` removes a page only when the same GitBook page
  path is already published here; a page that exists only in GitBook is reported and kept.
* **Source repositories are read-only.** The app downloads a tarball through `gh api` and never
  writes to, or fetches branches into, the source repository.
* **A dry run is available** and writes nothing at all — not even `gitbook-sources.json`.
* **One publication at a time.** A second job while one is running is refused rather than racing
  on the same index.

## After a push: GitBook still has to read the branch

Pushing only updates GitHub. The cards appear in the hosted space when the space's Git Sync
direction includes **GitHub → GitBook** — a GitBook → GitHub connection writes GitBook's export
into the repository instead and silently overwrites the dashboard. See
[dashboard cards for DSA and Spring Boot](GITBOOK.md#dashboard-cards-for-dsa-and-spring-boot)
for the evidence and the exact setting.

## Relationship to the command line

| Task | App | Command line |
|---|---|---|
| Import one course and publish | **Push to GitBook** | `python tools/sync_gitbook.py --refresh --only <id>` then commit and push |
| Refresh every configured course | **Publish library** after a CLI refresh | `python tools/sync_gitbook.py --refresh` |
| Regenerate dashboard/sidebar only | **Publish library** | `python tools/sync_gitbook.py` |
| Validate | automatic before every push | `python tools/sync_gitbook.py --check` |
| Remove GitBook's export | automatic before every import | `python tools/sync_gitbook.py --prune-reexport` |

## Checks

```bash
python -m pytest tests -q                      # 78 tests, including 20 for the publisher
python -m pytest tests/test_publisher.py -q    # form validation, preview, dry run, HTTP surface
```

The publisher tests never touch the network: they build their own source archive and patch the
two functions that would call GitHub.

## Troubleshooting

| Symptom | Cause / what to do |
|---|---|
| `The GitHub CLI (gh) is not installed or not on PATH` | Install `gh`; the source check runs `gh api` |
| `gh api … failed: HTTP 404` | Wrong repository or branch, or `gh` has no access to it. Check `gh auth status` |
| `No Markdown chapters matched …` | The notes directory is wrong, the branch has no `.md` files there, or the extension differs. Try a blank notes directory to test the whole repository |
| `401 Missing or wrong publisher token` | Paste the token printed at startup into the token box in the header (it is stored in your browser only) |
| `Refusing to delete unmanaged pages with no published counterpart` | Search the log for the listed paths. GitBook created them; they are kept deliberately. Decide whether to publish them or delete them by hand |
| `Two published pages share one GitBook page path` | One chapter and one folder README resolve to the same page (`day-01.md` and `day-01/README.md`). Rename one in the source repository |
| Push rejected as non-fast-forward | The remote branch contains commits you do not have (often GitBook's export). Fetch/reconcile, then press **Publish library** again — the app never force-pushes |
| Push succeeds but GitBook is unchanged | The space's sync direction. See the section above |
