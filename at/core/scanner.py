"""The scanner: the folder says what it carries that it should not (§4, item 51).

The philosophy of the folder is that it is copied WITHOUT encryption, and that
what a PERSON writes in it is theirs — the AT does not hide it. Not protecting is
not the same as not warning: a secret that entered by mistake into a task's
description, a document of `Arquivos/` or the history of `.git` travels to the
copy, to the versioning and to wherever the copy goes, and this module is the
honest answer to that same philosophy: AT does not hide what is the person's, and
says what it found.

**The rule list is `gitleaks`' own, and AT writes none of it.** A scanner IS a
list of rules that ages, and a list AT maintained would age badly: it would keep
saying "nothing found" after the world moved. So the tool is `gitleaks` — the one
the person named, the established one —, and the rules it serves itself from are
that tool's default list, which is SAID OUT LOUD in the answer (`rules`, with the
version that answered).

**And AT carries the tool, so nothing is installed on the person's machine.** The
vendor's tarball travels inside `at-cli` (§3, Dependência externa) and
`at/services/gitleaks.py` unpacks it into `App/gitleaks/`; `found` answers THAT
path. **The embedded one wins, and the machine's PATH is never consulted.** A
`gitleaks` the person installed would be a dependency nobody pinned — and the
version this module names is honest only because there is exactly one candidate:
the one the binary carries, which is the same on every machine that runs it. Two
people with one artifact scan one folder the same way, and the answer's version
is a fact about the release and not about the machine. The precedent is the
Caddy's, which travels this way for this same reason. What is LEFT of the old
external-dependency shape is the refusal: the Podman one `certutil` follows
(`at_deploy/trust.py`) — where the tool is not there AT says so and installs
NOTHING —, and the state that remains for it is the extraction that failed: the
artifact carries no gitleaks for this platform, the tarball is not one AT can
unpack, or `App/` could not be written. Nothing here reaches a network, and
nothing here is a model.

**What it walks: the folder, and the history it carries.** The files as they are
— the tables and everything in `Arquivos/` — and, when the folder carries a
repository, its story commit by commit, because a secret a person REMOVED is a
secret that still lives in the history. The tool gets two runs for that, and a
place the filesystem already names is ONE finding and not its repeat in the
history (`_distinct`).

**It reports, and it never corrects.** The answer says WHERE — the file and the
line, and the commit for a finding only the history keeps — and never the VALUE:
what the scanner read is not what a surface draws, the same care the `phone`
takes with the token it prints once (§7c). A report carries the secret itself
(`Secret`, `Match`) and this module reads those fields to COUNT and nothing else:
no value leaves here, and the dataclass below has no field one could travel in.

**No line, and no version.** A scan is a READ of the folder, and §3 makes reading
not doing: it leaves no `audit` line, and the folder is not versioned for it.
What the vault sealed is exempt BY CONSTRUCTION and not by an exclusion AT
writes: the `secret` table's value is an envelope (`xsalsa20poly1305:<base64>`)
and never a cleartext, so there is nothing in it for a scanner to find — which is
the whole of what the cofre buys, and the reason the scan declares no rule of its
own about it. **Measured** against the tool the person named, `gitleaks 8.30.1`
with its default list: a folder carrying a sealed row scans CLEAN, so the
exemption is a fact about the envelope and not a hope about the rules.

**The seam is one.** `found` answers where the tool is — the one unpacked out of
the artifact —, and `run` is the only call to it: the arguments are composed here
and the binary is resolved there, so a scanner that could not be unpacked is a
state the suite proves without one byte of the program.

**The report never lands in the folder.** The tool writes its JSON where AT tells
it to, and that place is a temporary directory OUTSIDE the Working Folder: a scan
that left a file in the folder it is auditing would be a scan that writes what it
was asked to look for.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from at.core import paths, versioning
from at.services import gitleaks as embedded

# The tool, and the only one AT knows for this. It travels inside the artifact
# (`at/services/gitleaks.py`), which is what unpacks it into the folder; it is
# never installed on the person's machine, and the PATH is never consulted.
BINARY = "gitleaks"

# The report the tool is asked for, and the only shape this module reads. JSON is
# the stable one: a text report is for a person, and a person is not parsing.
FORMAT = "json"

# What the tool is asked, as the two halves of the walk. `detect` is its own word
# for the act, and `--no-git` is what tells the files as they are from the
# repository's story — the first does not need a repository and the second does.
FILES = ("detect", "--no-git")
HISTORY = ("detect",)

# The exit codes that are the tool ANSWERING rather than refusing: `0` is
# "nothing found" and `1` is "found something" — its own convention, and one AT
# does not depend on, because the report is what is read. What is left is the
# tool refusing, and a refusal is a state of this module.
QUIET = (0, 1)

# The states of a scan, and the whole of what a door has to draw apart.
CLEAN = "clean"
FOUND = "found"
# The name survived the tool moving into the artifact: what it means now is that
# the scanner is not there — the extraction that failed (`found`) —, which is the
# same thing to the person and a different thing to the code.
NO_TOOL = "no_tool"
FAILED = "failed"


@dataclass(frozen=True)
class Finding:
    """One leak, as a person may be told about it: WHERE, and nothing of WHAT.

    There is no field for the value, and that is the design and not a habit: a
    secret that had a field here would travel to a screen eventually, which is
    the one thing item 51 forbids. `commit` is set for a finding only the
    history keeps, and `None` for one the files as they are already carry.
    """

    rule: str
    where: str
    line: int
    commit: str | None = None


@dataclass(frozen=True)
class Report:
    """What a scan answers: the state, the tool that served it, and the findings.

    `tool` is the tool NAMED WITH ITS VERSION when it answers one — it is the
    "rule list said out loud" of item 51: whoever reads knows which scanner and
    which list of rules stood behind the answer.
    """

    state: str
    tool: str
    findings: tuple[Finding, ...] = ()


def found() -> str | None:
    """Where the AT's own `gitleaks` is, or `None` — the question that decides
    everything.

    A path and not a boolean, for the reason `versioning.found` and
    `trust.found` answer one: what the person reads is WHICH program was found.

    **It answers the unpacked one and never the machine's PATH.** The scanner is
    the artifact's, like the Caddy is (§3, Dependência externa): `ensure` unpacks
    the vendor's tarball into `App/gitleaks/` — once, and only when the platform
    stamp disagrees — and answers where it landed. A `gitleaks` the person
    installed is not consulted even when it is newer: it is a dependency nobody
    pinned, and the version this module says stood behind a scan is only a fact
    while there is one candidate to say it about.

    `None` is the extraction that did not happen, and there are three ways for it
    to: the artifact carries no gitleaks for this platform, the tarball is not one
    AT can unpack, or the folder could not be written. They are one state because
    they are one thing to the person — the scanner is not there —, and the door
    says so with the ways out instead of a dry refusal.
    """
    try:
        where = embedded.ensure()
    except (embedded.GitleaksError, OSError):
        return None
    return str(where) if where is not None else None


def run(args: Sequence[str]) -> subprocess.CompletedProcess:
    """One call to the tool — the seam, and the only one.

    The binary is resolved HERE and never by the caller, so nothing outside this
    function has to know where it is, or that there is one. The output is
    captured because AT answers in its own words (§3): the text of a diagnostic
    program is for whoever is diagnosing, and it is not passed on.

    A missing binary is the caller's to prevent (`found`), and it does — `scan`
    never gets here without one —, so this raises `FileNotFoundError` rather than
    falling back to the PATH: a fallback would run a `gitleaks` this module did
    not choose, and the answer would name a version that is not the artifact's.
    """
    where = found()
    if where is None:
        raise FileNotFoundError(BINARY)
    return subprocess.run(  # noqa: S603 — the tool's own binary, resolved above
        [where, *(str(part) for part in args)],
        capture_output=True,
        text=True,
    )


def version() -> str:
    """The version the tool answers, or `""` when it does not answer one.

    It is read for the answer's sake and never for a decision: a tool that
    refuses to say its version is still a tool that scans, and a scan refused
    over a missing `--version` would be the tail wagging the dog.
    """
    try:
        answered = run(["version"]).stdout.strip()
    except OSError:
        return ""
    return answered.splitlines()[0].strip() if answered else ""


def named() -> str:
    """The tool as the answer names it — `gitleaks 8.18.4`, or the bare word."""
    spelled = version()
    return f"{BINARY} {spelled}" if spelled else BINARY


def scan() -> Report:
    """Walk the folder, and answer what it carries that it should not.

    The order of the two questions is the one that decides: the tool first,
    because without it there is no walk at all — and its absence is a state of
    its own so the door can say the ways out instead of a dry refusal. The first
    question is also what unpacks the scanner, once, the first time it is asked.
    """
    if found() is None:
        return Report(NO_TOOL, BINARY)
    name = named()
    findings: list[Finding] = []
    with tempfile.TemporaryDirectory(prefix="at-scan-") as hold:
        for index, mode in enumerate(_modes()):
            walked = _walk(mode, Path(hold) / f"{index}.json")
            if walked is None:
                return Report(FAILED, name)
            findings += walked
    distinct = _distinct(findings)
    return Report(FOUND if distinct else CLEAN, name, distinct)


def _modes() -> tuple[tuple[str, ...], ...]:
    """The walks this folder needs: the files, and the history it carries.

    The history is walked only where there IS one: a folder that carries a
    repository AT drives and one a person arranged are both repositories, and a
    folder with neither has no story to look through. Asking the versioning
    module is what keeps this module from having an opinion about `.git`.
    """
    if versioning.state() in (versioning.OWNED, versioning.FOREIGN):
        return (FILES, HISTORY)
    return (FILES,)


def _walk(mode: tuple[str, ...], report: Path) -> list[Finding] | None:
    """One walk, and what it found — or `None` when the tool refused.

    The report is written where AT tells the tool to write it, and read back
    from there. A report that is NOT there is not a refusal by itself: the tool
    answers its quiet cases with an exit code and no findings, and only an exit
    code outside `QUIET` with nothing to read is the refusal it is.
    """
    done = run([
        *mode,
        "--source",
        paths.working_folder(),
        "--report-format",
        FORMAT,
        "--report-path",
        report,
    ])
    loaded = _parsed(report)
    if loaded is None:
        return [] if done.returncode in QUIET else None
    history = mode == HISTORY
    return [
        _finding(entry, history) for entry in loaded if isinstance(entry, dict)
    ]


def _parsed(where: Path) -> list | None:
    """The report as a list of findings, or `None` when there is none to read."""
    try:
        raw = json.loads(where.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, list) else None


def _finding(entry: dict, history: bool) -> Finding:
    """One entry of the report, with the VALUE left where it is.

    The fields `Secret` and `Match` are the leak itself, and neither is read
    here — not filtered out later, but never taken: a `Finding` has no room for
    one, which is what makes "the screen is never the secret" a property of the
    shape instead of a promise about the code.
    """
    line = entry.get("StartLine")
    return Finding(
        rule=_text(entry.get("RuleID")),
        where=_relative(_text(entry.get("File"))),
        line=line if isinstance(line, int) and not isinstance(line, bool) else 0,
        commit=(_text(entry.get("Commit")) or None) if history else None,
    )


def _text(value: object) -> str:
    """A field of the report as the string it is, and `""` for anything else."""
    return value.strip() if isinstance(value, str) else ""


def _relative(where: str) -> str:
    """The path as a person reads it in the folder, when the tool answered one
    that is absolute — the report of the two walks says it differently."""
    path = Path(where)
    if not where or not path.is_absolute():
        return where
    try:
        return path.relative_to(paths.working_folder()).as_posix()
    except ValueError:
        return where


def _distinct(findings: list[Finding]) -> tuple[Finding, ...]:
    """One finding per PLACE, and the filesystem's place beats the history's.

    A leak that is in the files as they are is found twice — once by the walk of
    the files and once by the commit that carries it — and that is one finding
    and not two: what a person needs is WHERE it is, and the worktree's path and
    line are the ones they can open. A place that only an older commit keeps is
    its own finding, and it says which commit.

    The order is settled here as well, because the tool's is its own: two scans
    of one folder have to read the same, and a report that shuffled itself would
    be a report nobody could diff.
    """
    places = {(item.rule, item.where, item.line) for item in findings if item.commit is None}
    seen: set[tuple[str, str, int, str]] = set()
    kept: list[Finding] = []
    for item in findings:
        if item.commit is not None and (item.rule, item.where, item.line) in places:
            continue
        key = (item.rule, item.where, item.line, item.commit or "")
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return tuple(sorted(kept, key=lambda item: (item.where, item.line, item.rule, item.commit or "")))
