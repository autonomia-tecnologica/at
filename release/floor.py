"""The glibc floor of an artifact — MEASURED, never assumed.

**A frozen binary carries the machine that built it.** PyInstaller bundles the
interpreter and its extension modules, and a shared object records, for every
symbol it calls, the VERSION of the library it was linked against. Build on a
machine whose glibc publishes `cosh` under `GLIBC_2.44` and the artifact says it
needs `GLIBC_2.44` — for a symbol it may never call, in a module it may never
load — and every machine with an older glibc refuses to load it at all. That is
not theory: it is what the release built on a rolling distribution did, dying on
`libm.so.6: version 'GLIBC_2.44' not found` inside a Debian a year newer than the
floor it was supposed to run on.

So the floor is NOT a property of the code and cannot be fixed by editing it. It
is a property of WHERE the release was built — which is why it is declared
(`builder.json`), why the build happens where the declaration says, and why this
module exists: to measure the artifact against the declared ceiling and refuse
to publish past it. A promise nobody can falsify is not a promise.

**Two readings, and confusing them is the whole bug.** `objdump -T` lists what a
file DEFINES and what it NEEDS, and a library that publishes `GLIBC_2.44` is not
asking anybody for it. Only the `*UND*` lines are a requirement; reading the
others is how a build machine's own glibc gets mistaken for the artifact's floor.

    python3 -m release.floor build/at-cli/PKG-00.toc --floor 2.35
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

# The version of one symbol's library, as `objdump` writes it: `(GLIBC_2.44)`.
NUMBER = re.compile(r"GLIBC_(\d+)\.(\d+)")

# What an artifact carries that can ask for a library: the bootloader, the
# interpreter and the extension modules. The rest of the bundle is data —
# Python source, the PYZ archive, the WebApp's assets — and none of it links.
OPAQUE = ("BINARY", "EXTENSION", "EXECUTABLE")

# Where PyInstaller writes the manifest of what it bundled, per spec.
MANIFEST = "PKG-00.toc"

# The release's own declaration: the floor it promises and the payload it
# promises to carry. ONE home — the gate reads it here, and the build reads the
# same file for the machine, so the number cannot say one thing in the script
# and another in the check.
DECLARED = Path(__file__).resolve().parent / "builder.json"

Version = tuple[int, int]


class FloorError(Exception):
    """The floor could not be read — which is not the same as being fine."""


def needed(listing: str) -> Version | None:
    """The highest glibc version `objdump -T` says this file NEEDS.

    Only the UNDEFINED symbols count. A version that appears on a line that is
    not `*UND*` is something the file PUBLISHES, and a library that carries
    `GLIBC_2.44` is not asking its machine for anything.
    """
    top: Version | None = None
    for line in listing.splitlines():
        if "*UND*" not in line:
            continue
        for found in NUMBER.finditer(line):
            version = (int(found.group(1)), int(found.group(2)))
            if top is None or version > top:
                top = version
    return top


def parse(text: str) -> Version:
    """`"2.35"` as the pair it is. A floor that is not one is refused here."""
    parts = str(text).strip().split(".")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise FloorError(f"not a glibc version: {text!r}")
    return int(parts[0]), int(parts[1])


def shown(version: Version) -> str:
    return f"{version[0]}.{version[1]}"


def entries(manifest: Path) -> list[tuple[str, str, str]]:
    """The `(name, where it came from, kind)` the build wrote, read back.

    PyInstaller writes `build/<name>/PKG-00.toc` when it packs: a tuple of
    eleven fields, and the entries are ONE of them — a list whose items are
    three-tuples. They are FOUND and not indexed: eleven fields is one release's
    shape, the list of three-tuples is what an entry IS, and a reader that pinned
    the position would break in silence on the version that moved it.
    """
    try:
        data = ast.literal_eval(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, SyntaxError) as error:
        raise FloorError(f"cannot read {manifest}: {error}") from error
    found = next(
        (
            part
            for part in data
            if isinstance(part, (list, tuple))
            and part
            and all(isinstance(item, (list, tuple)) and len(item) == 3 for item in part)
        ),
        None,
    )
    if found is None:
        raise FloorError(f"{manifest} carries no list of entries to read")
    return [(str(name), str(source), str(kind)) for name, source, kind in found]


def pieces(manifest: Path) -> list[Path]:
    """Every ELF the bundle carries, read off the build's own manifest.

    The source is what matters here: the artifact IS those files, so reading the
    manifest is reading the bundle without unpacking it, and measuring the source
    is measuring what will run.
    """
    found: list[Path] = []
    for _, source, kind in entries(manifest):
        if kind not in OPAQUE or not source:
            continue
        where = Path(source)
        if where.is_file():
            found.append(where)
    return found


def carried(manifest: Path) -> list[Path]:
    """Every file the bundle is MADE OF, and not only the ones that link.

    The floor is measured on what can link (`pieces`): a Python source, a block
    of JSON and a WebApp asset ask the machine for nothing. The release's
    PROMISE is about something else — what the artifact carries —, and a third
    party's licence text is data that asks for nothing and is still something the
    release said it would carry. Checking the promise against the ELF alone left
    the notices outside the gate; they are inside it now, which is the only way
    the sentence "the artifact carries the terms of what it distributes" is a
    promise somebody can falsify.
    """
    return [
        where
        for _, source, _ in entries(manifest)
        if source and (where := Path(source)).is_file()
    ]


def measure(paths) -> dict[Path, Version]:
    """What each path needs, by the tool that reads a binary (`objdump`).

    A file with no versioned requirement at all is left out: the libc itself is
    asked for nothing, and saying `None` for it would be a hole a later
    comparison reads past.
    """
    found: dict[Path, Version] = {}
    for where in paths:
        try:
            answer = subprocess.run(
                ["objdump", "-T", str(where)], capture_output=True, text=True
            )
        except FileNotFoundError as error:
            raise FloorError("objdump is not on this machine: binutils is owed") from error
        if answer.returncode != 0:
            raise FloorError(f"cannot read {where}: {answer.stderr.strip()}")
        version = needed(answer.stdout)
        if version is not None:
            found[where] = version
    return found


def past(measured: dict[Path, Version], ceiling: Version) -> list[tuple[Path, Version]]:
    """The pieces that go PAST the declared ceiling, worst first."""
    over = [(where, version) for where, version in measured.items() if version > ceiling]
    return sorted(over, key=lambda entry: entry[1], reverse=True)


def missing(carried: list[Path], wanted: list[str]) -> list[str]:
    """What the release PROMISES to carry and the bundle does not.

    A payload the builder cannot supply is a payload PyInstaller leaves out in
    SILENCE — the same silence the spec denounces for a WebApp `dist/` that was
    never built. Measured: a builder with no Tk produced an `at-deploy` thirteen
    megabytes lighter, without its own Wizard's runtime, and nothing said so.
    What the release carries is a promise, so it is declared and it is checked.
    """
    names = [where.name for where in carried]
    return [
        want
        for want in wanted
        if not any(want in name for name in names)
    ]


def report(root: Path, ceiling: Version, out=sys.stdout,
           wanted: dict[str, list[str]] | None = None) -> bool:
    """Measure every bundle under `root`, say each, and answer whether it holds.

    The floor of a bundle is the floor of its WORST piece: it is not the sum of
    what the artifact asks for, it is the oldest machine where every one of them
    loads. So the answer per bundle is the maximum, and the gate is one
    comparison against the declaration.

    And the two failures are told apart, because they are different mistakes: a
    release that asks for a newer libc than it promised, and a release that
    quietly stopped carrying something it promised to carry.
    """
    held = True
    for manifest in sorted(root.glob(f"*/{MANIFEST}")):
        where = manifest.parent.name
        measured = measure(pieces(manifest))
        if not measured:
            # Finding nothing to measure is not the same as finding nothing
            # wrong: a bundle nobody could read is a bundle nobody proved, and
            # what was not proved does not pass.
            print(f"{where}: nothing to measure — {manifest} carried no readable ELF",
                  file=out)
            held = False
            continue
        worst = max(measured.values())
        over = past(measured, ceiling)
        # O que cada artefato promete é o que o SPEC dele promete, e os dois não
        # são o mesmo: `at-deploy` nomeia `tkinter` (`hiddenimports`) pelo
        # Wizard que ele carrega sem chamar, e `at-cli` não carrega Tk nenhum.
        absent = missing(carried(manifest), (wanted or {}).get(where, []))
        where_worst = max(measured, key=lambda path: measured[path])
        print(f"{where}: floor {shown(worst)} ({where_worst.name}), "
              f"{len(measured)} piece(s) measured", file=out)
        if over:
            held = False
            for path, version in over:
                print(f"  PAST {shown(ceiling)}: {shown(version)} in {path}", file=out)
        for want in absent:
            held = False
            print(f"  MISSING: nothing carrying {want!r} travels in {where}", file=out)
    return held


def declared() -> dict:
    """`builder.json` — the machine, the floor, and the payload."""
    try:
        return json.loads(DECLARED.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FloorError(f"cannot read {DECLARED}: {error}") from error


def main(argv: list[str] | None = None) -> int:
    """`python3 -m release.floor <build dir>` — the gate.

    It is run INSIDE the builder, right after the pack: the manifest names the
    builder's own paths, so it is the builder that can read them. What leaves is
    the artifacts, and what the gate answers is whether they may.

    The ceiling and the payload come from the declaration and not from the
    command line: a number typed twice is a number that disagrees with itself.
    """
    words = list(sys.argv[1:] if argv is None else argv)
    if len(words) != 1 or words[0].startswith("-"):
        print("usage: python3 -m release.floor <build dir>")
        return 2
    try:
        said = declared()
        ceiling = parse(said["floor"])
    except (FloorError, KeyError) as error:
        print(error)
        return 2
    print(f"Declared floor: glibc {shown(ceiling)}")
    if report(Path(words[0]), ceiling, wanted=said.get("payload") or {}):
        print("The release holds what it declared.")
        return 0
    print("The release did not hold what it declared, and does not leave.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
