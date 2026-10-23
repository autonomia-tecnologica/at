"""O assist: o que o Jev lê de uma frase — a leitura PRIMÁRIA, e não mais um
fallback (TASK-180, invertido a pedido da pessoa, 03/10/2026).

**O Jev lê toda frase, e o matcher determinístico é o apoio.**
`at.nlu.propose` pergunta ao Jev PRIMEIRO (`decide`); o matcher responde
quando o Jev não tem o que dizer — sem chave, switch desligado, Jev fora do ar,
um palpite abaixo do piso, ou um rewrite que o matcher não resolve. Antes era o
contrário: o matcher era o portão e o Jev só via as frases que o matcher já
tinha RECUSADO (`no_action`/`no_table`), o que fazia das frases "entendidas"
uma leitura 100% NLU — que é a queixa que motivou a inversão.

**A escrita continua determinística** (§4, "o que não resolve é resíduo, nunca
um palpite"): o que o Jev propõe é um REWRITE que o PRÓPRIO matcher resolve, e
o motor determinístico executa o ato e o audita. O Jev sugere a leitura; quem
age é o motor, sobre a frase reescrita nas palavras do vocabulário.

**O `nlu` continua inteiro.** `matcher.py`, `normalizer.py`, `interpreter.py`,
`reading.py` e o vocabulário não carregam palavra deste módulo — a leitura
determinística não muda; o que mudou é quem é consultado primeiro.

**Three tiers, read off the risk the ACTION already carries on §4's own
scale.** A read (`list`, `view`) is cheap to get wrong — a person sees a
listing that was not what they meant and asks again — so it auto-applies from
`0.7`. A write is not: it auto-applies only from `0.9`, and confirms (never
silently) from `0.5`. Below `0.5`, or either half of the guess landing on
`jev.NONE`, is the same answer as no guess at all — the sentence is handed
back to the `Refused` that was already on its way out. The two thresholds and
the floor are `jev-test/slang_dispatch.py`'s own numbers, proven against real
slang before this module existed; this fatia is the engine that CARRIES them
into the product, not a re-derivation of them.

**Auto rewrites, and resubmits to the REAL matcher — never to a second
reading of its own.** The rewrite plants the vocabulary's own words for the
guessed action and table at the front of the sentence (`jev.spoken`), so what
runs next is `at.nlu.matcher.match` on an ORDINARY sentence: the date, the
number, the row, the residue — every one of them is read exactly as it always
was, because nothing about THAT reading is this module's to repeat. Confirm
asks instead of applying, through the very `Question` shape `cli` and WebApp
already print — the rewritten sentence is what the person is asked to repeat,
so saying yes is saying that sentence again and walking the ordinary road.

**E a DATA e a HORA ganham, cada uma, a palavra-campo da própria tabela**
(`_ground`): "me lembrar de imprimir passagens hoje 18h" não escreve "data" nem
"horário", e é o Jev quem aponta `hoje` e `18h` (`jev.DAY_SPAN`/`TIME_SPAN`) —
o código planta `data` e `horário` antes delas, e o matcher lê a frase como
qualquer outra. É por isso que a leitura da data e da hora continua 100%
determinística: o Jev diz ONDE, e quem lê o valor é o matcher, com a mesma
gramática de sempre. Uma data dita ancora a recorrência em `once` (a regra da
pessoa, 2026-10-05), plantado antes do corpo para uma frequência falada vencer.

**The switch is this module's own, separate from the interpreter's, and born
ON.** `nlu.SWITCH` ("interpreter") governs the deterministic layer, which
calls no service and so has nothing to weigh against being on by default; this
one (`SWITCH`, "assist") governs a call OUT, and still starts on — a folder
that never chose gets the feature, and `settings.json` is where it is turned
back off. The two switches share nothing: turning the interpreter off already
takes `propose` out of the core API before this module is ever reached, and
turning this one off takes only the Jev fallback out, leaving the
deterministic reading exactly as it was.

**The credential lives in the Vault, scoped to `jev.SERVICE`, and this module
never seals one.** Sealing is `at.core.secrets.seal`'s own door, carried out
once by whoever provisions the folder with a Main Key — the same three grades
of §4 govern how a caller comes to hold the string. What THIS module does is
the read: a `main_key` handed to `decide` opens the one row of `secret` scoped
`jev` (`at.core.secrets.open_value`), and no key at all — nobody passed one,
the row is not there, the phrase is wrong — answers `None` exactly the way
`open_value` already does, which this module turns into "stand by the
refusal" rather than a crash over a credential that was never provisioned.
`main_key` has no caller yet in `cli` or the WebApp (this fatia does not touch
either): the engine is complete and proven with an injected key and an
injected Jev client, and wiring a live Main Key through a surface is a later
fatia's own decision, not a gap in this one.

**Fatia 2/3 wires the first surface, and it is a DRY RUN.** `preview` is
`decide`'s own call to Jev and `_tier`'s own reading of it, with no
`Refused` to carry in and no rewrite, no confirm and no match ever attempted
— `at-cli assist "<frase>"` prints the action, the table, both confidences
and the tier a real sentence would land in, and nothing about the folder
changes for having asked. It is the surface `main_key` was always missing:
read without echo, the same way `backup` and `admin` already read theirs.
`preview` reads `_tier` RAW, on purpose: it is the engine's own judgment,
off the scale `jev-test/slang_dispatch.py` proved, and it does not move with
a folder's `MODE` — the dry run answers the same question in every folder,
and what the folder chose is `at-cli setting view` to read.

**Fatia 3/3 gives the REAL path a second knob, beside the switch.** The
switch answers whether Jev is asked at all; `MODE` answers what a tier
that is not `REFUSE` does once Jev has answered — and it is the only place
the two tiers `AUTO` and `CONFIRM` still disagree, because a demand either
asks or does not. `CAUTIOUS` (the default a folder that never chose gets,
the same "born safe" `nlu.SWITCH` is not — a service call is not free to
assume) turns every non-`REFUSE` tier into `CONFIRM`: nothing this module
ever proposes applies without a person reading it back first, no matter how
sure Jev was. `AUTOMATIC` is the other way: every non-`REFUSE` tier becomes
`AUTO`, and a person who chose it has said a guess this product is not
flatly wrong about is a guess worth acting on. `REFUSE` is neither tier's
to touch — a guess naming `jev.NONE`, or below the floor, is not a
confidence problem the folder's taste can fix (the module's own §4 reading,
carried unchanged from fatia 1/3). `_tier` computes the RAW tier off the
read/write thresholds exactly as it always did; `decide` is the one caller
that asks `_mode` to fold `AUTO` and `CONFIRM` together before acting on it,
which is why `preview` — a question about the engine, not about what this
folder would DO — never calls it.
"""

