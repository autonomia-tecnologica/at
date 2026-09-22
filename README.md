# Bill

Bill is a deterministic task engine. It runs **in a folder**, and that folder
becomes its **Working Folder**. This repository is the **product to publish** —
the engine, the default declarations, the bundled infrastructure and the single
binary. It carries no personal data: no path of anyone's machine, no host, no id.

## Where the authority is

`MANIFESTO.md` is the founding stone and the only file here written by a human
directly. It is the authority on everything. This README is its **secondary
harness**: derived from it, and here so that an agent can work without
re-deriving the architecture. The code is an extension of this README.

The chain of custody is `MANIFESTO.md → README.md → code`. Two consequences:

- When this file disagrees with the Manifesto, **this file is wrong** and gets
  corrected — never the Manifesto.
- Any other LLM-memory markdown (`CLAUDE.md` and the like) is ignored for work in
  this repository where it conflicts with either.

`MANIFESTO.md` and `FAQ.md` are written in `pt_BR`; **every other markdown here
is in `en_US`** (§3). Pending work lives in `BACKLOG.md`.

## The layers

The engine is layered, and every layer has one job (§4). Nothing outside `core`
resolves a path of its own.

| Path | What it is |
|---|---|
| `bill/core/` | the rules — the Working Folder, the settings, the first run, the single writer, the table engine, the project scope |
| `bill/data/` | the tables: `data/<table>.jsonl` for the rows, `data/schema/<table>.json` for the schema, and the declarations the product ships in `defaults/` |
| `bill/prose/` | every file that is not structured data: the tree of `prose/`, what a file there IS, and the write with its revision |
| `bill/services/` | external services, as tool-agnostic as the layer can be |
| `bill/encryption/` | secrets: the master key and the `secrets` table |
| `bill/ui/cli/` | the command line — the surface that reaches everything |
| `bill/ui/wizard/` | the Control Panel, in Tkinter |
| `bill/ui/webapp/` | the WebApp: the server, the look it serves, and the Vue app |
| `bill/i18n/` | the translation blocks, packed into the product |
| `bill/tests/` | the suite — stdlib `unittest`, because a test runner is not a dependency |

## The Working Folder

The folder the binary was opened in is the binary's folder, and that folder is
the Working Folder (§3). On the first run Bill describes the folder and asks
before writing anything; `.bill/settings.json` is what makes a folder configured.

A folder is born with:

```
.bill/settings.json     the instance's key-value configuration
.bill/i18n/active       the chosen language — the catalogs travel in the product
.bill/counters.json     the last id handed out per table
data/schema/*.json      the system tables, written in from the product
data/*.jsonl            the rows (they arrive with the first write)
prose/                  everything that is not structured data, with a welcome note
```

Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A decision nobody could
  answer is not one; Bill stops with exit code `1` instead of assuming.
- **Declining creates nothing.** Bill says where to move the binary instead —
  and exits without an error, because declining is not one.

`BILL_ROOT` aims the engine at another folder. It exists for the tests and for
running from a checkout, and it is the only environment variable that decides
where Bill writes.

While developing, this checkout *is* the Working Folder: `data/`, `prose/` and
`.bill/` are created where they belong and are ignored by git.

## The tables

A table is one declaration: `data/schema/<table>.json` says what it is, where its
rows live, which field names a row, and what each field accepts. The declaration
**ships with the product** (`bill/data/defaults/`) and is written into the folder
on the first run — after that, the folder's copy is the one that counts.

**The declaration carries no text a person reads.** A label is a key of `i18n`,
never the words themselves (§4) — so `"label": "table.task.field.status"` lives
in the schema and `Status`/`Status` live in the catalog.

The id counter is **not** in the declaration: it counts what happened in *this*
folder, and the declaration is published. It goes in `.bill/counters.json`, and
it is written before the row — a number handed out is spent even if the write
that followed failed, because an id that comes back is an id two rows answer to.

Actions: `list`, `view`, `create`, `edit`. `cancel` and `delete` are not here yet
(both need the `lifecycle` a table declares for closing with history).

```sh
bill task create --set text="write the README" --set priority=high
bill task list              # the table's default slice; `--all` shows everything
bill task view 3            # or TASK-3, or tarefa-3
bill task edit 3 --set status=done
```

## Language

The rule is absolute (§3): **no string is written into the code**, in any
surface. Every text a person reads comes from `bill/i18n/`.

