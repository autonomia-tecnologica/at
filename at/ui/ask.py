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

**It is also where the LINE is born, and that is the same argument one floor
down.** §3 makes every action that enters the core one line of the `audit`, and
the one who knows the ACTOR and the VIA is a door — so `run` takes both, records
the act or the refusal it raised, and versions it (§4, item 30, which took this
very road for this very reason). The writes the engine makes on AT's own behalf —
the migrations, the engine's row, a credential — do not pass here and do not
leave a line: they have no actor and no via to name, and `at/core/audit.py` says
what that costs. The page's table route walks this door too, so the `cli`, the
interpreter and the WebApp all leave the same kind of trail.

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

**The settings are the second door of this module, and for the same reason.** §4
makes them reachable through the core API, and the one who knows the actor and
the via is a door — so `setting` is here, beside `run`, and not inside
`core.settings`: what that module owns is the FILE (which keys exist, what a
value is, what a write refuses), and what this one owns is the ACT (who did it,
by which road, and the line it owes). A read leaves nothing; an edit is a write
like any other, and it is one line and one version.

**Here is also where a demand WAITS, and it could be nowhere else.** The core
measures the risk (`risk.demand`) — whoever asks does not assess their own — but
the other half of the filter is a fact about presence, and presence is the
actor and the via, which only a door has. So `holds` is the comparison, and it
is made at the door, before the engine sees the act: the demand at or above the
bar becomes a row of `jobs` and the answer names it.

**And the job's own acts are the third door.** They are not the engine's six, so
they do not walk `run`: `job` is here, beside `setting`, and what it owns is the
approval as a LINE — the person's word over the demand, separate from the job
that waited — and the run, which is the engine performing the act with the via
`engine` and the actor that owns the job.

**And `scan` is the fourth, and the one that OWES nothing.** `secret scan` is
also an act the engine does not have — it reads the folder and rewrites no row —
so it does not walk `run` either. What makes it the odd one of the four is that
it is a read, and §3 makes reading not doing: no line is written, nothing is
versioned, and there is no actor nor via to name. What the door still owns is the
sentence, which is what keeps the `cli` and a page after it reading one wording.

**And the clock is the fifth — one pass of the engine without anybody there.**
`tick` rounds the jobs that have come round (§4, item 24), and it is a door and
not a rule for the reason the four above are: what a round performs is an ACT —
with the via `engine` and the actor that owns the job, so its ceiling is that
actor's, leaving the line §3 asks of every act and the version item 30 asks of
every write. `at.core.clock` says who is due and when the next instant is; this
is where the act happens. The process that keeps waking it is the WebApp's
(`at.ui.webapp.app`), and the clock leaves it the day the engine does.

**And `remind` is the sixth, and it owes no line either.** A reminder that
comes round is not an act the engine performs — there is no row to write and
nothing to refuse — it is a push that may or may not reach a phone, so what
this door owns is the SENDING and the one field the round keeps to itself
(`reminder.notified`), not a line in the `audit` (§3: that trail is for what
the engine did, and a push is not that). It shares the WebApp's process with
`tick` and the same reason for being there: the derived key it publishes with
lives only in that process's memory (§4, item 50).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from at import i18n, nlu
from at.nlu import matcher
from at.core import (
    actors,
    assist,
    audit,
    backup,
    clock,
    files,
    hooks,
    jev,
    jobs,
    notifier,
    permissions,
    projects,
    reminder,
    risk,
    scanner,
    secrets,
    settings,
    tables,
    versioning,
)
from at.data import schema
from at.i18n import tr
from at.services import gitleaks
from at.ui import words

