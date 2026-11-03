"""The matcher: a sentence becomes one proposal, and never two.

The grammar reads a phrase WHOLE (`interpreter.resolve`), and nobody writes in
whole phrases: `cria uma tarefa pra sexta` is an action, a table, a connecting
word and a day. What this module does is SEGMENT the sentence and hand piece
after piece to the vocabulary and to the grammar, and to guess at neither.

**The widest window the vocabulary knows wins.** At each position the longest
expression the packed list carries is the one that is spent, which is what keeps
`em andamento` from being read as `em` and something else. What is left goes to
the grammar — the whole piece, never a smaller reading fished out of it — and
what the grammar does not read is **residue**: the words that carry content, and
the field a table declares as `primary` is where they go. The connecting words
are neither: they are particles, spent and silent, which is why `uma` and `pra`
never become a title.

**One action per request.** A sentence naming two actions is refused and not
disambiguated — a batch would be an action of its own the day a batch API
exists, with its own permission — and the same holds for two tables. A sentence
the catalogue does not reach is refused BY NAME, with the reason's key: what does
not resolve is residue, never a guess.

**The field a value lands in comes off the DECLARATION.** A day with a field word
before it (`desde sexta`) goes to that field; a day with no field word on it goes
to the `day` field the declaration does NOT fill by itself — the one whose
default is null — which is how `deadline` is the right field without that name
appearing anywhere below. A table that declares no such field (a `project`, whose
only day is `since`) has nowhere to put a day said alone, and asks which field
holds it instead of picking one.

Nothing here writes and nothing here measures a risk: the interpreter proposes,
the core validates and writes (§4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from at import i18n
from at.core import tables
from at.data import schema
from at.nlu import vocabulary
from at.nlu.matcher_fields import (
    REASON,
    enum_field,
    field_before,
    field_word,
    list_field,
    open_day_field,
    read_chunk,
    reason_before,
    temporal,
    unmistaken,
)
from at.nlu.matcher_request import (
    ROW_ACTIONS,
    TITLED_ACTIONS,
    find_action,
    find_table,
    implied_window,
    said_an_action,
)
from at.nlu.matcher_rows import joined, reference_row, reference_target, take_row, take_title
from at.nlu.matcher_segment import (
    FULL_TABLE_WORDS,
    PARTICLE,
    content_after_the_object,
    demote_fuzzy_actions,
    full_table,
    segmented,
    unspent_runs,
)
from at.nlu.polish import polish_text
from at.nlu.proposal import Proposal
from at.nlu.reading import Question, Refused, Value

# The names this module has always exported (the suite and `at.core.assist` read
# them from here); the code now lives in `matcher_*`, one responsibility each.
__all__ = [
    "FULL_TABLE_WORDS", "PARTICLE", "REASON", "list_field",
    "match", "open_day_field",
]

_Leftover = list[tuple[int, int, list[str]]]


def match(
    text: str,
    *,
    language: str | None = None,
    now: datetime | None = None,
    action: str | None = None,
    table: str | None = None,
) -> Proposal | Question:
    """What one sentence proposes, or the question it comes back as.

    `now` is the clock the grammar hangs its relative phrases from and it is
    injected for the same reason `resolve` injects it: the ruler is
    deterministic. A phrase of a kind that names a value no calendar or clock has
    raises `Refused`, exactly as it does one layer down.

    **`action` e `table` são a leitura PRIMÁRIA** (o Jev, `at.core.assist`):
    quando vêm dadas, o matcher NÃO as procura — ele as usa e lê só os
    ARGUMENTOS (o campo, a data, a linha, o resíduo) do texto. É o que permite
    ao Jev decidir sem reescrever a frase: uma palavra que o vocabulário já lê
    continua sendo GASTA pela segmentação (não vira resíduo), e a gíria que ele
    não lê é o material do campo — o trecho que o Jev apontou já saiu do texto.

    As etapas, em ordem: a segmentação, o pedido (ação e tabela), os valores
    das listas fechadas, o verbo que carrega o valor, a linha nomeada, a
    leitura de cada trecho que sobrou e o resíduo.
    """
    language = language or i18n.active_code()
    now = now if now is not None else datetime.now()

    words = text.split()
    if not words:
        raise Refused("nlu.error.no_action", text=text)

    whole_table, words = full_table(words)
    if not words:
        raise Refused("nlu.error.no_action", text=text)

    marks = segmented(words, language, now)
    demote_fuzzy_actions(marks, words, language)
    action = action if action is not None else find_action(marks, text, language)
    table = table if table is not None else find_table(marks, text, words, action, language, now)
    unmistaken(marks, words, table, language)
    content_after_the_object(marks, table)

    # A value of a closed vocabulary fills the field that carries it. The word is
    # spent either way: `alta` names a priority, it is not content.
    values: dict[str, Any] = {}
    # E COMO cada valor se compara ao que a linha guarda (`ranges`): `até` é `<=`,
    # `desde` é `>=`, e o que não tem palavra de intervalo é exato (`=`, o padrão,
    # e por isso não entra aqui). É o que um `list` lê para filtrar.
    ranges: dict[str, str] = {}
    for mark in marks:
        field = enum_field(table, mark)
        if field is not None:
            values[field] = mark

    spent = _implied_values(table, words, marks, values, language)

    runs = unspent_runs([mark is not None for mark in marks])
    # O ATO QUE O VERBO JÁ DISSE (20/10/2026): dizer o resultado de uma linha
    # que existe é mudá-la (`edit`), e não fechá-la com motivo. O verbo que
    # nomeia um valor de uma lista fechada vale como a ação quando a frase não
    # nomeou outra — `conclui a tarefa 3` é uma edição; `cria uma nota` continua
    # sendo o `create` da palavra dela.
    if spent and action == "create" and not said_an_action(words, language):
        action = "edit"
    row: Any = None
    if action in ROW_ACTIONS:
        named_row = _name_the_row(action, table, words, marks, runs)
        if isinstance(named_row, Question):
            return named_row
        row, runs = named_row

    leftover = _read_pieces(table, action, words, marks, runs, values, ranges, language, now)
    if isinstance(leftover, Question):
        return leftover

    # A pontuação de separação colada ao fim (`nome X,`) não é do texto; o `.` fica.
    residue = joined(leftover, words, marks).strip().rstrip(",:").rstrip()
    primary = schema.primary(table)
    if residue and primary:
        values[primary] = polish_text(table, primary, residue, language) if action == "create" else residue
    # UM PEDIDO QUE NÃO DIZ O QUE CRIAR (20/10/2026): "cria uma tarefa", sozinha,
    # não é uma linha vazia — é uma pergunta. O campo que a pessoa não disse é o
    # PRINCIPAL da tabela, e é o que ela ainda tem de escrever; a resposta vai
    # como a pergunta do matcher (`nlu.ask.what`), e nada é escrito. Um pedido
    # que preencheu outro campo (`cria uma tarefa pra hoje`) sai daqui como
    # proposta, e é a PORTA (`ui.ask`) que pergunta o principal que falta: ele é
    # obrigatório em toda tabela (03/11/2026), e o motor não grava a linha sem ele.
    if action == "create" and primary and not values.get(primary) and not values:
        return Question("nlu.ask.what", tables.label(table, primary))

    return Proposal(
        action=action, table=table, values=values, row=row, ranges=ranges,
        full_table=whole_table,
    )


def _implied_values(
    table: str, words: list[str], marks: list[str | None], values: dict[str, Any],
    language: str,
) -> dict[str, str]:
    """O VERBO QUE CARREGA O VALOR (20/10/2026): "conclui a tarefa 3" diz o que
    fazer com ela, e o valor já está no verbo. O vocabulário `implies` diz a
    palavra e o valor; o campo é o da tabela cuja lista fechada CARREGA esse
    valor — lido da declaração, como `conclui` num `project`, sem o valor
    nele, não significa nada. A palavra é gasta (a marca vira `PARTICLE`), e
    nunca vira texto; o que volta é o que foi dito, por valor.
    """
    implied = vocabulary.implies(language)
    spent: dict[str, str] = {}
    for index, _mark in enumerate(marks):
        # A IMPLICAÇÃO É DE UMA PALAVRA OU DE UMA EXPRESSÃO (20/10/2026): `check
        # off` é duas palavras e vale junto — o verbo fica inteiro ou não fica.
        window = implied_window(implied, words, index)
        if window is None:
            continue
        size, wanted = window
        found = enum_field(table, wanted)
        if found is None:
            continue
        # O VALOR QUE A PALAVRA JÁ NOMEOU (20/10/2026): `complete` está no
        # vocabulário das ações E no das listas fechadas — a segmentação já a
        # leu como `done` —, e o que falta é ela valer como o ATO. A palavra é
        # gasta do mesmo jeito; o valor não é escrito duas vezes.
        if found not in values:
            values[found] = wanted
        for at in range(index, index + size):
            marks[at] = PARTICLE
        spent[wanted] = words[index]
    return spent


def _name_the_row(
    action: str, table: str, words: list[str], marks: list[str | None],
    runs: list[tuple[int, int]],
) -> tuple[Any, list[tuple[int, int]]] | Question:
    """A linha que a ação nomeia, e os trechos que sobram — ou a pergunta.

    The row is chosen among the pieces the grammar is not going to read:
    `dia 3` is a day and stays one, and a bare `3` is a row when — and only
    when — the action asked for one.
    """
    row, runs = take_row(table, words, runs, marks)
    if isinstance(row, Question):
        return row
    if row is None and action in TITLED_ACTIONS:
        # NOMEAR POR TÍTULO (23/10/2026): sem número, o que sobra da frase
        # é buscado no título da tabela.
        row, runs = take_title(table, words, runs)
        if isinstance(row, Question):
            return row
    if row is None:
        return Question("nlu.ask.no_row", tables.table_name(table))
    return row, runs


def _read_pieces(
    table: str, action: str, words: list[str], marks: list[str | None],
    runs: list[tuple[int, int]], values: dict[str, Any], ranges: dict[str, str],
    language: str, now: datetime,
) -> _Leftover | Question:
    """Lê cada trecho que o vocabulário não gastou e devolve o que fica de texto.

    A DATA OU A HORA DENTRO DO TEXTO LIVRE (20/10/2026): a ordem em que o
    valor entra. O trilho abaixo é o caso EXATO (a frase diz "prazo sexta" e
    a data é a frase inteira); o que sobra depois dele é texto, e uma data
    escrita no meio dele não é mais uma frase de data — é a data que a
    pessoa pôs no fim do título. Ela é separada pelo tipo do campo que a
    tabela deixa ABERTO (`deadline`, o `at` de um lembrete), e o resto fica
    o texto. Um trecho que não carrega data nenhuma fica inteiro.

    Os valores lidos entram em `values` e `ranges`; a `Question` que a
    gramática ou uma referência devolve volta inteira, sem nada preenchido.
    """
    leftover: _Leftover = []
    for start, end in runs:
        chunk = " ".join(words[start:end])
        named = field_before(table, marks, start)
        # O MOTIVO DE UM ENCERRAMENTO (20/10/2026): "cancela a tarefa 2 motivo
        # desisti" escreve o motivo, e o motivo NÃO é um campo da tabela — é o
        # que o `lifecycle` dela manda para um campo (`table.cancel`). O
        # matcher não lê a vida da tabela; ele entrega o texto sob a chave
        # `reason`, e é `ui/ask` quem a lê (e a descarta quando a tabela não
        # declara campo nenhum com esse nome). Sem isto, o motivo virava o
        # título da linha, que é o oposto do que a pessoa escreveu.
        if named is None and action == "cancel" and start > 0:
            # O MOTIVO ANUNCIADO POR UMA PALAVRA DA LÍNGUA (20/10/2026):
            # `cancela a tarefa 3 porque desisti` diz o motivo, e o `porque` não
            # é o motivo — é a palavra que o apresenta. Ela é gasta, e o trecho
            # inteiro vai para a chave `reason`. A palavra do CAMPO (`motivo`,
            # `reason`) faz o mesmo pelo outro caminho.
            if reason_before(words, marks, start, language):
                values[REASON] = chunk
                continue
            if field_word(table, marks, start) == REASON:
                values[REASON] = chunk
                continue
        # A REFERÊNCIA DITA PELO NOME (24/10/2026): `projeto tr4` é o campo
        # `project` da tarefa, e o valor dele é a LINHA que o nome acha — não o
        # texto. O nome que não acha, ou que acha mais de uma, volta como
        # recusa ou pergunta: o que não resolve é resíduo, nunca palpite.
        target = reference_target(table, named)
        if target is not None and named is not None:
            referenced = reference_row(target, chunk)
            if isinstance(referenced, Question):
                return referenced
            values[named] = referenced
            continue
        field, reading = read_chunk(table, chunk, named, language, now)
        if isinstance(reading, Question):
            # Nothing is filled in for what the grammar asked back: the whole
            # sentence comes back as the question, and no row is proposed.
            return reading
        if isinstance(reading, Value):
            assert field is not None  # a read value always lands in a field
            values[field] = reading.value
            if reading.op != "=":
                ranges[field] = reading.op
        else:
            if action == "create":
                stripped, extra = temporal(table, chunk, language, now, values)
                if extra:
                    leftover.append((start, end, stripped.split()))
                    continue
            leftover.append((start, end, words[start:end]))
    return leftover
