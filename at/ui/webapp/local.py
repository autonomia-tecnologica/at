"""O modo LOCAL: `at-cli` sem palavra sobe o app numa porta efêmera, abre o
navegador e morre com ele (TASK-169, fatia 1/3).

**Forms nasce desligado neste modo** — é a decisão já tomada no backlog, e é
o que faz `run` chamar `webapp.make_server(asks=False, ...)`: não há ator a
provar, e a tela de entrada nunca é desenhada. O que protege a porta não é
Forms, é o TOKEN de uso único que este módulo sorteia no boot
(`webapp.Handler._local_gate`): a pessoa não digita nada — o navegador já
abre autenticado, pela URL — e qualquer outro processo da máquina, sem o
token, não entra. Loopback alcança todo mundo na máquina local; o token é o
que separa "a pessoa" de "a máquina".

**As duas mortes.** Com moldura (um navegador Chromium-like, aberto por
`--app=` com um perfil PRÓPRIO) o navegador É um processo filho, e este é o
que o espera: a janela fechando é o processo saindo, e `run` sai com ele. Sem
moldura (uma aba do navegador padrão — `webbrowser.open` entrega a um
navegador que já estava rodando, com as abas da pessoa, e não devolve
processo nenhum) não há o que esperar, e a morte é por OCIOSIDADE: nenhuma
aba com uma conexão `/api/events` aberta, por `IDLE_TIMEOUT` a fio
(`_idle_watch`). Essa conexão É o sinal de vida da página — cada aba aberta
mantém uma, com um `keep-alive` a cada `app.EVENTS_HEARTBEAT` — e ela só
desaparece quando a aba fecha ou o navegador cai, nunca por um timer de JavaScript
que o navegador congelou numa aba em segundo plano (a reconexão de um
`EventSource` é da pilha de rede do navegador, não de um timer da página).
"""

from __future__ import annotations

import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import webbrowser
from collections.abc import Callable

from at import i18n
from at.ui.webapp import app as webapp

# Quanto tempo sem NENHUMA aba com `/api/events` aberta antes do processo se
# encerrar sozinho, no caso sem moldura (§ acima). Generoso de propósito: o
# próprio navegador pode demorar para abrir e conectar, e uma reconexão de
# rede não é instantânea — um valor curto demais mataria o processo debaixo
# da própria pessoa.
IDLE_TIMEOUT = 600.0

# De quanto em quanto tempo `_idle_watch` confere — nunca o timeout inteiro
# de uma vez, para a morte não atrasar mais do que isso além do N prometido.
IDLE_POLL = 5.0

# Os nomes, por plataforma, de um navegador Chromium-like o bastante para
# `--app=` desenhar uma janela sem moldura de abas — a decisão desta fatia
# sobre "como o binário descobre". `shutil.which` cobre Linux e Windows (os
# instaladores desses navegadores põem o executável no PATH); o macOS não
# põe o `.app` no PATH, e os três caminhos fixos são onde cada um sempre se
# instala.
_CHROMIUM_NAMES = (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "brave-browser", "microsoft-edge", "msedge", "chrome",
)
_CHROMIUM_MAC_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def _chromium_executable() -> str | None:
    """O caminho de um navegador Chromium-like, ou `None` quando a máquina não
    tem um que este módulo reconheça — e então a janela nasce sem moldura."""
    for name in _CHROMIUM_NAMES:
        found = shutil.which(name)
        if found:
            return found
    for path in _CHROMIUM_MAC_PATHS:
        import os

        if os.path.isfile(path):
            return path
    return None


Opened = tuple[subprocess.Popen, str] | None


def open_browser(url: str) -> Opened:
    """Abre `url` — com moldura e processo filho quando a máquina tem um
    Chromium-like, numa aba do padrão quando não.

    O PERFIL PRÓPRIO (`--user-data-dir` num diretório temporário) é o que
    faz `--app=` nascer um processo NOVO e esperável: um Chromium que já
    estava de pé, sem perfil próprio, só entrega a URL à janela existente e
    sai — e aí não haveria processo nenhum para `run` esperar.
    """
    exe = _chromium_executable()
    if exe is None:
        webbrowser.open(url)
        return None
    profile = tempfile.mkdtemp(prefix="at-local-")
    try:
        process = subprocess.Popen(
            [exe, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        shutil.rmtree(profile, ignore_errors=True)
        webbrowser.open(url)
        return None
    return process, profile


def _idle_watch(server: "webapp.Server", timeout: float,
                 pause: Callable[[float], None], poll: float) -> None:
    """Fica de pé até que nenhuma aba tenha dado sinal de vida por `timeout`
    a fio — então volta, e é a volta que diz a `run` para derrubar o processo.

    O sinal de vida É a conexão `/api/events` de uma aba aberta
    (`webapp.events.Broadcaster`, `len(server.events)`); nada aqui lê o
    conteúdo de um aviso, só se existe alguém ouvindo.
    """
    quiet_since: float | None = None
    while True:
        pause(poll)
        if len(server.events) > 0:
            quiet_since = None
            continue
        now = time.monotonic()
        if quiet_since is None:
            quiet_since = now
        elif now - quiet_since >= timeout:
            return


def run(opener: Callable[[str], Opened] = open_browser,
        idle_timeout: float = IDLE_TIMEOUT, poll: float = IDLE_POLL,
        pause: Callable[[float], None] = time.sleep) -> int:
    """`at-cli` sem palavra: a porta efêmera, o token, o navegador, e a morte
    que o acompanha.

    `opener`, `idle_timeout`, `poll` e `pause` são as mesmas costuras que
    `webapp.beat` já expõe (`times`/`pause`) — o que um teste troca para
    provar as duas mortes sem de fato abrir um navegador nem esperar minutos.
    """
    webapp.keys.boot()
    token = secrets.token_urlsafe(32)
    server = webapp.make_server(0, webapp.HOST, asks=False, local_token=token)
    port = server.server_address[1]
    url = f"http://{webapp.HOST}:{port}/?k={token}"

    threading.Thread(target=server.serve_forever, daemon=True,
                      name="at-webapp-local").start()
    webapp.start_clock(server)

    print(i18n.tr("webapp.local_serving", url=url))
    opened = opener(url)
    try:
        if opened is not None:
            process, _profile = opened
            try:
                process.wait()
            except KeyboardInterrupt:
                pass
        else:
            _idle_watch(server, idle_timeout, pause, poll)
    finally:
        server.shutdown()
        server.server_close()
        if opened is not None:
            _process, profile = opened
            shutil.rmtree(profile, ignore_errors=True)
    return 0
