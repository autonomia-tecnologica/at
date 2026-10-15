"""Server-Sent Events: a escrita na pasta vigiada chega à aba aberta sem
recarregar (TASK-128, fatia 2/3).

**O vigia só detecta e despacha** (`at/core/vigia.py`) — quem decide o que
fazer com o despacho é o consumidor, e o consumidor aqui é este `Broadcaster`.
O que ele faz é repassar, e nada mais: não sabe QUAL arquivo mudou (o
`vigia.Event` morre em `beat()`, antes de chegar aqui), porque quem lê o
aviso no navegador relê a página inteira — não um arquivo específico.

**Uma instância por SERVIDOR, como `session.Sessions`** (`app.py`): duas
instâncias do WebApp — a suíte sobe uma por teste — não podem compartilhar
as conexões abertas de uma com a outra.

**Cada aba é uma fila própria.** `publish` não sabe quantas abas há, nem
precisa: ele só põe um sinal em cada fila cadastrada, e quem lê essa fila é a
própria conexão HTTP que a abriu (`app.py`'s `_get_events`) — uma aba que
nunca pediu nada não tem fila para encher.
"""

from __future__ import annotations

import queue
import threading


class Broadcaster:
    """As filas de toda aba aberta, e o aviso que enche todas de uma vez."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: list[queue.Queue] = []

    def subscribe(self) -> queue.Queue:
        """Uma fila nova, cadastrada — o que uma conexão SSE lê enquanto
        fica de pé."""
        made: queue.Queue = queue.Queue()
        with self._lock:
            self._queues.append(made)
        return made

    def unsubscribe(self, made: queue.Queue) -> None:
        """Tira a fila do cadastro — a conexão que a abriu já se foi."""
        with self._lock:
            if made in self._queues:
                self._queues.remove(made)

    def publish(self) -> None:
        """Avisa toda fila cadastrada — uma escrita na pasta vigiada."""
        with self._lock:
            targets = list(self._queues)
        for made in targets:
            made.put(None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._queues)
