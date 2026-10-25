"""The words that are an object's own: `setting`, `ask`, `job` and the tables."""

from __future__ import annotations

from collections.abc import Callable

from at.core import actors, audit, files, jobs, permissions, tables
from at.i18n import tr
from at.ui import ask as door
from at.ui.ask import REFUSED, USAGE
from at.ui.cli import jsonout
from at.ui.cli.common import reject as _reject


def _setting(rest: list[str]) -> int:
    """`at-cli setting list|view|edit` — the settings through the core (§4).

    §5 says the `cli` reaches everything, and the settings are reachable by one
    road only: the three words are the object's own actions, read from the
    catalogue the way a table's are, and the door is `at.ui.ask.setting`, which
    owns the line and the version. The actor of an act typed here is the first
    admin and the via is the terminal's — the same pair every other word of this
    surface records, and a fact of the folder rather than of a request (§3).

    The action list is `permissions.actions` and not a tuple written here: the
    word the help offers and the word the dispatch accepts are the same list,
    which is what keeps a spelling from dispatching without being offered.
    """
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in permissions.actions(permissions.SETTING):
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    code, answer = door.setting(action, args, actor=actors.first_admin(), via=audit.CLI)
    print(answer)
    return code


def _ask(rest: list[str]) -> int:
    """`at-cli ask "..."` — one sentence becomes one proposal, and runs.

    The sentence is ONE argument: it is a phrase, and a phrase the shell split in
    two is two phrases. `pedir` is the same door, and `ask pedir` is that door
    written out — the spelling the derived document carries.

    The door itself is `at.ui.ask`, which the WebApp's box reads too: what a
    person reads, in order, is the proposal and then the answer — the proposal so
    the reading can be checked, and the answer in the ENGINE's own words, because
    the engine is the one that validated and wrote. This surface invents no
    second sentence for either.
    """
    args = rest[1:] if rest[:1] == ["pedir"] else rest
    if len(args) != 1:
        return _reject("ask")
    # The ACTOR of an act typed at the terminal is the first admin (§3, item 15):
    # the `cli` is local by construction and whoever is in front of it is the
    # folder's owner. A folder that never made one asks with nobody, which is
    # what it always did.
    result = door.ask(args[0], actor=actors.first_admin())
    # A question and a refusal have no proposal to check — nothing was proposed
    # and nothing was written — and they are the one sentence the result carries.
    if result.proposal:
        print(result.proposal)
    print(result.text)
    return result.code


def _job(rest: list[str]) -> int:
    """`at-cli job list|view|run|approve|refuse|declare|disable` — the demand
    that waits, and the round the clock drives on its own (§4, item 24).

    The seven words are the object's OWN, read from the catalogue the way a
    table's actions are (`permissions.actions`) and not written here, so a word
    the help offers is a word the dispatch accepts and the other way round. What
    they answer is `at.ui.ask.job`, which is the door: the line, the version and
    the ceiling all live there, and this surface only chooses WHERE the words go.

    The actor is the first admin and the via is the terminal's, the same pair
    every other word of this surface records: the `cli` is local by construction,
    and whoever is in front of it is the folder's owner (§3). The approval is
    therefore typed by a person — which is the whole of what it means.
    """
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in permissions.actions(jobs.JOB):
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    try:
        # The door answers its own refusals (a state the act does not answer, a
        # machine trying the approval) as text and a code, like `setting` does;
        # what reaches here is the engine's, raised while the job RUNS.
        code, answer = door.job(
            action, args, actor=actors.first_admin(), via=audit.CLI
        )
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(answer)
    return code


# The acts that are a TABLE's own — read the folder or the store and write no
# row, so none of them walks `run` and none of them is one of `tables.ACTIONS`.
# `secret scan` is the one item 51 gave; `secret install-hooks` is its own
# second act, writing two files and no row either; `reminder due` is item 29's
# first slice. A fourth one is a fourth entry, not a fourth `if`.
_OWN_ACTS: dict[tuple[str, str], Callable[[list[str]], tuple[int, str]]] = {
    (permissions.SECRET, permissions.SCAN): door.scan,
    (permissions.SECRET, permissions.INSTALL_HOOKS): door.install_hooks,
    (permissions.REMINDER, permissions.DUE): door.reminder_due,
}


def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        # An act the engine does not have is the object's OWN, and it does not
        # walk `run`: `secret scan` reads the folder and writes nothing, so it
        # records no line and versions nothing. `_OWN_ACTS` is the closed list of
        # them, held to the same names `permissions.actions` answers with.
        #
        # The engine's own words keep dispatching exactly as they always did,
        # including the ones a narrowed table does not answer: `audit delete`
        # reaches the engine and is refused by it, and the attempt is a line
        # (§3). A word the table does not answer is a refusal to RECORD, and a
        # dispatch that turned it into a usage error would be a wall with no
        # trail behind it.
        own = _OWN_ACTS.get((table, action))
        if own is None:
            print(tr("table.error.unknown_action", action=action))
            return USAGE
        code, answer = own(args)
        print(answer)
        return code
    jsonout.attach("table", table)
    try:
        # The actor of an act typed here is the first admin, and the via is the
        # terminal's: what the door records is WHO and HOW, and the `cli` is the
        # one surface where both are facts of the folder rather than of a request
        # (§3, item 15).
        code, answer, row, _, _ = door.run(
            table, action, args, actor=actors.first_admin(), via=audit.CLI
        )
        jsonout.attach("row", row)
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(answer)
    return code
