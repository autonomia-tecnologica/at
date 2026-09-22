"""What the grammar read in a phrase — the four outcomes, and no fifth.

A phrase is read for a field, and the reading is one of four things. It **names a
value**, written the way the field's type stores it. It is a **residue**, and the
phrase comes back exactly as it went in, because it is not an expression of the
kind the field declares. It **names a value that cannot exist** — a day no
calendar has — and the refusal says so, with the reason's key, instead of letting
a typo become text. Or it **admits more than one reading** and the declared kind
settles none, and then a question goes back to whoever wrote the sentence, which
is what §9 means by "the ambiguous ones come back as a question".

There is no fifth outcome, and the reason is the rule this layer lives under:
**what does not resolve is residue, never a guess.** A reading that is not one of
these four would have to be the likeliest one, and the likeliest one is the guess
the interpreter is forbidden to make.
"""

from __future__ import annotations

from dataclasses import dataclass

from bill.i18n import tr


@dataclass(frozen=True)
class Value:
    """What the phrase named, spelled the way the declared type stores it.

    A `day` answers as the writer's local calendar day (`AAAA-MM-DD`), an
    `instant` answers as a point in time in UTC with milliseconds, and a number
    answers as the number. Those are the shapes §4 fixes, and the value leaves
    ready to be handed to the field it was read for.
    """

    value: object


@dataclass(frozen=True)
class Residue:
    """A phrase the grammar does not read as an expression of the kind.

    The text is the phrase as it came, untouched: the layer hands back what it
    did not read rather than picking a reading out of it. Whoever takes the
    sentence from here — the matcher of item 15, slice 7 — is the one that
    decides what a word the grammar did not spend is worth.
    """

    text: str


@dataclass(frozen=True)
class Question:
    """A phrase with more than one reading, and the declared kind settles none.

    `key` is the i18n key of what is being asked and `text` the phrase that
    raised it, so the surface can ask in the active language without knowing
    which language the phrase was written in.
    """

    key: str
    text: str


class Refused(Exception):
    """An expression of the kind that names a value which cannot exist.

    `dia 32` is a day expression and there is no such day; `25:00` is a clock
    expression and no clock has it. Neither is a residue — the phrase plainly
    means a date, a time — and neither can be resolved, so it is refused, with
    the reason's `i18n` key and never a value the person did not write.
    """

    def __init__(self, key: str, **kw: object):
        self.key = key
        self.kw = kw
        super().__init__(tr(key, **kw))


# The three readings a phrase may come back as, in one name: what `resolve`
# answers, and the whole of it.
Reading = Value | Residue | Question
