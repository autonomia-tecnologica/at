"""The settings as the door's second act: `setting`, the line it owes and the version.
"""

from __future__ import annotations

import json

from at.core import (
    audit,
    files,
    permissions,
    settings,
)
from at.i18n import tr
from at.ui.ask_base import OK, REFUSED, USAGE
from at.ui.ask_risk import _arrival, _line

# ------------------------------------------------------------- the settings ---

# What a key nobody wrote answers, told apart from a key that holds `null`: the
# door says "not chosen" for the first and the value for the second, and the two
# are not the same answer.
_UNSET = object()


def setting(
    action: str,
    args: list[str],
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
) -> tuple[int, str]:
    """One act on the settings — the door the `cli` reaches them by (§4).

    The settings are an OBJECT of the catalogue and not a table, so they do not
    walk `run`: there are no rows, no fields and no lifecycle, and a sentence the
    interpreter reads never lands here. What they share with a table act is the
    whole of what §3 asks — the actor, the via and the line — and the line is
    written HERE, at the door, for the same reason it is written there: the
    engine does not know who asked nor by which road, and a line without them
    would be a line that pretends.

    **A read leaves nothing at all.** `list` and `view` are the one read
    (`permissions.NARROWED`), §3 makes a read not an act, and the folder is not
    versioned for one either: nothing changed, so there is nothing to keep. An
    `edit` is the act — it writes, leaves exactly one line, and ends in a version
    named by the very sentence the surface printed.

    The value is read by the CORE (`settings.literal`): `0.95` is the float the
    filter compares against and `forms` is the word the gate reads, and a surface
    that decided which is which would be a second reader of the file's shape.
    """
    if action == "list":
        if args:
            return USAGE, tr("setting.error.arguments")
        return OK, _settings_listing()
    if action == "view":
        if len(args) != 1:
            return USAGE, tr("setting.error.arguments")
        return OK, _settings_line(args[0])
    if action != "edit" or len(args) != 2:
        return USAGE, tr("setting.error.arguments")
    key, typed = args
    # The bar, read BEFORE the write — and it is this act that makes the reading
    # matter: editing `risk_threshold` moves the bar, so a reading taken after
    # the write would be the bar the demand chose and not the one it faced.
    bar = _arrival()
    try:
        written = settings.put(key, settings.literal(typed))
    except settings.Refused as refused:
        # A refusal is an act and leaves a line, with the reason's KEY and no
        # value — the value is what the person typed, and §3 keeps it out (§3,
        # `TheRefusalMask`).
        _line(
            permissions.SETTING, action, actor, via,
            audit.REFUSED, refused.key, str(refused), threshold=bar,
        )
        return REFUSED, str(refused)
    except files.ReadOnly as error:
        # The one writer's rule, answered here as the engine answers it there.
        saying = tr("cli.error.read_only", where=error.where)
        _line(
            permissions.SETTING, action, actor, via,
            audit.REFUSED, "cli.error.read_only", saying, threshold=bar,
        )
        return REFUSED, saying
    # The value is read BACK, so what the answer says is what the file now holds
    # and not what was typed: the write is the file's, and the file is the truth.
    saying = tr(
        "setting.edited",
        setting=written,
        value=_value_text(settings.get(written)),
    )
    _line(
        permissions.SETTING, action, actor, via, audit.OK, None, saying,
        threshold=bar,
    )
    return OK, saying


def _settings_listing() -> str:
    """Every key the door hands over — the ones the product reads and the ones
    this folder carries — with the value each one holds, aligned."""
    keys = settings.keys()
    width = max(len(key) for key in keys)
    return "\n".join(f"{key.ljust(width)}  {_setting_value(key)}" for key in keys)


def _setting_value(key: str) -> str:
    value = settings.get(key, _UNSET)
    return tr("setting.unset") if value is _UNSET else _value_text(value)


def _settings_line(key: str) -> str:
    """One key and its value — or the sentence that says the folder never chose.

    A key nobody set is an ANSWER and not a failure: §4's settings are the
    person's file, and a folder that never chose one is not a folder in trouble.
    What the door does not do is invent the default — that belongs to whoever
    reads the key (`nlu` its switch, `risk` its bar), and a second home for it
    here would be the one that drifts.
    """
    value = settings.get(key, _UNSET)
    if value is _UNSET:
        return tr("setting.unset.line", setting=key)
    return tr("setting.line", setting=key, value=_value_text(value))


def _value_text(value: object) -> str:
    """A value as a person reads it: a word as the word, and everything else the
    way the file writes it — `true` and not `True`, `0.95` and not a float's
    whole repr."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
