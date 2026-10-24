"""`install` — which command of the same name wins on the `PATH`."""

from __future__ import annotations

import os
from pathlib import Path

from at.core.install_base import _is
from at.i18n import tr


def _announce(word: str, into: Path, link: Path) -> None:
    """Which of two commands of the same name answers, and it is the PATH's order.

    AT installs and then says; it never refuses, because the machine is the
    person's and two names can live in two directories for as long as they want
    to. What nobody can read off a file they did not write is which one wins.
    """
    other = _foreign(link.name, link)
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


def _foreign(name: str, link: Path) -> Path | None:
    """The first command of that FILE name on the PATH that is not AT's own link.

    Scanned and not asked of `which`, because `which` answers with the winner
    and what this has to name is the LOSER: the tool that AT shadows, which is
    the one a person looking at their PATH order would not find.

    `name` is `link.name` and not the command word: on Windows that is
    `at-cli.cmd`, and a scan for the extensionless `at-cli` would never find
    what actually answers to the typed command there.
    """
    for entry in _path_entries():
        candidate = entry / name
        if _is(candidate, link):
            continue
        if (candidate.is_symlink() or candidate.is_file()) and os.access(candidate, os.X_OK):
            return candidate
    return None
