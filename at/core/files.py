"""The single writer, and the read-only switch.

Every file AT rewrites goes through `atomic_write_text`. Three properties come
from that one place:

- a crash mid-write leaves the previous content intact, never half a file;
- `$AT_READONLY` refuses **before anything is touched**, so a verification run
  cannot mutate the Working Folder through any engine;
- every write is **counted**, and the count is what the versioning reads
  (`versioning.pending`): how much this process wrote since the last commit.

The switch belongs to the write, not to the command's name. A list of "words
that mutate" is a list somebody forgets to extend; guarding the one writer covers
every engine at once, including the ones not written yet. The COUNT is the same
argument from the other side: an action that writes and does not commit leaves
the count where it was, and that is a thing a test can see.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_READONLY = "AT_READONLY"

_TRUE_WORDS = ("1", "true", "yes", "on")

# How many writes this process has made. Module state on purpose: the count is
# about a RUN — one command, one request — and a fresh process starts at zero.
_writes = 0


def writes() -> int:
    """How many times this process wrote, every one of them through here."""
    return _writes


def reset_writes() -> None:
    """Forget the count. The tests' door, and nothing in the product calls it."""
    global _writes
    _writes = 0


class ReadOnly(Exception):
    """A write was attempted while the read-only switch is on.

    `where` names the file the write would have touched — what a reader needs to
    know, and what a message has to say to be worth anything.
    """

    def __init__(self, where: object):
        super().__init__(str(where))
        self.where = where


def readonly() -> bool:
    return os.environ.get(ENV_READONLY, "").strip().lower() in _TRUE_WORDS


def guard(where: object) -> None:
    """Refuse a write the switch forbids, for the writes that are not text.

    The switch belongs to the write and not to the command's name, and a
    writer that skipped it would be the one hole in the rule. This is the
    second door: `atomic_write_text` is for content, and this is for what has
    no content to write through it — a symlink, a directory, a removal. Both
    read the same switch.
    """
    if readonly():
        raise ReadOnly(where)


def atomic_write_text(path: Path, text: str, mode: int | None = None) -> None:
    """Write `text` to `path`, atomically, or refuse under the read-only switch.

    The temporary file is written BESIDE the target and renamed onto it: `os.replace`
    on one filesystem is atomic, so a half-written store never exists under the
    name anything reads.

    `mode` is for the files whose CONTENT is a credential, and it exists because
    the default is the umask's — right for everything a person reads, wrong for a
    secret. The permission goes on the TEMPORARY file and `os.replace` carries it
    onto the target: a `chmod` afterwards would leave a window in which the value
    is written and the world can still read it.
    """
    global _writes

    guard(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    # `newline="\n"` because text mode turns every LF into CRLF on Windows, and
    # the data is POSIX on every host (§3, Portabilidade).
    temporary.write_text(text, encoding="utf-8", newline="\n")
    if mode is not None:
        os.chmod(temporary, mode)
    os.replace(temporary, path)
    # Counted AFTER the replace, and only then: what this counts is content that
    # is on disk, which is exactly what a version has to carry.
    _writes += 1


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """`atomic_write_text`'s twin, for content that is not text — a generated
    DOCX or PDF (`at/convert/`), never a JSONL row or a prose file, which stay
    on the text door so the `newline="\n"` promise keeps covering them.

    Same shape, same guarantee: the temporary file sits BESIDE the target and
    `os.replace` is what makes it appear, whole or not at all.
    """
    global _writes

    guard(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)
    _writes += 1


def mark_write() -> None:
    """Count a write that did not go through `atomic_write_text` — for content
    that is not a single file written whole. A restore's tar extraction is many
    files in one act, and the cadence only needs to know ONE write happened
    since the last version, not how many files carried it. The switch is the
    caller's to have asked already (`guard`), before the write it counts here.
    """
    global _writes
    _writes += 1


def read_json(path: Path, default: object = None) -> object:
    """A JSON file as it is, or `default` when it is absent or unreadable.

    Corrupt is not the same as absent: a file that exists and does not parse is
    reported, never silently replaced — rewriting it would destroy whatever a
    person had put there.
    """
    import json

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default
    return json.loads(text)
