"""The table engine — what a row is, and what may be done to one.

Six actions: `list`, `view`, `create`, `edit`, `cancel`, `delete`. They are the
same six the CLI dispatches and the WebApp calls, because there is one engine and
the surfaces are only ways of reaching it (§4).

`cancel` CLOSES WITH HISTORY — the row stays, the status becomes the terminal one
and the reason goes where the table keeps its story — and every part of that comes
from the `lifecycle` the table declares. A table that declares none says so
instead of inventing a closing. `delete` takes the row out and refuses while
anything NAMES it; what names a row is read off the declarations (`ref`), never
off a scan of the folder.

What this module knows lives in the declaration, never in a list of names: the
fields, their types, their closed vocabularies, their ceilings, their defaults,
their references and their lifecycle all come from `data/schema/<table>.json`. Add
a table and nothing here changes.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from at.data import schema, store
from at.encryption import password, vault
from at.i18n import tr

ACTIONS = ("list", "view", "create", "edit", "cancel", "delete")

# The two types whose value does not come out of a row. They are told apart by
# WHY: a `hashed` value is only ever compared, and a `sealed` one is only ever
# opened with the key — and to whoever reads a line they are one thing, a word
# where the value would be. What the word says is which of the two it is
# (`table.word.hashed`, `table.word.sealed`), so the reader knows whether the
# something behind it can ever be theirs.
OPAQUE = ("hashed", "sealed")

# The two types whose declaration is held to a closed list of keys — and the
# list of each. `hashed` and `sealed` fix a METHOD, and a method is not a
# schema author's choice: what the declaration says is what it says about any
# other field. `default` is absent from both on purpose: a default is a value
# the declaration WRITES, and the declaration is published — a credential or a
# sealed value with a default would be one in the repository.
LISTED_KEYS: dict[str, tuple[str, ...]] = {
    "hashed": ("type", "label", "required", "max_length", "hide"),
    "sealed": ("type", "label", "required", "hide"),
}

# The two that only READ, and the rest — the actions that change the folder, and
# the ones a version has to carry (§4, item 30). It is derived from the six above
# and not written a second time: who writes is the ENGINE's to say, and a list
# beside this one would drift the day a seventh action arrives.
READS = ("list", "view")
WRITES = tuple(action for action in ACTIONS if action not in READS)

# The words a declared default may use instead of a literal: the engine resolves
# them when the row is born, because only then is "today" a day. They resolve to
# ISO TEXT, never to a datetime object — the store is JSON, and a date a person
# reads is a string on every host (§3, Portabilidade).
#
# `now` is a point in time, so it is written the way §4 writes one: UTC, with
# milliseconds. The machine's zone is a property of whoever reads, never of what
# is stored — a naive local instant is a value two machines disagree about.
_WHEN = {
    "today": lambda: date.today().isoformat(),
    "now": lambda: utc(datetime.now(timezone.utc)),
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
    `primary`, and then the id. Never a field guessed here.

    A table that declares one of the two unreadable types as its principal is
    refused: a title is read, and neither a derivation nor a sealed value is. An
    identity a surface has to spell out is not a credential's job, and the
    declaration is where that is caught — before any row can carry one.
    """
    _checked(table)
    declared = schema.primary(table)
    kind = opaque(table, declared) if declared else None
    if kind is not None:
        raise TableError(
            f"error.{kind}_primary",
            table=table_name(table),
            field=label(table, declared),
        )
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


# -------------------------------------------------------------- display ---

def _as_day(value: Any) -> str:
    """A day written the way the reader's locale writes one: `22/09/2026`.

    A value that does not parse is shown as it is stored, never hidden: a row
    written before the type existed still has to be readable.
    """
    try:
        moment = date.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return tr(
        "format.day",
        day=f"{moment.day:02d}",
        month=f"{moment.month:02d}",
        year=moment.year,
    )


