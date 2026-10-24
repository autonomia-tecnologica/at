"""The manifest's vocabulary (§7a): Image, Port, Mount, Mirror, Gate and Service.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from at.core import paths
from at_deploy.environment_base import LOOP, NETWORK, PIN_DIGITS, PIN_PREFIX
from at_deploy.environment_paths import gate_materialized

# ------------------------------------------------------------ the manifest ---

@dataclass(frozen=True)
class Image:
    """One image at the pin: the repository, the version and the digest.

    **Two readings, because there are two readers, and they were one.** A tag
    moves and a digest does not (§3), so the digest is what pins — and what pins
    is what `podman run` takes and what the folder records, and neither can do
    without it. That is `.reference()`. A PERSON reading a status line has no
    use for sixty-four characters of hexadecimal: what they need is which image
    and which release, and that is `.shown()`.

    They were one function, and the pin leaked into every sentence a person
    reads. The one who wants to check that an image did not move reads the
    folder's own record — the promise is kept by the digest being USED, not by
    its being printed.
    """

    repo: str
    version: str
    digest: str

    def reference(self) -> str:
        """`repo:version@digest` — the machine's reading: what runs, and what is
        recorded. A tag moves, a digest does not."""
        return f"{self.repo}:{self.version}@{self.digest}"

    def shown(self) -> str:
        """`repo:version` — the person's reading, without the pin."""
        return f"{self.repo}:{self.version}"

    def at_the_pin(self) -> bool:
        """Whether this is a pin at all, in the shape §3 demands.

        The suite reads this: an image with no digest, or with a digest that is
        not one, is an image that would move under the person's feet — and what
        §3 says cannot move is exactly that.
        """
        body = self.digest[len(PIN_PREFIX):]
        return (
            bool(self.version)
            and self.digest.startswith(PIN_PREFIX)
            and len(body) == PIN_DIGITS
            and all(character in "0123456789abcdef" for character in body)
        )


@dataclass(frozen=True)
class Port:
    """A port published on the host, on an address AT names out loud.

    The address defaults to the loop and is declared per service, which is the
    measured rule made visible: a port published on `0.0.0.0` is a port nothing
    in the host's firewall rules covers, so the exception — a service that must
    be reachable on a private network address — has to be written here to exist.
    """

    port: int
    protocol: str = "tcp"
    address: str = LOOP

    def published(self) -> str:
        """The argument the runtime reads: `address:host:container/protocol`."""
        return f"{self.address}:{self.port}:{self.port}/{self.protocol}"


@dataclass(frozen=True)
class Mount:
    """State of the instance, inside the container — a folder, or a file.

    `host` is relative to the service's own state folder — `App/services/<name>/`
    — and empty means the folder itself: §7 puts every service's persistent
    state there, so a service whose state does not fit is a service that does
    not enter, and what it mounts is always inside what the backup covers.

    **Which of the two folders it mounts is what `host` decides, and it is the
    item-50 line.** With no `host` it is the folder AT MATERIALIZES — the
    service's own, which the container only READS —, and what the volume points
    at is the copy in the run directory, outside the person's folder. With a
    `host` it is a folder the CONTAINER fills — the provider's database, the
    Caddy's storage —, and it stays in the state folder:
    what a container writes has to outlive it for the backup to bring it back.

    **`file` é a exceção da exceção, e ela existe porque o serviço a exige.** O
    provedor abre o caminho do notificador como ARQUIVO, e um diretório montado
    ali é um container que morre no primeiro `open` (`is a directory`): o que
    ele ESCREVE tem de ser o arquivo, e não uma pasta onde ele caiba. A fonte,
    então, é um arquivo da pasta de estado — que o `_prepare` cria vazio, porque
    o runtime criaria um DIRETÓRIO no lugar dele —, e o serviço o abre e o
    preenche. Um caminho que já exista com a outra forma é recusado antes de
    tentar (`_state_trouble`), como todo o resto da forma do estado.
    """

    container: str
    host: str = ""
    file: bool = False

    def volume(self, where: Path, materialized: Path) -> str:
        """The argument the runtime reads, with the SELinux label it needs.

        `:Z` is podman's word for "give this a private label": without it an
        enforcing host stops the container at the first read, and where there is
        no SELinux it is ignored. Both sources are things AT created, so the
        relabel touches nothing of the person's.
        """
        source = where / self.host if self.host else materialized
        return f"{source}:{self.container}:Z"