from __future__ import annotations

import json
import unicodedata

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from at.core import files, jev, paths, permissions, secrets, settings, tables
from at.data import schema, store
from at.encryption import vault
from at.nlu import matcher
from at.nlu.proposal import Proposal
from at.nlu.reading import Intent, Question, Refused

# The key of this module's own switch in `app/settings.json` — separate from
# `at.nlu.SWITCH`, because two switches that touched each other would be the
# two names the glossary already forbids touching. Born ON (see the module
# docstring): a folder that never chose still gets the fallback, and turning
# it off is what `settings.json` is for.
SWITCH = "assist"

# The three tiers `_tier` answers with, and the only three there are.
AUTO = "auto"
CONFIRM = "confirm"
REFUSE = "refuse"

# §4's own scale, carried from the prototype that proved it (module docstring):
# a READ auto-applies cheaper than a WRITE does, and both confirm from the same
# floor before the guess is worth nothing at all.
READ_THRESHOLD = 0.7
WRITE_THRESHOLD = 0.9
CONFIRM_FLOOR = 0.5

# A INTENÇÃO (conversa: saudação, agradecimento, ajuda…) é só fala — não escreve
# nada —, então vale o piso de uma leitura barata. E a subintenção que o Jev não
# soube dizer cai em `PLAIN`, a que toda intenção tem.
INTENT_THRESHOLD = READ_THRESHOLD
PLAIN = "plain"

# The `i18n` key of the question a CONFIRM tier asks — carried in `nlu.json`
# beside `ask.which_field` and `ask.which_hour`, because it is the same shape
# of question the matcher's own grammar already asks back, and a surface that
# prints one already knows how to print the other.
ASK_KEY = "nlu.ask.slang"

# The key of the folder's OTHER choice about this module (TASK-180, fatia
# 3/3) — separate from `SWITCH`, which answers whether Jev is asked at all.
# `MODE` answers what `decide` does once Jev HAS answered: `CAUTIOUS` is the
# default (the module docstring's "born safe"), and `AUTOMATIC` is the one a
# folder opts into.
MODE = "assist_mode"
CAUTIOUS = "cautious"
AUTOMATIC = "automatic"


