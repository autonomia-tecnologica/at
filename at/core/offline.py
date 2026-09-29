"""O motor offline: a fila de escrita local e a reconciliação por
last-write-wins (TASK-162, fatia 1/2).

**O que esta fatia é, e o que ela não é.** Ela é o motor: dada uma fila de
edições feitas sem rede — cada uma com o instante em que a pessoa a fez —,
decide qual sobrevive quando a conexão volta. Ela NÃO é o Service Worker, não é
a fila em si tal como o navegador a guarda, e não toca UI nenhuma — é por isso
que toda a suíte deste módulo roda sem navegador (`Testável pela suíte
sozinha`, o desc da TASK). Ligar isto a um `fetch` de um Service Worker é a
fatia 2/2.

**Onde a fila mora no navegador é uma decisão desta fatia, e a resposta é
IndexedDB** — o candidato óbvio para um PWA (suporta objetos estruturados,
sobrevive ao fechar a aba, e é o que a fatia 2 grava e lê ao montar a UI da
fila). Esta fatia não abre um IndexedDB — não há navegador na suíte —, mas o
formato de `QueueEntry` é o contrato que a fatia 2 escreve lá e lê de lá.

**O timestamp que o last-write-wins compara.** `modifications[].at` (a tabela
`task`) NÃO serve: ele só se move quando o campo `status` muda
(`tables._log_status`), então uma edição de `text` ou `desc` sem trocar status
não deixa rastro nenhum ali — exatamente o caso que o offline mais produz
(editar o corpo de uma tarefa, não fechá-la). Por isso a TASK-162 decide um
campo NOVO: `edited_at`, um `instant` que a engine RESTAMPA a cada escrita
(`tables._touch`, TASK-162), esteja ou não o `status` entre o que mudou. É
contra ELE que uma entrada da fila é comparada.

**A regra.** Uma entrada vence quando o instante em que a PESSOA a escreveu é
mais recente que o `edited_at` que a linha carrega NO SERVIDOR neste momento —
e nunca o instante em que a fila finalmente conseguiu falar com o servidor,
que pode ser horas depois e não diz nada sobre quem escreveu por último. Um
`create` nunca perde: a linha ainda não existe do lado de cá, então não há com
o que ele conflitar. Um empate (os dois instantes iguais) fica com o servidor —
critério de desempate, não um caso que se espera ver.

**Sem tela de resolução.** Uma entrada que perde é DESCARTADA, silenciosa — a
decisão já foi da pessoa (TASK-162, "o risco é aceito") — e o que volta no
`Resolution` é a linha como ela está no servidor, para a fatia 2 atualizar o
cache local com o que de fato venceu.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from at.core import tables
from at.data import store

# O escopo é só Tarefas (TASK-162, Ressalvas) — "Arquivos offline" é outro
# item do backlog, com desenho próprio. Uma constante e não um parâmetro:
# nada aqui precisa reconciliar mais de uma tabela ainda.
TABLE = "task"


@dataclass(frozen=True)
class QueueEntry:
    """Uma escrita da fila, como a pessoa a fez sem rede.

    `edited_at` é o instante DA EDIÇÃO — o relógio do dispositivo no momento em
    que a pessoa mexeu, não o momento em que a fila finalmente fala com o
    servidor. `id` é a linha do servidor (um número já conhecido) OU o
    `local_id` de um `create` anterior NESTA MESMA fila — a fatia 2 cria uma
    tarefa offline e a edita de novo antes de reconectar, e a segunda entrada
    aponta para a primeira por um nome que o navegador inventou, porque o
    servidor ainda não deu um número a ela. `local_id` é o nome que O PRÓPRIO
    `create` leva, para uma entrada seguinte apontar para ele.
    """

    action: str  # "create" ou "edit" — as duas que TASK-162 pede
    values: dict[str, str]
    edited_at: str
    id: int | str | None = None
    local_id: str | None = None


@dataclass(frozen=True)
class Resolution:
    """O que aconteceu com uma entrada: venceu (`applied`) ou perdeu — e a
    linha como ela está no servidor AGORA, nos dois casos. Uma perdedora
    devolve a linha para a fila poder atualizar o que tinha em cache com o que
    de fato ficou; uma que não encontrou a linha (apagada enquanto a pessoa
    estava fora) devolve `None`."""

    entry: QueueEntry
    applied: bool
    row: dict | None


def _instant(value: str) -> str:
    """O instante da entrada, lido do jeito que a engine lê qualquer outro:
    UTC, com milissegundos — a mesma grafia de `tables.utc`, para a comparação
    nunca discordar do que uma linha já carrega em `edited_at`."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise tables.TableError(
            "error.not_an_instant",
            field=tables.label(TABLE, "edited_at"),
            value=value,
        ) from None
    return tables.utc(parsed)


def reconcile(entries: Sequence[QueueEntry]) -> list[Resolution]:
    """A fila inteira, na ordem em que chega — a ordem em que a pessoa
    escreveu, que é a mesma que uma fila offline naturalmente guarda.

    Processada em ordem porque um `edit` pode apontar para um `create` da MESMA
    passada (`local_id`): resolver fora de ordem deixaria essa referência sem
    linha para achar.
    """
    resolved: dict[str, int] = {}
    out: list[Resolution] = []
    for entry in entries:
        at = _instant(entry.edited_at)
        if entry.action == "create":
            row = tables.create(TABLE, entry.values, at=at)
            if entry.local_id is not None:
                number = store.number_of(row)
                if number is not None:
                    resolved[entry.local_id] = number
            out.append(Resolution(entry, True, row))
            continue

        target = resolved.get(entry.id) if isinstance(entry.id, str) else entry.id
        if target is None:
            # Um `edit` sem linha para achar — a referência a um `local_id`
            # que este lote não trouxe. Descartada como qualquer perdedora,
            # só que sem linha nenhuma para devolver.
            out.append(Resolution(entry, False, None))
            continue

        try:
            row = tables.find(TABLE, target)
        except tables.TableError:
            # A linha sumiu enquanto a pessoa estava fora (apagada do outro
            # lado) — não há com o que reconciliar, e não é um erro da fila.
            out.append(Resolution(entry, False, None))
            continue

        current = row.get("edited_at")
        if current is not None and current >= at:
            # O servidor escreveu por último (ou empatou) — a entrada perde,
            # silenciosa, e a linha que volta é a que de fato ficou.
            out.append(Resolution(entry, False, row))
            continue

        updated = tables.edit(TABLE, target, entry.values, at=at)
        out.append(Resolution(entry, True, updated))
    return out
