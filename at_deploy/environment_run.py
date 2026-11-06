"""The `podman run` that IS a service, and the state folder and run directory
it is made from (§7a, item 50).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from at.core import files
from at.services import caddy as caddy_service
from at_deploy.environment_base import CADDY, LABEL
from at_deploy.environment_models import Image, Mount, Port, Service
from at_deploy.environment_paths import container, gate_materialized, materialized, run_dir, state
from at_deploy.environment_secrets import _opened, _text


def ports_of(service: Service) -> tuple[Port, ...]:
    """The ports a service publishes, resolved NOW.

    `ports` is a tuple for every service but one, and the exception is the
    edge's (`_caddy_ports`): what address it publishes on is §7e's, and
    §7e is measured when the environment comes up — the machine's address on
    the private network, or the loop. A value read at import would be a value
    that stopped being true the moment the person joined a network. It is a
    callable for the same reason `command` and `writes` are.
    """
    return service.ports() if callable(service.ports) else service.ports


def env_of(service: Service, key: bytes | None) -> tuple[tuple[str, str], ...]:
    """The variables a service is handed, resolved NOW — the same shape, the same
    reason (`ports_of`): what one of them names is the folder. `key` is the
    key of this subida, or `None` — `_webapp_env`'s to read, and every
    other service's to ignore."""
    return service.env(key) if callable(service.env) else service.env


def addresses(service: Service) -> tuple[str, ...]:
    """The host addresses this service publishes on, in the order declared."""
    return tuple(dict.fromkeys(port.address for port in ports_of(service)))


def run_argv(service: Service, image: Image, key: bytes | None = None) -> list[str]:
    """The `podman run` that IS the service: every decision about it, in one list.

    Detached, named, labeled, on its network, publishing what it declares and
    mounting what it mounts — and then the image at the pin, and the command
    when the service has one. There is no restart policy on purpose: §3 says AT
    has no watchdog and does not propose to have one, and a container that comes
    back on its own is one.

    `key` is the key this subida derived, or `None` — passed straight through to
    `env_of`, which is the one reader that knows what to do with it.

    **Every container drops every capability** (`--cap-drop=ALL`), and the one
    exception is the edge: Caddy listens on 443 inside its own network namespace,
    and binding a port below the unprivileged floor takes `NET_BIND_SERVICE`. That
    exception is written here, by name, and tested. The seccomp profile is the
    Podman default, so the argv says nothing about it — and it never says
    `seccomp=unconfined`.
    """
    argv = [
        "run",
        "--detach",
        "--name", container(service.name),
        "--label", f"{LABEL}={service.name}",
        "--network", service.network,
        "--cap-drop=ALL",
    ]
    if service.name == CADDY:
        argv.append("--cap-add=NET_BIND_SERVICE")
    for port in ports_of(service):
        argv += ["--publish", port.published()]
    for mount in service.mounts:
        argv += ["--volume",
                 mount.volume(state(service.name), materialized(service.name))]
    for name, value in env_of(service, key):
        argv += ["--env", f"{name}={value}"]
    argv.append(image.reference())
    if service.command is not None:
        argv += list(service.command())
    return argv


def _prepare(service: Service, key: bytes | None) -> Path:
    """The service's state folder, ready: the folders it mounts, and its files.

    The files go in the order the manifest declares them, which is the order a
    writer that reads what another one wrote depends on — and each writer is the
    service's own (§ `Service.writes`), so nothing here knows what a Caddyfile
    or an Authelia configuration is.

    **And what it wrote is materialized for the container** (`_materialize`), in
    the same act: the folder is the source and the run directory is the copy
    that serves the boot, and a call site that wrote one and forgot the other
    would be a container reading yesterday's file. `key` é a chave derivada
    desta subida, e ela desce até lá porque o que a pasta guarda de um valor
    sorteado é o envelope: montá-lo é abri-lo.
    """
    where = state(service.name)
    where.mkdir(parents=True, exist_ok=True)
    for mount in service.mounts:
        # Only the service's OWN paths are born here: a `Mirror` mounts the
        # Working Folder, which exists — creating it would be AT writing in
        # the person's folder for no reason —, and a `Gate` mounts a file, whose
        # folder is the run directory's and born with the copy.
        #
        # **Um `file` é criado VAZIO e nunca de novo** (`touch`): o runtime
        # criaria um DIRETÓRIO no lugar de uma fonte que não existe, e o
        # provedor morreria no `open` — mas apagar o que o container já escreveu
        # ali seria perder o aviso que esta montagem existe para guardar.
        if isinstance(mount, Mount) and mount.host:
            path = where / mount.host
            if mount.file:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
            else:
                path.mkdir(parents=True, exist_ok=True)
    for name, body in service.writes:
        files.atomic_write_text(where / name, body())
    _materialize(service, key)
    return where


