"""The functions of AT: which folders each one works in.

`function` is a table of the system (§3): one row per internal function, with
the folders it is bound to and whether it is on. This module is the table's
reader and its seed; it does NOT change how the core resolves a folder — that is
the next step, and `paths` still answers from its own table of names.

Four functions, and the others are not in the map on purpose: `projects`,
`shared`, `app`, `data` and `convert` are the fixed base structure. `Arquivos`
is the old name of the library (`paths.FORMER`), not a function.

A folder is a path relative to the Working Folder, or an absolute one, inside or
outside the repository. Only the library accepts several. Switching a function
off keeps its row and its folders: nothing is erased.
"""

from __future__ import annotations

from pathlib import Path

from at.core import paths, tables
from at.core.tables_base import TableError
from at.data import store

TABLE = "function"

LIBRARY = "library"
STRONGBOX = "strongbox"
CODE = "code"
HARNESS = "harness"

# The internal functions, in the order the table is seeded. The value is whether
# the function takes SEVERAL folders.
FUNCTIONS: dict[str, bool] = {
    LIBRARY: True,
    STRONGBOX: False,
    CODE: False,
    HARNESS: False,
}

# The internal folder name each function seeds with — `code` has none until the
# person picks one.
SEEDED_FROM: dict[str, str | None] = {
    LIBRARY: "prose",
    STRONGBOX: "strongbox",
    CODE: None,
    HARNESS: "harness",
}

ON = "enabled"
OFF = "disabled"


def _known(function: str) -> None:
    if function not in FUNCTIONS:
        raise TableError("function.error.unknown_function", function=function)


def seed() -> list[dict]:
    """Write the row of each function that has none, with today's folders.

    The folder is spelled as THIS Working Folder carries it (`paths.folder`), so
    an instance that already exists keeps working in the same folders. A row
    that is already there is never touched: a person who edited the map owns it.
    """
    present = {row.get("function") for row in store.load(TABLE)}
    root = paths.working_folder()
    created: list[dict] = []
    for function, internal in SEEDED_FROM.items():
        if function in present:
            continue
        folders = [] if internal is None else [_relative(paths.folder(internal), root)]
        created.append(
            tables.create(TABLE, {"function": function, "folders": folders, "enabled": ON})
        )
    return created


def _relative(folder: Path, root: Path) -> str:
    try:
        return folder.relative_to(root).as_posix()
    except ValueError:
        return str(folder)


def rows() -> list[dict]:
    return [row for row in store.load(TABLE) if row.get("function") in FUNCTIONS]


def row(function: str) -> dict | None:
    """The row of a function, or `None` when the table has none."""
    _known(function)
    return next((item for item in rows() if item.get("function") == function), None)


def folders(function: str) -> list[str]:
    """The folders as written, in order."""
    found = row(function)
    raw = found.get("folders") if found else None
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",") if item.strip()]
    return [str(item) for item in raw or []]


def resolved(function: str) -> list[Path]:
    """The folders as paths: relative ones against the Working Folder."""
    root = paths.working_folder()
    return [
        path if path.is_absolute() else (root / path)
        for path in (Path(item).expanduser() for item in folders(function))
    ]


def enabled(function: str) -> bool:
    """Whether the function is on. A function with no row is not on."""
    found = row(function)
    return found is not None and found.get("enabled", ON) != OFF


def set_folders(function: str, values: list[str]) -> dict:
    """Bind the function to these folders; only the library takes more than one."""
    _known(function)
    cleaned = [item.strip() for item in values if item.strip()]
    if len(cleaned) > 1 and not FUNCTIONS[function]:
        raise TableError("function.error.one_folder", function=function)
    return _write(function, {"folders": cleaned})


def set_enabled(function: str, on: bool) -> dict:
    """Switch the function on or off. The row and its folders stay."""
    return _write(function, {"enabled": ON if on else OFF})


def _write(function: str, values: dict) -> dict:
    found = row(function)
    if found is None:
        raise TableError("function.error.no_function_row", function=function)
    return tables.edit(TABLE, found["id"], values)
