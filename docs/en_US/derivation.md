# Derivation

The derived half of the founding document: the Working Folder and the operation. Each section here is `derivation §N`, and the `§N` references point at the article with that id, wherever it lives.

## 1. The Working Folder

The folder the binary was opened in is the binary's folder, and that folder is the Working Folder (§3). On the first run AT describes the folder and asks before writing anything; `App/settings.json` is what makes a folder configured.

**The name on disk is the face; the machine reads the internal name.** Every folder has an internal name — `app`, `data`, `prose`, `projects`, `shared`, `harness` and `cofre` — and that is the one the engine uses and the one the declarations cite. The name a person reads comes from the active language, and the table in `paths.py` is the only thing that knows it: `Tabelas/`, `Biblioteca/`, `Projetos/`, `Compartilhado/` and `Cofre/` in `pt_BR`; `Tables/`, `Library/`, `Projects/`, `Shared/` and `Vault/` in `en_US`. The spellings `Arquivos/` and `Files/` are `prose/`'s retired ones — the resolution still accepts them, which is why a folder that did not migrate does not disappear. Two folders are the exception, and both are deliberate: the instance folder does not follow the language, because the language lives inside it — `App/` in both — and `Harness/` does not, because `pt_BR` took the word whole, so both languages spell it the same way.

A folder is born with:

```
README.md                 the folder presenting itself, to whoever works in it
App/settings.json         the instance's key-value configuration
App/i18n/active           the chosen language — the catalogs travel in the product
App/counters.json         the last id handed out per table
App/migrations            how far this folder has migrated
App/extensions/           the extensions, copied here
App/extensions.json       the review state of each one
App/services/<service>/   the persistent state of each service (§4)
Tables/schema/*.json      the system tables, written in from the product
Tables/*.jsonl            the rows (they arrive with the first write)
Library/                  everything that is not structured data, with a welcome note
Projects/                 what belongs to a project — named, still empty
Shared/                   what is shared with other people — named, still empty
Harness/                  what governs whoever works in the folder — named, still empty
Vault/                    what seals on its own — named, still empty
```

That listing is what a folder is born with. `App/services/` arrives later, and only
if a service is asked for — but it is the house of EVERY service now, on BOTH paths,
and each one lives in `App/services/<service>/`. The Caddy is the first: `at-cli
webapp` (without `--no-caddy`) unpacks `App/services/caddy/` — the Caddy out of the
binary, the stamp that says which platform it serves, the Caddyfile AT generates,
and the Caddy's own storage, its local authority among the rest (§6, §12) —, and it
lives under `App/` for the reason §3 gives: what was extracted to run belongs to the
folder, so a copied folder comes back with the Caddy and the certificates it had.
The hosted path's Authelia, the push, the gitleaks and the Jev cache live there too.

On the container path it is `at-deploy up` that writes in `App/services/`: `images.json`
records the pin this folder IS at, per service, and each service's own folder carries
what it reads — `caddy/Caddyfile`, the Caddyfile AT generates, with the storage inside
the container. Nothing comes up without Podman: AT checks whether it exists and, if it
does not, offers the two ways out — install it, or continue on the hosted path. The
images are pinned in version and hashing, as §3 demands, so the folder's pin and the
binary's are compared on every `up` — and an instance AHEAD of the binary's pin warns
and proceeds, because it is not downgraded.

The note at the root is the one file a folder carries for whoever works inside it:
it says what the folder is, what it holds and how to reach the rest, and it cites
the founding document instead of repeating a rule (§0). It is the `README.md` —
its **name** does not follow the language, because a note whose name moved with
the translation is a note a model stops finding — while the text does. It is
written once, as the welcome note is, and a folder that already existed gains it
by migration.

