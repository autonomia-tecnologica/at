"""The interpreter: the date, the time and the number, read in the active language.

Whoever does the work inside the `nlu` layer is this module (glossary). What it
consults is the grammar of the language being written — code, one module per
language — and what it answers in are the two fixed types of §4 together with
the plain number: a `day` is the writer's local calendar day, an `instant` is a
point in time in UTC, and the same sentence read in São Paulo and in Lisbon is
one same day and two different instants.

Nothing here writes, decides or measures a risk: the interpreter reads a phrase
and hands back a reading. Whoever validates and writes is `core` (§4), and the
risk is the core's to measure, because whoever asks does not assess their own.
"""

from __future__ import annotations

from datetime import datetime

from at import i18n
from at.nlu import grammar
from at.nlu.reading import Reading

# The kinds a field may declare, and the whole of what the grammar answers in:
# the two fixed types of §4, and the number a field with no type of its own holds.
KINDS = tuple(grammar.KINDS)


def resolve(
    text: str,
    kind: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
) -> Reading:
    """What the active language's grammar reads in `text`, for a field of `kind`.

    `now` is the clock the relative phrases hang from — `hoje`, `sexta`, `amanhã`
    — and it is injectable so the ruler is deterministic: production passes
    nothing and gets the machine's clock and the machine's zone, which is the
    zone of whoever is typing. The reading is then a `Value`, a `Residue` or a
    `Question`; an expression that names a value which cannot exist raises
    `Refused`, and nothing here ever answers with a guess.
    """
    language = language or i18n.active_code()
    now = now or datetime.now()
    return grammar.read(language, kind)(text, now)
