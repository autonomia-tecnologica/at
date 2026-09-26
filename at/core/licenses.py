"""What the artifacts carry from outside, and under which terms (§3, item 27).

The rule this module answers is one of §3's: a third party only travels inside an
artifact if its licence permits, and **whatever the licence demands travels with
it**. The AT is delivered as ONE file — no folder beside it to lay a notice in —
so the notices travel inside it, and come out through the `license` word the two
artifacts offer. That is the whole reason this module exists: without it the
artifact carries Python, PyInstaller's bootloader, PyNaCl, libsodium, cffi, the
Caddy, the typefaces and Vue without their terms, which is exactly what the
licences forbid.

**The declaration is ONE, and it is data.** `at/vendor/licenses/manifest.json`
says, per component, the name, the version, the SPDX identifier, which artifact
carries it and WHERE its text is. Nothing here invents a fact and nothing is
written in two places: the SBOM (item 46) generates its licence lines from this
same file, and the suite holds every claim in it to what the tree actually has
(`at/tests/test_licenses.py`). The texts themselves are each vendor's own file,
never a paraphrase — the same choice the Caddy's tarball already made, and the
reason `at/vendor/licenses/caddy/LICENSE` is held byte-equal to the member inside
`at/vendor/caddy/caddy_2.11.4_linux_amd64.tar.gz`.

**The two artifacts carry different things, and the answer says so.** The
`at-cli` carries the app: the WebApp's typefaces and the Vue bundle, and the
Caddy. The `at-deploy` carries the environment and nothing of those — its
payload is deliberately short —, so `declared` filters by the artifact that is
ASKING, and neither binary claims a component it does not hold.

**Nothing here is a permission, and that is on purpose.** Reading a licence is
about the FILE and not about the folder, the same way `version` and `help` are:
it is answered before anything of the person's is touched, and no role gates it.

**What it does not do: it does not read the licence back off a binary.** The
declaration is written by whoever embeds a component, and the suite checks it
against the payload lists — a scan for strings inside a frozen artifact would be
a guess about a format, and the manifest is a fact somebody states.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from at import __version__
from at.i18n import tr

# Where the notices travel: `at/vendor/licenses/`, the arithmetic `caddy.py` uses
# for its payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/at/core/licenses.py`, so `parents[1]` is `at/` in both worlds
# and `parents[2]` is the tree's root, which the build also collects as the
# bundle's root (`("LICENSE.md", ".")` in both specs).
ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "licenses"

# The declaration, and the product's own licence. The second is OUTSIDE the
# payload folder on purpose: the repository carries it at its root, where a
# person looks for it, and the build collects that one file into the artifact.
MANIFEST = PAYLOAD / "manifest.json"
PRODUCT = ROOT / "LICENSE.md"


@dataclass(frozen=True)
class Component:
    """One third party the artifact carries, as the declaration states it.

    `version` is `None` for the component whose version is not AT's to name —
    libsodium travels compiled inside PyNaCl's extension, and the honest answer
    is the declaration's note and not a number invented here. `text` is
    repository-relative, and `note` is the declaration's own remark.
    """

    key: str
    name: str
    version: str | None
    license: str
    artifacts: tuple[str, ...]
    text: str
    note: str = ""

    def spelled(self) -> str:
        """The component as one line: `Caddy 2.11.4 — Apache-2.0`."""
        named = f"{self.name} {self.version}" if self.version else self.name
        return f"{named} — {self.license}"


def declared(artifact: str) -> tuple[Component, ...]:
    """Every component `artifact` carries, in the declaration's order.

    An empty answer means the declaration did not travel with the build — the
    state a spec that forgot the payload produces. It is not silent: the suite
    reads the same file and refuses a build that would answer nothing
    (`at/tests/test_licenses.py`), the way the Caddy's payload is held.
    """
    return tuple(entry for entry in _entries() if artifact in entry.artifacts)


def _entries() -> tuple[Component, ...]:
    """The declaration read whole, whatever artifact is asking."""
    try:
        loaded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    components = loaded.get("components") if isinstance(loaded, dict) else None
    if not isinstance(components, dict):
        return ()
    return tuple(
        Component(
            key=key,
            name=_text(said.get("name")) or key,
            version=_text(said.get("version")) or None,
            license=_text(said.get("license")),
            artifacts=tuple(
                one for one in said.get("artifacts") or () if isinstance(one, str)
            ),
            text=_text(said.get("text")),
            note=_text(said.get("note")),
        )
        for key, said in components.items()
        if isinstance(said, dict)
    )


def _text(value: object) -> str:
    """A field of the declaration as the string it is, and `""` for anything else."""
    return value.strip() if isinstance(value, str) else ""


def notice(component: Component) -> str | None:
    """The component's licence text, or `None` when it does not travel here.

    The path comes from the declaration and is resolved against the tree's root,
    which is the repository from a checkout and the bundle from a frozen
    artifact — the same arithmetic, so the answer is the same in both.
    """
    try:
        return (ROOT / component.text).read_text(encoding="utf-8")
    except OSError:
        return None


def product() -> str | None:
    """The AT's own licence — the MIT that `LICENSE.md` spells at the root."""
    try:
        return PRODUCT.read_text(encoding="utf-8")
    except OSError:
        return None


def report(artifact: str, texts: bool = False) -> str:
    """The whole answer of the `license` word, in the active language.

    The shape is the product's and not a lawyer's: what the AT is licensed as,
    what THIS artifact carries, and — when asked — each third party's own text.
    The texts stay behind `texts` because they are the vendors' whole legalese,
    tens of kilobytes of it, and a person asking what the binary carries is not
    usually asking to read them; the flag is how whoever needs them reaches them,
    and it is named in the help like every other flag of the product.
    """
    lines = [tr("licenses.title", version=__version__), ""]
    own = product()
    lines.append(tr("licenses.product"))
    lines.append(own if own is not None else tr("licenses.no_product"))
    carried = declared(artifact)
    lines += ["", tr("licenses.carried", count=len(carried))]
    for component in carried:
        lines.append(f"  {component.spelled()}")
        if texts:
            body = notice(component)
            if body is not None:
                lines += ["", body.rstrip("\n"), ""]
    return "\n".join(lines)
