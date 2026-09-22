"""The single writer, and the read-only switch.

Every file Bill rewrites goes through `atomic_write_text`. Two properties come
from that one place:

- a crash mid-write leaves the previous content intact, never half a file;
- `$BILL_READONLY` refuses **before anything is touched**, so a verification run
  cannot mutate the Working Folder through any engine.

The switch belongs to the write, not to the command's name. A list of "words
that mutate" is a list somebody forgets to extend; guarding the one writer covers
every engine at once, including the ones not written yet.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_READONLY = "BILL_READONLY"

_TRUE_WORDS = ("1", "true", "yes", "on")


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


def atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path`, atomically, or refuse under the read-only switch.

    The temporary file is written BESIDE the target and renamed onto it: `os.replace`
    on one filesystem is atomic, so a half-written store never exists under the
    name anything reads.
    """
    if readonly():
        raise ReadOnly(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    # `newline="\n"` because text mode turns every LF into CRLF on Windows, and
    # the data is POSIX on every host (README §3, Portabilidade).
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


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
