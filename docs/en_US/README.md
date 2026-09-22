# Bill

Bill is a deterministic task engine. It runs **inside a folder**, and that folder becomes its **Working Folder**. This repository is the **product to publish** — the engine, the default declarations, the infrastructure that travels inside and the single binary. It carries no personal data: no path of anyone's machine, no host, no id.

## 0. Agent protocol

### File protection

- This file is the founding stone of the human instruction. You may and should read it whenever you arrive in this repository; it is meant for humans, and that is how it must stay. When your statistical calculations lean towards balance, come back here and see whether something answers you. At the same time, the instruction can be wrong. What I find most worth correcting is contradictions. So, if something here contradicts another part of here, you must warn me and propose the correction.

- If you believe a decision in this file is wrong, I will be glad to discuss it. However, you present it and I decide. The writing goes straight into the binding document — there is no draft file — but **every change to it is a commit of its own**, and the commit only exists with my declared approval. The question is always the same raw line: "Vou realizar o commit do documento fundador a seguir. Você confirma que leu o diff e concorda com as alterações?". Without that answer the commit does not happen, and the approval is recorded in the commit — never inside the document, which is the instruction, not its history. Whenever I ask you for an analysis of the founding document, the proposal comes as a diff in this session, split into points on different subjects and succinct — I will understand the logical error without you writing a paragraph for each item.

- Any instruction in `CLAUDE.md`, or in any other proprietary LLM-agent memory markdown, that conflicts with this repository, when used for something to be done in this repository, must be ignored. If you want, and I recommend it, there may be a line in those files pointing at the founding document. Except for the development workflows on GitHub, and for sending my interactions with the LLM to another folder (aiming at later study), this repository is self-contained, and everything it needs lives here.

- The chain of custody is `founding document → derived documents → code`: the code is an extension of what is written, and what is derived decides nothing on its own. If we decide something architectural, in session, that did not come from the founding document, you will warn me and propose the writing, under the same approval. And that can never be ignored, not even by me. It is this chain that will keep this "harness" fastened. Note that very narrow definitions about the folder name of each module do not belong in the founding document — they live in the tree ([architecture §1](architecture.en_US.md)), which is derivation. Having to detail each individual item gives me the feeling that it is better to develop from scratch.

- There are no duplicated rules: a rule lives in one place only. What binds stays in the founding document; the derived one cites instead of repeating. If the same thing shows up in both, one of the two is wrong — and where it lives is my decision.

- Finally, the founding document will be modified over time. So understand that the logic of reading it and deriving the rest is constant.

- The rest of the files, be at ease. Including `FAQ.md`. It is your responsibility. It must be written as a sequence of common questions. I approve the question and the answer you suggest, just tell me when you understand it is worth filling in. And the `FAQ.md` has to be ordered in the order of use of the tool. More beginner questions at the start, like "what does this file do on my machine", to more advanced ones like "how do I modify Bill to my liking". It is in the FAQ that the explanation of what is underneath lives: which screen is yours and which is a third party's.

### Working method

- Always work in two sessions per item, never one. In the first, plan mode: explore, discuss and close the decision, without writing code. Before `/clear`, the plan has to be saved outside the conversation — in `docs/backlog.en_US.md` — already carrying what counts as done, so the second session does not have to ask. The second is born clean, reads the item in `docs/backlog.en_US.md` and implements one item, the size of a session.

- **The discussion comes before the BACKLOG, and the implementation always comes out of the BACKLOG.** A decision only enters the list once it is settled, and nothing is implemented that is not in it. In a long discussion, the implications come **one at a time**, and whatever closes is written down and committed on the spot — what is decided cannot live only in the conversation, which dies. **The simple answer to a question is the approval**: if I proposed something and you answered, I do not ask you again whether it is approved.

- When I tell you I am going to clear the session, generate **at once** the recommended start of the next one, in italics, ready for me to copy and modify as I decide, with this raw line before it: "Prompt recomendado para a próxima sessão. Fique à vontade para utilizar ou não.". It says which item, where it is, what counts as done and what the session needs to know before writing the first line.

- Never dump a large file or output into the context: filter it, cut it or delegate it to a subagent and bring back only the conclusion; do not re-read what is already in the conversation, do not repeat what has already been said and do not spend a turn for nothing — every turn resends everything. And where information is missing to decide, ask before acting, with the cost of each option on display: what is not authorized does not happen.

## 1. Origin [context]

### Introduction

Bill is software written entirely by an LLM. The first version of this document was written by me — it is in the git history, which is where the Manifesto lives, the seed of this repository — and from then on whoever modified it was the LLM, as it found contradictions or as we decided new things; every change passed through my approval (§0). The _ghostwriter_ of the PoC is Claude Code + DeepSeek Flash version 4, and from the start of the final development of the project, version 4.1. The choice is deliberate: first, the price. Second, if my data is going to be used for training, let it be for something that comes back as open weights to the community. I think the math is simple. It is also an attempt to prove that we already have enough LLM. Maybe then they will stop once and for all this endless race for an AGI.

Bill is software thought out for me. The fruit of a few weeks of near-burnout focus on LLMs and the attempt to control the uncontrollable. Between studies of harnesses aimed at security, I tested architectural views of software or themes based on old social networks directly in a program I nicknamed `Bill`.

This document aims to be an attempt to make the LLM agent understand the conceptual origin of Bill, avoiding the Poisoned Tree Fruit Theory, where errors pile up and the harness that was created no longer makes any sense after a few billion tokens.

