"""Caddy: o segredo do portão — onde mora, como se sorteia e como se lê."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from at.core import files
from at.encryption import vault
from at.services.caddy_base import GATE_BYTES, GATE_FILE, GATE_PATH_ENV, directory


def gate_file() -> Path:
    """`App/services/caddy/gate` — the secret's file, drawn by whoever installs the gate.

    É o arquivo da PASTA, e dois desenhos escrevem nele — nunca os dois na
    mesma pasta. O container path o sela (`at_deploy.environment.draw_gate`,
    item 50, porque aquela pasta de estado é copiada sem criptografia); o
    bundle hospedado o escreve em claro (`draw_gate`, abaixo, logo abaixo
    desta função) — a mesma razão do `App/` nunca precisar do selo: nada
    aqui atravessa fronteira de container. Quem lê pode estar lendo outro
    arquivo (`gate_handed` e `gate_secret`), e é por isso que este nome e a
    leitura são duas coisas.
    """
    return directory() / GATE_FILE


def _drawn_in_the_clear(where: Path) -> str:
    """O valor que um arquivo já guarda, ou um sorteado agora e mantido dali
    em diante — em CLARO, e de propósito (`draw_gate`'s own docstring diz
    por quê). `draw_gate` é a face disto.

    **O nome do arquivo é o mesmo que o caminho container usa**
    (`at_deploy.environment.gate_file`, na mesma `caddy.directory()`), porque
    os dois são a mesma pasta `App/services/caddy/` do mesmo Caddy — só que o caminho
    container SELA o que escreve ali (item 50), e o que está selado não é o
    valor em claro que este caminho lê. Um envelope encontrado aqui não é um
    valor já sorteado — é o OUTRO caminho, e o sorteio é o mesmo de um arquivo
    ausente.
    """
    try:
        held = where.read_text(encoding="utf-8").strip()
        if held and not vault.envelopes(held):
            return held
    except FileNotFoundError:
        pass
    value = secrets.token_urlsafe(GATE_BYTES)
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where, f"{value}\n")
    return value


def draw_gate() -> str:
    """O segredo do portão, sorteado uma vez e mantido em CLARO (§6, bundle).

    **Este é o desenho do CAMINHO HOSPEDADO**, e não o do item 50: a pasta
    deste Caddy (`App/services/caddy/`) nunca é copiada para dentro de um container —
    ela é a cópia de trabalho de uma única máquina, já coberta pelo backup —,
    então o valor que o `header_up` carrega não precisa do envelope da Chave
    Principal que o caminho container exige (`at_deploy.environment.
    draw_gate`). Um valor já sorteado não é sorteado de novo: rotacioná-lo
    derrubaria toda sessão que o WebApp já aceitou pelo mesmo Caddy.
    """
    return _drawn_in_the_clear(gate_file())


def gate_handed() -> Path | None:
    """A cópia do portão que o AMBIENTE entregou — ou `None`, fora do container.

    Item 50: o que o container monta é a cópia que o `up` materializou fora da
    pasta, e a pasta guarda a FONTE. O WebApp é o leitor que a recebe, e a
    variável é o nome que o ambiente diz (`GATE_PATH_ENV`). Sem ela — o AT
    rodando da pasta, no caminho hospedado — não há cópia entregue, e o que se
    lê é o arquivo da pasta.
    """
    handed = os.environ.get(GATE_PATH_ENV, "").strip()
    return Path(handed) if handed else None


def gate_secret() -> str | None:
    """The M2M secret between the Caddy and the WebApp, when there is a gate.

    §7b: the secret is drawn by AT at installation, written into the Caddyfile
    AT generates, attached by the Caddy to every request carrying an identity,
    and refused by AT to whoever does not bring it (`ui/webapp/app.py`). The
    line in the Caddyfile is this file's, and it is written only when the secret
    is there — a hosted folder with no gate has no file and gets no line.

    **O que ele lê é a cópia que o ambiente entregou, quando há uma**
    (`gate_handed`), e o arquivo da pasta quando não há: é esta função que faz
    do portão materializado o que o WebApp de dentro do container prova.
    """
    where = gate_handed() or gate_file()
    try:
        secret = where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return secret or None
