"""The lembrete's own arithmetic — which reminders a DAY is about (§4, item 29
of `docs/en_US/container.md`: "the configured reminders can be notified").

**This module decides nothing about WHEN it runs, only what a given day
MEANS.** The table (`data/defaults/reminder.json`) carries the calendar rule —
`freq` and the anchor that goes with it — and this module reads it the way
`at.core.clock` reads a job's `when`: a pure function of a date and the rows,
with no clock of its own and no notifier at the other end. The round that fires
on its own and reaches a phone is another slice's work (item 29's second one);
what is here is the decision that slice will ask for.

**The anchor a row consults is the FREQ's, and never a guess from what happens
to be filled.** A row may carry `on_weekday`, `on_day`, `on_month` and `on_date`
all at once — a hand edit, a field left over from a changed `freq` — and `freq`
alone says which of them the recurrence reads: `weekly` reads `on_weekday` and
nothing else, `monthly` reads `on_day` alone, `yearly` reads `on_month` AND
`on_day` together (a month-day pair, the way a birthday is one), `once` reads
`on_date` alone, and `daily` reads none of them. There is no priority to break a
tie, because there is no tie: each `freq` owns exactly the fields it names, and
the others are not consulted at all.

**`since` is the floor, for every freq alike.** A row is never due before the
day it started, so a reminder created today does not fire for a `weekly` day
that fell last month.

**`warn_days` is read against EVERY occurrence, not the first.** A row with
`warn_days=[3, 1]` is inside its window on the day that is 3 days — or 1 day —
before ANY day the recurrence lands on, which is what lets a `weekly` reminder
warn ahead of each week's occurrence and not just its first.

**The date is INJECTED**, the way `clock.now` injects the instant: `today` is
this module's one reading of the machine's calendar, and the seam a test
freezes instead of sleeping to the next day.

**`notified` is the round's own guard, and it is per (day, HOUR).** A reminder
names the hours of its day (`at`: `["09:00", "18:00"]` — the water six times,
the medicine at its two doses), the clock's cadence is ten minutes
(`at.core.clock.CADENCE`), and the round covers every hour it runs for: a row
that pushed at 09:00 and is asked again ten minutes later must not push again
for THAT hour, while 18:00 is still owed its own. The mark is the pair, and
`mark_notified` writes the one field the round owns on this row the way
`jobs.reschedule` writes the one field the clock owns on a job's — directly,
with no actor and no via to name, because it is the engine keeping its own
bookkeeping and not an act a person or a via performed (§3).
"""

from __future__ import annotations

import re

from datetime import date, datetime, timedelta

from at.core import tables
from at.data import store

# The table this module reads. It ships with the product: `data/defaults/reminder.json`.
REMINDER = "reminder"

FREQ = "freq"
ON_WEEKDAY = "on_weekday"
ON_DAY = "on_day"
ON_MONTH = "on_month"
ON_DATE = "on_date"
# A que horas o dia deve tocar — o `at`, uma LISTA (`["09:00", "18:00"]`): é
# ela que diz quantos avisos o dia deve, e a hora marcada é o que a rodada lê
# para não tocar tudo de uma vez na primeira passada do dia.
AT = "at"
WARN_DAYS = "warn_days"
STATUS = "status"
SINCE = "since"
# The round's own bookkeeping — an ISO day, read the way `_day` reads any
# other. It is declared WITHOUT `"type": "day"` on purpose: that type is what
# tells `nlu.matcher.open_day_field` which field a bare date fills, and its own
# rule reads one field alone among the ones with no default — a second one
# would leave a sentence like "hoje" with nowhere to land. `notified` is never
# typed by a person, so it is exempted the same way `since` is (a default), but
# by carrying no `day` type instead of a default that would misstate a fresh
# row as already notified.
NOTIFIED = "notified"

ACTIVE = "active"
PAUSED = "paused"

DAILY = "daily"
WEEKLY = "weekly"
MONTHLY = "monthly"
YEARLY = "yearly"
ONCE = "once"
FREQUENCIES = (DAILY, WEEKLY, MONTHLY, YEARLY, ONCE)

