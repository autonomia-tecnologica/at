"""The decisor: what a sentence Jev read becomes, when the deterministic
matcher found no action, no table, or neither (§4's own rule for the layer —
"what does not resolve is residue, never a guess" — read from the OUTSIDE of
it; TASK-180, fatia 1/3).

**It is `at.nlu.propose`'s own fallback, and nothing else's.** `nlu` stays
exactly the layer it always was: `matcher.py`, `normalizer.py`,
`interpreter.py`, `reading.py` and the vocabulary files carry no word of this
module, and the suite's own gate over them does not change. What changes is
`propose`'s one door: a `Refused` the matcher raised for `nlu.error.no_action`
or `nlu.error.no_table` — and no other reason — is handed here before it is
re-raised, and this module answers either `None` (stand by the refusal) or the
same three shapes `propose` always answered (`Proposal`, `Question`, or a
`Refused` the deterministic path raises on ITS OWN when the rewritten sentence
still does not read).

**Three tiers, read off the risk the ACTION already carries on §4's own
scale.** A read (`list`, `view`) is cheap to get wrong — a person sees a
listing that was not what they meant and asks again — so it auto-applies from
`0.7`. A write is not: it auto-applies only from `0.9`, and confirms (never
silently) from `0.5`. Below `0.5`, or either half of the guess landing on
`jev.NONE`, is the same answer as no guess at all — the sentence is handed
back to the `Refused` that was already on its way out. The two thresholds and
the floor are `jev-test/slang_dispatch.py`'s own numbers, proven against real
slang before this module existed; this fatia is the engine that CARRIES them
into the product, not a re-derivation of them.

**Auto rewrites, and resubmits to the REAL matcher — never to a second
reading of its own.** The rewrite plants the vocabulary's own words for the
guessed action and table at the front of the sentence (`jev.spoken`), so what
runs next is `at.nlu.matcher.match` on an ORDINARY sentence: the date, the
number, the row, the residue — every one of them is read exactly as it always
was, because nothing about THAT reading is this module's to repeat. Confirm
asks instead of applying, through the very `Question` shape `cli` and WebApp
already print — the rewritten sentence is what the person is asked to repeat,
so saying yes is saying that sentence again and walking the ordinary road.

**The switch is this module's own, separate from the interpreter's, and born
ON.** `nlu.SWITCH` ("interpreter") governs the deterministic layer, which
calls no service and so has nothing to weigh against being on by default; this
one (`SWITCH`, "decisor") governs a call OUT, and still starts on — a folder
that never chose gets the feature, and `settings.json` is where it is turned
back off. The two switches share nothing: turning the interpreter off already
takes `propose` out of the core API before this module is ever reached, and
turning this one off takes only the Jev fallback out, leaving the
deterministic reading exactly as it was.

**The credential lives in the Cofre, scoped to `jev.SERVICE`, and this module
never seals one.** Sealing is `at.core.secrets.seal`'s own door, carried out
once by whoever provisions the folder with a Main Key — the same three grades
of §4 govern how a caller comes to hold the string. What THIS module does is
the read: a `main_key` handed to `decide` opens the one row of `secret` scoped
`jev` (`at.core.secrets.open_value`), and no key at all — nobody passed one,
the row is not there, the phrase is wrong — answers `None` exactly the way
`open_value` already does, which this module turns into "stand by the
refusal" rather than a crash over a credential that was never provisioned.
`main_key` has no caller yet in `cli` or the WebApp (this fatia does not touch
either): the engine is complete and proven with an injected key and an
injected Jev client, and wiring a live Main Key through a surface is a later
fatia's own decision, not a gap in this one.
"""

from __future__ import annotations

from datetime import datetime

from at.core import jev, permissions, secrets, settings, tables
from at.data import store
from at.nlu import matcher
from at.nlu.proposal import Proposal
from at.nlu.reading import Question, Refused

# The key of this module's own switch in `app/settings.json` — separate from
# `at.nlu.SWITCH`, because two switches that touched each other would be the
# two names the glossary already forbids touching. Born ON (see the module
# docstring): a folder that never chose still gets the fallback, and turning
# it off is what `settings.json` is for.
SWITCH = "decisor"