**The migration.** Updating AT is replacing the binary inside the folder, so every release that changes the folder's structure brings its migration and it runs on the first start after the swap (§3). The stamp is `App/migrations`, and it lives with the rest of what AT writes, never inside the published declaration. There are thirty-three migrations today: `.bill/` → `app/`, `app/` → `App/`, the person's folders into the active language, `Harness/`, the declarations of the tables a release introduces, and the administrator's role catching up with the permissions a release grew the catalogue by — twice, because the catalogue grew twice and a published migration is never edited. The third asks first, because renaming breaks whatever points at them from outside AT; whoever declines keeps the name they had, and the resolution reads both spellings. The rest touch only what AT writes, and none of them overwrites anything — the sixth names the tables THAT release brings, and not the whole directory, so it never brings back a declaration a person deleted; what only completes brings nothing beyond what the folder never had the CHANCE to carry.

A folder that has not migrated yet **is found by its old name**: `paths.instance_dir()` reads what is on disk before deciding, so that a folder with `.bill/` is not read as a new one — which was the defect migration number one existed to close.

Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A decision nobody could answer is not one; AT stops with exit code `1` instead of assuming.
- **Declining creates nothing.** AT says where to move the binary instead — and exits without an error, because declining is not one.

`AT_ROOT` aims the engine at another folder. It exists for the tests and for running from a checkout, and it is the only environment variable that decides where AT writes.

While developing, this checkout *is* the Working Folder: the folders are created where they belong, under the active language's spelling, and every spelling is ignored by git.

## 2. Operation

```sh
python3 -m at help                         # the words
python3 -m at task create --set text="write the README" --set priority=high
python3 -m at task list                    # the table's default slice; `--all` shows everything
python3 -m at task view 3                  # or TASK-3, or tarefa-3
python3 -m at task edit 3 --set status=done
python3 -m at admin                        # the first administrator: a name, and the credential with no echo
python3 -m at pedir "cria uma tarefa pra sexta"   # the proposal, and the answer
python3 -m at webapp run                   # exposed by default, with the Caddy's TLS on `--port`
                                             # and `--host` naming the address it answers on
python3 -m at webapp --no-caddy            # local loop, port 12345; `--port N` changes it
python3 -m at_deploy services up           # the container path: the services at the pin
python3 -m at_deploy services status       # what is standing, and on which image
python3 -m at_deploy services down         # down; the folder stays
python3 -m at_deploy services credential <name>   # the credential the gate proves, and the provider restarted
.venv/bin/python -m unittest discover -t .   # both suites (the venv carries the checker)
```

The table actions are `list`, `view`, `create`, `edit`, `cancel` and `delete`. `cancel` closes a row WITH history — the terminal status, where the reason lands and whether it is required all come from the `lifecycle` the table declares — while `delete` takes the row out, refusing while another row NAMES it and never giving the number back. What names a row is read off the declarations, never off a scan of the folder, and a table that declares no `lifecycle` has no closing and says so.

Surfaces, and the state of each one today:

| surface | how to reach it | state |
|---|---|---|
| `cli` | `at-cli <word>` | `help`, `version`, `webapp`, `admin`, `lang`, `ask` and the tables |
| the deploy's `cli` | `at-deploy <word>` | `help`, `version` and the six `services` words plus the operator's own — `credential`; it carries no WebApp, and its Wizard is item 27's third slice |
| Wizard | — | down until item 9 reaches slice 3: `at-cli` with no word prints the `help` |
| WebApp | `at-cli webapp run` | reads and edits the tables, reaches the interpreter through the chat and the balloon, refuses to come up in a folder with no administrator and — when there is one — asks for the credential and gives no answer of the API before it is proved; and it is where the ceiling is MOVED: the People entry, with the actor and the role screens, the closed list a role is written against, and the machine credential AT mints |

`at-cli webapp` exposes by default, the exposure §3 demands TLS for: the Caddy
that came inside the binary terminates it with AT's own certificate, and the
WebApp stays on `127.0.0.1` behind it. `--no-caddy` goes back to the local
loop over HTTP. What `--host` names changes with the flag — the name the
certificate is issued for by default, since a certificate is issued for a name
and `0.0.0.0` is not one; and the loop it may bind with `--no-caddy`.

Exit codes: `0` success · `1` refused or failed · `2` usage error.