def _as_instant(value: Any) -> str:
    """An instant in the reader's clock: the stored UTC turned into their zone.

    The zone is the machine's, because AT runs where the person is — §4's
    "locality is detected on display": the store keeps the point in time in UTC
    and only the reading moves it. Minutes are the display's precision; the
    milliseconds stay where they were written.
    """
    text = str(value)
    # What is not a point in time is not shown as one: a day an older row wrote
    # in this field is shown as it is stored, and the display invents no clock.
    if not _INSTANT_SHAPE.match(text):
        return text
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return text
    here = moment.astimezone()
    return tr(
        "format.instant",
        day=f"{here.day:02d}",
        month=f"{here.month:02d}",
        year=here.year,
        hour=f"{here.hour:02d}",
        minute=f"{here.minute:02d}",
    )


# The two types about time, and how the locale writes each one. The shapes are
# i18n data, like every other text a person reads — a locale that writes a date
# differently changes a block, never this file.
_LOCALE = {"day": _as_day, "instant": _as_instant}


def _locale_writer(declared: dict):
    """The locale's way of writing a value of the declared type, or `None`."""
    kind = declared.get("type")
    return _LOCALE.get(kind) if isinstance(kind, str) else None


def text_of(table: str, field: str, value: Any) -> str:
    """A value as a person reads it in a line: the closed vocabulary's word, the
    title a reference resolves to, a list joined, and an empty value as `—`.

    A field of one of the two types about time is written the way the READER's
    locale writes it — the day in their order, the instant in their clock.
    """
    _checked(table)
    declared = schema.field(table, field)
    if value is None:
        return tr("table.word.none")
    kind = opaque(table, field)
    if kind is not None:
        # The mask, and never the value. The display does not refuse — a listing
        # that crashed on the very field it is meant to hide would be a worse
        # answer than the one that says there is something here you do not read.
        # A value that is not there, which is what a clearing leaves, reads as
        # nothing and never as a hidden something.
        return tr(f"table.word.{kind}") if value else tr("table.word.none")
    written = _locale_writer(declared)
    if written is not None:
        return written(value)
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
        return ", ".join(_item(item, declared) for item in value)
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


def _item(value: Any, declared: dict) -> str:
    """One entry of a list field. A logged change is an object, and a reader
    wants the change, not Python's spelling of a dict.

    The stamp of a `tracks`/`append` entry is the one date that hides inside a
    value instead of being a field, and the declaration is what types it — so it
    is written in the reader's locale like any other date.
    """
    if not isinstance(value, dict):
        return str(value)
    append = declared.get("append")
    append = append if isinstance(append, dict) else {}
    written = _locale_writer(append)
    stamp = append.get("stamp")
    return ", ".join(
        f"{key}={written(item) if written and key == stamp else item}"
        for key, item in value.items()
    )


# ------------------------------------------------------------------ rows ---

def rows(table: str, show_all: bool = False) -> list[dict]:
    """Every row, in file order, minus what the table declares as hidden.

    A field that declares `show` lists the values a listing carries; everything
    else is what the listing hides, which is what `--all` puts back.
    """
    declared = _checked(table)
    loaded = store.load(table)
    if show_all:
        return loaded
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


# ----------------------------------------------------- what is not read ---


def opaque(table: str, field: str) -> str | None:
    """The type of `field` when it is one whose value does not come out, or
    `None` — the one read of `OPAQUE`, so every door of the engine agrees on
    which fields are which.

    It is public because the WebApp asks it before it builds a record: a page
    carries what a cell may draw, and the value of one of these is drawn as the
    mask and handed over by nobody.
    """
    kind = schema.field(table, field).get("type")
    return kind if kind in OPAQUE else None


def _checked(table: str) -> dict:
    """The table's declaration, with its `hashed` and `sealed` fields held to the
    closed list of the keys their type takes.

    The check runs HERE — at the point of use, where the engine reads a
    declaration to act on a field — and never where the registry loads the
    folder. The words are `i18n`'s and `i18n` is the core's, so a `data` layer
    reaching back for them would be the dependency pointing the wrong way; and a
    registry that dropped the offending table would trade a loud refusal for a
    blank screen, which is the one answer nobody can act on.
    """
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    if isinstance(fields, dict):
        for name, field in fields.items():
            if not isinstance(field, dict):
                continue
            kind = field.get("type")
            # The refusal is read off the list, so `method`, `algorithm`,
            # `opslimit`, `memlimit` and whatever key somebody invents next are
            # all refused BY NAME without this module having to predict them.
            allowed = LISTED_KEYS.get(kind) if isinstance(kind, str) else None
            if allowed is not None:
                _refuse_unlisted_keys(table, name, field, allowed)
    return declared