- Texts live in **blocks** — one file per subject, both languages side by side,
  at `bill/i18n/blocks/<block>.json`. The filename is the namespace:
  `blocks/boot.json` holds `first_run.confirm`, read as `boot.first_run.confirm`.
- Keys are **stable ids**, never the English sentence: renaming a text must not
  rename a key.
- `pt_BR` is the source language — texts are written there first, and `en_US` is
  their translation. A key missing in the active language falls back to the
  source, then to the key itself, so a gap is visible rather than silent.
- Resolution order: `$BILL_LANG` → `.bill/i18n/active` → the OS locale → `en_US`.
- The suite asserts both languages carry exactly the same keys, so a translation
  that lags is a failing test instead of a surprise.

Code runs the other way: identifiers, comments, object keys, methods and
filenames are `en_US` (§3).

## The WebApp

```sh
bill webapp run              # loopback, port 12345; `--port N` to change it
```

The WebApp serves three things and nothing else: **the built page**, **the look**
(`base.css`, the themes, the drawings, the hosted typefaces) and the **JSON** the
page reads. The page owns no rule — the server decides, the page draws.

The panel has four entries:

| entry | what it is |
|---|---|
| **Tarefas** | the **projects tree** — a project with the count of the tasks that name it, the subprojects indented, and last the **"no project"** node, which opens the tasks no project claims. A project opens a **page** carrying the tasks of its whole subtree, each row saying which subproject it came from. |
| **Arquivos** | the tree of `prose/`, and the page of one file — read, and written in place when the server says it may be. |
| **Tabelas** | the vocabulary: every declared table, with its count. |
| **Configurações** | the foot of the panel: the language (read-only), the side of the theme, the motion and the theme list. It writes no store — what it configures is the page. |

**There is no separate "Projetos" entry.** The Tarefas fold *is* the projects
tree: a project is a scope of tasks, and the tree is how one reaches them — a
second line would be the same door with another name.

- **No authentication of its own.** The only way in is loopback; the guard belongs
  to the ingress (§7). What stands in its place is the pair of guards on every
  write: the `Origin` must carry the same authority as the `Host`, and the body
  must declare itself JSON.
- **The theme is a LOOKUP, never a path**: an id that names no theme falls back to
  the default, so a query string can never reach a file the registry does not name.
- **The drawings and the typefaces are served BY NAME** through `/icons/<name>`
  and `/vendor/<key>`. Nothing is embedded as `data:` — the page runs under
  `default-src 'self'`, and an embedded drawing would simply never paint.
- **The hosted dependencies are pinned**: `vendor/manifest.json` names the package,
  the version and the sha256 of every file, and the server checks the hash against
  what was installed (§3).

The page is a **Vue 3 + TypeScript** app, built by Vite (§5). The build is
derivation, never edited:

```sh
cd bill/ui/webapp
npm ci && npm run build      # writes dist/, which the server serves
npm run typecheck            # vue-tsc
```

Two settings in `vite.config.ts` are not taste: the modulepreload polyfill and
the inline-asset limit are OFF, because both would emit an inline `<script>` or a
`data:` and the policy would refuse them. And the look is injected into the head
by a `transformIndexHtml` plugin — Vite treats `<link rel="stylesheet">` as
something to bundle and **silently removes** what it cannot find on disk, which
is how a build once shipped without a single rule.

## Surfaces

| Surface | How to reach it | State |
|---|---|---|
| `cli` | `bill <word>` | `help`, `version`, `webapp`, and the tables |
| Wizard | `bill` with no word | the Control Panel opens, at hello world |
| WebApp | `bill webapp run` | reads and edits the tables |

Exit codes: `0` success · `1` refused or failed · `2` usage error.

## Development

```sh
python3 -m bill help                         # the words
python3 -m unittest discover -s bill/tests   # the suite
```

Python 3.14.7 with no runtime dependency at all. A dependency arrives pinned in
version and hashing (§3), and starting from zero is how that promise is kept
cheap. The one exception is deliberate: the WebApp's hosted typefaces live in
`bill/ui/webapp/vendor/` with the hash the manifest pins.

### The single binary

```sh
# build-time only, never a runtime dependency; both pinned (§3) because the
# hooks ship separately from the freezer and float on their own
.venv/bin/pip install 'pyinstaller==6.22.3' 'pyinstaller-hooks-contrib==2026.7'
.venv/bin/pyinstaller --clean --noconfirm bill.spec   # writes dist/bill
```

