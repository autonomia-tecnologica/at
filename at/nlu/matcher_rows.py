"""The rows a sentence names: by number, by title, by a reference, and the residue.

A row is named the way a person names one (`3`, `TASK-3`, a piece of its
title, `projeto tr4`); what does not resolve is a question or a refusal, never
a guess.
"""

from __future__ import annotations

from typing import Any, cast

from at.core import tables
from at.data import schema, store
from at.nlu.matcher_fields import declared_fields
from at.nlu.matcher_segment import PARTICLE
from at.nlu.normalizer import fold
from at.nlu.reading import Question, Refused

# Quantos candidatos a pergunta lista antes de cortar.
MAX_CHOICES = 10


# A palavra que só anuncia o número (`nota numero 3`): gasta ao nomear a linha.
NUMBER_WORDS = frozenset({"numero", "number", "nr", "num"})


def reference_target(table: str, field: str | None) -> str | None:
    """A tabela para onde o campo `field` de `table` aponta — quando aponta para
    UMA só, que é o caso em que um nome escrito acha a linha."""
    if not field:
        return None
    declared = declared_fields(table).get(field)
    targets = declared.get("ref") if isinstance(declared, dict) else None
    if isinstance(targets, list) and len(targets) == 1 and schema.of(targets[0]):
        return str(targets[0])
    return None


def reference_row(target: str, chunk: str) -> int | Question:
    """O número da linha de `target` que o texto nomeia, ou a pergunta.

    O nome é comparado por `fold` (caixa e acento) com o campo principal da
    tabela, e só a IGUALDADE resolve. Um único igual vale; vários iguais, ou
    nenhum igual mas alguns que CONTÊM o que foi dito, voltam como pergunta,
    com a lista; nenhum parecido é recusa, com o que existe. Um identificador
    (`3`, `PRJ-3`) nomeia a linha pelo número, se ela existe.
    """
    primary = schema.primary(target)
    rows = tables.rows(target, show_all=True)
    name = tables.table_name(target)
    wanted = fold(chunk)
    number = tables.number_of(target, chunk.strip())
    if number is not None:
        for row in rows:
            if store.number_of(row) == number:
                return number
    titled = [
        row for row in rows if primary and isinstance(row.get(primary), str)
    ]
    exact = [row for row in titled if fold(row[primary]) == wanted]
    if len(exact) == 1:
        return cast("int | Question", store.number_of(exact[0]))
    similar = exact or [row for row in titled if wanted and wanted in fold(row[primary])]
    if similar:
        lines = [
            f"{index}. {tables.format_id(target, store.number_of(row))} · {row[primary]}"
            for index, row in enumerate(similar[:MAX_CHOICES], 1)
        ]
        if len(similar) > MAX_CHOICES:
            lines.append("…")
        return Question("nlu.ask.which_ref", f"{name} \"{chunk}\":\n" + "\n".join(lines))
    existing = ", ".join(str(row[primary]) for row in titled[:MAX_CHOICES]) or "—"
    raise Refused("nlu.error.no_ref", table=name, text=chunk, existing=existing)


def take_title(table: str, words: list[str], runs: list[tuple[int, int]]):
    """A linha nomeada pelo TÍTULO: o texto que sobrou da frase, buscado no campo
    principal que a tabela declara (`schema.primary`), sem diferenciar caixa nem
    acento. Uma só linha: devolve o número dela. Uma linha cujo título é IGUAL ao
    texto vence as que apenas o contêm. Várias: devolve a `Question`. Nenhuma:
    `Refused`. Sem texto algum: `None` (a frase continua sem linha).

    Um `2323` dentro de um texto de várias palavras é parte do texto, nunca o id:
    o número só nomeia a linha quando é a única coisa dita (`numero 3`).
    """
    chunk = [
        word for start, end in runs for word in words[start:end]
        if fold(word) not in NUMBER_WORDS
    ]
    if not chunk:
        return None, runs
    if len(chunk) == 1:
        number = tables.number_of(table, chunk[0])
        if number is not None:
            return number, []
    wanted = fold(" ".join(chunk))
    primary = schema.primary(table)
    if not primary or tables.opaque(table, primary) is not None:
        return None, runs
    found = [
        row for row in tables.rows(table, show_all=True)
        if isinstance(row.get(primary), str) and wanted in fold(row[primary])
    ]
    exact = [row for row in found if fold(row[primary]) == wanted]
    found = exact or found
    if not found:
        raise Refused("nlu.error.no_title", table=tables.table_name(table), text=" ".join(chunk))
    if len(found) == 1:
        return store.number_of(found[0]), []
    lines = [
        f"{index}. {tables.format_id(table, store.number_of(row))} · {row[primary]}"
        for index, row in enumerate(found[:MAX_CHOICES], 1)
    ]
    if len(found) > MAX_CHOICES:
        lines.append("…")
    return Question("nlu.ask.which_row", "\n".join(lines)), runs


def take_row(table: str, words: list[str], runs: list[tuple[int, int]]):
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


def joined(
    leftover: list[tuple[int, int, list[str]]], words: list[str], marks: list[str | None]
) -> str:
    """O resíduo, com as partículas que ficam NO MEIO dele.

    `não falar com fulano` é um texto só: o `com` está entre duas palavras que
    ficaram, e gastá-lo escreveria "não falar fulano". A partícula da BORDA
    (`uma`, `pra`) continua gasta, e a que separa um resíduo de um valor que a
    gramática leu também — só a que une dois pedaços de resíduo é do texto.
    """
    out: list[str] = []
    previous_end: int | None = None
    for start, end, piece in leftover:
        if previous_end is not None and start > previous_end and all(
            marks[at] == PARTICLE for at in range(previous_end, start)
        ):
            out.extend(words[previous_end:start])
        out.extend(piece)
        previous_end = end
    return " ".join(out)
