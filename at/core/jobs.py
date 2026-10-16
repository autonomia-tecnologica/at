"""The job that waits — the demand that could not run (§4, item 15).

A demand carries a **risk** and the folder a **threshold**: below it the demand
RUNS, and at or above it it WAITS for a person. What waits is a **job, not a
queue** — the act that cannot run becomes a row of this table, in the state that
says it waits, and the answer names it. §4 already spoke of "a scheduled job"
with no table to hold it; this is the table.

**A job is a definition and a life, and not a demand that disappears once
served.** The row carries the act it performs (`what`, and the table it is on),
the arguments it needs to perform it, the actor that OWNS it, the instant it is
about and the state of its life: `waiting`, `approved`, `refused`, `done` and
`scheduled`.

**And `when` is the instant the job is ABOUT — which instant that is depends on
who drives the job, and that is why the fifth state exists.** The demand that
waited carries the instant it ARRIVED (`hold`), and it waits for a person; the
job the CLOCK drives carries the next instant it must ROUND, and `scheduled` is
the state that says so. The two are not the same thing and the table keeps them
apart by name: `waiting` is the demand that could not run, `scheduled` is the
act that will run again, and `at.core.clock` reads the second and never the
first. **The clock READS `when` and REWRITES it**: after every round it moves
the instant on by the cadence, which is what makes a job's life a series of
rounds instead of one, and what lets a round that did not go through be tried
again on the next pass instead of in a hot loop.

**The job runs with the via `engine` and with the actor that owns it, so its
ceiling is that actor's.** That is why the owner is a column and why the run
reads the ceiling again rather than trusting the approval: a role edited under a
waiting job is read on the next read like any other row (`actors.role_of`), and
a job whose owner lost the permission is one the engine refuses — by name, and
with a line, because a wall an actor found is exactly what the log is for (§3).

**Who waits is about presence, and that rule is the DOOR's** (`at.ui.ask`): the
act a person types or clicks never waits, because the act IS the approval, and
an act that runs on its own waits at or above the threshold, because the one who
cannot ask is the one who waits. What lives here is the row and its states; the
door is where the actor and the via exist, and therefore where the job is born —
the same place the `audit` line is born, and for the same reason.

**The arguments are the job's, and the log keeps none.** §3 keeps every value
out of the `audit`, and that promise is the AUDIT's: a job is a definition the
engine has to be able to run again, so its arguments travel in its own row — and
the ACT they describe leaves its line in the log like any other, with no value
in it either.

**The acts here are the filter's own, and the filter does not hold them.** Run,
approve and refuse are what a demand at the bar becomes; a filter that held its
own approval would be a door nobody could open, and one that held a released job
would ask for a second approval of the same act forever. That is why the door
hands the engine's run `released=True`, and why these three never walk `holds`.
"""

from __future__ import annotations

import json
from datetime import datetime

from at.core import audit, permissions, tables
from at.data import store
from at.i18n import tr

# The table this module is about. It is a system table like any other, and it
# ships with the product: `data/defaults/job.json`.
JOB = permissions.JOB

# The field names, in one home so that the declaration, the engine and the suite
# are held to the same words.
WHAT = "what"
TABLE = "table"
ARGUMENTS = "arguments"
ACTOR = "actor"
WHEN = "when"
STATUS = "status"

# The states of the job's life. `waiting` is the one that says it waits (§4,
# item 15), and three of the others are what an act leaves behind: a person
# approved it, a person refused it, or the engine ran it. `scheduled` is the
# fifth and it is the CLOCK's (item 24): a job that was DECLARED with a `when`
# and that rounds on its own, over and over, while the state stays where it is —
# a `scheduled` job is never `done`, because its life is a series of rounds and
# not one act.
WAITING = "waiting"
APPROVED = "approved"
REFUSED = "refused"
DONE = "done"
SCHEDULED = "scheduled"
STATES = (WAITING, APPROVED, REFUSED, DONE, SCHEDULED)

