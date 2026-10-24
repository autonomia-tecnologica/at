"""Closing a row — `cancel` with history, `delete` with the references read off the
declarations."""

from __future__ import annotations

from datetime import date
from typing import Any

from at.core.tables_base import TableError, enum_label, format_id, table_name
from at.core.tables_rows import find
from at.core.tables_write import _coerce, _in_declared_order, _log_status, _require, _touch
from at.data import schema, store
from at.i18n import tr


def lifecycle(table: str) -> dict:
    """The `cancel` a table declares — the terminal status, where the reason
    lands and whether it is required. `{}` when the table declares none.

    The declaration carries KEYS, never sentences: `reason.text` is an i18n key
    like a label is, because a text a person reads does not live in the schema.
    """
    declared = schema.of(table) or {}
    spec = declared.get("lifecycle")
    spec = spec.get("cancel") if isinstance(spec, dict) else None
    return spec if isinstance(spec, dict) else {}


def _terminal_field(table: str, value: object) -> str | None:
    """The field the terminal status belongs to: the one whose closed vocabulary
    already carries it. Never a field this module assumes is called `status`."""
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return None
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        choices = field.get("enum")
        if isinstance(choices, dict) and value in choices:
            return name
    return None


def cancel(table: str, pid: object, reason: str = "", values: dict | None = None) -> dict:
    """Close the row, keeping it — the terminal status and the story of the day.

    Every part is the table's to declare: which status ends the row, where the
    reason goes, and whether a reason is required. The value the closing writes
    is the `tracks`/`append` log's business too, so the two never fight: the log
    is written first and the reason is APPENDED, never assigned, into a field the
    declaration names.
    """
    spec = lifecycle(table)
    if not spec:
        raise TableError("error.no_lifecycle", table=table_name(table))

    closed = spec.get("status")
    field = _terminal_field(table, closed)
    if field is None:
        raise TableError("error.no_terminal_status", status=closed)
    reason_field = _reason_field(table, spec.get("reason"))

    row = find(table, pid)
    previous = dict(row)
    number = store.number_of(row)
    if row.get(field) == closed:
        raise TableError(
            "error.already_closed",
            id=format_id(table, number),
            status=enum_label(table, field, closed),
        )

    reason = reason.strip() if isinstance(reason, str) else ""
    if spec.get("reason_required") and not reason:
        raise TableError("error.reason_required")

    if values:
        row.update(_coerce(table, values, born=False))
        _require(table, row)
    row[field] = closed
    # The log first, so the closing line is the last thing the row's story says.
    _log_status(table, row, previous=previous)
    _write_reason(table, row, reason_field, spec.get("reason"), reason)
    _touch(table, row)

    row = _in_declared_order(table, row)
    store.save(
        table,
        [row if store.number_of(old) == number else old for old in store.load(table)],
    )
    return row


def _reason_field(table: str, declared: object) -> str | None:
    """The field the reason lands in, or `None` when the declaration names none.

    A declaration that names a field the table does not have is a typo, and it is
    refused: writing the line anyway would invent a key in every row the table
    closes, which is the opposite of a field a person can find.
    """
    spec = declared if isinstance(declared, dict) else {}
    into = spec.get("into")
    if not isinstance(into, str) or not into:
        return None
    if not schema.field(table, into):
        raise TableError("error.no_reason_field", field=into)
    return into


def _write_reason(
    table: str, row: dict, into: str | None, declared: object, reason: str
) -> None:
    """The reason, where the declaration says history lives — APPENDED, never
    assigned.

    The field it lands in may be the very one the engine's own log writes: a
    list field is given one more entry, a text field one more paragraph, and
    neither takes the other's place.
    """
    spec = declared if isinstance(declared, dict) else {}
    if not reason or into is None:
        return
    line = tr(
        spec.get("text") or "table.closed.reason",
        # A day is stored the one way §4 stores one: the text of a calendar day.
        # A line a person reads is no reason to write a locale-shaped date into
        # the store — that value would change with the language of whoever wrote.
        date=date.today().isoformat(),
        reason=reason,
    )
    if schema.field(table, into).get("type") == "list":
        log = row.get(into)
        row[into] = (list(log) if isinstance(log, list) else []) + [line]
        return
    old = row.get(into)
    old = str(old).strip() if old is not None else ""
    row[into] = f"{old}\n\n{line}" if old else line


def deletable(table: str) -> bool:
    """Whether a row of this table may be taken out — declared, never assumed.

    §4 makes the deletability of a ROW a property the table declares in its own
    schema, and `audit` declares that no row of its own is erased: it is a log,
    and a log with holes is not one. A table that declares nothing is deletable,
    which is what every table was before the key existed.
    """
    declared = schema.of(table) or {}
    return declared.get("deletable", True) is not False


def referrers(table: str, number: int | None) -> list[tuple[str, str, int | None]]:
    """`(table, field, row id)` of every row that NAMES row `number` of `table`.

    Read from the DECLARATIONS and nothing else: a field whose `ref` can reach
    `table` is a field that can point here, and one that cannot is not made into
    a link by the shape of its value. The folder is never scanned for a number
    that looks like this one.
    """
    found: list[tuple[str, str, int | None]] = []
    for other, declared in schema.tables().items():
        fields = declared.get("fields")
        if not isinstance(fields, dict):
            continue
        for name, field in fields.items():
            if not isinstance(field, dict):
                continue
            targets = field.get("ref")
            if not isinstance(targets, list) or table not in targets:
                continue
            for row in store.load(other):
                # A row is not its own referrer: a project's `parent` may name
                # the very project that is being taken out.
                if other == table and store.number_of(row) == number:
                    continue
                if _names(row.get(name), table, number):
                    found.append((other, name, store.number_of(row)))
    return found


def _names(value: Any, target: str, number: int | None) -> bool:
    """Whether `value` names row `number` of `target`, in any shape a reference
    takes: the bare number a single-target field stores, the `[table, number]`
    pair a field that may point at more than one stores, or a list of either."""
    if isinstance(value, list):
        if (
            len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], int)
            and not isinstance(value[1], bool)
        ):
            return value[0] == target and value[1] == number
        return any(_names(item, target, number) for item in value)
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value == number


def delete(table: str, pid: object) -> dict:
    """Take the row out — refusing while anything names it, and never giving the
    number back.

    The refusal is read off the declarations, and the number stays SPENT: the
    notes and the commits that carry it go on naming the row that was there, so
    the next `create` may not hand it to a second one.

    **A table that declares no row of its own is erased refuses FIRST**, before
    the row is even looked for: the wall is the TABLE's and not the number's, so
    which id was typed cannot change the answer — and a log is exactly the table
    whose holes would be the thing worth hiding.
    """
    if not deletable(table):
        raise TableError("error.not_deletable", table=table_name(table))
    row = find(table, pid)
    number = store.number_of(row)
    blockers = referrers(table, number)
    if blockers:
        raise TableError(
            "error.named_by",
            id=format_id(table, number),
            n=len(blockers),
            where=" · ".join(
                f"{format_id(other, rid)} ({field})" if rid is not None
                else f"{table_name(other, many=True)} ({field})"
                for other, field, rid in blockers[:3]
            ),
        )
    store.save(
        table,
        [old for old in store.load(table) if store.number_of(old) != number],
    )
    assert number is not None  # `find` hands back a row that carries its id
    store.spend(table, number)
    return row
