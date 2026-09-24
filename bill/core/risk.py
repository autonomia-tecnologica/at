"""The demand filter's numbers — and what of them exists today (§4, item 15).

A demand carries a **risk**; the **risk threshold** lives in the settings; below
it the demand RUNS, and AT or above it it WAITS for a person. This module is where
the threshold is read, so that the ruler on the page and the filter that will
honour it (item 15, slice 3) read one number — a second reading of the same
setting is the one that drifts.

**What is here and what is still owed.** The declared risks belong to the
permission catalogue: each entry declares its own, and `permissions.risk` is where
that number lives — the catalogue is what knows its entries, and reading it from
a second home is how the two would drift. What item 15 still owes is the OTHER
half of the sentence: a FIELD of a table may declare the number it RAISES the
demand to, and the demand's risk is the highest among the action and the arguments
it carries. Nothing of that is here yet, and the marks `declared()` draws are the
floor each entry starts from — which is what the ruler on the page shows.
"""

from __future__ import annotations

import math

from bill.core import permissions, settings

# The key of the threshold in `app/settings.json`, and the value of a folder that
# never chose (§4).
KEY = "risk_threshold"
DEFAULT = 0.5

# The scale the ruler draws and a risk lives on: nothing below zero, and the
# product declares nothing at one (§4).
FLOOR = 0.0
CEILING = 1.0


def threshold() -> float:
    """The price from which a demand waits.

    A value that is not a number is a setting that was never made, and the folder
    answers with the default — the same rule the page's own preferences carry. A
    number OUTSIDE the scale is brought into it, because the ruler draws from the
    floor to the ceiling and a mark off the scale is a mark off the drawing.
    """
    value = settings.get(KEY, DEFAULT)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT
    if not math.isfinite(value):
        return DEFAULT
    return min(max(float(value), FLOOR), CEILING)


def waits(risk: float) -> bool:
    """Whether a demand of this risk waits for a person: AT or above the line.

    §4 closes the boundary the document left open — "the price FROM WHICH a demand
    waits" — and the ruler draws it on the same side, so that what a person reads
    and what the engine does cannot disagree.
    """
    return risk >= threshold()


def declared() -> list[dict]:
    """The risks the product declares, one entry per catalogue entry — the marks
    the ruler draws (§4, item 15).

    It is one entry per PERMISSION and not per number: two entries that declare
    the same risk are two marks on the same spot, and the page says which
    permission is which. `key` is the permission's own name, machine word like
    every other canonical (§3), and `risk` the number the catalogue declares.

    The order is the catalogue's, so the marks arrive in a stable order and the
    page draws a list it did not sort — a surface that sorted them would be
    deciding something the catalogue already decided.
    """
    return [{"key": name, "risk": permissions.risk(name)} for name in permissions.all_permissions()]
