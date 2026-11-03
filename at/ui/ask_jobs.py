"""The job's acts and the clock's rounds: the door's third and fifth acts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from at.core import (
    actors,
    audit,
    clock,
    files,
    jobs,
    permissions,
    risk,
    tables,
)
from at.i18n import tr
from at.ui.ask_base import OK, REFUSED, USAGE, _sets
from at.ui.ask_listing import _listing, _viewing
from at.ui.ask_risk import _arrival, _line, holds
from at.ui.ask_run import run

# ------------------------------------------------------------------ the job ---


def job(
    action: str,
    args: list[str],
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
) -> tuple[int, str]:
    """One act on a job — the door the `cli` reaches it by (§4, item 15).

    **The reads are the engine's and leave nothing.** `list` and `view` are
    `job:read`, §3 makes a read not an act, and the folder is not versioned for
    one either: the job's listing is a listing, and it walks the very helpers a
    table's does.

    **The three acts are the object's own, and each leaves one line.** They are
    not the engine's six — none of them rewrites a field of a row through the
    surface's words — so they do not walk `run`; what they share with a table act
    is the whole of what §3 asks (the actor, the via, the line and the version),
    and that is written here, at the door, for the same reason it is written
    there.

    **The approval is a line of its own, and separate from the job.** §5 says it
    with all the letters: the approval happens inside AT, with the session in
    force, and the line carries the actor and the via it came through. It is not
    written into the job's row — the row carries the STATE, and the trail carries
    who decided and by which road.

    A refusal is a line too, and the reason is the KEY of the sentence the person
    read (`jobs.JobError.key`), never the words and never a value.
    """
    if action == "list":
        code, text, _, _ = _listing(jobs.JOB, args)
        return code, text
    if action == "view":
        # The `cli` prints the engine's listing and reads nothing else, which is
        # the whole of what this door owes a terminal — the row a conversation
        # would draw is `ask`'s to carry (`_acted`), and it is not this one.
        code, text, _ = _viewing(jobs.JOB, args)
        return code, text
    if action == jobs.DECLARE:
        return _declared(args, actor=actor, via=via)
    if action not in jobs.ACTS or len(args) != 1:
        return USAGE, tr("job.error.arguments")

    bar = _arrival()
    try:
        row = jobs.find(args[0])
    except tables.TableError as error:
        # The id names no row of the table, and the refusal is the ENGINE's
        # sentence — so it is a line like every other refusal (§3), with the
        # reason's key, written here because the lookup happens before the act
        # and the engine's own door is not the one that found it.
        _line(
            jobs.JOB, action, actor, via, audit.REFUSED, f"table.{error.key}",
            str(error), threshold=bar,
        )
        raise
    try:
        if action == jobs.RUN:
            return _ran(row)
        _approval(action, actor)
        settled = _SETTLED[action](row)
        saying = tr(_SAID[action], id=jobs.shown(settled))
    except jobs.JobError as refused:
        _line(
            jobs.JOB, action, actor, via, audit.REFUSED, refused.key, str(refused),
            threshold=bar,
        )
        return REFUSED, str(refused)
    _line(jobs.JOB, action, actor, via, audit.OK, None, saying, threshold=bar)
    return OK, saying


# The person's word over a row, by action — `APPROVE`/`REFUSE` over a demand
# that waited, `DISABLE` over a round that was still `scheduled`. One map and
# not a chain of `if`s, so a third word of this shape is a third entry and not
# a third branch.
_SETTLED: dict[str, Callable[[dict], dict]] = {
    jobs.APPROVE: jobs.approve,
    jobs.REFUSE: jobs.refuse,
    jobs.DISABLE: jobs.disable,
}

_SAID: dict[str, str] = {
    jobs.APPROVE: "job.approved",
    jobs.REFUSE: "job.refused",
    jobs.DISABLE: "job.disabled",
}


def _declared(
    args: list[str], *, actor: dict | None, via: str
) -> tuple[int, str]:
    """`job declare <table> <action> [...] [--set field=value ...] --when
    <instant>` — the row born `scheduled`, through `jobs.declare`.

    `--when` is pulled out first, wherever it sits, because it is not the
    underlying act's own argument — it is the JOB's, the one thing a
    declaration adds over the act it holds. What is left is read the way
    every table act already is (`_sets`): the first two leftovers name the
    table and the action, and the rest travel on as the act's own.
    """
    when, rest = _pulled("--when", args)
    values, leftovers = _sets(rest)
    if when is None or len(leftovers) < 2:
        return USAGE, tr("job.error.arguments")
    table, action, leftovers = leftovers[0], leftovers[1], leftovers[2:]
    bar = _arrival()
    try:
        row = jobs.declare(table, action, leftovers, values, when, actor=actor)
    except tables.TableError as error:
        _line(
            jobs.JOB, jobs.DECLARE, actor, via, audit.REFUSED, f"table.{error.key}",
            str(error), threshold=bar,
        )
        raise
    saying = tr("job.declared", id=jobs.shown(row))
    _line(jobs.JOB, jobs.DECLARE, actor, via, audit.OK, None, saying, threshold=bar)
    return OK, saying


def _pulled(flag: str, args: list[str]) -> tuple[str | None, list[str]]:
    """One `flag value` pair taken out of `args`, wherever it sits — the rest,
    in the order it arrived, and `None` for the flag when it was not there."""
    rest: list[str] = []
    found: str | None = None
    position = 0
    while position < len(args):
        if args[position] == flag and position + 1 < len(args):
            found = args[position + 1]
            position += 2
            continue
        rest.append(args[position])
        position += 1
    return found, rest


def _approval(action: str, actor: dict | None) -> None:
    """Only a person answers a waiting demand — a machine is refused by name.

    §4 gives no machine actor `job:approve` or `job:refuse`, for the very reason
    §3 gives for `audit:read`: an `agent` that could release its own waiting
    demand would have opened the door it was held behind, and one that could read
    its own refusals would learn where the wall is. The catalogue names the two
    permissions and a role is what a person writes; what this door adds is the
    one thing a role cannot say — that the word over a demand is a PRESENCE, and
    a machine is exactly the absence of one.

    A folder asking nobody keeps answering as it always did: an act typed at the
    terminal is the owner's (§3), and `None` is the person in front of it.
    """
    if actor is not None and actor.get("type") != "person":
        raise jobs.JobError(
            "error.machine",
            permission=permissions.label(permissions.needed(jobs.JOB, action)),
        )


def _ran(row: dict) -> tuple[int, str]:
    """The job served: the engine performs the act the row holds.

    **The via is `engine` and the actor is the one that OWNS the job**, so its
    ceiling is that actor's — read here and not at the approval, because the
    store is the truth and a role edited under a waiting job is read on the next
    read like any other row. A job whose owner no longer carries what the act
    demands is refused by name, and the refusal is a line — the RUN's line, with
    the via `engine` and the owner as its actor, which is why it is written here
    and not by the door's own handler: the refusal is not the caller's.

    `released=True` is what tells `run` this demand already faced the filter: it
    waited, a person let it through, and holding it again would be asking for the
    same approval forever.

    **The answer is the engine's** — `table.deleted`, `table.edited`, or the
    refusal it raised — because the engine is what validated and wrote, and this
    surface invents no second sentence for either. The row is marked `done` only
    when the act went through: an act the engine refused leaves the job released,
    and the refusal is its own line.
    """
    jobs.released(row)
    owner = jobs.owner(row)
    refused = _ceiling(row)
    if refused is not None:
        _line(
            jobs.JOB, jobs.RUN, owner, audit.ENGINE, audit.REFUSED,
            refused.key, str(refused), threshold=_arrival(),
        )
        return REFUSED, str(refused)
    table, action = jobs.release(row)
    code, answer, _, _, _ = run(
        table,
        action,
        jobs.stored(row),
        actor=owner,
        via=audit.ENGINE,
        released=True,
    )
    if code == OK:
        jobs.done(row)
    return code, answer


def _ceiling(row: dict) -> jobs.JobError | None:
    """The wall the OWNER of a job finds, or `None` — the refusal, ready to say.

    It is read HERE and not at the approval, because the store is the truth: a
    role edited under a waiting job is read on the next read like any other row,
    and a job whose owner no longer carries what the act demands is refused by
    name. It answers with the ERROR and not with a sentence so that the two
    callers — a person's `job run` and the clock's round — write the refusal in
    one wording and leave the one line a wall owes (§3).
    """
    table, action = jobs.release(row)
    needed = permissions.needed(table, action)
    if actors.may(jobs.owner(row) or {}, needed):
        return None
    return jobs.JobError(
        "error.ceiling", id=jobs.shown(row), permission=permissions.label(needed)
    )


# ------------------------------------------------------------------ the clock ---


def tick(now: datetime | None = None) -> list[dict]:
    """One pass of the clock: every job that has come round is rounded (§4, item 24).

    **Two kinds of job come round, and they are not rounded the same way.**

    - a `scheduled` job is the DECLARED one, and its round faces the BAR: the
      clock is AT acting on its own, and §4 is flat — what runs on its own waits
      at the threshold. A round the bar holds does not run: the job becomes
      `waiting`, which is item 15's model and the whole of "no second model" —
      same table, same row, same state. A round that runs leaves the job
      `scheduled` and moves its instant on, so the job lives and rounds again;
    - an `approved` job is one a PERSON released: the demand that waited and was
      answered. It is fired ONCE, by the very road `at-cli job run` walks
      (`_ran`), which is what §4 means by the act belonging to the engine's
      clock — nobody typed it, and nothing else changed.

    `now` is the instant the pass is measured against, and it is handed in by
    whoever keeps the clock (`at.ui.webapp.app`) or by a test; `None` reads the
    machine's hour through `at.core.clock.now`, which is the module's one seam.

    **A folder under the read-only switch applies NOTHING** (§3), and a round is
    a write like any other: the pass answers nothing and leaves the folder
    exactly as it found it.

    The rows it rounded come back, so that a caller can say what happened
    without reading the store back.
    """
    if files.readonly():
        return []
    at = now if now is not None else clock.now()
    rounded: list[dict] = []
    for row in clock.due(jobs.SCHEDULED, at):
        _round(row, at)
        rounded.append(row)
    for row in clock.due(jobs.APPROVED, at):
        _fired(row)
        rounded.append(row)
    return rounded


def _round(row: dict, at: datetime) -> None:
    """One round of a DECLARED job: the bar, the act, and the instant moved on.

    **The bar is faced, and it can hold the round** — the sentence item 24 ends
    on, and where the round that ends waiting for approval becomes a job like
    any other (§4, item 15). It is measured HERE and not by `run`, because the
    job that waits is THIS row: `hold` is the filter's for a demand that never
    became a job, and a schedule that already is one does not need a second row
    to say it waits. A round the bar holds leaves NO line, for the reason §3
    gives — a demand that waits is neither a write nor a refusal.

    **The ceiling is the OWNER's, read again on every round**: a role edited
    under a `scheduled` job is read on the next read like any other row, and a
    job whose owner lost the permission is refused by NAME — with the line a
    wall owes (§3) — and the round ENDS: the job becomes `refused`, the same
    state `disable` leaves, so the clock stops hammering a wall its owner cannot
    clear. Reviving it is a person's declaration, not the clock's.

    **A missed instant is recovered before the round runs, and the line says so.**
    It is the engine's own act — the round AT was not up for — and §3 writes a
    line for every act. The round itself is then the ordinary one: it may run,
    and it may be held by the bar.
    """
    if clock.missed(row, at):
        _line(
            jobs.JOB, clock.RECOVERED, jobs.owner(row), audit.ENGINE, audit.OK,
            None, tr("job.recovered"),
        )
    refused = _ceiling(row)
    if refused is not None:
        _line(
            jobs.JOB, jobs.RUN, jobs.owner(row), audit.ENGINE, audit.REFUSED,
            refused.key, str(refused), threshold=_arrival(),
        )
        jobs.stops(row)
        return
    table, action = jobs.release(row)
    owner = jobs.owner(row)
    try:
        values, _ = _sets(jobs.stored(row))
    except tables.TableError:
        # The arguments a hand edited into something the door cannot read: there
        # is no demand to measure, so the bar is not asked and the round goes
        # straight to `run`, which writes the refusal's line and re-raises it.
        values = None
    if values is not None and holds(
        risk.demand(table, action, values), actor=owner, via=audit.ENGINE
    ):
        jobs.waits(row)
        return
    try:
        run(
            table,
            action,
            jobs.stored(row),
            actor=owner,
            via=audit.ENGINE,
            released=True,
        )
    except (tables.TableError, files.ReadOnly):
        # `run` already wrote the line of the refusal and re-raised it: what the
        # engine refused is the surface's to answer, and this surface is the
        # LOG — the job stays `scheduled` and its instant moves on, so it is
        # tried again on the next pass and not in a loop.
        pass
    jobs.reschedule(row, clock.next_instant(at))


def _fired(row: dict) -> None:
    """The round of a job a PERSON released: `job run`, with nobody typing it.

    It is the very road `at-cli job run` walks, and that is the whole point of
    §4's sentence — the act belongs to the engine's clock, and what a person
    does is release it. A job the engine refuses stays `approved` (that is
    `_ran`'s rule: the refusal is its own line, and leaving the job released is
    what lets it be asked for again once whatever refused the act is dealt
    with), and the clock is the one that asks again — on the next pass.
    """
    _ran(row)