`bill.spec` is the one place that says what travels inside the binary, and it is
by hand on purpose: three of the payloads (`bill/i18n/blocks`,
`bill/data/defaults`, and the WebApp's `assets`, `dist` and `vendor`) are
invisible to an import graph, and `bill/ui/webapp/` also holds `node_modules/` and
`src/`, which are the derivation and must not travel. A payload left out fails
silently in the WebApp — 404s and a 500 — and loudly everywhere else, because
`tr()` raises on the first message of every command.

**It builds on Linux only.** PyInstaller is not a cross-compiler and cannot be:
it freezes by executing code from the *target* interpreter at build time. So
Windows and macOS binaries need their own builds on their own runners (§8), and
`bill.spec` is written to be the file all three of them share.

The binary is one file because that is what the Manifesto promises (§3), and the
price is that the whole payload — Tcl/Tk included — is re-extracted on every
launch, so cold start is slower than a directory build would be.

The Working Folder does not depend on that choice: `paths.working_folder()`
resolves from `sys.executable`, which is the launched binary under `--onedir`
too, so the folder the binary sits in is the folder it works in either way. Run
it from anywhere and it still works on its own folder. Note that `bill` with no
word opens the Tkinter Wizard, so a headless check wants `bill <word>`.

## Decisions taken in session

These did not come from the Manifesto — they were taken while building, and this
table is where they are kept. The right-hand column says **where each one is
settled**: a Manifesto section once it is written there, this README when the
decision sits below the Manifesto's altitude (§0 — module folder names, paths and
API shapes do not belong in that file).

This file is not a request for a signature. Where a decision is Manifesto-level
and is **not** yet written there, the agent says so in session, because the
Manifesto is the human's and nothing reaches it any other way (§0). `†` marks
those: the decision holds here today, and the pen is the human's.

| Decision | Where it is settled |
|---|---|
| The layer folders are `bill/{core,data,prose,services,encryption,ui,i18n}` | this README — folder names sit below the Manifesto's altitude (§0) |
| The Wizard stays **Tkinter** | `MANIFESTO.md` §5 |
| The first run **requires an interactive answer**; with no terminal Bill refuses | `MANIFESTO.md` §3 |
| The active language resolves as `$BILL_LANG` → `.bill/i18n/active` → locale → `en_US` | `MANIFESTO.md` §3 |
| `bill` with no word opens the Wizard; `bill help` prints the words | `MANIFESTO.md` §7 |
| The **id counter** lives in `.bill/counters.json`, never in the published schema | `MANIFESTO.md` §4 |
| The schema is a **declaration that ships with the product**, written into the folder on the first run | `MANIFESTO.md` §4 |
| A **display label is an i18n key** in the schema, never the text | `MANIFESTO.md` §4 |
| **A block carries both languages; a key is a stable id** — renaming a text must not rename a key | this README † |
| The **theme registry** travels with the UI (`ui/webapp/assets/themes.jsonl`), not in `data/` — §4 does not list `themes` among the system tables | this README |
| The table actions today are **list, view, create, edit** | this README — `cancel`/`delete` need `lifecycle`, a decision of its own |
| The WebApp **runs on loopback with no authentication of its own**; the container (§6c) and the `basic` for Authelia (§7) are pending | this README, with the debt named |
| The page's **own words** come from the catalog through `/api/state` | this README |
| The **id a person reads is the machine word, uppercased** (`TASK-7`), and it does not follow the UI language | this README † — an exception to §3's i18n rule, so the Manifesto should carry it |
| The Working Folder resolves as the binary's folder / `cwd`, with `BILL_ROOT` for tests | this README — §3 owns the binary's folder; `BILL_ROOT` is the test door |
| A task names its project, and **that is the only direction** — the project keeps no `tasks` list. Two lists that must agree are two lists that drift | this README † — a change from the PoC, which read both |
| The **files tree is rooted at `prose/`**, not at the Working Folder: `data/` is the table engine's and `.bill/` is the instance's | this README |
| A file is written **with the revision it was read at**; a stale write answers `409` and carries the revision the disk holds | this README † |
| The **checker (LanguageTool) is not in**: the write field saves, and it does not check | this README — §6d makes it optional |
| There is **no live channel**: the trees re-read when the page is poked, not when another tab writes | this README |

## Not here yet

`BACKLOG.md` holds what comes next, with what counts as done for each.
