"""Rows in and out — the `.jsonl` store, and the counter that keeps an id spent.

A store is one line per row, one row per JSON object, in file order. Nothing here
knows what a field means: the schema says that, and the engine applies it.

**The id counter lives in the Working Folder, not in the schema.** It counts what
happened in *this* folder, and the schema ships with the product — putting the
two in one file would publish one instance's numbering to every other. It goes in
`app/counters.json`, and it is written BEFORE the row: a number that was handed
out is spent even if the write that followed failed, because an id that comes
back is an id two rows can answer to.
"""

from __future__ import annotations

import json
from pathlib import Path

from bill.core import files, paths
from bill.data import schema

COUNTERS = "counters.json"


def counter_file() -> Path:
    return paths.app_dir() / COUNTERS


def path(table: str) -> Path | None:
    return schema.store_path(table)


def load(table: str) -> list[dict]:
    """Every row of `table`, in file order. Missing store is an empty table.

    A malformed line is skipped, never fatal: one bad byte must not blank a
    table a person is reading.
    """
    where = path(table)
    if where is None or not where.is_file():
        return []
    rows: list[dict] = []
    for line in where.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def save(table: str, rows: list[dict]) -> None:
    """Rewrite the whole store from `rows`, through the single writer."""
    where = path(table)
    if where is None:
        raise NoStore(table)
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    files.atomic_write_text(where, body)


def find(table: str, number: int) -> dict | None:
    return next((row for row in load(table) if number_of(row) == number), None)


def number_of(row: dict) -> int | None:
    """The row's id as a number, or None when it carries none.

    Booleans are excluded on purpose: in JSON `true` is an `int` in Python, and a
    row whose id came out `true` is a row with no id.
    """
    value = row.get("id")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def highest(table: str) -> int:
    return max((n for row in load(table) if (n := number_of(row)) is not None), default=0)


def counters() -> dict[str, int]:
    try:
        raw = files.read_json(counter_file(), default={})
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(table): value
        for table, value in raw.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


def counter(table: str) -> int:
    """The highest number the folder remembers having spent for `table`.

    Spent, not next: the remembered number is one an id already used. That is
    the whole point — the row may be gone from the store and the number is still
    taken.
    """
    return counters().get(table, 0)


def allocate(table: str) -> int:
    """Hand out the next id for `table`, and record it as spent.

    Two floors, and the higher wins: what the folder remembers (an id whose row
    was deleted) and what the rows still show (a store restored from a backup
    can carry a row the counter never saw). Either one alone would hand out a
    number twice.
    """
    number = max(highest(table) + 1, counter(table) + 1)
    spend(table, number)
    return number


def spend(table: str, number: int) -> None:
    """Record a number as spent WITHOUT handing it out.

    `delete` is the caller, and it is the whole reason this is a door of its own:
    the row is taken out, and the number may not come back — the next `allocate`
    would otherwise start again from the highest row still standing and hand a
    second row an id a person's notes and commits already carry.
    """
    remembered = counters()
    if remembered.get(table, 0) >= number:
        return
    remembered[table] = number
    body = json.dumps(remembered, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    files.atomic_write_text(counter_file(), body)


def reset() -> None:
    """Nothing is cached here, but the door exists: every layer above calls it."""
    schema.reset()


class NoStore(Exception):
    """The table declares no store, so there is nowhere for rows to live."""

    def __init__(self, table: str):
        super().__init__(table)
        self.table = table
