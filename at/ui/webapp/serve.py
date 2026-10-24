"""The server (§3, §4): `Server`, the `ThreadingHTTPServer` that holds the
sessions, the strongbox links and the events broadcaster of ONE AT on one port,
and `make_server`, which builds it with the `Handler`.

Moved out of `app.py` (B-6) without a change of behaviour. `HOST` and
`DEFAULT_PORT` came along because `make_server` answers with them as defaults.
`app.py` imports the names back.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from at.ui.webapp import events, session, strongbox_links

HOST = "127.0.0.1"
DEFAULT_PORT = 12345


class Server(ThreadingHTTPServer):
    """The server, with the sessions it holds.

    The registry lives HERE and not in a module-level name: a server is one AT
    on one port, and two of them — which is what the suite builds, one per test
    — are two of them, each with its own entrances open. A shared registry would
    hand one test's session to another test's folder.

    **And the ASKING lives here for the same reason** (`asks`): whether this
    server draws an entrance is a fact of THIS server, and `run` is the one that
    decides it from the artifact (`paths.source`). The suite builds bare servers,
    which ask as the bundle does — a test that wants the dev answer asks for it
    out loud (`make_server(asks=False)`), which is what keeps every other test's
    refusals exactly what they were.

    **`daemon_threads = True`** (TASK-128, fatia 2/3): uma conexão `/api/events`
    fica de pé por uma aba inteira, às vezes mais do que o processo — e uma
    thread não-daemon é uma thread que o interpretador espera no fim, mesmo
    depois do servidor ter fechado. É a mesma razão do relógio ser DAEMON
    (`beat`'s own docstring): o que fica de pé morre com o processo, e nada
    tem de derrubá-lo à mão.

    **`local_token` é do MODO LOCAL** (TASK-169, fatia 1/3; `at.ui.webapp.local`)
    e `None` em toda outra subida — é o que `Handler._local_gate` pergunta antes
    de qualquer outra coisa, e com ele ausente a pergunta nem se faz.

    **`folder_cancelled` é a RECUSA da pergunta da pasta** (TASK-169, fatia
    2/3): `_post_folder` o marca quando a página recusa, e `local.run` é
    quem dorme nele — é o sinal que fecha a janela do mesmo jeito que
    fechá-la por fora já fechava. Sempre um `Event` novo, numa pasta
    confirmada ou não: marcá-lo onde não há ninguém esperando não custa nada.

    **`request_queue_size = 128`** (a FILA do servidor): o `socketserver`
    deixa 5, e o servidor é HTTP/1.0 — sem keep-alive, cada request é uma
    conexão nova. Com 300 conexões simultâneas o kernel descartava o SYN
    (medido: 298 timeouts, 6089 `TcpExtListenOverflows`): a fila encheu e o
    pedido morreu antes de chegar. A fila é do kernel (`listen()`), e 128 é o
    que aguenta a rajada que a WebApp provoca — cada aba, cada `<img>`, cada
    seek de vídeo.
    """

    daemon_threads = True
    request_queue_size = 128

    def __init__(self, address: tuple[str, int],
                 handler: type[BaseHTTPRequestHandler], asks: bool = True,
                 local_token: str | None = None) -> None:
        super().__init__(address, handler)
        self.sessions = session.Sessions()
        self.strongbox_links = strongbox_links.Links()
        self.events = events.Broadcaster()
        self.asks = asks
        self.local_token = local_token
        self.folder_cancelled = threading.Event()


def make_server(port: int = DEFAULT_PORT, host: str = HOST, asks: bool = True,
                 local_token: str | None = None) -> Server:
    # `Handler` lives in `app.py`, which imports this module: asking for it here,
    # and not at the top, is what keeps the import from being a cycle.
    from at.ui.webapp.app import Handler

    return Server((host, port), Handler, asks=asks, local_token=local_token)
