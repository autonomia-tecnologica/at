"""The command line: the surface that reaches everything Bill can do (§5).

Dispatch is deliberately small and hand-rolled. A framework would put the word
list in a decorator, and the word list has one home already — `tree.py`, which
the help reads too. The table words are not here either: they are generated from
`data/schema/`, every invocation.

Exit codes: `0` success · `1` refused or failed · `2` usage error.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from bill import __version__
from bill.core import boot, files, tables
from bill.data import schema
from bill.i18n import tr
from bill.ui import ask as door
from bill.ui.ask import OK, REFUSED, USAGE
from bill.ui.cli import tree


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)

    # Every invocation confirms the Working Folder first — including `help` and
    # `--version`. The folder belongs to the binary, not to the word, so there
    # is no word that could run before the folder is Bill's.
    if not boot.ensure_working_folder():
        return REFUSED

    if not words:
        from bill.ui.wizard import app as wizard

        return OK if wizard.open_wizard() else REFUSED

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
        return OK

    if word == "webapp":
        return _webapp(rest)

    # The interpreter's word is read off the tree, so a switch that turns it off
    # takes it out of the dispatch and out of the help in the same breath.
    if word in tree.ask_words():
        return _ask(rest)

    if schema.of(word) is not None:
        return _table(word, rest)

    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def _webapp(rest: list[str]) -> int:
    """`bill webapp` opens the app — running it is the only thing it does today.

    This is the hosted path: loopback, in HTTP, and nothing leaves it until a
    person authenticates (§3, Acesso e exposição). The container is the other
    path, where the WebApp runs inside one and the Caddy at the edge carries the
    TLS and the gate (§7b, §7c). Neither the authenticator nor the Caddy exists
    yet — the debt is named in the derived document (derivation §3).
    """
    from bill.ui.webapp import app as webapp

    args = rest[1:] if rest[:1] == ["run"] else rest
    port = webapp.DEFAULT_PORT
    if args:
        if len(args) != 2 or args[0] not in ("--port", "--porta"):
            return _reject("webapp")
        if not args[1].isdigit():
            return _reject("webapp")
        port = int(args[1])
        if not 0 < port < 65536:
            return _reject("webapp")
    return webapp.run(port)


# ---------------------------------------------------------- the interpreter ---

def _ask(rest: list[str]) -> int:
    """`bill ask "..."` — one sentence becomes one proposal, and runs.

    The sentence is ONE argument: it is a phrase, and a phrase the shell split in
    two is two phrases. `pedir` is the same door, and `ask pedir` is that door
    written out — the spelling the derived document carries.

    The door itself is `bill.ui.ask`, which the WebApp's box reads too: what a
    person reads, in order, is the proposal and then the answer — the proposal so
    the reading can be checked, and the answer in the ENGINE's own words, because
    the engine is the one that validated and wrote. This surface invents no
    second sentence for either.
    """
    args = rest[1:] if rest[:1] == ["pedir"] else rest
    if len(args) != 1:
        return _reject("ask")
    result = door.ask(args[0])
    # A question and a refusal have no proposal to check — nothing was proposed
    # and nothing was written — and they are the one sentence the result carries.
    if result.proposal:
        print(result.proposal)
    print(result.text)
    return result.code


# --------------------------------------------------------------- tables ---

def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    try:
        code, answer = door.run(table, action, args)
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(answer)
    return code


# ----------------------------------------------------------------- args ---

def _reject(word: str) -> int:
    print(door.rejected(word))
    return USAGE
