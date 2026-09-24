"""The interpreter's door — one sentence becomes one proposal, and it runs.

It is **not a surface**: it is what the surfaces that reach the interpreter read.
`ask` is the word the `cli` offers, and the WebApp's box walks the same road —
`nlu.propose` for the reading and the table engine for the writing — with no step
of its own. What a surface decides is only where the words GO: a terminal prints
them, the conversation keeps them. So the words are composed HERE, once, and read
back by both, and a surface that wrote a second sentence would be a second engine.

The engine answers in its OWN words. The proposal is spelled the way the engine
spells its actions, its tables and its values — a closed value in the reader's
language, a day in their own locale — because a proposal is something a person
checks before trusting it. What follows it is the message the engine would have
given the `cli`: `table.created`, `table.edited`, or the refusal it raised.

`run` is the same door for ONE table action, from the words of a surface or from a
proposal: there is one engine, and a second path into it would be a second one.

**The door carries the ceiling, and it is the same one for every surface.** §5 is
explicit — "o que ela pode propor é o que ela já pode fazer" — and the sentence is
about the interpreter, not about the WebApp's route: a surface that demanded the
proposal's permission for itself would be a second ceiling, and the two would
disagree the moment a third surface reached the door. So `ask` takes the ACTOR
that is asking, the proposal answers the action and the table, and what the actor's
role does not carry is refused HERE — before the proposal is shown and before
anything runs. The `balloon`, the `chat` and `at-cli ask` read this one door.

**No actor is no ceiling, and that is not a hole.** The `cli` asks with nobody
proved (there is no entrance in a terminal, and item 10's brief leaves the `cli`'s
ceiling to its own item), and a WebApp in a folder with no credential to prove has
no actor either (§3: "sem nenhuma forma de autenticação configurada, o AT escuta
apenas 127.0.0.1"). Both are the folder that asks nobody, which is exactly where
the routes answer as they always did — and where this door does too.

The sentences about a WORD — the word took no argument, the folder is read-only —
are the `cli` block's, and they are read here rather than copied into a second
home: the same sentence would otherwise live twice, and the two would drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from at import nlu
from at.core import actors, files, permissions, tables, versioning
from at.data import schema
from at.i18n import tr

# The three outcomes of an exit, and the same three the `cli` documents.
OK = 0
REFUSED = 1
USAGE = 2


@dataclass(frozen=True)
class Result:
    """What the door answers, in the engine's words and in no other.

    `kind` is one of three, and the difference between the last two is the whole
    of what a surface has to draw apart:

    - `answer` — the sentence became a proposal, so `proposal` is the proposal and
      `text` is what the engine said about it. The engine may have REFUSED the
      write (`table.error.*`), and that is an answer like any other: the proposal
      was made, and the refusal is the engine's own sentence about it.
    - `question` — the sentence admitted more than one reading, and `text` is the
      question (§9). Nothing was proposed, so nothing was written.
    - `refused` — the sentence was not read at all, and `text` names the reason.
    """

    kind: str
    proposal: str | None
    text: str
    code: int = OK


def ask(
    text: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
    actor: dict | None = None,
) -> Result:
    """One sentence, read and — when it is a write — run.

    A question and a refusal are ANSWERS and not failures: they come back in the
    result, with the words the person reads, and `code` says what a process would
    have exited with. `actor` is the row of whoever is asking, and `None` is the
    folder that asks nobody (`ceiling`).
    """
    try:
        proposed = nlu.propose(text, language=language, now=now)
    except nlu.Refused as refused:
        # The refusal already speaks the active language — the reason's key is
        # i18n's — so it is read as it stands.
        return Result("refused", None, str(refused), REFUSED)
    if isinstance(proposed, nlu.Question):
        # The question carries the phrase it is about, so the surface asks in the
        # active language without knowing which one the phrase was written in.
        return Result("question", None, tr(proposed.key, text=proposed.text), REFUSED)

    # The ceiling, before the proposal is shown and before anything runs: what the
    # actor may propose is what it may already do (§5). A refusal is an ANSWER and
    # not a crash of the request, like every other one this door gives.
    missing = ceiling(actor, proposed)
    if missing is not None:
        return Result(
            "refused",
            None,
            tr("permission.denied", permission=permissions.label(missing)),
            REFUSED,
        )

    written = proposed_text(proposed)
    try:
        code, answer = execute(proposed)
    except tables.TableError as error:
        return Result("answer", written, str(error), REFUSED)
    except files.ReadOnly as error:
        return Result("answer", written, tr("cli.error.read_only", where=error.where), REFUSED)
    return Result("answer", written, answer, code)


def ceiling(actor: dict | None, proposal: nlu.Proposal) -> str | None:
    """The permission this proposal needs that the actor's role does not carry, or
    `None` when the act is the actor's to make (§5).

    It is `actors.may` and no rule of its own: the actor's row points at the role,
    the catalogue says what the role carries, and the permission asked is the one
    the proposal NAMES — `table:action`, the same form the routes demand, because
    the interpreter's proposal is a table action like any other. It returns the
    NAME and not a bool so the refusal can say which permission was missing, in
    the catalogue's own label.

    A sentence the interpreter did not read never gets here — there is no proposal
    to ask about — and neither does a folder asking nobody: no actor is no ceiling,
    and the door keeps answering as it always did.

    The permission is `permissions.needed` and not the action's own name written
    out here: a table may narrow itself (`secret` answers `read` and `edit`), and
    a ceiling that composed the name its own way would refuse an act the role
    carries.
    """
    if actor is None:
        return None
    needed = permissions.needed(proposal.table, proposal.action)
    return None if actors.may(actor, needed) else needed


def proposed_text(proposal: nlu.Proposal) -> str:
    """The proposal, written with the engine's own words.

    The action and the table are named the way the engine names them and every
    value is written the way the listing would write it, because a proposal is
    something a person checks before trusting it.
    """
    fields = ", ".join(
        f"{tables.label(proposal.table, name)} = "
        f"{tables.text_of(proposal.table, name, value)}"
        for name, value in proposal.values.items()
    )
    return tr(
        "nlu.proposal",
        action=tr(f"table.action.{proposal.action}"),
        table=tables.table_name(proposal.table),
        fields=fields or tr("table.word.none"),
    )


def execute(proposal: nlu.Proposal) -> tuple[int, str]:
    """Run the proposal through the table engine, and answer with its words.

    The row a person named is spelled the way `run` already reads one: `list` and
    `view` take it among the arguments, and the rest as the leftover.
    """
    args = [] if proposal.row is None else [str(proposal.row)]
    return run(proposal.table, proposal.action, args, (proposal.values, args))


def run(
    table: str,
    action: str,
    args: list[str],
    given: tuple[dict, list[str]] | None = None,
) -> tuple[int, str]:
    """One table action, from the words of a surface or from a proposal.

    **Every action that changes the folder ends in a version** (§4, item 30),
    and this is where that happens: `run` is the ONE door the `cli`, the WebApp
    and the interpreter reach the engine by, so a commit here covers the three
    surfaces at once and a fourth one gains it by using the same door. The
    version is named by the ANSWER — the engine's own sentence, the very one the
    surface prints — so `git log` reads like the table's own story and no second
    wording of the act is written.

    `given` is the `(values, leftovers)` a proposal already carries — the
    interpreter read them out of the sentence, and only the road by which the
    values arrived differs.

    The ANSWER comes back as text, never printed: where it goes is the surface's,
    and the words are the engine's in both. What the engine refuses — a missing
    required field, a closed row, a read-only folder — is raised as it always was,
    and whoever asked is the one that catches it. A refusal writes nothing, so
    there is nothing to version and nothing is left behind.
    """
    code, answer = _acted(table, action, args, given)
    if code == OK and action in tables.WRITES:
        versioning.commit(answer)
    return code, answer


def _acted(
    table: str,
    action: str,
    args: list[str],
    given: tuple[dict, list[str]] | None = None,
) -> tuple[int, str]:
    """The action itself — what `run` does before it versions the result.

    Private on purpose: `run` is the door, and a caller that reached the engine
    around it would be a second road that versions nothing.
    """
    if action == "list":
        return _listing(table, args)
    if action == "view":
        return _viewing(table, args)
    values, leftovers = given if given is not None else _sets(args)
    if action == "create":
        if leftovers:
            return USAGE, rejected(action)
        row = tables.create(table, values)
        return OK, tr("table.created", id=tables.format_id(table, row["id"]))
    if action == "cancel":
        if len(leftovers) != 1:
            return USAGE, rejected(action)
        # The reason is the argument the CLOSING owns, and it is read outside the
        # field coercion: a table does not have to declare a field for it. When
        # one does declare a field of that name, the field wins — the engine sets
        # it like any other, and the same text answers the closing.
        reason = values.get("reason", "")
        if not schema.field(table, "reason"):
            values.pop("reason", None)
        row = tables.cancel(table, leftovers[0], reason, values)
        return OK, tr("table.cancelled", id=tables.format_id(table, row["id"]))
    if action == "delete":
        if len(leftovers) != 1 or values:
            return USAGE, rejected(action)
        row = tables.delete(table, leftovers[0])
        return OK, tr("table.deleted", id=tables.format_id(table, row["id"]))
    # edit
    if len(leftovers) != 1:
        return USAGE, rejected(action)
    row = tables.edit(table, leftovers[0], values)
    return OK, tr("table.edited", id=tables.format_id(table, row["id"]))


def _listing(table: str, args: list[str]) -> tuple[int, str]:
    show_all = "--all" in args
    if [arg for arg in args if arg != "--all"]:
        return USAGE, rejected("list")
    rows = tables.rows(table, show_all=show_all)
    if not rows:
        return OK, tr("table.word.empty")
    return OK, rendered(table, rows)


def _viewing(table: str, args: list[str]) -> tuple[int, str]:
    if len(args) != 1:
        return USAGE, rejected("view")
    row = tables.find(table, args[0])
    lines = [f"{tr('table.field.id')}: {tables.format_id(table, row['id'])}"]
    for name in (schema.of(table) or {}).get("fields", {}):
        if name == "id":
            continue
        lines.append(f"{tables.label(table, name)}: {tables.text_of(table, name, row.get(name))}")
    return OK, "\n".join(lines)


def rendered(table: str, rows: list[dict]) -> str:
    """The listing: the id, then the columns the table declares.

    The widths are measured from what is about to be printed, so a column is as
    wide as its widest cell — the alternative, a fixed width, is a table that
    breaks the first time a title is long.
    """
    header = [tr("table.field.id")] + [tables.label(table, name) for name in tables.columns(table)]
    cells = [
        [tables.format_id(table, row["id"])]
        + [tables.text_of(table, name, row.get(name)) for name in tables.columns(table)]
        for row in rows
    ]
    widths = [max(len(line) for line in column) for column in zip(header, *cells)]
    line = lambda row: "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
    return "\n".join([line(header), *[line(cell) for cell in cells]])


def _sets(args: list[str]) -> tuple[dict[str, str], list[str]]:
    """`--set field=value` pairs, and whatever was left that was not one."""
    values: dict[str, str] = {}
    leftovers: list[str] = []
    position = 0
    while position < len(args):
        if args[position] != "--set":
            leftovers.append(args[position])
            position += 1
            continue
        if position + 1 >= len(args) or "=" not in args[position + 1]:
            raise tables.TableError("error.set_needs_value")
        name, value = args[position + 1].split("=", 1)
        values[name.strip()] = value
        position += 2
    return values, leftovers


def rejected(word: str) -> str:
    """The sentence a surface reads when a word was given the wrong arguments."""
    return tr("cli.error.rejected_arguments", word=word)
