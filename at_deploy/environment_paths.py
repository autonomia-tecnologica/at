"""Where the environment's names and folders are: the container's name, the
service's state folder, the run directory and the pin file.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from at.core import paths
from at.services import caddy as caddy_service
from at_deploy.environment_base import GATE_DIR, PREFIX, RUN_ENV, RUN_ID, RUN_SERVICES


def container(name: str) -> str:
    """The name of the container AT runs for that service.

    It is declared here — above the manifest that uses it, and far above the
    orchestration — because it is a NAME and not a step: the service's container,
    the gateway name another service reaches it by (§7c's `GATE_ENV`) and what
    `down` removes are the same word said once.
    """
    return f"{PREFIX}{name}"


def state(name: str) -> Path:
    """`App/services/<serviço>/` — where that service's state lives (§7)."""
    return paths.service_dir(name)


def run_dir() -> Path:
    """O diretório de execução da pasta: o que o container lê (§ `RUN_ENV`).

    Fora da Pasta de Trabalho por definição — é a metade que morre com o
    ambiente —, e resolvido a cada chamada, como a própria pasta: o
    `XDG_RUNTIME_DIR` que estiver de pé naquele momento é o de lá.
    """
    root = os.environ.get(RUN_ENV, "").strip()
    base = Path(root) if root and Path(root).is_dir() else Path(tempfile.gettempdir())
    return base / f"{PREFIX}{_folder_id()}"


def _folder_id() -> str:
    """A pasta, reduzida a um id — dois ambientes nesta máquina não se cruzam.

    O CAMINHO da pasta e não o nome dela: duas pastas de mesmo nome em lugares
    diferentes são dois ambientes, e o que decide qual é qual tem de ser o que
    as distingue de fato.
    """
    name = str(paths.working_folder()).encode("utf-8")
    return hashlib.sha256(name).hexdigest()[:RUN_ID]


def materialized(name: str) -> Path:
    """`<run>/services/<serviço>/` — a cópia que aquele container monta."""
    return run_dir() / RUN_SERVICES / name


def gate_materialized() -> Path:
    """`<run>/caddy/gate` — a cópia clara do portão, para quem o lê montado."""
    return run_dir() / GATE_DIR / caddy_service.GATE_FILE


def gate_opened() -> str | None:
    """O portão como o CONTAINER o lê — a cópia aberta, ou `None` sem cópia.

    **Quem lê o valor do portão de fora do container tem de ler daqui e não do
    arquivo da pasta** (item 50): o da pasta é o ENVELOPE, e quem compara o
    cabeçalho é o WebApp de dentro, que lê a cópia que a subida montou. Mandar o
    envelope seria uma prova que não prova — o portão acusado de recusar a
    identidade que ele aceita (`switch.witness`).

    Sem cópia não há segredo: o ambiente não está de pé, e é isso que a resposta
    diz.
    """
    try:
        opened = gate_materialized().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return opened or None


def pin_file() -> Path:
    """`App/services/images.json` — the pin this folder IS at, per service."""
    return paths.services_dir() / "images.json"
