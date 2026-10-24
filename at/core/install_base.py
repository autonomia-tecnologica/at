"""`install` — the record, the directory and the mark: what the other install modules share."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from at.core import files, paths

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

# Windows has no `symlink` a person's own account can write without asking an
# administrator, so the word there is not a link but a tiny `.cmd` that
# forwards to the artifact — written fresh every run and never a copy of the
# binary (§3: nothing is copied). The extension is not a choice: it is what
# makes the file a command `cmd.exe` runs at all.
WIN32 = "win32"
CMD_EXTENSION = ".cmd"
CMD_COMMENT = "::"

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


def _mine(link: Path, artifact: str) -> bool:
    """Whether that link is one AT wrote: a symlink aimed at an artifact's name."""
    return link.is_symlink() and link.readlink().name == artifact


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


def _is(left: Path, right: Path) -> bool:
    """Whether two paths name the same thing, with the links followed."""
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


# ------------------------------------------------------------ the completion ---


MARK_TEXT = "{word}: written by `{word} install`; an edit here is overwritten"


def mark(word: str, comment: str = "#") -> str:
    """The line that makes a completion file — or the Windows shim — AT's.

    NOT translated, and deliberately: this is a MARK and not a sentence — the
    same kind of thing as the `OWNER` written inside the repository AT created
    —, and what reads it is `uninstall` deciding whether the file is AT's to
    take back. A mark that moved with the language would be a file the next
    language could not recognise, which is the one thing a mark may not be.

    `comment` is the one thing that DOES change with the file: `#` is a
    comment to bash and zsh, and a `.cmd` reads it only behind `::`. `_marked`
    looks for the bare text and never for one comment style, so both still
    answer to the same mark.
    """
    return f"{comment} {MARK_TEXT.format(word=word)}\n"


def _written(word: str) -> list[str]:
    entry = record().get(word)
    return list(entry.get("wrote", [])) if isinstance(entry, dict) else []


def _marked(path: Path, word: str) -> bool:
    """Whether that file carries AT's mark — the completion's own evidence,
    and the Windows shim's: a `.cmd` is not a symlink `_mine` can read, so the
    mark inside it is the only thing that says the file is AT's."""
    try:
        return path.is_file() and MARK_TEXT.format(word=word) in path.read_text(encoding="utf-8")
    except OSError:
        return False
