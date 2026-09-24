"""The audit — one line per act, and never one for a read (§3, item 15).

§3: "toda ação que entra pelo core vira uma linha". The line carries the 5W2H and
nothing else — what (`object:action`), where (the table), when (the instant),
who (the actor), how (the via) and the outcome — plus the reason KEY of a
refusal, and no cost. It stores no VALUE: what it cites of a row is a raw number
and never a `ref`, which is why the log never blocks a `delete` (§4).

**Where the line is born, and what that costs.** The one who knows the ACTOR and
the VIA is a door: the engine does not know either, and a line without them would
be a line that pretends. So the line is born at the door every surface reaches
the engine by — `at.ui.ask.run` — which is the road item 30's `versioning.commit`
already took for the same reason, and the page's table route walks it too. The
cost is exact and it is named here: **the engine's own writes do not leave a
line** — the migrations handing the catalogue over to a role, the engine's row
being born with the folder, a credential being derived, a secret being sealed.
Those are AT acting on itself; there is no actor and no via to name them with,
and inventing one would be the pretending §3 forbids. The day a surface demands
one of them, it comes through the door and gains its line with no second rule.

**The engine writes the line without the permission to create**, and by the same
road `core.secrets` takes to seal a value: `tables.create`, the engine's own
door. That is not a hole — it is where the ceiling lives: `audit` is narrowed to
`read` (`{"read": ["list", "view"]}`), so no surface offers a create and no role
carries `audit:create`, and what writes the line is the ENGINE, which demands no
permission of itself. What it costs is that a declaration a person deleted takes
the act down with it, because the line is part of the act and not a remark about
one — the audit is the record, and an act nobody can record is one AT refuses to
perform in silence.

**Reads leave nothing at all.** §3: "ler não é fazer, e auditar leitura faria o
rastro crescer mais rápido do que o uso". A refused READ leaves nothing either,
for the same reason — and a refused WRITE is a line, because a wall an actor
found is exactly what the log is for (§3, `audit:read` is the admin's alone).

**The instant is injected.** A test that reads the clock twice is a test that
disagrees with itself, so `log` takes the instant it stamps (`at`) and every
caller that does not pass one gets `moment()` — the single clock read of the
module, and the seam a test freezes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from at.core import actors, files, tables
from at.data import store

# The table this module is about. It is a system table like any other, and it
# ships with the product: `data/defaults/audit.json`.
AUDIT = "audit"

# The field names §3 lists, in one home so that the declaration, the engine and
# the suite are held to the same words. `table` is the table the act was on and
# `what` is the act in the catalogue's own form (`object:action`) — the two agree
# while every object that acts is a table, and the row carries both because a log
# read by a person wants the act in one word and the table as its own column.
WHAT = "what"
TABLE = "table"
WHEN = "when"
ACTOR = "actor"
VIA = "via"
STATUS = "status"
REASON = "reason"

# The outcome: what happened. An attempt that ran is `ok`, and one the engine or
# the ceiling refused is `refused` — §3 writes exactly two kinds of line.
OK = "ok"
REFUSED = "refused"
OUTCOMES = (OK, REFUSED)

# The vias §4 names, and the whole closed list. The surface that reaches the
# interpreter does NOT become the via: a sentence typed in the WebApp or in the
# terminal is recorded as `nlu`, because the road the act came through is the
# interpreter's and not the cloth it was typed on.
CLI = "cli"
WEBAPP = "webapp"
NLU = "nlu"
ENGINE = "engine"
WIZARD = "wizard"
VIAS = (CLI, WEBAPP, NLU, ENGINE, WIZARD)

# The reason a ceiling records. It is a KEY like every other reason, never a
# sentence: whoever reads it asks `i18n` for the words in their own language.
DENIED = "permission.denied"


def moment() -> str:
    """The instant this line is stamped with — the module's one clock read.

    It is written the way §4 writes a point in time, through `tables.utc`, so the
    engine has one spelling of an instant and not two. A test that must prove the
    stamp FREEZES this function instead of reading the clock beside it.
    """
    return tables.utc(datetime.now(timezone.utc))


def actor_of(row: dict | None) -> int | None:
    """The number the line cites as WHO acted, or `None` when nobody can be.

    **An act with no actor proved is the ENGINE's**, and that is what its row was
    born for (`actors.seed_engine`): whoever validated and wrote was the core, so
    naming it is the truth — and the folder that asks nobody (§3, the loopback
    with no credential) still gets a line that names somebody. The value is the
    row's NUMBER and never a `ref`: §3 makes the ids the log cites raw data, so
    deleting the actor later never becomes impossible because of the log.
    """
    chosen = row if isinstance(row, dict) and row else actors.engine_row()
    return store.number_of(chosen) if isinstance(chosen, dict) else None


def log(
    table: str,
    action: str,
    *,
    actor: dict | None = None,
    via: str = ENGINE,
    status: str = OK,
    reason: str | None = None,
    at: datetime | None = None,
) -> dict | None:
    """One act, one line — or nothing at all, when the run is read-only.

    A read-only run applies NOTHING (§3): the line is a write like any other, so
    a verification pass leaves no trail behind it — and the act it would have
    recorded is refused by the engine for the same reason.

    `reason` is the KEY of a refusal's message and never the words: §3 stores the
    "why" as an `i18n` key, so the same line reads in every language and no value
    a person typed is ever written into the log.
    """
    if files.readonly():
        return None
    values: dict[str, object] = {
        WHAT: f"{table}:{action}",
        TABLE: table,
        WHEN: tables.utc(at) if isinstance(at, datetime) else moment(),
        ACTOR: actor_of(actor),
        VIA: via,
        STATUS: status,
    }
    if reason is not None:
        values[REASON] = reason
    return tables.create(AUDIT, values)