# The two, and only two, reasons `propose` hands a refusal here instead of
# re-raising it outright — read off the exact keys `at.nlu.matcher` raises
# them with, never off a guess at what "ambiguous" might also mean. Real
# ambiguity (two actions, two tables) and the grammar's own `Question` are
# NOT here, and `decide` answers `None` for every other key for exactly that
# reason.
NO_ACTION = "nlu.error.no_action"
NO_TABLE = "nlu.error.no_table"
TRIGGERS = (NO_ACTION, NO_TABLE)

# The three tiers `_tier` answers with, and the only three there are.
AUTO = "auto"
CONFIRM = "confirm"
REFUSE = "refuse"

# §4's own scale, carried from the prototype that proved it (module docstring):
# a READ auto-applies cheaper than a WRITE does, and both confirm from the same
# floor before the guess is worth nothing at all.
READ_THRESHOLD = 0.7
WRITE_THRESHOLD = 0.9
CONFIRM_FLOOR = 0.5

# The `i18n` key of the question a CONFIRM tier asks — carried in `nlu.json`
# beside `ask.which_field` and `ask.which_hour`, because it is the same shape
# of question the matcher's own grammar already asks back, and a surface that
# prints one already knows how to print the other.
ASK_KEY = "nlu.ask.slang"


def enabled() -> bool:
    """Whether this module's own fallback is on. Born on (see the docstring)."""
    return bool(settings.get(SWITCH, True))


def decide(
    refused: Refused,
    text: str,
    *,
    language: str,
    now: datetime | None = None,
    main_key: str | None = None,
    transport: jev.Transport | None = None,
) -> Proposal | Question | None:
    """What `text` becomes once Jev has read it, or `None` to stand by
    `refused` exactly as it was raised.

    `None` is the answer for every door this module is not: the refusal is
    not one of the two triggers, the switch is off, there is no credential to
    open, or Jev itself did not answer (`jev.JevError` — the network, the key,
    a shape this reader does not know). None of those is this module's to
    raise over; `propose` already has a `Refused` ready to re-raise, and a
    service that could not be reached is not a reason to replace it with a
    worse one.
    """
    if refused.key not in TRIGGERS:
        return None
    if not enabled():
        return None
    api_key = _credential(main_key)
    if api_key is None:
        return None
    try:
        guess = jev.decide(text, language=language, api_key=api_key, transport=transport)
    except jev.JevError:
        return None
    tier = _tier(guess)
    if tier == REFUSE:
        return None
    rewritten = _rewrite(text, guess, language)
    if tier == CONFIRM:
        return Question(ASK_KEY, rewritten)
    return matcher.match(rewritten, language=language, now=now)


def _tier(guess: jev.Decision) -> str:
    """Which of the three tiers this guess lands in (the module docstring's
    own scale) — `jev.NONE` on either half is the floor itself and nothing
    below it, because a guess that names nothing is not a confidence problem."""
    if guess.action == jev.NONE or guess.table == jev.NONE:
        return REFUSE
    threshold = WRITE_THRESHOLD if guess.action in tables.WRITES else READ_THRESHOLD
    if guess.confidence >= threshold:
        return AUTO
    if guess.confidence >= CONFIRM_FLOOR:
        return CONFIRM
    return REFUSE


def _rewrite(text: str, guess: jev.Decision, language: str) -> str:
    """`text`, with the guessed action and table planted at the front in
    words the deterministic vocabulary ALREADY reads — what the matcher
    resolves next with no help from this module (the docstring's own
    "resubmits to the real matcher")."""
    words = [jev.spoken(guess.action, language), jev.spoken(guess.table, language)]
    prefix = " ".join(word for word in words if word)
    return f"{prefix} {text}".strip() if prefix else text


def _credential(main_key: str | None) -> str | None:
    """The Jev API key, opened from the Cofre with `main_key` — or `None` for
    every way there is nothing to open: no key was handed in, no row of
    `secret` is scoped `jev` yet, or the phrase does not open the one there
    is (`secrets.open_value`'s own three-ways-to-nothing)."""
    if not main_key:
        return None
    row = _row(jev.SERVICE)
    if row is None:
        return None
    return secrets.open_value(row, main_key)


def _row(service: str) -> dict | None:
    """The one row of `secret` scoped to `service`, or `None` — read off the
    store directly, the way a credential that proves nothing of its own is
    found before anything about it is opened."""
    for row in store.load(permissions.SECRET):
        if row.get(secrets.SCOPE) == service:
            return row
    return None
