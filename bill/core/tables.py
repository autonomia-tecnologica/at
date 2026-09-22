"""The table engine — what a row is, and what may be done to one.

Four actions: `list`, `view`, `create`, `edit`. They are the same four the CLI
dispatches and the WebApp calls, because there is one engine and the surfaces are
only ways of reaching it (§4). `cancel` and `delete` are not here
yet: both need the `lifecycle` a table declares for closing with history, and
that is a decision of its own.

What this module knows lives in the declaration, never in a list of names: the
fields, their types, their closed vocabularies, their ceilings, their defaults
and their references all come from `data/schema/<table>.json`. Add a table and
nothing here changes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from bill.data import schema, store
from bill.i18n import tr

ACTIONS = ("list", "view", "create", "edit")

# The words a declared default may use instead of a literal: the engine resolves
# them when the row is born, because only then is "today" a day. They resolve to
# ISO TEXT, never to a datetime object — the store is JSON, and a date a person
# reads is a string on every host (§3, Portabilidade).
_WHEN = {
    "today": lambda: date.today().isoformat(),
    "now": lambda: datetime.now().isoformat(timespec="seconds"),
}


class TableError(Exception):
    """Something the declaration refuses. The message is already in the active
    language — every surface prints it as it stands."""

    def __init__(self, key: str, **kw: object):
        self.key = key
        self.kw = kw
        super().__init__(_message(key, kw))


def _message(key: str, kw: dict) -> str:
    return tr(f"table.{key}", **kw)


# ---------------------------------------------------------------- identity ---

def word(table: str) -> str:
    """The table's machine word, as an id spells it: `TASK`."""
    return table.upper()


def format_id(table: str, number: int) -> str:
    """The id a person reads and types back. It is the MACHINE word, uppercased,
    and it does not follow the UI language: an id is a datum a person keeps in a
    note or in a commit, and one that changed with the translation would stop
    naming the same row."""
    return f"{word(table)}-{number}"


def number_of(table: str, value: object) -> int | None:
    """The number inside whatever spelling came in: `7`, `TASK-7`, `task-7`."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    prefix = f"{word(table)}-"
    if text.upper().startswith(prefix):
        text = text[len(prefix):]
    return int(text) if text.isdigit() else None


def title(table: str, row: dict) -> str:
    """What a person reads as the row's name: the field the table declares as
    `primary`, and then the id. Never a field guessed here."""
    declared = schema.primary(table)
    value = row.get(declared) if declared else None
    if isinstance(value, str) and value.strip():
        return value
    number = store.number_of(row)
    return format_id(table, number) if number is not None else ""


# ------------------------------------------------------------ vocabulary ---

def label(table: str, field: str) -> str:
    """The field's display name — the schema carries the KEY, i18n the text."""
    declared = schema.field(table, field)
    key = declared.get("label")
    return tr(key) if isinstance(key, str) else field


def table_name(table: str, many: bool = False) -> str:
    key = schema.name_key(table, many=many)
    return tr(key) if key else table


def columns(table: str) -> list[str]:
    """The fields a listing shows, in the declared order."""
    return schema.columns(table)


def enum_values(table: str, field: str) -> list[str]:
    declared = schema.field(table, field)
    values = declared.get("enum")
    return list(values) if isinstance(values, dict) else []


def enum_label(table: str, field: str, value: object) -> str:
    declared = schema.field(table, field)
    choices = declared.get("enum")
    key = choices.get(value) if isinstance(choices, dict) else None
    return tr(key) if isinstance(key, str) else str(value)


def text_of(table: str, field: str, value: Any) -> str:
    """A value as a person reads it in a line: the closed vocabulary's word, the
    title a reference resolves to, a list joined, and an empty value as `—`."""
    declared = schema.field(table, field)
    if value is None:
        return tr("table.word.none")
    if enum_values(table, field):
        return enum_label(table, field, value)
    # A reference is answered BEFORE the list, because a field that may point at
    # more than one table stores its reference AS a list — and joining that list
    # would print the table's name beside the number.
    targets = declared.get("ref")
    if isinstance(targets, list) and targets:
        return _reference_text(value, targets)
    if isinstance(value, list):
        if not value:
            return tr("table.word.none")
        return ", ".join(_item(item) for item in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _reference_text(value: Any, targets: list) -> str:
    """The title a reference resolves to, or its id when it names nothing.

    An id that resolves to nothing still says WHICH row was meant — showing `—`
    for a dangling reference would hide the very thing worth seeing.
    """
    if isinstance(value, list):
        if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
            return _title_of_reference(value[0], value[1])
        return ", ".join(
            entry for item in value if (entry := _title_of_reference(targets[0], item))
        )
    return _title_of_reference(targets[0], value)


def _title_of_reference(target: str, number: object) -> str:
    if isinstance(number, bool) or not isinstance(number, int):
        return str(number)
    found = store.find(target, number)
    return title(target, found) if found else format_id(target, number)


def _item(value: Any) -> str:
    """One entry of a list field. A logged change is an object, and a reader
    wants the change, not Python's spelling of a dict."""
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value)


