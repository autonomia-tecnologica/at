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

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from at import nlu
from at.core import (
    assist,
    audit,
    files,
    jev,
    permissions,
    scanner,  # noqa: F401 — `at.ui.ask.scanner.scan` is a patch target of the suites
    tables,
)
from at.data import schema
from at.i18n import tr

# The door's pieces live in their own modules; every name a caller reached by
# `at.ui.ask.<name>` is read back here, so the door stays ONE address.
from at.ui.ask_backup import _backed, _main_key, backup_message  # noqa: F401
from at.ui.ask_base import OK, PROJECT, REFUSED, TASK, USAGE, _sets, _sign, rejected, surplus  # noqa: F401
from at.ui.ask_jobs import _ceiling, _fired, _ran, _round, job, tick  # noqa: F401
from at.ui.ask_listing import (  # noqa: F401
    _bare_day,
    _described,
    _kept,
    _listing,
    _matches,
    _table_rows,
    _viewing,
    card,
    rendered,
)
from at.ui.ask_reads import (  # noqa: F401
    _covers,
    _jev_label,
    _shown,
    assist_preview,
    install_hooks,
    remind,
    reminder_due,
    scan,
)
from at.ui.ask_risk import _arrival, _line, ceiling, denied, holds, present  # noqa: F401
from at.ui.ask_run import _acted, execute, run  # noqa: F401
from at.ui.ask_settings import setting  # noqa: F401


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
        awaiting = cast("str | None", refused.kw.get("canonical")) if refused.key == "nlu.error.no_table_bare" else None
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
        # An `edit`'s confirmation also shows WHAT CHANGES, field by field; a
        # question with no diff speaks the ordinary `key` sentence.
        saying = (
            tr("nlu.ask.slang_changes", text=proposed.text, changes=proposed.changes)
            if proposed.changes
            else tr(proposed.key, text=proposed.text)
        )
        return Result(
            "question", None, saying, REFUSED,
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


def __getattr__(name: str) -> Any:
    """`last_rows` and `last_scan` are WRITTEN by the pieces that own them; read here
    live, so `at.ui.ask.last_rows` is never a stale copy taken at import."""
    if name == "last_rows":
        from at.ui import ask_listing  # noqa: PLC0415

        return ask_listing.last_rows
    if name == "last_scan":
        from at.ui import ask_reads  # noqa: PLC0415

        return ask_reads.last_scan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
