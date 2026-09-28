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

**`notified` is the round's own guard against firing every pass, and it lives
on the row.** The clock's cadence is the minute (`at.core.clock.CADENCE`), and
a reminder's occurrence is the DAY — so a round that pushed once and asked
again ten minutes later would push again, all day, for as long as the day's
occurrence holds. `mark_notified` writes the one field the round owns on this
row, the way `jobs.reschedule` writes the one field the clock owns on a job's —
directly, with no actor and no via to name, because it is the engine keeping
its own bookkeeping and not an act a person or a via performed (§3).
"""

from __future__ import annotations

from datetime import date, timedelta

from at.core import tables
from at.data import store

# The table this module reads. It ships with the product: `data/defaults/reminder.json`.
REMINDER = "reminder"

FREQ = "freq"
ON_WEEKDAY = "on_weekday"
ON_DAY = "on_day"
ON_MONTH = "on_month"
ON_DATE = "on_date"
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


def notified(row: dict, day: date) -> bool:
    """Whether this row already pushed for `day` — the round's own guard.

    A row `mark_notified` has not yet written to, or one whose `notified` was
    hand-edited to something else, answers `False`: the safe side for a round
    is asking again, never staying silent on a day it never actually pushed
    for.
    """
    return _day(row, NOTIFIED) == day


def mark_notified(row: dict, day: date) -> dict:
    """Write `day` as the one this row was last pushed for.

    The one field the round owns on this row, written directly like
    `jobs.reschedule` writes the one field the clock owns on a job's — no
    actor, no via, no line: it is the engine's own bookkeeping and not an act
    (§3). A row the store no longer carries (deleted between the read and the
    write) is handed back untouched.
    """
    number = store.number_of(row)
    if number is None or store.find(REMINDER, number) is None:
        return row
    return tables.edit(REMINDER, number, {NOTIFIED: day.isoformat()})
