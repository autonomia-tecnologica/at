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
from at.i18n import tr
from at.nlu import grammar, vocabulary
from at.nlu.interpreter import KINDS, resolve
from at.nlu.normalizer import canonical, fold
from at.nlu.proposal import Proposal
from at.nlu.reading import Question, Reading, Refused, Residue, Value

# What the segmentation writes for a word that carries no meaning at all. It is
# not a canonical — no name of the product is empty, which is what the suite's
# gate over the vocabulary says — so it cannot collide with one.
PARTICLE = ""

# The actions that act upon a row, and cannot be done without naming one.
_ROW_ACTIONS = frozenset({"view", "edit", "cancel", "delete"})


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
    """
    language = language or i18n.active_code()
    now = now if now is not None else datetime.now()

    words = text.split()
    if not words:
        raise Refused("nlu.error.no_action", text=text)

    full_table, words = _full_table(words)
    if not words:
        raise Refused("nlu.error.no_action", text=text)

    marks = _segmented(words, language, now)
    action = action if action is not None else _action(marks, text, language)
    table = table if table is not None else _table(marks, text, words, action, language, now)

    # A value of a closed vocabulary fills the field that carries it. The word is
    # spent either way: `alta` names a priority, it is not content.
    values: dict[str, Any] = {}
    # E COMO cada valor se compara ao que a linha guarda (`ranges`): `até` é `<=`,
    # `desde` é `>=`, e o que não tem palavra de intervalo é exato (`=`, o padrão,
    # e por isso não entra aqui). É o que um `list` lê para filtrar.
    ranges: dict[str, str] = {}
    for mark in marks:
        field = _enum_field(table, mark)
        if field is not None:
            values[field] = mark

    # O VERBO QUE CARREGA O VALOR (20/10/2026): "conclui a tarefa 3" diz o que
    # fazer com ela, e o valor já está no verbo. O vocabulário `implies` diz a
    # palavra e o valor; o campo é o da tabela cuja lista fechada CARREGA esse
    # valor — lido da declaração, como `conclui` num `project`, sem o valor
    # nele, não significa nada. A palavra é gasta, e nunca vira texto; a AÇÃO é
    # `edit`, porque dizer o resultado de uma linha que existe é mudancá-la,
    # e não fechá-la com motivo.
    implied = vocabulary.implies(language)
    spent: dict[str, str] = {}
    for index, mark in enumerate(marks):
        # A IMPLICAÇÃO É DE UMA PALAVRA OU DE UMA EXPRESSÃO (20/10/2026): `check
        # off` é duas palavras e vale junto — o verbo fica inteiro ou não fica.
        window = _implied_window(implied, words, index)
        if window is None:
            continue
        size, wanted = window
        found = _enum_field(table, wanted)
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

    runs = _runs([mark is not None for mark in marks])
    # O ATO QUE O VERBO JÁ DISSE (20/10/2026): dizer o resultado de uma linha
    # que existe é mudá-la (`edit`), e não fechá-la com motivo. O verbo que
    # nomeia um valor de uma lista fechada vale como a ação quando a frase não
    # nomeou outra — `conclui a tarefa 3` é uma edição; `cria uma nota` continua
    # sendo o `create` da palavra dela.
    if spent and action == "create" and not _said_an_action(words, language):
        action = "edit"
    row: Any = None
    if action in _ROW_ACTIONS:
        # The row is chosen among the pieces the grammar is not going to read:
        # `dia 3` is a day and stays one, and a bare `3` is a row when — and
        # only when — the action asked for one.
        row, runs = _take_row(table, words, runs)
        if row is None:
            raise Refused("nlu.error.no_row", table=tables.table_name(table))

        # A DATA OU A HORA DENTRO DO TEXTO LIVRE (20/10/2026): a ordem em que o
    # valor entra. O trilho abaixo é o caso EXATO (a frase diz "prazo sexta" e
    # a data é a frase inteira); o que sobra depois dele é texto, e uma data
    # escrita no meio dele não é mais uma frase de data — é a data que a
    # pessoa pôs no fim do título. Ela é separada pelo tipo do campo que a
    # tabela deixa ABERTO (`deadline`, o `at` de um lembrete), e o resto fica
    # o texto. Um trecho que não carrega data nenhuma fica inteiro.
    leftover: list[str] = []
    for start, end in runs:
        chunk = " ".join(words[start:end])
        named = _field_before(table, marks, start)
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
            if _reason_before(words, marks, start, language):
                values[REASON] = chunk
                continue
            if _field_word(table, marks, start) == REASON:
                values[REASON] = chunk
                continue
        field, reading = _read(table, chunk, named, language, now)
        if isinstance(reading, Question):
            # Nothing is filled in for what the grammar asked back: the whole
            # sentence comes back as the question, and no row is proposed.
            return reading
        if isinstance(reading, Value):
            values[field] = reading.value
            if reading.op != "=":
                ranges[field] = reading.op
        else:
            if action == "create":
                stripped, extra = _temporal(table, chunk, language, now, values)
                if extra:
                    leftover.extend(stripped.split())
                    continue
            leftover.extend(words[start:end])

    residue = " ".join(leftover).strip()
    primary = schema.primary(table)
    if residue and primary:
        values[primary] = residue
    # UM PEDIDO QUE NÃO DIZ O QUE CRIAR (20/10/2026): "cria uma tarefa", sozinha,
    # não é uma linha vazia — é uma pergunta. O campo que a pessoa não disse é o
    # PRINCIPAL da tabela, e é o que ela ainda tem de escrever; a resposta vai
    # como a pergunta do matcher (`nlu.ask.what`), e nada é escrito. Um pedido
    # com o principal preenchido — ou que preencheu qualquer campo que só a
    # pessoa sabe — não é este caso: uma tarefa com prazo e sem texto continua
    # sendo a tabela que aceita e grava (o `text` dela não é `required`), e o
    # lembrete sem nada é o motor que recusa, na palavra dele.
    if action == "create" and primary and not values.get(primary) and not values:
        return Question("nlu.ask.what", tables.label(table, primary))

    return Proposal(
        action=action, table=table, values=values, row=row, ranges=ranges,
        full_table=full_table,
    )


# The word the person's own convention gives a `list` to ask for the GRID
# instead of the one-line-per-row default (the person's own words, 03/10/2026):
# "listar tarefas" reads as a short line each, "listar tabela tarefa" as every
# declared column. It is neither an action, a table, a field nor a closed
# value — the four shapes `vocabulary.of` names — so it is read here, by the
# literal word in both languages this product speaks, the same way a
# PARTICLE is: spent before anything else looks at the sentence, and never
# residue.
FULL_TABLE_WORDS = ("tabela", "table")


def _full_table(words: list[str]) -> tuple[bool, list[str]]:
    found = [word for word in words if fold(word) in FULL_TABLE_WORDS]
    if not found:
        return False, words
    return True, [word for word in words if fold(word) not in FULL_TABLE_WORDS]


# ------------------------------------------------------------ segmentation ---

def _segmented(words: list[str], language: str, now: datetime) -> list[str | None]:
    """Every word, marked with the canonical it names — or with nothing.

    Three answers, and they are the three the matcher has for a word: the
    canonical the vocabulary knows it by, `PARTICLE` for a word that carries no
    meaning, and `None` for what neither pass could place — which is the material
    the grammar and the residue are made of.
    """
    pairs = vocabulary.of(language)
    widest = max((len(expression.split()) for expression in pairs), default=1)
    particles = {fold(particle) for particle in vocabulary.particles(language)}
    # A CORTESIA QUE ABRE UM PEDIDO (20/10/2026): `quero criar uma tarefa` é o
    # pedido sem o `quero`, e a palavra não é o objeto de nada. Ela é gasta como
    # uma partícula — a diferença é que ela vem num bloco próprio, porque vale
    # para toda tabela e não aponta nenhuma. A mais longa vence.
    openers = {fold(opener) for opener in vocabulary.openers(language)}
    folded = [fold(word) for word in words]
    # AS FRASES DE DATA QUE SÓ SE LEEM INTEIRAS (20/10/2026): `depois de amanhã`
    # era picada — `amanhã` virava a data e `depois` o texto —, e `semana que
    # vem` virava a frequência `semanal` mais sobra. Estas palavras ficam
    # juntas, sem marca nenhuma, e chegam inteiras ao trilho da data.
    kept = set(_phrase_spans(folded, language, now))

    marks: list[str | None] = []
    position = 0
    while position < len(words):
        starts = {start for start, _ in kept}
        if position in starts:
            size = _span_size(position, kept)
            marks.extend([None] * size)
            position += size
            continue
        size, found = _window(folded, position, widest, language)
        if size:
            marks.extend([found] * size)
        elif _opening(folded, position, openers):
            size = _opening(folded, position, openers)
            marks.extend([PARTICLE] * size)
        elif folded[position] in particles:
            marks.append(PARTICLE)
        else:
            marks.append(_machine(words[position]))
        position += size or 1
    # A PARTÍCULA QUE ANUNCIA A HORA FICA COM ELA (20/10/2026): `às 18` só é
    # uma hora porque o `às` está na frente, e gastá-la antes de a hora ser
    # lida deixava `18` sozinho no texto — a data sem a palavra que a
    # apresentava. A partícula volta a ser sem marca quando o número que ela
    # apresenta FECHA a frase: ali ela é a hora e não a partícula, e as duas
    # saem juntas. `as 2 caixas` não é este caso — o número não fecha nada.
    announcers = set(getattr(grammar.of(language), "ANNOUNCERS", ()))
    for index, word in enumerate(folded):
        if marks[index] != PARTICLE or word not in announcers:
            continue
        last = index + 1
        if last == len(folded) - 1 and marks[last] is None:
            marks[index] = None
    return marks


def _opening(folded: list[str], position: int, openers: set[str]) -> int:
    """O tamanho da cortesia que começa em `position`, ou zero.

    A mais LONGA vence: `por favor` é uma cortesia inteira, e `por` sozinho é
    uma partícula — o que vier maior é o que a pessoa escreveu.
    """
    longest = 0
    for opener in openers:
        size = len(opener.split())
        if size <= longest:
            continue
        if folded[position:position + size] == opener.split():
            longest = size
    return longest


def _phrase_spans(
    folded: list[str], language: str, now: datetime
) -> list[tuple[int, int]]:
    """As posições das frases de data da linguagem, como `(início, tamanho)`.

    A linguagem é quem sabe quais são: a lista declarada (`phrases`) e as
    contagens que só se leem inteiras (`em duas semanas`) vivem no
    `grammar.spans`, que confirma cada janela pelo próprio leitor de dia.
    """
    return grammar.spans(language, folded, now)


def _span_size(position: int, kept: set[tuple[int, int]]) -> int:
    """O tamanho da frase que começa em `position` — a mais longa que começa
    ali, para uma frase contida em outra não picar a maior."""
    return max(size for start, size in kept if start == position)


def _window(folded: list[str], position: int, widest: int, language: str):
    """The widest window from `position` that the vocabulary knows, and what.

    The widest and not the nearest: a longer expression is a more precise thing
    than the words it is built of, and `em andamento` is one value, never `em`
    and a word about progress.
    """
    for size in range(min(widest, len(folded) - position), 0, -1):
        found = canonical(" ".join(folded[position:position + size]), language)
        if found:
            return size, found
    return 0, None


def _machine(word: str) -> str | None:
    """The machine word a person wrote as it is — a table's id, a field's name.

    The packed vocabulary is the product's, and a table a person declares in
    their own folder names nothing there yet: what still names it is the word the
    declaration itself carries, written as the declaration writes it. A
    per-instance vocabulary is item 16's, and this is the piece of it that costs
    nothing today — which is how the matcher meets the schema in hand.
    """
    written = fold(word)
    for name, declared in schema.tables().items():
        if fold(name) == written:
            return name
        fields = declared.get("fields")
        if not isinstance(fields, dict):
            continue
        for field in fields:
            if fold(field) == written:
                return field
    return None


# --------------------------------------------------------------- reading ---

def _read(
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
            return named, _list_reading(chunk, declared.get("items"), language, now)
        # A field of a type the grammar has no reader for — a text is the
        # example — is not read at all: its content is residue, and residue is
        # what the primary field is for.
        return None, Residue(chunk)

    field = open_day_field(table)
    reading = resolve(chunk, "day", language=language, now=now)
    if field is None and isinstance(reading, Value):
        return None, Question("nlu.ask.which_field", chunk)
    return field, reading


def _temporal(
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


def _list_reading(
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


def open_day_field(table: str) -> str | None:
    """The `day` field the declaration does NOT fill by itself.

    The rule is read off the DECLARATION and never off a list of names: it is
    the `day` field whose default is null, because a field that declares a value
    is already filled the moment the row is born. `since` declares `today` and is
    out; `deadline` declares `null` and is in — and neither name is written here.
    """
    found = [
        name
        for name, declared in _fields(table).items()
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
    for name, declared in _fields(table).items():
        if (
            isinstance(declared, dict)
            and declared.get("type") == "list"
            and declared.get("items") == kind
        ):
            return name
    return None


def _fields(table: str) -> dict:
    declared = schema.of(table) or {}
    fields = declared.get("fields")
    return fields if isinstance(fields, dict) else {}


# A palavra que abre o MOTIVO de um encerramento — `motivo`/`reason`, que o
# vocabulário já conhece como campo (`field.json`) e que nem toda tabela
# declara. Aqui ela é lida só como marca de onde o motivo começa; o valor vai
# para a chave `REASON`, e quem o entrega ao fechamento é `at.ui.ask`.
REASON = "reason"


def _field_word(table: str, marks: list[str | None], start: int) -> str | None:
    """A palavra de CAMPO que abre o trecho, mesmo de um campo que a tabela não
    declara — `motivo` de uma tarefa é o `reason`, e a tarefa não o declara.

    É `_field_before` sem o filtro da declaração, e existe por uma razão só: o
    motivo de um encerramento mora no `lifecycle`, não nos campos.
    """
    index = start - 1
    while index >= 0 and marks[index] == PARTICLE:
        index -= 1
    return marks[index] if index >= 0 and marks[index] else None


def _reason_before(
    words: list[str], marks: list[str | None], start: int, language: str
) -> bool:
    """Se o trecho em `start` é o MOTIVO que uma palavra da língua anunciou.

    A palavra é lida no vocabulário `reasons` (`porque`, `pois`, `because`), e
    as partículas entre ela e o trecho são saltadas, como em `_field_before`:
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


