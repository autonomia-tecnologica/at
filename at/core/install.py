"""`install`: the artifact puts itself where commands are found (§3, item 28).

Using the artifact means keeping the file somewhere and typing its path — or a
shim written by hand to avoid that, which is what the machine this was written
on had, aimed at one checkout and pinning the folder. The product's own answer
is `install`.

**What it creates is a SYMLINK to the artifact inside the Working Folder**, and
nothing is copied. That one decision is the whole of the update story: the next
release replaces the file in the folder and the link follows it, so there is no
copy to find and no second file to leave behind. What the install writes outside
the folder is a link and the shell's completion — and a link is not state.

**The one thing that IS remembered lives in `App/install.json`**: the directory
the person chose, when they chose one. A link needs no memory; a directory
chosen once would otherwise have to be chosen again at every install, and the
default would leave the second link standing. The record is the folder's, like
everything else AT writes (§3).

**This is the word that runs before a folder exists.** Every other invocation
confirms a Working Folder first, because everything else is ABOUT the folder;
this one is about the FILE and where it sits. So it reads the folder from where
the artifact is (§3: the binary's folder), links to it, and says plainly when
that folder is not AT's yet — and then it records nothing, because there is
nowhere of AT's to record it in, and the person is told what that costs.

**The command is `at-cli`, and the install still says what it finds.** `at` is a
command a UNIX machine may already answer to — the `at`/`atd` job scheduler, one
package away and in this distribution's own repositories — and the artifact is
named `at-cli` so that the product does not take a name that is not only its own.
That settles the NAME and not the DIRECTORY: a link can still land where another
command of its own name already answers, and there the install does not refuse
and does not choose — it writes the link and SAYS which directory wins in the
order of `PATH`, because installing is an explicit request on the person's own
machine and whoever decides is whoever will live with it (§3, Permissão de
acesso).

**The completion is generated from the word tree**, which is the one declaration
the help reads too (§5), so a word that is offered is a word that completes and
neither can drift from the other. It offers WORDS and never flags: a flag list
written here would be a second declaration of what the tree declares.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path

from at.core import files, paths, settings
from at.i18n import tr

# The words a completion offers, as pairs of (word, the words under it). Plain
# tuples and not the tree's own `Node`: the trees belong to the surfaces, and
# the core must not reach into one — the shape is all this needs.
Words = Sequence[tuple[str, tuple[str, ...]]]

# Where a command is found when nothing says otherwise: the XDG one, and the
# directory a UNIX shell already carries on the PATH.
DEFAULT_BIN = (".local", "bin")

# The record of what was installed where. In `App/`, because it is state and
# state lives in `App/` (§3) — and because it is the folder's, the memory
# travels with the folder instead of being a second thing to keep in step.
RECORD = "install.json"

# The two shells whose completion the product knows how to write, and the
# directory each one reads it from, under the user's home. bash-completion looks
# a completion up BY THE COMMAND'S NAME under its own data directory and finds
# it with no configuration at all; zsh reads a file named `_<command>` off its
# `fpath`, and a person's own directory is not on it until the person puts it
# there — which is why the install PRINTS that line instead of editing a shell
# configuration file that is not AT's to edit.
COMPLETIONS: dict[str, tuple[str, ...]] = {
    "bash": (".local", "share", "bash-completion", "completions"),
    "zsh": (".local", "share", "zsh", "site-functions"),
}

BASH = "bash"
ZSH = "zsh"

# The outcomes, the way `environment` and `versioning` have them: this module
# speaks and answers, and the `cli` decides what an exit code is.
DONE = "done"
ALREADY = "already"
HELD = "held"
MISSING = "missing"
REMOVED = "removed"
NOTHING = "nothing"


# ------------------------------------------------------------- the directory ---

def record_path() -> Path:
    return paths.app_dir() / RECORD


def record() -> dict:
    """The record as it is on disk; `{}` for a folder that has none.

    A file that does not parse reads as empty, and this is the one place that
    treats it so on purpose: what this file holds is AT's own bookkeeping and
    nothing of the person's — unlike `settings.json`, where an unreadable file
    is reported and never replaced. Losing it costs one install going to the
    default; rewriting it costs nothing anybody wrote.
    """
    try:
        data = files.read_json(record_path(), {})
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def remembered(word: str) -> str | None:
    """The directory the last install of that word recorded, if any."""
    entry = record().get(word)
    return entry.get("bin") if isinstance(entry, dict) else None


def where(word: str, flag: str | None = None) -> Path:
    """The directory the link is written into.

    The flag first, then what the last install remembered, then the default —
    one answer per question, and the memory in the middle is what makes a
    directory chosen once stay chosen instead of being asked for again and the
    default leaving a second link behind.
    """
    if flag:
        return Path(flag).expanduser()
    known = remembered(word)
    if known:
        return Path(known).expanduser()
    return Path.home().joinpath(*DEFAULT_BIN)


def target(artifact: str) -> Path:
    """Where the link points: the artifact, in the folder the binary is in.

    §3: the binary lives in the folder and that folder is the Working Folder —
    resolved from where the ARTIFACT is and never from where the shell happened
    to be standing, which from the binary is the same place and from a checkout
    is not.
    """
    return paths.working_folder() / artifact


# ------------------------------------------------------------------ the act ---

def parse(rest: Sequence[str]) -> tuple[str | None, bool]:
    """What the word takes: `[--bin <directory>]`, and nothing else.

    `(flag, ok)`, and the flag is the person's own spelling: the resolution that
    turns it into a directory is `where`'s, so both `cli`s read the same rule.
    """
    flag: str | None = None
    args = list(rest)
    while args:
        head, args = args[0], args[1:]
        if head != "--bin" or not args:
            return None, False
        flag, args = args[0], args[1:]
    return flag, True


def act(
    word: str,
    artifact: str,
    words: Words,
    bin_flag: str | None = None,
    shell: str | None = None,
) -> str:
    """Put the artifact where commands are found, and say what it did.

    `word` is the command (`at-cli`, `at-deploy`) and `artifact` is the FILE in
    the folder it points at — two names, because they are two different names:
    the command is what a person types and the file is what the release
    publishes, and on Windows they differ by the `.exe`.
    """
    into = where(word, bin_flag)
    link = into / word
    artifact_at = target(artifact)

    if not artifact_at.is_file():
        # The link would be born pointing at nothing, and a link that means
        # nothing is worse than no link: it answers the shell with a failure that
        # names the link and not the reason.
        print(tr("install.no_artifact", artifact=artifact,
                 folder=paths.working_folder(), word=word))
        return MISSING

    obstacle = _obstacle(link, artifact)
    if obstacle is not None:
        key, values = obstacle
        print(tr(key, **values))
        return HELD

    already = _same(link, artifact_at)

    files.guard(link)
    try:
        into.mkdir(parents=True, exist_ok=True)
        # Written BESIDE the link and renamed onto it, the way every text this
        # product rewrites is (`files.atomic_write_text`): a crash in the middle
        # leaves the link that was already there, never a link pointing nowhere
        # — which on a `PATH` is a command that stopped working.
        temporary = link.with_name(link.name + ".tmp")
        temporary.unlink(missing_ok=True)
        os.symlink(artifact_at, temporary)
        os.replace(temporary, link)
    except OSError:
        # A directory that cannot be written — a permission, a read-only mount.
        # The install does not bring the machine down over its own directory.
        print(tr("install.no_dir", bin=into))
        return HELD
    print(tr("install.already" if already else "install.done",
             word=word, link=link, target=artifact_at))

    _announce(word, into, link)

    completion = _write_completion(word, words, shell)
    wrote = [link] + ([completion] if completion else [])

    if settings.exists():
        _remember(word, into, wrote)
        print(tr("install.recorded", where=record_path()))
    else:
        # A folder that is not AT's has nowhere of AT's to keep the record, and
        # creating `App/` here would be creating a Working Folder through the
        # back door — which is the one thing `boot` asks before (§3).
        print(tr("install.no_folder", settings=paths.settings_file(), bin=into))

    return DONE


def _obstacle(link: Path, artifact: str) -> tuple[str, dict] | None:
    """What stands in the way, when it is not AT's to move.

    The test is the NAME the link points at, and it answers two cases at once:
    a link of AT's that is current is not in the way, and neither is one whose
    target was DELETED — the folder moved and the binary was left behind, and
    the link is still AT's because AT is the only thing that writes a link named
    after its own artifact. In a collision the person's edit rules (§3): a file,
    or a link aimed somewhere else, is not touched and the install says so.
    """
    if not link.is_symlink() and not link.exists():
        return None
    if _mine(link, artifact):
        return None
    if link.is_symlink():
        return "install.held.link", {"link": link, "other": link.readlink()}
    return "install.held.file", {"link": link}


def _mine(link: Path, artifact: str) -> bool:
    """Whether that link is one AT wrote: a symlink aimed at an artifact's name."""
    return link.is_symlink() and link.readlink().name == artifact


