# AT

AT is a deterministic task engine. It runs **inside a folder**, and that folder becomes its **Working Folder**. This repository is the **product to publish** — the engine, the default declarations, the infrastructure that travels inside and the two binaries — `at-cli`, which is the folder and the app, and `at-deploy`, which builds the environment of §7. It carries no personal data: no path of anyone's machine, no host, no id.

## 0. Agent protocol

### File protection

- This file is the founding stone of the human instruction. You may and should read it whenever you arrive in this repository; it is meant for humans, and that is how it must stay. When your statistical calculations lean towards balance, come back here and see whether something answers you. At the same time, the instruction can be wrong. What I find most worth correcting is contradictions. So, if something here contradicts another part of here, you must warn me and propose the correction.

- If you believe a decision in this file is wrong, I will be glad to discuss it. However, you present it and I decide. The writing goes straight into the binding document — there is no draft file — but **every change to what is `[normativo]`, wherever it lives, is a commit of its own**, and the commit only exists with my declared approval. The question is always the same raw line: "Vou realizar o commit do `[normativo]` a seguir. Você confirma que leu o diff e concorda com as alterações?". Without that answer the commit does not happen, and the approval is recorded in the commit — never inside the document, which is the instruction, not its history. Whenever I ask you for an analysis of the founding document, the proposal comes as a diff in this session, split into points on different subjects and succinct — I will understand the logical error without you writing a paragraph for each item.

- Any instruction in `CLAUDE.md`, or in any other proprietary LLM-agent memory markdown, that conflicts with this repository, when used for something to be done in this repository, must be ignored. If you want, and I recommend it, there may be a line in those files pointing at the founding document. Except for the development workflows on GitHub, and for sending my interactions with the LLM to another folder (aiming at later study), this repository is self-contained, and everything it needs lives here.

- The chain of custody is `founding document → derived documents → code`: the code is an extension of what is written, and what is derived decides nothing on its own. If we decide something architectural, in session, that did not come from the founding document, you will warn me and propose the writing, under the same approval. And that can never be ignored, not even by me. It is this chain that will keep this "harness" fastened. Note that very narrow definitions about the folder name of each module do not belong in the founding document — they live in the tree ([derivation §1](derivation.md)), which is derivation. Having to detail each individual item gives me the feeling that it is better to develop from scratch.

- There are no duplicated rules: a rule lives in one place only. What binds is what carries `[normativo]`, wherever it lives; the derived one cites instead of repeating. The marker on a level-1 title binds the whole file, and on a section title it binds the section and what lies below it. If the same thing shows up in both, one of the two is wrong — and where it lives is my decision.

- Finally, the founding document will be modified over time. So understand that the logic of reading it and deriving the rest is constant.

- The rest of the files, be at ease. Including `FAQ.md`. It is your responsibility. It must be written as a sequence of common questions. I approve the question and the answer you suggest, just tell me when you understand it is worth filling in. And the `FAQ.md` has to be ordered in the order of use of the tool. More beginner questions at the start, like "what does this file do on my machine", to more advanced ones like "how do I modify AT to my liking". It is in the FAQ that the explanation of what is underneath lives: which screen is yours and which is a third party's.

### Working method

- Always work in two sessions per item, never one. In the first, plan mode: explore, discuss and close the decision, without writing code. Before `/clear`, the plan has to be saved outside the conversation — in `docs/en_US/backlog.md` — already carrying what counts as done, so the second session does not have to ask. The second is born clean, reads the item in `docs/en_US/backlog.md` and implements one item, the size of a session.

- **The discussion comes before the BACKLOG, and the implementation always comes out of the BACKLOG.** A decision only enters the list once it is settled, and nothing is implemented that is not in it. In a long discussion, the implications come **one at a time**, and whatever closes is written down and committed on the spot — what is decided cannot live only in the conversation, which dies. **The simple answer to a question is the approval**: if I proposed something and you answered, I do not ask you again whether it is approved.

- When I tell you I am going to clear the session, generate **at once** the recommended start of the next one, in italics, ready for me to copy and modify as I decide, with this raw line before it: "Prompt recomendado para a próxima sessão. Fique à vontade para utilizar ou não.". It says which item, where it is, what counts as done and what the session needs to know before writing the first line.

- Never dump a large file or output into the context: filter it, cut it or delegate it to a subagent and bring back only the conclusion; do not re-read what is already in the conversation, do not repeat what has already been said and do not spend a turn for nothing — every turn resends everything. And where information is missing to decide, ask before acting, with the cost of each option on display: what is not authorized does not happen.

## 1. Origin [context]

### Introduction

AT is software written entirely by an LLM. The first version of this document was written by me — it is in the git history, which is where the Manifesto lives, the seed of this repository — and from then on whoever modified it was the LLM, as it found contradictions or as we decided new things; every change passed through my approval (§0). The _ghostwriter_ of the PoC is Claude Code + DeepSeek Flash version 4, and from the start of the final development of the project, version 4.1. The choice is deliberate: first, the price. Second, if my data is going to be used for training, let it be for something that comes back as open weights to the community. I think the math is simple. It is also an attempt to prove that we already have enough LLM. Maybe then they will stop once and for all this endless race for an AGI.

AT is software thought out for me. The fruit of a few weeks of near-burnout focus on LLMs and the attempt to control the uncontrollable. Between studies of harnesses aimed at security, I tested architectural views of software or themes based on old social networks directly in a program I nicknamed `AT`.

