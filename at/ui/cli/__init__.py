"""The command line: the surface that reaches everything AT can do (§5).

Dispatch is deliberately small and hand-rolled. A framework would put the word
list in a decorator, and the word list has one home already — `tree.py`, which
the help reads too. The table words are not here either: they are generated from
`data/schema/`, every invocation.

Exit codes: `0` success · `1` refused or failed · `2` usage error.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from at import __version__
from at.core import boot, install, jobs, paths, permissions
from at.data import schema
from at.i18n import tr
from at.ui import ask as door  # noqa: F401 — the name stays reachable here
from at.ui.ask import OK, REFUSED, USAGE
from at.ui.cli import jsonout, tree
from at.ui.cli.common import Ask
from at.ui.cli.common import reject as _reject
from at.ui.cli.file_words import _backup, _convert, _installed, _license, _search
from at.ui.cli.object_words import _OWN_ACTS, _ask, _job, _setting, _table  # noqa: F401
from at.ui.cli.person_words import _admin, _assist, _lang
from at.ui.cli.webapp_word import _webapp


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)
    if jsonout.FLAG in words:
        # `--json` is global: it swaps what is PRINTED, in any position, and
        # nothing about what runs (`jsonout`).
        return jsonout.run([w for w in words if w != jsonout.FLAG], _dispatch)
    return _dispatch(words)


def _dispatch(words: list[str]) -> int:
    # `install` and `uninstall` run BEFORE the Working Folder is confirmed, and
    # they are the only words that do. Every other word is ABOUT the folder —
    # what it holds, how it is spoken — and the folder belongs to the binary, so
    # no word could run before the folder is AT's. These two are about the FILE
    # and where it is found, and the folder is only where the file happens to
    # be: confirming one, or worse, creating one so the install has somewhere to
    # write, is exactly what §3's first run asks before and never assumes.
    if words[:1] in (["install"], ["uninstall"]):
        return _installed(words[0], words[1:])

    if not words:
        # The Control Panel is a screen for whoever does not type commands
        # (§5) — and it is this one now (TASK-169, fatia 1/3): the wordless
        # command opens the browser on the app itself, on a port nobody
        # types and behind a token nobody but that browser ever saw.
        # Managing AT stays in the `cli`, where a person and a machine reach
        # the same door — `help` still prints the tree this used to.
        #
        # **And it runs BEFORE `ensure_working_folder`, on purpose** (TASK-169,
        # fatia 2/3): that gate asks in the TERMINAL, and the wordless command
        # is exactly the one with none to ask in. A folder that does not exist
        # yet is not refused here — the browser asks instead, the same
        # question, on the one screen this mode has (`webapp.entry_payload`'s
        # `folder`, `/api/folder`).
        from at.ui.webapp import local

        return local.run()

    if not boot.ensure_working_folder():
        return REFUSED

    word, rest = words[0], words[1:]

    if word in ("help", "--help", "-h"):
        if rest:
            return _reject(word)
        print(tree.as_text())
        return OK

    if word in ("version", "--version", "-V"):
        if rest:
            return _reject(word)
        print(tr("cli.version.line", version=__version__))
        jsonout.attach("version", __version__)
        # A completion written for zsh is not on its `fpath` until the person's
        # `.zshrc` puts it there — `install` said it once, and there is no
        # terminal-free way to know it was read, let alone acted on. `version`
        # is asked often enough to carry the reminder until the inherited
        # `$FPATH` says it was (`install.fpath_needed`'s own heuristic).
        folder = install.fpath_needed(paths.ARTIFACT)
        if folder is not None:
            print(tr("install.completion.fpath", folder=folder))
        return OK

    if word == "license":
        return _license(rest)

    if word == "webapp":
        return _webapp(rest)

    if word == "backup":
        return _backup(rest)

    if word == "convert":
        return _convert(rest)

    if word == "search":
        return _search(rest)

    if word == "admin":
        return _admin(rest)

    if word == "lang":
        return _lang(rest)

    if word == "assist":
        return _assist(rest)

    if word == permissions.SETTING:
        return _setting(rest)

    # The interpreter's word is read off the tree, so a switch that turns it off
    # takes it out of the dispatch and out of the help in the same breath.
    if word in tree.ask_words():
        return _ask(rest)

    # The job's acts are not the engine's six, so the word does NOT walk the
    # table dispatch: `run`, `approve` and `refuse` are the object's own, and the
    # door that takes them is the one above (`door.job`). It reads its actions
    # from the catalogue, so the help and the dispatch still offer one list.
    if word == jobs.JOB:
        return _job(rest)

    if schema.of(word) is not None:
        return _table(word, rest)

    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def _readers() -> tuple[Ask | None, Ask | None]:
    """A line reader and a no-echo reader, when there is a terminal to use."""
    if not sys.stdin.isatty():
        return None, None
    import getpass

    return (lambda question: input(question), getpass.getpass)
