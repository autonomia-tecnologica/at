"""The Working Folder under versioning — git, and AT drives it (§3, item 30).

The folder is the person's whole life in one place, and until this existed
nothing kept its history: losing a line meant it was gone, and nothing answered
how a table got to the state it is in. What this module builds is the HISTORY of
the folder, and **it is versioning, never backup**: a copy that survives the
machine is another thing, owed and named at the end of the backlog. The two are
never the same word, on any surface.

**Git is the tool, and the person does not have to know it exists.** AT is what
runs it — `git init` where there is no repository, a commit for every action
that changes the folder — and the folder is born under versioning by AT.

**Where the repository is born, and whose it is.** At the folder's ROOT, because
what it carries is everything the person wrote — `Tabelas/`, `Arquivos/`,
`Projetos/` — and not only `App/`. And AT versions where the repository is AT's:
the mark is `OWNER`, inside the git directory, written when AT creates it. A
folder that already carries a repository of its own is neither clobbered nor
driven — the history is its owner's, and AT says so. One rule, and it answers
two cases at once: the person who already uses git, and this checkout, which is
a repository and a Working Folder at the same time (§10, derivation).

**What the generated ignore leaves out** is what is DERIVED or regenerable —
the Caddy unpacked out of the binary, what a service rebuilds, the binaries that
updating replaces, the caches — and never what the person wrote.

**A missing git does not bring the folder down.** The precedent is Podman
(§7a): AT finds the tool missing, says so, and offers the two ways out instead
of a dry refusal. The question is asked where AT would have versioned — at the
folder's birth and in the migration that gives an existing folder its
repository — and only once: after that the folder SAYS it is not under
versioning rather than asking again.

**The commit is not made in here.** `commit` is the door; the ACTION is what
calls it with the sentence that names it — the engine's own — so `git log` reads
like the table's own story. And what the action wrote is `files.writes`, the
single writer's count, so this door costs a `list` nothing and never guesses
whether there is anything to version.

**And the folder is versioned from time to time, never on every write.** The
default is PERIODIC (§4, item 30): the WebApp writes to disk on every edit, and
one version per keystroke is not a history, it is a metronome. The cadence is the
FOLDER's — a setting says how many minutes may pass between versions, and `0` is
the person asking for every write back — and the WRITE itself looks at how long
ago the last version was and only commits when the interval has passed. That is
the cheapest of the shapes the item names and the one that needs no clock: the
folder never goes unversioned for longer than the interval AT is being USED. What
arrives between versions is not lost — the writes are on disk, and the next
version carries all of them, because a version is the whole folder and not one
action's diff.

**A folder that has fallen behind SAYS SO.** The `cli` prints it on the run it
notices, and the page draws it in the same band that already carries the folder
that has no versioning at all: `phrase` is the one wording, and `stale` is the
one predicate — AT's repository, writes the last version does not carry, and the
chosen interval gone by. A version that fires on its own while the WebApp is up
is item 24's job, and until it exists this sentence is the whole of what tells
the person the folder is waiting.

**Automatic versioning is off for now, behind `DISABLED`.** While the switch is
`True`, AT does not create the folder's repository, does not commit, and says
nothing about versioning; the histories already written stay where they are.
Turning it back on is changing the constant to `False`, and every door below
answers as if the folder had nothing to version.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from at.core import files, paths, settings
from at.i18n import tr

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot.ensure_working_folder` takes.
Ask = Callable[[str], str]

# The word on the PATH, and the only one AT knows (§7a's precedent, one tool
# over).
BINARY = "git"

# The repository's own directory, and the mark AT leaves in the one it created.
# The mark is INSIDE `.git/` on purpose: it belongs to the repository and travels
# with it in the folder's copy, it is never staged and never shown to a person,
# and a folder whose `.git/` lacks it is a repository that is not AT's.
GIT_DIR = ".git"
OWNER = "at"
IGNORE = ".gitignore"

# Who the commits are by. They are AT's and they say so: a commit wearing the
# person's name would be somebody answering for an act that was not theirs.
AUTHOR = "AT"
MAIL = "at@localhost"

# What the folder is, versioning-wise.
OWNED = "owned"
FOREIGN = "foreign"
BARE = "bare"
MISSING = "missing"

# The switch that turns automatic versioning off, for now. While it is `True`,
# AT does not create the folder's repository, does not commit, and says nothing
# about versioning; putting it back is changing this to `False`.
DISABLED = True

# What a person must hear about each state, and `bare` is deliberately absent: a
# folder with no repository on a machine that has git is a folder about to have
# one (`ensure`), not a state worth a sentence.
PHRASES = {FOREIGN: "versioning.foreign", MISSING: "versioning.missing"}

# The three outcomes of the offer, the way §7a's has them.
INSTALL = "install"
WITHOUT = "without"
NO_ANSWER = "no_answer"

# The cadence (§4, item 30). `KEY` is the setting — the name lives in
# `core.settings`, which owns the file's keys, so the two homes are one — and
# `DEFAULT` is what a folder that never chose is versioned at: minutes, and few
# enough that a working session is a handful of versions instead of hundreds.
# `EVERY_WRITE` is the number a person writes to have the metronome back, and it
# is the old default kept as a choice.
KEY = settings.VERSIONING
DEFAULT = 10.0
EVERY_WRITE = 0.0

# The seconds in a minute, for the one comparison the cadence makes: the
# interval is READ in minutes and COMPARED in seconds, and the conversion lives
# here and nowhere else.
_MINUTE = 60.0

# The sentence a folder that fell behind is owed. It is not a STATE like the two
# in `PHRASES`: the folder IS under versioning, and what it says is about time —
# the interval went by with writes still waiting.
STALE = "versioning.stale"

# How many writes this process has committed. Module state like the writer's
# count, and for the same reason: both are about a RUN.
_committed = 0


def found() -> str | None:
    """Where git is, or `None` — §7a's whole check, on the other tool.

    A path and not a boolean: what a person reads when the tools of a machine
    are being told apart is which one was found, and `which` is the same
    question the shell answers.
    """
    return shutil.which(BINARY)


def present() -> bool:
    return found() is not None


def run(args: Sequence[str]) -> subprocess.CompletedProcess:
    """One call to git — the seam, and the only one.

    The binary is resolved HERE and never by the caller, so nothing outside this
    function has to know where a git is, or that there is one. Output is
    captured: git speaks for whoever is diagnosing, and AT answers in its own
    words (§3) — an error's text is a machine's.

    `cwd` is the Working Folder and never the process's: the folder is what is
    being versioned, and the binary runs from wherever the shell happened to be.

    A missing binary is the caller's to prevent (`present()`): this raises
    `FileNotFoundError` like any `subprocess.run`.
    """
    return subprocess.run(  # noqa: S603 — the tool's own binary, resolved above
        [found() or BINARY, *(str(part) for part in args)],
        cwd=paths.working_folder(),
        capture_output=True,
        text=True,
    )


def owner_mark(root: Path) -> Path:
    """The mark AT leaves in the repository it created."""
    return root / GIT_DIR / OWNER


def state() -> str:
    """What this folder is, versioning-wise. Reads, and never writes.

    - `owned` — the repository is AT's, and AT drives it;
    - `foreign` — the folder carries a repository of its own, and AT leaves it
      alone;
    - `bare` — there is no repository, and git is here to make one;
    - `missing` — there is no repository, and there is no git either.

    A `.git` that is a FILE — a worktree, a submodule pointer — reads as
    `foreign`, which is right: it is a repository somebody else arranged, and
    running `git init` over it would be the clobbering this refuses.
    """
    root = paths.working_folder()
    if owner_mark(root).is_file():
        return OWNED
    if (root / GIT_DIR).exists():
        return FOREIGN
    return BARE if present() else MISSING


def interval() -> float:
    """The cadence, in minutes — the ONE reading of the folder's setting (§4).

    Both halves of the cadence read here: the write that decides whether to
    commit, and the sentence that reports the folder which waited. Two readings
    would be two answers about how long the folder may stay unversioned, and the
    one the person was shown would be the one that lies.

    A value that is not a number is a setting that was never made, and the folder
    answers the default — the way `risk.threshold` answers its own — because a
    cadence AT cannot read may neither flood the history nor quietly stop it. A
    number below zero is that same strange value. Zero is not: it is a cadence
    like any other, the one where no version is ever late.
    """
    value = settings.get(KEY, DEFAULT)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT
    if not math.isfinite(value) or value < EVERY_WRITE:
        return DEFAULT
    return float(value)


def _now() -> float:
    """The clock, in seconds since the epoch — the cadence's one seam.

    A function and not an inline call so that a test can move the clock instead
    of sleeping through the interval it is proving, and so that the whole module
    reads it in one place.
    """
    return time.time()


def last_version() -> float | None:
    """When the folder was last versioned, in seconds — the COMMIT's own stamp.

    The commit IS the version, so its stamp is the version's hour, and there is
    no second record of it to drift from: a stamp of the folder's own would be a
    second answer to a question git already answers, and the two would disagree
    the day somebody committed in the folder by hand.

    `None` is the folder that has waited forever — one with no version yet — and
    it is also what an answer nobody can read becomes, because the failure this
    door may not have is the one that stops versioning: a stamp that does not
    parse reads as "no version", and no version commits.
    """
    try:
        stamp = run(["log", "-1", "--format=%ct"]).stdout.strip()
        return float(stamp) if stamp else None
    except (OSError, ValueError):
        return None


def _elapsed(minutes: float) -> bool:
    """Whether `minutes` have gone by since the folder was last versioned.

    A folder with no version yet has waited long enough by definition: the first
    version is not something a cadence postpones.
    """
    last = last_version()
    return last is None or _now() - last >= minutes * _MINUTE


def dirty() -> bool:
    """Whether the folder carries writes no version has taken.

    The process's own counter cannot answer it: a `cli` run starts at zero, and
    the folder's dirt is older than the process asking. So the question goes to
    git, and `status --porcelain` lists exactly what the next `add --all` would
    carry — the derived files git ignores are not writes of the person's, and
    they are not dirt either. A folder git cannot answer for reads as clean,
    because what this feeds is a sentence and never a refusal.
    """
    if DISABLED:
        return False
    if state() != OWNED:
        return False
    try:
        return bool(run(["status", "--porcelain"]).stdout.strip())
    except OSError:
        return False


def stale() -> bool:
    """Whether the folder is under versioning and has fallen behind (§4, item 30).

    Three things at once, and each one is needed: the repository is AT's, there
    are writes the last version does not carry, and the interval this folder
    chose has gone by. A clean folder is never behind — there is nothing owed —
    and neither is the folder that asked for a version on every write: its writes
    are versioned as they happen, so the wait this asks about never exists.
    """
    if DISABLED:
        return False
    minutes = interval()
    return (
        minutes > EVERY_WRITE
        and state() == OWNED
        and dirty()
        and _elapsed(minutes)
    )


def phrase(where: str | None = None) -> str | None:
    """The catalog key of what a person must hear, or `None` for silence.

    The PAGE reads this, and so does the sentence `notice` prints: one home for
    the wording, because the same truth told twice is the two sentences that
    drift. Two truths arrive here, told apart by the state the rest of the module
    reads: the folder that is not under versioning at all, and the folder that IS
    and has fallen behind (`stale`).
    """
    if DISABLED:
        return None
    here = state() if where is None else where
    if here == OWNED:
        return STALE if stale() else None
    return PHRASES.get(here)


def ensure() -> str:
    """The folder's own repository, born by AT when it can be. Answers the state.

    It is safe to call on every run, and it is meant to be: a folder that gains
    git after it existed gains the history on the next start, without anybody
    asking again. A read-only run creates nothing (§3) — a verification pass
    does not leave a repository behind any more than it writes a row.
    """
    here = state()
    if DISABLED or here in (OWNED, FOREIGN) or files.readonly() or not present():
        return here
    if not _create(paths.working_folder()):
        # A git that is there and cannot do it — a permission, a read-only
        # mount — leaves the folder where it was. It is the same promise the
        # missing tool gets: the product does not exist because of git, so the
        # folder may not fall because git failed.
        return here
    print(tr("versioning.born"))
    commit(tr("versioning.commit.started"))
    return OWNED


def start(ask: Ask | None = None) -> str:
    """The folder's versioning begins: the repository, or the two ways out.

    Called where the folder is BORN and where the migration gives an existing
    folder its repository — the two moments the shape of the folder changes.
    This is the one place the question is ASKED, because the moment AT would
    have versioned is the moment the person is owed the reason it is not
    happening; after it, the folder says it is not under versioning instead of
    asking a second time.
    """
    if DISABLED:
        return state()
    here = ensure()
    if here == MISSING:
        ways_out(ask)
    elif here == FOREIGN:
        print(tr(PHRASES[FOREIGN]))
    return here


def ways_out(ask: Ask | None = None) -> str:
    """The two ways out of a machine without git (§7a's precedent).

    A yes sends the person to install it: AT says how and stops there — it does
    not install anything, because that is the person's machine and §3 spends
    nothing there. Anything else keeps the folder where it already works, with
    no versioning at all: the product does not exist because of git, and the
    folder may not fall because it is missing.
    """
    # Read here and not at the top of the file: `migrations` carries a step that
    # reads THIS module, and the two would be an import cycle (the same door
    # `services/switch.py` takes).
    from at.core import migrations  # noqa: PLC0415

    if ask is None:
        print(tr("versioning.no_git.no_tty"))
        return NO_ANSWER
    if migrations.is_yes(ask(tr("versioning.no_git.ask"))):
        print(tr("versioning.no_git.install"))
        return INSTALL
    print(tr("versioning.no_git.without"))
    return WITHOUT


def notice() -> str:
    """What every run says about the folder's versioning, and nothing when there
    is nothing to say.

    The repository is born here when it could not be born before, so a machine
    that gained git gains the history by itself. What is said is the STATE and
    never a question: the question is the birth's and the migration's, and a
    folder that answers the same one every run is a folder nagging. The folder
    that IS versioned and has fallen behind is the third thing said here, and it
    is the one a `list` owes: a wait nobody names is a history quietly missing.
    """
    if DISABLED:
        return state()
    here = ensure()
    key = phrase(here)
    if key:
        print(tr(key))
    return here


def pending() -> bool:
    """Whether this process wrote anything the last commit did not carry.

    It is the single writer's count against what was committed, and it is what
    makes the cadence a thing a test can see instead of a promise. With the
    periodic default it is TRUE between versions, and that is the cadence
    working: what the folder owes is the next version, and not one per write.
    """
    return files.writes() != _committed


def commit(message: str) -> bool:
    """A version of what the folder now is, named by the action that made it.

    `False` — and no git call at all — when there is nothing to version: the
    repository is not AT's, the run is read-only, the process wrote nothing since
    the last commit, or the folder's cadence is periodic and the interval it
    chose has not gone by yet (§4, item 30). That last guard is what makes a
    CADENCE of the commit: the writes waiting for it are not lost, and the next
    version carries all of them.

    Identity travels per call and is never written into the folder's config:
    nothing of the person's is touched to make AT's commits possible.
    """
    global _committed

    if DISABLED:
        return False
    minutes = interval()
    if (
        state() != OWNED
        or files.readonly()
        or files.writes() == _committed
        or (minutes > EVERY_WRITE and not _elapsed(minutes))
    ):
        return False
    try:
        # `--quiet` answers with the exit code and nothing else: 0 is "nothing
        # staged", and that is an action that rewrote the same bytes — a version
        # of nothing, which is not a version.
        run(["add", "--all"])
        if run(["diff", "--cached", "--quiet"]).returncode == 0:
            _committed = files.writes()
            return False
        written = run([
            "-c", f"user.name={AUTHOR}",
            "-c", f"user.email={MAIL}",
            "commit", "--quiet", "--message", message,
        ])
    except OSError:
        # A git that breaks under a running AT — taken off the PATH, a
        # permission, a full disk — does not bring the ACTION down: what the
        # person asked for is already written, and losing the version is not
        # losing the write. The folder goes on, unclean, and says so.
        return False
    if written.returncode == 0:
        _committed = files.writes()
    return written.returncode == 0


def commit_file(rel: str) -> bool:
    """A file of the person's was written — the version named by its path.

    The prose layer is the other door that changes the folder (§4): a document
    saved into `Arquivos/` is the very write this item was felt on, and the path
    is the name whoever reads `git log` is looking for. The sentence is composed
    here and not there, because `prose` answers with catalog KEYS and never
    speaks a language of its own.

    The path is written with the folder's own name in front — `Arquivos/nota.md`
    — because that is where the file IS: what the prose layer hands over is
    relative to its root, and a version that said `nota.md` would name a file
    the reader cannot find.
    """
    return commit(tr("versioning.commit.file", path=_prose_path(rel)))


def _prose_path(rel: str) -> str:
    return f"{paths.prose_dir().name}/{rel}"


def commit_created(rel: str) -> bool:
    """A file or folder was BORN in the prose folder (TASK-120, fatia 5/7) —
    distinct from `commit_file`'s "written", which a birth is not.
    """
    return commit(tr("versioning.commit.created", path=_prose_path(rel)))


def commit_renamed(frm: str, rel: str) -> bool:
    """A file or folder of the prose folder changed name or place."""
    return commit(tr(
        "versioning.commit.renamed", frm=_prose_path(frm), path=_prose_path(rel)
    ))


def commit_deleted(rel: str) -> bool:
    """A file or folder LEFT the prose folder."""
    return commit(tr("versioning.commit.deleted", path=_prose_path(rel)))


def reset() -> None:
    """Forget both counters — the writes' and what they committed. The tests'
    door, like `files.reset_writes`, and nothing in the product calls it."""
    global _committed

    files.reset_writes()
    _committed = 0


def generated_dirs() -> tuple[Path, ...]:
    """The ONE folder AT itself fills, and a person never types into: the state
    every service writes — the Caddy and the Authelia it unpacks, the push, the
    gitleaks, the Jev cache — under `App/services/` (§7, item 51).

    It used to be TWO — `App/caddy/` beside `App/services/` — because the hosted
    path scattered its services across `App/` and only the container path knew
    `App/services/`. The services share the one house now, so the list collapsed
    to the folder that holds them all, read off `paths.services_dir` and not
    retyped as a second list: this is the ONE place that says "AT wrote it, and
    nobody typed it", and both `ignore_text` (what git leaves out) and
    `at.core.scanner` (what a scan skips) read it rather than carrying their own
    copy.
    """
    return (paths.services_dir(),)


def ignore_text() -> str:
    """The ignore AT generates, written the way §3 writes what it generates: in
    the active language, and with the binary names read off `paths` and never
    spelled again here.

    Both extensions of both artifacts, and not only this platform's: the folder
    is carried between machines (§3), and an ignore that stopped covering the
    binary the day the folder crossed to Windows is a history with a 30 MB
    executable in it.
    """
    artifacts = "\n".join(
        name + extension
        for name in (paths.ARTIFACT, paths.DEPLOY)
        for extension in (paths.WINDOWS, paths.UNIX)
    )
    generated = "\n".join(
        f"{where.relative_to(paths.working_folder()).as_posix()}/"
        for where in generated_dirs()
    )
    return tr("versioning.ignore.body", artifacts=artifacts, generated=generated)


def _create(root: Path) -> bool:
    """`git init`, the mark, and the ignore AT generates.

    `False` when git is there and could not do it — the caller answers that the
    same way it answers the tool being absent, because the folder may not fall
    over either one.

    The ignore is written only where there is none: a `.gitignore` a person
    wrote is a person's edit, and a migration never overwrites one (§3) — it is
    said, and the folder keeps it. What that costs is the derived files staying
    in the history, which is the price of the person's file being theirs.
    """
    try:
        run(["init", "--quiet"])
        files.atomic_write_text(owner_mark(root), f"{AUTHOR}\n")
        where = root / IGNORE
        if where.exists():
            print(tr("versioning.ignore.kept"))
            return True
        files.atomic_write_text(where, ignore_text())
    except OSError:
        return False
    return True