def _run_place(where: Path) -> Path:
    """Uma pasta do diretório de execução, criada — e com o modo DELE.

    O diretório de execução nasce `0700`, e não é detalhe: ele pode cair no
    temporário do sistema, onde ele é de todo mundo, e o que ele guarda é a
    cópia CLARA do que a pasta sela. O modo do ARQUIVO em si continua sendo o da
    umask: quem o lê é o container, e a porta é a pasta.
    """
    run_dir().mkdir(mode=0o700, parents=True, exist_ok=True)
    where.mkdir(parents=True, exist_ok=True)
    return where


def _materialize(service: Service, key: bytes | None) -> Path:
    """A cópia que o container LÊ, fora da pasta (§ `RUN_ENV`, item 50).

    **A pasta de estado é a FONTE e este é o diretório de execução**: o `up`
    escreve na pasta e copia para cá, e o `--volume` do serviço aponta para cá.
    **E o que ele copia é o valor, e não o envelope**: cada envelope que o
    arquivo carrega é aberto aqui, com a Chave desta subida, e é o texto aberto
    que o container monta — é esta função que faz de um arquivo selado na pasta
    um arquivo que o container consegue ler (item 50, pergunta 2).

    O que NÃO vem para cá são as pastas que o container enche: elas continuam na
    pasta de estado, que é a que o backup leva, e um `Mount` com `host` não
    passa por aqui.
    """
    where = materialized(service.name)
    if not service.writes:
        # Um serviço que não lê arquivo nenhum da pasta não tem o que copiar: o
        # WebApp (§7c) lê a pasta INTEIRA que monta, e o que o alcança é o
        # `Mirror`. Um diretório vazio no diretório de execução não seria o que
        # ele monta, e sim um resto.
        return where
    _run_place(where)
    for name, _ in service.writes:
        body = _opened(_text(state(service.name) / name), service.name, key)
        files.atomic_write_text(where / name, body)
    return where


def _materialize_gate(key: bytes | None) -> Path:
    """A cópia clara do portão, para o leitor que a lê montada (§ `GATE_MOUNT`).

    O portão é escrito na pasta pelo `draw_gate` e lido de lá pelos dois leitores
    de fora do container — o Caddy que AT gera, que o carrega dentro do
    `Caddyfile`, e o próprio AT. O WebApp é o terceiro e o único de dentro, e
    ele o lê por uma montagem própria; esta é a cópia, e ela é o valor ABERTO —
    a pasta guarda o envelope, e quem o abre é esta linha.
    """
    where = gate_materialized()
    _run_place(where.parent)
    body = _opened(_text(caddy_service.gate_file()), CADDY, key)
    files.atomic_write_text(where, body)
    return where


def _clear_run_dir() -> None:
    """O diretório de execução nasce vazio, e o `up` o reescreve inteiro.

    Ele é a cópia que serve ESTA subida: um serviço que saiu do manifesto não
    pode deixar a cópia dele para trás, e o que sobrou de uma subida anterior não
    é estado — estado é o que a pasta guarda. O `down` usa a mesma porta, e é por
    isso que ele é a metade que MORRE: o que o container enche está na pasta de
    estado, e o que se perde aqui é só a cópia.
    """
    shutil.rmtree(run_dir(), ignore_errors=True)
