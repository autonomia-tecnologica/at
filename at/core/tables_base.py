"""The table engine's ground — the refusal, the identity of a row, the words of a
declaration, and the two types that do not read (`hashed`, `sealed`).

Everything else of `at.core.tables` stands on this module and none of it stands
back: it imports the data layer and nothing of its siblings.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from at.data import schema, store
from at.encryption import password
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


def format_id(table: str, number: int | None) -> str:
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
            field=label(table, declared or ""),
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
    nothing else: no Main Key, no `settings.json`, no Working Folder. That is
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
