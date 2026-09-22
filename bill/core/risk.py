"""The demand filter's numbers — and what of them exists today (§4, item 15).

A demand carries a **risk**; the **risk threshold** lives in the settings; below
it the demand RUNS, and AT or above it it WAITS for a person. This module is where
the threshold is read, so that the ruler on the page and the filter that will
honour it (item 15, slice 3) read one number — a second reading of the same
setting is the one that drifts.

**What is not here yet, and it is not an accident.** The declared risks belong to
the permission catalogue: each entry declares its own and each field the number it
RAISES the demand to (§4), and the catalogue is item 11. `declared()` therefore
answers empty, and the ruler on the page says so instead of drawing a mark nobody
declared — the ruler draws what the product DECLARES, never a guess. It answers a
LIST rather than `None` so that the day the catalogue lands, the page draws it
with no line changing there.
"""

from __future__ import annotations

import math

from bill.core import settings

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
    """The risks the product declares today, one entry per catalogue entry.

    Empty, and it means it: the permission catalogue is item 11, and neither an
    action nor a field carries a number yet.
    """
    return []
