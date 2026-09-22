# Architecture

The derived half of the founding document: the tree, the Working Folder and the operation. Each section here is `architecture §N`, and the `README §N` references point at the [founding document](README.en_US.md), which binds.

## 1. The repository tree

Each node with its job, and none resolves a path of its own beyond `core` (`README` §4).

```
bill/                          the product: the engine, the declarations and the UI
├── core/                      the rules — the Working Folder, the settings, the first run,
│                              the single writer, the table engine, the project scope
├── data/                      the tables: `data/<table>.jsonl` for the rows and
│   │                          `data/schema/<table>.json` for the schema
│   └── defaults/              the declarations the product delivers, written into the folder on the first run
├── prose/                     every file that is not structured data: the tree of `prose/`,
│                              what a file there IS, and the write with its revision
├── services/                  external services, as tool-agnostic as the layer can be
├── encryption/                secrets: the Access Phrase, the Bill Key and the derived keys
├── nlu/                       interpretation: the vocabulary, the matcher and the action proposal
├── posture/                   the posture: the graded functions, the grades and the weakest link
├── ui/
│   ├── cli/                   the command line — the surface that reaches everything
│   ├── wizard/                the Control Panel, in Tkinter
│   └── webapp/                the WebApp: the server, the look it serves, and the Vue app
│       ├── app.py             the server
│       ├── assets/            `base.css`, the themes (`themes.jsonl`), the drawings
│       ├── src/               the derivation (Vue 3 + TypeScript) — does NOT travel in the binary
│       ├── dist/              the built output, served at runtime — comes from `npm run build`
│       ├── vendor/            the hosted typefaces, with the hash the manifest pins
│       └── node_modules/      the derivation — does NOT travel in the binary
├── i18n/
│   ├── blocks/<block>.json    one file per subject, both languages side by side — the filename
│   │                          is the namespace (`blocks/boot.json` holds `first_run.confirm`)
│   └── vocabulary/            the interpreter's vocabulary, per language, packed like the blocks
└── tests/                     the suite — stdlib `unittest`, because a test runner is not a dependency
    ├── spelling.pt_BR.txt     what the checker must ignore in Portuguese
    └── spelling.en_US.txt     the same, in English

docs/                          the documents
├── README.pt_BR.md            the source: the founding document, which binds
├── README.en_US.md            the translation, which moves along with it
├── architecture.pt_BR.md      the derivation: the tree, the Working Folder and the operation
├── architecture.en_US.md      its translation, which moves along with it
├── functionalities.pt_BR.md   what the grade measures: the functionalities, levels and grades
├── functionalities.en_US.md   its translation, which moves along with it
└── backlog.en_US.md           the working document: what comes next, and what counts as done
bill.spec                      what travels inside the binary, written by hand
pyproject.toml                 the packaging and the metadata
requirements-dev.txt           the development dependencies, pinned in version and hash
README.md                      the door: the title and the links to the documents in each language
```

`bill.spec` is the one place that says what travels inside the binary, and it is by hand on purpose: three of the payloads — `bill/i18n`, `bill/data/defaults`, and the WebApp's `assets`, `dist` and `vendor` — are invisible to an import graph, and `bill/ui/webapp/` also holds `node_modules/` and `src/`, which are the derivation and must not travel. A payload left out fails silently in the WebApp (404s and a 500) and loudly everywhere else, because `tr()` raises on the first message of every command.

## 2. The Working Folder

The folder the binary was opened in is the binary's folder, and that folder is the Working Folder (`README` §3). On the first run Bill describes the folder and asks before writing anything; `app/settings.json` is what makes a folder configured.

A folder is born with:

```
app/settings.json         the instance's key-value configuration
app/i18n/active           the chosen language — the catalogs travel in the product
app/counters.json         the last id handed out per table
app/plugins/              the extensions, and the review state of each one
app/services/<service>/   the persistent state of each service (`README` §4)
data/schema/*.json        the system tables, written in from the product
data/*.jsonl              the rows (they arrive with the first write)
prose/                    everything that is not structured data, with a welcome note
```

Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A decision nobody could answer is not one; Bill stops with exit code `1` instead of assuming.
- **Declining creates nothing.** Bill says where to move the binary instead — and exits without an error, because declining is not one.