# ------------------------------------------------------------------ rows ---

def rows(table: str, show_all: bool = False) -> list[dict]:
    """Every row, in file order, minus what the table declares as hidden.

    A field that declares `show` lists the values a listing carries; everything
    else is what the listing hides, which is what `--all` puts back.
    """
    loaded = store.load(table)
    if show_all:
        return loaded
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return loaded
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        shown = field.get("show")
        if not isinstance(shown, list) or not shown:
            continue
        loaded = [row for row in loaded if row.get(name) in shown]
    return loaded


def find(table: str, pid: object) -> dict:
    number = number_of(table, pid)
    row = store.find(table, number) if number is not None else None
    if row is None:
        raise TableError(
            "error.unknown_row", id=pid, table=table_name(table, many=True)
        )
    return row


# --------------------------------------------------------------- writing ---

def create(table: str, values: dict[str, str]) -> dict:
    """A new row from what was typed, with the declaration filling the rest."""
    row = _coerce(table, values, born=True)
    _require(table, row)
    row["id"] = store.allocate(table)
    row = _in_declared_order(table, row)
    _log_status(table, row, previous=None)
    store.save(table, store.load(table) + [row])
    return row


def edit(table: str, pid: object, values: dict[str, str]) -> dict:
    if not values:
        raise TableError("error.nothing_to_set")
    row = find(table, pid)
    previous = dict(row)
    row.update(_coerce(table, values, born=False))
    _require(table, row)
    row = _in_declared_order(table, row)
    _log_status(table, row, previous=previous)
    loaded = store.load(table)
    number = store.number_of(row)
    store.save(table, [row if store.number_of(old) == number else old for old in loaded])
    return row


def _coerce(table: str, values: dict[str, str], born: bool) -> dict:
    """What was typed, read as the field's type — and refused when it is not.

    `born` is the difference between the two doors: a row being created receives
    the declared defaults, and an edit receives only what was typed.
    """
    declared = schema.of(table) or {}
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


def _value(table: str, name: str, field: dict, raw: Any) -> Any:
    if not isinstance(raw, str):
        return raw
    kind = field.get("type")
    if kind == "list":
        items = [item.strip() for item in raw.split(",") if item.strip()]
        return [_scalar(item) for item in items]
    if field.get("ref"):
        return _reference_value(field, raw)
    ceiling = field.get("max_length")
    if isinstance(ceiling, int) and len(raw) > ceiling:
        raise TableError("error.too_long", field=label(table, name), max=ceiling)
    if field.get("enum"):
        if raw not in enum_values(table, name):
            raise TableError("error.not_in_enum", value=raw, field=label(table, name))
        return raw
    return _scalar(raw)


def _scalar(raw: str) -> Any:
    text = raw.strip()
    if text.isdigit():
        return int(text)
    if text in ("true", "false"):
        return text == "true"
    return raw


def _reference_value(field: dict, raw: str) -> Any:
    targets = field.get("ref") or []
    number = number_of(targets[0], raw) if len(targets) == 1 else None
    if number is None and raw.isdigit():
        number = int(raw)
    if number is None:
        return raw
    # A field that points at ONE table stores the bare number — the declaration
    # already says which table it is, and repeating it in every row is noise. A
    # field that may point at MORE THAN ONE stores the pair, so the row says
    # which table it meant without the declaration at hand.
    return [targets[0], number] if len(targets) > 1 else number


def _require(table: str, row: dict) -> None:
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if not isinstance(fields, dict):
        return
    for name, field in fields.items():
        if not isinstance(field, dict) or not field.get("required"):
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
                     append.get("stamp", "at"): date.today().isoformat()}
        log = row.get(name)
        row[name] = (list(log) if isinstance(log, list) else []) + [entry]