def _field_before(table: str, marks: list[str | None], start: int) -> str | None:
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
    return mark if mark and mark in _fields(table) else None


def _enum_field(table: str, mark: str | None) -> str | None:
    """The field of `table` whose closed vocabulary carries `mark`, if one does."""
    if not mark:
        return None
    for name, declared in _fields(table).items():
        if not isinstance(declared, dict):
            continue
        choices = declared.get("enum")
        if isinstance(choices, dict) and mark in choices:
            return name
    return None


# ------------------------------------------------------------- the request ---

def _implied_any(implied: dict[str, str], text: str) -> bool:
    """Se alguma expressão de `implies` está na frase, inteira e como palavra."""
    spelled = f" {fold(text)} "
    return any(
        f" {fold(expression)} " in spelled for expression in implied if expression
    )


def _implied_window(
    implied: dict[str, str], words: list[str], index: int
) -> tuple[int, str] | None:
    """A expressão de `implies` que começa em `index`, com o tamanho dela.

    A mais longa vence (`me lembra de` antes de `me lembra`), pela mesma razão
    que a janela do vocabulário é a mais longa: uma expressão maior é mais
    precisa do que as palavras de que ela é feita.
    """
    longest = 0
    wanted: str | None = None
    for expression, canonical in implied.items():
        size = len(fold(expression).split())
        if size <= longest:
            continue
        piece = fold(" ".join(words[index:index + size]))
        if piece == fold(expression):
            longest, wanted = size, canonical
    return (longest, wanted) if wanted is not None else None