# The act this table's own — `at-cli reminder due` (item 29's first slice). It
# is not one of the engine's six: it reads the store and rewrites no row, so it
# is declared under `permissions.NARROWED` and not among `tables.ACTIONS`.
DUE = "due"

# A forma de um horário no `at`: `HH:MM`, 24 horas — a mesma que o motor guarda,
# e o que a rodada lê para casar a hora marcada com o relógio. Um `at` que não
# casa (uma edição à mão) é ignorado, e não vira um aviso fora de hora.
HOUR = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# Quantos "já avisei" a linha guarda — fundo o bastante para a semana inteira de
# qualquer lembrete, e um teto para o campo não crescer sem fim.
HISTORY = 64


def today() -> date:
    """The day a pass is measured against — this module's one calendar read.

    A function and not an inline call, for the reason `clock.now` is one: a
    test moves the calendar instead of waiting for it, and the whole module
    reads the day in one place.
    """
    return date.today()


def _day(row: dict, name: str) -> date | None:
    text = row.get(name) if isinstance(row, dict) else None
    if not isinstance(text, str):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def occurs(row: dict, day: date) -> bool:
    """Whether this reminder's recurrence LANDS on `day` — the whole rule.

    A row that is not `active`, or whose `since` is still ahead of `day`, never
    occurs — the rule failing closed rather than a reminder firing on a paused
    row or on a day it had not started yet. What is read after that depends on
    `freq` alone, per the module's own rule about the anchor.
    """
    if not isinstance(row, dict) or row.get(STATUS) != ACTIVE:
        return False
    since = _day(row, SINCE)
    if since is not None and day < since:
        return False
    freq = row.get(FREQ)
    if freq == DAILY:
        return True
    if freq == WEEKLY:
        weekdays = row.get(ON_WEEKDAY)
        return isinstance(weekdays, list) and day.weekday() in weekdays
    if freq == MONTHLY:
        on_day = _int(row.get(ON_DAY))
        return on_day is not None and day.day == on_day
    if freq == YEARLY:
        on_month = _int(row.get(ON_MONTH))
        on_day = _int(row.get(ON_DAY))
        return (
            on_month is not None
            and on_day is not None
            and day.month == on_month
            and day.day == on_day
        )
    if freq == ONCE:
        on_date = _day(row, ON_DATE)
        return on_date is not None and day == on_date
    # A `freq` a hand edited to something the table does not enum is a row that
    # never occurs — failing closed, the same answer an unreadable `when` gives
    # the clock.
    return False


def hours(row: dict) -> list[str]:
    """Os horários do dia que a linha deve tocar, como `HH:MM`, em ordem.

    O `at` é uma LISTA (`["09:00", "18:00"]`) — a água seis vezes ao dia, o
    remédio nas duas doses — e é ela que diz QUANTOS avisos o dia deve. `occurs`
    diz o dia; isto diz a que horas, e a rodada precisa dos dois para não tocar
    a manhã inteira na primeira passada. Uma linha sem `at` legível não deve
    aviso nenhum: não há hora para casar.
    """
    raw = row.get(AT) if isinstance(row, dict) else None
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, list):
        return []
    found: list[str] = []
    for item in raw:
        text = str(item).strip()
        if HOUR.match(text):
            found.append(text)
    return sorted(found)


def _warn_days(row: dict) -> list[int]:
    warn = row.get(WARN_DAYS) if isinstance(row, dict) else None
    if not isinstance(warn, list):
        return []
    return [days for days in (_int(entry) for entry in warn) if days is not None]


