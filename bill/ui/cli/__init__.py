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

from bill import __version__, nlu
from bill.core import boot, files, tables
from bill.data import schema
from bill.i18n import tr
from bill.ui.cli import tree

OK = 0
REFUSED = 1
USAGE = 2


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

    What a person reads, in order, is the proposal and then the answer: the
    proposal so the reading can be checked, and the answer in the ENGINE's own
    words, because the engine is the one that validated and wrote. This surface
    invents no second sentence for either.
    """
    args = rest[1:] if rest[:1] == ["pedir"] else rest
    if len(args) != 1:
        return _reject("ask")
    try:
        proposed = nlu.propose(args[0])
    except nlu.Refused as refused:
        # The refusal already speaks the active language — the reason's key is
        # i18n's — so it is printed as it stands.
        print(refused)
        return REFUSED
    if isinstance(proposed, nlu.Question):
        # The question carries the phrase it is about, so the surface asks in
        # the active language without knowing which one the phrase was written
        # in — and nothing is proposed, so nothing is written.
        print(tr(proposed.key, text=proposed.text))
        return REFUSED
    print(_proposed(proposed))
    try:
        return _execute(proposed)
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED


def _proposed(proposal: nlu.Proposal) -> str:
    """The proposal, written with the engine's own words.

    The action and the table are named the way the engine names them and every
    value is written the way the listing would write it — the day in the
    reader's own locale, a closed value in their own language — because a
    proposal is something a person checks before trusting it.
    """
    fields = ", ".join(
        f"{tables.label(proposal.table, name)} = "
        f"{tables.text_of(proposal.table, name, value)}"
        for name, value in proposal.values.items()
    )
    return tr(
        "nlu.proposal",
        action=tr(f"table.action.{proposal.action}"),
        table=tables.table_name(proposal.table),
        fields=fields or tr("table.word.none"),
    )


def _execute(proposal: nlu.Proposal) -> int:
    """Run the proposal through the table engine, and answer with its words.

    It takes the same road `bill <table> <action>` takes — `_run` — because
    there is one engine and a second path into it would be a second engine. What
    changes is only where the values came from: the interpreter read them out of
    a sentence instead of off `--set`, and re-spelling them as `--set` arguments
    would be a second reading of the same thing.
    """
    # The row a person named, spelled as `_run` already reads one: `list` and
    # `view` take it among the arguments, and the rest as the leftover.
    args = [] if proposal.row is None else [str(proposal.row)]
    return _run(proposal.table, proposal.action, args, (proposal.values, args))


# --------------------------------------------------------------- tables ---

def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    try:
        return _run(table, action, args)
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED


def _run(
    table: str,
    action: str,
    args: list[str],
    given: tuple[dict, list[str]] | None = None,
) -> int:
    """One table action, from the words of the `cli` or from a proposal.

    `given` is the `(values, leftovers)` a proposal already carries — the
    interpreter read them out of the sentence, and only the road by which the
    values arrived differs.
    """
    if action == "list":
        return _list(table, args)
    if action == "view":
        return _view(table, args)
    values, leftovers = given if given is not None else _sets(args)
    if action == "create":
        if leftovers:
            return _reject(action)
        row = tables.create(table, values)
        print(tr("table.created", id=tables.format_id(table, row["id"])))
        return OK
    if action == "cancel":
        if len(leftovers) != 1:
            return _reject(action)
        # The reason is the argument the CLOSING owns, and it is read outside the
        # field coercion: a table does not have to declare a field for it. When
        # one does declare a field of that name, the field wins — the engine sets
        # it like any other, and the same text answers the closing.
        reason = values.get("reason", "")
        if not schema.field(table, "reason"):
            values.pop("reason", None)
        row = tables.cancel(table, leftovers[0], reason, values)
        print(tr("table.cancelled", id=tables.format_id(table, row["id"])))
        return OK
    if action == "delete":
        if len(leftovers) != 1 or values:
            return _reject(action)
        row = tables.delete(table, leftovers[0])
        print(tr("table.deleted", id=tables.format_id(table, row["id"])))
        return OK
    # edit
    if len(leftovers) != 1:
        return _reject(action)
    row = tables.edit(table, leftovers[0], values)
    print(tr("table.edited", id=tables.format_id(table, row["id"])))
    return OK


def _list(table: str, args: list[str]) -> int:
    show_all = "--all" in args
    if [arg for arg in args if arg != "--all"]:
        return _reject("list")
    rows = tables.rows(table, show_all=show_all)
    if not rows:
        print(tr("table.word.empty"))
        return OK
    print(_rendered(table, rows))
    return OK


def _view(table: str, args: list[str]) -> int:
    if len(args) != 1:
        return _reject("view")
    row = tables.find(table, args[0])
    print(f"{tr('table.field.id')}: {tables.format_id(table, row['id'])}")
    for name in (schema.of(table) or {}).get("fields", {}):
        if name == "id":
            continue
        print(f"{tables.label(table, name)}: {tables.text_of(table, name, row.get(name))}")
    return OK


def _rendered(table: str, rows: list[dict]) -> str:
    """The listing: the id, then the columns the table declares.

    The widths are measured from what is about to be printed, so a column is as
    wide as its widest cell — the alternative, a fixed width, is a table that
    breaks the first time a title is long.
    """
    header = [tr("table.field.id")] + [tables.label(table, name) for name in tables.columns(table)]
    cells = [
        [tables.format_id(table, row["id"])]
        + [tables.text_of(table, name, row.get(name)) for name in tables.columns(table)]
        for row in rows
    ]
    widths = [max(len(line) for line in column) for column in zip(header, *cells)]
    line = lambda row: "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
    return "\n".join([line(header), *[line(cell) for cell in cells]])


# ----------------------------------------------------------------- args ---

def _sets(args: list[str]) -> tuple[dict[str, str], list[str]]:
    """`--set field=value` pairs, and whatever was left that was not one."""
    values: dict[str, str] = {}
    leftovers: list[str] = []
    position = 0
    while position < len(args):
        if args[position] != "--set":
            leftovers.append(args[position])
            position += 1
            continue
        if position + 1 >= len(args) or "=" not in args[position + 1]:
            raise tables.TableError("error.set_needs_value")
        name, value = args[position + 1].split("=", 1)
        values[name.strip()] = value
        position += 2
    return values, leftovers


def _reject(word: str) -> int:
    print(tr("cli.error.rejected_arguments", word=word))
    return USAGE