Beyond that, it aims to be extremely architectural. If you understand that the "harnesses" of this architecture are not good enough, maybe I lack knowledge. Post an issue, I will be glad to learn!

### The name

Bill is a name that appears in my head when I read the word bootstrap. The exact reason, I cannot say. But I like the word bootstrap very much.

The history is far too interesting. "To pull oneself up by one's bootstraps" is an English phrase from the early 19th century, initially treated as a sarcastic joke because of the impossibility of lifting oneself (from the air or from the water, for example) by one's own bootstraps. Ironically, that is what our devices do (the famous _boot_). Computers and smartphones have a standard piece of code executed when the device is turned on. It is what loads the operating system you know (Windows or Linux). Bill has this purpose of being a _bootstrap_ for what it sets out to be. Right now I am doing that bootstrap. Bill was born in a chaos while I was studying LLM harnesses and thought I had solved all the problems of the world. Now I am migrating what I developed in a rush into the format to be published. Very much in the mold of [Linux From Scratch](https://www.linuxfromscratch.org/) (which I strongly recommend for learning Linux).

Besides that, a person I know once said that it seems every waiter in western films is called Bill. We laughed a lot, but I believe there is no statistical basis for it. Either way, I like to think I am saying "Hey, Bill. Fill my glass.". With a country accent, or just a Belo Horizonte one.

## 2. Purposes and limits [context]

### What it sets out to do

The idea of Bill is to be a deterministic task engine, usable by a person, by a program or by an LLM. I like machines doing boring things for me. I like ease of access with security. I like Technological Autonomy. And I do not want to spend time developing this. And I like spending very little money. Here I accept spending money in pursuit of that goal, aiming at not needing the massive LLMs again down the line.

