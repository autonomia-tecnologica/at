"""`run` — the one road a table action takes to the engine, with its line and version.
"""

from __future__ import annotations

from at import nlu
from at.core import (
    audit,
    files,
    jobs,
    risk,
    tables,
)
from at.data import schema
from at.i18n import tr
from at.ui.ask_backup import _backed
from at.ui.ask_base import OK, USAGE, _sets, rejected
from at.ui.ask_listing import _listing, _viewing
from at.ui.ask_risk import _arrival, _line, holds


def execute(
    proposal: nlu.Proposal, *, actor: dict | None = None
) -> tuple[int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """Run the proposal through the table engine, and answer with its words.

    The row a person named is spelled the way `run` already reads one: `list` and
    `view` take it among the arguments, and the rest as the leftover. The VIA is
    the interpreter's and not the surface's: the box in the WebApp and the word
    in the terminal reach the same answering layer, and §4 named the road `nlu`.
    """
    args = [] if proposal.row is None else [str(proposal.row)]
    return run(
        proposal.table,
        proposal.action,
        args,
        (proposal.values, args),
        ranges=proposal.ranges,
        actor=actor,
        via=audit.NLU,
        full_table=proposal.full_table,
    )


def run(
    table: str,
    action: str,
    args: list[str],
    given: tuple[dict, list[str]] | None = None,
    ranges: dict[str, str] | None = None,
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
    released: bool = False,
    full_table: bool = True,
) -> tuple[int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """One table action, from the words of a surface or from a proposal.

    **Every action that changes the folder ends in a version** (§4, item 30), and
    **every write act — and every refusal — leaves exactly one line** (§3, item
    15). This is where both happen: `run` is the ONE door the `cli`, the WebApp
    and the interpreter reach the engine by, so a commit and a line here cover
    the three surfaces at once and a fourth one gains them by using the same
    door. The version is named by the ANSWER — the engine's own sentence, the
    very one the surface prints — so `git log` reads like the table's own story
    and no second wording of the act is written.

    **A refusal takes the same road**: it is recorded, versioned, and then
    RE-RAISED, because what the engine refused is the surface's to answer (the
    `cli` prints it, the page draws it) and the log's to keep. The reason stored
    is the refusal's own `i18n` KEY, never its words and never the value that
    caused it (§3).

    `given` is the `(values, leftovers)` a proposal already carries — the
    interpreter read them out of the sentence, and only the road by which the
    values arrived differs.

    **A demand at or above the bar and with nobody present does not run**: it
    becomes a row of `jobs`, in the state that says it waits, and the answer
    names it. The measurement is `risk.demand` (the action and the arguments it
    carries) read HERE, at the door, and the presence is `holds` — the core
    measures, the door knows who is asking.

    The ANSWER comes back as text, never printed: where it goes is the surface's,
    and the words are the engine's in both. The ROW comes back beside it because
    the page's route answers with the RECORD it just wrote — a read, and a word
    the arguments were rejected for, answer `None`.

    `released` says this demand has ALREADY faced the filter: a job that runs
    walks this door with it (`job`, below), and the filter does not hold a
    demand that waited and was approved a second time.
    """
    # The bar, read before anything runs: it is what this demand is measured
    # against, and the line it may leave carries it (§4, item 15).
    bar = _arrival()
    if action in tables.WRITES and not released:
        try:
            values, leftovers = given if given is not None else _sets(args)
        except tables.TableError as error:
            # The word was given arguments it cannot read, so nothing ran and the
            # attempt is a line — the same one the engine's own refusal would
            # leave, written here because the parsing happens before it.
            _line(
                table, action, actor, via, audit.REFUSED,
                f"table.{error.key}", str(error), threshold=bar,
            )
            raise
        measured = risk.demand(table, action, values)
        if holds(measured, actor=actor, via=via):
            held = jobs.hold(table, action, leftovers, values, actor=actor)
            return OK, tr("job.waits", id=tables.format_id(jobs.JOB, held["id"])), None, None, None
    try:
        code, answer, row, table_rows, bullets = _acted(table, action, args, given, ranges, full_table)
    except tables.TableError as error:
        _line(
            table, action, actor, via, audit.REFUSED,
            f"table.{error.key}", str(error), threshold=bar,
        )
        raise
    except files.ReadOnly as error:
        _line(
            table, action, actor, via, audit.REFUSED, "cli.error.read_only",
            tr("cli.error.read_only", where=error.where), threshold=bar,
        )
        raise
    if action in tables.WRITES:
        if code == OK:
            _line(table, action, actor, via, audit.OK, None, answer, threshold=bar)
        else:
            # The word was given the wrong arguments: it never reached the
            # engine, and the attempt is a line like any other (§3).
            _line(
                table, action, actor, via, audit.REFUSED,
                "cli.error.rejected_arguments", answer, threshold=bar,
            )
    return code, answer, row, table_rows, bullets


def _acted(
    table: str,
    action: str,
    args: list[str],
    given: tuple[dict, list[str]] | None = None,
    ranges: dict[str, str] | None = None,
    full_table: bool = True,
) -> tuple[int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """The action itself — what `run` does before it records and versions.

    Private on purpose: `run` is the door, and a caller that reached the engine
    around it would be a second road that leaves no line and no version. The
    third element is the ROW the act wrote, which the page's route answers with;
    a read, and a word whose arguments were rejected, answer `None`. The fourth
    and fifth are a `list`'s own two shapes — the grid (header and cells) and
    the one-line-per-row bullets — a surface that draws either reads it instead
    of parsing the second element's ASCII back apart; every other action
    answers `None` for both, and a `list` only ever fills ONE of the two.
    """
    if table == "backup":
        # The one OBJECT the engine dispatches that is not a table (§5): `make`
        # and `restore` cipher or lay down the whole folder, and `tables.edit`
        # — the branch a `backup:make` would otherwise fall into — has no such
        # table to touch. `_backed` is the round; it is reached by the door the
        # same way, so a scheduled `backup:make` runs with no second road.
        return _backed(action)
    if action == "list":
        values = given[0] if given is not None else {}
        code, answer, table_rows, bullets = _listing(table, args, values, ranges or {}, full_table)
        return code, answer, None, table_rows, bullets
    if action == "view":
        # THE ROW TRAVELS BACK for a `view` (20/10/2026): the card a
        # conversation draws is the very record the `cli` prints, and the
        # second element is still the engine's own listing of it, unchanged.
        code, answer, found = _viewing(table, args)
        if code != OK:
            return code, answer, None, None, None
        return code, answer, found, None, None
    values, leftovers = given if given is not None else _sets(args)
    return _written(table, action, values, leftovers)


def _written(
    table: str, action: str, values: dict, leftovers: list[str]
) -> tuple[int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """The four writes of the engine's six — `create`, `cancel`, `delete`, `edit` —
    each with the arguments it takes, or the word rejected."""
    if action == "create":
        if leftovers:
            return USAGE, rejected(action), None, None, None
        row = tables.create(table, values)
        return OK, tr("table.created", id=tables.format_id(table, row["id"])), row, None, None
    if action == "cancel":
        if len(leftovers) != 1:
            return USAGE, rejected(action), None, None, None
        # The reason is the argument the CLOSING owns, and it is read outside the
        # field coercion: a table does not have to declare a field for it. When
        # one does declare a field of that name, the field wins — the engine sets
        # it like any other, and the same text answers the closing.
        reason = values.get("reason", "")
        if not schema.field(table, "reason"):
            values.pop("reason", None)
        row = tables.cancel(table, leftovers[0], reason, values)
        return OK, tr("table.cancelled", id=tables.format_id(table, row["id"])), row, None, None
    if action == "delete":
        if len(leftovers) != 1 or values:
            return USAGE, rejected(action), None, None, None
        row = tables.delete(table, leftovers[0])
        return OK, tr("table.deleted", id=tables.format_id(table, row["id"])), row, None, None
    # edit
    if len(leftovers) != 1:
        return USAGE, rejected(action), None, None, None
    row = tables.edit(table, leftovers[0], values)
    return OK, tr("table.edited", id=tables.format_id(table, row["id"])), row, None, None
