"""The SSE route: `GET /api/events`, the stream that tells an open tab the
watched folder changed.

Moved out of `app.py` (B-6) without a change of behaviour. `SseRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `server.events` from
the `Handler`'s server. This module does not import `app` at the top.
`app.py` imports `EVENTS_HEARTBEAT` back.
"""

from __future__ import annotations

import queue

from at.ui.webapp.routes_base import RouteBase

# Quanto tempo uma conexão `/api/events` fica sem escrever nada antes de
# mandar um comentário de keep-alive (TASK-128, fatia 2/3). `EventSource`
# ignora toda linha que começa com `:` — não dispara `onmessage` —, então o
# keep-alive não é um evento, é só o que mantém a conexão viva através de um
# proxy (o Caddy) que fecharia um socket ocioso por tempo demais, e o que
# deixa este processo notar uma aba que fechou sem esperar a próxima escrita
# na pasta vigiada.
EVENTS_HEARTBEAT = 20.0


class SseRoutes(RouteBase):
    def _get_events(self) -> None:
        """A conexão fica de pé: a cada escrita em `Arquivos/`, uma linha sai
        (TASK-128, fatia 2/3).

        **O corpo nunca diz QUAL arquivo mudou.** A aba que recebe o aviso
        relê a página inteira (`poke()`, do lado do navegador) — dizer o
        caminho aqui seria um campo que ninguém lê, a mesma razão de
        `vigia.Event` carregar só o caminho e nada além dele.

        **Uma fila por conexão, e não um vigia por aba** (`events.Broadcaster`):
        o vigia que varre `Arquivos/` vive uma vez só, no relógio (`beat()`),
        e publica uma vez por rodada — é o `Broadcaster` que copia esse aviso
        para a fila de toda aba aberta.

        Sem `Content-Length`: o corpo não tem fim conhecido, e é isso que
        `text/event-stream` pede — a conexão fecha quando a aba fecha, não
        quando um tamanho se esgota.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        made = self.server.events.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    made.get(timeout=EVENTS_HEARTBEAT)
                    payload = b"data: changed\n\n"
                except queue.Empty:
                    payload = b": keep-alive\n\n"
                self.wfile.write(payload)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            # A aba fechou — não é uma falha deste processo, é o fim de uma
            # conexão que nunca prometeu durar.
            pass
        finally:
            self.server.events.unsubscribe(made)
