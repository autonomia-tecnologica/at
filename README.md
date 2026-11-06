# AT

- [Português (Brasil)](docs/pt_BR/README.md)
- [English (United States)](docs/en_US/README.md)

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
