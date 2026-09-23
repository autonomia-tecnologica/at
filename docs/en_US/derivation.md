# Derivation

The derived half of the founding document: the tree, the Working Folder and the operation. Each section here is `derivation §N`, and the `§N` references point at the article with that id, wherever it lives.

## 1. The repository tree

Each node with its job, and none resolves a path of its own beyond `core` (§4).

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
├── encryption/                secrets: the Access Phrase, the Bill Key and the derived keys,
│                              and `password`, the derivation the hashed field stores
├── nlu/                       interpretation: the vocabulary, the matcher and the action proposal
├── posture/                   the posture: the graded functions, the grades and the weakest link
├── ui/
│   ├── ask.py                 the interpreter's door: one sentence, one proposal, and it runs
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
├── pt_BR/                     the source: the documents written in Portuguese
│   ├── README.md              the founding document, which binds
│   ├── rules.md               the rules that bind (§3)
│   ├── architecture.md        the architecture that binds (§4)
│   ├── interfaces.md          the interfaces: `cli`, WebApp and Wizard (§5)
│   ├── paths.md               the two paths of use (§6)
│   ├── container.md           the container path: the steps (§7)
│   ├── extensions.md          the extensions and the plugins (§8)
│   ├── end-to-end.md          the end-to-end test environment (§9)
│   ├── derivation.md          the derivation: the tree, the Working Folder and the operation
│   ├── functionalities.md     what the grade measures: the functionalities, levels and grades
│   └── glossary.md            what a name means, term by term
└── en_US/                     the translation: the same documents, in English
    ├── README.md              the founding document's translation, which moves along with it
    ├── rules.md               its translation, which moves along with it
    ├── architecture.md        its translation, which moves along with it
    ├── interfaces.md          its translation, which moves along with it
    ├── paths.md               its translation, which moves along with it
    ├── container.md           its translation, which moves along with it
    ├── extensions.md          its translation, which moves along with it
    ├── end-to-end.md          its translation, which moves along with it
    ├── derivation.md          its translation, which moves along with it
    ├── functionalities.md     its translation, which moves along with it
    ├── glossary.md            its translation, which moves along with it
    └── backlog.md             the working document, English only: what comes next, and what counts as done
