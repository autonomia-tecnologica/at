"""AT's door into Jev, TypeSafe's System One model — the slang layer's one
external call (§5's interpreter vocabulary, item 11; TASK-180, fatia 1/3).

**This is a SERVICE and not an SDK — and it lives beside `notifier.py`, not
under `at/services/`.** TypeSafe ships a Python SDK, and this module uses none
of it: §3 (Dependência externa) keeps AT to the one runtime dependency it
already pins (`PyNaCl`), and the HTTP contract behind the SDK is one `POST`
with a JSON body — the same shape `at.core.notifier` already talks to another
external service with, through `urllib` alone. `at/services/` is the OTHER
kind of third party (`test_boundary.py`'s own closed list): the Caddy and the
`gitleaks` the BINARY carries, bytes that travel inside the artifact and never
touch a socket on their own. Jev is the opposite shape — nothing is vendored,
every call leaves the process over the network — so it takes the same shelf
`notifier.py` already does. It is also not one of the containerized services
`at-deploy` provisions on a machine of its own (no image, no port, no `services
up`): it is a plain HTTPS API AT calls FROM the process that is already
running, the way a weather API or a payment gateway would be — "serviço
interno" in the sense that matters here is that its credential and its switch
are the folder's own, never a container's.

**This module owns the CALL and the CRITERIA; `at.core.assist` owns the
DECISION.** The prototype that proved the idea (`jev-test/slang_dispatch.py`)
hard-coded its own Portuguese descriptions of each action and table; this one
does not, because AT already has a place those descriptions would drift from —
`tables.ACTIONS`, the declared tables, and the vocabulary the deterministic
matcher reads first. The criteria built here say, for every option, which words
are ALREADY read without Jev at all (the vocabulary's own synonyms), so the
model is asked to judge only what is left outside them — gíria, jargão, a way of
saying it the product does not know yet. Judging the three TIERS of what to do
with the answer, rewriting a sentence, asking for confirmation — none of that is
here; a service is a call and a shape, not a policy.

**The client is INJECTABLE, and the default is the one that reaches a socket.**
`transport` is the seam: the suite passes a FAKE one and asserts nothing about
the network, and the one line that owns a real request (`_post`) is the only
place `urllib` is named.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from at import i18n
from at.core import permissions, tables
from at.data import schema
from at.nlu import vocabulary
from at.nlu.normalizer import fold

# The Cofre's scope for this credential (`at.core.secrets.seal`'s `service`) —
# a name like any other service's (`notifier`, `cofre`, `backup`), and this
# module's own to carry because it is the one that knows what it is for.
SERVICE = "jev"

# TypeSafe's System One endpoint and the model this product speaks to. Named
# here because this is the one module that reaches either.
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

# How long a call waits before this process stops waiting on it — the same
# number `notifier.TIMEOUT` reads a push against, for the same reason: a
# sentence somebody typed is not left hanging on a service that did not answer.
TIMEOUT = 10.0

# What a Choice answers when neither option is what the phrase means. It is not
# a canonical of the product — no table, field or action is named `none` — so it
# cannot collide with one, the same promise `matcher.PARTICLE` makes for the
# segmentation.
NONE = "none"

ACTION = "action"
TABLE = "table"

# Os TRECHOS: qual palavra da frase É a ação e qual É a tabela. O
# `choice` de `action`/`table` diz o CANÔNICO que a frase quer dizer; estes
# dizem ONDE, na frase, ele está escrito — que é o que o código precisa para
# gastar a palavra e não deixá-la vazar para os argumentos (o que o TypeSafe
# recomenda: o código levanta os trechos, o modelo ESCOLHE o pretendido, e o
# código copia). Sem isto, a gíria da ação vira `text` da tarefa.
ACTION_SPAN = "action_span"
TABLE_SPAN = "table_span"

# A DATA e a HORA, quando a frase as escreve como PALAVRA e não como campo.
# "me lembrar de imprimir passagens hoje 18h" não tem "data" nem "horário": o
# Jev é quem diz que "hoje" é a data e "18h" a hora, e o código planta a
# palavra-campo antes de cada uma — depois disso o matcher lê uma frase comum.
DAY_SPAN = "day_span"
TIME_SPAN = "time_span"


@dataclass(frozen=True)
class Decision:
    """What Jev answered about one phrase: an action, a table, each with its
    own confidence — never a row, never a value, never a thing that runs.

    `confidence` is the WEAKER of the two, because a guess is only as good as
    its least certain half: an action Jev is sure of over a table it is not is
    still a demand this product cannot place anywhere with any confidence.

    **`action_span` e `table_span` são ONDE a frase diz isso** — as palavras
    que carregam a ação e a tabela, ou `NONE` quando a frase não as escreve (o
    comando vem do sentido, não de uma palavra). É o que o código gasta antes
    de ler os argumentos.

    **`day_span` e `time_span` são a mesma coisa para a DATA e a HORA.** Elas
    não são canônicos de ação nem de tabela: são as palavras que dizem QUANDO e
    A QUE HORAS — `hoje`, `sexta`, `18h` —, e o código planta a palavra-campo da
    tabela antes de cada uma, para o matcher ler uma frase comum (`at.core.assist`,
    `_ground`). `NONE` quando a frase não nomeia nenhuma das duas.
    """

    action: str
    action_confidence: float
    table: str
    table_confidence: float
    action_span: str = ""
    table_span: str = ""
    day_span: str = ""
    time_span: str = ""

    @property
    def confidence(self) -> float:
        return min(self.action_confidence, self.table_confidence)


class JevError(Exception):
    """The call failed, timed out, or answered a shape this door does not
    read — never raised past `at.core.assist`, which decides what a service
    that did not answer is worth (the same rule `notifier.publish` answers
    to its own caller instead of raising over)."""


# `(url, body, headers, timeout) -> raw response bytes`, or raises `JevError`.
# The one seam between this module and the network, and the one a test swaps.
Transport = Callable[[str, bytes, dict[str, str], float], bytes]


def _post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> bytes:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        error.close()
        raise JevError(f"{error.code}: {detail}") from None
    except (urllib.error.URLError, OSError) as error:
        raise JevError(str(getattr(error, "reason", error))) from None


def decide(
    text: str,
    *,
    language: str,
    api_key: str,
    transport: Transport | None = None,
) -> Decision:
    """Ask Jev which action and which table the phrase means, each with a
    confidence — grounded in the SAME closed vocabularies the deterministic
    matcher already reads, so the model is asked about nothing the matcher
    would have resolved for free.

    Raises `JevError` for anything that is not a usable answer: the network,
    the key, the service's own refusal, or a shape this reader does not know.
    What that is WORTH — fall back, ask, or apply — is never decided here.
    """
    post = transport if transport is not None else _post
    spans = _span_criteria(text, language)
    body = json.dumps(
        {
            "state": text,
            "model": MODEL,
            "questions": {
                ACTION: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.action.instructions", language),
                    "criteria": _action_criteria(language),
                },
                TABLE: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.table.instructions", language),
                    "criteria": _table_criteria(language),
                },
                # ONDE a frase diz o que diz. O código levanta os trechos, o
                # Jev escolhe o pretendido, e o código copia (a recomendação
                # do TypeSafe para valor que o modelo não pode devolver).
                ACTION_SPAN: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.span.action", language),
                    "criteria": spans,
                },
                TABLE_SPAN: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.span.table", language),
                    "criteria": spans,
                },
                # Quando e a que horas, na mesma forma: o Jev aponta a palavra,
                # o código copia e planta a palavra-campo da tabela antes dela.
                DAY_SPAN: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.span.day", language),
                    "criteria": spans,
                },
                TIME_SPAN: {
                    "type": "choice",
                    "instructions": _text("assist.criteria.span.time", language),
                    "criteria": spans,
                },
            },
        }
    ).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    raw = post(ENDPOINT, body, headers, TIMEOUT)
    return _read(raw)


def _span_criteria(text: str, language: str) -> dict[str, str]:
    """Os TRECHOS candidatos: uma entrada por palavra da frase, mais o
    `NONE`. A palavra que o vocabulário conhece vem com o seu canônico; a que
    ele não conhece — a gíria — vem como está, que é exatamente o que o Jev
    tem de reconhecer.
    """
    pairs = vocabulary.of(language)
    seen: dict[str, str] = {}
    for word in text.split():
        if word in seen:
            continue
        known = pairs.get(word) or pairs.get(fold(word))
        seen[word] = f"«{word}»" + (f" (= {known})" if known else "")
    seen[NONE] = _text("assist.criteria.span.none", language)
    return seen


def _read(raw: bytes) -> Decision:
    try:
        payload = json.loads(raw.decode("utf-8"))
        answers = payload["answers"]
        action = answers[ACTION]
        table = answers[TABLE]
        return Decision(
            action=str(action["choice"]),
            action_confidence=float(action["confidence"]),
            table=str(table["choice"]),
            table_confidence=float(table["confidence"]),
            # Um `answers` sem as perguntas de trecho (um transporte antigo, um
            # servidor que ainda não as conhece) responde `NONE`: a leitura é a
            # mesma, só sem saber ONDE — e o código não gasta trecho nenhum.
            action_span=str(answers.get(ACTION_SPAN, {}).get("choice", NONE)),
            table_span=str(answers.get(TABLE_SPAN, {}).get("choice", NONE)),
            # Mesma tolerância dos trechos acima: um servidor que ainda não
            # conhece as perguntas de data e hora responde `NONE`, e a leitura
            # segue sem elas — nenhuma palavra-campo é plantada.
            day_span=str(answers.get(DAY_SPAN, {}).get("choice", NONE)),
            time_span=str(answers.get(TIME_SPAN, {}).get("choice", NONE)),
        )
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        raise JevError(f"unreadable answer: {error}") from None


# ------------------------------------------------------------- the grounding ---
#
# A criterion that said only the label and its synonyms measured WORSE than the
# prototype's hand-written one did (the fatia's own "medição real": the same
# eight reference phrases, run against the live Jev, matched the prototype's
# tier on 3 of 8 before this — the words a person already types are not, by
# themselves, a description of what an option MEANS). What the prototype had
# that a bare label does not is a sentence of MEANING, and this module has one
# too, in two different homes depending on what the option is:
#
# - the six engine actions are a CLOSED, product-wide set (`tables.ACTIONS`),
#   so their meaning is written once, as `i18n` text no person ever reads
#   (`assist.criteria.action.desc.*`) — the same shelf the instructions
#   already sit on;
# - a table's meaning is ALREADY written, in `desc` (`data/schema/<table>
#   .json`) — the architecture's own prose, which `schema.py`'s docstring
#   already marks as "no text a person reads" (never `i18n`, never a label).
#   Jev is not a person; reusing it here costs nothing new to maintain and
#   extends to an instance's own table the moment its declaration carries one.

def _action_criteria(language: str) -> dict[str, str]:
    # The LABEL is `permissions.action_label`'s own — it reads `i18n.tr`
    # ambient, like every label in the product — and it agrees with
    # `language` in every caller `decide` has today (`language` is always
    # `nlu.propose`'s own, which already matches the active code). The
    # DESCRIPTION and the EXAMPLES beside it are drawn for `language` itself
    # (`_text`, `_synonyms`), so the day the two may legitimately differ is
    # the day this label is the one piece still worth a second look.
    return _criteria(
        tables.ACTIONS,
        (permissions.action_label(action) for action in tables.ACTIONS),
        (_text(f"assist.criteria.action.desc.{action}", language) for action in tables.ACTIONS),
        language,
        "assist.criteria.none.action",
    )


def _table_criteria(language: str) -> dict[str, str]:
    declared = schema.tables()
    names = tuple(declared)
    return _criteria(
        names,
        (tables.table_name(name) for name in names),
        (declared[name].get("desc") for name in names),
        language,
        "assist.criteria.none.table",
    )


def _criteria(
    canonicals: Iterable[str],
    labels: Iterable[str],
    descriptions: Iterable[str | None],
    language: str,
    none_key: str,
) -> dict[str, str]:
    known = _synonyms(language, canonicals)
    criteria = {
        canonical: _option(label, description, known.get(canonical, ()), language)
        for canonical, label, description in zip(canonicals, labels, descriptions)
    }
    criteria[NONE] = _text(none_key, language)
    return criteria


def _option(
    label: str, description: str | None, examples: tuple[str, ...], language: str
) -> str:
    said = f"{label}: {description}" if description else label
    if not examples:
        return said
    return _text("assist.criteria.option", language, said=said, examples=", ".join(examples))


def _text(key: str, language: str, **kw: str) -> str:
    """`key`'s text in EXACTLY `language`, never the ambient active one.

    `i18n.tr` reads the process's active language, which is right for a
    person — one process serves one reader at a time. A criterion grounded
    for `language` must not mix in whatever happens to be active instead: the
    vocabulary's own synonyms are already drawn by the explicit `language`
    (`vocabulary.of`), and the text beside them has to agree.
    """
    said = i18n.text(key, language)
    return said.format(**kw) if kw else said


def spoken(canonical: str, language: str) -> str | None:
    """The first word THIS language already reads as `canonical`, or `None`.

    It is what `at.core.assist` plants back into a sentence when it rewrites
    one: the word is already in the deterministic vocabulary, so the matcher
    reads it with no help from this module the second time around.
    """
    for expression, mapped in vocabulary.of(language).items():
        if mapped == canonical:
            return expression
    return None


def _synonyms(language: str, canonicals: Iterable[str]) -> dict[str, tuple[str, ...]]:
    """Every word THIS language already reads as one of `canonicals`, grouped —
    the words a person's phrase in them would not need Jev for at all."""
    wanted = set(canonicals)
    found: dict[str, list[str]] = {}
    for expression, canonical in vocabulary.of(language).items():
        if canonical in wanted:
            found.setdefault(canonical, []).append(expression)
    return {canonical: tuple(examples) for canonical, examples in found.items()}