def enabled() -> bool:
    """Whether this module's own fallback is on. Born on (see the docstring)."""
    return bool(settings.get(SWITCH, True))


def mode() -> str:
    """The folder's choice between `CAUTIOUS` and `AUTOMATIC` — `CAUTIOUS` for
    every value that is not exactly `AUTOMATIC`, the same "a strange
    declaration fails closed" reading `at.ui.ask.present` already gives a
    hand-edited `type` — a folder that never chose, and a folder a hand
    mistyped, both get the side that never applies without being read back
    first.
    """
    return AUTOMATIC if settings.get(MODE) == AUTOMATIC else CAUTIOUS


# ------------------------------------------------------------------- cache ---
#
# O cache das leituras do Jev: a frase normalizada (mais o idioma, porque o
# rewrite é por idioma) vira a decisão que o Jev deu UMA vez. Bate = nenhuma
# rede e NENHUMA chave — o cache não abre credencial nenhuma, que é o ponto: a
# frase repetida responde offline. Erra = pergunta ao Jev e guarda.
#
# **Uma entrada que o motor não reconhece é MISS.** A decisão guardada nomeia
# uma ação e uma tabela; se a ação sumiu de `tables.ACTIONS`, ou a tabela não é
# mais declarada nesta pasta, a entrada não serve — o Jev responde de novo, e o
# cache se cura sozinho. É a mesma checagem que `_tier`/`_rewrite` fariam
# depois, feita cedo para não gastar uma rede com lixo.
#
# **O Jev é uma API EXTERNA, e ainda assim é um serviço (§4).** A casa dele é
# `App/services/jev/`, e o cache é o estado DELE — antes morava solto em
# `App/jev-cache.json`, e a fatia dos serviços o trouxe para a casa. O nome
# interno do serviço é `jev`, e o arquivo, `cache.json`.
FOLDER = "jev"
CACHE = "cache.json"


def cache_file() -> Path:
    """`App/services/jev/cache.json` — o que o Jev respondeu, guardado."""
    return paths.service_dir(FOLDER) / CACHE


def _normalize(text: str) -> str:
    """A frase reduzida à chave: sem caixa, sem acento, sem pontuação, com os
    espaços colapsados. Duas grafias da MESMA frase (acento, maiúscula,
    vírgula) batem na mesma entrada — que é o que um cache quer."""
    lowered = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in lowered if not unicodedata.combining(c))
    return " ".join("".join(c if c.isalnum() else " " for c in plain).split())


def _key(text: str, language: str) -> str:
    return f"{language}:{_normalize(text)}"


def _entries() -> dict:
    data = files.read_json(cache_file(), default={})
    return data if isinstance(data, dict) else {}