@dataclass(frozen=True)
class Mirror:
    """The Working Folder, mounted at the SAME absolute path it has outside.

    §7a's measured contract, and the only mount that is not a service's state
    folder: the app's own database stores the absolute path, so the same path
    has to exist inside the container or every row of the library points at
    nothing. It is what §7c mounts — and it is also where the binary lives, so
    what the container runs is what the folder is, and nothing of the machine
    beyond that mount is reachable from inside.

    It answers the same `volume` as `Mount` so that the argv has one way of
    asking, and it ignores both folders it is handed: this folder is not the
    service's, it is the person's.
    """

    def volume(self, where: Path, materialized: Path) -> str:
        root = paths.working_folder()
        return f"{root}:{root}:Z"


@dataclass(frozen=True)
class Gate:
    """O portão materializado, montado para o leitor que o lê por outro caminho.

    §7b's secret has three readers, and only one of them is inside a container
    (§ `GATE_MOUNT`): the Caddy reads it inside the `Caddyfile` AT writes, the
    provider never reads it — §7b is explicit that the gate is the Caddy's and
    the WebApp's, and that Authelia never sees it —, and the WebApp reads it
    beside every other file of the folder, through the `Mirror`. That is the
    file of the FOLDER, and the day the vault seals it nobody inside the
    container opens it. So the run directory carries the clear copy and this
    mounts it, and `at-cli` is told where it is (`caddy.GATE_PATH_ENV`).

    It is a FILE and not a folder, and it answers the same `volume` as `Mount`
    for the same reason `Mirror` does: the argv has one way of asking.
    """

    container: str

    def volume(self, where: Path, materialized: Path) -> str:
        return f"{gate_materialized()}:{self.container}:Z"


@dataclass(frozen=True)
class Service:
    """A service of the environment: its image at the pin, and how it runs.

    `writes` is what AT puts in the service's state folder before it starts —
    a name and the writer that produces the text, one pair per file — and every
    writer is the service's own, because what a service reads is the service's
    business and not the orchestration's.

    `command` is what the container RUNS after its image, and `None` means the
    image's own entrypoint — which is most of them. §7c's WebApp is the one that
    is not: its image is a base with nothing of AT's in it, so what it runs is
    the artifact the folder carries (`binary`). It is a callable for the same
    reason `writes` is: it reads where the folder is, and where the folder is is
    resolved at RUN time and not when this file was imported.
    """

    name: str
    label: str
    image: Image
    # A tuple, or a callable that answers one when the environment comes up —
    # the SITE's is the second, and `ports_of` is the one reader that knows.
    ports: Callable[[], tuple[Port, ...]] | tuple[Port, ...] = ()
    mounts: tuple[Mount | Mirror | Gate, ...] = ()
    command: Callable[[], tuple[str, ...]] | None = None
    # What the service is TOLD about the environment it is part of — the
    # environment's own words, handed to the container as its variables. A
    # container cannot see the host's loop, so a service that has to reach
    # another one is told the name to use instead of guessing (§7c's WebApp and
    # its gate). It is a callable for the same reason `ports` is, where a value
    # is not a word but a path: what one of them names is the folder. The
    # callable takes the key THIS subida derived — `None` when there is none —
    # because §7c's WebApp is handed derived keys through this same door
    # (`_webapp_env`), and a service with nothing to derive ignores the
    # argument, exactly as it ignores every other tuple entry it does not need.
    env: (Callable[[bytes | None], tuple[tuple[str, str], ...]]
          | tuple[tuple[str, str], ...]) = ()
    writes: tuple[tuple[str, Callable[[], str]], ...] = ()
    network: str = NETWORK