But beyond that, Bill is a minimalist working environment — minimum to be **functional**, not minimum to be **aesthetic**; the [themes](#design-system-and-themes) are here for that. "I do not need much to be productive in a technological environment". That is a manifesto in itself: it is possible to be productive with a binary and a folder. The support — the supporting infrastructure (§7) — stays outside the minimum: it comes in when I want it, and its absence takes no functionality away from Bill. Several extensions of Bill will live as something of mine, initially. Sending my library of finished games to rawg using the Steam and Heroic bases does not fit in the default part of Bill. And opening the possibility of community extensions, without curation, with all the risk of Supply Chain attacks, is complicated. That is why Bill is born as it is, analyzing functionality by functionality whether it fits here.

### Does Bill reinvent the wheel?

Yes, it does. There are many more advanced applications for specific parts of Bill. If you understand that your Project cannot be managed here, and that you need far more functions, I understand you, and unfortunately Bill is not for you. But for me it is more than enough. At first I had defined that tasks were not deleted. They had to be cancelled, to keep history. I find that valid, and the function exists. But if I want to delete, I can. More details on [tables](#tables) below. There are tools like Obsidian and AnyType for files and structured data. Those tools are fantastic and I do not want to replace them.

### Where to run Bill

The idea is for Bill to run on a machine. A Turing-compatible one. It can be your desktop, your notebook, your NAS, a VPS. I would like it to be light — light in what the binary demands from the machine, not in the size of the artifact, which carries the interpreter and the libraries packed in. But I am not in the mood to learn Go or Rust. So Python it is. "Everybody" knows Python. And if an ESP32 runs Micropython, it is because I can aim far here.

Bill has two paths of use, and both are supported: the **hosted** one, where it is the binary and the folder, and the **container** one, where it builds an environment of services. The choice belongs to the person, and they can change their mind later; what each path guarantees, and what it does not, is in [§6](#6-the-two-paths-of-use-normative).

## 3. Rules [normative]

### Security

- Every security decision of the application lives in this file, and this section is their record. No security decision is taken without discussion, and none is decided outside here: the other sections describe operation and detail what is recorded below, but they do not decide security on their own. If it is not recorded here, it does not exist.

- Isolation belongs to the container path. On the hosted path Bill is a process on the machine, with no container around it, and that is declared — there is no promise of containing the blast radius of a compromise. What the hosted path offers in exchange is listening only on the local loop by default, and demanding authentication and TLS to leave it.

- Decisions in force. The line is the decision; the detail lives where the link points:
  - Without authentication, Bill listens only on `127.0.0.1`; exposed demands authentication — [Access and exposure](#access-and-exposure).
  - Exposed demands TLS, and TLS only exists with Caddy: `bill webapp` without the flag is HTTP on the local loop — [Access and exposure](#access-and-exposure).
  - Bill has an authenticator of its own, with four ways in, all of them ending at an actor: local Forms, Basic, machine credential and the identity the gate asserts — [Interfaces](#5-interfaces-normative), [Tables](#tables).
  - The actor's credential lives hashed in its own row, with `libsodium`; Basic and Forms are the **same** credential, and what separates them is the transport — [Tables](#tables).
  - No secret lives in `settings.json`: it holds permission and adjustment, never a credential — [General settings](#general-settings).
  - Every function of the core API is protected by RBAC; the permission is `object:action`, a role is a set of permissions, and a machine credential has a declared role — [Tables](#tables).
  - The first admin is born on the first start, with a terminal in front; with no actor at all Bill does not expose — [Interfaces](#5-interfaces-normative).
  - Role and permission are a WebApp screen, and only an admin touches them — [Interfaces](#5-interfaces-normative).
  - **Installing a service is the Wizard's and only the Wizard's** — [Interfaces](#5-interfaces-normative).
  - A machine secret is stored hashed, with a role; a secret Bill **uses**, such as a service credential, is stored encrypted in the `secret` table — [Secret management](#secret-management).
  - Bill authenticates to the services instead of taking advantage of being on the same machine: an administrative credential exists where it is necessary, and it counts in the posture — [The security posture](#the-security-posture).
  - A service that talks to Bill gets a delimited scope — least privilege: the compromise of a service reaches its function and nothing else — [Container path](#7-container-path-the-steps-normative).
  - Identity arriving through the gate is only valid with the gate secret: Bill draws a secret per installation, writes it into the Caddyfile it generates itself, and refuses identity without it — [Install the identity provider as a container](#b-install-the-identity-provider-as-a-container-required).
  - Forms stays on until Authelia is proven to work in front of Bill; the switch is a set that commits or rolls back — [The switch between paths](#the-switch-between-paths).
  - A fallen gate closes Bill: it says the authentication portal is unavailable, and the way back to Forms mode is the Wizard or the `cli`, both local — [The switch between paths](#the-switch-between-paths).
  - Every action leaves one line in the `audit` table, and a refusal is one of them — [The audit](#the-audit).
  - What is proved is stored hashed; what Bill uses is stored encrypted — [Tables](#tables).
  - The persistent state of every service lives in the Working Folder; a service whose state does not fit there does not come in — [Container path](#7-container-path-the-steps-normative).
  - **No extension executes code today.** The first class is pure data, and code is the last option — [Extensions](#8-extensions-and-plugins-normative).
  - The theme of the authentication portal is not Bill's: it stays as neutral as possible, and the `FAQ.md` explains what is underneath — [Interfaces](#5-interfaces-normative).
  - Authenticator, WebApp, checker, notifier and VPN run in isolated containers on the container path — [Container path](#7-container-path-the-steps-normative).
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

- Except for the root door, every document in this repository carries the **language in its own name**, in the POSIX format (`pt_BR`, `en_US`), aligned with the `i18n` module — it is not BCP 47. The root door is a `README.md` without a language, and it has no text beyond the title, the links to the versions in each language, and a short note in `en_US` addressed to LLM agents: that they read in the language that suits their model best, that when in doubt they read in English, and that the English track uses the market's terms and concepts on purpose, so that a name means the same thing here and out there.

- The documents live in `docs/`, one file per language, and each one links its siblings in the other languages. **No English document exists without the language suffix**, and the names are lowercase — only the `README` stays uppercase, for being the name the world already knows.

- **The two languages always change together**, and the approval of a commit covers the pair. `pt_BR` is the source language; where the two diverge, `pt_BR` rules.

- A **working document** lives in the same folder, in `en_US` and **with no pair**: `docs/backlog.en_US.md` is for the agent, changes every day, and translating what changes every day is work nobody reads.

- A **gate in the suite** affirms what that rule promises: the name of each document, the existence of the pair, the same heading structure in both, and the spelling — both languages go through the repository's checker, and whatever it ignores stays in a versioned list, one per language. Grammar stays with the human reading.

- All code, including comments, object keys, variables, methods and file names, will be in American English (`en_US`). In general, code files are not meant to be read by end users, only audited by developers. So it is more advantageous to keep the base in English for the LLM's processing. This rule holds for what is versioned in the repository; it does not hold for the files Bill generates in the Working Folder.

- The whole interface follows `i18n`. No string is saved directly in the code, be it backend or frontend — `cli`, WebApp and Wizard. The source of truth is the `i18n` module, which organizes the texts into large blocks, avoiding a gigantic `pt_BR.json` that the LLM has to read all the time. The blocks are packed into the binary; what stays in the Working Folder is only the active language, in `app/i18n/active`.

- By default the LLM should generate texts in order to populate `i18n` in `pt_BR` originally and `en_US` as a translation. A key missing in the active language falls back to the source and then to itself, so the gap is visible instead of silent. The key is a **stable id**, never the English sentence: renaming a text must not rename a key. And the suite affirms that both languages carry exactly the same keys, so that a lagging translation is a failing test instead of a surprise.

- On the `cli`, messages and help always come out through `i18n`. The command `bill lang pt_BR --include-subcommands` extends the translation to the subcommand names, which is not usual, and that is why it stays optional. Language resolution is `$BILL_LANG` → `app/i18n/active` → the system locale → `en_US`, and every surface reports where it came from.

### Code and delivery

- Bill is written in `Python 3.14`. Its whole code style is based on `PEP 8`. The idea is for it to be delivered as a single binary: Windows, Linux and Mac. Its versioning is SemVer, and the binary carries that number — on Windows it comes out as `bill.exe`, on the others as `bill`.

- The binary carries **Caddy** inside itself. Caddy is a single static binary, and on the hosted path it is the one that terminates TLS and publishes Bill; on the container path it runs as a container, for the isolation. There is no release variant: one artifact only, and the disk cost is accepted in exchange for that simplicity. Since Caddy goes inside the binary, its version is the binary's — there is no separate pin for it.

- Updating is replacing the binary. Since it carries the manifest of pinned images, on starting after the swap it re-checks the service images and re-pins whatever is out of date — the pin only moves forward and never backward. An instance ahead of the binary's pin **warns and proceeds**: it is not downgraded. Keeping everything up to date, and without a security failure, is my management, not the binary's.

- Every update that changes structure brings its **migration**, and it runs on the first start after the binary is replaced. The folder knows how far it has migrated, and that stamp lives in `app/` — along with the rest of what Bill writes — never inside the published declaration. The declaration remains pure data, which you edit; what the two authors sign stays separate.

- The migration **never overwrites what already exists**: it adds what is missing and reports what it skipped. In a collision, your edit rules, and Bill warns instead of choosing for you — the same choice as the image pin. And a published migration **is not edited**: folders have already run it, and a fix becomes the next migration.

- Comments in the code explain only what the code does not say by itself: why that piece is necessary and, when it is not obvious, what it does. For history, we use `git`. There is no need to note dates of decisions. See, the code must speak for itself (as [chess speaks for itself](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). If we need kilos of comments, maybe it is not so well written after all.

- The binary lives in the folder and that folder belongs to the binary. It is the Working Folder. If you open the binary inside the `Downloads` folder, the `Downloads` folder is its own. On the first load you will be warned that: "Bill was opened in the folder <folder>. Since there is no `app/settings.json` file here, this is understood to be a new Working Folder. Do you confirm that Bill may use this folder? Using an empty folder, anywhere on your computer, is recommended. Cancel and move the file to another folder if you disagree.". Or something of the sort.

- The backup of the Working Folder is Bill's promise: **the copied folder is enough for everything to work again**, with no binary swap in between. That is why nothing regenerates on its own — neither what was extracted, nor what was downloaded — and the only exception is what is platform-specific: a folder that changes operating system re-extracts what no longer serves. Everything Bill writes lives in `app/`, in a visible folder precisely so that nobody mistakes it for junk: adjustments, active language, counters, migration stamp, plugin state, what was extracted to run, cache and the state of the services.

- Bill **has no watchdog and does not propose to have one**. It is aware that everything can be modified from outside, and if the person knows how to modify it, let them: what it does is measure what it finds and say what that costs, never police the folder.

- With no terminal to ask, there is no first run: Bill exits with code `1` instead of assuming a folder. And declining creates nothing — Bill says where to move the binary and exits without an error, because declining is not an error.

### Privilege

- Bill, by default, is architected to run without administration permissions (i.e. it does not use `root` or `Administrator`). However, building the environment of §7 inevitably demands elevation at some point. In those cases privilege elevation will happen through an explicit request, with the reason on display.

- The closed list of what demands elevation is not written before the function: it is born with the implementation that asks for it. Each item that enters it is a security decision and passes through this section.

### Portability

- Data is always POSIX. `LF` or `/`. Conversions to Windows only for display (as in the Working Folder welcome message, above) or for the `syscalls`.

### External dependency

- Dependencies on packages and images are pinned in version and hashing — be it packages, be it external images.

- Caddy is the declared exception, and not by carelessness: it travels embedded in the binary, so whoever pins it is the binary itself, with Bill's SemVer.

## 4. Architecture [normative]

### Layer separation

- Bill is structured in layers. `core` handles every rule of the application. It is not a monolithic block: it is broken into modules and files according to the subject. But everything passes through it. No layer outside `core` resolves a path of its own.

- `ui` is a form of layer, but it has more. Bill is born with three surfaces: `cli`, WebApp and Wizard. All of them are only different ways of interacting with `core`. Not everything done by the `cli` is available in the WebApp. But everything in the `WebApp + Wizard` is available in the cli.

- Another very important layer is `data`. This layer is responsible for accessing the tables. Structured data saved as `.jsonl` inside the `./data` folder. The `./data` folder is created automatically on the first run, with the system tables in force.

- Bill also supports managing miscellaneous files. It is the `prose` layer. Any file that is not structured data is this layer's business. The `./prose` folder, also created on the first run, comes with a welcome file generated by `i18n` in the active language chosen on the first run (`Bem-vindo.md` in `pt_BR`, `Welcome.md` in `en_US`), to make the next steps easier.

- External services are handled by the `services` layer. This is so that the layer is as tool-agnostic as possible: the **service** has a canonical name and the **tool** that fulfils it is replaceable. It is in this layer that the services part of the product lives — every configured service lives here, with its state in the folder.

- Secrets are managed by the `encryption` layer.

- Natural language interpretation is the `nlu` layer: it turns a sentence into an action **proposal**, and nothing else. It does not write, does not decide and has no ceiling of its own — whoever validates and writes is `core`.

- The security posture is the `posture` layer: it measures what is configured, adds up the per-function grades by the weakest link and answers the screen and the API. It measures; it does not block.

### Tables

- Bill has an engine of its own for managing structured data. The term Table is used here, or `table` internally. The identity of the table is an id, and the id is singular (`task`, `project`, `reminder`, `secret`, `actor`, `role`, `audit`): it is what names the table everywhere, including in the command (`bill task list`) and in the schema. The file of rows is the one that goes in the plural. So `data/tasks.jsonl` is the table itself and `data/schema/task.json` is its schema.

- The tables `task`, `project`, `reminder`, `secret`, `actor`, `role` and `audit` are system defaults. They serve to deliver an inherent functionality. System tables are not deletable, and **the deletability of a row is declared in the table's schema**: `audit` declares that no row of its own is erased.

- User tables allow full CRUD of the table itself.

- The table schema has many features, such as default fields in the display and default order in the display of tables. The display labels it carries are `i18n` keys, never the final text. The id counter does not live in the schema: it counts what happened in this folder, and the schema is published — so it lives in `app/counters.json`, and it is written before the row, because an id handed out is spent even if the write that followed failed.

- The schema declares **field types**, and each type has a fixed rule, with no choice per field:
  - **hashed** — stores the result of a secure derivation, made with `libsodium`; the value does not come back on a read, it is only compared.
  - **instant** — a point in time: ISO, always UTC, always with milliseconds (`2026-09-22T13:04:07.123Z`). Locality is detected on display, never stored.
  - **day** — a calendar day, with no time and no timezone, resolved by the locality of whoever writes. "Today" is your today.
  - The common types — text, number, date, reference, enumeration — as they always were.

- **What is proved is stored hashed; what Bill uses is stored encrypted.** `secret` is of the second kind, `actor` is of the first.

- **Whoever acts is an actor**, and every actor is a row of the `actor` table, with the field `type` holding `person`, `engine` or `agent`. The row carries the identity, the role and the credential in the hashed field. The engine acts in what belongs to the engine; the `agent` is whoever uses Bill without being a person, and it is the one with a ceiling of its own — whoever types a sentence is the person, and the via is `nlu`.

- The permission catalogue is declared in the code, and it is not loose data: the permission has the form `object:action`, the objects and the actions are a closed list, and the display labels come from `i18n` like everything else. The objects go beyond the tables: the settings, the services, the plugins and the interpreter's vocabulary are also objects, with permissions of their own. A role is a row of the `role` table with a set of permissions, and the `actor` table points at the role. A role naming a permission that does not exist does not bring Bill down: it warns, and the warning is what gets read.

### Secret management

- To perform certain actions, such as accessing external service APIs, Bill needs access to secrets. Every secret Bill **stores** is written into the `secret` table — a secret that is only compared, such as an actor's credential, lives hashed in its own row (§4, Tables). There are the metadata and the secret itself, saved in encrypted form.

- Bill's encryption starts from an **Access Phrase**, which is what the person knows and types: at least 16 characters, and it is a phrase. "Mariazinha comeu todo o pudim", in lowercase and without spaces, is safer than `Mariazinha@123`. From it the **Bill Key** is derived, and from it the **derived keys**, one per service or purpose. The Bill Key recovers any lost derived key.

- It is recommended to keep the Access Phrase outside the machine, in a safe place. Printing it and storing it among personal documents that are hard to reach, for example.

- In cryptography there is no magic. Either you type the Access Phrase every time Bill needs a secret, or you type it once and it holds while Bill is up, or Bill stores what it needs to unlock itself. **The choice is graded, and the security grade says the price of each:** typing when Bill starts is `S`; keeping it unlocked in the system user's folder (`~/.bill/` on Unix, `%APPDATA%` on Windows) is `A`; keeping it inside the Working Folder is `B` — and the last one is allowed, because then the folder backup carries everything.

- Bill runs on its own when it needs to: a scheduled job does not ask for a password on every execution. What it does not do is choose for you where the key lives.

- The verification of an incoming credential does **not** depend on the Access Phrase, and that is on purpose: otherwise Bill only starts when somebody types the phrase. That is why what is compared is hashed, and that is why the credential does not live in `secret`.

### General settings

- Bill's settings live inside `app/settings.json`, inside the working folder. There live properties in key-value format. `i18n` does not live here: the translation blocks are packed into the binary and the active language lives in `app/i18n/active`.

- **The settings are reachable through the core API** (`setting:read` and `setting:edit` are permissions), because that is where everything that acts passes through — including the reading of the **risk threshold** that was in force at the instant a demand ran, which is what the audit line records.

- No secret lives in `settings.json`. It holds permission and adjustment — such as the permission for an actor to come in through Basic, or the risk threshold — never the credential itself.

- The Tkinter Wizard displays the installation possibilities of the environment. With advanced mode enabled, the Wizard presents the rendering of the settings file, allowing any of them to be modified. It follows the design choice of some tools, such as VS Code, which have the base of the settings in JSON but allow the change in the UI.

- Each service may have persisted data. In that case, it lives in `app/services/<service>`, such as `app/services/vpn` or `app/services/spelling-checker`. The service name is canonical and does not change with the tool that fulfils it: `spelling-checker` is the service, LanguageTool is who fulfils it today (§7d), and whatever replaces it one day renames neither folders nor keys. What is a display label is an `i18n` key.

- That folder is not a convenience, it is a condition of entry: a service only enters §7 if its persistent state fits in there. A service that keeps its life in some volume nobody copies makes the folder backup lie.

## 5. Interfaces [normative]

### Command line (`cli`), web application (WebApp) and Tkinter interface (Wizard)

- When opening Bill, whether on the command line or straight through the graphical interface, we have the "Control Panel". It is a Tkinter interface, the Wizard. Here the "guts" of Bill's environment are configured, its first layer being the web application.

- Calling the binary straight from the terminal loads the Tkinter interface. Any other parameter passed makes the program act as a `cli`. `bill ajuda`, or `bill help`, shows how to use the cli completely. You can change it in the settings so that the command `bill` opens `bill help` instead of Tkinter.

- The command line works for everything in Bill. Any functionality it exposes, whether in the REST API (used by the WebApp frontend) or in the WebApp itself, is reachable from the command line.

- The Wizard is a screen that allows more critical configurations of Bill that I did not want to leave available on the network. It has roles that do not move: the **first start**, where the Working Folder is confirmed and the first admin is created; the **installation of services**, and only it installs; the **return to Forms mode**, when the authentication gate falls; and the management of the main keys in advanced mode.

- The `cli` runs only locally, except when it is communicating with external APIs for the due configuration. And it is it, or the Wizard, that returns Bill to Forms mode: both are local surfaces, and that is why the return exists.

- Role and permission are **not** the Wizard's business: that is a WebApp screen, and the friction of doing admin there does not pay off. The Wizard keeps what only it can do.

### The interpretation layer

- Natural language comes in as a **resource** of the WebApp and the `cli`, and not as a fourth surface: nothing becomes possible merely by speaking. What the person types becomes a proposal, and what they can propose is what they can already do.

- **The interpreter is deterministic.** There is no LLM at run time: the LLM helps to **write** the vocabulary, and what runs is code with data. That is what cuts the cord with the third-party token, and that is why Bill needs no video card to understand a sentence.

- What the interpreter consults is the **vocabulary**, per language, packed into the product alongside the `i18n` blocks, because translating vocabulary and translating text are the same task. The vocabulary is dumb data: pairs of expression → canonical expression, with language and region, and nothing conditional. What depends on context is grammar, and grammar is the product's code.

- **The interpreter proposes; the core validates and writes.** One action per request while there is no batch API; the day there is one, the batch is an action, with a permission of its own. The unit of everything is the operation of the core API, and the REST API is one of the doors to it.

- **The access ceiling is what the actor may do; the risk threshold is what it may do without asking.** Every demand has a **risk**, measured by the core from what the product declares per action and per argument — never by the interpreter, because whoever asks does not assess their own risk. The **threshold** lives in the settings: below it the action runs, above it the person approves. The risk of each action is adjustable in `settings.json`, and that of an extension is accepted at the moment of installing.

- The approval arrives by notification, and the notification is **a doorbell, not a key**: the tap opens Bill and the approval happens inside it, with the session in force. The credential does not live in the notification center. A job that runs on its own can be approved this way, and the approval is a line in the audit, separate from the demand that waited.

- **The agent function is switchable**, and switching it off is taking the interpreter out of the core API: whoever does not want the language layer uses Bill without it and loses nothing beyond it.

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

#### Design System and themes

- The Design System is the LLM's development. Gradual growth of components.

- Theme support is a structural part of Bill. Several themes help me test the strength of the Design System over different views. At the same time they make me happy to use the system. Theme PRs are welcome, but they are entirely subject to my personal judgement and I will be glad to share my terrible taste if I do not want to accept a PR. But do not be shy!

- The theme holds for the whole WebApp, **the login screen included**: there is no page of Bill that escapes the Design System, and the entrance is the first impression it has to make.

- The Authelia portal is **not** a Bill screen, and there is no way to dress it with the Design System: Authelia accepts a logo, a favicon, translated texts and one of four palettes, and nothing beyond that. So its theme stays as neutral as possible, and the `FAQ.md` says whose screen that is — educating about what the person is actually using is part of the product.

#### Templates

- Bill uses `Vue`. As much as I dislike using many external dependencies because of the Supply Chain risk, and as much as most of that comes from JavaScript libraries, I like `Vue`. I find it a valid loss for the template management it brings. Even though I am not writing that code, it does not please me to see the LLM creating individual JavaScript files for pages. It hurts my legibility and I am very much in favor of good legibility.

#### TypeScript and frameworks

- Bill's WebApp is written in TypeScript and _transpiled_ using `ViteJS`. The TypeScript is well written, respecting modules and domains, making human management easier.

## 6. The two paths of use [normative]

- There are two paths, and both are supported. They differ in what they guarantee, and the difference is declared here so that nobody decides with wrong information.

### Hosted path

- It is Bill and the folder. The binary is opened in the Working Folder, the WebApp comes up through the command, the Wizard opens when there is no parameter, and the `cli` does the rest. There is no container at all, and the person needs neither Podman nor anything beyond the binary.

- **There is no isolation**, and Bill promises none on this path: a compromise of the WebApp is a process compromise on your machine, with access to what your user has. In exchange, the default is not to leave the local loop, and leaving it demands authentication and TLS.

- Leaving the local loop, here, is `bill webapp --include-caddy`: the Caddy that came inside the binary terminates the TLS and publishes Bill. Without the flag, the WebApp serves over HTTP and only on `127.0.0.1`.

- The integrations (§7) can exist without a container: whoever installs the service on their own and points Bill at it uses the service, knowing that the state of that service is no longer Bill's business — and therefore that the folder backup does not cover it. Approving a risky demand, here, happens on the machine itself: the `notifier` service belongs to the container path.

- Exposing Bill on the hosted path with the container path's Authelia is the **advanced mode**, and it is not supported: whoever wants the gate uses the container path.

### Container path

- It is Bill building an environment of services in containers from pinned images (§7). Here there is isolation, and it exists for a specific reason: **containing the blast radius of each service**. A compromise of `ntfy` reaches the notification and nothing else; the checker's reaches the checker. What each service exposes is what it sets out to do, and nothing beyond.

- A service that needs to talk to Bill — and not Bill to the service — has a delimited scope: a credential with a declared role, and only what that role allows. Least privilege, applied. In `ntfy`, that is the per-topic ACL: Bill publishes, the phone reads, and neither token serves for anything else.

- The container path is what sustains the authentication gate (§7b), and it is where Bill comes in as one more app behind it.

### The switch between paths

- Going from one path to the other is a **switch**, and a switch is transactional: Bill executes the set of actions and, if any of them does not end successfully, everything goes back to the previous state. The environment does not stay half done, and what existed before keeps working.

- In the container direction, Forms stays on until Authelia is **proven** to work in front of Bill — it is not "the container came up", it is Bill receiving the identity it expects, through the real path, with the gate secret. Only then does Forms turn off.

- If the gate falls afterwards, with the switch already committed, Bill **closes** and warns: "Portal de autenticação indisponível. Utilize o Wizard para retornar o Bill para modo forms." It does not reopen Forms on its own — reopening on its own would be trading security for convenience, with nobody deciding.

- If Bill finds an infrastructure environment configured in the folder but does not find the environment, it asks: "Foi detectado que você tem um ambiente de infraestrutura configurado nesse ambiente, mas o ambiente de infraestrutura não foi encontrado. Você deseja instalar novamente o Podman/Docker ou restaurar o bill para modo hospedado na máquina?". It is the backup promise showing up on the screen: the folder came back, and what was missing was only the ground.

## 7. Container path: the steps [normative]

### Configuration steps

- The steps below are the container path. They are not a requirement for using Bill: without them, what one has is the hosted path (§6), which is also supported. "Required" here means required for this path.

#### a. Create the container environment (required)

- This is the main switch of the environment. The person needs Podman installed. Bill checks whether it exists and, if it does not, offers the two ways out: install Podman, or continue on the hosted path. It does not install Podman on its own. From there on, Bill orchestrates the environment and the services, which come up as containers from pinned images.

- It is a complex function with a lot of room for error and for a security failure. The security decisions around it are in [Security](#security).

- Podman is the choice for containers. `dnsmasq` and Caddy are the first services. The first to customize the access urls and the second to publish Bill, now in a container, for the isolation.

#### b. Install the identity provider as a container (required)

- Bill has an authenticator of its own, and on the container path it is the gate: an external identity provider, here Authelia, in front of everything. It becomes responsible for the authentication of all the services existing here, and Bill comes in as one more app — not as an exception.

- Authelia speaks **OIDC** with whoever speaks OIDC, and **forward-auth** with whoever does not. Sonarr, Radarr and Prowlarr do not speak OIDC, and it is forward-auth that gives them the same experience: one login at the portal, the cookie holding for all. Bill does not speak OIDC with it either: it comes in through forward-auth, like the others.

- The split is: **who** is an actor belongs to Bill, and **how** it is proved that it is them belongs to Authelia. The `actor` table (§4) holds identity, role and the hashed credential — and on the container path whoever uses the Authelia credential is Authelia.

- What Authelia **is not**: a login provider with Google. It does not play the relying party role, and that is a decision of the project, not configuration. Login with third parties is not part of Bill.

- Here there is no authentication with Bill's face. The portal is Authelia's, and what Bill does is ask it to be as neutral as possible, so as not to look like what it is not (§5).

- What Bill demands from whoever arrives with an identity is the **gate secret**: a value drawn by Bill at installation, written into the Caddyfile it generates itself, attached by Caddy to every request carrying an identity, and refused to whoever does not bring it. It is the M2M between Caddy and Bill's WebApp, and Authelia never sees it.

#### c. Install the WebApp as a container (required)

- The WebApp, the main way of using Bill, is installed as a container. It aims to reduce the blast radius in a compromised web application.

#### d. Install the spelling and grammar checker as a container (optional)

- Bill's default for text correction is LanguageTool, today the tool that fulfils the `spelling-checker` service (§4). It serves to underline errors on the editing screen. Quite useful.

- This is the checker of the **person's text**, at run time. The checker of the repository's documents is another one, and it is a development tool ([architecture §3](architecture.en_US.md)).

#### e. Install a VPN (optional)

- Bill allows configuring a VPN. Here it is relevant, because it allows creating a private network so that multiple devices talk to each other. So if the Bill WebApp runs on your personal machine, it becomes securely reachable from your phone, anywhere. Here I am using Tailscale. It is proprietary, but it avoids needing a server in the cloud. Headscale support in the future.

#### f. Install the notifier as a container (optional)

- With everything configured, the cherry on the cake is `ntfy`, today the tool that fulfils the `notifier` service (§4). The configured reminders can be notified directly as a Push Notification, and it is through it that the approval of a demand that passed the risk threshold arrives.

- This is where the first graded functionality comes in: its levels and what each one costs live in [functionalities](functionalities.en_US.md).

## 8. Extensions and plugins [normative]

- The extension exists to teach Bill, and the first of them is the slang map: it is data that changes by region, by person and by time, and waiting for a release to be understood is too expensive.

- **No extension executes code today.** The first class is **pure data**: a folder with a declaration and the data, with not one executable line. A data plugin has no runtime presence at all — it is not a process, not a reader: whoever reads the sentence is Bill, and the plugin only says how to translate. That is why it does not ask for a read permission; asking would be theatre, and theatre teaches people to click "accept" without reading the next one.

- **The plugin carries a manifest**, and the manifest declares what it does in the environment. The permissions are granular and the person sees what they are installing. The first permission in Bill's history is about what the plugin **alters**: *"Esse plugin pode alterar suas palavras antes de ser analisado pelo motor (core) do Bill."* The sentence of the permission belongs to the **product**, rendered from the internal name in the product's `i18n` — the plugin merely references the id, because a warning written by whoever is being warned is not a warning. The plugin may add a note of authorship, marked as its own.

- **Installing ties a review to a hash.** Bill sees what exists on disk and keeps the state; copying into the folder makes it **see**, and the act of installing is what counts. The plugin's whole folder is hashed, **content only, in canonical order** — no modification time, no permission, no empty folder —, and any altered byte changes the hash, invalidates the review and lowers the grade. The acceptances have to be made again, which closes the classic hole of trusting the author: the thing you approved and the thing that runs afterwards are the same, or Bill knows they are not.

- The way back up the grade is an **explicit review**, in one of three modes: *I read what it does*, *I asked an AI to read what it does*, *I trust whoever made it*. Nobody verifies the declaration — it is the only possible format — and that is why the grade presents itself as a declaration (§3, The security posture).

- The plugin state lives in `app/`, in a file, and not in the tables. Since the folder is the person's, one can edit that state and lie to one's own grade: that is not a flaw in the design, because the hash protects you **from the author**, not the author from you.

- **Code is the last option.** Code that executes is code that is hard to contain, and before it the plan is to deliver extension in much more established forms.

## 9. End-to-end test environment [normative]

- The main test is checking that, with Podman installed, executing Bill's actions works perfectly. That test will happen on Mac, Linux and Windows VMs.

- It is **automated end to end**: no part depends on an eye or a hand on a screen. The script brings up the VM, opens the binary and checks what came back — Podman absent makes Bill offer the two ways out; Podman present brings the environment up with the images at the pin; an instance ahead of the pin warns and proceeds; Bill refuses to go on the network without authentication and goes up with it; the WebApp answers behind the gate; and the Working Folder created on the first run is only what §3 describes.

- The hosted path has a gate of its own, and it is cheap because it depends on neither a VM nor a container: the first start asks for the admin and does not let Bill expose without it; without authentication Bill listens only on `127.0.0.1`; exposing without TLS is refused; the switch to the container rolls back whole when any action does not close; and the fallen gate closes Bill with the sentence on display.

- The interpreter has a ruler of its own, and it runs as a test: sentences that must work, sentences that must be refused, and ambiguous sentences that must be returned as a question. No LLM, no network and no video card.

- The test **is not the criterion of done for each function** — a function is done by what `docs/backlog.en_US.md` says it is. It is the gate of the first publication on GitHub, and from there on.

## 10. Derivation

The tree, the Working Folder and the operation are derivation: they change whenever a folder changes, and so they do not bind. They live in [architecture](architecture.en_US.md), in both languages. The chain is `founding document → derived documents → code` (§0).

## 11. Glossary

Each name has one meaning, and names that would touch each other do not coexist. Whenever I invent a term, it is defined here before being used.

| term | what it is |
|---|---|
| **product** | the published set: this repository, the binary it generates and the declarations that travel inside |
| **binary** | the single file the product publishes |
| **Working Folder** | the folder where the binary was opened and which becomes its own |
| **layer** | each code folder with a single job: `core`, `data`, `prose`, `services`, `encryption`, `nlu`, `posture`, `ui`, `i18n` |
| **surface** | each way for a person to reach the core: `cli`, WebApp and Wizard |
| **service** | the capability, with a canonical name (`spelling-checker`, `identity-provider`) |
| **tool** | whoever fulfils the service today (LanguageTool, Authelia), replaceable without renaming anything |
| **table**, **schema**, **row**, **field** | the pieces of the data engine |
| **hashed field** | a field that stores the derivation and never the value; it is only compared |
| **instant field** | a field of a point in time: ISO, always UTC, with milliseconds |
| **day field** | a field of a calendar day, with no time and no timezone, local on write |
| **actor** | the row of `actor` that acts; **person**, **engine** and **agent** are the types |
| **access ceiling** | the effective limit of the actor; **role** is the row that grants it |
| **audit** | the `audit` table, the log of acts |
| **via** | where the act came in from: `cli`, WebApp, Wizard, `nlu`, engine. Port is the network one, and only that |
| **nlu** | the layer; **interpreter**, whoever does the work inside it; **vocabulary**, the per-language dictionary it consults |
| **interpreter test** | the ruler: what must work, what must be refused, what must be asked back |
| **risk threshold** | the price from which a demand waits for approval; below it, it runs |
| **demand risk** | the price of a demand, measured by the core over the action and the arguments |
| **permission catalogue** | the closed list `object:action` |
| **posture** | the measured security state of the environment: the graded functions and the grade |
| **grade** | the letter of a graded function, from `F` to `S`; the environment's is the weakest link |
| **functionality** | a capability the person recognizes, with levels and dependencies |
| **plugin** / **extension** | what teaches Bill something; today pure data only, with a manifest and a hash |
| **review** | the acceptance of a plugin, tied to the hash, in one of three modes |
| **Access Phrase** | what the person knows and types; from it the **Bill Key** is derived |
| **Bill Key** | the key derived from the Access Phrase; from it the **derived keys** derive, per service |
| **manifesto** | the seed of this repository, visible in the git history; and `manifest.json` is just the file that has that name |
| **pin**, **migration** | stay in English, like the rest of the code: version and hashing fixation, and the structure change that runs on the first start |

## 12. What is not here yet

`docs/backlog.en_US.md` holds what comes next, with what counts as done for each item.

Three debts were born from the decisions of this session, and all three are named so they do not become a surprise:

- **The code.** Nothing that was decided here is built: the actor, the audit, the demand filter, the posture, the interpreter, the plugins. Every one of them has an item in `docs/backlog.en_US.md`.
- **The checker's list.** It was born large — 217 words in Portuguese and 131 in English — and the reason is written in its header: the checker's dictionary comes from subtitle frequencies and gets the formal register wrong, where "seção", "deleção" and "registrar" do not appear. If that list grows on its own, the gate became decoration, and the diff is where one notices.
- **The `FAQ.md`.** It does not exist yet, and it now has work waiting: saying what is underneath — which screen is Bill's and which is a third party's — and that writing well is the best remedy against a misunderstanding of the interpreter.