`BILL_ROOT` aims the engine at another folder. It exists for the tests and for running from a checkout, and it is the only environment variable that decides where Bill writes.

While developing, this checkout *is* the Working Folder: `data/`, `prose/` and `app/` are created where they belong and are ignored by git.

## 3. Operation

```sh
python3 -m bill help                         # the words
python3 -m bill task create --set text="write the README" --set priority=high
python3 -m bill task list                    # the table's default slice; `--all` shows everything
python3 -m bill task view 3                  # or TASK-3, or tarefa-3
python3 -m bill task edit 3 --set status=done
python3 -m bill pedir "cria uma tarefa pra sexta"   # the proposal, for you to check
python3 -m bill webapp run                   # local loop, port 12345; `--port N` changes it
.venv/bin/python -m unittest discover -s bill/tests   # the suite (the venv carries the checker)
```

The table actions today are `list`, `view`, `create` and `edit`. `cancel` and `delete` are not here yet: both need the `lifecycle` a table declares for closing with history, and deletion needs the reference rule — `audit` is a declared exception to it, for being a log and not a link.

Surfaces, and the state of each one today:

| surface | how to reach it | state |
|---|---|---|
| `cli` | `bill <word>` | `help`, `version`, `webapp` and the tables |
| Wizard | `bill`, with no word | the Control Panel opens, at hello world |
| WebApp | `bill webapp run` | reads and edits the tables |

Exit codes: `0` success · `1` refused or failed · `2` usage error.

Python 3.14.7 with no runtime dependency at all. A dependency arrives pinned in version and hashing (`README` §3), and starting from zero is how that promise is kept cheap. There are two deliberate exceptions, both on the development side: the WebApp's hosted typefaces, in `bill/ui/webapp/vendor/`, with the hash the manifest pins; and the documents' checker, which runs in the suite and is therefore a tool, not an installation — it cannot demand from another dev or from the runner anything that does not come pinned inside `.venv`.

The suite runs the document gate (`README` §3, Internationalization), and its checker is installed once:

```sh
.venv/bin/pip install --require-hashes -r requirements-dev.txt
```

### The page

The page is a **Vue 3 + TypeScript** app, built by Vite (`README` §5). The build is derivation, never edited:

```sh
cd bill/ui/webapp
npm ci && npm run build      # writes dist/, which the server serves
npm run typecheck            # vue-tsc
```

Two settings in `vite.config.ts` are not taste: the modulepreload polyfill and the inline-asset limit are OFF, because both would emit an inline `<script>` or a `data:` and the policy would refuse them. And the look is injected into the head by a `transformIndexHtml` plugin — Vite treats `<link rel="stylesheet">` as something to bundle and **silently removes** what it cannot find on disk, which is how a build once shipped without a single rule.

### The single binary

```sh
# build-time only, never a runtime dependency; both pinned (`README` §3) because the
# hooks ship separately from the freezer and float on their own
.venv/bin/pip install 'pyinstaller==6.22.3' 'pyinstaller-hooks-contrib==2026.7'
.venv/bin/pyinstaller --clean --noconfirm bill.spec   # writes dist/bill
```

**It builds on Linux only.** PyInstaller is not a cross-compiler and cannot be: it freezes by executing code from the *target* interpreter at build time. So Windows and macOS binaries need their own builds on their own runners (`README` §9), and `bill.spec` is written to be the file all three of them share.

The binary is one file because that is what the founding document promises (`README` §3), and the price is that the whole payload — Tcl/Tk included — is re-extracted on every launch, so cold start is slower than a directory build would be.

The Working Folder does not depend on that choice: `paths.working_folder()` resolves from `sys.executable`, which is the launched binary under `--onedir` too, so the folder the binary sits in is the folder it works in either way. Run it from anywhere and it still works on its own folder. Note that `bill` with no word opens the Tkinter Wizard, so a headless check wants `bill <word>`.