def _same(link: Path, artifact_at: Path) -> bool:
    try:
        return link.resolve() == artifact_at.resolve()
    except OSError:
        return False


# --------------------------------------------------------------- the memory ---

def _remember(word: str, into: Path, wrote: Sequence[Path]) -> None:
    data = record()
    data[word] = {"bin": str(into), "wrote": [str(path) for path in wrote]}
    _save(data)


def forget(word: str) -> None:
    """Take that word's entry out, and the file with it when it empties."""
    data = record()
    if word not in data:
        return
    files.guard(record_path())
    del data[word]
    if data:
        _save(data)
    else:
        record_path().unlink(missing_ok=True)


def _save(data: dict) -> None:
    files.atomic_write_text(
        record_path(),
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


# ------------------------------------------------------------------ the name ---

def _announce(word: str, into: Path, link: Path) -> None:
    """Which of two commands of the same name answers, and it is the PATH's order.

    AT installs and then says; it never refuses, because the machine is the
    person's and two names can live in two directories for as long as they want
    to. What nobody can read off a file they did not write is which one wins.
    """
    other = _foreign(word, link)
    here = _order(into)
    if other is None:
        if here is None:
            # The link is written and will not be found: the directory is not on
            # the PATH at all, and adding it is the person's edit to make.
            print(tr("install.off_path", bin=into, word=word))
        return
    there = _order(other.parent)
    if there is not None and (here is None or there < here):
        print(tr("install.collision.shadowed", word=word, other=other, bin=into))
    else:
        print(tr("install.collision.shadowing", word=word, other=other, bin=into))


def _path_entries() -> list[Path]:
    return [
        Path(entry).expanduser()
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry
    ]


def _order(directory: Path) -> int | None:
    """Where that directory sits on the PATH — the whole of who wins.

    `None` for a directory that is not on it at all, which is a different
    answer from sitting at the end: the one means nobody finds the command, and
    the other means somebody else is found first.
    """
    for index, entry in enumerate(_path_entries()):
        if _is(entry, directory):
            return index
    return None


def _foreign(word: str, link: Path) -> Path | None:
    """The first command of that name on the PATH that is not AT's own link.

    Scanned and not asked of `which`, because `which` answers with the winner
    and what this has to name is the LOSER: the tool that AT shadows, which is
    the one a person looking at their PATH order would not find.
    """
    for entry in _path_entries():
        candidate = entry / word
        if _is(candidate, link):
            continue
        if (candidate.is_symlink() or candidate.is_file()) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _is(left: Path, right: Path) -> bool:
    """Whether two paths name the same thing, with the links followed."""
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


# ------------------------------------------------------------ the completion ---

def shell_name() -> str:
    """The shell the person is in, by its own name — `$SHELL`'s last word.

    `/bin/zsh` and `zsh` are the same shell: what is read is the name of the
    program, and never the directory it happens to be installed under.
    """
    return Path(os.environ.get("SHELL", "")).name


def completion_path(word: str, shell: str) -> Path | None:
    """Where that shell reads the completion of that word.

    The FILE name is not a choice: bash-completion loads a file by the command's
    name, and zsh reads a file whose name is the command's with an underscore in
    front. `None` for a shell whose completion has no home the product knows.
    """
    directory = _completion_dir(shell)
    if directory is None:
        return None
    return directory / (f"_{word}" if shell == ZSH else word)


def _completion_dir(shell: str) -> Path | None:
    parts = COMPLETIONS.get(shell)
    return Path.home().joinpath(*parts) if parts else None


def _write_completion(word: str, words: Words, shell: str | None) -> Path | None:
    """The completion, written where the shell reads it — or nothing, and said.

    No terminal to read `$SHELL` from is not a failure: a completion is what
    makes the words reachable without a path, and it is not what makes the
    command work. So an unknown shell is a sentence and nothing else — the link
    is already written by the time this runs.
    """
    name = shell_name() if shell is None else shell
    if not name:
        print(tr("install.completion.no_shell"))
        return None
    path = completion_path(word, name)
    if path is None:
        print(tr("install.completion.unknown", shell=name))
        return None
    files.atomic_write_text(path, completion_text(word, words, name))
    print(tr("install.completion.written", shell=name, path=path))
    if name == ZSH:
        # zsh reads a file off its `fpath`, and the person's own directory is
        # not on it by default. AT prints the line and does not write it: the
        # shell's configuration file is the person's, and a product that edited
        # it would be a product that has to find and undo its own edit later.
        print(tr("install.completion.fpath", folder=path.parent))
    return path


# The variable zsh ties its `fpath` array to, and the one this module can ask
# a CHILD process about: `fpath` itself is a shell-local array, and a person's
# `.zshrc` has to export it (or `typeset -g -x FPATH`) for a process AT starts
# to see it at all. A shell that never exports it answers the same as one that
# has not been fixed yet — the safe side is asking again.
FPATH_ENV = "FPATH"


def fpath_needed(word: str) -> Path | None:
    """The zsh completion's directory, while the person has not put it on
    `fpath` yet — or `None` when there is nothing to remind about.

    Asked on every run of `version`, and not only right after `install`: the
    shell reads its own `fpath` once, at start, and a completion written a
    minute — or a week — ago is not on it until the `.zshrc` line is added AND
    the shell is restarted, which is a gap `install`'s own one-time print
    cannot close on its own.

    A folder with no zsh completion written at all has nothing to remind about
    (`None`, the same answer `completion_path` gives a shell with no home),
    and neither does one whose directory is already in the INHERITED
    `$FPATH` — the heuristic this door has: a directory a person's `.zshrc`
    already put there is a line already fixed, and asking again would be
    noise nobody needs. `$FPATH` unset or not carrying it yet reads as "not
    resolved", which is the floor this reminder cannot go below: repeating a
    line that was already fixed costs a sentence, and going quiet on one that
    was not costs the completion itself.
    """
    path = completion_path(word, ZSH)
    if path is None or not path.is_file():
        return None
    directory = path.parent
    inherited = os.environ.get(FPATH_ENV, "")
    entries = [Path(entry).expanduser() for entry in inherited.split(os.pathsep) if entry]
    if any(_is(entry, directory) for entry in entries):
        return None
    return directory


def mark(word: str) -> str:
    """The line that makes a completion file AT's.

    NOT translated, and deliberately: this is a MARK and not a sentence — the
    same kind of thing as the `OWNER` written inside the repository AT created
    —, and what reads it is `uninstall` deciding whether the file is AT's to
    take back. A mark that moved with the language would be a file the next
    language could not recognise, which is the one thing a mark may not be.
    """
    return f"# {word}: written by `{word} install`; an edit here is overwritten\n"


def completion_text(word: str, words: Words, shell: str) -> str:
    """The completion script for one artifact, in one shell.

    Generated from the tree and never from a list kept here: the words offered
    are the words the help offers, and the day a word arrives it arrives in
    both. Only the comment is the person's — the rest is the shell's own
    language, and it is not translated for the same reason the command words
    are not (§3).
    """
    note = f"# {tr('install.note', word=word)}\n"
    head = f"{mark(word)}{note}"
    if shell == ZSH:
        return f"#compdef {word}\n{head}{_zsh(words)}\n"
    return f"{head}{_bash(word, words)}\n"


def _bash(word: str, words: Words) -> str:
    function = "_" + word.replace("-", "_") + "_complete"
    roots = " ".join(name for name, _ in words)
    lines = [
        f"{function}() {{",
        '  local cur="${COMP_WORDS[COMP_CWORD]}"',
        "  local offer",
        '  case "${COMP_WORDS[1]}" in',
    ]
    for name, under in words:
        if under:
            lines.append(f"    {name}) offer=\"{' '.join(under)}\" ;;")
    lines += [
        f'    *) offer="{roots}" ;;',
        "  esac",
        '  COMPREPLY=($(compgen -W "$offer" -- "$cur"))',
        "}",
        f"complete -F {function} {word}",
    ]
    return "\n".join(lines)


def _zsh(words: Words) -> str:
    roots = " ".join(name for name, _ in words)
    lines = ["local -a offer", 'case "${words[2]}" in']
    for name, under in words:
        if under:
            lines.append(f"  {name}) offer=({' '.join(under)}) ;;")
    lines += [
        f"  *) offer=({roots}) ;;",
        "esac",
        "_describe 'word' offer",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- the undo ---

def undo(
    word: str,
    artifact: str,
    bin_flag: str | None = None,
    shell: str | None = None,
) -> str:
    """Take back what the install put there, and only that.

    The candidates are the record's — an exact list of what was written — plus
    the two paths this run would write, because an install made in a folder that
    is not AT's has no record and still has to be undoable.

    Every candidate is checked before it goes, and that check is the whole rule
    one more time: a link aimed at the artifact's own name is AT's, and a
    completion carrying AT's mark is AT's. Anything else is the person's, and it
    stays — with a sentence saying so, because "nothing happened" and "I refused
    to touch your file" are different answers.
    """
    files.guard(where(word, bin_flag))

    candidates = [Path(path) for path in _written(word)]
    link = where(word, bin_flag) / word
    if link not in candidates:
        candidates.append(link)
    name = shell_name() if shell is None else shell
    completion = completion_path(word, name) if name else None
    if completion is not None and completion not in candidates:
        candidates.append(completion)

    removed = held = 0
    for path in candidates:
        if not path.is_symlink() and not path.exists():
            continue
        if not _mine(path, artifact) and not _marked(path, word):
            print(tr("install.uninstall.kept", path=path))
            held += 1
            continue
        files.guard(path)
        path.unlink()
        print(tr("install.uninstall.removed", path=path))
        removed += 1

    if not removed and not held:
        print(tr("install.uninstall.nothing", word=word, bin=where(word, bin_flag)))
        return NOTHING
    forget(word)
    return HELD if held else REMOVED


def _written(word: str) -> list[str]:
    entry = record().get(word)
    return list(entry.get("wrote", [])) if isinstance(entry, dict) else []


def _marked(path: Path, word: str) -> bool:
    """Whether that file carries AT's mark — the completion's own evidence."""
    try:
        return path.is_file() and mark(word).strip() in path.read_text(encoding="utf-8")
    except OSError:
        return False
