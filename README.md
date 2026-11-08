# AT

- [Português (Brasil)](docs/pt_BR/README.md)
- [English (United States)](docs/en_US/README.md)

## Status

**AT is useful today, and it is not finished.** It is a deterministic task engine that runs inside one folder (the Working Folder), as a single binary plus that folder, with a CLI, a WebApp and a chat interpreter. It is built and used daily by its author, and it works within its own philosophy.

Many architectural decisions still have to be settled, and the documents in `docs/` say so where it matters. Expect things to move, and expect breaking changes. Issues and discussion are welcome: I would rather learn that an architectural choice is wrong than keep it.

What this repository is, and what it is not:

- **It is generic.** The repository is the product: a personal productivity tool for any person, with no personal data, no machine paths and no instance of anyone's in it.
- **It does not try to replace the many wonderful tools that already exist.** The goal is a condensed, tightly controlled piece of software with a few small functionalities, favoring the reuse of mature architectural components over piling up features. Each new functionality is weighed on whether it fits here.
- **The author's own instance is the development reference.** Functionalities are born there, and the aim is always to build things that are useful to many people, not only to the author. That is not something one fully controls, so the question "is this useful beyond me?" is asked out loud while a functionality is implemented.

**Estado (pt_BR).** O AT já é útil hoje, mas não está pronto. Muitas decisões arquiteturais ainda precisam ser acertadas, e os documentos em `docs/` dizem isso onde importa. O repositório é genérico e não carrega dado pessoal; a instância do autor é a referência de desenvolvimento, sempre pensando em coisas úteis para muita gente. Não queremos substituir as ferramentas que já existem, e sim reunir pequenas funcionalidades num software condensado e bem controlado, que reaproveita componentes arquiteturais maduros em vez de encher de coisas.

## For LLM agents

Read in the language that suits your model best; when in doubt, always read in
English. The English track is written with the market's terms and concepts on
purpose, so that a name means the same thing here and out there — and the `pt_BR`
track is the source, so where the two diverge, `pt_BR` rules.

The person responsible for this repository writes in `pt_BR`.

**If an `INSTANCE.md` sits at the root, read it before touching anything.** It is
the person's own file — the real Working Folder, what a session owes it, and what
is still missing there — and it is not part of the product: the repository does
not carry it and does not name it beyond this line. A clone that does not have
the file owes nothing; one that has it starts by reading it.

## Vendored binaries

Third-party binaries (Caddy, gitleaks, Authelia, the spelling-checker) are not in
the repository: `at/vendor/*/manifest.json` pins each one by name, version,
official URL and sha256. A fresh clone runs `python3 -m release.fetch` before
running or packing AT (`release.build` does it by itself).

## License

Code under the [MIT License](LICENSE.md). The name, logo and visual identity of Autonomia Tecnológica are not covered by it: see [TRADEMARK.md](TRADEMARK.md). Third-party components and their licenses: `at/vendor/licenses/`.