def _refuse_unlisted_keys(
    table: str, name: str, field: dict, allowed: tuple[str, ...]
) -> None:
    """Refuse a declaration of one of the two types that names a key its closed
    list lacks — by the name of the key, and of the type that lacks it."""
    for key in field:
        if key not in allowed:
            # `named` and not `key`: the refusal's own reason is already called
            # `key`, and the sentence is about the KEY OF THE DECLARATION.
            raise TableError(
                f"error.{field['type']}_key", field=label(table, name), named=key
            )


def hashed(table: str, field: str) -> bool:
    """Whether the field is of the type that stores a derivation (§4)."""
    return schema.field(table, field).get("type") == "hashed"


def sealed(table: str, field: str) -> bool:
    """Whether the field is of the type that carries a sealed value (§4)."""
    return schema.field(table, field).get("type") == "sealed"


def raw_of(table: str, field: str, value: Any) -> Any:
    """A value as the store keeps it — for whoever starts from the truth.

    A form opens on what a row already carries, and a cell that shows the stored
    value asks here. The two types that do not read are the ones the engine does
    NOT hand over: a derivation is only ever compared, a sealed value is only
    ever opened with the key, and whoever asks gets the refusal BY NAME — the
    name of the field, and of what the field is — instead of the value.
    """
    _checked(table)
    kind = opaque(table, field)
    if kind is not None:
        raise TableError(f"error.{kind}_value", field=label(table, field))
    return value


def verify(table: str, field: str, candidate: str, stored: str) -> bool:
    """Whether the candidate is what the row's `field` proved — a comparison, and
    never a string match (§4).

    The answer is a BOOL and never an exception: the right candidate is true, the
    wrong one is false, and the stored derivation handed back as its own candidate
    is false too, because this door compares and does not match strings. A stored
    value a hand edited is false for the same reason — an exception would take
    down the read that found it.

    What it REFUSES is the field, by name: one the table does not declare, and one
    it declares as something other than hashed. `raw_of` will not hand the value
    over, so the comparison is the only door into it — and a door into a
    derivation opens on a field that holds one.

    It reads its two arguments — the candidate and the stored derivation — and
    nothing else: no Access Phrase, no `settings.json`, no Working Folder. That is
    what makes a credential verifiable while AT is locked, and it is why the
    value comes IN: the engine hands the whole row over (`find` answers it
    derivation included) and whoever compares passes the stored value here.
    """
    _checked(table)
    declared = schema.field(table, field)
    if not declared:
        raise TableError(
            "error.unknown_hashed_field", table=table_name(table), field=field
        )
    if declared.get("type") != "hashed":
        raise TableError("error.not_hashed", field=label(table, field))
    return password.verify(candidate, stored)


# ------------------------------------------------------------- the types ---

# §4 fixes the types and each one has its rule; there is no choice per field.
# These two are the ones about time, and they are the ones a string cannot be
# trusted with: a day is a calendar day and an instant is a point in time, and
# the same words mean different things in each — so each shape is checked
# before anything parses it.
_DAY_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_INSTANT_SHAPE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")


