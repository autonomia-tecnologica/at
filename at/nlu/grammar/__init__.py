"""The date, the time and the number, per language — code, and never a table.

The normalizer of item 15 is three pieces and this is the third. The slang and
jargon map is **data**, and it is the vocabulary packed beside the `i18n` blocks
(slice 5). The mechanical tolerance is **algorithm** (slice 5). What is left —
and it is the piece that decides what a word means — is this: the **grammar**,
which is code, one module per language, because here a word does not mean
anything alone. `meia` is half a dozen and is half past; `duas` is two and is two
o'clock; `sexta` is a weekday. The declared type of the field is what tells them
apart, and where it does not, the phrase is asked back.

Each language is a module beside this one, named by the very code the product
already calls it (`i18n.SUPPORTED`) — which is why the dispatch below is a name
and not a list. The two are written with the same shape so a reader can read one
against the other: `read_day`, `read_instant` and `read_number` are the whole
contract, and `read()` is what picks them. What the languages have in common is
not a rule of any language — the Gregorian calendar, the clock, the number a
numeral spells — so it lives here, and neither language writes a second calendar
of its own. The fold that compares a phrase to the language's own words is not
here: it is the product's one fold, and it lives with the rest of the mechanical
tolerance, in `at.nlu.normalizer`.
"""

from __future__ import annotations

import importlib
import re
from datetime import date, datetime, time, timedelta
from typing import cast

from at import i18n
from at.core import tables
from at.nlu.normalizer import fold
from at.nlu.reading import Refused, Residue, Value

# The readers every language's grammar must carry, keyed by the kind a field
# declares. This dict is the contract between this module and the language
# modules — the reason `read_day` and `read_number` can be called by name — and
# the whole of what the grammar answers in.
#
# `time` é a HORA-DO-DIA (`18:00`), e não o `instant` que o `day` completa: o
# lembrete guarda a que horas toca (`at`, uma lista), e a data dele mora noutro
# campo — ler `18h` como um ponto em UTC daria a hora de HOJE à hora que não tem
# dia. Os dois leem os mesmos números e as mesmas palavras; o que muda é o que
# sai.
KINDS = {
    "day": "read_day",
    "instant": "read_instant",
    "time": "read_time",
    "number": "read_number",
}


def of(language: str):
    """The grammar of a language, as the module that holds it.

    A language the product does not speak reads in the source language, which is
    where `i18n` already falls back to: a translation that lags must not leave a
    sentence unreadable.
    """
    code = language if language in i18n.SUPPORTED else i18n.SOURCE
    return importlib.import_module(f"{__name__}.{code}")


def read(language: str, kind: str):
    """The reader of a kind in a language — the one door to the grammar.

    `kind` is what the field declares: `day`, `instant` or `number`, and the
    whole of what the grammar answers in. A kind no reader answers to is a defect
    in whoever asked, and it is loud instead of becoming a residue.
    """
    name = KINDS.get(kind)
    if name is None:
        raise ValueError(f"unknown kind: {kind}")
    return getattr(of(language), name)


def spans(
    language: str, folded: list[str], now: datetime | None = None
) -> list[tuple[int, int]]:
    """Os trechos de data que o matcher não pode picar — `(início, tamanho)`.

    São as frases que a linguagem declara (`phrases`) mais as que só se leem
    inteiras por serem um número contado: `em duas semanas`, `daqui a 3 dias`.
    A segunda classe não cabe numa lista, porque o número muda; ela é
    reconhecida pelo que a linguagem declara como ABERTURA (`CONNECTORS`) e
    confirmada pelo próprio leitor de dia — a janela só fica junta quando
    `read_day` a lê inteira, e uma abertura comum no meio do texto (`em casa`)
    não vira data porque não se lê como uma.

    A maior janela vence em cada abertura: `daqui a 3 dias` inteira, e não
    `daqui a 3`.
    """
    found = _phrases(language, folded)
    module = of(language)
    openings = getattr(module, "CONNECTORS", ())
    reader = read(language, "day")
    moment = now if now is not None else datetime.now()
    for start in range(len(folded)):
        if not _opens(openings, folded, start):
            continue
        longest = min(MAX_PHRASE, len(folded) - start)
        for size in range(longest, 1, -1):
            piece = " ".join(folded[start:start + size])
            if isinstance(_read_quietly(reader, piece, moment), Value):
                found.append((start, size))
                break
    return sorted(found, key=lambda span: span[1], reverse=True)


def _opens(openings, folded: list[str], start: int) -> bool:
    """Se uma das aberturas declaradas começa em `start`."""
    for opening in openings:
        words = opening if isinstance(opening, tuple) else (opening,)
        if tuple(folded[start:start + len(words)]) == tuple(words):
            return True
    return False


def phrases(language: str) -> tuple[str, ...]:
    """As FRASES de data que a linguagem reconhece INTEIRAS, da mais longa para a
    mais curta — o que o matcher precisa para não picá-las palavra a palavra.

    Uma frase composta (`final da semana que vem`) só se lê se chegar inteira ao
    leitor: separada, `semana` vira a frequência de um lembrete e as partículas
    (`da`, `que`) a picam. O matcher pergunta aqui os trechos a manter juntos, e
    `read_day` os lê. Uma linguagem que não declara frase nenhuma responde vazio.
    """
    listed = getattr(of(language), "PHRASES", {})
    return tuple(sorted(listed, key=lambda phrase: len(phrase.split()), reverse=True))