def _cached(key: str) -> jev.Decision | None:
    entry = _entries().get(key)
    if not isinstance(entry, dict):
        return None
    action, table = entry.get("action"), entry.get("table")
    # `none` é uma resposta GUARDÁVEL: a frase de conversa ("oi") não pede ação
    # nem tabela, e é a intenção que a responde.
    if action not in (*tables.ACTIONS, jev.NONE):
        return None
    if table != jev.NONE and schema.of(table) is None:
        return None
    # Uma entrada `none`/`none` GRAVADA ANTES do eixo de intenção não tem a
    # chave `intent`: ela nunca foi perguntada sobre a intenção, e servi-la
    # seria responder "não entendi" a um "oi". É miss — o Jev responde de novo
    # e a entrada se regrava inteira.
    if action == jev.NONE and table == jev.NONE and "intent" not in entry:
        return None
    intent = entry.get("intent") or jev.NONE
    try:
        return jev.Decision(
            action=str(action),
            action_confidence=float(entry["action_confidence"]),
            table=str(table),
            table_confidence=float(entry["table_confidence"]),
            action_span=str(entry.get("action_span", "")),
            table_span=str(entry.get("table_span", "")),
            # Uma entrada GRAVADA ANTES dos trechos de data e hora não os tem:
            # lê `NONE`, e a leitura sai sem eles — o cache se cura na próxima.
            day_span=str(entry.get("day_span") or jev.NONE),
            time_span=str(entry.get("time_span") or jev.NONE),
            # Idem para a intenção: entrada anterior a este eixo lê `NONE`. Uma
            # intenção que o catálogo não declara mais é descartada por `_intent`.
            intent=str(intent),
            intent_confidence=float(entry.get("intent_confidence") or 0.0),
            subintent=str(entry.get("subintent") or jev.NONE),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _remember(key: str, guess: jev.Decision) -> None:
    data = _entries()
    data[key] = {
        "action": guess.action,
        "action_confidence": guess.action_confidence,
        "table": guess.table,
        "table_confidence": guess.table_confidence,
        "action_span": guess.action_span,
        "table_span": guess.table_span,
        "day_span": guess.day_span,
        "time_span": guess.time_span,
        "intent": guess.intent,
        "intent_confidence": guess.intent_confidence,
        "subintent": guess.subintent,
    }
    files.atomic_write_text(
        cache_file(),
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    )


def decide(
    text: str,
    *,
    language: str,
    now: datetime | None = None,
    main_key: str | None = None,
    transport: jev.Transport | None = None,
) -> Proposal | Question | Intent | None:
    """A leitura PRIMÁRIA: o que o Jev lê de `text`, ou `None` para deixar a
    frase ao matcher determinístico — o apoio.

    **Não há mais gatilho.** Antes, `propose` só chegava aqui quando o matcher
    já tinha RECUSADO a frase (`no_action`/`no_table`), e o Jev era a sobra;
    agora o Jev lê TODA frase primeiro, e o matcher passa a ser quem responde
    quando o Jev não tem o que dizer. É a inversão que a pessoa pediu: o Jev
    deixa de ser um botão depois do fracasso e vira o cérebro.

    `None` é a resposta de toda porta que não é do Jev: o switch desligado
    (`SWITCH`), a frase que nem o cache nem o Jev responderam (sem credencial
    para abrir na primeira vez, ou `jev.JevError` — a rede, a chave, uma forma
    que este leitor não conhece). Nenhuma dessas é deste módulo estourar: o
    matcher determinístico tem uma leitura pronta para a MESMA frase, e um
    serviço fora do ar não é motivo para trocar essa leitura por uma pior. O
    `REFUSE` do tier é o mesmo: um palpite que não merece confiança devolve a
    frase ao matcher, e não a uma recusa que o Jev não pediu para assinar.

    **O cache vem ANTES da credencial** (§ cache): uma frase já lida responde
    sem rede e sem chave — é o que faz a leitura repetida funcionar offline.

    E um rewrite que o matcher não resolve deterministicamente TAMBÉM devolve
    `None` — quem tenta a frase ORIGINAL, como apoio, é quem chamou.
    """
    if not enabled():
        return None
    key = _key(text, language)
    guess = _cached(key)
    if guess is None:
        api_key = _credential(main_key)
        if api_key is None:
            return None
        try:
            guess = jev.decide(text, language=language, api_key=api_key, transport=transport)
        except jev.JevError:
            return None
        _remember(key, guess)
    # **A INTENÇÃO só vale quando ação e tabela deram `none`**: se a frase pede
    # uma ação, a ação ganha e a escrita segue determinística. É conversa — não
    # escreve nada —, então o piso é o de uma leitura barata, e independe do
    # `MODE` da pasta (não há o que confirmar).
    spoken = _intent(guess, language)
    if spoken is not None:
        return spoken
    tier = _folded(_tier(guess))
    if tier == REFUSE:
        return None

    # **O JEV DECIDE.** Sem atalho: os argumentos saem da frase SEM os trechos que
    # ele apontou (a gíria da ação não vira `text`), e a ação/tabela vêm
    # EXPLÍCITAS — nada de rewrite colidindo, e nada de devolver a leitura do
    # matcher quando os dois concordam (era o que fazia o Jev sumir).
    #
    # O "Confirmar" reenvia a frase canônica com uma MARCA (`confirmed`), e o
    # `propose` a lê SÓ com o matcher — é o que impede o loop de re-perguntar ao
    # Jev para sempre.
    sentence = _ground(text, guess, language)
    if tier == CONFIRM:
        return Question(ASK_KEY, sentence)
    try:
        return matcher.match(sentence, language=language, now=now,
                             action=guess.action, table=guess.table)
    except Refused:
        return None


def _intent(guess: jev.Decision, language: str) -> Intent | None:
    """A conversa que o Jev leu, ou `None` quando a frase pede uma ação (ou
    tabela), a intenção é `none`, ou ela ficou abaixo do piso."""
    if guess.action != jev.NONE or guess.table != jev.NONE:
        return None
    if guess.intent == jev.NONE or guess.intent not in jev.intents(language):
        return None
    if guess.intent_confidence < INTENT_THRESHOLD:
        return None
    known = jev.subintents(guess.intent, language)
    sub = guess.subintent if guess.subintent in known else PLAIN
    return Intent(guess.intent, sub, f"intent.{guess.intent}.{sub}")


@dataclass(frozen=True)
class Preview:
    """What `decide` would see about one phrase, for a person to CHECK before
    anything is wired to run it (TASK-180, fatia 2/3 — the dry run `at-cli
    assist ask`).

    The four numbers are `jev.Decision`'s own, carried through unchanged, and
    `tier` is `_tier`'s own answer about them — this module computes the tier
    exactly once, and a preview reads it rather than guessing it a second way.
    """

    action: str
    action_confidence: float
    table: str
    table_confidence: float
    tier: str


def preview(
    text: str,
    *,
    language: str,
    main_key: str | None = None,
    transport: jev.Transport | None = None,
) -> Preview | None:
    """What Jev answers about `text`, and the tier it lands in — read only,
    and never applied, rewritten, or handed to the matcher.

    `None` collapses every way there is nothing to show, the same way
    `decide` already does: the switch is off, there is no credential to
    open, or Jev itself did not answer. It is reached directly, with no
    `Refused` to carry in — a dry run is about ANY phrase, not only the ones
    the deterministic matcher already gave up on.
    """
    if not enabled():
        return None
    api_key = _credential(main_key)
    if api_key is None:
        return None
    try:
        guess = jev.decide(text, language=language, api_key=api_key, transport=transport)
    except jev.JevError:
        return None
    return Preview(
        action=guess.action,
        action_confidence=guess.action_confidence,
        table=guess.table,
        table_confidence=guess.table_confidence,
        tier=_tier(guess),
    )


def _tier(guess: jev.Decision) -> str:
    """Which of the three tiers this guess lands in (the module docstring's
    own scale) — `jev.NONE` on either half is the floor itself and nothing
    below it, because a guess that names nothing is not a confidence problem.

    This is the RAW tier, off the read/write thresholds alone — `preview`
    reads it exactly as it stands, and `decide` is the one caller that folds
    it through `_folded` before acting on it (the module docstring's fatia
    3/3 note).
    """
    if guess.action == jev.NONE or guess.table == jev.NONE:
        return REFUSE
    threshold = WRITE_THRESHOLD if guess.action in tables.WRITES else READ_THRESHOLD
    if guess.confidence >= threshold:
        return AUTO
    if guess.confidence >= CONFIRM_FLOOR:
        return CONFIRM
    return REFUSE


def _folded(tier: str) -> str:
    """Where the folder's `MODE` folds `AUTO` and `CONFIRM` together —
    `REFUSE` is handed back untouched, because neither mode is free to act on
    a guess that named nothing or fell under the floor (module docstring).

    `CAUTIOUS` folds a `tier` that is not `REFUSE` into `CONFIRM`: even a
    guess the raw scale would have applied outright is read back first.
    `AUTOMATIC` folds it the other way, into `AUTO`: even a guess the raw
    scale would only have confirmed is applied outright. Which of the two
    `tier` started as stops mattering the moment it is not `REFUSE` — that is
    the whole of what "the folder's taste" means here.
    """
    if tier == REFUSE:
        return REFUSE
    return AUTO if mode() == AUTOMATIC else CONFIRM


# A palavra que o Jev NÃO apontou: o trecho não está escrito na frase.
def _real(span: str) -> bool:
    return bool(span) and span != jev.NONE


# O valor de `freq` que faz de uma recorrência um compromisso de uma vez só —
# a regra da pessoa (2026-10-05). É uma chave de enum como qualquer outra; o
# que o código lê é a DECLARAÇÃO, nunca o nome.
ONCE = "once"


def _ground(text: str, guess: jev.Decision, language: str) -> str:
    """A frase reescrita nas palavras do vocabulário — o matcher lê uma frase
    comum, e não precisa conhecer gíria nenhuma.

    A ação e a tabela que o Jev escolheu vão à FRENTE (`jev.spoken`), e as
    palavras que ele apontou como a ação e a tabela SAEM do corpo, para a gíria
    (`joga`, `penca`) não vazar como argumento.

    **A data e a hora ganham a palavra-campo que a PRÓPRIA tabela declara**, e é
    isso que faz "… hoje 18h" — sem campo nenhum — atravessar o matcher: a
    `hoje` planta-se o `data` (o `on_date` da tabela) e à `18h` o `horário` (o
    `at`), ambos lidos do `schema` e do vocabulário e nunca de uma lista aqui.
    Uma tabela que não declara o campo (uma tarefa, sem hora) não recebe planta
    nenhuma — o trecho volta a ser do corpo, como era.
    """
    table = guess.table
    drop = {span for span in (guess.action_span, guess.table_span) if _real(span)}
    plants = (
        (guess.day_span, matcher.open_day_field(table)),
        (guess.time_span, matcher.list_field(table, "time")),
    )
    body: list[str] = []
    for word in text.split():
        if word in drop:
            continue
        for span, field in plants:
            if _real(span) and word == span and field:
                body.append(jev.spoken(field, language) or field)
        body.append(word)
    parts = [
        word
        for word in (jev.spoken(guess.action, language), jev.spoken(guess.table, language))
        if word
    ]
    # O `once` da regra vai ANTES do corpo: uma frequência que a pessoa DISSE
    # (`todo dia`) vem depois e é a que fica — a última dita vence.
    anchor = _anchor(guess, table, language)
    if anchor:
        parts.append(anchor)
    parts.extend(body)
    return " ".join(parts).strip()


def _anchor(guess: jev.Decision, table: str, language: str) -> str:
    """Uma DATA dita na frase faz da recorrência um compromisso de UMA VEZ (a
    regra da pessoa, 2026-10-05): em vez do `daily` que a tabela traz por
    padrão, o `once`. Uma frase sem data — só a hora, ou nada — não ancora nada
    e deixa o `daily` da tabela valer.
    """
    if not _real(guess.day_span) or _freq_field(table) is None:
        return ""
    return jev.spoken(ONCE, language) or ""


def _freq_field(table: str) -> str | None:
    """O campo cuja lista fechada carrega o compromisso único — o `freq` de
    qualquer tabela que recorra. Lido da DECLARAÇÃO (`enum`), nunca de um nome.
    """
    fields = (schema.of(table) or {}).get("fields")
    if not isinstance(fields, dict):
        return None
    for name, field in fields.items():
        enum = field.get("enum") if isinstance(field, dict) else None
        if isinstance(enum, dict) and ONCE in enum:
            return name
    return None


def _credential(main_key: str | None) -> str | None:
    """The Jev API key, opened from the Vault with `main_key` — or `None` for
    every way there is nothing to open: no key was handed in, no row of
    `secret` is scoped `jev` yet, or the phrase does not open the one there
    is (`secrets.open_value`'s own three-ways-to-nothing)."""
    if not main_key:
        return None
    row = _row(jev.SERVICE)
    if row is None:
        return None
    return secrets.open_value(row, main_key)


def _row(service: str) -> dict | None:
    """The one row of `secret` scoped to `service`, or `None` — read off the
    store directly, the way a credential that proves nothing of its own is
    found before anything about it is opened."""
    for row in store.load(permissions.SECRET):
        if row.get(secrets.SCOPE) == service:
            return row
    return None


def configured() -> bool:
    """Se a pasta tem a credencial do Jev selada — um `secret` de escopo `jev`.

    É a pergunta da superfície: sem a linha, o Jev não é consultado (a leitura
    cai no matcher), e é isso que a página diz em "Jev não configurado".
    """
    return _row(jev.SERVICE) is not None


def configure(value: str, main_key: str) -> bool:
    """Sela a credencial do Jev nesta pasta — cria a linha, ou reescreve a dela.

    **Uma linha só por serviço.** Um segundo `secret` scoped `jev` deixaria a
    pasta com dois valores e só o primeiro seria lido (`_row`), então a segunda
    configuração REESCREVE a mesma linha — uma rotação, não uma cópia.

    `False` é a Chave Principal que o Cofre recusa (a frase curta demais, o
    escopo inválido); a mensagem é a do próprio Cofre, e quem a lê é a
    superfície. O valor em claro não sai daqui (§4).
    """
    try:
        envelope = vault.seal(value, secrets.key_of(jev.SERVICE, main_key))
    except secrets.SecretsError:
        return False
    row = _row(jev.SERVICE)
    if row is None:
        tables.create("secret", {"name": jev.SERVICE, "service": jev.SERVICE,
                                 secrets.SEALED: envelope})
    else:
        tables.edit("secret", store.number_of(row), {secrets.SEALED: envelope})
    return True