def _said_an_action(words: list[str], language: str) -> bool:
    """Se a frase tem uma palavra que nomeia uma AÇÃO do produto.

    O verbo implicado (`conclui`, `risca`) vale como a ação quando ela não veio
    dita — mas só quando ela não veio dita: `adiciona uma tarefa concluída` tem
    as duas, e a ação escrita é a que a pessoa quis.
    """
    pairs = vocabulary.of(language)
    for word in words:
        if pairs.get(fold(word)) in tables.ACTIONS:
            return True
    return False


def _action(marks: list[str | None], text: str, language: str | None = None) -> str:
    found = _named(marks, tables.ACTIONS)
    if not found:
        # O VERBO QUE CARREGA O ATO (20/10/2026): `complete task 1` não escreve
        # nenhuma palavra de ação, e o verbo já diz o que fazer. Quando alguma
        # palavra da frase está em `implies`, a frase TEM ação — ela vem depois
        # (`_said_an_action`), e o `create` aqui é só um lugar para ela passar.
        if language is not None and _implied_any(vocabulary.implies(language), text):
            return "create"
        raise Refused("nlu.error.no_action", text=text)
    if len(found) > 1:
        raise Refused(
            "nlu.error.two_actions",
            first=tr(f"table.action.{found[0]}"),
            second=tr(f"table.action.{found[1]}"),
        )
    return found[0]


