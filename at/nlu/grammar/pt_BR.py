"""The Portuguese grammar — where the language costs more than English.

A number in Portuguese agrees with what it counts, so one `um` is `um` and `uma`,
one two is `dois` and `duas`, one half is `meio` and `meia`. And the same word
lives in two domains at once: `duas` is two and is two o'clock; `meia` is half —
of a dozen, of a kilo — and is half past, which is half past SOME hour. What
separates the two readings is the type the field declares: a number field
answers `2`, an instant field answers `02:00`, and `meia` alone in an instant
field has no hour to be half past — so it comes back as a question instead of
becoming a guess.

`sexta` costs the same way: it is a weekday, and in a day field that is what it
says. Nothing here reads it as the sixth of anything.

The readers below are the grammar's contract (`read_day`, `read_instant`,
`read_time`, `read_number`), and each answers what fits the type — `day` leaves
as the writer's local day, `instant` as a point in time in UTC, and `time` as the
clock hour alone (`HH:MM`).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from at.nlu.grammar import clock, clock_text, day_of_month, next_weekday, number_of
from at.nlu.normalizer import fold, folded
from at.nlu.reading import Question, Reading, Refused, Residue, Value

# The week starts on Monday, as it does for the calendar both languages share.
# The two spellings live side by side because both are written: `sexta` and
# `sexta-feira` fold to different keys, and both are the same Friday.
WEEKDAYS = folded({
    "segunda": 0, "segunda-feira": 0,
    "terça": 1, "terça-feira": 1,
    "quarta": 2, "quarta-feira": 2,
    "quinta": 3, "quinta-feira": 3,
    "sexta": 4, "sexta-feira": 4,
    "sábado": 5,
    "domingo": 6,
})

# `amanhã` is the day that comes; `hoje` is the day the clock is saying — and
# `hj`, the way it is written short, is the same day the clock is saying. It
# lives here and not in the assist's vocabulary because a spoken day is read by
# the GRAMMAR: the assist plants the field word and hands the span over as it
# was written, so a `once` reminder made from "…passagens hj 19h" only lands a
# date if `read_day` knows the abbreviation (2026-10-05, the defect).
RELATIVE = folded({"hoje": 0, "hj": 0, "amanhã": 1})

# As frases de data que só se leem INTEIRAS — o matcher as mantém juntas
# (`grammar.phrases`) e o `read_day` as lê. `depois de amanhã` era lida como
# `amanhã` mais o texto "depois"; `semana que vem` era `semana` (a frequência
# de um lembrete) mais "que vem". A contagem é de DIAS a partir de hoje, e a
# semana que vem é a próxima segunda, que é como uma pessoa a nomeia.
PHRASES = (
    "depois de amanhã",
    "amanhã de manhã",
    "amanhã de tarde",
    "amanhã de noite",
    "amanhã à tarde",
    "amanhã à noite",
    "hoje de manhã",
    "hoje de tarde",
    "hoje de noite",
    "hoje à tarde",
    "hoje à noite",
    "de manhã",
    "à tarde",
    "à noite",
    "de tarde",
    "de noite",
    "semana que vem",
    "próxima semana",
    "segunda que vem",
    "terça que vem",
    "quarta que vem",
    "quinta que vem",
    "sexta que vem",
    "sábado que vem",
    "domingo que vem",
    "fim de semana",
    "final de semana",
    "da manhã",
    "da tarde",
    "da noite",
)

# The numbers that are written out. One entry per form — the gender changes the
# word and never the value, and `duas` and `dois` are the same two.
NUMBERS = folded({
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18,
    "dezenove": 19, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
    "cem": 100, "cento": 100,
})

# `meia` is half: of a dozen, of a kilo, of an hour. In a number field it is 0.5 —
# and in an instant field it is nothing alone, because half an hour is half of
# some hour.
HALVES = folded({"meia": 0.5, "meio": 0.5})

# The word for half of the hour — `meia`, and not `meio`: `meio` is half a kilo,
# and an hour has no masculine. It is the one that asks, alone in an instant
# field, because half an hour is half of some hour.
HALF_PAST_WORD = fold("meia")

# The hours the language writes whole, with no hour left to complete.
FIXED = folded({
    "meia-noite": (0, 0),
    "meio-dia": (12, 0),
    "meio-dia e meia": (12, 30),
    # A ARTIGO QUE A HORA INTEIRA PEDE: `ao meio-dia`, `à meia-noite`. O `à` cai
    # no `fold` para o mesmo `a` do artigo, e por isso ele NÃO pode ser uma
    # partícula que anuncia hora — `a 3 dias` é uma contagem. A hora inteira é
    # lida com o artigo junto, e é aqui que as duas formas moram.
    "ao meio-dia": (12, 0),
    "a meia-noite": (0, 0),
})

# `14:30` and `14h30`; `14h` too, because that is how a whole hour is written.
CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
CLOCK_H = re.compile(r"^(\d{1,2})h(\d{2})?$")
# `dia 3` and `dia três`: the day of the month, which without the month is the
# next one to come.
DAY_OF_MONTH = re.compile(r"^dia (.+)$")
# `duas e meia`: the hour that was said, and the half of it.
HALF_PAST = re.compile(r"^(.+) e mei[ao]$")
# `9 da manhã`, `3 da tarde`, `8 da noite`: a hora dita pelo PERÍODO em que ela
# cai, que é como a língua fala de manhã cedo e de noite sem dizer o vinte e
# uma. O período diz o que a hora sozinha não diz — e é a única leitura em que
# `8 da noite` é vinte e não oito.
PART_OF_DAY = re.compile(r"^(.+) d[ae] (manha|tarde|noite)$")

# The comma is the decimal separator here; the point is of thousands, and
# thousands are not read.
DECIMAL = ","

# As palavras de INTERVALO. Elas não nomeiam um valor — dizem COMO o valor que
# vem depois se compara ao que a linha guarda: `até sexta` é o que for menor ou
# igual a sexta, `desde segunda` o que for maior ou igual. Sem palavra alguma, o
# valor é exato. É o que separa "listar as de hoje" de "listar as de até sexta".
RANGES = folded({
    "até": "<=",
    "desde": ">=",
    "a partir de": ">=",
})

# A mais LONGA primeiro: `a partir de` não pode virar `a` seguido de sobra.
_INTERVALS = tuple(sorted(RANGES, key=len, reverse=True))


def _interval(text: str) -> tuple[str, str]:
    """O `(op, resto)` de uma frase: a palavra de intervalo que a abre, e o que
    sobra — ou `("=", texto)` quando não há nenhuma."""
    spelled = fold(text)
    if spelled in RANGES:
        return RANGES[spelled], ""
    for word in _INTERVALS:
        if spelled.startswith(f"{word} "):
            return RANGES[word], spelled[len(word) + 1:]
    return "=", spelled


def _count(text: str) -> int | float | None:
    """The number a word or a numeral names.

    It is the reading the three domains share: the same `duas` is worth two in a
    number field, is the hour two in an instant field, and is the day two behind
    `dia duas`, which nobody writes but which the rule need not forbid.
    """
    spelled = fold(text)
    if spelled in NUMBERS:
        return NUMBERS[spelled]
    if spelled in HALVES:
        return HALVES[spelled]
    return number_of(spelled, DECIMAL)


# A FRASE COMPOSTA, e o que ela nomeia. `depois de amanhã` é o dia que vem
# depois do que vem; a semana que vem é a próxima segunda-feira, que é como uma
# pessoa a conta; o fim de semana é o sábado que vem. Nenhuma delas é uma
# palavra — é por isso que elas vivem em `PHRASES`, e o matcher as mantém
# juntas antes de qualquer leitura.
COMPOSED = folded({
    "depois de amanhã": ("days", 2),
    "semana que vem": ("monday", 1),
    "próxima semana": ("monday", 1),
    "fim de semana": ("saturday", 0),
    "final de semana": ("saturday", 0),
    # `sexta que vem` é a sexta da semana que vem, e não a que vem primeiro:
    # é como a língua separa `sexta` (a próxima) de `sexta que vem` (a de
    # depois). A segunda-feira dita numa segunda é disto o caso mais claro.
    "segunda que vem": ("weekday-next", 0),
    "terça que vem": ("weekday-next", 1),
    "quarta que vem": ("weekday-next", 2),
    "quinta que vem": ("weekday-next", 3),
    "sexta que vem": ("weekday-next", 4),
    "sábado que vem": ("weekday-next", 5),
    "domingo que vem": ("weekday-next", 6),
    # O PERÍODO DO DIA nomeia o DIA, e não a hora (20/10/2026): um campo de dia
    # guarda um dia, e `hoje de manhã` é hoje. A hora que o período sugere
    # (nove da manhã?) é a que esta camada não inventa — o dia é o que a frase
    # diz sem dúvida, e é só ele que sai. Sozinho, um período sem dia é hoje.
    "hoje de manhã": ("days", 0),
    "hoje de tarde": ("days", 0),
    "hoje de noite": ("days", 0),
    "hoje à tarde": ("days", 0),
    "hoje à noite": ("days", 0),
    "amanhã de manhã": ("days", 1),
    "amanhã de tarde": ("days", 1),
    "amanhã de noite": ("days", 1),
    "amanhã à tarde": ("days", 1),
    "amanhã à noite": ("days", 1),
    "de manhã": ("days", 0),
    "de tarde": ("days", 0),
    "de noite": ("days", 0),
    "à tarde": ("days", 0),
    "à noite": ("days", 0),
})

# A CONTAGEM RELATIVA: `daqui a 3 dias`, `em duas semanas`, `dentro de 5 dias`.
# O número é o que a palavra diz, e a unidade é a da palavra ao lado. `em` sozinho
# também é contagem — `em 2 dias` —, e nada mais nesta língua começa assim num
# campo de dia.
COUNTED = re.compile(r"^(?:daqui a|daqui|em|dentro de|faz) (.+) (dias?|semanas?)$")

# As aberturas de uma contagem — o matcher as mantém juntas com o número e a
# unidade (`grammar.spans`), porque `daqui`, `a`, `3` e `dias` separados não são
# uma data: são duas partículas, um número e um texto. A leitura é quem confirma
# que a janela é uma data; uma abertura comum no meio do texto (`em casa`) fica
# como estava.
CONNECTORS = tuple(fold(word) for word in ("daqui", "em", "dentro", "faz"))

# As marcas de relógio: a palavra que já é uma hora inteira, e a partícula que
# anuncia a hora escrita em número (`às 18`). O `18h` e o `14:30` não precisam
# delas — a forma é a marca —, e um número solto sem nenhuma tampouco é hora.
CLOCK_MARKERS = tuple(fold(word) for word in (
    "meia-noite", "meio-dia", "às", "as", "manhã", "tarde", "noite",
))
# As que anunciam a hora sem serem ela: `às 18` — e a palavra sai junto com o
# número, porque ela só estava ali para dizer que o número era uma hora. O `as`
# sem acento fica de fora: ele é `as duas caixas` antes de ser `as 18`, e só a
# partícula escrita com o acento — a que a língua usa para a hora — anuncia.
ANNOUNCERS = tuple(fold(word) for word in ("às", "ao"))


def _of_day(hour: int, period: str) -> int:
    """A hora dita pelo PERÍODO em que ela cai.

    `8 da noite` é vinte, `3 da tarde` é quinze, `9 da manhã` é nove. A regra é
    a da língua: o período vale para as horas que ele nomeia — de 1 a 11 na
    manhã e na tarde, de 1 a 11 na noite e meia-noite —, e uma hora que já é o
    vinte e um dito por extenso (`21 da noite` é raro mas não é outro dia) fica
    como está: o período não a soma duas vezes.
    """
    if period == "manha":
        return hour
    return hour + 12 if hour < 12 else hour


def _composed(spelled: str, today) -> "date":
    """O dia que a frase composta nomeia: uma contagem de dias, ou a próxima
    vez que a semana chega naquele dia (`semana que vem` é a próxima segunda)."""
    kind, count = COMPOSED[spelled]
    if kind == "days":
        return today + timedelta(days=count)
    if kind == "weekday-next":
        return next_weekday(today, count) + timedelta(days=7)
    weekday = WEEKDAYS["segunda" if kind == "monday" else "sabado"]
    # A próxima ocorrência, e a semana que vem é a seguinte à próxima: uma
    # segunda-feira dita numa segunda é HOJE, e "semana que vem" é a de depois.
    nxt = next_weekday(today, weekday)
    return nxt + timedelta(days=7) if count else nxt


def read_day(text: str, now) -> Reading:
    """`hoje`, `amanhã`, `sexta` e `dia 3` — e o intervalo que os abre
    (`até sexta`, `desde segunda`): a day said in Portuguese."""
    op, spelled = _interval(text)
    if not spelled:
        return Residue(text)
    if spelled in RELATIVE:
        return Value((now.date() + timedelta(days=RELATIVE[spelled])).isoformat(), op)
    if spelled in COMPOSED:
        return Value(_composed(spelled, now.date()).isoformat(), op)
    if spelled in WEEKDAYS:
        return Value(next_weekday(now.date(), WEEKDAYS[spelled]).isoformat(), op)
    match = COUNTED.match(spelled)
    if match:
        count = _count(match.group(1))
        if count is None:
            return Residue(text)
        days = int(count) * (7 if match.group(2).startswith("semana") else 1)
        return Value((now.date() + timedelta(days=days)).isoformat(), op)
    match = DAY_OF_MONTH.match(spelled)
    if match:
        count = _count(match.group(1))
        if count is None:
            # `dia` and a word that is not a number: not a date.
            return Residue(text)
        if not isinstance(count, int):
            raise Refused("nlu.error.no_such_day", value=match.group(1))
        return Value(day_of_month(now.date(), count).isoformat(), op)
    return Residue(text)


def read_instant(text: str, now) -> Reading:
    """`14:30`, `14h`, `duas`, `meia-noite`, `duas e meia`: an hour in Portuguese."""
    op, spelled = _interval(text)
    if not spelled:
        return Residue(text)
    if spelled in FIXED:
        hour, minute = FIXED[spelled]
        return Value(clock(now.date(), hour, minute, text), op)
    if spelled == HALF_PAST_WORD:
        # Half an hour of which hour? The question goes back instead of the
        # likeliest reading.
        return Question("nlu.ask.which_hour", text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock(now.date(), count, 30, text), op)
    match = PART_OF_DAY.match(spelled)
    if match:
        said, period = match.group(1), match.group(2)
        minute = 0
        # `duas e meia da tarde` é a meia que o `HALF_PAST` não viu, porque o
        # período vem depois dela.
        half = HALF_PAST.match(said)
        if half:
            said, minute = half.group(1), 30
        count = _count(said)
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock(now.date(), _of_day(count, period), minute, text), op)
    for shape in (CLOCK, CLOCK_H):
        match = shape.match(spelled)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            return Value(clock(now.date(), hour, minute, text), op)
    count = _count(spelled)
    if isinstance(count, int) and 0 <= count <= 23:
        # A number alone in an instant field is the hour it says, with no twelve
        # added and no period supposed. Outside the hours that exist it is not an
        # hour: it comes back as a residue, and not as a guessed period of day.
        return Value(clock(now.date(), count, 0, text), op)
    return Residue(text)


def read_time(text: str, now) -> Reading:
    """`18h`, `18h30`, `18:30`, `duas`, `meia-noite`: a hora-do-dia, as `HH:MM`.

    Lê as MESMAS palavras que `read_instant` — os dois domínios são a mesma
    expressão de relógio — e difere no que devolve: aqui a hora sozinha, sem dia
    e sem fuso, que é o que o `at` de um lembrete guarda. O `now` entra só para
    o contrato dos leitores; uma hora não tem dia para pendurar.
    """
    op, spelled = _interval(text)
    if not spelled:
        return Residue(text)
    if spelled in FIXED:
        hour, minute = FIXED[spelled]
        return Value(clock_text(hour, minute, text), op)
    if spelled == HALF_PAST_WORD:
        return Question("nlu.ask.which_hour", text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock_text(count, 30, text), op)
    match = PART_OF_DAY.match(spelled)
    if match:
        said, period = match.group(1), match.group(2)
        minute = 0
        half = HALF_PAST.match(said)
        if half:
            said, minute = half.group(1), 30
        count = _count(said)
        if not isinstance(count, int):
            return Residue(text)
        return Value(clock_text(_of_day(count, period), minute, text), op)
    for shape in (CLOCK, CLOCK_H):
        match = shape.match(spelled)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            return Value(clock_text(hour, minute, text), op)
    count = _count(spelled)
    if isinstance(count, int) and 0 <= count <= 23:
        return Value(clock_text(count, 0, text), op)
    return Residue(text)


def read_number(text: str, now) -> Reading:
    """`3`, `3,5`, `duas`, `meia`, `duas e meia`: a number in Portuguese."""
    op, spelled = _interval(text)
    if not spelled:
        return Residue(text)
    match = HALF_PAST.match(spelled)
    if match:
        count = _count(match.group(1))
        if not isinstance(count, int):
            return Residue(text)
        # `duas e meia` is 2.5 — the same pair of words that an instant field
        # reads as half past two. The type is what decides.
        return Value(count + 0.5, op)
    count = _count(spelled)
    if count is None:
        return Residue(text)
    return Value(count, op)
