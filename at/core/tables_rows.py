"""The rows a listing carries, in the order the table declares, and the one lookup."""

from __future__ import annotations

from typing import Any

from at.core.tables_base import TableError, _checked, enum_values, number_of, table_name
from at.data import schema, store


def rows(table: str, show_all: bool = False) -> list[dict]:
    """The rows a listing carries, in the order the table declares.

    A field that declares `show` lists the values a listing carries; everything
    else is what the listing hides, which is what `--all` puts back. What
    survives the filter is then handed to `ordered`, so a table that declares
    an order answers "which one comes first" from one place — the CLI's listing
    and the page's table read the same one.
    """
    declared = _checked(table)
    loaded = store.load(table)
    fields = declared.get("fields")
    if not show_all and isinstance(fields, dict):
        for name, field in fields.items():
            if not isinstance(field, dict):
                continue
            shown = field.get("show")
            if not isinstance(shown, list) or not shown:
                continue
            loaded = [row for row in loaded if row.get(name) in shown]
    return ordered(table, loaded)


def sort_spec(table: str) -> dict | None:
    """The order the table declares for its display, or `None`.

    §4 names it beside the default fields — "default order in the display of
    tables" — and it is the ORDER the folder answers "what is next" with. The
    shape is `{"by": <field>, "direction": "asc"|"desc", "then": <field>}`, and
    only `by` is required: `then` is a second key, always ascending, for the tie
    the first one leaves.
    """
    declared = schema.of(table) or {}
    spec = declared.get("sort")
    if isinstance(spec, dict) and isinstance(spec.get("by"), str):
        return spec
    return None


def ordered(table: str, rows: list[dict]) -> list[dict]:
    """`rows` as the table declares them ordered — a copy, never in place.

    A table that declares no `sort` is handed back untouched: the file's order
    IS its order, and the engine invents none. When one declares it, the keys
    are applied LAST FIRST, each with a stable sort, which is what makes the
    result lexicographic without the engine composing a tuple of mixed types.
    """
    spec = sort_spec(table)
    if spec is None:
        return rows
    keys: list[tuple[str, bool]] = [(spec["by"], spec.get("direction") == "desc")]
    if isinstance(spec.get("then"), str):
        keys.append((spec["then"], False))
    out = list(rows)
    for name, descending in reversed(keys):
        out.sort(key=lambda row, field=name: _sort_key(table, field, row),  # type: ignore[misc]  # mypy cannot infer a lambda with a bound default
                 reverse=descending)
    return out


def _sort_key(table: str, name: str, row: dict) -> tuple[int, Any]:
    """One row's key for one declared field, in two parts: the KIND first, then
    the value — so a row that carries something else in the field never makes
    two kinds meet in one comparison.

    A closed vocabulary sorts by the ORDER its declaration lists the values in,
    which is what turns `low…critical` into a rank without a second declaration
    of what a priority is worth. A value the vocabulary does not name — and a
    row that predates the field, which is the common case — reads as the
    declared default, so an old row lands where a new one would.
    """
    declared = schema.field(table, name)
    value = row.get(name)
    if value is None:
        value = declared.get("default")
    values = enum_values(table, name)
    if values:
        return (0, values.index(value) if value in values else len(values))
    if isinstance(value, bool) or value is None:
        return (2, str(value))
    if isinstance(value, (int, float)):
        return (0, float(value))
    return (1, str(value))


def find(table: str, pid: object) -> dict:
    number = number_of(table, pid)
    row = store.find(table, number) if number is not None else None
    if row is None:
        raise TableError(
            "error.unknown_row", id=pid, table=table_name(table, many=True)
        )
    return row
