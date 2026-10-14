"""`at-cli secret install_hooks` — the varredura becomes `git`'s own portão.

`core.scanner` already reports what a folder carries that it should not; this
module is the second half, written into the session itself: it writes
`pre-commit` and `pre-push` into a repository's own `.git/hooks/`, so a secret
in clear is refused BEFORE it ever reaches a commit or leaves over a push — not
only when someone remembers to ask (§3, item 51 — `.claude/CLAUDE.md`, "A
varredura é portão do commit e do push").

**What the hook scans is the repository it was installed into, and — when the
environment configures one — the Working Folder beside it, always.** The two
are not the same folder: a product checkout is never a Working Folder (§3,
`.claude/CLAUDE.md`), so `install(repo)` takes the target it protects as its
own argument instead of reading `paths.working_folder()` — the SAME repository
this very checkout's own hooks protect. At the moment `git` runs the hook, it
ALSO reads `AT_ROOT` out of the committer's own shell: a Working Folder
configured there is scanned too, by name and never by a fixed path this module
remembers — nothing here hardcodes an instance's address, the way the session
side of this feature (`.claude/scripts/git-hooks/secret-gate`) still did before
this module existed.

**The tool's own cache never lands inside the repository it protects.**
`scanner.scan(source=...)` is what makes that possible (item 51's own
docstring says why): the walk happens over `source`, and the `gitleaks` binary
it needs is unpacked under `AT_ROOT` — which this module points at
`<repo>/.git/at-secret-gate/` for the repo it is installed into, a path
`.git/` already keeps out of every commit by what `.git/` IS. A foreign
repository never gains an `App/` folder of AT's own only because something
scanned it.

**The hook is a small Python script, not a shim that calls the artifact.** It
is written with `sys.executable` as its own shebang — the very interpreter
running `install`, which is the one guaranteed to import `at.core.scanner` —
and it calls the scanner as a library, the same way this module does: a
`.git/hooks/pre-commit` is not a terminal, and `at-cli`'s own dispatch would
ask `boot.ensure_working_folder()` a question nothing is there to answer for a
repository that was never meant to become one.

**A secret found is a hard refusal — there is no flag that turns the gate
off.** The ressalva is the feature's own: a bypass a person could reach for
without thinking is not a gate.
"""

from __future__ import annotations

import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from at.core import paths

PRE_COMMIT = "pre-commit"
PRE_PUSH = "pre-push"
HOOK_NAMES = (PRE_COMMIT, PRE_PUSH)

# Where the tool's own cache lives for a repository this module protects — a
# path `.git/` already keeps out of the worktree and out of every commit,
# which is what lets `scanner.found()` unpack `gitleaks` without writing
# anything a person would see walking the repository it protects.
CACHE_NAME = "at-secret-gate"

INSTALLED = "installed"
NOT_A_REPO = "not_a_repo"


@dataclass(frozen=True)
class Report:
    """What `install` answers: the state, and the repository it names."""

    state: str
    target: Path


def install(repo: Path | None = None) -> Report:
    """Write `pre-commit` and `pre-push` into `repo`'s own `.git/hooks/`.

    `repo` defaults to the Working Folder running this command — the ordinary
    case, an AT user protecting their own data's repository — and takes any
    other path when the repository to protect is not the one this session
    calls its Working Folder (a product checkout, chiefly: §3's own rule is
    that it is never one).

    A folder that carries no `.git` is refused (`NOT_A_REPO`): writing a hook
    into a repository that is not there would be inventing one, which is
    `versioning`'s job and never this module's. What was already at
    `pre-commit`/`pre-push` is replaced — the two names are this feature's own
    the moment it is asked for, the same way `install-git-hooks.sh`'s own
    symlink already replaced whatever answered those names before it.
    """
    target = (repo if repo is not None else paths.working_folder()).expanduser().resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        return Report(NOT_A_REPO, target)
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    content = _script(target, git_dir / CACHE_NAME)
    for name in HOOK_NAMES:
        hook = hooks_dir / name
        hook.write_text(content, encoding="utf-8")
        mode = hook.stat().st_mode
        hook.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return Report(INSTALLED, target)


def _script(target: Path, cache: Path) -> str:
    """The hook's own source — a Python script, shebanged with the very
    interpreter `install` runs under, so it can `import at.core.scanner`
    wherever that import already works."""
    header = f"#!{sys.executable}\n"
    assignments = f"TARGET = {str(target)!r}\nCACHE = {str(cache)!r}\n"
    return header + assignments + _BODY


# The hook's body, as the committer's shell runs it — PLAIN text, not an
# f-string of this module's: every `{}` below is the GENERATED script's own
# syntax, read by the interpreter the shebang names, never by this one.
_BODY = '''
import os
import sys
from pathlib import Path

# Read BEFORE `AT_ROOT` is pointed at the tool's own cache, below — the
# committer's shell is the only place "the Working Folder configured" can
# come from, and it is gone the instant this line is overwritten.
ambient = os.environ.get("AT_ROOT")

os.environ["AT_ROOT"] = CACHE
from at.core import scanner
from at.i18n import tr


def _speak(report, where):
    print(tr("secrets.hooks.blocked", where=where), file=sys.stderr)
    if report.state == scanner.FOUND:
        for finding in report.findings:
            place = f"{finding.where}:{finding.line}" if finding.line else finding.where
            print(f"  {finding.rule} - {place}", file=sys.stderr)
    elif report.state == scanner.NO_TOOL:
        print(tr("secrets.scan.ways"), file=sys.stderr)
    else:
        print(tr("secrets.scan.failed"), file=sys.stderr)


ok = True

report = scanner.scan(source=Path(TARGET))
if report.state != scanner.CLEAN:
    _speak(report, TARGET)
    ok = False

if ambient and os.path.abspath(ambient) != os.path.abspath(TARGET):
    os.environ["AT_ROOT"] = ambient
    extra = scanner.scan()
    if extra.state != scanner.CLEAN:
        _speak(extra, ambient)
        ok = False

sys.exit(0 if ok else 1)
'''
