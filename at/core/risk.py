"""The demand filter's numbers — and what of them exists today (§4, item 15).

A demand carries a **risk**; the **risk threshold** lives in the settings; below
it the demand RUNS, and AT or above it it WAITS for a person. This module is
where the threshold is read, so that the ruler on the page and the filter that
will honour it read one number — a second reading of the same setting is the one
that drifts.

**The risk is a number, and this is where the core measures it.** Each entry of
the catalogue declares its own (`permissions.risk`: `0` a read, `0.2` creating or
editing the actor's own data, `0.5` overwriting or removing what existed, `0.8`
changing what the system allows), and an ARGUMENT may raise it — a field of a
table declares the number in its own declaration (`FIELD`), and a key of the
settings declares it in `at.core.settings`, which has no declaration to write it
in. `demand` is the highest among them and nothing else: with the scale bounded,
a sum would escape it and the ruler would stop being predictable.

**Whoever asks does not measure their own risk.** The number is read from the
catalogue, from the declarations and from this folder's own settings — three
homes a surface does not own — so the door a request arrives by is where the
measurement belongs (`at.ui.ask`), and the door is what will compare it with the
threshold the day the filter lands. Nothing waits yet: the job that holds a
demand at or above the line is the next slice, and today what the door records
of all this is the threshold that was in force when the act ran.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from at.core import permissions, settings
from at.data import schema

# The key of the threshold in `app/settings.json`, and the value of a folder that
# never chose (§4).
KEY = "risk_threshold"
DEFAULT = 0.5

# The scale the ruler draws and a risk lives on: nothing below zero, and the
# product declares nothing at one (§4).
FLOOR = 0.0
CEILING = 1.0

# The key a TABLE's field declares the number it raises a demand to (§4, item
# 15). It is a key of the declaration and not a list here, because what a field
# raises is the table's business — and a table that declares nothing raises
# nothing.
FIELD = "risk"


def _number(value: object) -> float | None:
    """The number this is, or `None` when it is not one.

    A boolean is not a number here, and that is not pedantry: in Python `True`
    is an `int`, and a declaration that answered `1` by saying `true` would be a
    switch read as the top of the scale.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def threshold() -> float:
    """The price from which a demand waits.

    A value that is not a number is a setting that was never made, and the folder
    answers with the default — the same rule the page's own preferences carry. A
    number OUTSIDE the scale is brought into it, because the ruler draws from the
    floor to the ceiling and a mark off the scale is a mark off the drawing.
    """
    value = _number(settings.get(KEY, DEFAULT))
    if value is None:
        return DEFAULT
    return min(max(value, FLOOR), CEILING)


def waits(risk: float) -> bool:
    """Whether a demand of this risk waits for a person: AT or above the line.

    §4 closes the boundary the document left open — "the price FROM WHICH a demand
    waits" — and the ruler draws it on the same side, so that what a person reads
    and what the engine does cannot disagree.
    """
    return risk >= threshold()


def raised(object: str, name: str) -> float:
    """The number this ARGUMENT raises the demand to, or the floor (§4, item 15).

    The declaration is read where it lives: a table writes it on the field
    (`FIELD`), and the settings — which are not a table, and have no schema — on
    the key (`settings.RAISED`). An argument that declares nothing raises
    NOTHING, and that absence is the answer: a table that declares no number
    makes a demand no dearer than the action already does, and so does a key
    nobody raised. It is never a refusal — the declaration is the folder's, and
    a strange one is read the way every strange declaration is, as the floor.
    """
    if object == permissions.SETTING:
        declared = settings.raised(name)
    else:
        declared = schema.field(object, name).get(FIELD)
    value = _number(declared)
    return FLOOR if value is None else min(max(value, FLOOR), CEILING)


def demand(object: str, action: str, arguments: Iterable[str] = ()) -> float:
    """The risk of a demand: the HIGHEST among the action and the arguments.

    The action's number is the catalogue's, read through `needed` so that an
    object that narrowed itself is priced for what it actually answers — a
    `secret` listing is `secret:read`, and its write is `secret:edit`. Each
    argument may raise it (`raised`), and the highest is the whole of the rule:
    a sum would escape the bounded scale, and the demand's risk has to be a mark
    a person can find on the ruler.
    """
    found = permissions.risk(permissions.needed(object, action))
    for name in arguments:
        found = max(found, raised(object, name))
    return min(max(found, FLOOR), CEILING)


def declared() -> list[dict]:
    """The risks the product declares, one entry per catalogue entry — the marks
    the ruler draws (§4, item 15).

    It is one entry per PERMISSION and not per number: two entries that declare
    the same risk are two marks on the same spot, and the page says which
    permission is which. `key` is the permission's own name, machine word like
    every other canonical (§3), and `risk` the number the catalogue declares.

    **A number a field raises is not one of these**, and the page draws no mark
    for it: the ruler is the catalogue's, an argument's number belongs to a
    demand, and a mark that named no permission would be a mark nobody could
    read. What the field numbers are FOR is the demand (`demand`).

    The order is the catalogue's, so the marks arrive in a stable order and the
    page draws a list it did not sort — a surface that sorted them would be
    deciding something the catalogue already decided.
    """
    return [{"key": name, "risk": permissions.risk(name)} for name in permissions.all_permissions()]
