"""How a value is read in a line — the closed vocabulary's word, the title a
reference resolves to, the day and the instant in the reader's locale."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from at.core.tables_base import (
    _INSTANT_SHAPE,
    _checked,
    enum_label,
    enum_values,
    format_id,
    opaque,
    title,
)
from at.data import schema, store
from at.i18n import tr

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
