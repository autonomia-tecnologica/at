"""The demand filter's numbers — and what of them exists today (§4, item 15).

A demand carries a **risk**; the **risk threshold** lives in the settings; below
it the demand RUNS, and AT or above it it WAITS for a person. This module is
where the threshold is read, so that the ruler on the page and the filter that
honours it read one number — a second reading of the same setting is the one
that drifts.

**The risk is a number, and this is where the core measures it.** Each entry of
the catalogue declares its own (`permissions.risk`: `0` a read, `0.2` creating or
editing the actor's own data, `0.5` overwriting or removing what existed, `0.8`
changing what the system allows), and an ARGUMENT may raise it — a field of a
table declares the number in its own declaration (`FIELD`), and a key of the
settings declares it in `at.core.settings`, which has no declaration to write it
in. `demand` is the highest among them and nothing else: with the scale bounded,
a sum would escape it and the ruler would stop being predictable.

**And the FOLDER adjusts the catalogue's numbers, which is the other half of the
promise.** §5: "o risco de cada ação é ajustável em `settings.json`". The map
lives in the settings (`BY_ACTION`), it is keyed by the catalogue's own
`object:action`, and where it carries a number inside the scale that number
GOVERNS: `adjusted` is the one reading of it, and `demand` and the ruler both
start from there, so the screen and the engine cannot disagree about what a
demand is measured at. It is an OVERRIDE and never a second home for the
numbers — what the catalogue declares is what governs every entry the folder did
not write — and a strange declaration (not a number, off the scale, or a name the
catalogue does not carry) is read as that same catalogue number and never as a
refusal, so a garbage value can never take a demand down.

**Whoever asks does not measure their own risk.** The number is read from the
catalogue, from the declarations and from this folder's own settings — three
homes a surface does not own — so the door a request arrives by is where the
measurement belongs (`at.ui.ask`), and the door is what compares it with the
threshold (`at.ui.ask.holds`) — the core measures, the door knows who is asking.
What the line of an act records of all this is the threshold that was in force
when the demand arrived, and never the demand's own number (§3).
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from at.core import permissions, settings
from at.data import schema

# The key of the threshold in `app/settings.json`, and the value of a folder that
# never chose (§4). The key's own name lives in `core.settings`, which owns the
# file's keys, and it is read from there so that the two homes are one.
KEY = settings.THRESHOLD
DEFAULT = 0.5

# The key of the per-action adjustment (§4/§5): a map of the catalogue's own
# `object:action` → the number the folder wants that entry to carry. It is the
# folder's OVERRIDE of `permissions.risk` and never a second home for the
# numbers — what an entry the folder did not write is measured at is the
# catalogue's own declaration.
BY_ACTION = settings.BY_ACTION

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


def _written() -> dict:
    """The adjustment map this folder wrote, or `{}` — read the way every strange
    declaration is read.

    A value that is not a map adjusts nothing, and it is not a refusal: the file
    is the person's, a hand may put anything in it, and a reader that raised over
    a typo would take down the whole demand filter because of a key nothing else
    reads. What a value MEANS is decided entry by entry (`_adjusted`).
    """
    written = settings.get(BY_ACTION, None)
    return written if isinstance(written, dict) else {}


def _adjusted(permission: str, written: dict) -> float:
    """The number that governs this entry, given the map — the one rule, read
    once per map so that the ruler does not open the file once per mark.

    A number the folder wrote GOVERNS, and it governs in place of the catalogue's
    — it may raise the entry or lower it. §4's "the bar does not lower itself" is
    about the THRESHOLD, which is the wall itself and is what an automatic act
    could otherwise walk under; this is the folder tuning the price of one action
    under its own hand, which is what §5 promises it may do.

    **Anything else leaves the catalogue's number standing**, which is the rule
    every strange declaration gets: a value that is not a number, a number off
    the scale the ruler draws, or a name the catalogue does not carry adjusts
    nothing and is never a refusal. So no strange value can take a demand DOWN —
    the defect it would be is the mirror of the boolean read as the top of the
    scale, and it is why `_number` is strict about what a number is.
    """
    value = _number(written.get(permission))
    if (
        value is not None
        and FLOOR <= value <= CEILING
        and permissions.is_known(permission)
    ):
        return value
    return permissions.risk(permission)


def adjusted(permission: str) -> float:
    """The number this catalogue entry is measured at in THIS folder (§4/§5).

    It is the catalogue's declaration with the folder's adjustment on top, and it
    is the ONE reading of the two: `demand` starts from it and the ruler draws it
    (`marks`), so the engine and the screen cannot say different numbers about
    the same entry.
    """
    return _adjusted(permission, _written())


def demand(object: str, action: str, arguments: Iterable[str] = ()) -> float:
    """The risk of a demand: the HIGHEST among the action and the arguments.

    The action's number is the catalogue's, ADJUSTED by what this folder wrote
    (`adjusted`) and read through `needed` so that an object that narrowed itself
    is priced for what it actually answers — a `secret` listing is `secret:read`,
    and its write is `secret:edit`. Each argument may raise it (`raised`), and the
    highest is the whole of the rule: a sum would escape the bounded scale, and
    the demand's risk has to be a mark a person can find on the ruler.
    """
    found = adjusted(permissions.needed(object, action))
    for name in arguments:
        found = max(found, raised(object, name))
    return min(max(found, FLOOR), CEILING)


def marks() -> list[dict]:
    """The marks the ruler draws: one per catalogue entry, carrying the number
    that governs it in this folder (§4, item 15).

    It is one entry per PERMISSION and not per number: two entries measured at
    the same number are two marks on the same spot, and the page says which
    permission is which. `key` is the permission's own name, machine word like
    every other canonical (§3), and `risk` the number the ruler draws.

    **The number is the ADJUSTED one and not the declared one**, and that is the
    whole of the decision: the marks and the line are what a person reads to know
    what runs and what waits, and a mark drawn from the catalogue while the
    filter compared against the folder's number would be the screen lying about
    the very thing it exists to show. `adjusted` is the one reading both use.

    **A number a field raises is not one of these**, and the page draws no mark
    for it: the ruler is the catalogue's, an argument's number belongs to a
    demand, and a mark that named no permission would be a mark nobody could
    read. What the field numbers are FOR is the demand (`demand`).

    The order is the catalogue's, so the marks arrive in a stable order and the
    page draws a list it did not sort — a surface that sorted them would be
    deciding something the catalogue already decided.
    """
    written = _written()
    return [
        {"key": name, "risk": _adjusted(name, written)}
        for name in permissions.all_permissions()
    ]
