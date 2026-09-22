"""The English grammar — the same three domains, with its own words for them.

English does not agree its numbers with what they count, so one `two` serves for
two of anything, and `half` is half a dozen, half a pound and half past. What it
spends instead is on the shapes: the day of the month is an ordinal (`the 3rd`,
never `day 3`), the clock takes a period (`2pm`, which Portuguese does not
write), and half past is said from the other end — `half past two` where
Portuguese says `duas e meia`.

What both languages share is the rule underneath: the type the field declares is
what decides which domain a word is read in, and where the type does not decide,
the phrase comes back as a question and never as the likeliest reading.

The three readers below are the grammar's contract (`read_day`, `read_instant`,
`read_number`), and each answers what fits the type — `day` leaves as the writer's
local day, `instant` as a point in time in UTC.
"""

from __future__ import annotations

import re
from datetime import timedelta

from bill.nlu.grammar import (
    clock,
    day_of_month,
    fold,
    folded,
    next_weekday,
    number_of,
)
from bill.nlu.reading import Question, Reading, Residue, Refused, Value

# The week starts on Monday, as it does for Python and for the calendar both
# languages share. English says the day whole; the short forms are the
# vocabulary's business (slice 5), not the grammar's.
WEEKDAYS = folded({
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
})

# `tomorrow` is the day that comes; `today` is the day the clock is saying.
RELATIVE = folded({"today": 0, "tomorrow": 1})

# The numbers that are written out. One entry per form — English spends no
# gender on them, which is one place where it costs less than Portuguese.
NUMBERS = folded({
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90, "hundred": 100,
})

# `half` is half of anything: a dozen, a pound, an hour. In a number field it is
# 0,5 — and in an instant field it is nothing alone, because half is half OF an
# hour, and that hour has to be said.
HALVES = folded({"half": 0.5})

# The hours the language writes whole, with no hour left to complete.
FIXED = folded({"noon": (12, 0), "midnight": (0, 0)})

# `14:30`; `2pm` and `2:30 pm`, which is how English writes an afternoon.
CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
MERIDIEM = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s?(am|pm)$")
# `the 3rd` and `3rd`: the day of the month, which without the month is the next
# one to come. The word forms — `the third` — are the next list, not this one.
DAY_OF_MONTH = re.compile(r"^(?:the )?(\d{1,2})(?:st|nd|rd|th)$")
# `half past two`: the hour first, and the half after it — the other end of the
# same pair of words Portuguese says as `duas e meia`.
HALF_PAST = re.compile(r"^half past (.+)$")
# `two and a half`: the number, and the half added to it.
AND_A_HALF = re.compile(r"^(.+) and a half$")

# The point is the decimal separator here; the comma is of thousands, and
# thousands are not read.
DECIMAL = "."


def _count(text: str) -> int | float | None:
    """The number a word or a numeral names.

    It is the reading the three domains share: the same `two` is worth two in a
    number field, is the hour two in an instant field, and is the day two behind
    `the 2nd`, which nobody writes but which the rule need not forbid.
    """
    spelled = fold(text)
    if spelled in NUMBERS:
        return NUMBERS[spelled]
    if spelled in HALVES:
        return HALVES[spelled]
    return number_of(spelled, DECIMAL)


def read_day(text: str, now) -> Reading:
    """`today`, `tomorrow`, `friday` and `the 3rd`: a day said in English."""
    spelled = fold(text)
    if spelled in RELATIVE:
        return Value((now.date() + timedelta(days=RELATIVE[spelled])).isoformat())
    if spelled in WEEKDAYS:
        return Value(next_weekday(now.date(), WEEKDAYS[spelled]).isoformat())
    match = DAY_OF_MONTH.match(spelled)
    if match:
        return Value(day_of_month(now.date(), int(match.group(1))).isoformat())
    return Residue(text)


def read_instant(text: str, now) -> Reading:
    """`14:30`, `2pm`, `two`, `midnight`, `half past two`: an hour said in English."""
    spelled = fold(text)
    if spelled in FIXED:
        hour, minute = FIXED[spelled]
        return Value(clock(now.date(), hour, minute, text))
    if spelled in HALVES:
        # Half of which hour? The question goes back instead of the likeliest reading.
        return Question("nlu.ask.which_hour", text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock(now.date(), count, 30, text))
    match = CLOCK.match(spelled)
    if match:
        return Value(clock(now.date(), int(match.group(1)), int(match.group(2)), text))
    match = MERIDIEM.match(spelled)
    if match:
        hour = int(match.group(1))
        if not 1 <= hour <= 12:
            # `13pm` is a clock expression, and no clock has that hour.
            raise Refused("nlu.error.no_such_clock", value=text)
        afternoon = match.group(3) == "pm"
        return Value(
            clock(now.date(), hour % 12 + (12 if afternoon else 0),
                  int(match.group(2) or 0), text)
        )
    count = _count(spelled)
    if isinstance(count, int) and 0 <= count <= 23:
        # A number alone in an instant field is the hour it says, with no period
        # guessed at. Outside the hours that exist it is not an hour at all: it
        # comes back as a residue, and not as a guess between morning and night.
        return Value(clock(now.date(), count, 0, text))
    return Residue(text)


def read_number(text: str, now) -> Reading:
    """`3`, `3.5`, `two`, `half`, `two and a half`: a number said in English."""
    spelled = fold(text)
    match = AND_A_HALF.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        # `two and a half` is 2.5 — the same pair of words that Portuguese
        # writes from the other end. The type is what decides.
        return Value(count + 0.5)
    count = _count(spelled)
    if count is None:
        return Residue(text)
    return Value(count)
