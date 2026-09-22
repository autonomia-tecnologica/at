"""The matcher: a sentence becomes one proposal, and never two.

The grammar reads a phrase WHOLE (`interpreter.resolve`), and nobody writes in
whole phrases: `cria uma tarefa pra sexta` is an action, a table, a connecting
word and a day. What this module does is SEGMENT the sentence and hand piece
after piece to the vocabulary and to the grammar, and to guess at neither.

**The widest window the vocabulary knows wins.** At each position the longest
expression the packed list carries is the one that is spent, which is what keeps
`em andamento` from being read as `em` and something else. What is left goes to
the grammar — the whole piece, never a smaller reading fished out of it — and
what the grammar does not read is **residue**: the words that carry content, and
the field a table declares as `primary` is where they go. The connecting words
are neither: they are particles, spent and silent, which is why `uma` and `pra`
never become a title.

**One action per request.** A sentence naming two actions is refused and not
disambiguated — a batch would be an action of its own the day a batch API
exists, with its own permission — and the same holds for two tables. A sentence
the catalogue does not reach is refused BY NAME, with the reason's key: what does
not resolve is residue, never a guess.

**The field a value lands in comes off the DECLARATION.** A day with a field word
before it (`desde sexta`) goes to that field; a day with no field word on it goes
to the `day` field the declaration does NOT fill by itself — the one whose
default is null — which is how `deadline` is the right field without that name
appearing anywhere below. A table that declares no such field (a `project`, whose
only day is `since`) has nowhere to put a day said alone, and asks which field
holds it instead of picking one.

Nothing here writes and nothing here measures a risk: the interpreter proposes,
the core validates and writes (§4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bill import i18n
from bill.core import tables
from bill.data import schema
from bill.i18n import tr
from bill.nlu import vocabulary
from bill.nlu.interpreter import KINDS, resolve
from bill.nlu.normalizer import canonical, fold
from bill.nlu.proposal import Proposal
from bill.nlu.reading import Question, Reading, Refused, Residue, Value

# What the segmentation writes for a word that carries no meaning at all. It is
# not a canonical — no name of the product is empty, which is what the suite's
# gate over the vocabulary says — so it cannot collide with one.
PARTICLE = ""

# The actions that act upon a row, and cannot be done without naming one.
_ROW_ACTIONS = frozenset({"view", "edit", "cancel", "delete"})


def match(
    text: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
) -> Proposal | Question:
    """What one sentence proposes, or the question it comes back as.

    `now` is the clock the grammar hangs its relative phrases from and it is
    injected for the same reason `resolve` injects it: the ruler is
    deterministic. A phrase of a kind that names a value no calendar or clock has
    raises `Refused`, exactly as it does one layer down.
    """
    language = language or i18n.active_code()
    now = now if now is not None else datetime.now()

    words = text.split()
    if not words:
        raise Refused("nlu.error.no_action", text=text)

    marks = _segmented(words, language)
    action = _action(marks, text)
    table = _table(marks, text)

    # A value of a closed vocabulary fills the field that carries it. The word is
    # spent either way: `alta` names a priority, it is not content.
    values: dict[str, Any] = {}
    for mark in marks:
        field = _enum_field(table, mark)
        if field is not None:
            values[field] = mark

    runs = _runs([mark is not None for mark in marks])
    row: Any = None
    if action in _ROW_ACTIONS:
        # The row is chosen among the pieces the grammar is not going to read:
        # `dia 3` is a day and stays one, and a bare `3` is a row when — and
        # only when — the action asked for one.
        row, runs = _take_row(table, words, runs)
        if row is None:
            raise Refused("nlu.error.no_row", table=tables.table_name(table))

    leftover: list[str] = []
    for start, end in runs:
        chunk = " ".join(words[start:end])
        field, reading = _read(
            table, chunk, _field_before(table, marks, start), language, now
        )
        if isinstance(reading, Question):
            # Nothing is filled in for what the grammar asked back: the whole
            # sentence comes back as the question, and no row is proposed.
            return reading
        if isinstance(reading, Value):
            values[field] = reading.value
        else:
            leftover.extend(words[start:end])

    residue = " ".join(leftover).strip()
    primary = schema.primary(table)
    if residue and primary:
        values[primary] = residue

    return Proposal(action=action, table=table, values=values, row=row)


# ------------------------------------------------------------ segmentation ---

def _segmented(words: list[str], language: str) -> list[str | None]:
    """Every word, marked with the canonical it names — or with nothing.

    Three answers, and they are the three the matcher has for a word: the
    canonical the vocabulary knows it by, `PARTICLE` for a word that carries no
    meaning, and `None` for what neither pass could place — which is the material
    the grammar and the residue are made of.
    """
    pairs = vocabulary.of(language)
    widest = max((len(expression.split()) for expression in pairs), default=1)
    particles = {fold(particle) for particle in vocabulary.particles(language)}
    folded = [fold(word) for word in words]

    marks: list[str | None] = []
    position = 0
    while position < len(words):
        size, found = _window(folded, position, widest, language)
        if size:
            marks.extend([found] * size)
        elif folded[position] in particles:
            marks.append(PARTICLE)
        else:
            marks.append(_machine(words[position]))
        position += size or 1
    return marks


def _window(folded: list[str], position: int, widest: int, language: str):
    """The widest window from `position` that the vocabulary knows, and what.

    The widest and not the nearest: a longer expression is a more precise thing
    than the words it is built of, and `em andamento` is one value, never `em`
    and a word about progress.
    """
    for size in range(min(widest, len(folded) - position), 0, -1):
        found = canonical(" ".join(folded[position:position + size]), language)
        if found:
            return size, found
    return 0, None


def _machine(word: str) -> str | None:
    """The machine word a person wrote as it is — a table's id, a field's name.

    The packed vocabulary is the product's, and a table a person declares in
    their own folder names nothing there yet: what still names it is the word the
    declaration itself carries, written as the declaration writes it. A
    per-instance vocabulary is item 16's, and this is the piece of it that costs
    nothing today — which is how the matcher meets the schema in hand.
    """
    written = fold(word)
    for name, declared in schema.tables().items():
        if fold(name) == written:
            return name
        fields = declared.get("fields")
        if not isinstance(fields, dict):
            continue
        for field in fields:
            if fold(field) == written:
                return field
    return None


# --------------------------------------------------------------- reading ---

def _read(
    table: str,
    chunk: str,
    named: str | None,
    language: str,
    now: datetime,
) -> tuple[str | None, Reading]:
    """What the grammar reads in one piece, and the field it lands in.

    A piece with a field word before it is read as the type THAT FIELD declares.
    A piece with no field word goes to the `day` field the declaration leaves
    open, and a table that declares none is asked about instead.
    """
    if named is not None:
        kind = schema.field(table, named).get("type")
        if kind in KINDS:
            return named, resolve(chunk, kind, language=language, now=now)
        # A field of a type the grammar has no reader for — a text is the
        # example — is not read at all: its content is residue, and residue is
        # what the primary field is for.
        return None, Residue(chunk)

    field = open_day_field(table)
    reading = resolve(chunk, "day", language=language, now=now)
    if field is None and isinstance(reading, Value):
        return None, Question("nlu.ask.which_field", chunk)
    return field, reading


def open_day_field(table: str) -> str | None:
    """The `day` field the declaration does NOT fill by itself.

    The rule is read off the DECLARATION and never off a list of names: it is
    the `day` field whose default is null, because a field that declares a value
    is already filled the moment the row is born. `since` declares `today` and is
    out; `deadline` declares `null` and is in — and neither name is written here.
    """
    found = [
        name
        for name, declared in _fields(table).items()
        if isinstance(declared, dict)
        and declared.get("type") == "day"
        and declared.get("default") is None
    ]
    return found[0] if len(found) == 1 else None


def _fields(table: str) -> dict:
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    return fields if isinstance(fields, dict) else {}


def _field_before(table: str, marks: list[str | None], start: int) -> str | None:
    """The field the piece at `start` is spoken into, when a word names one.

    The connecting words are stepped over — `com prazo sexta` names the field
    `deadline` — and a word that is not a field of THIS table names nothing.
    """
    index = start - 1
    while index >= 0 and marks[index] == PARTICLE:
        index -= 1
    if index < 0:
        return None
    mark = marks[index]
    return mark if mark and mark in _fields(table) else None


def _enum_field(table: str, mark: str | None) -> str | None:
    """The field of `table` whose closed vocabulary carries `mark`, if one does."""
    if not mark:
        return None
    for name, declared in _fields(table).items():
        if not isinstance(declared, dict):
            continue
        choices = declared.get("enum")
        if isinstance(choices, dict) and mark in choices:
            return name
    return None


# ------------------------------------------------------------- the request ---

def _action(marks: list[str | None], text: str) -> str:
    found = _named(marks, tables.ACTIONS)
    if not found:
        raise Refused("nlu.error.no_action", text=text)
    if len(found) > 1:
        raise Refused(
            "nlu.error.two_actions",
            first=tr(f"table.action.{found[0]}"),
            second=tr(f"table.action.{found[1]}"),
        )
    return found[0]


def _table(marks: list[str | None], text: str) -> str:
    found: list[str] = []
    for mark in marks:
        if mark and schema.of(mark) and mark not in found:
            found.append(mark)
    if not found:
        raise Refused("nlu.error.no_table", text=text)
    if len(found) > 1:
        raise Refused(
            "nlu.error.two_tables",
            first=tables.table_name(found[0]),
            second=tables.table_name(found[1]),
        )
    return found[0]


def _named(marks: list[str | None], universe) -> list[str]:
    """The marks that name a word of `universe`, in the order they were written."""
    found: list[str] = []
    for mark in marks:
        if mark and mark in universe and mark not in found:
            found.append(mark)
    return found


def _runs(spent: list[bool]) -> list[tuple[int, int]]:
    """The pieces the vocabulary did not spend, as `(start, end)` spans."""
    found: list[tuple[int, int]] = []
    start: int | None = None
    for index, done in enumerate([*spent, True]):
        if done and start is not None:
            found.append((start, index))
            start = None
        elif not done and start is None:
            start = index
    return found


def _take_row(table: str, words: list[str], runs: list[tuple[int, int]]):
    """The piece that names a row, and the pieces that are left.

    A row is named the way a person names one — `3`, `TASK-3` — and only a piece
    of one word is looked at, so `dia 3` stays a day.
    """
    kept: list[tuple[int, int]] = []
    found: Any = None
    for start, end in runs:
        if found is None and end - start == 1:
            number = tables.number_of(table, words[start])
            if number is not None:
                found = number
                continue
        kept.append((start, end))
    return found, kept