def _table(
    marks: list[str | None], text: str, words: list[str], action: str,
    language: str, now: datetime,
) -> str:
    found: list[str] = []
    for mark in marks:
        if mark and schema.of(mark) and mark not in found:
            found.append(mark)
    if not found:
        # O VERBO QUE NOMEIA A TABELA (20/10/2026): "anota que o banco ligou"
        # não escreve "nota", mas `anota` já diz que a linha é uma nota. O
        # vocabulário `implies` carrega esse par — a palavra e o que ela
        # implica —, e o que for uma tabela DECLARADA nesta pasta vale como o
        # nome da tabela.
        implied = vocabulary.implies(language)
        for word in words:
            wanted = implied.get(fold(word))
            if wanted and schema.of(wanted):
                found.append(wanted)
                break
    if not found:
        # A PALAVRA QUE NOMEIA A TABELA SEM DIZER O NOME DELA (20/10/2026):
        # "me lembra de imprimir as passagens" não escreve "lembrete", mas
        # "me lembra" já diz o que a linha é. O vocabulário `hints` é essa
        # leitura, e só vale quando a frase não nomeia tabela nenhuma — um
        # "cria um lembrete" fica com a sua palavra.
        hinted = _hinted(words, language)
        if hinted is not None:
            found.append(hinted)
    if not found:
        guessed = " ".join(
            words[index] for index, mark in enumerate(marks) if mark is None
        )
        # The word the person most likely MEANT as the object: whatever the
        # vocabulary did not place at all (not a particle, not the action, not
        # a closed value) AND is not a day or a number either — "listar teste"
        # names no table, and "teste" is the one word left with nowhere else to
        # have gone. "cria pra sexta" is NOT this: "sexta" is residue too, but
        # it is a day with nowhere to land, the same incompleteness a bare
        # "cria" has — not a guess at an object's name.
        if guessed and not _reads_as_a_value(guessed, language, now):
            raise Refused(
                "nlu.error.no_such_table", word=guessed, action=tr(f"table.action.{action}").lower(),
            )
        # A BARE VERB — "listar", nothing after it (or an argument with
        # nowhere to land, which names just as little) — and the one useful
        # answer is what IS there to name: every declared table, the same
        # catalogue `--help` reads off (`canonical` carries the action through
        # for `lib/chat.ts`'s own follow-up, below `{action}`'s own label).
        names = ", ".join(tables.table_name(name) for name in schema.tables())
        raise Refused(
            "nlu.error.no_table_bare",
            action=tr(f"table.action.{action}").lower(), names=names, canonical=action,
        )
    if len(found) > 1:
        raise Refused(
            "nlu.error.two_tables",
            first=tables.table_name(found[0]),
            second=tables.table_name(found[1]),
        )
    return found[0]


