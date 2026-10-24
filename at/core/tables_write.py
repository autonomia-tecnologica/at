"""Writing a row — `create` and `edit`, and what both do to a row before it is saved."""

from __future__ import annotations

from datetime import date
from typing import Any

from at.core.tables_base import _WHEN, TableError, _checked, label
from at.core.tables_rows import find
from at.core.tables_types import _value
from at.data import schema, store


def create(table: str, values: dict[str, Any], *, at: str | None = None) -> dict:
    """A new row from what was typed, with the declaration filling the rest."""
    row = _coerce(table, values, born=True)
    _require(table, row)
    row["id"] = store.allocate(table)
    row = _in_declared_order(table, row)
    _log_status(table, row, previous=None)
    _touch(table, row, at=at)
    store.save(table, store.load(table) + [row])
    return row


def edit(table: str, pid: object, values: dict[str, Any], *, at: str | None = None) -> dict:
    if not values:
        raise TableError("error.nothing_to_set")
    row = find(table, pid)
    previous = dict(row)
    row.update(_coerce(table, values, born=False))
    _require(table, row)
    row = _in_declared_order(table, row)
    _log_status(table, row, previous=previous)
    _touch(table, row, at=at)
    loaded = store.load(table)
    number = store.number_of(row)
    store.save(table, [row if store.number_of(old) == number else old for old in loaded])
    return row


def _coerce(table: str, values: dict[str, Any], born: bool) -> dict:
    """What was typed, read as the field's type — and refused when it is not.

    `born` is the difference between the two doors: a row being created receives
    the declared defaults, and an edit receives only what was typed.
    """
    declared = _checked(table)
    fields = declared.get("fields")
    fields = fields if isinstance(fields, dict) else {}

    out: dict[str, Any] = {}
    if born:
        for name, field in fields.items():
            if isinstance(field, dict) and "default" in field:
                out[name] = _literal(field["default"])

    for name, raw in values.items():
        if name == "id":
            # The number is the store's to hand out, and the counter is what
            # keeps a deleted id deleted.
            continue
        field = fields.get(name)
        if not isinstance(field, dict):
            raise TableError("error.unknown_field", table=table, field=name)
        out[name] = _value(table, name, field, raw)
    return out


def _literal(value: Any) -> Any:
    if isinstance(value, str) and value in _WHEN:
        return _WHEN[value]()
    return value


def _required(field: dict, row: dict) -> bool:
    """Whether this field is required FOR THIS ROW — the declaration's two ways.

    `required` is unconditional: the field a row can never be born without. A
    `required_when` is the OTHER way, and it is what a rule of the DECLARATION
    says about one field in terms of another: a map of field→value that, when
    every pair holds on the row, makes this field required too. The reminder's
    `on_date` carries `{"freq": "once"}` — a `once` reminder with no date is a
    row that can never come round (`reminder.occurs`), so it must not be born;
    a `daily` one declares no date at all and is complete without it.

    It is read off the declaration and never off a name in code: a table that
    needs the rule says it in its own file, the way `open_day_field` reads the
    field whose `default` is null and no list of names is written anywhere.
    """
    if field.get("required"):
        return True
    when = field.get("required_when")
    if not isinstance(when, dict):
        return False
    return all(row.get(name) == value for name, value in when.items())


def _require(table: str, row: dict) -> None:
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return
    for name, field in fields.items():
        if not isinstance(field, dict) or not _required(field, row):
            continue
        value = row.get(name)
        if value is None or value == "" or value == []:
            raise TableError("error.required", field=label(table, name))


def _in_declared_order(table: str, row: dict) -> dict:
    """The row written as the declaration orders it — id first, then the fields —
    so a store read by a person looks the way the schema reads."""
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    fields = fields if isinstance(fields, dict) else {}
    out: dict[str, Any] = {}
    if "id" in row:
        out["id"] = row["id"]
    for name in fields:
        if name != "id" and name in row:
            out[name] = row[name]
    for name, value in row.items():
        if name not in out:
            out[name] = value
    return out


def _stamp(kind: object) -> str:
    """When the entry was written, in the type the `append` declares.

    A table that declares nothing keeps the day this log was born with, which is
    what its rows already carry; one that declares `instant` gets the point in
    time §4 means by it. Neither is a naive local instant.
    """
    return _WHEN["now"]() if kind == "instant" else date.today().isoformat()


def _touch(table: str, row: dict, at: str | None = None) -> None:
    """Every field the table declares `touch: true` on gets RESTAMPED, on every
    write and whatever was typed — the row's own "last written" instant.

    It is what the offline motor's reconciliation compares a queued edit's own
    instant against (TASK-162): `modifications[].at` only moves when the
    TRACKED field changes (§`_log_status`, the status log), so a row whose
    `text` or `desc` changed without its `status` carries no timestamp at all
    under that field — which is exactly the case last-write-wins has to settle.

    `at` lets a caller assert the instant instead of taking the write's own
    now(): the motor stamps the row with the EDIT's own moment (when the
    person actually wrote it, offline or not), not the moment it happened to
    reach this store — two edits reconciled out of order must still compare by
    when they were MADE.
    """
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return
    for name, field in fields.items():
        if isinstance(field, dict) and field.get("touch"):
            row[name] = at if at is not None else _stamp(field.get("type"))


def _log_status(table: str, row: dict, previous: dict | None) -> None:
    """A field that declares `tracks` gets the change appended, on every path.

    It is how the date a task was finished and the date it was cancelled exist
    without a stamp field for each — and it is why the log is written by the
    engine rather than by whoever remembered to.
    """
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        tracked = field.get("tracks")
        append = field.get("append")
        if not isinstance(tracked, str) or not append:
            continue
        value = row.get(tracked)
        if previous is not None and previous.get(tracked) == value:
            continue
        entry: Any = value
        if isinstance(append, dict):
            entry = {append.get("text", "text"): value,
                     append.get("stamp", "at"): _stamp(append.get("type"))}
        log = row.get(name)
        row[name] = (list(log) if isinstance(log, list) else []) + [entry]