# The acts, in the order the tree offers them. `DECLARE` is NOT one of `ACTS`:
# it takes no single id — it takes the act to declare and the `when` it starts
# at — and the door reaches it by its own name before `ACTS` is even asked
# (item 24's fatia 2/3). The other four each answer to ONE row: `RUN` performs
# the act it holds, `APPROVE`/`REFUSE` are the person's word over a demand that
# waited, and `DISABLE` is the person's word over a round that was still
# `scheduled` — the verb `declare`'s own docstring already named as owed
# (`at.ui.webapp.app._declare_backup`).
RUN = "run"
APPROVE = "approve"
REFUSE = "refuse"
DECLARE = "declare"
DISABLE = "disable"
ACTS = (RUN, APPROVE, REFUSE, DISABLE)


class JobError(Exception):
    """Something the job's own door refuses — a state that does not answer the
    act, a machine trying the approval, an owner whose role moved.

    `key` is the FULL `i18n` key, because that is what the `audit` line records
    as a refusal's reason (§3): the words are read back from it in the language
    of whoever reads, and a short key would name nothing outside this module.
    """

    def __init__(self, key: str, **kw: object):
        self.key = f"job.{key}"
        self.kw = kw
        super().__init__(tr(self.key, **kw))


# ------------------------------------------------------------ the definition ---


def what(table: str, action: str) -> str:
    """The act in the catalogue's own form (`object:action`), which is how the
    `audit` spells one and therefore how a job names the act it holds."""
    return f"{table}:{action}"


def arguments(leftovers: list[str], values: dict) -> list[str]:
    """The act's arguments, written the way the door reads them back.

    A job is re-run through the SAME door the demand arrived by (`at.ui.ask.run`
    with `given=None`), so what the row carries is the argument list the door
    parses: the leftovers first, and then a `--set` pair for every value. That
    is why the spelling is not a JSON blob of our own invention — it is the one
    the door's own `_sets` already reads, and a second spelling would be a second
    parser.

    A value that is not a string is written the way `_scalar` reads it back:
    `true` and not `True`, `42` and not `42.0`. The type a FIELD declares is
    applied again when the job runs, which is the whole point of the arguments
    travelling as text.
    """
    spelled = list(leftovers)
    for name, value in values.items():
        spelled += ["--set", f"{name}={_written(value)}"]
    return spelled


def _written(value: object) -> str:
    if isinstance(value, bool):
        # NOT `str(True)`: `_scalar` reads `true` and `True` as two different
        # things, and the one it reads back is the lowercase one.
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def hold(
    table: str,
    action: str,
    leftovers: list[str],
    values: dict,
    *,
    actor: dict | None = None,
    at: datetime | None = None,
) -> dict:
    """The demand that cannot run becomes a row that waits — and the row is the
    whole of what it keeps.

    The ENGINE writes it, through its own door (`tables.create`), by the same
    road `core.audit` writes a line: a row is a row, and the counter that keeps
    an id spent counts this one too. The `actor` is the row's NUMBER and never a
    name, exactly as the log cites one — a raw number, so deleting the actor
    later never becomes impossible because of the job.

    **No line is left here, and that is the item's own rule.** §3 writes a line
    for every WRITE and every REFUSAL, and a demand that waits is neither: it did
    not run and it was not refused. What records it is the JOB — the act, the
    owner and the instant — and the lines arrive when it has an outcome: the
    approval, the refusal, and the run.
    """
    return tables.create(
        JOB,
        {
            WHAT: what(table, action),
            TABLE: table,
            ARGUMENTS: arguments(leftovers, values),
            ACTOR: audit.actor_of(actor),
            WHEN: tables.utc(at) if isinstance(at, datetime) else audit.moment(),
            STATUS: WAITING,
        },
    )


def declare(
    table: str,
    action: str,
    leftovers: list[str],
    values: dict,
    when: str,
    *,
    actor: dict | None = None,
) -> dict:
    """The job a person DECLARES, born `scheduled` and never `waiting` —
    item 24's "a job declared with a when comes round on its own".

    It shares every column `hold` writes, through the same door
    (`tables.create`), for the same reason: a row is a row. The one thing
    `hold` computes and this does not is `when` — `hold` carries the instant a
    demand ARRIVED, which the engine always knows; a declaration carries the
    instant a person TYPED, which only the schema's own `instant` type can
    tell apart from a day, a bare word, or nonsense, and refuse by name when
    it is none of those (`tables._instant`). This module does not parse a
    second time what the engine already refuses correctly.
    """
    return tables.create(
        JOB,
        {
            WHAT: what(table, action),
            TABLE: table,
            ARGUMENTS: arguments(leftovers, values),
            ACTOR: audit.actor_of(actor),
            WHEN: when,
            STATUS: SCHEDULED,
        },
    )


