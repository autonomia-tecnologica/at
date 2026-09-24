"""The Portuguese grammar — where the language costs more than English.

A number in Portuguese agrees with what it counts, so one `um` is `um` and `uma`,
one two is `dois` and `duas`, one half is `meio` and `meia`. And the same word
lives in two domains at once: `duas` is two and is two o'clock; `meia` is half —
of a dozen, of a kilo — and is half past, which is half past SOME hour. What
separates the two readings is the type the field declares: a number field
answers `2`, an instant field answers `02:00`, and `meia` alone in an instant
field has no hour to be half past — so it comes back as a question instead of
becoming a guess.

`sexta` costs the same way: it is a weekday, and in a day field that is what it
says. Nothing here reads it as the sixth of anything.

The three readers below are the grammar's contract (`read_day`, `read_instant`,
`read_number`), and each answers what fits the type — `day` leaves as the writer's
local day, `instant` as a point in time in UTC.
"""

from __future__ import annotations

import re
from datetime import timedelta

from at.nlu.grammar import clock, day_of_month, next_weekday, number_of
from at.nlu.normalizer import fold, folded
from at.nlu.reading import Question, Reading, Residue, Refused, Value

# The week starts on Monday, as it does for the calendar both languages share.
# The two spellings live side by side because both are written: `sexta` and
# `sexta-feira` fold to different keys, and both are the same Friday.
WEEKDAYS = folded({
    "segunda": 0, "segunda-feira": 0,
    "terça": 1, "terça-feira": 1,
    "quarta": 2, "quarta-feira": 2,
    "quinta": 3, "quinta-feira": 3,
    "sexta": 4, "sexta-feira": 4,
    "sábado": 5,
    "domingo": 6,
})

# `amanhã` is the day that comes; `hoje` is the day the clock is saying.
RELATIVE = folded({"hoje": 0, "amanhã": 1})

# The numbers that are written out. One entry per form — the gender changes the
# word and never the value, and `duas` and `dois` are the same two.
NUMBERS = folded({
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
    "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
    "cem": 100, "cento": 100,
})

# `meia` is half: of a dozen, of a kilo, of an hour. In a number field it is 0.5 —
# and in an instant field it is nothing alone, because half an hour is half of
# some hour.
HALVES = folded({"meia": 0.5, "meio": 0.5})

# The word for half of the hour — `meia`, and not `meio`: `meio` is half a kilo,
# and an hour has no masculine. It is the one that asks, alone in an instant
# field, because half an hour is half of some hour.
HALF_PAST_WORD = fold("meia")

# The hours the language writes whole, with no hour left to complete.
FIXED = folded({
    "meia-noite": (0, 0),
    "meio-dia": (12, 0),
    "meio-dia e meia": (12, 30),
})

# `14:30` and `14h30`; `14h` too, because that is how a whole hour is written.
CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
CLOCK_H = re.compile(r"^(\d{1,2})h(\d{2})?$")
# `dia 3` and `dia três`: the day of the month, which without the month is the
# next one to come.
DAY_OF_MONTH = re.compile(r"^dia (.+)$")
# `duas e meia`: the hour that was said, and the half of it.
HALF_PAST = re.compile(r"^(.+) e mei[ao]$")

# The comma is the decimal separator here; the point is of thousands, and
# thousands are not read.
DECIMAL = ","


def _count(text: str) -> int | float | None:
    """The number a word or a numeral names.

    It is the reading the three domains share: the same `duas` is worth two in a
    number field, is the hour two in an instant field, and is the day two behind
    `dia duas`, which nobody writes but which the rule need not forbid.
    """
    spelled = fold(text)
    if spelled in NUMBERS:
        return NUMBERS[spelled]
    if spelled in HALVES:
        return HALVES[spelled]
    return number_of(spelled, DECIMAL)


def read_day(text: str, now) -> Reading:
    """`hoje`, `amanhã`, `sexta` and `dia 3`: a day said in Portuguese."""
    spelled = fold(text)
    if spelled in RELATIVE:
        return Value((now.date() + timedelta(days=RELATIVE[spelled])).isoformat())
    if spelled in WEEKDAYS:
        return Value(next_weekday(now.date(), WEEKDAYS[spelled]).isoformat())
    match = DAY_OF_MONTH.match(spelled)
    if match:
        count = _count(match.group(1))
        if count is None:
            # `dia` and a word that is not a number: not a date.
            return Residue(text)
        if not isinstance(count, int):
            raise Refused("nlu.error.no_such_day", value=match.group(1))
        return Value(day_of_month(now.date(), count).isoformat())
    return Residue(text)


def read_instant(text: str, now) -> Reading:
    """`14:30`, `14h`, `duas`, `meia-noite`, `duas e meia`: an hour in Portuguese."""
    spelled = fold(text)
    if spelled in FIXED:
        hour, minute = FIXED[spelled]
        return Value(clock(now.date(), hour, minute, text))
    if spelled == HALF_PAST_WORD:
        # Half an hour of which hour? The question goes back instead of the
        # likeliest reading.
        return Question("nlu.ask.which_hour", text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock(now.date(), count, 30, text))
    for shape in (CLOCK, CLOCK_H):
        match = shape.match(spelled)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            return Value(clock(now.date(), hour, minute, text))
    count = _count(spelled)
    if isinstance(count, int) and 0 <= count <= 23:
        # A number alone in an instant field is the hour it says, with no twelve
        # added and no period supposed. Outside the hours that exist it is not an
        # hour: it comes back as a residue, and not as a guessed period of day.
        return Value(clock(now.date(), count, 0, text))
    return Residue(text)


def read_number(text: str, now) -> Reading:
    """`3`, `3,5`, `duas`, `meia`, `duas e meia`: a number in Portuguese."""
    spelled = fold(text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        # `duas e meia` is 2.5 — the same pair of words that an instant field
        # reads as half past two. The type is what decides.
        return Value(count + 0.5)
    count = _count(spelled)
    if count is None:
        return Residue(text)
    return Value(count)
