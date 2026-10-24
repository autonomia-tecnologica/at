"""What was typed, read as the field's type — §4's types and the refusals of each."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from at.core.tables_base import (
    _DAY_SHAPE,
    _INSTANT_SHAPE,
    _WHEN,
    TableError,
    enum_values,
    label,
    number_of,
    utc,
)
from at.encryption import password, vault


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

    The engine does NOT seal: sealing needs the Main Key, and no module holds a
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
    return _typed_text(table, name, field, raw)


def _typed_text(table: str, name: str, field: dict, raw: str) -> Any:
    """A typed string read as a list, a reference, a ceilinged text, a closed
    vocabulary word or a scalar — in that order."""
    if field.get("type") == "list":
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