# ------------------------------------------------------------- the life ---


def find(pid: object) -> dict:
    """The row a number names, refused by the engine's own words when there is
    none — a job is a row, and the id a person types is read like every other."""
    return tables.find(JOB, pid)


def state(row: dict) -> str:
    """The state the row carries, or the empty string for one a hand edited.

    It is read and never trusted: a row whose state is not one of the four
    answers no act at all (`_waiting` and `_approved` both refuse it), which is
    the rule failing closed rather than a job the engine runs on a strange word.
    """
    value = row.get(STATUS)
    return value if isinstance(value, str) else ""


def instant(row: dict) -> datetime | None:
    """The point in time `when` carries, or `None` — read and never trusted.

    The value is written in the one spelling §4 gives an instant (`tables.utc`:
    UTC, with milliseconds), and a row a hand edited to something else answers
    `None` — which is the clock reading it as "not due", the rule failing closed
    rather than a job fired on a strange word. A value with no zone is that same
    strange value: an instant AT cannot place is one it does not act on.
    """
    text = row.get(WHEN) if isinstance(row, dict) else None
    if not isinstance(text, str):
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def owner(row: dict) -> dict | None:
    """The ACTOR row the job belongs to, or `None` — the owner, resolved.

    The row carries the actor's number and the resolution happens HERE, on every
    read, for the reason `actors.role_of` resolves the role on every read: the
    store is the truth, and a rebuilt row would be a second copy of a fact that
    lives in it. A number nobody wears answers `None`, and the ceiling of a job
    nobody owns is nothing — which is the rule failing closed.
    """
    number = row.get(ACTOR) if isinstance(row, dict) else None
    if isinstance(number, bool) or not isinstance(number, int):
        return None
    return store.find("actor", number)


def waiting(row: dict) -> None:
    """The guard every answer to a WAITING demand passes: a job that already has
    an outcome is refused by name, with the state it is in."""
    if state(row) != WAITING:
        raise JobError(
            "error.not_waiting",
            id=shown(row),
            status=tables.enum_label(JOB, STATUS, state(row)),
        )


def released(row: dict) -> None:
    """The guard the RUN passes: what a person released, and nothing else.

    A job that still waits is refused here and not run, which is the whole of
    what the approval is FOR — and a job that already ran or was refused is
    refused for the sibling reason.
    """
    if state(row) != APPROVED:
        raise JobError(
            "error.not_approved",
            id=shown(row),
            status=tables.enum_label(JOB, STATUS, state(row)),
        )


def scheduled(row: dict) -> None:
    """The guard the DISABLE passes: a round the clock still drives, and
    nothing else — a row that already answered an outcome, or that never
    was `scheduled`, is refused by name, with the state it is in."""
    if state(row) != SCHEDULED:
        raise JobError(
            "error.not_scheduled",
            id=shown(row),
            status=tables.enum_label(JOB, STATUS, state(row)),
        )


def shown(row: dict) -> str:
    """The id a person reads and types back — `JOB-3`, like every other row."""
    number = store.number_of(row)
    return tables.format_id(JOB, number) if number is not None else ""


def approve(row: dict) -> dict:
    """The job released by a person: `waiting` becomes `approved`.

    The approval does NOT run the job, and that is the whole reason the state
    exists: the person's act is the word over the demand, and the ACT belongs to
    the engine's clock — asked for by `at-cli job run` today, and fired by the
    clock of item 24 tomorrow, with no second model.
    """
    waiting(row)
    return tables.edit(JOB, store.number_of(row), {STATUS: APPROVED})


