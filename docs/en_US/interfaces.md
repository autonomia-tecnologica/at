# 5. Interfaces [normative]

### Command line (`cli`), web application (WebApp) and Tkinter interface (Wizard)

- When opening AT, whether on the command line or straight through the graphical interface, we have the "Control Panel". It is a Tkinter interface, the Wizard. Here the "guts" of AT's environment are configured, its first layer being the web application.

- Calling the binary straight from the terminal loads the Tkinter interface. Any other parameter passed makes the program act as a `cli`. `at ajuda`, or `at help`, shows how to use the cli completely. You can change it in the settings so that the command `at` opens `at help` instead of Tkinter.

- The command line works for everything in AT. Any functionality it exposes, whether in the REST API (used by the WebApp frontend) or in the WebApp itself, is reachable from the command line.

- The Wizard is a screen that allows more critical configurations of AT that I did not want to leave available on the network. It has roles that do not move: the **first start**, where the Working Folder is confirmed and the first admin is created; the **installation of services**, and only it installs; the **return to Forms mode**, when the authentication gate falls; and the management of the main keys in advanced mode.

- While the Control Panel is not built, the first start happens in the `cli`: `at admin` asks for the name and reads the credential with no echo, and `at` with no word prints the `help`. The Wizard does not lose the role — the first admin's screen is its own — and the door is the same one: the rule of this section is that everything of the `Wizard` is reachable from the `cli`.

- The `cli` runs only locally, except when it is communicating with external APIs for the due configuration. And it is it, or the Wizard, that returns AT to Forms mode: both are local surfaces, and that is why the return exists.

- Role and permission are **not** the Wizard's business: that is a WebApp screen, and the friction of doing admin there does not pay off. The Wizard keeps what only it can do.

### The interpretation layer

- Natural language comes in as a **resource** of the WebApp and the `cli`, and not as a fourth surface: nothing becomes possible merely by speaking. What the person types becomes a proposal, and what they can propose is what they can already do.

- **The interpreter is deterministic.** There is no LLM at run time: the LLM helps to **write** the vocabulary, and what runs is code with data. That is what cuts the cord with the third-party token, and that is why AT needs no video card to understand a sentence.

- What the interpreter consults is the **vocabulary**, per language, packed into the product alongside the `i18n` blocks, because translating vocabulary and translating text are the same task. The vocabulary is dumb data: pairs of expression → canonical expression, with language and region, and nothing conditional. What depends on context is grammar, and grammar is the product's code.

- **The interpreter proposes; the core validates and writes.** One action per request while there is no batch API; the day there is one, the batch is an action, with a permission of its own. The unit of everything is the operation of the core API, and the REST API is one of the doors to it.

- **The access ceiling is what the actor may do; the risk threshold is what it may do without asking.** Every demand has a **risk**, measured by the core from what the product declares per action and per argument — never by the interpreter, because whoever asks does not assess their own risk. The **threshold** lives in the settings: below it the action runs, above it the person approves. The risk of each action is adjustable in `settings.json`, and that of an extension is accepted at the moment of installing.

- The approval arrives by notification, and the notification is **a doorbell, not a key**: the tap opens AT and the approval happens inside it, with the session in force. The credential does not live in the notification center. A job that runs on its own can be approved this way, and the approval is a line in the audit, separate from the demand that waited.

- **The agent function is switchable**, and switching it off is taking the interpreter out of the core API: whoever does not want the language layer uses AT without it and loses nothing beyond it.

- Since the interpreter is deterministic, **the responsibility goes back to whoever asked**: a misunderstanding is our defect or a badly written sentence, and the trail says who asked. The `FAQ.md` says that in so many words, along with the advice that writing well is the best remedy.

### The WebApp application

The WebApp serves three things and nothing else: **the built page**, **the look** (`base.css`, the themes, the drawings and the hosted typefaces) and the **JSON** the page reads. The page owns no rule — the server decides, the page draws.

The panel has the entries:

| entry | what it is |
|---|---|
| **Tarefas** | the **projects tree** — a project with the count of the tasks that name it, the subprojects indented, and last the **"no project"** node, which opens the tasks no project claims. A project opens a **page** carrying the tasks of its whole subtree, each row saying which subproject it came from. |
| **Arquivos** | the tree of `prose/`, and the page of one file — read, and written in place when the server says it may be. |
| **Tabelas** | the vocabulary: every declared table, with its count. |
| **Pessoas** | the actors and the roles: who may act, with which ceiling. Only the admin opens it. |
| **Serviços** | every configured service, its state and the tokens it needs — including `ntfy`'s. |
| **Extensões** | the plugins found in the folder, each one's hash, the review mode and the blockers. This is where one installs. |
| **Postura** | the security grade, function by function, and **which functions are stopping it from rising**. |
| **Configurações** | the foot of the panel: the language, the theme, the motion, the risk threshold and the adjustments the core API exposes. |

**There is no separate "Projetos" entry.** The Tarefas fold *is* the projects tree: a project is a scope of tasks, and the tree is how one reaches them — a second line would be the same door with another name.

- **The drawings and the typefaces are served BY NAME**, through `/icons/<name>` and `/vendor/<key>`. Nothing is embedded as `data:` — the page runs under `default-src 'self'`, and an embedded drawing would simply never paint.
- **The hosted dependencies are pinned**: `vendor/manifest.json` names the package, the version and the sha256 of every file, and the server checks the hash against what was installed (§3, External dependency).
- **The theme is a LOOKUP, never a path**: an id that names no theme falls back to the default, so a query string can never reach a file the registry does not name.

#### People: where the ceiling is moved

The **People** entry holds the two system tables of the access ceiling, each row opening its own screen. Nothing here is free text: the permission is `objeto:ação` over a **closed list**, and what a person picks is picked from it.

- **The `role` screen draws the closed list as checks** — the objects, and the actions each one accepts — and writes the set back through the table route the `cli` already walks. A role that names a permission the catalogue does not have **does not take AT down**: §4's saying is drawn on the screen, beside the role, until somebody takes it out.
- **The `actor` screen is where a machine's credential is minted.** A token is not something a person types, so AT draws it, the row keeps the derivation and the token is shown **once** — it is never read back. The same screen gives a machine a new token, which is what a lost or leaked one costs, and **revokes** it: the row stays, because an actor is the name the audit will carry, and the door simply stops opening.
- **None of it is a second rule.** The screens are reachable by whoever carries the permission — the administrator's role carries the whole catalogue by construction — and everyone else is refused by the server, in the server's words.

#### Design System and themes

- The Design System is the LLM's development. Gradual growth of components.

- Theme support is a structural part of AT. Several themes help me test the strength of the Design System over different views. At the same time they make me happy to use the system. Theme PRs are welcome, but they are entirely subject to my personal judgement and I will be glad to share my terrible taste if I do not want to accept a PR. But do not be shy!

- The theme holds for the whole WebApp, **the login screen included**: there is no page of AT that escapes the Design System, and the entrance is the first impression it has to make.

- The Authelia portal is **not** an AT screen, and there is no way to dress it with the Design System: Authelia accepts a logo, a favicon, translated texts and one of four palettes, and nothing beyond that. So its theme stays as neutral as possible, and the `FAQ.md` says whose screen that is — educating about what the person is actually using is part of the product.

#### Templates

- AT uses `Vue`. As much as I dislike using many external dependencies because of the Supply Chain risk, and as much as most of that comes from JavaScript libraries, I like `Vue`. I find it a valid loss for the template management it brings. Even though I am not writing that code, it does not please me to see the LLM creating individual JavaScript files for pages. It hurts my legibility and I am very much in favor of good legibility.

#### TypeScript and frameworks

- AT's WebApp is written in TypeScript and _transpiled_ using `ViteJS`. The TypeScript is well written, respecting modules and domains, making human management easier.
