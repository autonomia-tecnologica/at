"""The clock — what fires a job on its own (§4, item 24).

**A job that only runs when somebody asks is not the scheduled job §4 already
speaks of.** The table of item 15 gives a job a definition and a life, and this
module is the other half of it: a job DECLARED with a `when` comes round on its
own, while AT is up, and a round that ends waiting for approval waits as a job —
item 15's model, with no second one.

**The clock is a RULE, and the process that keeps it is the WebApp's.** What
lives here is *when a job comes round*, *what a missed instant means* and *what
the next one is*; `at.ui.ask.tick` performs the round — the filter, the act, the
line and the version belong to a door, which is the same argument that puts the
`audit` line there — and `at.ui.webapp.app` is the process that keeps waking it
while AT is up. **The clock leaves the WebApp the day the ENGINE leaves it, and
that is another item's work**: today what manages a job IS the WebApp, and a job
whose manager is down has nobody to ask.

**The cadence is the clock's, and its granularity is the MINUTE.** `CADENCE` is
how long a job waits between two rounds, and it is ONE number for the whole
folder: the declaration of a job says WHEN it starts, and the rhythm after that
belongs to the clock. **That is a limit worth naming, not hiding**: every
declared job rounds on the same cadence, so a job that must not act every round
reads its own interval the way the versioning write does — it looks at the stamp
of the last version and only commits when the interval has passed. The grain is
the log's price too: every round leaves a line and a version, so a fine cadence
is a folder with a long history.

**A missed instant is RECOVERED, never lost and never replayed in full.** A job
whose `when` went by while AT was down is due the moment AT comes up, and it
rounds ONCE: the next instant is measured from the round that happened and not
from the appointment it missed, so an AT that was off for a week comes back to
one round and not to a week of them. The line that says so is the clock's own
(`job:recovered`, written by the door before the round runs), because §3 writes
a line for every act and the recovery is one the engine performs on its own.

**The instant is INJECTED.** `now` is this module's one reading of the machine's
clock and the seam a test freezes — the same shape `audit.moment` gives the
line's stamp — so the suite proves the clock with the clock it hands in, and no
test depends on the machine's hour or on a network.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from at.core import jobs, tables
from at.data import store

# The cadence (§4, item 24): how long a job waits between two rounds, and
# therefore the grain of the whole schedule. It is read in MINUTES, and it is
# the clock's own — a job's declaration says when it starts and nothing else,
# because a period is a field the table does not carry. Ten is the number the
# versioning cadence settled on (§4, item 30), which is the one job the folder
# already has: an idle folder gets its version at that grain.
CADENCE = timedelta(minutes=10)

# The act the clock performs when it recovers a round AT was not up for. It is
# this module's own word, the way `job:run` is the object's: §3 writes a line for
# every act, and a recovery is one — the ANSWER's half is the door's, which is
# where the line and the version are written.
RECOVERED = "recovered"


def now() -> datetime:
    """The instant a pass is measured against — this module's one clock read.

    A function and not an inline call so that a test moves the clock instead of
    sleeping through a cadence, and so that the whole module reads the hour in
    one place. It is the same shape `audit.moment` gives the line's stamp, and
    for the same reason: a test that reads the machine's clock twice is a test
    that disagrees with itself.
    """
    return datetime.now(timezone.utc)


def due(state: str, at: datetime | None = None) -> list[dict]:
    """The jobs of this state whose instant has ARRIVED, oldest first.

    It is the whole of what the clock reads. A job that is not in `state` is not
    the clock's to round — a `waiting` demand waits for a person, and a `done`
    or `refused` job is over — and a row whose `when` does not read as an
    instant is not due, which is the rule failing closed rather than a job fired
    on a strange word (`jobs.instant`).

    The order is the INSTANT's and not the file's: two jobs that came round
    together are rounded in the order they were due, so the log reads the way
    the schedule did.
    """
    at = at if at is not None else now()
    arrived: list[tuple[datetime, dict]] = []
    for row in store.load(jobs.JOB):
        if jobs.state(row) != state:
            continue
        moment = jobs.instant(row)
        if moment is None or moment > at:
            continue
        arrived.append((moment, row))
    arrived.sort(key=lambda pair: pair[0])
    return [row for _, row in arrived]


def missed(row: dict, at: datetime | None = None) -> bool:
    """Whether this instant went by with AT down — the round that is RECOVERED.

    One cadence is the slack, and nothing else could be: the clock wakes on its
    own rhythm, so a round fired at the instant it was due is late by less than
    the time it waits between rounds, and anything older than that is a pass
    that did not happen. A row whose instant cannot be read is not a missed
    round — it is not a round at all.
    """
    at = at if at is not None else now()
    moment = jobs.instant(row)
    return moment is not None and at - moment > CADENCE


def next_instant(at: datetime) -> str:
    """The instant the round just fired gives way to — the `when` REWRITTEN.

    It is measured from the ROUND and never from the appointment the round may
    have missed, and that is the whole of the catch-up: an AT that was down for
    a week comes back to one round, because the instant it leaves behind is the
    next one after now and not the next one after a week ago.

    It is spelled through `tables.utc` like every other instant in the folder,
    so the engine has one spelling of a point in time and not two.
    """
    return tables.utc(at + CADENCE)