Python 3.14.7, with **one** runtime dependency: `PyNaCl`, the binding of `libsodium`, pinned in version and in hashing in `requirements.txt` (§3). The hashed field's derivation is `libsodium`'s, and that is not the standard library, so the price is named instead of avoided. Its wheel carries `libsodium` inside it, so the binary stays self-contained and nothing is asked of the machine that runs it. Two more exceptions are deliberate, and both stay on the development side: the WebApp's hosted files — the typefaces and the renderer —, in `at/ui/webapp/vendor/`, with the hash the manifest pins; and the documents' checker, which runs in the suite and is therefore a tool, not an installation — it cannot demand from another dev or from the runner anything that does not come pinned inside `.venv`.

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
cd at/ui/webapp
npm ci && npm run build      # writes dist/, which the server serves
npm run typecheck            # vue-tsc
npm run dev                  # the app with hot reload, to work in
```

`npm run dev` starts Vite **and needs the server behind it**: Vite serves the app — the modules, the hot reload — and `at-cli webapp` keeps everything that is not the app (the words, the tables, the look, the icons, the pinned files), on its own port (`AT_WEBAPP_PORT`, defaulting to AT's own — 12345). Two processes and one origin, which is why the look enters the head the same way: the `transformIndexHtml` plugin runs in dev too, and `/theme.css` and `/base.css` cross the proxy.

Two settings in `vite.config.ts` are not taste: the modulepreload polyfill and the inline-asset limit are OFF, because both would emit an inline `<script>` or a `data:` and the policy would refuse them. And the look is injected into the head by a `transformIndexHtml` plugin — Vite treats `<link rel="stylesheet">` as something to bundle and **silently removes** what it cannot find on disk, which is how a build once shipped without a single rule.

### The two binaries

```sh
# build-time only, never a runtime dependency; both live in the development
# requirements, with version and hash (§3), because the hooks ship separately
# from the freezer and float on their own
.venv/bin/pip install --require-hashes -r requirements-dev.txt
.venv/bin/pyinstaller --clean --noconfirm at-cli.spec          # writes dist/at
.venv/bin/pyinstaller --clean --noconfirm at-deploy.spec   # writes dist/at-deploy
```

**One release, two files, and the split IS the point.** `at-cli` is the folder and the app — the tables, the prose, the interpreter, the WebApp and the Wizard — and `at-deploy` is §7 whole: the Podman, the VPN, the gate's containers, the edge, the transactional switch and the only elevation in the product. It is a second artifact and not a second command of the same one because the promise §3 makes is read off what the FILE is: an `at-cli` that *cannot* ask is a stronger promise than an `at-cli` that does not. The elevation MOVED and is not duplicated, and what keeps the two apart is the import graph — `at_deploy` imports `at`, and `at` imports nothing of the deploy — which the suite affirms from the sources. The shared core (`paths`, `i18n`, `files`, the table engine) travels in both, collected from the same files: one source and not two.

Each binary is one file because that is what the founding document promises (§3), and the price is that the whole payload — Tcl/Tk included — is re-extracted on every launch, so cold start is slower than a directory build would be. The deploy carries no Tcl/Tk and no WebApp: its payload is the `i18n` blocks and the table declarations, because it confirms the Working Folder exactly as `at-cli` does and has to be able to make one.

**It builds on Linux only.** PyInstaller is not a cross-compiler and cannot be: it freezes by executing code from the *target* interpreter at build time. So Windows and macOS binaries need their own builds on their own runners (§9), and the two specs are written to be the files all three platforms share — `at-deploy.spec` is not a second target of `at-cli.spec`, because a spec IS one artifact and the two differ in the entry point, the payloads and the exclusions.

The Working Folder does not depend on that choice: `paths.working_folder()` resolves from `sys.executable`, which is the launched binary under `--onedir` too, so the folder the binary sits in is the folder it works in either way. Run it from anywhere and it still works on its own folder. Note that `at-cli` with no word prints the help — the Tkinter Wizard is down until item 9's third slice —, so a headless check wants `at-cli <word>`. The two artifacts share the folder's STATE and not an API, so `at-deploy up` works on the same folder `at-cli` serves, and `at-cli` keeps serving it with the deploy absent.