def _hinted(words: list[str], language: str) -> str | None:
    """The table a phrase names without writing its name — "me lembra" é uma
    linha de `reminder`, e o verbo já o diz.

    A dica mais LONGA vence (`me lembrar de` antes de `me lembrar`), pela mesma
    razão que a janela do vocabulário é a mais longa: uma expressão maior é
    mais precisa do que as palavras de que ela é feita. E a dica só vale para
    uma tabela que ESTA pasta declara — uma dica de uma tabela que sumiu é
    lixo, e o matcher não a lê.
    """
    hints = vocabulary.hints(language)
    if not hints:
        return None
    spelled = fold(" ".join(words))
    for expression in sorted(hints, key=lambda one: len(fold(one).split()), reverse=True):
        wanted = fold(expression)
        if wanted and f" {wanted} " in f" {spelled} " and schema.of(hints[expression]):
            return hints[expression]
    return None


def _reads_as_a_value(chunk: str, language: str, now: datetime) -> bool:
    """Whether the grammar reads `chunk` as a day or a number ON ITS OWN —
    "sexta", "amanhã", "3" — regardless of there being any field for it to
    fill. A residue this reads as is a VALUE with nowhere to land, never a
    guess at a word the vocabulary does not know."""
    for kind in ("day", "number"):
        try:
            if isinstance(resolve(chunk, kind, language=language, now=now), Value):
                return True
        except Refused:
            continue
    return False


def _named(marks: list[str | None], universe) -> list[str]:
    """The marks that name a word of `universe`, in the order they were written."""
    found: list[str] = []
    for mark in marks:
        if mark and mark in universe and mark not in found:
            found.append(mark)
    return found


def _runs(spent: list[bool]) -> list[tuple[int, int]]:
    """The pieces the vocabulary did not spend, as `(start, end)` spans."""
    found: list[tuple[int, int]] = []
    start: int | None = None
    for index, done in enumerate([*spent, True]):
        if done and start is not None:
            found.append((start, index))
            start = None
        elif not done and start is None:
            start = index
    return found


def _take_row(table: str, words: list[str], runs: list[tuple[int, int]]):
    """The piece that names a row, and the pieces that are left.

    A row is named the way a person names one — `3`, `TASK-3` — and only a piece
    of one word is looked at, so `dia 3` stays a day.
    """
    kept: list[tuple[int, int]] = []
    found: Any = None
    for start, end in runs:
        if found is None and end - start == 1:
            number = tables.number_of(table, words[start])
            if number is not None:
                found = number
                continue
        kept.append((start, end))
    return found, kept
