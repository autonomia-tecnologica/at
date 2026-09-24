# 3. Rules [normative]

### Security

- Every security decision of the application lives in `rules.md`, and this section is their record. No security decision is taken without discussion, and none is decided outside here: the other sections describe operation and detail what is recorded below, but they do not decide security on their own. If it is not recorded here, it does not exist.

- Isolation belongs to the container path. On the hosted path Bill is a process on the machine, with no container around it, and that is declared — there is no promise of containing the blast radius of a compromise. What the hosted path offers in exchange is listening only on the local loop by default, and demanding authentication and TLS to leave it.

- Decisions in force. The line is the decision; the detail lives where the link points:
  - Without authentication, Bill listens only on `127.0.0.1`; exposed demands authentication — [Access and exposure](#access-and-exposure).
  - Exposed demands TLS, and TLS only exists with Caddy: `bill webapp` without the flag is HTTP on the local loop — [Access and exposure](#access-and-exposure).
  - Bill has an authenticator of its own, with four ways in, all of them ending at an actor: local Forms, Basic, machine credential and the identity the gate asserts — [Interfaces](interfaces.md), [Tables](architecture.md#tables).
  - The actor's credential lives hashed in its own row, with `libsodium`; Basic and Forms are the **same** credential, and what separates them is the transport — [Tables](architecture.md#tables).
  - No secret lives in `settings.json`: it holds permission and adjustment, never a credential — [General settings](architecture.md#general-settings).
  - Every function of the core API is protected by RBAC; the permission is `object:action`, a role is a set of permissions, and a machine credential has a declared role — [Tables](architecture.md#tables).
  - The first admin is born on the first start, with a terminal in front; with no actor at all Bill does not expose — [Interfaces](interfaces.md).
  - Role and permission are a WebApp screen, and only an admin touches them — [Interfaces](interfaces.md).
  - **Installing a service is the Wizard's and only the Wizard's** — [Interfaces](interfaces.md).
  - A machine secret is stored hashed, with a role; a secret Bill **uses**, such as a service credential, is stored encrypted in the `secret` table — [Secret management](architecture.md#secret-management).
  - Bill authenticates to the services instead of taking advantage of being on the same machine: an administrative credential exists where it is necessary, and it counts in the posture — [The security posture](#the-security-posture).
  - A service that talks to Bill gets a delimited scope — least privilege: the compromise of a service reaches its function and nothing else — [Container path](paths.md#container-path).
  - Identity arriving through the gate is only valid with the gate secret: Bill draws a secret per installation, writes it into the Caddyfile it generates itself, and refuses identity without it — [Install the identity provider as a container](container.md#b-install-the-identity-provider-as-a-container-required).
  - The gate proves the credential the actor's row already carries: Bill writes the identity provider the folder's own people, with the derivation that row holds, and both the names and the derivations stay inside the Working Folder, which is what the backup covers — [Install the identity provider as a container](container.md#b-install-the-identity-provider-as-a-container-required).
  - **The notifier stays out of the gate**, and it is a measurement: the gate authenticates by redirect and by session cookie, so a headless phone app takes the 302 and never connects — measured, `subscribers=0` behind Authelia and `101` without it. Its authentication is the per-topic token ACL — [Install the notifier as a container](container.md#f-install-the-notifier-as-a-container-optional).
  - Bill's own credential in the notifier is **delimited to the topic** — it publishes and does nothing else — and, while the `secret` table does not exist, it lives in a `0600` file inside the state folder of that service, never in the argv and never printed — [Install the notifier as a container](container.md#f-install-the-notifier-as-a-container-optional).
  - Forms stays on until Authelia is proven to work in front of Bill; the switch is a set that commits or rolls back — [The switch between paths](paths.md#the-switch-between-paths).
  - A fallen gate closes Bill: it says the authentication portal is unavailable, and the way back to Forms mode is the Wizard or the `cli`, both local — [The switch between paths](paths.md#the-switch-between-paths).
  - Every action leaves one line in the `audit` table, and a refusal is one of them — [The audit](#the-audit).
  - What is proved is stored hashed; what Bill uses is stored encrypted — [Tables](architecture.md#tables).
  - The persistent state of every service lives in the Working Folder; a service whose state does not fit there does not come in — [General settings](architecture.md#general-settings).
  - **No extension executes code today.** The first class is pure data, and code is the last option — [Extensions](extensions.md).
  - The theme of the authentication portal is not Bill's: it stays as neutral as possible, and the `FAQ.md` explains what is underneath — [Interfaces](interfaces.md).
  - Authenticator, WebApp, checker, notifier and VPN run in isolated containers on the container path — [Container path](container.md).
  - Execution is without privilege, with elevation only on explicit request — [Privilege](#privilege).
  - Packages and images are pinned in version and hashing — [External dependency](#external-dependency).

### Access and exposure

- With no form of authentication configured, Bill listens only on `127.0.0.1`. There is no exception, and there is no "only on this internal network" mode: either there is authentication, or Bill does not leave the local loop.

- Exposing demands authentication **and** TLS. Since the TLS is Caddy's, and Caddy is embedded (§3, Code and delivery), exposure on the hosted path happens through `bill webapp --include-caddy`: without the flag, the command serves the WebApp over HTTP, and only on the local loop. On the container path, whoever sits at the edge is the Caddy in a container, for the isolation.

- Bill does not deliver HSTS, for an obvious reason: it serves with its own certificate, and HSTS would turn the browser's warning into an error with no way out. That is the price of not depending on a public domain, and of not being able to guarantee trusted TLS.

### The threat model

- Bill protects itself from what it can see, and says out loud what it cannot. The first barrier is the path's authenticator: Authelia on the container path, the Forms credential on the hosted one.

- The second barrier is **implicit and is not Bill's**: the protection of the phone itself. Allowing a notification to approve an action is trusting that `ntfy` was well configured **and** that this configuration is protected by a locked device. Bill **does not audit the phone** — whether it has root, whether it is emulated, whether it has a screen lock — because that is a bank's job and Bill is not a bank.

- Keeping the authenticator credential in a password manager or in the browser's vault is the person's choice, and it is dangerous. It is written here instead of hidden.

- The same goes for the outside: a folder backup that does not exist, a machine without a password, an open network. Bill measures what it controls and **declares what it does not measure**, instead of giving a grade it cannot sustain — [The security posture](#the-security-posture).

### The audit

- Every action that enters through the core becomes **one line** in the `audit` table: what was changed (`object:action`), where (the table), when (the instant), who (the actor), through which via, and the outcome. The "why" only exists in a refusal, where it is the reason, stored as an `i18n` key; outside of it, the line does not pretend to have an intention. Cost does not enter.

- **Attempt and refusal are lines**, with the outcome saying what happened — it is the attack-audit view. **A read is not a line**: reading is not doing, and auditing reads would make the trail grow faster than the use.

- The audit is **a log, not a reference**: the ids it cites are raw data, with no `ref`, and that is why it never blocks a `delete` (§4, Tables). It stores no value at all, and **nothing is deleted from it** — deletability is declared in the schema, and `audit` declares that it accepts none.

- Only the admin role carries `audit:read`, and no machine actor has it: an `agente` that could read its own refusals would learn where the wall is and adjust the next attempt.

### The security posture

- The environment has a **security grade**, from `F` to `S`, and it exists for one thing: making the person see the price of what they build and improve their environment. It is not a padlock and it blocks nothing.

- **The grade is per function, and the environment's is the weakest link.** Each graded function — where the Access Phrase lives, exposure, the second factor of whoever comes in, the scope of the service credentials, what Bill itself carries, the plugins, the risk threshold — carries its own grade, and for the environment to be `S` all of them must be `S`. An environment with a bad function cannot call itself good, and the screen always names **which functions are stopping it from rising**.

- **The grade measures what is configured and what you declared, never the truth.** Nobody checks whether you read what a plugin does. That is not a defect: it is the only possible format, and that is why the grade presents itself as "this is what your environment declares", not as "you are safe".

- **Every security impasse is resolved by offering the options and letting the person accept their own security.** The grade informs the price; whoever decides is whoever will live with it. Autonomy is also knowing the security you want for yourself.

- What Bill does **not** measure, it says: whether there is no backup of the folder, whether the machine has no password, whether the phone has no lock — Bill does not know, and prefers to say so rather than invent a letter.

### Internationalization

- Except for the root door, every document in this repository lives in the **folder of its language**, in the POSIX format (`pt_BR`, `en_US`), aligned with the `i18n` module — it is not BCP 47. The root door is a `README.md` outside the folders, and it has no text beyond the title, the links to the versions in each language, and a short note in `en_US` addressed to LLM agents: that they read in the language that suits their model best, that when in doubt they read in English, and that the English track uses the market's terms and concepts on purpose, so that a name means the same thing here and out there.

- The documents live in `docs/`, **one folder per language**, and each document has its pair in the other language's folder, under the same name. **The name does not repeat the language the folder already says**, and the names are lowercase — only the `README` stays uppercase, for being the name the world already knows.

- **The two languages always change together**, and the approval of a commit covers the pair. `pt_BR` is the source language; where the two diverge, `pt_BR` rules.

- A **working document** lives in the folder of its language and **with no pair**: `docs/en_US/backlog.md` is for the agent, changes every day, and translating what changes every day is work nobody reads.

- A **gate in the suite** affirms what that rule promises: the folder of each document, the existence of the pair, the same heading structure in both, and the spelling — both languages go through the repository's checker, and whatever it ignores stays in a versioned list, one per language. Grammar stays with the human reading.

- All code, including comments, object keys, variables, methods and file names, will be in American English (`en_US`). In general, code files are not meant to be read by end users, only audited by developers. So it is more advantageous to keep the base in English for the LLM's processing. This rule holds for what is versioned in the repository; it does not hold for the files Bill generates in the Working Folder.

- The whole interface follows `i18n`. No string is saved directly in the code, be it backend or frontend — `cli`, WebApp and Wizard. The source of truth is the `i18n` module, which organizes the texts into large blocks, avoiding a gigantic `pt_BR.json` that the LLM has to read all the time. The blocks are packed into the binary; what stays in the Working Folder is only the active language, in `App/i18n/active`.

- By default the LLM should generate texts in order to populate `i18n` in `pt_BR` originally and `en_US` as a translation. A key missing in the active language falls back to the source and then to itself, so the gap is visible instead of silent. The key is a **stable id**, never the English sentence: renaming a text must not rename a key. And the suite affirms that both languages carry exactly the same keys, so that a lagging translation is a failing test instead of a surprise.

- On the `cli`, messages and help always come out through `i18n`. The command `bill lang pt_BR --include-subcommands` extends the translation to the subcommand names, which is not usual, and that is why it stays optional. And `bill lang pt_BR --include-app-folders` answers the question the language change would ask BEFORE it is asked: the person's folders are renamed in the same run, with no terminal to consult — the flag is the person saying yes, and nothing moves without an answer or a typed flag. Language resolution is `$BILL_LANG` → `App/i18n/active` → the system locale → `en_US`, and every surface reports where it came from.

### Code and delivery

- Bill is written in Python, and the version it demands lives in `pyproject.toml`, at `requires-python`. Its whole code style is based on `PEP 8`. It is delivered as **two artifacts** — `bill`, which is the folder and the app, and `bill-deploy`, which is §7 — for Windows, Linux and Mac. Its versioning is SemVer, and both carry that number: there is one release, and it publishes both files — on Windows they come out as `bill.exe` and `bill-deploy.exe`, on the others as `bill` and `bill-deploy`. Whoever uses the container path needs both; whoever stays on the hosted one needs `bill` alone.

- `bill` carries **Caddy** inside itself. Caddy is a single static binary, and on the hosted path it is the one that terminates TLS and publishes Bill; on the container path it runs as a container, for the isolation. There is no release variant: one release only, publishing the two artifacts, and the disk cost is accepted in exchange for that simplicity. Since Caddy goes inside `bill`, its version is `bill`'s — there is no separate pin for it.

- Updating is replacing the binaries. Since `bill-deploy` carries the manifest of pinned images, on bringing the environment up after the swap it re-checks the service images and re-pins whatever is out of date — the pin only moves forward and never backward. An instance ahead of the binary's pin **warns and proceeds**: it is not downgraded. Keeping everything up to date, and without a security failure, is my management, not the binary's.

- Every update that changes structure brings its **migration**, and it runs on the first start after the binary is replaced. The folder knows how far it has migrated, and that stamp lives in `App/` — along with the rest of what Bill writes — never inside the published declaration. The declaration remains pure data, which you edit; what the two authors sign stays separate.

- A migration **handles its own impact and decides what to do with it**. Naming a folder moves a path, and what a person points at from outside — a vault of another tool, a copy script — is what breaks later, when that other thing is opened. What touches the person's own folders therefore asks before it moves and says what breaks; what touches only Bill's own folder does not ask, because there is nothing outside to break.

- The migration **never overwrites what already exists**: it adds what is missing and reports what it skipped. In a collision, your edit rules, and Bill warns instead of choosing for you — the same choice as the image pin. And a published migration **is not edited**: folders have already run it, and a fix becomes the next migration.

- Comments in the code explain only what the code does not say by itself: why that piece is necessary and, when it is not obvious, what it does. For history, we use `git`. There is no need to note dates of decisions. See, the code must speak for itself (as [chess speaks for itself](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). If we need kilos of comments, maybe it is not so well written after all.

- **The folders a person opens answer in the person's language, and they are capitalized.** `Tabelas/`, `Arquivos/`, `Projetos/`, `App/`, `Compartilhada/` and `Harness/` in `pt_BR`; `Tables/`, `Files/`, `Projects/`, `App/`, `Shared/` and `Harness/` in `en_US`. The name on disk is the **face**; the machine reads the **internal name** — `data`, `prose`, `projects`, `app`, `shared`, `harness` —, declared in one place and resolved through it: a localized name is a declaration, never an `if` in the code that acts, and the declaration a table publishes cites the internal name, never the face. Two folders are the exception, and both are deliberate: `App/` does not follow the language, because the language is recorded inside it, and `Harness/` does not, because `pt_BR` took the word whole — both languages spell it the same way.

- **Changing the language renames the folders, and the rename is offered and never automatic.** Bill says every implication before doing it — what breaks outside the folder first of all, because a vault another tool points at is the thing the person does not see break until later. Whoever declines keeps the name they had: Bill reads every spelling the product has given a folder, and says what that costs.

- The binary lives in the folder and that folder belongs to the binary. It is the Working Folder. If you open the binary inside the `Downloads` folder, the `Downloads` folder is its own. On the first load you will be warned that: "Bill was opened in the folder <folder>. Since there is no `App/settings.json` file here, this is understood to be a new Working Folder. Do you confirm that Bill may use this folder? Using an empty folder, anywhere on your computer, is recommended. Cancel and move the file to another folder if you disagree.". Or something of the sort.

- The backup of the Working Folder is Bill's promise: **the copied folder is enough for everything to work again**, with no binary swap in between. That is why nothing regenerates on its own — neither what was extracted, nor what was downloaded — and the only exception is what is platform-specific: a folder that changes operating system re-extracts what no longer serves. Everything Bill writes lives in `App/`, in a visible folder precisely so that nobody mistakes it for junk: adjustments, active language, counters, migration stamp, plugin state, what was extracted to run, cache and the state of the services.

- Bill **has no watchdog and does not propose to have one**. It is aware that everything can be modified from outside, and if the person knows how to modify it, let them: what it does is measure what it finds and say what that costs, never police the folder.

- With no terminal to ask, there is no first run: Bill exits with code `1` instead of assuming a folder. And declining creates nothing — Bill says where to move the binary and exits without an error, because declining is not an error.

### Privilege

- Bill, by default, is architected to run without administration permissions (i.e. it does not use `root` or `Administrator`). However, building the environment of §7 inevitably demands elevation at some point. In those cases privilege elevation will happen through an explicit request, with the reason on display.

- The closed list of what demands elevation is not written before the function: it is born with the implementation that asks for it. Each item that enters it is a security decision and passes through this section.

- **The list, so far: the low-port rule, and only it — and `bill-deploy` is the one that asks.** §7a's `dnsmasq` publishes DNS on `127.0.0.1:53`, and a machine that ships the kernel's `net.ipv4.ip_unprivileged_port_start` — every Linux does — refuses that bind to a user process. `bill-deploy` asks, with the reason and the exact command on display, and what it asks for is the NARROWEST thing that works: the floor moves to the lowest port the environment publishes, never to zero. It lasts until the next boot, and the next boot asks again — an explicit request made again, not a permission remembered behind the person's back.

- **`bill` cannot ask, and that is read off the artifact.** The environment of §7 left `bill` whole and became `bill-deploy` (item 27): the elevation MOVED with it and is not duplicated, so what this section promises about running without administration permissions is a property of what the file IS and not of how it behaves. The two artifacts share the folder's STATE and not an API, and the deploy tool is the one that writes it.

### Portability

- Data is always POSIX. `LF` or `/`. Conversions to Windows only for display (as in the Working Folder welcome message, above) or for the `syscalls`.

### External dependency

- Dependencies on packages and images are pinned in version and hashing — be it packages, be it external images.

- Caddy is the declared exception, and not by carelessness: it travels embedded in the binary, so whoever pins it is the binary itself, with Bill's SemVer.

- **Nothing experimental comes in**, not even as a development tool: stable components only. Alpha, beta, release candidate and preview stay out, and whatever the vendor marks as experimental stays out with them — the promise that Bill does not change under your feet cannot rest on a surface whose owner says it will change.

