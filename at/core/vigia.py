"""O vigia: o motor que detecta a mudança numa pasta e despacha a consumidores
cadastrados (TASK-152).

**Ele detecta e despacha, e só.** Quem age é o consumidor — o Cofre sela
(TASK-154), a página relê (TASK-128, `/api/events`) — e este módulo não sabe o
que um consumidor faz com o evento que recebe. **A cifra não mora aqui**: quem
cifra é a camada de criptografia (`at/encryption/vault`), como um HSM, e um
consumidor que precisa dela a chama por conta própria.

**A detecção é por VARREDURA, e não por um observador do sistema operacional.**
O produto é `stdlib` só (§3, Dependência externa) — nada de `inotify` nem de uma
dependência nova para isto —, então o que existe é comparar o retrato de agora
com o de ontem: o nome de cada arquivo e o `mtime` dele. Quem chama `scan()` é
quem tem o relógio — o mesmo desenho do job agendado (`core/clock.py`), onde o
motor só diz O QUE muda de estado e o processo que fica de pé (a WebApp) é quem
o chama de novo e de novo.

**A primeira varredura não despacha nada.** Um `Vigia` que acabou de nascer não
tem retrato anterior, e todo arquivo que já estava na pasta pareceria uma
escrita nova — o Cofre não pode selar o que já era `.enc` antes dele existir.
Ela grava o retrato e sai quieta; é a SEGUNDA varredura, e as que vêm depois,
que comparam e falam.

**Só a ESCRITA é vista, e o apagamento não.** O `mtime` que muda é a assinatura
de um arquivo criado ou reescrito; um arquivo que sumiu não dispara consumidor
nenhum — nada nesta fatia precisa disso, e um evento que ninguém pede é uma
forma que se paga sem uso.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


# O que um consumidor recebe: o caminho ABSOLUTO do arquivo cuja escrita o
# vigia viu. Nenhum outro campo — o resto é do consumidor perguntar ao próprio
# arquivo, e um `Event` maior seria um campo a mais para nunca ser lido.
@dataclass(frozen=True)
class Event:
    path: Path


# Um consumidor é uma função de um evento, e nada mais: ele não devolve nada
# que o vigia leia, porque o vigia não decide o que fazer com o que despachou.
Consumer = Callable[[Event], None]


class Vigia:
    """Um vigia, de UMA pasta. Cadastra consumidores, varre, despacha.

    Cada instância é a sua própria pasta e o seu próprio retrato — duas pastas
    vigiadas são dois `Vigia`, e não uma tabela indexada por caminho que o
    módulo guardasse sozinho: um estado de módulo sobreviveria entre testes que
    não têm nada um com o outro, e um objeto por pasta não.
    """

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self._consumers: list[Consumer] = []
        self._known: dict[str, int] | None = None

    def watch(self, consumer: Consumer) -> None:
        """Cadastra um consumidor. Ele é chamado a partir da PRÓXIMA varredura
        que encontrar uma mudança — nunca por uma que já passou."""
        self._consumers.append(consumer)

    def scan(self) -> tuple[Event, ...]:
        """Varre a pasta agora, despacha o que mudou, e devolve o que despachou.

        Uma pasta que ainda não existe varre como vazia — não é uma recusa,
        porque uma pasta vigiada pode nascer depois do vigia que a espera.
        """
        current = self._listing()
        first = self._known is None
        previous = self._known or {}
        self._known = current
        if first:
            return ()
        changed = tuple(
            Event(self.folder / name)
            for name, stamp in sorted(current.items())
            if previous.get(name) != stamp
        )
        for event in changed:
            for consumer in self._consumers:
                consumer(event)
        return changed

    def _listing(self) -> dict[str, int]:
        if not self.folder.is_dir():
            return {}
        # `st_mtime_ns` e não `st_mtime`: a suíte não pode dormir um segundo
        # inteiro entre duas escritas só para provar que a segunda mudou algo,
        # e o `float` de `st_mtime` perde exatamente essa resolução.
        return {
            item.relative_to(self.folder).as_posix(): item.stat().st_mtime_ns
            for item in self.folder.rglob("*")
            if item.is_file()
        }