def refuse(row: dict) -> dict:
    """The job denied by a person: `waiting` becomes `refused`, and the row stays.

    It is not a deletion: a job is the record of a demand that could not run, and
    a record that vanished when it was answered would be a log with holes.
    """
    waiting(row)
    return tables.edit(JOB, store.number_of(row), {STATUS: REFUSED})


def disable(row: dict) -> dict:
    """The job a person turns OFF: `scheduled` becomes `refused`.

    No sixth state is added for it. `refused` already means "a person said
    no to this round ever running", which is exactly what turning a
    schedule off is — reusing it is the one-model rule item 15 already
    gives `waiting`/`refused`, read for a second kind of row instead of a
    second value the schema's enum would carry forever. The clock's own gate
    (`_driven`) is what then keeps it from ever being found by `clock.due`
    again, the same way a `waiting` row never is.
    """
    scheduled(row)
    return tables.edit(JOB, store.number_of(row), {STATUS: REFUSED})


def done(row: dict) -> dict:
    """The job the engine ran: `approved` becomes `done`.

    Only a run that WENT THROUGH ends here. An act the engine refused leaves the
    job `approved` — the refusal is its own line in the `audit`, and leaving the
    job released is what lets the same job be asked for again once whatever
    refused the act has been dealt with.
    """
    released(row)
    return tables.edit(JOB, store.number_of(row), {STATUS: DONE})


def _driven(row: dict) -> int | None:
    """The row's number, when the STORE still says the clock drives it.

    The state a pass read is a snapshot, and the store is the truth: AT answers a
    request in a thread and the `cli` is another process, so a person may have
    approved or refused a job between the read and the write. The two transitions
    below write only where the state still says `scheduled`, which is what keeps
    the clock from overwriting a word that arrived after it looked.
    """
    number = store.number_of(row)
    held = store.find(JOB, number) if number is not None else None
    if held is None or state(held) != SCHEDULED:
        return None
    return number


def reschedule(row: dict, written: str) -> dict:
    """The next instant this job may round — the `when` the clock REWRITES.

    It is the one write the clock makes to the row it just rounded: the act it
    performed belongs to the engine, and the only thing the clock owns of the
    job is WHEN it comes round again. Moving the instant on is what keeps a
    single appointment from firing twice, and what makes a round that did not go
    through wait for the next pass instead of being retried in a loop.

    `written` is the instant already spelled the way §4 spells one, because the
    cadence is the clock's and this module is not the one that knows it. A row
    the clock no longer owns — one a person answered while the round was being
    prepared — is handed back untouched (`_driven`).
    """
    number = _driven(row)
    if number is None:
        return row
    return tables.edit(JOB, number, {WHEN: written})


def waits(row: dict) -> dict:
    """The round that ended WAITING for approval — `scheduled` becomes `waiting`.

    It is item 15's model, and the whole of what "no second model" means: a
    round whose demand is at or above the bar does not become a queue, a lock or
    a second record — it becomes THIS ROW, in the state that says it waits, and
    a person's approval is what releases it. No second row is born and no
    instant is rewritten: the job is waiting for somebody, and `when` keeps
    saying when it came round.

    A row the clock no longer owns is handed back untouched, for the reason
    `reschedule` gives.
    """
    number = _driven(row)
    if number is None:
        return row
    return tables.edit(JOB, number, {STATUS: WAITING})


def stored(row: dict) -> list[str]:
    """The arguments the row carries, read as the list of strings they are.

    Read and never trusted, like the state: a row a hand edited to something
    that is not a list answers no argument at all, and the act it holds is then
    run with none — which the engine refuses, by name, like any other argument
    it cannot read.
    """
    value = row.get(ARGUMENTS) if isinstance(row, dict) else None
    return [str(item) for item in value] if isinstance(value, list) else []


def release(row: dict) -> tuple[str, str]:
    """The act the job holds, split the way it was written: `(table, action)`.

    A job carries one act in the catalogue's form (`object:action`), and this is
    the one place that reads it back. It is the inverse of `what`, and the two
    live together so the spelling cannot drift from its reading.
    """
    table, _, action = str(row.get(WHAT) or "").partition(":")
    return table, action
