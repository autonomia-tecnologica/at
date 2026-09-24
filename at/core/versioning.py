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
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Callable

from at.core import files, paths
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

# What a person must hear about each state, and `bare` is deliberately absent: a
# folder with no repository on a machine that has git is a folder about to have
# one (`ensure`), not a state worth a sentence.
PHRASES = {FOREIGN: "versioning.foreign", MISSING: "versioning.missing"}

# The three outcomes of the offer, the way §7a's has them.
INSTALL = "install"
WITHOUT = "without"
NO_ANSWER = "no_answer"

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


def phrase(where: str | None = None) -> str | None:
    """The catalog key of what a person must hear, or `None` for silence.

    The PAGE reads this, and so does the sentence `notice` prints: one home for
    the wording, because the same truth told twice is the two sentences that
    drift.
    """
    return PHRASES.get(state() if where is None else where)


def ensure() -> str:
    """The folder's own repository, born by AT when it can be. Answers the state.

    It is safe to call on every run, and it is meant to be: a folder that gains
    git after it existed gains the history on the next start, without anybody
    asking again. A read-only run creates nothing (§3) — a verification pass
    does not leave a repository behind any more than it writes a row.
    """
    here = state()
    if here in (OWNED, FOREIGN) or files.readonly() or not present():
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
    folder that answers the same one every run is a folder nagging.
    """
    here = ensure()
    key = PHRASES.get(here)
    if key:
        print(tr(key))
    return here


def pending() -> bool:
    """Whether this process wrote anything the last commit did not carry.

    It is the single writer's count against what was committed, and it is what
    makes "the folder is never left dirty" a thing a test can see instead of a
    promise.
    """
    return files.writes() != _committed


def commit(message: str) -> bool:
    """A version of what the folder now is, named by the action that made it.

    `False` — and no git call at all — when there is nothing to version: the
    repository is not AT's, the run is read-only, or the process wrote nothing
    since the last commit. That last guard is `files.writes` and not a guess: a
    `list` costs nothing, and an action that wrote is exactly the case this door
    exists for.

    Identity travels per call and is never written into the folder's config:
    nothing of the person's is touched to make AT's commits possible.
    """
    global _committed

    if state() != OWNED or files.readonly() or files.writes() == _committed:
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
    return commit(tr("versioning.commit.file", path=f"{paths.prose_dir().name}/{rel}"))


def reset() -> None:
    """Forget both counters — the writes' and what they committed. The tests'
    door, like `files.reset_writes`, and nothing in the product calls it."""
    global _committed

    files.reset_writes()
    _committed = 0


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
    return tr("versioning.ignore.body", artifacts=artifacts)


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