This document aims to be an attempt to make the LLM agent understand the conceptual origin of AT, avoiding the Poisoned Tree Fruit Theory, where errors pile up and the harness that was created no longer makes any sense after a few billion tokens.

Beyond that, it aims to be extremely architectural. If you understand that the "harnesses" of this architecture are not good enough, maybe I lack knowledge. Post an issue, I will be glad to learn!

### The name

AT is the acronym of what I am after: **Technological Autonomy**, which §2 declares. And it is a name that appears in my head when I read the word bootstrap — the exact reason, I cannot say, but I like the word bootstrap very much.

The history is far too interesting. "To pull oneself up by one's bootstraps" is an English phrase from the early 19th century, initially treated as a sarcastic joke because of the impossibility of lifting oneself (from the air or from the water, for example) by one's own bootstraps. Ironically, that is what our devices do (the famous _boot_). Computers and smartphones have a standard piece of code executed when the device is turned on. It is what loads the operating system you know (Windows or Linux). AT has this purpose of being a _bootstrap_ for what it sets out to be. Right now I am doing that bootstrap. AT was born in a chaos while I was studying LLM harnesses and thought I had solved all the problems of the world. Now I am migrating what I developed in a rush into the format to be published. Very much in the mold of [Linux From Scratch](https://www.linuxfromscratch.org/) (which I strongly recommend for learning Linux).

## 2. Purposes and limits [context]

### What it sets out to do

The idea of AT is to be a deterministic task engine, usable by a person, by a program or by an LLM. I like machines doing boring things for me. I like ease of access with security. I like Technological Autonomy. And I do not want to spend time developing this. And I like spending very little money. Here I accept spending money in pursuit of that goal, aiming at not needing the massive LLMs again down the line.

But beyond that, AT is a minimalist working environment — minimum to be **functional**, not minimum to be **aesthetic**; the [themes](interfaces.md#design-system-and-themes) are here for that. "I do not need much to be productive in a technological environment". That is a manifesto in itself: it is possible to be productive with a binary and a folder. The support — the supporting infrastructure (§7) — stays outside the minimum: it comes in when I want it, and its absence takes no functionality away from AT. Several extensions of AT will live as something of mine, initially. Sending my library of finished games to rawg using the Steam and Heroic bases does not fit in the default part of AT. And opening the possibility of community extensions, without curation, with all the risk of Supply Chain attacks, is complicated. That is why AT is born as it is, analyzing functionality by functionality whether it fits here.

### Does AT reinvent the wheel?

Yes, it does. There are many more advanced applications for specific parts of AT. If you understand that your Project cannot be managed here, and that you need far more functions, I understand you, and unfortunately AT is not for you. But for me it is more than enough. At first I had defined that tasks were not deleted. They had to be cancelled, to keep history. I find that valid, and the function exists. But if I want to delete, I can. More details on [tables](architecture.md#tables) below. There are tools like Obsidian and AnyType for files and structured data. Those tools are fantastic and I do not want to replace them.

### Where to run AT

The idea is for AT to run on a machine. A Turing-compatible one. It can be your desktop, your notebook, your NAS, a VPS. I would like it to be light — light in what the binary demands from the machine, not in the size of the artifact, which carries the interpreter and the libraries packed in. But I am not in the mood to learn Go or Rust. So Python it is. "Everybody" knows Python. And if an ESP32 runs Micropython, it is because I can aim far here.

AT has two paths of use, and both are supported: the **hosted** one, where it is the binary and the folder, and the **container** one, where it builds an environment of services. The choice belongs to the person, and they can change their mind later; what each path guarantees, and what it does not, is in [§6](paths.md).

## Index

`§N` is the article's stable id, and it does not change a digit when the article changes file. The table says what each article is and where it lives.

| § | what it is | where it lives |
|---|---|---|
| §0 | the agent protocol: how to read and how to change this repository | here |
| §1 | the origin: where AT came from and why that name | here |
| §2 | the purposes and the limits: what it is and what it refuses to be | here |
| §3 | the rules: security, code and delivery, external dependency | [`rules.md`](rules.md) |
| §4 | the architecture: the layers, the tables and the secrets | [`architecture.md`](architecture.md) |
| §5 | the interfaces: `cli`, WebApp and Wizard | [`interfaces.md`](interfaces.md) |
| §6 | the two paths of use | [`paths.md`](paths.md) |
| §7 | the container path: the steps | [`container.md`](container.md) |
| §8 | the extensions and the plugins | [`extensions.md`](extensions.md) |
| §9 | the end-to-end test environment | [`end-to-end.md`](end-to-end.md) |
| §10 | the derivation: the tree, the Working Folder and the operation | [`derivation.md`](derivation.md) |
| §11 | the glossary: what a name means | [`glossary.md`](glossary.md) |

## What is not here yet

`docs/en_US/backlog.md` holds what comes next, with what counts as done for each item.

Three debts were born from the decisions of this session, and all three are named so they do not become a surprise:

- **The code.** Nothing that was decided here is built: the actor, the audit, the demand filter, the posture, the interpreter, the plugins. Every one of them has an item in `docs/en_US/backlog.md`.
- **The checker's list.** It was born large — 220 words in Portuguese and 141 in English — and the reason is written in its header: the checker's dictionary comes from subtitle frequencies and gets the formal register wrong, where "seção", "deleção" and "registrar" do not appear. If that list grows on its own, the gate became decoration, and the diff is where one notices.
- **The `FAQ.md`.** It does not exist yet, and it now has work waiting: saying what is underneath — which screen is AT's and which is a third party's — and that writing well is the best remedy against a misunderstanding of the interpreter.
