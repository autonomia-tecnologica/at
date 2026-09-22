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

    if schema.of(word) is not None:
        return _table(word, rest)

    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def _webapp(rest: list[str]) -> int:
    """`bill webapp` opens the app — running it is the only thing it does today.

    The Manifesto makes the WebApp a container (§6c). Until that item lands it
    runs here, on loopback, with no authentication of its own: the guard is the
    ingress's (§7).
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


def _run(table: str, action: str, args: list[str]) -> int:
    if action == "list":
        return _list(table, args)
    if action == "view":
        return _view(table, args)
    values, leftovers = _sets(args)
    if action == "create":
        if leftovers:
            return _reject(action)
        row = tables.create(table, values)
        print(tr("table.created", id=tables.format_id(table, row["id"])))
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