```

`bill.spec` is the one place that says what travels inside the binary, and it is by hand on purpose: three of the payloads — `bill/i18n`, `bill/data/defaults`, and the WebApp's `assets`, `dist` and `vendor` — are invisible to an import graph, and `bill/ui/webapp/` also holds `node_modules/` and `src/`, which are the derivation and must not travel. A payload left out fails silently in the WebApp (404s and a 500) and loudly everywhere else, because `tr()` raises on the first message of every command.

## 2. The Working Folder

The folder the binary was opened in is the binary's folder, and that folder is the Working Folder (§3). On the first run Bill describes the folder and asks before writing anything; `App/settings.json` is what makes a folder configured.

**The name on disk is the face; the machine reads the internal name.** Every folder has an internal name — `app`, `data`, `prose`, `projects`, `shared` — and that is the one the engine uses and the one the declarations cite. The name a person reads comes from the active language, and the table in `paths.py` is the only thing that knows it: `Tabelas/`, `Arquivos/`, `Projetos/` and `Compartilhada/` in `pt_BR`; `Tables/`, `Files/`, `Projects/` and `Shared/` in `en_US`. The instance folder is the exception, and it is deliberate: it does not follow the language, because the language lives inside it — `App/` in both.

A folder is born with:

```
App/settings.json         the instance's key-value configuration
App/i18n/active           the chosen language — the catalogs travel in the product
App/counters.json         the last id handed out per table
App/migrations            how far this folder has migrated
App/plugins/              the extensions, and the review state of each one
App/services/<service>/   the persistent state of each service (§4)
Tables/schema/*.json      the system tables, written in from the product
Tables/*.jsonl            the rows (they arrive with the first write)
Files/                    everything that is not structured data, with a welcome note
Projects/                 what belongs to a project — named, still empty
Shared/                   what is shared with other people — named, still empty
```

**The migration.** Updating Bill is replacing the binary inside the folder, so every release that changes the folder's structure brings its migration and it runs on the first start after the swap (§3). The stamp is `App/migrations`, and it lives with the rest of what Bill writes, never inside the published declaration. There are three migrations today: `.bill/` → `app/`, `app/` → `App/`, and the person's folders into the active language — and the last one asks first, because renaming breaks whatever points at them from outside Bill. Whoever declines keeps the name they had, and the resolution reads both spellings.

A folder that has not migrated yet **is found by its old name**: `paths.instance_dir()` reads what is on disk before deciding, so that a folder with `.bill/` is not read as a new one — which was the defect migration number one existed to close.

Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A decision nobody could answer is not one; Bill stops with exit code `1` instead of assuming.
- **Declining creates nothing.** Bill says where to move the binary instead — and exits without an error, because declining is not one.

`BILL_ROOT` aims the engine at another folder. It exists for the tests and for running from a checkout, and it is the only environment variable that decides where Bill writes.

While developing, this checkout *is* the Working Folder: the folders are created where they belong, under the active language's spelling, and every spelling is ignored by git.

## 3. Operation

```sh
python3 -m bill help                         # the words
python3 -m bill task create --set text="write the README" --set priority=high
python3 -m bill task list                    # the table's default slice; `--all` shows everything
python3 -m bill task view 3                  # or TASK-3, or tarefa-3
python3 -m bill task edit 3 --set status=done
python3 -m bill pedir "cria uma tarefa pra sexta"   # the proposal, and the answer
python3 -m bill webapp run                   # local loop, port 12345; `--port N` changes it
.venv/bin/python -m unittest discover -s bill/tests   # the suite (the venv carries the checker)
```

The table actions are `list`, `view`, `create`, `edit`, `cancel` and `delete`. `cancel` closes a row WITH history — the terminal status, where the reason lands and whether it is required all come from the `lifecycle` the table declares — while `delete` takes the row out, refusing while another row NAMES it and never giving the number back. What names a row is read off the declarations, never off a scan of the folder, and a table that declares no `lifecycle` has no closing and says so.

Surfaces, and the state of each one today:

| surface | how to reach it | state |
|---|---|---|
| `cli` | `bill <word>` | `help`, `version`, `webapp`, `ask` and the tables |
| Wizard | `bill`, with no word | the Control Panel opens, at hello world |
| WebApp | `bill webapp run` | reads and edits the tables, and reaches the interpreter through the chat and the balloon |

Exit codes: `0` success · `1` refused or failed · `2` usage error.

Python 3.14.7, with **one** runtime dependency: `PyNaCl`, the binding of `libsodium`, pinned in version and in hashing in `requirements.txt` (§3). The hashed field's derivation is `libsodium`'s, and that is not the standard library, so the price is named instead of avoided. Its wheel carries `libsodium` inside it, so the binary stays self-contained and nothing is asked of the machine that runs it. Two more exceptions are deliberate, and both stay on the development side: the WebApp's hosted typefaces, in `bill/ui/webapp/vendor/`, with the hash the manifest pins; and the documents' checker, which runs in the suite and is therefore a tool, not an installation — it cannot demand from another dev or from the runner anything that does not come pinned inside `.venv`.

That dependency installs first, under the same rule:

```sh
.venv/bin/pip install --require-hashes -r requirements.txt
```

The suite runs the document gate (§3, Internationalization), and its checker is installed once:

```sh
.venv/bin/pip install --require-hashes -r requirements-dev.txt
```

### The page

The page is a **Vue 3 + TypeScript** app, built by Vite (§5). The build is derivation, never edited:

```sh
cd bill/ui/webapp
npm ci && npm run build      # writes dist/, which the server serves
npm run typecheck            # vue-tsc
```

Two settings in `vite.config.ts` are not taste: the modulepreload polyfill and the inline-asset limit are OFF, because both would emit an inline `<script>` or a `data:` and the policy would refuse them. And the look is injected into the head by a `transformIndexHtml` plugin — Vite treats `<link rel="stylesheet">` as something to bundle and **silently removes** what it cannot find on disk, which is how a build once shipped without a single rule.

### The single binary

```sh
# build-time only, never a runtime dependency; both live in the development
# requirements, with version and hash (§3), because the hooks ship separately
# from the freezer and float on their own
.venv/bin/pip install --require-hashes -r requirements-dev.txt
.venv/bin/pyinstaller --clean --noconfirm bill.spec   # writes dist/bill
```

**It builds on Linux only.** PyInstaller is not a cross-compiler and cannot be: it freezes by executing code from the *target* interpreter at build time. So Windows and macOS binaries need their own builds on their own runners (§9), and `bill.spec` is written to be the file all three of them share.

The binary is one file because that is what the founding document promises (§3), and the price is that the whole payload — Tcl/Tk included — is re-extracted on every launch, so cold start is slower than a directory build would be.

The Working Folder does not depend on that choice: `paths.working_folder()` resolves from `sys.executable`, which is the launched binary under `--onedir` too, so the folder the binary sits in is the folder it works in either way. Run it from anywhere and it still works on its own folder. Note that `bill` with no word opens the Tkinter Wizard, so a headless check wants `bill <word>`.
