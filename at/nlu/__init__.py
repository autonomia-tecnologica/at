"""The `nlu` layer: a sentence becomes one proposal, and nothing else (§4).

It is a **resource, not a surface**: the WebApp and the `cli` reach it, the actor
is the person and the via is `nlu`. Inside it, the glossary's three names hold —
`nlu` is this layer, the **interpreter** is whoever works in it, and the
**vocabulary** is the dictionary it consults per language. The vocabulary is data
and lands in slice 5; the grammar, which is code and lives one module per
language, is what exists here.

What the layer answers is a **reading**: a value, a residue, a question, or a
refusal (§4, and the item's own rule — what does not resolve is residue, never a
guess). It does not write, does not decide and has no ceiling of its own.

Three doors open into it. `resolve` reads a date, a time or a number in the
active language's grammar; `canonical` names the machine word a person's word
means, however it was typed; and `propose` takes the whole of a sentence — the
action, the table, the values and the residue — through the **matcher**.

The layer has a **switch**, and it is named after the interpreter rather than
after the `agent` of §4, because two names that would touch each other do not
coexist (glossary). It is born ON, and turning it off is a subtraction: the word
leaves the tree, `propose` refuses, and nothing else changes — the tables, the
page and the `cli` keep working, which is what §5 means by the language layer
being a resource and not a surface.
"""

from __future__ import annotations

from datetime import datetime

from at import i18n
from at.core import settings
from at.nlu.interpreter import KINDS, resolve
from at.nlu.matcher import match
from at.nlu.normalizer import canonical
from at.nlu.proposal import Proposal
from at.nlu.reading import Question, Reading, Refused, Residue, Value

# The key of the switch in `app/settings.json`. Turning the interpreter off takes
# it out of the core API and the word out of the tree, and takes nothing else.
SWITCH = "interpreter"


def enabled() -> bool:
    """Whether the interpreter's function is on. Born on, for a folder that
    never chose — a folder that has no settings at all runs with it."""
    return bool(settings.get(SWITCH, True))


def propose(
    text: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
    main_key: str | None = None,
) -> Proposal | Question:
    """What a sentence proposes, or the question it comes back as.

    This is the door of the **core API**, and it is the only one the surfaces
    use: the matcher below it does the reading, and the switch is checked here,
    where the API begins. A sentence outside the catalogue raises `Refused` with
    the reason's `i18n` key — the surface answers in the active language without
    owning the words.

    **A `Refused` the matcher raised for `nlu.error.no_action` or
    `nlu.error.no_table` gets one more door before it is re-raised** — the
    decisor (`at.core.decisor`, TASK-180): a slang layer that reads the same
    sentence through Jev and either applies a rewritten one, asks for it to be
    confirmed, or stands by the very refusal the matcher already raised. It is
    reached HERE and nowhere inside the matcher, which is why it is imported
    lazily — `match`, the grammar and the vocabulary carry no word of it, and
    none of this changes when the decisor's own switch does. `main_key` has no
    caller in `cli` or the WebApp yet; it exists so the decisor can open its
    credential the day a surface hands one in, and it does nothing where none
    arrives.
    """
    if not enabled():
        raise Refused("nlu.error.interpreter_off")
    try:
        return match(text, language=language, now=now)
    except Refused as refused:
        from at.core import decisor

        decided = decisor.decide(
            refused,
            text,
            language=language or i18n.active_code(),
            now=now,
            main_key=main_key,
        )
        if decided is not None:
            return decided
        raise
