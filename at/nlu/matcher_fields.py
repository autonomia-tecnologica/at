"""The fields of a table: what the declaration says, and how a piece is read into one.

Everything here is read off the DECLARATION (`schema`), never off a list of
names: the open `day` field, a list of times, the field a word names, the
closed value a mark carries, and the grammar's reading of one piece of text.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from at.core import tables
from at.data import schema
from at.nlu import grammar, vocabulary
from at.nlu.interpreter import KINDS, resolve
from at.nlu.matcher_segment import PARTICLE, exact_flags
from at.nlu.normalizer import fold
from at.nlu.reading import Question, Reading, Residue, Value

# A palavra que abre o MOTIVO de um encerramento — `motivo`/`reason`, que o
# vocabulário já conhece como campo (`field.json`) e que nem toda tabela
# declara. Aqui ela é lida só como marca de onde o motivo começa; o valor vai
# para a chave `REASON`, e quem o entrega ao fechamento é `at.ui.ask`.
REASON = "reason"


def declared_fields(table: str) -> dict:
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    return fields if isinstance(fields, dict) else {}


def open_day_field(table: str) -> str | None:
    """The `day` field the declaration does NOT fill by itself.

    The rule is read off the DECLARATION and never off a list of names: it is
    the `day` field whose default is null, because a field that declares a value
    is already filled the moment the row is born. `since` declares `today` and is
    out; `deadline` declares `null` and is in — and neither name is written here.
    """
    found = [
        name
        for name, declared in declared_fields(table).items()
        if isinstance(declared, dict)
        and declared.get("type") == "day"
        and declared.get("default") is None
    ]
    return found[0] if len(found) == 1 else None


def list_field(table: str, kind: str) -> str | None:
    """The `list` field whose items are `kind`, if the table declares one.

    Read off the DECLARATION — `"items": "time"` on the reminder's `at` — and
    never off a list of field names, the same rule `open_day_field` follows.
    """
    for name, declared in declared_fields(table).items():
        if (
            isinstance(declared, dict)
            and declared.get("type") == "list"
            and declared.get("items") == kind
        ):
            return name
    return None


def field_word(table: str, marks: list[str | None], start: int) -> str | None:
    """A palavra de CAMPO que abre o trecho, mesmo de um campo que a tabela não
    declara — `motivo` de uma tarefa é o `reason`, e a tarefa não o declara.

    É `field_before` sem o filtro da declaração, e existe por uma razão só: o
    motivo de um encerramento mora no `lifecycle`, não nos campos.
    """
    index = start - 1
    while index >= 0 and marks[index] == PARTICLE:
        index -= 1
    return marks[index] if index >= 0 and marks[index] else None


def reason_before(
    words: list[str], marks: list[str | None], start: int, language: str
) -> bool:
    """Se o trecho em `start` é o MOTIVO que uma palavra da língua anunciou.

    A palavra é lida no vocabulário `reasons` (`porque`, `pois`, `because`), e
    as partículas entre ela e o trecho são saltadas, como em `field_before`:
    `cancela a tarefa 3 por causa de desisti` ainda é o motivo.
    """
    wanted = {fold(word) for word in vocabulary.reasons(language)}
    index = start - 1
    for _ in range(4):
        if index < 0:
            return False
        word = fold(words[index])
        if word in wanted:
            return True
        # Uma palavra que já tem sentido nesta frase — a tabela, a ação — para
        # a busca: o `porque` do motivo vem logo antes dele, e não no começo da
        # frase.
        if marks[index] not in (None, PARTICLE):
            return False
        index -= 1
    return False


def field_before(table: str, marks: list[str | None], start: int) -> str | None:
    """The field the piece at `start` is spoken into, when a word names one.

    The connecting words are stepped over — `com prazo sexta` names the field
    `deadline` — and a word that is not a field of THIS table names nothing.
    """
    index = start - 1
    while index >= 0 and marks[index] == PARTICLE:
        index -= 1
    if index < 0:
        return None
    mark = marks[index]
    return mark if mark and mark in declared_fields(table) else None


def enum_field(table: str, mark: str | None) -> str | None:
    """The field of `table` whose closed vocabulary carries `mark`, if one does."""
    if not mark:
        return None
    for name, declared in declared_fields(table).items():
        if not isinstance(declared, dict):
            continue
        choices = declared.get("enum")
        if isinstance(choices, dict) and mark in choices:
            return name
    return None


def unmistaken(marks: list[str | None], words: list[str], table: str, language: str) -> None:
    """Desfaz a marca que a TOLERÂNCIA inventou e que não serve a esta tabela.

    `limpar` está a uma letra de `limiar` e virava o campo `threshold`, gasto
    em silêncio — a palavra da pessoa sumia do título. A tolerância perdoa o
    dedo que escorregou, e só vale quando o que ela achou tem papel NESTA frase:
    a ação, uma tabela, um campo da tabela, um valor dela. Uma marca que não
    tem papel e não foi escrita por inteiro volta a ser texto.
    """
    exact = exact_flags(words, language)
    for index, mark in enumerate(marks):
        if not mark or mark == PARTICLE or exact[index]:
            continue
        if (
            mark in tables.ACTIONS
            or schema.of(mark)
            or mark in declared_fields(table)
            or enum_field(table, mark) is not None
            or mark == REASON
        ):
            continue
        marks[index] = None


def read_chunk(
    table: str,
    chunk: str,
    named: str | None,
    language: str,
    now: datetime,
) -> tuple[str | None, Reading]:
    """What the grammar reads in one piece, and the field it lands in.

    A piece with a field word before it is read as the type THAT FIELD declares.
    A piece with no field word goes to the `day` field the declaration leaves
    open, and a table that declares none is asked about instead.
    """
    if named is not None:
        declared = schema.field(table, named)
        kind = declared.get("type")
        if kind in KINDS:
            return named, resolve(chunk, kind, language=language, now=now)
        # A LIST whose ITEMS are a kind the grammar reads (`at`, the reminder's
        # hours) is read item by item: `18h, 20h` becomes a list of two times.
        # The declaration is what says the items are times — the type alone
        # cannot, since every `list` field stores one.
        if kind == "list" and declared.get("items") in KINDS:
            return named, list_reading(chunk, cast(str, declared.get("items")), language, now)
        # A field of a type the grammar has no reader for — a text is the
        # example — is not read at all: its content is residue, and residue is
        # what the primary field is for.
        return None, Residue(chunk)

    field = open_day_field(table)
    reading = resolve(chunk, "day", language=language, now=now)
    if field is None and isinstance(reading, Value):
        return None, Question("nlu.ask.which_field", chunk)
    return field, reading


def temporal(
    table: str, chunk: str, language: str, now: datetime, values: dict
) -> tuple[str, bool]:
    """A data/hora escrita DENTRO do texto livre, separada dele e guardada.

    O trecho que o matcher não leu como valor é o texto que a pessoa escreveu —
    e uma pessoa escreve o quando junto dele: "comprar pão amanhã", "imprimir
    as passagens hoje 18h". O campo que recebe a data é o que a DECLARAÇÃO deixa
    aberto (`open_day_field` — o `deadline` de uma tarefa, o `on_date` de um
    lembrete), e a hora é o campo de lista de horas que a tabela declare (`at`
    de um lembrete). Os dois são lidos da declaração, nunca de um nome aqui.

    A ORDEM importa e é a da pessoa: a hora primeiro (ela está no fim do
    trecho, e "hoje 18h" são duas coisas), depois a data. O que a separação
    devolve é o texto sem a expressão, e `True` quando alguma foi guardada —
    um trecho sem data e sem hora volta inteiro, e não há valor nenhum.

    Um valor que a frase JÁ disse não é sobrescrito: o trilho exato venceu, e
    o texto não é onde ler um segundo valor por cima.
    """
    field = open_day_field(table)
    hours = list_field(table, "time")
    rest = chunk
    found = False
    # A HORA É GASTA MESMO SEM CAMPO PARA ELA (20/10/2026): "cria uma tarefa
    # comprar pão às 18h" não tem onde guardar as 18h — a tarefa não declara
    # hora —, e a hora ficava DENTRO do texto ("comprar pão 18h"). Uma hora
    # dita não é parte do título; é quando, e o quando sem campo é descartado,
    # como a cortesia. O que a tabela declara é lido e guardado; o resto sai do
    # texto e não vira valor nenhum.
    split = grammar.split(language, "time", rest, now)
    if split is not None:
        rest, time = split
        found = True
        if hours is not None and hours not in values:
            values[hours] = [time]
    if field is not None and field not in values:
        split = grammar.split(language, "day", rest, now)
        if split is not None:
            rest, day = split
            values[field] = day
            found = True
    return rest, found


def list_reading(
    chunk: str, kind: str, language: str, now: datetime
) -> Reading:
    """A `list` field's value: every comma-separated item, each read as `kind`.

    An item the grammar does not read makes the WHOLE chunk a residue — a list
    half-read is a list guessed at — and residue is what the primary field is
    for. A question an item raises goes back whole, the same as everywhere else.
    """
    items = [piece.strip() for piece in chunk.split(",") if piece.strip()]
    if not items:
        return Residue(chunk)
    values: list[Any] = []
    for piece in items:
        reading = resolve(piece, kind, language=language, now=now)
        if isinstance(reading, Question):
            return reading
        if not isinstance(reading, Value):
            return Residue(chunk)
        values.append(reading.value)
    return Value(values)