def split(
    language: str, kind: str, text: str, now: datetime | None = None
) -> tuple[str, str] | None:
    """A data (ou a hora) escrita DENTRO de um trecho, e o texto que a cerca.

    Não é a leitura de uma frase: é a leitura de um trecho que a frase carrega
    — `comprar pão amanhã` é o título e a data, e `imprimir passagens hoje 18h`
    é o título, a data e a hora. Quem não separa os dois grava o título com a
    data colada dentro ("comprar pão amanhã"), e é o defeito que isto fecha.

    **A ordem é a da frase, e a expressão mais LONGA vence**: os trechos são
    varridos do fim para o começo (é onde a pessoa põe o quando), uma janela
    de até `MAX_PHRASE` palavras é tentada da maior para a menor, e o primeiro
    que o leitor do `kind` lê INTEIRO é o que vale. O `kind` é o do campo que
    recebe o valor — `day` para o prazo, `time` para o horário de um lembrete
    —, e um leitor que devolve `Residue` (ou pergunta, ou recusa) não achou
    nada: o trecho fica como está, e o texto não é adivinhado.

    Responde `(antes, valor)` com o texto sem a expressão, ou `None` quando
    nenhuma palavra do trecho é a data/hora que o campo procura.
    """
    reader = read(language, kind)
    moment = now if now is not None else datetime.now()
    words = text.split()
    folded = [fold(word) for word in words]
    # A EXPRESSÃO COMPOSTA QUE A FRASE PARTE (20/10/2026): `depois de amanhã`
    # são três palavras, e o matcher já gastou o `amanhã` delas como a data —
    # o que sobra aqui é `depois de`, e a expressão inteira vence. As frases
    # que a linguagem declara em `PHRASES` são lidas JUNTAS primeiro; a janela
    # solta vem depois, e não passa por cima delas.
    kept = spans(language, folded, moment)
    for start, size in kept:
        piece = " ".join(words[start:start + size])
        reading = _read_quietly(reader, piece, moment)
        if isinstance(reading, Value):
            rest = " ".join([*words[:start], *words[start + size:]]).strip()
            return rest, cast(str, reading.value)
    longest = min(MAX_PHRASE, len(words))
    for size in range(longest, 0, -1):
        for start in range(len(words) - size, -1, -1):
            if (start, size) in kept:
                continue
            piece = " ".join(words[start:start + size])
            # A HORA PRECISA DE MARCA DE RELÓGIO (20/10/2026): um número
            # solto no meio do texto não é uma hora — "comprar 2 pães" perdia
            # o `2` para as duas da manhã, e "revisar o item 5" perdia o `5`.
            # A hora que a pessoa ESCREVE vem com o relógio junto (`18h`,
            # `18:30`, `meio-dia`) ou logo atrás da partícula que a anuncia
            # (`às 18`, `at 6`); fora disso, é contagem, e contagem é texto.
            # Quando é a partícula que anuncia, ela sai junto com a hora: ela
            # só estava ali para dizer que o número era uma hora.
            if kind == "time" and not _clocked(language, folded, start, size):
                continue
            if kind == "time" and _counted_date(language, words, start, size, moment):
                continue
            reading = _read_quietly(reader, piece, moment)
            if isinstance(reading, Value):
                head = start - 1 if _announced(language, folded, start) else start
                rest = " ".join([*words[:head], *words[start + size:]]).strip()
                return rest, cast(str, reading.value)
    return None


def _announced(language: str, folded: list[str], start: int) -> bool:
    """Se a palavra antes da hora é a partícula que a anuncia (`às`, `at`)."""
    announcers = set(getattr(of(language), "ANNOUNCERS", ()))
    return start > 0 and folded[start - 1] in announcers


def _counted_date(language: str, words: list[str], start: int, size: int, moment) -> bool:
    """Se a janela é uma DATA contada — `daqui a 3 dias`, `em duas semanas`.

    `3 dias` também se lê como três horas num campo de hora, e `daqui a 3
    dias` é uma data, não a hora três. O que decide é a leitura do dia sobre o
    trecho MAIOR, com a abertura junto: se ele lê a contagem inteira, a hora
    não pode tomar o número dela.
    """
    reader = read(language, "day")
    for extra in (1, 2):
        head = start - extra
        if head < 0:
            continue
        piece = " ".join(words[head:start + size])
        if isinstance(_read_quietly(reader, piece, moment), Value):
            return True
    return False


def _clocked(language: str, folded: list[str], start: int, size: int) -> bool:
    """Se a janela diz uma hora com a marca de relógio dela.

    A marca é de três formas: o número escrito com o relógio junto (`18h`,
    `14:30`, `2pm`), a palavra que já é uma hora inteira (`meio-dia`, `noon`),
    e a partícula que anuncia a hora e fica FORA da janela (`às 18`, `at 6`).
    Fora delas, o número é contagem — e contagem é texto.
    """
    keys = set(folded[start:start + size])
    markers = set(getattr(of(language), "CLOCK_MARKERS", ()))
    if keys & markers:
        return True
    if any(CLOCK_LITERAL.match(word) for word in keys):
        return True
    return _announced(language, folded, start)