def due(at: date | None = None, rows: list[dict] | None = None) -> dict[str, list[dict]]:
    """The active reminders `at` is about: the ones DUE, and the ones WARNED.

    `due` holds the rows whose recurrence lands ON `at`; `warn` holds the rows
    that do not land on `at` but land within their OWN `warn_days`, ahead of it —
    a row in both would be a row counted twice for the same occurrence, so a hit
    on `due` is never also read for its warning.

    `rows` is injected the way `at` is, so a test hands in reminders without a
    store; the CLI and any other caller that means the folder's own table reads
    `store.load(REMINDER)` and leaves this argument alone.
    """
    at = at if at is not None else today()
    candidates = rows if rows is not None else store.load(REMINDER)
    arrived: list[dict] = []
    warned: list[dict] = []
    for row in candidates:
        if occurs(row, at):
            arrived.append(row)
            continue
        if any(occurs(row, at + timedelta(days=days)) for days in _warn_days(row)):
            warned.append(row)
    return {"due": arrived, "warn": warned}


# O horizonte em que "o próximo disparo" é procurado — um ano e um dia, o maior
# ciclo que uma recorrência tem (`yearly`). Uma linha que não ocorre dentro dele
# não tem próximo: um `once` já vencido, um `monthly` no dia 31 de um mês que não
# o tem, um `freq` que falha fechado.
HORIZON = 366


def upcoming(row: dict, now: datetime | None = None) -> tuple[date, str] | None:
    """O PRÓXIMO disparo da linha — o dia e a hora —, ou `None` se nunca mais vem.

    É o que a tela de Lembretes mostra e o que separa um lembrete de uma tarefa:
    a tarefa tem prazo, o lembrete tem um PRÓXIMO toque. A regra é a de sempre,
    lida de `occurs` (o dia) e `hours` (as horas) e nunca reescrita aqui —
    procura-se para a frente, do dia de `now`, o primeiro dia que a recorrência
    alcança com uma hora ainda por vir.

    "Ainda por vir" espelha a janela da rodada (`ask._covers`): a hora marcada
    vale do seu minuto em diante, e nada depois. A de hoje às 19:00, lida às
    19:04, já é a de amanhã.
    """
    moment = now if now is not None else datetime.now()
    day = moment.date()
    times = hours(row)
    if not times:
        return None
    current = moment.hour * 60 + moment.minute
    for step in range(HORIZON):
        when = day + timedelta(days=step)
        if not occurs(row, when):
            continue
        for hour in times:
            if step > 0 or _minute(hour) >= current:
                return when, hour
    return None


def _minute(hour: str) -> int:
    """`HH:MM` no minuto do dia — a mesma aritmética que `ask._covers` faz."""
    return int(hour[:2]) * 60 + int(hour[3:])


def _stamps(row: dict) -> list[str]:
    """The "already pushed" marks the row carries, as `"AAAA-MM-DD HH:MM"`.

    Uma versão anterior gravava o DIA sozinho (`"2026-09-28"`); ele é lido como
    um carimbo sem hora, então não casa com horário nenhum e as horas restantes
    do dia ainda saem. O campo é do próprio round (§3), e o formato é dele.
    """
    held = row.get(NOTIFIED) if isinstance(row, dict) else None
    if isinstance(held, str):
        return [held]
    if isinstance(held, list):
        return [str(item) for item in held]
    return []


def notified(row: dict, day: date, hour: str) -> bool:
    """Whether this row already pushed for `day` at `hour` — the round's guard.

    It is per (day, hour): a reminder that names six hours of the day owes six
    pushes, and one does not cover the others. A row `mark_notified` has not yet
    written to, or one whose `notified` was hand-edited to something else,
    answers `False` — the safe side for a round is asking again.
    """
    return f"{day.isoformat()} {hour}" in _stamps(row)


def mark_notified(row: dict, day: date, hour: str) -> dict:
    """Write `day`+`hour` as one this row was pushed for.

    The one field the round owns on this row, written directly like
    `jobs.reschedule` writes the one field the clock owns on a job's — no
    actor, no via, no line: it is the engine's own bookkeeping and not an act
    (§3). A row the store no longer carries (deleted between the read and the
    write) is handed back untouched.
    """
    number = store.number_of(row)
    if number is None or store.find(REMINDER, number) is None:
        return row
    stamp = f"{day.isoformat()} {hour}"
    stamps = [entry for entry in _stamps(row) if entry != stamp]
    stamps.append(stamp)
    return tables.edit(REMINDER, number, {NOTIFIED: stamps[-HISTORY:]})
