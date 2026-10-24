"""Segmentation: the sentence becomes one mark per word.

Each word is marked with the canonical it names, with `PARTICLE`, or with
nothing — the material the grammar and the residue are made of. The widest
window the vocabulary knows wins (`matcher.py` has the whole story).
"""

from __future__ import annotations

from datetime import datetime

from at.core import tables
from at.data import schema
from at.nlu import grammar, vocabulary
from at.nlu.normalizer import canonical, fold

# What the segmentation writes for a word that carries no meaning at all. It is
# not a canonical — no name of the product is empty, which is what the suite's
# gate over the vocabulary says — so it cannot collide with one.
PARTICLE = ""


# The word the person's own convention gives a `list` to ask for the GRID
# instead of the one-line-per-row default (the person's own words, 03/10/2026):
# "listar tarefas" reads as a short line each, "listar tabela tarefa" as every
# declared column. It is neither an action, a table, a field nor a closed
# value — the four shapes `vocabulary.of` names — so it is read here, by the
# literal word in both languages this product speaks, the same way a
# PARTICLE is: spent before anything else looks at the sentence, and never
# residue.
FULL_TABLE_WORDS = ("tabela", "table")


def full_table(words: list[str]) -> tuple[bool, list[str]]:
    found = [word for word in words if fold(word) in FULL_TABLE_WORDS]
    if not found:
        return False, words
    return True, [word for word in words if fold(word) not in FULL_TABLE_WORDS]


def segmented(words: list[str], language: str, now: datetime) -> list[str | None]:
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
    kept = set(phrase_spans(folded, language, now))

    marks: list[str | None] = []
    position = 0
    while position < len(words):
        starts = {start for start, _ in kept}
        if position in starts:
            size = span_size(position, kept)
            marks.extend([None] * size)
            position += size
            continue
        size, found = widest_window(folded, position, widest, language)
        if size:
            marks.extend([found] * size)
        elif opening(folded, position, openers):
            size = opening(folded, position, openers)
            marks.extend([PARTICLE] * size)
        elif folded[position] in particles:
            marks.append(PARTICLE)
        else:
            marks.append(machine_word(words[position]))
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


def opening(folded: list[str], position: int, openers: set[str]) -> int:
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


def phrase_spans(
    folded: list[str], language: str, now: datetime
) -> list[tuple[int, int]]:
    """As posições das frases de data da linguagem, como `(início, tamanho)`.

    A linguagem é quem sabe quais são: a lista declarada (`phrases`) e as
    contagens que só se leem inteiras (`em duas semanas`) vivem no
    `grammar.spans`, que confirma cada janela pelo próprio leitor de dia.
    """
    return grammar.spans(language, folded, now)


def span_size(position: int, kept: set[tuple[int, int]]) -> int:
    """O tamanho da frase que começa em `position` — a mais longa que começa
    ali, para uma frase contida em outra não picar a maior."""
    return max(size for start, size in kept if start == position)


def widest_window(folded: list[str], position: int, widest: int, language: str):
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


def machine_word(word: str) -> str | None:
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


def exact_flags(words: list[str], language: str) -> list[bool]:
    """Por palavra: se o vocabulário a leu como foi ESCRITA, sem a tolerância.

    A mesma segmentação de `segmented` (a janela mais larga primeiro), só que
    sem perdoar a letra trocada — o que ela acha é o que a pessoa escreveu.
    """
    pairs = vocabulary.of(language)
    widest = max((len(expression.split()) for expression in pairs), default=1)
    folded = [fold(word) for word in words]
    flags = [False] * len(words)
    position = 0
    while position < len(words):
        size = 0
        for width in range(min(widest, len(words) - position), 0, -1):
            if canonical(" ".join(folded[position:position + width]), language,
                         tolerant=False):
                size = width
                break
        for at in range(position, position + size):
            flags[at] = True
        position += size or 1
    return flags


def demote_fuzzy_actions(marks: list[str | None], words: list[str], language: str) -> None:
    """Uma palavra que só a tolerância leu como ação não é uma SEGUNDA ação.

    `criar tarefa clean car`: `clean` está a uma letra de `clear` (apagar), mas
    a frase já tem uma ação escrita por inteiro, e uma segunda que só o dedo
    escorregado explicaria é a palavra da pessoa — texto. Sem nenhuma ação
    exata, a tolerância segue valendo (`criarr tarefa x`).
    """
    exact = exact_flags(words, language)
    actions = [index for index, mark in enumerate(marks) if mark in tables.ACTIONS]
    if not any(exact[index] for index in actions):
        return
    for index in actions:
        if not exact[index]:
            marks[index] = None


def content_after_the_object(marks: list[str | None], table: str) -> None:
    """Uma segunda palavra de CRIAR depois do objeto é o texto, não outro verbo.

    `criar projeto Novo site`: `novo` é da família de criar, e `criar` já foi
    dito antes da tabela. Depois da tabela, uma palavra de criar numa frase que
    JÁ criava é conteúdo da linha. `tarefa nova ...` sem outro verbo antes
    continua sendo o verbo.
    """
    seen_create = False
    seen_table = False
    for index, mark in enumerate(marks):
        if mark == table:
            seen_table = True
        elif mark == "create":
            if seen_create and seen_table:
                marks[index] = None
            seen_create = True


def marks_named(marks: list[str | None], universe) -> list[str]:
    """The marks that name a word of `universe`, in the order they were written."""
    found: list[str] = []
    for mark in marks:
        if mark and mark in universe and mark not in found:
            found.append(mark)
    return found


def unspent_runs(spent: list[bool]) -> list[tuple[int, int]]:
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