# The two tables the tree is read off, named once: the `--project` filter and
# the slices of an item are about the pair, and a string typed twice is the one
# that drifts from the declaration.
PROJECT = projects.PROJECT
TASK = projects.TASK

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

    A fourth, `intent`, is the assist reading the sentence as CONVERSATION (a
    greeting, thanks, a request for help): nothing was proposed or written, and
    `text` is what is said back — a line of the chat, not an error.
    """

    kind: str
    proposal: str | None
    text: str
    code: int = OK
    # Whether the assist could still answer THIS sentence if a Main Key
    # arrived with it: `True` for any `refused` with the switch on and no key
    # already tried — o Jev lê TODA frase (a leitura primária), então QUALQUER
    # recusa sem chave pode virar resposta com uma. A surface reads this to
    # offer the retry.
    assist: bool = False
    # The REWRITTEN sentence a "Confirmar" would resubmit — the one Jev's own
    # `CONFIRM` tier asks the person to repeat (TASK-183) — or `None` for every
    # other `question`: the ordinary ambiguity `nlu`'s own grammar raises
    # (`ask.which_hour`, `ask.which_field`) names the SAME phrase that was
    # already refused, and resubmitting it verbatim would only ask the same
    # question again. A surface tells the two apart by this field alone, never
    # by the question's `key`, which is this module's to read and not the
    # page's to compare against.
    confirm: str | None = None
    # A `list`'s own header and cells, when the proposal was one and it found
    # rows — `None` for every other action, and for a `list` that found none.
    # A surface that draws an actual table reads this; one that only prints
    # reads `text`, which carries the same rows as the `cli`'s own ASCII.
    table: tuple[list[str], list[list[str]]] | None = None
    # A `list`'s own bullets — one line per row, its TITLE and nothing else —
    # when the sentence did NOT say "tabela"/"table" (the person's own default,
    # 03/10/2026). Mutually exclusive with `table`: a `list` fills exactly one
    # of the two, never both and never neither when it found rows.
    bullets: list[str] | None = None
    # The ACTION a bare verb named with nothing to act on — "listar", alone —
    # so a surface can complete it from whatever is typed NEXT, the way a
    # person finishing their own sentence a beat late still gets read
    # (`nlu.error.no_table_bare`, `lib/chat.ts`). `None` for every other
    # refusal and for every answer and question.
    awaiting: str | None = None
    # THE RECORD an action about ONE row left behind — `create`, `edit`,
    # `cancel`, `delete` and `view` — as a CARD a surface draws (the person's
    # own ask, 20/10/2026: "mostra o objeto inteiro"). `None` for `list` (its
    # own `table`/`bullets` are the shape), for a `backup`, for a demand that
    # WAITED, and for a sentence that answered nothing but a refusal.
    #
    # The card is the ONE the record's page already draws (`record`, `app.py`),
    # and it is built HERE because the door is where the row is; the page
    # composes no card of its own (§3). Only the fields the table declares as
    # its `columns` travel — the same ones a listing shows, the person's rule
    # ("os campos principais da tabela, definido no schema") — so the card is
    # as wide as the table says and never as wide as the row.
    record: dict | None = None
    # THE SENTENCE THE CONVERSATION ADDS AROUND THE CARD — "Pronto, criei
    # TASK-2:" — composed HERE, for the reason the whole module exists: the
    # words are composed once, and what a surface decides is only where they
    # GO. `text` is still the engine's own answer (the fact, the line the
    # version carries); this is what a conversation says about it, and a
    # surface that is not a conversation never draws it.
    #
    # `None` for everything the card does not answer — a `list`, a `backup`, a
    # question, a refusal — and for a demand that waited: there is no row to
    # show, so there is no sentence to lead into it.
    lead: str | None = None
    # O desfecho `intent` (conversa: saudação, agradecimento, ajuda…): `text` é a
    # fala já resolvida no idioma ativo, e estes dois dizem QUAL intenção e
    # subintenção a produziram. `None` em todo outro desfecho.
    intent: str | None = None
    subintent: str | None = None


def ask(
    text: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
    actor: dict | None = None,
    main_key: str | None = None,
    confirmed: bool = False,
) -> Result:
    """One sentence, read and — when it is a write — run.

    A question and a refusal are ANSWERS and not failures: they come back in the
    result, with the words the person reads, and `code` says what a process would
    have exited with. `actor` is the row of whoever is asking, and `None` is the
    folder that asks nobody (`ceiling`).

    `main_key` is handed straight to `nlu.propose`, which hands it to the
    assist (TASK-180, fatia 3/3) — this door opens no credential itself, the
    same reason `at.core.assist` gives for reading it as an argument rather
    than asking where it came from. A caller with no key to hand in passes
    `None`, which is the whole of what `cli`'s `ask` word and a WebApp request
    with nothing typed already do.
    """
    try:
        proposed = nlu.propose(text, language=language, now=now, main_key=main_key,
                               confirmed=confirmed)
    except nlu.Refused as refused:
        # The refusal already speaks the active language — the reason's key is
        # i18n's — so it is read as it stands.
        #
        # O assist poderia ter uma resposta para ESTA frase — ele é a leitura
        # PRIMÁRIA agora, e só não foi consultado porque esta chamada não
        # trouxe uma Chave Principal para abrir a credencial. `hinted` é esse
        # fato e nada mais: uma superfície o lê para oferecer o retry, ou não.
        hinted = assist.enabled() and main_key is None
        # A BARE VERB carries the action it named forward — the one thing a
        # surface needs to complete it from whatever arrives next, the way
        # `lib/chat.ts` reads "sim"/"não" against an open CONFIRM question.
        awaiting = refused.kw.get("canonical") if refused.key == "nlu.error.no_table_bare" else None
        return Result("refused", None, str(refused), REFUSED, assist=hinted, awaiting=awaiting)
    if isinstance(proposed, nlu.Intent):
        return Result("intent", None, tr(proposed.key), OK,
                      intent=proposed.intent, subintent=proposed.subintent)
    if isinstance(proposed, nlu.Question):
        # The question carries the phrase it is about, so the surface asks in the
        # active language without knowing which one the phrase was written in.
        #
        # The assist's OWN question (`assist.ASK_KEY`) is the one a "Confirmar"
        # may resubmit as it stands — `_rewrite` already planted the guessed
        # action and table in it, so repeating it walks straight into `match`
        # (TASK-183). Every other question is the grammar's own ambiguity, about
        # the SAME phrase that was already refused, and `confirm` stays `None`
        # for it: a button that resubmitted it would only ask the same question
        # back.
        confirmable = proposed.text if proposed.key == assist.ASK_KEY else None
        return Result(
            "question", None, tr(proposed.key, text=proposed.text), REFUSED,
            confirm=confirmable,
        )

    # The ceiling, before the proposal is shown and before anything runs: what the
    # actor may propose is what it may already do (§5). A refusal is an ANSWER and
    # not a crash of the request, like every other one this door gives.
    missing = ceiling(actor, proposed)
    if missing is not None:
        saying = tr("permission.denied", permission=permissions.label(missing))
        # A wall an actor found is a line (§3): it is the one the sight of a
        # machine's own refusal would teach where the wall is, which is why only
        # the admin carries `audit:read`.
        denied(
            proposed.table,
            proposed.action,
            actor=actor,
            via=audit.NLU,
            reason=audit.DENIED,
            saying=saying,
        )
        return Result("refused", None, saying, REFUSED)

    written = proposed_text(proposed)
    try:
        code, answer, row, table_rows, bullets = execute(proposed, actor=actor)
    except tables.TableError as error:
        return Result("answer", written, str(error), REFUSED)
    except files.ReadOnly as error:
        return Result("answer", written, tr("cli.error.read_only", where=error.where), REFUSED)
    # THE CARD of the row the act touched — one row's own action, and only
    # it: a `list` answers its own shape (above), and a demand that WAITED
    # answered `None` from `run` (nothing was written to show).
    shown = card(proposed.table, row) if row is not None else None
    lead = _lead(proposed, shown, table_rows, bullets, answer)
    return Result(
        "answer", written, answer, code,
        table=table_rows, bullets=bullets,
        record=shown,
        # THE LEAD names the row by the engine's OWN id (`shown_id`) and never
        # by its title: a title is prose, and prose belongs to the person the
        # row is about — the card under it carries the whole of what the row
        # says, and a sentence that repeated it would be a second telling.
        lead=lead,
        intent=jev.ACT, subintent=f"{proposed.table}.{proposed.action}",
    )


def say(table: str, action: str, **kw: object) -> str:
    """A fala humana de `objeto.ação` — a intenção `act` (`intent.act.<tabela>.<ação>`),
    e, quando a combinação não tem mensagem própria, a da AÇÃO (`intent.act.<ação>`).
    Uma mensagem por chave: o i18n não tem variantes."""
    key = f"intent.act.{table}.{action}"
    if tr(key) == key:
        key = f"intent.act.{action}"
    return tr(key, **kw)


def _lead(proposed: nlu.Proposal, shown: dict | None, table_rows, bullets, answer: str) -> str | None:
    """A frase que a conversa diz ANTES do cartão ou da listagem.

    Cartão: nomeia a linha pelo id do motor (`shown_id`), nunca pelo título. Lista
    com linhas: a fala da lista. Lista vazia SEM filtro: a fala de vazio. Lista
    vazia COM filtro (ou num dia): `None` — o texto do motor já diz o filtro, e uma
    frase genérica por cima o repetiria. Qualquer outra coisa: `None`."""
    if shown:
        return say(proposed.table, proposed.action, id=shown["shown_id"])
    if proposed.action != "list":
        return None
    if table_rows is not None or bullets is not None:
        return say(proposed.table, "list")
    if answer == tr("table.word.empty"):
        return say(proposed.table, "list.empty")
    return None


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


def _sign(op: str) -> str:
    """A operação como um SINAL, para a proposta: `até` é `≤`, `desde` é `≥`, e
    o valor exato é `=`. É o que a pessoa lê para saber se o filtro é um ponto ou
    um intervalo."""
    return {"<=": "≤", ">=": "≥", "<": "<", ">": ">"}.get(op, "=")


def proposed_text(proposal: nlu.Proposal) -> str:
    """The proposal, written with the engine's own words.

    The action and the table are named the way the engine names them and every
    value is written the way the listing would write it, because a proposal is
    something a person checks before trusting it.

    **A `list`'s own residue is left out** — `_kept` never filters by the
    primary field either (its own docstring: "listar tarefas comprar pão" is
    not "the tasks whose text is exactly comprar pão"), and a proposal that
    showed it as `Texto = comprar pão` would be claiming a filter that never
    runs. `create`/`edit` keep it: there the primary IS the value being
    written, not residue a list could not place anywhere else.
    """
    primary = schema.primary(proposal.table) if proposal.action == "list" else None
    fields = ", ".join(
        f"{tables.label(proposal.table, name)} "
        f"{_sign(proposal.ranges.get(name, '='))} "
        f"{tables.text_of(proposal.table, name, value)}"
        for name, value in proposal.values.items()
        if name != primary
    )
    return tr(
        "nlu.proposal",
        action=tr(f"table.action.{proposal.action}"),
        table=tables.table_name(proposal.table),
        fields=fields or tr("table.word.none"),
    )


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


def holds(measured: float, *, actor: dict | None, via: str) -> bool:
    """Whether this demand WAITS for a person: at or above the bar, and nobody
    present to answer (§4, item 15).

    **Who waits is about presence, not about type.** An act a person types or
    clicks never waits: the act IS the approval, and asking again would be
    theatre. An act that runs on its own waits at or above the threshold,
    because the one who cannot ask is the one who waits — and the two marks of
    that absence are the via `engine`, which is AT acting by itself, and an
    actor that is a MACHINE, which is what the `agent` of §4 is.

    **A folder asking nobody is a person at the terminal**, so `None` waits for
    nothing: §3's loopback with no credential is a person in front of the
    machine, and the `cli` is local by construction — the same reading that
    gives an act typed there the first admin as its actor.

    It reads `risk.waits` for the number and nothing of its own: the boundary is
    §4's (at or above it waits), the boundary the ruler draws on the page, and a
    second comparison here would be the one that drifts.
    """
    return risk.waits(measured) and not present(actor, via)


def present(actor: dict | None, via: str) -> bool:
    """Whether a PERSON is present in this act — whoever can answer it.

    The engine's via is AT acting on its own, and an actor whose `type` is not
    `person` is the machine of §4: neither is somebody who can be asked, and
    both are therefore what the filter holds. A row a hand edited to a type
    nobody declares is read as a machine for the same reason every strange
    declaration fails closed — the absence of a person is what waits, and only
    the word `person` says one is there.
    """
    if via == audit.ENGINE:
        return False
    return actor is None or actor.get("type") == "person"


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


def denied(
    table: str,
    action: str,
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
    reason: str,
    saying: str,
) -> None:
    """A refusal the CEILING made, recorded — the line a wall owes (§3).

    It is called where an act is refused BEFORE the engine sees it — the
    interpreter's ceiling, and the page's route — because the engine's own
    refusals are recorded by `run`, which is where they are raised. `saying` is
    the sentence the surface printed, so the version the line ends in is named by
    the words the person read.
    """
    _line(table, action, actor, via, audit.REFUSED, reason, saying)


def _line(
    table: str,
    action: str,
    actor: dict | None,
    via: str,
    status: str,
    reason: str | None,
    saying: str,
    *,
    threshold: float | None = None,
) -> None:
    """The line, and the version it ends in — the two halves of one write.

    They belong together because a line nothing versions is a folder left dirty
    (§4, item 30), and the version is named by the sentence the surface printed:
    one wording for the person, the log and `git log`.

    `threshold` is the bar the demand faced, read when it ARRIVED (`_arrival`),
    and handed in because one demand moves it: `setting:edit` on
    `risk_threshold` changes the number the line is about.
    """
    audit.log(
        table, action, actor=actor, via=via, status=status, reason=reason,
        threshold=threshold,
    )
    versioning.commit(saying)


def _arrival() -> float:
    """The bar in force when the demand arrived — the one it is measured against.

    Read once, at the door, before anything runs: it is the core that measures a
    demand and never whoever asks (§4), and a bar read after the act would be the
    bar the act left behind instead of the one that governed it.
    """
    return risk.threshold()


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
    wall owes (§3) — and its instant still moves on, so the round comes back
    once the role does instead of hammering in a loop.

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
        jobs.reschedule(row, clock.next_instant(at))
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


# --------------------------------------------------------------- the backup ---


def backup_message(action: str, outcome: backup.Report, target: str) -> str:
    """The sentence one act of `backup` ends in — the ONE home of the wording,
    read by the `cli`'s terminal line and by the push the clock sends when the
    automatic copy did not go out.

    It lived in `at.ui.cli` while the terminal was its only reader; the clock's
    round is the second, and a second sentence for the same fact would be the
    two that drift. `core.backup` answers in facts (a state, a tool) and never
    in words, which is why the composition is here and not there.
    """
    if action == backup.MAKE:
        if outcome.state == backup.MADE:
            return tr("backup.make.done", destination=target)
        if outcome.state == backup.BLOCKED:
            return tr("backup.make.blocked")
        if outcome.state == backup.NO_TOOL:
            return tr("backup.make.no_tool", tool=outcome.tool)
        return tr("backup.make.failed", tool=outcome.tool, destination=target)
    if outcome.state == backup.RESTORED:
        return tr("backup.restore.done")
    if outcome.state == backup.NOT_FOUND:
        return tr("backup.restore.not_found", where=target)
    if outcome.state == backup.NOT_FRESH:
        return tr("backup.restore.not_fresh")
    return tr("backup.restore.wrong_key")


def _main_key() -> str | None:
    """The Main Key in memory this boot, or `None` (§4, item 50) — the natural
    candidate for the phrase nobody types.

    It is read off the HOSTED path's in-memory copy (`at.ui.webapp.keys`), and
    the container path never has it: there it answers `None`, and the round says
    the truth instead of pretending it copied. The import is LAZY — the same
    door `versioning.ways_out` takes to avoid a cycle: the key is only asked for
    when the round is genuinely about to copy. A test injects it the way it
    injects the notifier's: `at.ui.webapp.keys.keep_main_key`.
    """
    from at.ui.webapp import keys  # noqa: PLC0415 — a mesma porta de `ways_out`

    return keys.main_key()


def _backed(action: str) -> tuple[
    int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None
]:
    """One round of the BACKUP's declared job — the act `backup:make` that runs
    on its own (§4, item 24; TASK-133).

    **The cadence is the backup's own, and it is read before anything else.** The
    clock brings this round every minute; the copy only leaves when the interval
    the folder chose has passed since the last attempt (`backup.due`). A round
    that is not due does nothing, leaves no stamp and says nothing — it asks
    again on the next pass. With no destination declared there is nowhere to
    copy to, and the round is that same silence: an unconfigured backup is not
    an event, and the moment the person declares a destination it starts working.

    **The phrase comes from the Main Key, and the round never fakes it.** A boot
    with no Key in memory — the container path, a host that never brought one —
    does not copy: it marks the attempt and sends ONE notice that the copy did
    not go out, so the person learns it from the phone rather than from a folder
    that quietly stopped protecting itself. The mark is what keeps the notice to
    once per interval instead of every minute. The same one-notice-per-interval
    is what a copy the scan blocked or the tool refused gets.

    **`restore` is never scheduled.** It lays the archive over the current
    folder, and an act shaped like a wipe fired with nobody asking is the loss
    the backup exists to prevent — refused by name, like any act this door does
    not answer.

    The answer is the engine's in both surfaces: what the terminal would print is
    what the notice carries, because both read `backup_message`.
    """
    if action != backup.MAKE:
        return USAGE, rejected(action), None, None, None
    at = clock.now()
    target = backup.destination()
    if not target or not backup.due(at):
        return OK, tr("backup.make.auto.waited"), None, None, None
    key = _main_key()
    if key is None:
        notice = tr("backup.make.no_key")
        notifier.publish(notifier.TITLE, notice)
        backup.attempted(at)
        return OK, notice, None, None, None
    try:
        report = backup.make(lambda: key, target)
    except (secrets.SecretsError, OSError) as error:
        # A Key too short to derive from, a destination the filesystem refused:
        # the round answers it the way the `cli` does — one sentence, no crash —
        # and the notice carries the same words the terminal would.
        notice = tr("backup.make.notice", reason=str(error))
        notifier.publish(notifier.TITLE, notice)
        backup.attempted(at)
        return OK, notice, None, None, None
    if report.state == backup.MADE:
        backup.attempted(at)
        return OK, backup_message(action, report, target), None, None, None
    notice = tr("backup.make.notice", reason=backup_message(action, report, target))
    notifier.publish(notifier.TITLE, notice)
    backup.attempted(at)
    return OK, notice, None, None, None


# --------------------------------------------------------- the reminder's push ---


def remind(
    now: datetime | None = None,
    key: bytes | None = None,
    send: Callable[[str, str, bytes | None], tuple[bool, str]] | None = None,
) -> list[dict]:
    """One round of the clock's OTHER schedule: the reminders THIS PASS is about
    (§4, item 29's second slice — TASK-145).

    **Two schedules share one clock, and they are not the same shape.** A job's
    round faces the bar and moves an instant on at the MINUTE's grain (`tick`);
    a reminder names the HOURS of its day (`at`: `["09:00", "18:00"]` — the
    water six times, the medicine at its two doses) and its grain is the
    (day, HOUR). `reminder.occurs` says the DAY, `reminder.hours` says the
    hours, and this round fires an hour when its pass COVERS it (`_covers`: the
    marked minute and the cadence after it). An hour the round was not up for is
    not owed — a server that was down at 11:00 does not fire the 11:00 at noon.

    **What keeps an hour from pushing on every pass that covers it is
    `reminder.notified`, asked before a send and written only after one that
    WENT OUT (`mark_notified`, per (day, hour)): a push that failed is retried
    on the next pass that covers the hour, the same "not in a loop, but not
    given up on either" the round's own bookkeeping already gives a job that a
    wall or a network refused. The guard is per HOUR and not per day: the 09:00
    of a six-times-a-day reminder must not cover its 11:00.

    **`due` wins the hour's push, `warn` gets its own text.** The two lists
    `reminder.due` answers never share a row for the same occurrence (that
    module's own rule), so a row read here is asked for exactly one of the two
    sentences below.

    `now` is the instant this pass reads (`datetime.now` when `None`) — the day
    AND the hour come off it, which is why the round can no longer be handed a
    bare calendar — `key` is the derived key this boot holds for the notifier's
    scope (`None` is a boot with nothing to open the credential with, and
    `notifier.publish` answers `no_token` for it rather than sending an envelope
    nobody could read on the other end), and `send` is the seam a test drives
    instead of reaching the network (`notifier.publish` when `None`).

    The rows this pass actually pushed for come back, the way `tick`'s rounded
    rows do, so a caller can say what happened without reading the store back.
    """
    if files.readonly():
        return []
    moment = now if now is not None else datetime.now()
    today = moment.date()
    push = send if send is not None else notifier.publish
    found = reminder.due(today)
    fired: list[dict] = []
    for rows, said in (
        (found["due"], "reminder.push.due"),
        (found["warn"], "reminder.push.warn"),
    ):
        for row in rows:
            for hour in reminder.hours(row):
                if not _covers(hour, moment) or reminder.notified(row, today, hour):
                    continue
                ok, _ = push(notifier.TITLE, tr(said, text=row.get("text", "")), key)
                if ok:
                    reminder.mark_notified(row, today, hour)
                    if row not in fired:
                        fired.append(row)
    return fired


def _covers(hour: str, moment: datetime) -> bool:
    """Whether THIS pass covers `hour` (`HH:MM`) — the marked minute and the
    clock's cadence after it, and no later.

    É o que faz "toca às 09:00" valer sem tocar o dia inteiro na primeira
    passada, e o que faz uma hora que passou com o servidor fora simplesmente
    não ser devida: a passada de meio-dia não cobre as onze.
    """
    start = int(hour[:2]) * 60 + int(hour[3:])
    current = moment.hour * 60 + moment.minute
    return start <= current < start + int(clock.CADENCE.total_seconds() // 60)


# -------------------------------------------------------------- the scan ---


def scan(args: list[str]) -> tuple[int, str]:
    """`secret scan` — the folder says what it carries that it should not (item 51).

    **The act is the table's own, and it does not walk `run`.** `scan` is not one
    of the engine's six: it reads the folder and rewrites no row of any table, so
    it is no `create`, no `edit` and no `cancel`, and the engine has nothing to
    do for it. What this door owns is the WORDS — the scanner answers in facts (a
    state, the tool, the findings) and what a person reads is composed here, so
    the `cli`, and any surface that comes after it, read one sentence.

    **A read leaves nothing of the person's (§3).** There is no actor and no via
    in the signature because there is no line to write and nothing to version:
    the scan changes nothing of the folder it reads, which is exactly what makes
    it a read. The one thing it can write is AT's own — `App/services/gitleaks/`, where
    the scanner the artifact carries is unpacked the first time it is asked for
    (`scanner.found`) — and that is AT's tool in AT's folder, the same sense
    `App/services/caddy/` is. What it also does not do is decide anything about the
    ceiling: the catalogue names `secret:scan` and the role that carries it, and a
    surface that has to refuse without it — the page's routes — writes that line
    itself, the way every other route does.
    """
    if args:
        return USAGE, rejected(permissions.SCAN)
    answer = scanner.scan()
    if answer.state == scanner.NO_TOOL:
        # The ways out, and the whole of what AT does about a scanner that is not
        # there: it says them and it installs NOTHING (§7a, the Podman the
        # `certutil` word already follows). What failed is the EXTRACTION — the
        # `gitleaks` travels inside the binary —, so the platform is named: it is
        # what tells "this artifact is not mine" from "this folder is not mine".
        return REFUSED, "\n".join(
            (
                tr("secrets.scan.no_tool", platform=gitleaks.label()),
                tr("secrets.scan.ways"),
            )
        )
    if answer.state == scanner.FAILED:
        return REFUSED, tr("secrets.scan.failed")
    # The rule list said out loud: which scanner, and which version of it, stood
    # behind what follows — the only honest answer to "a list that ages".
    lines = [tr("secrets.scan.rules", tool=answer.tool)]
    if answer.state == scanner.CLEAN:
        lines.append(tr("secrets.scan.clean"))
        return OK, "\n".join(lines)
    lines.append(tr("secrets.scan.found"))
    lines += [_shown(finding) for finding in answer.findings]
    return OK, "\n".join(lines)


def _shown(finding: scanner.Finding) -> str:
    """One finding as a person reads it: the rule and WHERE — never the value.

    The commit is cut to its short form because that is the spelling a person
    pastes into `git show`, and the whole hash is noise on a line. A finding the
    files as they are already carry has no commit, and the sentence says less
    because there is less to say.
    """
    where = f"{finding.where}:{finding.line}" if finding.line else finding.where
    if finding.commit:
        return tr(
            "secrets.scan.committed",
            rule=finding.rule,
            where=where,
            commit=finding.commit[:7],
        )
    return tr("secrets.scan.finding", rule=finding.rule, where=where)


def install_hooks(args: list[str]) -> tuple[int, str]:
    """`secret install_hooks` — the varredura becomes `git`'s own portão.

    **The act is the table's own, and it does not walk `run`.** It writes two
    files into a repository's own `.git/hooks/` and no row of any table, so it
    is no `create`, no `edit` and no `cancel` — `core.hooks` is composed the
    same way `core.scanner` already is.

    `--repo <path>` is the one argument: left out, the repository protected is
    the Working Folder running this command (an AT user's own data); said, it
    is ANY repository — chiefly a product checkout, which §3 never lets become
    a Working Folder, so there has to be a way to point this act at one that
    is not.
    """
    repo: Path | None = None
    rest = list(args)
    if rest[:1] == ["--repo"]:
        if len(rest) != 2 or not rest[1]:
            return USAGE, rejected(permissions.INSTALL_HOOKS)
        repo = Path(rest[1])
        rest = []
    if rest:
        return USAGE, rejected(permissions.INSTALL_HOOKS)
    report = hooks.install(repo)
    if report.state == hooks.NOT_A_REPO:
        return REFUSED, tr("secrets.hooks.not_a_repo", where=str(report.target))
    return OK, tr("secrets.hooks.installed", where=str(report.target))


# ----------------------------------------------------------- the reminder ---


def reminder_due(args: list[str]) -> tuple[int, str]:
    """`reminder due` — which reminders a DAY is about (item 29's first slice).

    **The act is the table's own, and it does not walk `run`.** `due` is not one
    of the engine's six: it reads the store and rewrites no row, the way `scan`
    reads the folder and rewrites none — so it is a read on §4's scale, with no
    actor and no via in the signature and no line to leave.

    **The day is `--at`, and it defaults to today — the engine's own, never the
    machine's read a second time here.** A day already past is not refused: the
    fatia this door belongs to is decision, checkable against any day, and the
    push that reaches a phone on the day itself is another slice's work.
    """
    at = reminder.today()
    rest = list(args)
    if rest[:1] == ["--at"]:
        if len(rest) != 2:
            return USAGE, tr("reminder.due.error.arguments")
        try:
            at = date.fromisoformat(rest[1])
        except ValueError:
            return USAGE, tr("reminder.due.error.arguments")
        rest = []
    if rest:
        return USAGE, tr("reminder.due.error.arguments")
    found = reminder.due(at)
    lines = [tr("reminder.due.today", date=at.isoformat())]
    lines.append(
        rendered(reminder.REMINDER, found["due"]) if found["due"] else tr("table.word.empty")
    )
    lines.append("")
    lines.append(tr("reminder.due.warn"))
    lines.append(
        rendered(reminder.REMINDER, found["warn"]) if found["warn"] else tr("table.word.empty")
    )
    return OK, "\n".join(lines)


# -------------------------------------------------------------- the assist ---


def assist_preview(text: str, *, language: str | None = None, main_key: str | None = None) -> tuple[int, str]:
    """`assist "<frase>"` — what Jev would propose for `text`, without ever
    running it (TASK-180, fatia 2/3).

    **The act is a READ, the way `scan` and `reminder_due` already are.**
    Nothing of the folder changes for having asked, so there is no actor, no
    via, and no line or version to leave — what this door owns is the
    SENTENCE, so the `cli` and any surface that comes after it read the same
    one.

    `main_key` is handed in rather than read here: the Vault's credential is
    opened by `at.core.assist`, and a surface that read the vault itself
    would be a second door into it.
    """
    found = assist.preview(text, language=language or i18n.active_code(), main_key=main_key)
    if found is None:
        return REFUSED, tr("assist.preview.none")
    return OK, tr(
        "assist.preview.line",
        action=_jev_label(found.action, is_action=True),
        action_confidence=f"{found.action_confidence:.2f}",
        table=_jev_label(found.table, is_action=False),
        table_confidence=f"{found.table_confidence:.2f}",
        tier=tr(f"assist.preview.tier.{found.tier}"),
    )


def _jev_label(canonical: str, *, is_action: bool) -> str:
    """One of Jev's two answers, in the engine's own words — `jev.NONE` reads
    the same dash a proposal's empty fields already do."""
    if canonical == jev.NONE:
        return tr("table.word.none")
    return tr(f"table.action.{canonical}") if is_action else tables.table_name(canonical)


# ------------------------------------------------------------- the settings ---

# What a key nobody wrote answers, told apart from a key that holds `null`: the
# door says "not chosen" for the first and the value for the second, and the two
# are not the same answer.
_UNSET = object()


def setting(
    action: str,
    args: list[str],
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
) -> tuple[int, str]:
    """One act on the settings — the door the `cli` reaches them by (§4).

    The settings are an OBJECT of the catalogue and not a table, so they do not
    walk `run`: there are no rows, no fields and no lifecycle, and a sentence the
    interpreter reads never lands here. What they share with a table act is the
    whole of what §3 asks — the actor, the via and the line — and the line is
    written HERE, at the door, for the same reason it is written there: the
    engine does not know who asked nor by which road, and a line without them
    would be a line that pretends.

    **A read leaves nothing at all.** `list` and `view` are the one read
    (`permissions.NARROWED`), §3 makes a read not an act, and the folder is not
    versioned for one either: nothing changed, so there is nothing to keep. An
    `edit` is the act — it writes, leaves exactly one line, and ends in a version
    named by the very sentence the surface printed.

    The value is read by the CORE (`settings.literal`): `0.95` is the float the
    filter compares against and `forms` is the word the gate reads, and a surface
    that decided which is which would be a second reader of the file's shape.
    """
    if action == "list":
        if args:
            return USAGE, tr("setting.error.arguments")
        return OK, _settings_listing()
    if action == "view":
        if len(args) != 1:
            return USAGE, tr("setting.error.arguments")
        return OK, _settings_line(args[0])
    if action != "edit" or len(args) != 2:
        return USAGE, tr("setting.error.arguments")
    key, typed = args
    # The bar, read BEFORE the write — and it is this act that makes the reading
    # matter: editing `risk_threshold` moves the bar, so a reading taken after
    # the write would be the bar the demand chose and not the one it faced.
    bar = _arrival()
    try:
        written = settings.put(key, settings.literal(typed))
    except settings.Refused as refused:
        # A refusal is an act and leaves a line, with the reason's KEY and no
        # value — the value is what the person typed, and §3 keeps it out (§3,
        # `TheRefusalMask`).
        _line(
            permissions.SETTING, action, actor, via,
            audit.REFUSED, refused.key, str(refused), threshold=bar,
        )
        return REFUSED, str(refused)
    except files.ReadOnly as error:
        # The one writer's rule, answered here as the engine answers it there.
        saying = tr("cli.error.read_only", where=error.where)
        _line(
            permissions.SETTING, action, actor, via,
            audit.REFUSED, "cli.error.read_only", saying, threshold=bar,
        )
        return REFUSED, saying
    # The value is read BACK, so what the answer says is what the file now holds
    # and not what was typed: the write is the file's, and the file is the truth.
    saying = tr(
        "setting.edited",
        setting=written,
        value=_value_text(settings.get(written)),
    )
    _line(
        permissions.SETTING, action, actor, via, audit.OK, None, saying,
        threshold=bar,
    )
    return OK, saying


def _settings_listing() -> str:
    """Every key the door hands over — the ones the product reads and the ones
    this folder carries — with the value each one holds, aligned."""
    keys = settings.keys()
    width = max(len(key) for key in keys)
    return "\n".join(f"{key.ljust(width)}  {_setting_value(key)}" for key in keys)


def _setting_value(key: str) -> str:
    value = settings.get(key, _UNSET)
    return tr("setting.unset") if value is _UNSET else _value_text(value)


def _settings_line(key: str) -> str:
    """One key and its value — or the sentence that says the folder never chose.

    A key nobody set is an ANSWER and not a failure: §4's settings are the
    person's file, and a folder that never chose one is not a folder in trouble.
    What the door does not do is invent the default — that belongs to whoever
    reads the key (`nlu` its switch, `risk` its bar), and a second home for it
    here would be the one that drifts.
    """
    value = settings.get(key, _UNSET)
    if value is _UNSET:
        return tr("setting.unset.line", setting=key)
    return tr("setting.line", setting=key, value=_value_text(value))


def _value_text(value: object) -> str:
    """A value as a person reads it: a word as the word, and everything else the
    way the file writes it — `true` and not `True`, `0.95` and not a float's
    whole repr."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


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


def _listing(
    table: str, args: list[str], values: dict | None = None,
    ranges: dict[str, str] | None = None, full_table: bool = True,
) -> tuple[int, str, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """A table's listing, and the one narrowing the `cli` adds to it: `--all`
    puts back what the declaration hides, and `--project` keeps what one item
    claims.

    The filter is the PAGE's SCOPE and not a second one: a project's tasks are
    the whole of its SUBTREE, the set item 3's page draws. What stays the
    listing's own is the status filter the table declares — `task list` hides
    what is finished, `--all` puts it back — so the scope is shared with the
    page and the narrowing is the listing's, each in its own place.

    **`full_table` is the person's own convention (03/10/2026):** the GRID,
    every declared column, only when the sentence said "tabela"/"table"
    (`nlu.matcher`'s own reading) — the `cli`, which never carries that word at
    all, keeps asking for it by never passing `False` here. Everything else —
    a bare "listar tarefas" — is a bullet, one line per row, the row's own
    TITLE and nothing beside it.
    """
    show_all = "--all" in args
    rest = [arg for arg in args if arg != "--all"]
    wanted: str | None = None
    if rest[:1] == ["--project"] and len(rest) == 2:
        wanted, rest = rest[1], []
    if rest:
        return USAGE, rejected("list"), None, None
    if wanted is not None and not _claims(table):
        return USAGE, rejected("list"), None, None
    rows = tables.rows(table, show_all=show_all)
    if wanted is not None:
        # A project nobody has is refused the way a row nobody has is, and by
        # the same sentence: the filter is a reference like any other.
        owner = tables.find(PROJECT, wanted)
        scope = set(projects.subtree(owner["id"]))
        rows = [row for row in rows if projects.project_of(row) in scope]
    values = dict(values or {})
    ranges = dict(ranges or {})
    on_day = _bare_day(table, values, ranges)
    rows = _kept(table, rows, values, ranges)
    if on_day is not None:
        rows = [row for row in rows if reminder.occurs(row, on_day)]
    if not rows:
        if on_day is not None:
            # Named the way the person asked it: the DAY, not a field nobody
            # said — "nenhum lembrete em 03/10/2026", not "nada aqui ainda".
            when = tables.text_of(reminder.REMINDER, matcher.open_day_field(table), on_day.isoformat())
            return OK, tr("table.reminder.list.empty_on_day", date=when), None, None
        described = _described(table, values, ranges)
        if described:
            return OK, tr(
                "table.list.empty_filtered",
                table=tables.table_name(table, many=True).lower(), filter=described,
            ), None, None
        return OK, tr("table.word.empty"), None, None
    if full_table:
        header, cells = _table_rows(table, rows)
        return OK, words.table([header, *cells]), (header, cells), None
    # O IDENTIFICADOR VAI JUNTO DO TÍTULO (23/10/2026): é o que a pessoa diz para
    # nomear a linha (`apagar nota 5`), então a lista o mostra.
    bullets = [
        f"{tables.format_id(table, row['id'])} · {tables.title(table, row)}"
        for row in rows
    ]
    return OK, "\n".join(f"- {line}" for line in bullets), None, bullets


def _bare_day(table: str, values: dict, ranges: dict[str, str]) -> date | None:
    """A day said ALONE, for the `reminder` table — popped out of `values` so
    `_kept` never compares it, and handed back for `occurs` to read instead.

    "Lembretes de hoje" names no field: the day lands on `on_date`, the one
    `nlu.matcher.open_day_field` leaves open for this table (the comment beside
    `reminder.NOTIFIED` is where that wiring is declared). Read as a literal
    field match, `on_date` only holds for a `once` reminder — every `daily`,
    `weekly`, `monthly` and `yearly` row carries no `on_date` at all, so "hoje"
    found NOTHING for the reminder a person has every day. A day is a set of
    INSTANCES, not a stored value (the person's own words for the defect): what
    "hoje" means for this table is `reminder.occurs`, which already reads the
    very recurrence `on_date`'s literal match could only ever cover a slice of.

    Only the EXACT day is read this way — `ranges` empty for the field, which is
    what a bare "hoje"/"amanhã" produces. "lembretes até sexta" keeps the literal
    field comparison: folding a RANGE through the recurrence is a future day's
    work, and falling back to what already existed is not a regression.
    """
    if table != reminder.REMINDER:
        return None
    field = matcher.open_day_field(table)
    if field is None or field not in values or ranges.get(field, "=") != "=":
        return None
    raw = values.pop(field)
    ranges.pop(field, None)
    try:
        return date.fromisoformat(raw) if isinstance(raw, str) else None
    except ValueError:
        return None


def _described(table: str, values: dict, ranges: dict[str, str]) -> str:
    """The filter, in words — "prazo até 03/10/2026", "status ativo" — joined
    the way a person would say more than one at once. The primary field never
    describes (the same reason `_kept` never filters by it): residue is
    content, never a clause an empty listing explains itself with. `""` is a
    bare "listar tarefas", with nothing to describe at all.
    """
    primary = schema.primary(table)
    parts = []
    for name, value in values.items():
        if name == primary or not schema.field(table, name):
            continue
        label = tables.label(table, name).lower()
        text = tables.text_of(table, name, value)
        op = ranges.get(name, "=")
        if op == "<=":
            parts.append(f"{label} {tr('table.list.until')} {text}")
        elif op == ">=":
            parts.append(f"{label} {tr('table.list.since')} {text}")
        elif op in ("<", ">"):
            parts.append(f"{label} {_sign(op)} {text}")
        elif schema.field(table, name).get("type") == "day":
            # A bare day reads as "due by" in how the person already says it
            # ("tarefas para hoje") even though the engine's own match on it
            # is exact — the same leniency `_bare_day` gives `reminder`.
            parts.append(f"{label} {tr('table.list.until')} {text}")
        else:
            parts.append(f"{label} {text}")
    return " e ".join(parts)


def _kept(table: str, rows: list[dict], values: dict, ranges: dict[str, str]) -> list[dict]:
    """O que a FRASE filtrou: cada campo que ela citou mantém só as linhas cujo
    valor casa.

    **O campo de texto livre não filtra** (`schema.primary`): "listar tarefas
    comprar pão" não é "as tarefas cujo texto é exatamente 'comprar pão'" — o
    resíduo de um `list` não é um filtro, e tratá-lo como um esvaziaria a
    listagem que a pessoa esperava ver. O que filtra são os campos que um leitor
    TIPADO preencheu (data, número, valor de enum) — e cada um com a sua
    operação: `=` quando não há palavra de intervalo, `<=`/`>=` quando há.
    """
    primary = schema.primary(table)
    declared = (schema.of(table) or {}).get("fields", {})
    for name, value in values.items():
        if name == primary or name not in declared:
            continue
        op = ranges.get(name, "=")
        rows = [row for row in rows if _matches(row.get(name), value, op)]
    return rows


def _matches(cell: Any, value: Any, op: str) -> bool:
    """Se o valor de uma linha casa com o que a frase pediu, sob `op`.

    Sem operação é igualdade. Com `até`/`desde` é a comparação — e uma célula
    VAZIA (`None`) nunca casa um intervalo: uma tarefa sem prazo não é "até
    sexta". Uma comparação que os tipos não deixam fazer (um texto contra uma
    data) não estoura: não casa.
    """
    if op == "=" or cell is None:
        return cell == value
    try:
        if op == "<=":
            return cell <= value
        if op == ">=":
            return cell >= value
        if op == "<":
            return cell < value
        if op == ">":
            return cell > value
    except TypeError:
        return False
    return cell == value


def _claims(table: str) -> bool:
    """Whether `table` is one a `--project` filter can narrow — a table that
    declares a field of its own pointing at `project`."""
    ref = schema.field(table, "project").get("ref")
    return isinstance(ref, list) and PROJECT in ref


def _viewing(table: str, args: list[str]) -> tuple[int, str, dict | None]:
    """One row's fields — and, for a project, what is inside it.

    A project is a SCOPE and not a table of its own (§4): the page a person
    opens shows the project's own fields and then the tasks of the whole
    subtree, and §5 does not let the `cli` be the surface that cannot. So the
    slices of an item are answered here, by the very rows the page draws.
    """
    if len(args) != 1:
        return USAGE, rejected("view"), None
    row = tables.find(table, args[0])
    lines = [f"{tr('table.field.id')}: {tables.format_id(table, row['id'])}"]
    for name in (schema.of(table) or {}).get("fields", {}):
        if name == "id":
            continue
        lines.append(f"{tables.label(table, name)}: {tables.text_of(table, name, row.get(name))}")
    if table == PROJECT:
        page = projects.page(row["id"]) or {}
        slices = [entry for entry in page.get("rows", []) if isinstance(entry, dict)]
        lines.append("")
        lines.append(f"{tables.table_name(TASK, many=True)}:")
        lines.append(rendered(TASK, slices) if slices else tr("table.word.empty"))
    return OK, "\n".join(lines), row


def card(table: str, row: dict) -> dict:
    """ONE row as a card a surface draws — the fields the table declares as its
    `columns`, and nothing else.

    It is the person's own rule (20/10/2026): the card is the table's MAIN
    fields, and which ones those are is the DECLARATION's to say, never the
    surface's — `schema.columns` is the very list a listing shows, so the card
    and the grid agree about what a table's main fields are.

    The ID travels beside the fields because a card is a door: the surface
    links to the record's page with it (`views.ts`'s `openRef`), the same way
    the row's own title does. Every value is written the way the engine writes
    one (`text_of`) — the closed vocabulary's word, the reference's title — so
    the card shows what the listing shows and never a raw number.

    It is the CARD's shape, not the record's (`at.ui.webapp.app._record`): a
    full record carries every declared field, `raw` values, references and the
    editor's own facts. A chat answer has no editor — what it needs is the row
    as a person reads it.
    """
    return {
        "table": table,
        "entity": tables.table_name(table),
        "id": row.get("id"),
        "shown_id": tables.format_id(table, row["id"]) if "id" in row else "",
        "title": tables.title(table, row),
        "fields": [
            {
                "name": name,
                "label": tables.label(table, name),
                "value": tables.text_of(table, name, row.get(name)),
            }
            for name in tables.columns(table)
            if schema.field(table, name)
        ],
    }


def _table_rows(table: str, rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    """The header and the cells, the id then the columns the table declares —
    the shape both `rendered` (the `cli`'s ASCII) and a surface that draws an
    actual table (the WebApp's chat, TASK-?) read, each in its own words."""
    header = [tr("table.field.id")] + [tables.label(table, name) for name in tables.columns(table)]
    cells = [
        [tables.format_id(table, row["id"])]
        + [tables.text_of(table, name, row.get(name)) for name in tables.columns(table)]
        for row in rows
    ]
    return header, cells


def rendered(table: str, rows: list[dict]) -> str:
    """The listing: the id, then the columns the table declares.

    The drawing is `ui/words.table`'s and not this file's: the deploy's status
    is the same kind of thing — a header and cells — and two renderers would be
    two sets of widths that part company the first time a title grows.
    """
    header, cells = _table_rows(table, rows)
    return words.table([header, *cells])


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
