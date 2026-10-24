"""The request: which ACTION and which TABLE a sentence asks for.

The verb that carries the act, the word that names a table without writing
its name, the two-actions and two-tables refusals — all read off the
vocabulary and the declared schema.
"""

from __future__ import annotations

from datetime import datetime

from at.core import tables
from at.data import schema
from at.i18n import tr
from at.nlu import vocabulary
from at.nlu.interpreter import resolve
from at.nlu.matcher_rows import reference_target
from at.nlu.matcher_segment import PARTICLE, marks_named
from at.nlu.normalizer import fold
from at.nlu.reading import Refused, Value

# The actions that act upon a row, and cannot be done without naming one.
ROW_ACTIONS = frozenset({"view", "edit", "cancel", "delete"})


# As ações que podem nomear a linha pelo TÍTULO. `edit` e `cancel` ficam de
# fora: o resto da frase delas também é o valor novo / o motivo, e o texto não
# distingue um do outro.
TITLED_ACTIONS = frozenset({"view", "delete"})


def implied_any(implied: dict[str, str], text: str) -> bool:
    """Se alguma expressão de `implies` está na frase, inteira e como palavra."""
    spelled = f" {fold(text)} "
    return any(
        f" {fold(expression)} " in spelled for expression in implied if expression
    )


def implied_window(
    implied: dict[str, str], words: list[str], index: int
) -> tuple[int, str] | None:
    """A expressão de `implies` que começa em `index`, com o tamanho dela.

    A mais longa vence (`me lembra de` antes de `me lembra`), pela mesma razão
    que a janela do vocabulário é a mais longa: uma expressão maior é mais
    precisa do que as palavras de que ela é feita.
    """
    longest = 0
    wanted: str | None = None
    for expression, meaning in implied.items():
        size = len(fold(expression).split())
        if size <= longest:
            continue
        piece = fold(" ".join(words[index:index + size]))
        if piece == fold(expression):
            longest, wanted = size, meaning
    return (longest, wanted) if wanted is not None else None


def said_an_action(words: list[str], language: str) -> bool:
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


def find_action(marks: list[str | None], text: str, language: str | None = None) -> str:
    found = marks_named(marks, tables.ACTIONS)
    if not found:
        # O VERBO QUE CARREGA O ATO (20/10/2026): `complete task 1` não escreve
        # nenhuma palavra de ação, e o verbo já diz o que fazer. Quando alguma
        # palavra da frase está em `implies`, a frase TEM ação — ela vem depois
        # (`said_an_action`), e o `create` aqui é só um lugar para ela passar.
        if language is not None and implied_any(vocabulary.implies(language), text):
            return "create"
        raise Refused("nlu.error.no_action", text=text)
    if len(found) > 1:
        raise Refused(
            "nlu.error.two_actions",
            first=tr(f"table.action.{found[0]}"),
            second=tr(f"table.action.{found[1]}"),
        )
    return found[0]


def find_table(
    marks: list[str | None], text: str, words: list[str], action: str,
    language: str, now: datetime,
) -> str:
    found: list[str] = []
    for mark in marks:
        if mark and schema.of(mark) and mark not in found:
            found.append(mark)
    found = object_tables(found, marks)
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
        hint = table_hint(words, language)
        if hint is not None:
            found.append(hint)
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
        if guessed and not reads_as_a_value(guessed, language, now):
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


def object_tables(found: list[str], marks: list[str | None]) -> list[str]:
    """As tabelas que a frase nomeia, sem as que são só o NOME DE UM CAMPO.

    `criar tarefa limpar carro em projeto tr4` escreve `projeto` — e `projeto`
    é a tabela e também o campo `project` da tarefa, que aponta para ela. Uma
    tabela que outra tabela da frase declara como campo (da mesma palavra, com
    `ref` para ela) e que TRAZ um nome logo depois (`projeto tr4`) é a palavra
    do campo e não um segundo objeto: o objeto é a outra. Sem o nome depois
    (`uma tarefa num projeto`) são mesmo duas tabelas, e o pedido continua
    recusado. Lido da declaração, sem nome nenhum escrito aqui.
    """
    if len(found) < 2:
        return found
    return [
        name for name in found
        if not (
            carries_a_name(marks, name)
            and any(
                other != name and reference_target(other, name) == name
                for other in found
            )
        )
    ]


def carries_a_name(marks: list[str | None], word: str) -> bool:
    """Se a palavra `word` tem um texto sem marca logo depois dela, saltadas as
    partículas — o nome que o campo recebe."""
    for index, mark in enumerate(marks):
        if mark != word:
            continue
        after = index + 1
        while after < len(marks) and marks[after] == PARTICLE:
            after += 1
        if after < len(marks) and marks[after] is None:
            return True
    return False


def table_hint(words: list[str], language: str) -> str | None:
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


def reads_as_a_value(chunk: str, language: str, now: datetime) -> bool:
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