def utc(value: datetime) -> str:
    """A point in time written the one way §4 allows: UTC, with milliseconds.

    It is public because §4's types are the core's, and whoever must WRITE one —
    the engine here, and the interpreter reading a sentence into an instant —
    writes it through this and not through a second spelling of its own.
    """
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _day(table: str, name: str, raw: Any) -> str:
    """A calendar day, with no time and no zone, resolved by the writer (§4).

    "Today" is your today: the day is read from the machine at the moment it is
    written, and it is stored as the text a person reads back.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if text == "today":
        return _WHEN["today"]()
    if not _DAY_SHAPE.match(text):
        raise TableError(
            "error.not_a_day", field=label(table, name), value=raw
        )
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        # The shape is right and the day is not — `2026-02-30` is not a date.
        raise TableError(
            "error.not_a_day", field=label(table, name), value=raw
        ) from None


def _instant(table: str, name: str, raw: Any) -> str:
    """A point in time: UTC, with milliseconds, whatever the machine's zone (§4).

    A value that carries its offset is taken as it stands; one that does not is
    read in the machine's zone, because that is what a person typing a clock
    time means. What is refused is the guess: a bare day is a day, not midnight
    somewhere, and it comes back as a refusal instead of becoming one.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if text == "now":
        return _WHEN["now"]()
    if not _INSTANT_SHAPE.match(text):
        raise TableError(
            "error.not_an_instant", field=label(table, name), value=raw
        )
    try:
        return utc(datetime.fromisoformat(text))
    except ValueError:
        raise TableError(
            "error.not_an_instant", field=label(table, name), value=raw
        ) from None


def _hashed(table: str, name: str, field: dict, raw: Any) -> str:
    """The derivation of what was typed, and never what was typed (§4).

    There is no method to choose here: the module that holds the primitive fixes
    it, and the closed list keeps the declaration from reaching it. What the
    declaration CAN say is a ceiling, and it measures the credential as it was
    typed — a value past it is refused before anything is derived.

    Nothing typed is not derived: the field is left empty, which is what
    `_require` refuses when the table declares it required and what a row reads
    back as nothing. A derivation of the empty value would be a credential
    nobody holds — not even whoever typed nothing — wearing the mask of one.
    """
    if raw is None:
        return ""
    text = raw.strip() if isinstance(raw, str) else str(raw)
    if not text:
        return ""
    ceiling = field.get("max_length")
    if isinstance(ceiling, int) and len(text) > ceiling:
        raise TableError("error.too_long", field=label(table, name), max=ceiling)
    return password.derive(text)


def _sealed(table: str, name: str, raw: Any) -> str:
    """The envelope that was handed in, and never anything else (§4).

    The engine does NOT seal: sealing needs the Vault Key, and no module holds a
    key while AT is up (§4, the three grades are a surface's choice). What the
    type does is the other half, and it is the half a table can do alone — it
    refuses what is not an envelope, so a cleartext typed into a sealed field is
    a refusal and not a secret written into a file a person copies and commits.
    The envelope seals the value by ITSELF (`vault.SEALED` ahead of it and the
    nonce inside the payload), so the field carries no second spelling of the
    algorithm and needs nothing beside it.

    Nothing typed is nothing stored, like the hashed field: an empty sealed field
    is what a clearing leaves, and it reads as nothing.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        return ""
    header, _, payload = text.partition(":")
    if header != vault.SEALED or not payload:
        raise TableError("error.not_sealed", field=label(table, name))
    return text


def _value(table: str, name: str, field: dict, raw: Any) -> Any:
    kind = field.get("type")
    if kind == "day":
        return _day(table, name, raw)
    if kind == "instant":
        return _instant(table, name, raw)
    if kind == "hashed":
        return _hashed(table, name, field, raw)
    if kind == "sealed":
        return _sealed(table, name, raw)
    if not isinstance(raw, str):
        return raw
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


def _stamp(kind: object) -> str:
    """When the entry was written, in the type the `append` declares.

    A table that declares nothing keeps the day this log was born with, which is
    what its rows already carry; one that declares `instant` gets the point in
    time §4 means by it. Neither is a naive local instant.
    """
    return _WHEN["now"]() if kind == "instant" else date.today().isoformat()


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


# -------------------------------------------------------------- closing ---

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


def referrers(table: str, number: int) -> list[tuple[str, str, int]]:
    """`(table, field, row id)` of every row that NAMES row `number` of `table`.

    Read from the DECLARATIONS and nothing else: a field whose `ref` can reach
    `table` is a field that can point here, and one that cannot is not made into
    a link by the shape of its value. The folder is never scanned for a number
    that looks like this one.
    """
    found: list[tuple[str, str, int]] = []
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


def _names(value: Any, target: str, number: int) -> bool:
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
    """
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
    store.spend(table, number)
    return row
