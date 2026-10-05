"""The date, the time and the number, per language — code, and never a table.

The normalizer of item 15 is three pieces and this is the third. The slang and
jargon map is **data**, and it is the vocabulary packed beside the `i18n` blocks
(slice 5). The mechanical tolerance is **algorithm** (slice 5). What is left —
and it is the piece that decides what a word means — is this: the **grammar**,
which is code, one module per language, because here a word does not mean
anything alone. `meia` is half a dozen and is half past; `duas` is two and is two
o'clock; `sexta` is a weekday. The declared type of the field is what tells them
apart, and where it does not, the phrase is asked back.

Each language is a module beside this one, named by the very code the product
already calls it (`i18n.SUPPORTED`) — which is why the dispatch below is a name
and not a list. The two are written with the same shape so a reader can read one
against the other: `read_day`, `read_instant` and `read_number` are the whole
contract, and `read()` is what picks them. What the languages have in common is
not a rule of any language — the Gregorian calendar, the clock, the number a
numeral spells — so it lives here, and neither language writes a second calendar
of its own. The fold that compares a phrase to the language's own words is not
here: it is the product's one fold, and it lives with the rest of the mechanical
tolerance, in `at.nlu.normalizer`.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, time, timedelta

from at import i18n
from at.core import tables
from at.nlu.reading import Refused

# The readers every language's grammar must carry, keyed by the kind a field
# declares. This dict is the contract between this module and the language
# modules — the reason `read_day` and `read_number` can be called by name — and
# the whole of what the grammar answers in.
#
# `time` é a HORA-DO-DIA (`18:00`), e não o `instant` que o `day` completa: o
# lembrete guarda a que horas toca (`at`, uma lista), e a data dele mora noutro
# campo — ler `18h` como um ponto em UTC daria a hora de HOJE à hora que não tem
# dia. Os dois leem os mesmos números e as mesmas palavras; o que muda é o que
# sai.
KINDS = {
    "day": "read_day",
    "instant": "read_instant",
    "time": "read_time",
    "number": "read_number",
}


def of(language: str):
    """The grammar of a language, as the module that holds it.

    A language the product does not speak reads in the source language, which is
    where `i18n` already falls back to: a translation that lags must not leave a
    sentence unreadable.
    """
    code = language if language in i18n.SUPPORTED else i18n.SOURCE
    return importlib.import_module(f"{__name__}.{code}")


def read(language: str, kind: str):
    """The reader of a kind in a language — the one door to the grammar.

    `kind` is what the field declares: `day`, `instant` or `number`, and the
    whole of what the grammar answers in. A kind no reader answers to is a defect
    in whoever asked, and it is loud instead of becoming a residue.
    """
    name = KINDS.get(kind)
    if name is None:
        raise ValueError(f"unknown kind: {kind}")
    return getattr(of(language), name)


def phrases(language: str) -> tuple[str, ...]:
    """As FRASES de data que a linguagem reconhece INTEIRAS, da mais longa para a
    mais curta — o que o matcher precisa para não picá-las palavra a palavra.

    Uma frase composta (`final da semana que vem`) só se lê se chegar inteira ao
    leitor: separada, `semana` vira a frequência de um lembrete e as partículas
    (`da`, `que`) a picam. O matcher pergunta aqui os trechos a manter juntos, e
    `read_day` os lê. Uma linguagem que não declara frase nenhuma responde vazio.
    """
    listed = getattr(of(language), "PHRASES", {})
    return tuple(sorted(listed, key=lambda phrase: len(phrase.split()), reverse=True))


# ------------------------------------------------------------- the words ---

# The fold that compares a phrase to the language's own words is the product's
# one fold, and it lives in the normalizer beside the rest of the mechanical
# tolerance — the languages import it from there and do not write a second one.

def number_of(text: str, decimal: str) -> int | float | None:
    """The number a written numeral names, or nothing.

    `decimal` is the separator of the language reading it: the same `3,5` is
    three and a half in Portuguese and not a number at all in English, which
    writes `3.5`. Thousands are not read — a separator with three digits behind
    it is as likely to be one, and reading `3.000` as three in Portuguese would
    be a defect dressed up as a feature.
    """
    body = text.strip()
    sign = 1
    if body[:1] in ("-", "+"):
        sign = -1 if body[0] == "-" else 1
        body = body[1:]
    if decimal in body:
        whole, _, part = body.partition(decimal)
        if not whole.isdigit() or not part.isdigit():
            return None
        return sign * float(f"{whole}.{part}")
    if body.isdigit():
        return sign * int(body)
    return None


# ---------------------------------------------------------- the calendar ---

def next_weekday(now: date, weekday: int) -> date:
    """The named weekday: today when today is that day, and the coming one after.

    A week starts on Monday because Python's does — the language names the days
    and this counts them, which is why the count is here and not there.
    """
    return now + timedelta(days=(weekday - now.weekday()) % 7)


def day_of_month(now: date, day: int) -> date:
    """`dia N`: the coming N-th, this month's while it has not gone by.

    A day no month carries — the 32nd — is refused here instead of being looked
    for in a calendar it will never be in.
    """
    if not 1 <= day <= 31:
        raise Refused("nlu.error.no_such_day", value=day)
    year, month = now.year, now.month
    for _ in range(13):
        moment = _date_or_none(year, month, day)
        if moment is not None and moment >= now:
            return moment
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    raise Refused("nlu.error.no_such_day", value=day)


def _date_or_none(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        # This month is too short for that day; the next one may not be.
        return None


# ------------------------------------------------------------- the clock ---

def clock(day: date, hour: int, minute: int, wrote: str) -> str:
    """The instant a local clock time names, written the way §4 writes one.

    The day is the one the phrase hangs from — a clock time with no date on it is
    the writer's today, exactly as `today` is — and the zone is the machine's,
    because that is the zone whoever typed it is in. What leaves is UTC with
    milliseconds, so the same sentence read in São Paulo and in Lisbon is the
    same point in time and the two fields it lands in are comparable.

    An hour or a minute no clock has is refused, naming the phrase as it was
    written: `25:00` is a time expression, and there is no such time.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise Refused("nlu.error.no_such_clock", value=wrote)
    here = datetime.combine(day, time(hour, minute)).astimezone()
    return tables.utc(here)


def clock_text(hour: int, minute: int, wrote: str) -> str:
    """A hora-do-dia a phrase names, written the way the reminder's `at` stores
    one: `HH:MM`, with no day and no zone — a time of day is the same in every
    calendar, and the day it lands on is the row's own (`on_date`, `freq`).

    The refusal is `clock`'s own: `25:00` is a clock expression and no clock has
    it, so it does not become a residue and does not become a guess.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise Refused("nlu.error.no_such_clock", value=wrote)
    return f"{hour:02d}:{minute:02d}"