# O número que traz o relógio junto — `18h`, `18h30`, `14:30`, `2pm`. Um
# número SOLTO não casa: `18` é uma hora num campo de hora, mas no texto é uma
# contagem, e é a marca que diz a diferença.
CLOCK_LITERAL = re.compile(r"^(?:\d{1,2}(?::\d{2}|h\d{0,2})|(?:\d{1,2})(?::\d{2})?(?:am|pm))$")


def _read_quietly(reader, piece: str, moment) -> object:
    """O que o leitor lê, ou `Residue` — uma expressão de data que não existe
    (`dia 32`) não para a busca de outra na mesma frase."""
    try:
        return reader(piece, moment)
    except Refused:
        return Residue(piece)


def _phrases(language: str, folded: list[str]) -> list[tuple[int, int]]:
    """As posições das frases de data que a frase carrega inteiras, da mais
    longa para a mais curta — `depois de amanhã`, `semana que vem`."""
    spans: list[tuple[int, int]] = []
    for phrase in phrases(language):
        words = fold(phrase).split()
        if not words:
            continue
        for start in range(len(folded) - len(words) + 1):
            if folded[start:start + len(words)] == words:
                spans.append((start, len(words)))
    return sorted(spans, key=lambda span: span[1], reverse=True)


# A janela que a data dentro de um trecho pode ocupar — `depois de amanhã` são
# três palavras, `sexta-feira que vem` são três, e nenhuma expressão de data
# desta língua passa disso.
MAX_PHRASE = 4


# ------------------------------------------------------------- the words ---

# The fold that compares a phrase to the language's own words is the product's
# one fold, and it lives in the normalizer beside the rest of the mechanical
# tolerance — the languages import it from there and do not write a second one.

def number_of(text: str, decimal: str) -> int | float | None:
    """The number a written numeral names, or nothing.

    `decimal` is the separator of the language reading it: the same `3,5` is
    three and a half in Portuguese and not a number at all in English, which
    writes `3.5`. Thousands are not read — a separator with three digits behind
    it is as likely to be one, and reading `3.000` as three in Portuguese would
    be a defect dressed up as a feature.
    """
    body = text.strip()
    sign = 1
    if body[:1] in ("-", "+"):
        sign = -1 if body[0] == "-" else 1
        body = body[1:]
    if decimal in body:
        whole, _, part = body.partition(decimal)
        if not whole.isdigit() or not part.isdigit():
            return None
        return sign * float(f"{whole}.{part}")
    if body.isdigit():
        return sign * int(body)
    return None


# ---------------------------------------------------------- the calendar ---

def next_weekday(now: date, weekday: int) -> date:
    """The named weekday: today when today is that day, and the coming one after.

    A week starts on Monday because Python's does — the language names the days
    and this counts them, which is why the count is here and not there.
    """
    return now + timedelta(days=(weekday - now.weekday()) % 7)


def day_of_month(now: date, day: int) -> date:
    """`dia N`: the coming N-th, this month's while it has not gone by.

    A day no month carries — the 32nd — is refused here instead of being looked
    for in a calendar it will never be in.
    """
    if not 1 <= day <= 31:
        raise Refused("nlu.error.no_such_day", value=day)
    year, month = now.year, now.month
    for _ in range(13):
        moment = _date_or_none(year, month, day)
        if moment is not None and moment >= now:
            return moment
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    raise Refused("nlu.error.no_such_day", value=day)


def _date_or_none(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        # This month is too short for that day; the next one may not be.
        return None


# ------------------------------------------------------------- the clock ---

def clock(day: date, hour: int, minute: int, wrote: str) -> str:
    """The instant a local clock time names, written the way §4 writes one.

    The day is the one the phrase hangs from — a clock time with no date on it is
    the writer's today, exactly as `today` is — and the zone is the machine's,
    because that is the zone whoever typed it is in. What leaves is UTC with
    milliseconds, so the same sentence read in São Paulo and in Lisbon is the
    same point in time and the two fields it lands in are comparable.

    An hour or a minute no clock has is refused, naming the phrase as it was
    written: `25:00` is a time expression, and there is no such time.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise Refused("nlu.error.no_such_clock", value=wrote)
    here = datetime.combine(day, time(hour, minute)).astimezone()
    return tables.utc(here)


def clock_text(hour: int, minute: int, wrote: str) -> str:
    """A hora-do-dia a phrase names, written the way the reminder's `at` stores
    one: `HH:MM`, with no day and no zone — a time of day is the same in every
    calendar, and the day it lands on is the row's own (`on_date`, `freq`).

    The refusal is `clock`'s own: `25:00` is a clock expression and no clock has
    it, so it does not become a residue and does not become a guess.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise Refused("nlu.error.no_such_clock", value=wrote)
    return f"{hour:02d}:{minute:02d}"
