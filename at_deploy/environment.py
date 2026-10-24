"""The container environment (§7a): the pinned images, the services, and the switch.

§7a is one switch and one rule. The switch: the person needs Podman, AT checks
whether it exists, and if it does not it offers the two ways out — install it, or
continue on the hosted path. **AT does not install it**, because installing a
package is an act of the person's machine and §3 spends elevation only on an
explicit request. The rule: from there on AT orchestrates the environment and
the services, which come up as containers **from pinned images** (§3, Dependência
externa).

**The manifest is this file's table, and the folder has its own pin.** `SERVICES`
is what the binary carries: the services of §7a, each with the image it runs —
repository, version and digest. The folder records the pin it IS at in
`App/services/images.json`, and the difference between the two is §3's sentence
about updating: the pin only moves forward, and an instance AHEAD of the binary's
pin warns and proceeds, because it is not downgraded. That is why the comparison
exists at all: a folder carried to a machine running an older AT keeps running
what it has.

**Every decision about a service is one argv.** `run_argv` is the whole of what
AT decides about a container, and it is a list: what it is called, which network
it joins, where it publishes, what it mounts, and the image at the pin. Two of
those decisions come from the retired environment, measured there and inherited
here: a host deny-list does not cover a published container port — the port goes
through DNAT and the `input` hook never sees it — so **what closes the LAN is
publishing on loopback**, never a firewall rule; and a container published on an
address the machine does not have yet comes up **running and without its port**,
so the orchestrator waits for the address to exist before it binds.

**How the services reach each other is the NETWORK, and there is one of them.**
A container's `127.0.0.1` is itself and nobody else, and two podman networks do
not reach each other at all — no route, and the name only resolves inside the
network that gave it. So what decides where a service stands is nothing but WHO
IT HAS TO TALK TO: the Caddy reaches the WebApp (its `reverse_proxy`), the
WebApp reaches the gate (its own "is my portal standing"), and the Caddy reaches
the gate (`forward_auth`) — the three stand together, and whoever has business
with them stands with them. Separating anything else would buy nothing, and
what keeps the WebApp closed on a network it shares is the gate secret (§7b),
not a second segment.

**What each service runs.** The `caddy` is up as the edge that publishes AT —
the same Caddyfile generator the hosted path reads, because it is the same
Caddy answering the same questions, and what the two paths answer DIFFERENTLY
is what an address means on each side: the storage is a path and not a
decision (§7a), and the backend, the provider and the bind are the container
path's (`_caddy_conf`). The `identity-provider` is up as §7b's gate: Authelia,
configured by AT to be the one that proves who is calling, with AT standing
behind it as an app and not as an exception — and the gate secret, drawn at
installation, is the line that says the request came through it. And the
`webapp` is up as §7c's container: the WebApp, moved off the person's machine
and behind the gate, answering on the network because the loop is a place
nobody in the environment can reach.

**There is no DNS of the environment's own, and that is a decision and not a
gap left by one** (TASK-187): the name the edge used to answer for was its own
invention — `at.local` — and nothing outside the machine could resolve it
without a `dnsmasq` of AT's to ask. Reached over the private network (§7e), the
edge is named by the NETWORK's own answer instead (`vpn.name`, `site_host`) — a
name Tailscale's own MagicDNS already resolves for every device on it, which is
the resolution the environment used to build for itself and does not have to
any more. Reached with no private network at all, the edge falls back to
`at.localhost`, which every browser resolves to the loop without asking
anything — the same fallback the hosted bundle already uses for the same reason
(`at.services.authelia.valid_cookie_domain`). Either way is one name, and the
environment has exactly one to answer for now.

**The WebApp's image carries nothing of AT's, and that is the decision.** The
app's own binary — `at-cli`, never the `at-deploy` that is putting the container
there — is what the container runs, reached through the folder both of them see.
§7a's measured contract says the absolute path is a contract, and the folder is
where the binary lives, so the Working Folder is mounted at the same path it has
outside and the container executes that same artifact. The image is the base the artifact needs,
pinned in version and digest like every other (§3), and it is deliberately
minimal: what the container can reach is the folder and nothing else of the
machine, which is the blast radius §7c is about. The base has to be one the
frozen artifact runs on — the release that builds the binary is what picks it,
and moving it is a release act.

**The order of the manifest is the order things come up.** The gate stands
before the edge that asks it about every request, so it is declared before the
Caddy; the WebApp stands before the edge that proxies to it, for the same reason
one step down — a `reverse_proxy` pointing at a port nothing answers on is an
edge that refuses every request.

**Bringing the environment up is not the SWITCH**, and this file does not
pretend otherwise: a service that does not come up is said, and what did come up
stays up for whoever wants to look. The switch — paths.md's transactional change
from the hosted path to the container one, Forms on until the gate is proved, and
a whole rollback when any step does not close — is `at_deploy/switch.py`'s, and it
is the one that undoes itself.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from at.core import actors, files, gate, paths, strongbox, tables
from at.core.migrations import is_yes
from at.encryption import vault
from at.i18n import tr
from at.services import authelia as authelia_service
from at.services import caddy as caddy_service
from at.ui import words
from at.ui.webapp import keys as webapp_keys
from at_deploy import podman, vpn

# What a person answers with, injected the way `boot` and `lang` take theirs: a
# test asks the same question without a terminal.
Ask = Callable[[str], str]

# What spends an elevation, injected the same way — and the suite MUST inject it:
# a test that ran `sudo` would be a test that asked a person for a password.
Spend = Callable[..., None]

# The outcomes of `up` and `update`, and the CLI is what turns them into an
# exit code.
UP = "up"                 # the environment is standing
UPDATED = "updated"       # `update` re-pinned and recreated, over a folder that
                          # already had an environment
PROVISIONED = "provisioned"  # `up` refused: this folder already has one — the
                             # word for a second time is `update`
INSTALL = "install"       # the person installs the Podman; AT said how
HOSTED = "hosted"         # the folder stays on the hosted path, and nothing moved
NO_ANSWER = "no_answer"   # no terminal to ask in: neither way was taken
FAILED = "failed"         # a service did not come up (or `update` on a folder
                          # with no environment yet — the word for that is `up`)
UNREADABLE = "unreadable"  # the Main Key does not open what the folder keeps
# A pasta de estado tem um caminho com a forma errada — um ARQUIVO onde o
# serviço monta uma pasta, ou o contrário. Não é um serviço que não subiu: é um
# estado que o AT sabe diagnosticar antes de tentar, e a subida recusa com a
# frase em vez de estourar no meio dela.
MALFORMED = "malformed"


class SealedRefused(Exception):
    """Um envelope que esta subida não abriu — e não se monta o que não se abriu.

    Ele guarda contra a única coisa que não pode acontecer em silêncio: o
    envelope indo parar no diretório de execução, onde o container o leria como
    se fosse o valor. A Chave Principal é conferida contra TUDO o que a pasta guarda antes
    de qualquer container (`_not_opened`), então chegar aqui é uma
    inconsistência — a cópia mudou entre a conferência e a montagem, ou alguém
    montou sem Chave Principal nenhuma. A resposta é a mesma nos dois casos, e é a do §4:
    o que não se abriu não se usa.
    """


# The outcomes of the gate's credential change — item 27's operator act (§7b).
# The row is written in all three: what separates them is how far the change
# travelled, and the person is owed exactly that difference.
CREDENTIAL_CHANGED = "changed"   # the row, the derivation and the provider
CREDENTIAL_UNKNOWN = "unknown"   # nobody in this folder wears that name
CREDENTIAL_PENDING = "pending"   # the folder has it; the gate does not yet

# The port the edge is reached on, and it is 443 because that is the port a URL
# does not say: the person types `https://<site_host()>`, and §7f's phone takes
# a URL and nothing more — a `:8443` in the middle of it is a port nobody asked
# to know. The Caddy is the edge, and its port is the FIRST the environment
# publishes outside the loop (§7e).
#
# **It costs its OWN elevation now, and that is the price of there being no
# DNS of the environment's own any more** (TASK-187): a rootless container
# publishes nothing below the kernel's floor, and `443` is itself under it on
# every machine that ships the rule — the floor has to move to `443` for the
# environment to come up at all (`elevate`).
PORT = 443
# Where the WebApp answers inside its container. **The address is the fix of
# this piece, and it is measured**: an app on the container's own loop is
# reached by nobody — the published port lands on the container's network
# address and finds nothing there, and the edge is another container whose
# `127.0.0.1` is itself. So the app answers on the container's addresses, and
# what keeps that from being an exposure is the network and the gate secret
# (`GATE_ENV`, §7b): who reaches it and brings no secret is refused with 403.
#
# The PORT is unchanged, and §7c is why: exposing moves the address the person
# reaches, never the one the WebApp listens on. `test_environment` holds the
# port to the WebApp's OWN constant, so the declaration cannot drift from the
# thing it names.
ALL = "0.0.0.0"
WEBAPP_HOST = ALL
WEBAPP_PORT = 12345

# The environment's network — the one the services of the environment talk over.
# **It is ONE network, and a second one buys almost nothing here**, which is a
# measurement and not a preference: two podman networks do not reach each other
# at all (no route, and the name only resolves inside the network that gave it),
# so what decides a service's network is nothing but WHO IT HAS TO TALK TO. The
# Caddy reaches the WebApp (its `reverse_proxy`), the WebApp reaches the gate
# (its own "is my portal standing"), and the Caddy reaches the gate
# (`forward_auth`) — so those three stand together, and whoever has business
# with them stands with them.
NETWORK = "at"

# The prefix of every container AT creates. A container is named for the
# service it runs, and the name is AT's: `down` removes what the name says,
# and another AT on this machine has other names.
PREFIX = "at-"

# The label every container of this environment carries, for whoever reads the
# runtime by hand and wants to know whose it is.
LABEL = "at.service"

# O DIRETÓRIO DE EXECUÇÃO: o que o container LÊ, materializado fora da Pasta de
# Trabalho (item 50). **A pasta de estado é a FONTE, e ele é a cópia que serve a
# subida** — o `up` o escreve para cada serviço e o `down` o apaga —, e ele mora
# onde morre: o `XDG_RUNTIME_DIR` da máquina quando ele existe (permissão `0700`,
# `tmpfs`, apagado no logout), e o temporário do sistema quando não existe. **É
# por aqui que um arquivo selado volta a ser lido sem a Chave Principal no
# processo**: quem abre o envelope é o `up`, uma vez, com a Chave Principal que a subida
# digitou, e o que o container monta é a cópia clara (`_materialize`).
#
# **O nome carrega o id da pasta e nunca o nome dela**: dois ambientes nesta
# máquina não se cruzam, e o nome da pasta de ninguém aparece num diretório
# compartilhado. O prefixo é o mesmo das imagens e dos containers: `at-`.
RUN_ENV = "XDG_RUNTIME_DIR"
RUN_ID = 12

# A pasta do diretório de execução que espelha a dos serviços, e a do portão.
# O diretório de execução é um `App/` em miniatura — `<run>/services/<serviço>/`
# é o que aquele serviço lê, e `<run>/caddy/gate` é a cópia clara do segredo do
# portão —, e as duas usam o MESMO nome que a pasta usa, para que quem olha um
# reconheça o outro.
RUN_SERVICES = "services"

# A cópia materializada do portão, montada no WebApp (§7b). Ele é o TERCEIRO dos
# leitores que o cofre nomeia e o único que não é o dono do arquivo: o Caddy lê
# o portão dentro do `Caddyfile` que AT escreve, o provedor lê os dele no
# `configuration.yml`, e o WebApp o lê pela pasta INTEIRA que monta (`Mirror`) —
# onde o arquivo é o da PASTA, que o selo vai fechar. Então ele recebe a cópia
# clara como uma montagem própria, e o `at-cli` é TOLD onde ela está pela
# variável que o próprio Caddy declara (`caddy.GATE_PATH_ENV`), exatamente como
# já é told o nome do provedor (`GATE_ENV`).
#
# É um ARQUIVO e não uma pasta: o que o WebApp precisa é de um valor, e a pasta
# em volta não tem nada que lhe sirva.
GATE_DIR = "caddy"
GATE_MOUNT = "/run/at/gate"

# The address a service publishes on when it declares none: the loop, because
# that is what closes the LAN (measured — see the module's docstring).
LOOP = "127.0.0.1"

# The machine's rule about low ports, and the ONE thing §7 asks of it. A user
# process may only bind ports from this floor up, and §7a's edge publishes on
# `443` — which is under it on every machine that ships the rule.
# The name is the DOTTED one the command takes; the file that ANSWERS it spells
# the same thing with slashes, and the two are not interchangeable.
SYSCTL_PORTS = "net.ipv4.ip_unprivileged_port_start"
SYSCTL_FILE = Path("/proc/sys") / SYSCTL_PORTS.replace(".", "/")

# Inside the containers, where each service reads what AT writes for it.
CADDY_CONFIG = "/etc/caddy"
CADDY_DATA = "/data"

# A pasta do SERVIÇO que o Caddy monta em `CADDY_DATA`: o storage dele, com a CA
# local e os certificados emitidos contra ela. Ela é um nome e não a linha do
# `Mount` porque DOIS lugares têm de concordar sobre ela — o que o container
# monta, e onde o Caddy guarda o que emite por nome (`_prune_names`).
CADDY_STORAGE = "storage"
IDENTITY_CONFIG = "/config"
IDENTITY_DATA = "/data"

# The identity provider (§7b), and the name of the service is the ROLE and not
# the brand: Authelia is what serves it today (`SERVICES`), and a product that
# named the brand here would have to rename the service the day another one
# serves it. Its port is Authelia's own default, published on the loop because
# that is where the Caddy's `forward_auth` reaches it from — the Caddy shares
# the host's network and the provider does not need to (§7a's measured rule).
IDENTITY = "identity-provider"
IDENTITY_PORT = 9091

# The three files of its state folder, and all three are the service's: the
# configuration AT generates, the people it writes for it to prove, and the
# session secret drawn once and kept — Authelia signs its cookie with it, and a
# secret drawn per start would drop every session on the floor.
IDENTITY_YAML = "configuration.yml"
IDENTITY_USERS = "users.yml"
IDENTITY_SESSION = "session"

# The other two secrets the provider needs, and they are the same kind of value
# as the session's: they belong to the INSTALLATION and not to a start. The
# first is what it ENCRYPTS its own records with — one drawn per start would
# make everything it had already written unreadable —, and the second is what it
# signs an identity-validation token with.
IDENTITY_ENCRYPTION = "encryption"
IDENTITY_JWT = "jwt"

# Os TRÊS, numa lista, porque dois lugares os nomeiam: quem os SORTEIA — o `up`,
# antes de qualquer escritor, e um a um — e quem os SELA na conferência da
# Chave Principal (`_sealed_files`). O `_identity_conf` continua nomeando cada um no lugar
# do YAML onde ele entra, porque lá a POSIÇÃO é o que importa; aqui é o
# CONJUNTO, e ele é um só.
IDENTITY_SECRETS = (IDENTITY_SESSION, IDENTITY_ENCRYPTION, IDENTITY_JWT)

# Where the provider writes what it has to TELL somebody, and the everyday case
# is an identity validating a second factor. §7 has no smtp to give it, so it is
# a FILE — inside the service's own state folder, which is the folder the backup
# covers (§3) and what makes the notice recoverable instead of lost.
IDENTITY_NOTIFICATIONS = "notifications"

# §7a's edge, by the name the manifest gives it — and by the name the deploy's
# own probes ask the environment for the image they run in (`inside`): it is the
# one image of the manifest that carries an HTTP client, and it is already
# pulled by the time anything asks.
CADDY = "caddy"

# The WebApp as a container (§7c), and what runs inside it is THIS artifact: the
# module's docstring holds the decision, and the test is what keeps it true —
# the folder is mounted at its own path, and the command names the binary the
# person is running.
WEBAPP = "webapp"

# The variable the environment hands the WebApp so it can find its gate. A
# container has no host's loop to ask — `127.0.0.1` inside it is the WebApp's
# own — so the environment is what says which name to use, and the name is the
# provider's on the network the two share (`core/gate.py`, which reads it).
GATE_ENV = "AT_GATE"

# How much secret the identity provider's own drawing carries. The same price
# as the gate's (`caddy.GATE_BYTES`): it is a value a header and a cookie carry,
# never one a person types.
SECRET_BYTES = 32

# O nome do ambiente quando não há rede privada nenhuma — o mesmo truque que o
# bundle hospedado já usa (`at.services.authelia.valid_cookie_domain`), e pela
# mesma medida: todo navegador resolve `*.localhost` para o laço sozinho, sem
# DNS nenhum por trás, e o ponto no meio é o que o portão exige de um domínio
# de cookie (TASK-187 — antes disso o ambiente respondia por um nome PRÓPRIO,
# `at.local`, que só um `dnsmasq` do próprio AT resolvia). Com uma rede privada
# de pé, o nome é o dela (`vpn.name`), e este nunca é usado.
FALLBACK_HOST = "at.localhost"

# How long the orchestrator waits for an address to exist before it gives up on
# publishing there. Long enough for an interface to come up, short enough that a
# person is not left staring at a command that will never start anything.
GRACE = 20.0
STEP = 0.5

# The pin, as §3 spells it: a version and a digest. `sha256:` is the digest the
# registry publishes, and 64 hex characters after it.
PIN_PREFIX = "sha256:"
PIN_DIGITS = 64

# What the folder's pin says about one service, against the binary's (§3).
CURRENT = "current"
OUTDATED = "outdated"
AHEAD = "ahead"

# The three states a container is in, for `status`.
RUNNING = "running"
STOPPED = "stopped"
ABSENT = "absent"

# WHAT A PERSON IS ASKED, and the three words are all of it: is it on this
# machine, and is it on. The container's life — created, stopped, removed — is
# the RUNTIME's vocabulary, and a report that answers in it is answering a
# question nobody asked. The three are checked, not inferred: the image is in
# the machine's store, and the container is running.
INSTALLED = "installed"     # the image is here, and nothing is running
MISSING = "missing"         # the image is not here — it was never brought


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


def binary() -> str:
    """The artifact the WebApp container runs — `at-cli`, the app's own (§7c).

    The binary IS the WebApp, so a container that ran another artifact would be a
    second product — and since item 27 that distinction is the whole point: what
    runs inside is `at-cli`, the artifact that keeps the folder and the app, and
    never `at-deploy`, which is the tool that put the container there.

    It is reached through the folder both of them see at the same path, and the
    artifact running is NOT the one being named: `at-deploy` is what brings the
    container up, and what goes inside it is `at-cli` (item 27). Frozen, the app
    sits beside the deploy at the folder's root, which is where §3 puts the
    binary and its Windows spelling. Run from a checkout, it is `dist/at-cli`,
    which is where `at-cli.spec` puts the artifact and which is inside the folder
    too — NOT `at/`, which is the package, and a directory is not something a
    container can execute. A folder that never built the artifact names a path
    that is not there, and that is honest: the switch is what notices, by proving
    the WebApp answers instead of believing this line.

    **The NAME comes from `paths.artifact_file()` and is not spelled here**, and
    that is the point of it being a name at all: the same pair — `.exe` on
    Windows, no extension on Linux and macOS — is what each spec writes (`at-cli.spec`,
    `at-deploy.spec`), and a container that guessed the spelling would be a
    container that never starts.
    """
    if getattr(sys, "frozen", False):
        return str(paths.working_folder() / paths.artifact_file())
    return str(paths.working_folder() / "dist" / paths.artifact_file())


# --------------------------------------------------- the machine's permission ---

def floor() -> int:
    """The lowest port this machine lets a user process bind — `0` where there
    is no such rule at all.

    Read from `/proc` and never from a command: `sysctl` would be a subprocess
    to ask a question the kernel already answers in a file, and the file is the
    same on every Linux. A machine that does not have the rule — a Mac, a
    Windows — answers `0`, which is "nothing is forbidden here", and that is the
    honest reading: the rule is the kernel's, and where the kernel has no such
    rule the environment needs no permission.
    """
    try:
        return int(SYSCTL_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def blocked() -> tuple[int, ...]:
    """The ports the environment publishes that this user may not bind.

    It is the ONLY thing that decides whether an elevation is asked for, and it
    is asked of the manifest and not of a list written by hand: a service that
    starts publishing a low port tomorrow enters this question by existing. The
    root user is allowed everything and is asked nothing.
    """
    if getattr(os, "geteuid", lambda: 1)() == 0:
        return ()
    below = floor()
    ports = {port.port for service in SERVICES
             for port in ports_of(service) if port.port < below}
    return tuple(sorted(ports))


def spend_elevation(*argv: str) -> None:
    """Run one command as the machine's administrator, through `sudo`.

    **The terminal is INHERITED and that is the point**: `sudo` asks for the
    password itself, and an AT that swallowed that prompt would look like a AT
    that hung. Nothing reaches here without §3's explicit request (`elevate`), and
    the suite never reaches here at all — `spend` is the seam.
    """
    subprocess.run(["sudo", *argv], check=False)  # noqa: S603 — sudo is the point


def elevate(ask: Ask | None = None, spend: Spend | None = None) -> str | None:
    """§3's explicit request: the reason on display, and the elevation spent.

    §3 says the environment inevitably demands elevation at some point, that it
    happens **through an explicit request with the reason on display**, and that
    the closed list of what demands it is born with the implementation that asks
    for it. This is that implementation and this is the one entry of the list:
    §7a's Caddy publishes the edge on `443`, and a machine that ships the
    kernel's low-port rule — every Linux does — refuses the bind to a user
    process.

    **What is asked is the NARROWEST thing that works**: the floor moves to the
    LOWEST port the environment publishes and not to zero, so the machine grants
    exactly what AT needs and nothing below it. And what it buys is not
    permanent — a `sysctl -w` is gone at the next boot, and AT asks again then,
    which is the same explicit request made again rather than a permission
    remembered behind the person's back.

    Refusing is a real answer and not a failure: nothing moved, the folder stays
    on the hosted path, and the person is told which ports are out of reach.

    **What comes back is an OUTCOME or `None`**, the shape `ways_out` already
    answers with: `None` is "nothing to ask" and "the permission was given",
    which are the same thing to `up` — go on — while the three refusals are told
    apart, because a terminal that could not ask, a person who said no and a
    machine that did not move are three different sentences to whoever reads the
    exit code.
    """
    ports = blocked()
    if not ports:
        return None
    listed, lowest = ", ".join(str(port) for port in ports), ports[0]
    if ask is None:
        print(tr("services.elevation.no_tty", ports=listed))
        return NO_ANSWER
    question = tr("services.elevation.ask", ports=listed, value=lowest,
                  setting=SYSCTL_PORTS)
    if not is_yes(ask(question)):
        print(tr("services.elevation.refused", ports=listed))
        return HOSTED
    (spend or spend_elevation)("sysctl", "-w", f"{SYSCTL_PORTS}={lowest}")
    if blocked():
        # The permission was asked and the machine did not move: saying "done"
        # here would be announcing a bind that is about to fail.
        print(tr("services.elevation.failed", ports=listed))
        return FAILED
    print(tr("services.elevation.spent", value=lowest))
    return None


def container(name: str) -> str:
    """The name of the container AT runs for that service.

    It is declared here — above the manifest that uses it, and far above the
    orchestration — because it is a NAME and not a step: the service's container,
    the gateway name another service reaches it by (§7c's `GATE_ENV`) and what
    `down` removes are the same word said once.
    """
    return f"{PREFIX}{name}"


def _webapp_command() -> tuple[str, ...]:
    """What §7c's container runs: the artifact, serving the WebApp on the network.

    The address is the container's own (`WEBAPP_HOST`) and it is the whole point
    of the command being written here: the app's default is the loop, and on the
    loop nobody inside the environment reaches it. The port is the WebApp's own
    default, and it is the one the Caddyfile proxies to — the two are the same
    number, and `test_environment` is what holds them together.
    """
    return (binary(), "webapp",
            "--port", str(WEBAPP_PORT), "--host", WEBAPP_HOST)


def _webapp_env(key: bytes | None) -> tuple[tuple[str, str], ...]:
    """What §7c's WebApp is TOLD: where its gate is, where its folder is, and —
    when this subida has the key — the derived keys it holds in memory.

    The gate, because a container cannot see the host's loop and the name is the
    environment's to say (`GATE_ENV`), **and the gate's FILE, because the one
    the WebApp would read by the folder is the folder's** (`GATE_MOUNT`, item
    50): the container gets the copy the `up` materialized, and the variable is
    how the `at-cli` inside it is told where that copy is — the same shape as
    the address above and for the same reason. And the FOLDER, which is the same
    lesson as the address and was measured the same way: run from a checkout, the
    artifact this container executes sits in `<folder>/dist/at-cli`, and an app
    that read its folder from where its binary is — the `install` rule, §3 —
    would take `<folder>/dist` for the person's folder, find no `App/`, and ask
    to confirm a new Working Folder that no terminal in a container can answer.
    It is a WebApp that never serves.

    **Frozen it lands right, and that is the worst kind of right**: the artifact
    sits at the folder's root, the inference agrees, and the defect waits for
    the first run from a checkout. `AT_ROOT` is the contract the image already
    declares in its own words (`Containerfile`), and naming it here costs one
    variable.

    **§4, item 50: os DOIS derived keys ride the same door, and only when
    there is a Main Key to derive them from.** `key` is `None` on a subida
    whose folder had nothing to open, draw or migrate this round (`unlock`) —
    a folder already entirely sealed does not get asked the Main Key again, so
    it does not get these variables either, and the WebApp inside it simply
    has no derived key this boot (`at.ui.webapp.keys.get`'s own contract).
    When there IS a key, it never travels itself — only `vault.derived_key`'s
    answer does, one scope at a time: the WebApp's own (`WEBAPP`), and the
    Vault's (TASK-154, `at.core.strongbox.SCOPE`), what
    `strongbox.Watcher.tick` seals a settled write in `Cofre/` with.
    """
    env = [
        (GATE_ENV, f"{container(IDENTITY)}:{IDENTITY_PORT}"),
        (paths.ROOT_ENV, str(paths.working_folder())),
        (caddy_service.GATE_PATH_ENV, GATE_MOUNT),
    ]
    if key is not None:
        env.append((webapp_keys.WEBAPP_KEY_ENV, _derived_b64(key, WEBAPP)))
        # TASK-154: a terceira porta para o que já existe — a mesma chave,
        # o escopo `cofre` (`at.core.strongbox.SCOPE` — o valor congelado
        # continua `"cofre"`), nenhum envelope resselado.
        env.append((webapp_keys.STRONGBOX_KEY_ENV, _derived_b64(key, strongbox.SCOPE)))
    return tuple(env)


def _derived_b64(key: bytes, scope: str) -> str:
    """A derived key, encoded for the one trip it takes: inside an env var."""
    return base64.urlsafe_b64encode(vault.derived_key(key, scope)).decode("ascii")


def site_host() -> str:
    """The NAME the environment's edge serves the site at (TASK-187).

    §7e is what this reads: with a private network up, the name is the one it
    gives the machine (`vpn.name`) — a name Tailscale's own MagicDNS already
    resolves for every device on it, so the environment needs no DNS of its
    own to be reached by it. With none, the fallback is `FALLBACK_HOST`, which
    every browser resolves to the loop on its own, no resolver asked — the
    same fallback the hosted bundle already carries (`at.services.authelia.
    valid_cookie_domain`). Either way it is a NAME and not an address, for the
    two measurements this piece always had to answer: the gate refuses a
    cookie domain without a dot that is not an IP, so the word `localhost` is
    out; and TLS needs a NAME for the SNI — a client connecting to an ADDRESS
    sends none, and the Caddy answers the handshake with `internal error`
    because it has no certificate it can serve.

    **It is a function and not a constant for the same reason as before, and
    one more now**: the private network is measured when the environment
    comes up — a value read at import would stop being true the moment the
    person joined one —, and every file that has to agree on the name — the
    Caddyfile, the identity provider's access rule and its cookie, and the URL
    the switch says — is written at that same moment.
    """
    return vpn.name() or FALLBACK_HOST


def portal_url() -> str:
    """Where the portal is reached — the site, plus the portal's own path (§7b).

    **ONE place decides it, and three read it**: the provider's `authelia_url`,
    the edge's routing of the portal and the switch's fourth probe. They have to
    name the same address or the redirect lands somewhere the edge does not
    serve, and the drift between "where the gate sends the person" and "what the
    proof asks" is exactly the kind of difference a proof passes through
    (`caddy.PORTAL`). It is a function for the same reason `site_host` is: the
    name is measured when the environment comes up.
    """
    return f"{caddy_service.address(site_host(), PORT)}{caddy_service.PORTAL}/"


def names() -> tuple[str, ...]:
    """Every name the environment answers for — one, since TASK-187.

    It stayed its own function, and not a bare call to `site_host`, because
    `_prune_names` reads it to know which of the Caddy's own certificates are
    stale: the name changes between a subida on a private network and one
    without it, and a certificate issued for yesterday's name is a private key
    the backup would carry for nothing.
    """
    return (site_host(),)


def _caddy_conf() -> str:
    """The Caddyfile the container's Caddy runs.

    The same generator the hosted path reads, because it is the same Caddy: the
    site, the TLS of AT's own certificate, the admin endpoint off and the
    storage — the one line that is a path and not a decision (§7a). The two
    lines of the gate come along when there is a secret, and §7b is what draws
    it: the Caddy asks the identity provider who is calling, and tells the
    WebApp that the request came through here. **And the portal's way around
    the ask comes with them**, because `auth` is here: the provider's own path
    is routed straight to it, so the redirect that sends the browser to the
    portal does not become another question (`caddy.PORTAL`).

    **Four things are the container path's and not the hosted path's**, and each
    is an address that means something else on this side of the network. The
    backend is the WebApp's NAME on the network and not the host's loop, which
    the edge cannot see. The provider is reached the same way, for the same
    reason. The site BINDS everything the container has, because the name the
    certificate carries is not an address this container holds — what makes the
    site reachable is the port the container publishes (§7e). And the site is
    the site: `site_host` is §7a's, and it is the same on both paths.
    """
    return caddy_service.caddyfile(
        site_host(), PORT, WEBAPP_PORT,
        gate=caddy_service.gate_secret(),
        storage=CADDY_DATA,
        auth=f"{container(IDENTITY)}:{IDENTITY_PORT}",
        bind=ALL,
        upstream=container(WEBAPP),
    )


def _caddy_ports() -> tuple[Port, ...]:
    """A porta do site (§7e, TASK-187).

    É a porta que um navegador alcança. Ela publica no endereço da REDE PRIVADA
    quando há uma — a mesma expressão que `site_host` usa — e no laço quando não
    há, que é o estado suportado e não um degradado. **Não é `0.0.0.0`**: uma
    porta publicada em todo endereço é uma porta na LAN, e o que §7a mede e este
    produto promete é que nada do AT fica exposto ali fora, exceto a borda, na
    rede que a pessoa escolheu.

    É uma função e não uma constante pela mesma razão que `site_host`: o
    endereço é medido quando o ambiente sobe, e um valor lido na importação
    deixaria de ser verdade no instante em que a pessoa entrasse numa rede.
    """
    where = vpn.address() or LOOP
    return (Port(PORT, address=where),)


def _prune_names() -> tuple[str, ...]:
    """Tira do storage do Caddy o certificado dos nomes que a borda já não serve.

    **O conjunto de nomes é do AT e não do Caddy** (`names`): quando o ambiente
    deixa de servir um nome, o Caddy não tem como sabê-lo — ele guarda o
    certificado daquele nome e a chave privada ao lado dele para sempre, e o que
    sobra é uma chave em claro que o portão do backup barraria sem motivo. É por
    isso que a poda é do `up`: a limpeza não é um ato à parte que a pessoa teria
    de lembrar de pedir, ela é o preço de o nome ter mudado, e ele já foi pago na
    subida seguinte.

    **É o ÚNICO ato do AT dentro do que o container encheu, e ele é estreito de
    propósito**: só os diretórios de `certificates/local` cujo nome não está no
    `names()` saem — um por nome, e o nome do diretório é o nome servido —, e o
    diretório da CA (`pki/`) nunca é tocado. O que o container escreveu de um
    nome que AINDA é servido continua byte a byte como ele deixou
    (`TheStorageOutOfReach`).
    """
    where = caddy_service.certificates_dir(state(CADDY) / CADDY_STORAGE)
    if not where.is_dir():
        return ()
    served = set(names())
    stale = sorted(
        entry for entry in where.iterdir()
        if entry.is_dir() and entry.name not in served
    )
    for entry in stale:
        shutil.rmtree(entry)
    return tuple(entry.name for entry in stale)


def _drawn_files() -> tuple[Path, ...]:
    """Os arquivos que o AT SORTEIA: onde os valores selados moram (item 50).

    O portão do Caddy e os três que o provedor assina, cifra e prova com (§7b):
    os conjuntos são nomeados juntos porque a pergunta que os usa é uma só —
    "há o que selar, ou o que abrir?" —, e ela é feita ANTES de qualquer sorteio.
    """
    return (caddy_service.gate_file(),
            *(state(IDENTITY) / name for name in IDENTITY_SECRETS))


def _sealed_files() -> tuple[tuple[Path, str], ...]:
    """Todo arquivo que pode carregar um envelope, e o escopo da chave que o abre.

    **O escopo é o SERVIÇO dono do valor** (§4: uma chave por serviço ou
    finalidade): os três do provedor são dele, e o portão é do Caddy — o arquivo
    é do Caddy, e é o `Caddyfile` dele que o carrega. É por isso que o escopo
    pode ser lido do arquivo e não precisa viajar dentro dele: quem compõe um
    texto sabe de quem é o valor que está compondo.

    Os arquivos ESCRITOS entram aqui também, e não só os sorteados: o
    `configuration.yml` e o `Caddyfile` carregam os envelopes inline, e são eles
    que a conferência da Chave Principal tem de abrir.
    """
    found = tuple((where, CADDY) for where in (caddy_service.gate_file(),))
    found += tuple((state(IDENTITY) / name, IDENTITY) for name in IDENTITY_SECRETS)
    for service in SERVICES:
        found += tuple((state(service.name) / name, service.name)
                       for name, _ in service.writes)
    return found


def _text(where: Path) -> str:
    """O texto de um arquivo da pasta, ou vazio quando não há o que ler.

    Ele é tolerante de propósito: quem pergunta é a conferência da Chave Principal, e o
    que ela precisa saber é quais envelopes existem — um arquivo que ainda não
    nasceu não tem nenhum, e não é erro.
    """
    try:
        return where.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return ""


def _clear(where: Path) -> bool:
    """Se o arquivo existe e guarda um valor EM CLARO — a pasta que nasceu antes do selo.

    É a medida do corte `f` do item 50, e ela não se confunde com a de um
    arquivo ausente: um ausente é um sorteio que vem aí, e um em claro é um
    valor que JÁ viajou. **Um texto sem envelope É o valor** — a mesma regra com
    que quem abre o envelope o lê —, e é por isso que a migração não precisa saber
    o que o valor significa: ele é re-sorteado como qualquer outro, e o que a
    pasta guardava deixa de abrir o que foi copiado dela.
    """
    text = _text(where).strip()
    return bool(text) and not vault.envelopes(text)


def _clear_drawn() -> tuple[Path, ...]:
    """Os arquivos que o AT SORTEIA e que estão em claro na pasta (item 50, corte `f`).

    A lista é a mesma pergunta de `_needs_phrase` feita arquivo a arquivo, e o
    que ela responde é o que a subida vai migrar: **cada um destes é
    re-sorteado e selado**, porque a pasta pode ter sido copiada e o valor que
    já viajou não volta. É isso que separa a migração de um simples selo.
    """
    return tuple(where for where in _drawn_files() if _clear(where))


def _sealed_somewhere() -> bool:
    """Se a pasta já guarda algum envelope do cofre.

    **É a pergunta que decide se a Chave Principal tem como ser CONFERIDA**: uma pasta que
    já selou abre o que guarda e sabe se a Chave Principal é a mesma; uma que nunca selou
    não tem contra o que conferir, e é por isso que ela é lida duas vezes na
    primeira vez (`_ask_phrase`).
    """
    return any(vault.envelopes(_text(where)) for where, _ in _sealed_files())


def _needs_phrase() -> bool:
    """Se a Chave Principal faz falta nesta subida: há o que abrir, ou há o que selar.

    As três coisas são a mesma pergunta para quem sobe: **abrir** o que a pasta
    guarda selado, **selar** o que este `up` vai sortear, e **migrar** o valor
    que nasceu em claro (`_clear_drawn`, o corte `f` do item 50). Uma pasta com
    os valores todos no lugar e todos selados não a pede: não há o que abrir nem
    o que sortear. **E a credencial do notificador entra na pergunta**: ela é
    um dos arquivos que o `up` sorteia (`_drawn_files`), como a M2M do Caddy
    que a acompanha.
    """
    for where in _drawn_files():
        if not where.exists():
            # Um sorteio vem aí, e um sorteio SELA: sem Chave não há selo.
            return True
        if _clear(where):
            # A pasta que nasceu antes do selo: há o que MIGRAR, e migrar
            # re-sorteia — o valor que já está no disco pode ter sido copiado,
            # e a rotação é o que mata a cópia.
            return True
    return _sealed_somewhere()


def _not_opened(key: bytes) -> Path | None:
    """O primeiro arquivo que esta Chave NÃO abre, ou `None` quando abre todos.

    **A conferência da Chave Principal é esta, e ela é a própria abertura**: dois valores
    selados com a mesma Chave Principal são a prova de que é a mesma, e não há nada a
    perguntar de novo — §4: o que só se confere responde, não levanta.
    """
    for where, scope in _sealed_files():
        derived = vault.derived_key(key, scope)
        for envelope in vault.envelopes(_text(where)):
            if vault.unseal(envelope, derived) is None:
                return where
    return None


def _ask_phrase(secret: Ask) -> bytes | None:
    """A Chave Principal lida e conferida: a chave derivada, ou `None` (§4).

    **Lida UMA vez por subida** — §4: digitar a Chave Principal quando o AT sobe é a nota
    `S`, e a Chave vive o tempo desta chamada e mais nada; nada a guarda, e
    nada a escreve. **E conferida contra o que a pasta guarda**: cada envelope
    que a subida vai ter de abrir é aberto aqui, antes de qualquer container, e
    uma Chave Principal que não abre um deles não sobe o ambiente.

    **A primeira vez é a exceção, e ela é declarada**: sem envelope nenhum não
    há contra o que conferir, então a Chave Principal é lida DUAS vezes — como a
    credencial do primeiro administrador (`at-cli admin`) —, porque uma Chave Principal
    que sela não tem como ser conferida depois, e um erro de digitação custaria
    exatamente o que ela acabou de selar.

    A Chave Principal curta é recusada pela regra do COFRE e não por esta porta (§3: quem
    pergunta não decide o tamanho), e a sentença é a mesma em qualquer lugar que
    a peça (`core.secrets` e aqui leem a mesma).
    """
    main_key = secret(tr("services.phrase"))
    try:
        key = vault.vault_key(main_key)
    except vault.MainKeyRefused:
        print(tr("secrets.error.phrase", min=vault.MINIMUM))
        return None
    if not _sealed_somewhere() and secret(tr("services.phrase.again")) != main_key:
        print(tr("services.phrase.mismatch"))
        return None
    where = _not_opened(key)
    if where is not None:
        print(tr("services.phrase.unopened", where=where))
        return None
    return key


def unlock(secret: Ask | None) -> tuple[bytes | None, str | None]:
    """A chave derivada para um ato que ABRE, e a recusa — uma das duas (§4).

    Ela é a porta por onde o `up`, o `restart` e a entrega do §7f pedem a Chave Principal,
    e a única: os três leem o que a pasta guarda — o `up` e o `restart` para
    montar o diretório de execução, e a entrega para autenticar no notificador
    —, e nenhum deles pode fazer isso com um envelope que não abriu. **`None` na
    Chave é o estado de uma pasta que não tem nada de selado, nada a sortear e
    nada a migrar**, e aí nada precisa dela: a pasta já está inteiramente
    selada.

    Quem SELA pergunta por outra porta (`sealing_key`): esta só pergunta quando a
    pasta tem o que abrir, o que sortear ou o que migrar (`_needs_phrase`).
    """
    if not _needs_phrase():
        return None, None
    return sealing_key(secret)


def sealing_key(secret: Ask | None) -> tuple[bytes | None, str | None]:
    """A chave derivada de um ato que SELA, pedida SEMPRE — e a recusa (§4).

    `unlock` responde "esta pasta precisa da Chave Principal?"; esta porta responde "dê-me
    a Chave", e é a diferença que um ato que SELA não pode ignorar: uma pasta que
    nasceu antes do selo não tem o que ABRIR e, no entanto, o valor que o ato vai
    sortear tem de sair selado — sem Chave ele iria para a pasta em claro, que é
    exatamente o que o item 50 existe para não haver.

    A recusa é a mesma das outras portas: sem terminal não se pergunta (§3, a
    postura fechada), e uma Chave Principal que não abre o que a pasta guarda não sela nada
    novo.
    """
    if secret is None:
        # A mesma postura da elevação: sem terminal não se pergunta, e não se
        # sobe um ambiente que não abriu o que ele mesmo guardou.
        print(tr("services.phrase.no_tty"))
        return None, NO_ANSWER
    key = _ask_phrase(secret)
    if key is None:
        return None, UNREADABLE
    return key, None


def _opened(text: str, scope: str, key: bytes | None) -> str:
    """O texto com cada envelope ABERTO — o que o container lê (§4, item 50).

    **Ele é o coração da fatia**: a pasta guarda o envelope, e o diretório de
    execução monta o valor. A Chave Principal já foi conferida contra tudo o que a pasta
    guarda antes de qualquer container subir (`_not_opened`), então um envelope
    que não abre aqui é uma inconsistência — e a resposta para ela é fechada:
    não se monta o que não se abriu (`SealedRefused`).
    """
    found = vault.envelopes(text)
    if not found:
        # O caso comum, e o de uma pasta que nasceu antes do selo: não há o que
        # abrir, e o texto vai como está.
        return text
    if key is None:  # pragma: no cover — `unlock` dá Chave quando há envelope
        raise SealedRefused()
    derived = vault.derived_key(key, scope)
    for envelope in found:
        value = vault.unseal(envelope, derived)
        if value is None:  # pragma: no cover — a Chave Principal já foi conferida
            raise SealedRefused()
        text = text.replace(envelope, value)
    return text


def draw_gate(key: bytes) -> str:
    """Draw the gate's secret, once, and SEAL it — §7b's drawing (§4).

    **It is the deploy's act and it moved here with the rest of §7** (item 27):
    §7b says AT draws a secret per installation, and the installation is the
    environment's, which is the deploy tool's. The FILE it writes is still the
    Caddy's own — `App/services/caddy/gate`, beside the Caddyfile that is its only writer
    — and both artifacts read it: `at-cli` refuses the identity that arrives
    without it, and the WebApp's check is what turns the M2M into a door.

    **O que ele escreve é o ENVELOPE do cofre, e não o valor** (item 50): a
    pasta é copiada sem criptografia, então o que ela guarda de um valor que o
    AT sorteou é o que só a Chave Principal abre. O escopo da chave é o Caddy —
    o valor é dele, o arquivo é dele, e é o `Caddyfile` dele que o carrega —, e
    quem o abre para o container é o `up`, no diretório de execução.

    **A key é obrigatória, e o chamador só a tem quando há o que sortear**: o
    `up` pergunta a Chave Principal exatamente quando um destes arquivos falta
    (`_needs_phrase`), então um sorteio sem Chave seria um valor em claro na
    pasta — o que esta fatia existe para não haver. O que já está lá não é
    sorteado de novo.

    **A secret already drawn and SEALED is not drawn again**, and that is the
    whole of the function: rotating it would take the running Caddy and the
    running WebApp apart — the first would attach a value the second no longer
    takes, and every identity would be refused (`webapp.gate_refused`) until both
    were restarted from the same file. Whoever wants a new secret removes this
    one and brings the environment up again, which is the same act as changing
    it, said out loud.

    **Um portão em CLARO é a única exceção, e é a migração** (item 50, corte
    `f`): a pasta que nasceu antes do selo guarda o valor sem envelope, e
    mantê-lo seria manter o que já pode ter sido copiado. Ele é re-sorteado como
    um que faltasse — a subida reinicia os dois leitores de qualquer modo, e é
    por isso que a rotação aqui não abre a janela que a de cima abre.

    **O que ele responde é o ENVELOPE**, e não o valor: é o que ficou na pasta, e
    é ele que o `Caddyfile` carrega — quem precisa do valor claro é o container,
    e quem o escreve no diretório de execução é o `up` (`_materialize_gate`).

    It is the CALLER that decides when — `up` draws it at installation, which is
    the moment §7b names — because a file written on import would be a secret in
    the folder of whoever never asked for one.
    """
    held = _held(caddy_service.gate_file())
    if held and vault.envelopes(held):
        return held
    drawn = secrets.token_urlsafe(caddy_service.GATE_BYTES)
    envelope = vault.seal(drawn, vault.derived_key(key, CADDY))
    files.atomic_write_text(caddy_service.gate_file(), f"{envelope}\n")
    return envelope


def _drawn(service: str, name: str, key: bytes) -> str:
    """A secret drawn once and SEALED, in the service's own state folder (§4).

    The same rule `draw_gate` follows and for the same reason: a value a service
    signs or proves with has to outlive the container, and one drawn per start
    would take everything it had issued down with it. Whoever wants a new one
    removes the file and brings the environment up again. **Um em CLARO é
    re-sorteado**, pela mesma exceção do `draw_gate`: ele é a pasta que nasceu
    antes do selo (item 50, corte `f`), e o `encryption` que ele redesenha é o
    que torna ilegível o que o provedor cifrou com o antigo.

    **O escopo da chave é o SERVIÇO** (§4: uma por serviço ou finalidade), e os
    três que ele desenha são dele — o provedor os assina, cifra e prova. É por
    isso que o escopo pode ser lido do arquivo depois: quem compõe um texto sabe
    de quem é o valor que está compondo (`_materialize`).
    """
    held = _held(state(service) / name)
    if held and vault.envelopes(held):
        return held
    drawn = secrets.token_urlsafe(SECRET_BYTES)
    envelope = vault.seal(drawn, vault.derived_key(key, service))
    files.atomic_write_text(state(service) / name, f"{envelope}\n")
    return envelope


def _held(where: Path) -> str:
    """O texto que um arquivo da pasta guarda — vazio quando ele não está lá."""
    try:
        return where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _kept(service: str, name: str) -> str:
    """O que a pasta guarda para aquele valor: o envelope, ou o que já estava lá.

    **Quem SORTEIA é o `up`, antes de qualquer escritor** (`_drawn`), e o
    escritor só LÊ: o selo precisa da chave derivada, e o escritor não a tem —
    `Service.writes` é uma função de nenhum argumento, e o que ela compõe é o
    arquivo com o que a pasta guarda, que é o envelope. Quem o abre para o
    container é o `_materialize`.

    Um valor que não está lá sai vazio, e o serviço que o lê recusa: o `up`
    sorteia antes de escrever, então isto é uma inconsistência e não um estado —
    e a resposta para ela é fechada, como a de todo valor que falta.
    """
    return _held(state(service) / name)


def _quoted(value: str) -> str:
    """A value as YAML reads it back — always quoted, so that a name carrying a
    colon, a hash or a leading space is the name and not the syntax around it."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _identity_conf() -> str:
    """Authelia's configuration — the gate, declared by AT (§7b).

    **Everything here was read off a REFUSAL, and that is the point.** The
    provider measures its own configuration and refuses to start without six
    things, none of which is a preference: the storage and the key it encrypts
    its records with; a notifier — an smtp or a file — because it has to be able
    to tell somebody something; the secret it signs an identity-validation token
    with; the access control, which denies by default and names AT's own site as
    `one_factor`, because AT comes in as one more app behind the gate and the
    app not named is the app that does not enter; the session secret; and the
    cookie's DOMAIN, which is the site and which the provider refuses without a
    dot unless it is an IP — and that last one is why the site on the loop is an
    ADDRESS and not the word `localhost` (`site_host`).

    **The portal gets a path, and it is the fourth thing the provider is told.**
    `server.address` carries it and `authelia_url` names it (`portal_url`), so
    the provider serves its page under the same address the edge routes around
    the ask — without it the redirect comes back to the edge, the edge asks
    about the portal, and the two rewrite each other until the request dies in
    `431` (`caddy.PORTAL`). The access control keeps naming the site alone: the
    portal never travels through it, because it never travels through the ask.

    Each secret is drawn once, SEALED, and kept beside this file — by the `up`,
    before this writer runs (`_drawn`) — because they belong to the installation
    and not to a start: one drawn per start would drop every session on the
    floor and make every record it had written unreadable. **O que este arquivo
    carrega é o ENVELOPE delas** (item 50): a pasta é copiada sem criptografia,
    a fonte é ela, e a cópia que o container monta é este mesmo texto com os
    três abertos (`_materialize`). **O caminho do notificador é o do ARQUIVO** —
    o `filename:` abaixo é o mesmo que a montagem do serviço declara com
    `file=True`, porque é assim que o Authelia o abre —, e ele vive na pasta de
    estado, que é a pasta que o backup cobre (§3): um aviso sobrevive a uma pasta
    copiada.

    **A sessão mora na MEMÓRIA do provedor, e é a única coisa que ele tem.**
    O que a PASTA guarda é o `secret` que assina o cookie, e o mesmo segredo
    entre dois restarts mantém o cookie válido — mas o registro que ele nomeia
    não atravessa: um restart do container, de qualquer origem — um crash, uma
    troca de credencial (`restart`), um `update`, um `podman restart` avulso —
    zera a memória, e é a pessoa de volta ao login com um cookie que o provedor
    já não conhece. **Este é o preço aceito, e não um a resolver aqui**: um
    registro que sobrevivesse a um restart seria um serviço de SESSÃO a mais no
    ambiente, e o §7 não o tem.

    **No OIDC provider is declared, and that is a decision and not an omission.**
    §7b has Authelia speaking OIDC with whoever speaks OIDC and forward-auth
    with whoever does not; every app of §7 reaches it by forward-auth, AT
    included, and the one that speaks OIDC is the one the person adds later.
    Authelia refuses a provider with no clients — `clients` has to name one or
    more, and `jwks` an RSA key — so a block written today would be an identity
    provider that does not start, declaring a client that does not exist. The
    provider enters with the first service that speaks OIDC, and it is that
    slice's to write.
    """
    session = _kept(IDENTITY, IDENTITY_SESSION)
    encryption = _kept(IDENTITY, IDENTITY_ENCRYPTION)
    signature = _kept(IDENTITY, IDENTITY_JWT)
    site = site_host()
    lines = [
        f"# {tr('services.identity-provider.file.header')}",
        "---",
        # A paleta do tema ativo (uma das quatro do Authelia); logo e favicon
        # ficam fora do container por ora — o escritor de arquivos aqui é só de texto.
        f"theme: {authelia_service.palette()}",
        # O endereço do container, e não uma publicação: o que sai dele é o que
        # o runtime mapeia (§7a) — e o NOME do serviço é como a borda e o WebApp
        # o alcançam, os dois na mesma rede. **O CAMINHO é o do portal**, e é o
        # que o Authelia lê para servir a página sob ele: sem o caminho, a borda
        # não teria como rotear o portal fora do `forward_auth`, e o portão
        # mandaria a pessoa a uma URL que ele mesmo volta a perguntar.
        "server:",
        f"  address: {_quoted(f'tcp://{ALL}:{IDENTITY_PORT}{caddy_service.PORTAL}')}",
        "log:",
        "  level: info",
        "session:",
        f"  secret: {_quoted(session)}",
        "  cookies:",
        # O domínio é o do SITE, e a URL é a do PORTAL — o nome em que a pessoa
        # está quando o portal lhe entrega o cookie (§7e), e o caminho onde o
        # portão a manda entrar. Um cookie emitido para outro nome é um cookie
        # que o navegador não devolve; e a URL sem o caminho é o redirecionamento
        # que voltava para a borda e era perguntado de novo, dobrando até o 431
        # (`caddy.PORTAL`).
        f"    - domain: {site}",
        f"      authelia_url: {portal_url()}",
        "storage:",
        f"  encryption_key: {_quoted(encryption)}",
        "  local:",
        f"    path: {IDENTITY_DATA}/db.sqlite3",
        "authentication_backend:",
        "  file:",
        f"    path: {IDENTITY_CONFIG}/{IDENTITY_USERS}",
        "access_control:",
        "  default_policy: deny",
        "  rules:",
        f"    - domain: {site}",
        "      policy: one_factor",
        "notifier:",
        "  filesystem:",
        f"    filename: {IDENTITY_CONFIG}/{IDENTITY_NOTIFICATIONS}",
        "identity_validation:",
        "  reset_password:",
        f"    jwt_secret: {_quoted(signature)}",
    ]
    return "\n".join(lines) + "\n"


def _identity_users() -> str:
    """The people of the folder, in the gate's own words (§7b).

    It is where the split §7b declares actually meets: WHO is an actor belongs
    to AT — the row of `actor`, with the role the ceiling is read from — and
    HOW it is proved belongs to the gate. What Authelia's file carries is the
    derivation the row already holds (the `hashed` field, §4), so the credential
    is the same one Forms and Basic prove, and what travels is a value that is
    only ever compared — never a credential, and nothing that could be turned
    back into one. The file lives inside the state folder, inside the folder the
    backup covers (§3).

    An actor with no credential is not in it: an entry with an empty derivation
    would be an account nobody holds and anybody could try. A folder with nobody
    in it gets the empty map — the gate reads it and lets nobody through, which
    is the honest state of a gate no key has been handed to yet.
    """
    entries = [row for row in actors.people() if row.get("credential")]
    lines = [f"# {tr('services.identity-provider.users.header')}"]
    if not entries:
        lines.append("users: {}")
        return "\n".join(lines) + "\n"
    lines.append("users:")
    for row in entries:
        lines += [
            f"  {_quoted(str(row.get('name', '')).strip())}:",
            f"    displayname: {_quoted(tables.title('actor', row))}",
            f"    password: {_quoted(str(row.get('credential')))}",
        ]
    return "\n".join(lines) + "\n"


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


# The base the artifact runs on. It carries nothing of AT's — no source, no
# payload, no configuration: the Working Folder is mounted, and the container's
# whole reach is that mount. **The base has to be one the artifact RUNS on**, and
# that is not a preference: a frozen binary links against the glibc of the
# machine that BUILT it, so the base needs a glibc at least as new as the
# release's floor — a floor the release DECLARES and the build PROVES
# (`release/builder.json`, checked by `release.build`'s gate).
#
# **This base is the old floor's leftover, and the swap is owed.** It was chosen
# when the release was built on whatever machine was at hand and needed
# `GLIBC_2.44`, which only a rolling distribution named; the release is built in
# the pinned builder now and needs `2.35`, which `debian:12` and everything
# newer carries — the artifact runs there, MEASURED. Rolling is still what names
# the same floor, and it costs 409 MB against `debian:12`'s 124. Nothing checks
# that a pinned base satisfies the declared floor yet, and that check is owed
# with the swap: a base that lags the release would be a container that dies
# before AT ever starts.
#
# Its `latest` is the vendor's own word: the DIGEST is what pins it, exactly
# like the Caddy's pin (§3), and moving it is a release act.
WEBAPP_IMAGE = Image(
    repo="docker.io/library/archlinux",
    version="latest",
    digest="sha256:f3691b4dde62ba4c4b6f0ae2c1fbf28e8c0c8c4b9a35c7e06dc1f70e21aa29f6",
)

# The manifest of pinned images: §7a's first services, §7b's gate and §7c's
# WebApp. Every pin is the registry's own index for that version —
# the digest covers every platform the image is published for, and the runtime
# picks the one this machine is. Moving a pin is a release's act, and it moves
# forward (§3).
SERVICES: tuple[Service, ...] = (
    # §7b's gate, and it comes up BEFORE the Caddy on purpose: the edge asks it
    # about every request, and an edge whose provider is not standing yet
    # answers nothing (the order is the module docstring's).
    Service(
        name=IDENTITY,
        label=f"services.{IDENTITY}.name",
        image=Image(
            repo="docker.io/authelia/authelia",
            version="4.39.28",
            digest="sha256:bd97cff4fcbf715b5ff1f9ae286afbe6033afce385302520b0368122d43a6f54",
        ),
        # Nothing is published, and that is not an omission: who reaches the
        # provider is the Caddy (`forward_auth`) and the WebApp (its own check),
        # and both reach it by name on the network — so the loop door it used to
        # hold, for a Caddy that shared the host's, is gone.
        mounts=(
            Mount(IDENTITY_CONFIG),
            # O aviso que o provedor ESCREVE, e ele é um ARQUIVO: o arquivo de
            # configuração o aponta para `/config/notifications`, e o Authelia o
            # abre como arquivo — um DIRETÓRIO montado ali é um container que
            # morre no primeiro `open` (`is a directory`, medido). E a cópia
            # materializada de `/config` morre com o ambiente, então o aviso tem
            # de sobreviver a ele: quem o guarda é a pasta de estado (§3, a
            # promessa do backup), num arquivo que o container enche e que o
            # diretório de execução não copia.
            Mount(f"{IDENTITY_CONFIG}/{IDENTITY_NOTIFICATIONS}",
                  host=IDENTITY_NOTIFICATIONS, file=True),
            Mount(IDENTITY_DATA, host="data"),
        ),
        writes=((IDENTITY_YAML, _identity_conf), (IDENTITY_USERS, _identity_users)),
    ),
    # §7c's WebApp, and it comes up after the gate and before the edge: the gate
    # is what stands in front of it, and the edge is what proxies to it.
    Service(
        name=WEBAPP,
        label=f"services.{WEBAPP}.name",
        image=WEBAPP_IMAGE,
        # No published port: the door of this container is the network and the
        # edge that stands on it, and a port on the machine would be a second
        # door — one the gate's secret would have to keep closed on its own.
        mounts=(Mirror(), Gate(GATE_MOUNT)),
        command=_webapp_command,
        env=_webapp_env,
    ),
    Service(
        name=CADDY,
        label="services.caddy.name",
        image=Image(
            repo="docker.io/library/caddy",
            version="2.11.4",
            digest="sha256:0c994536bddb66445885237f1a5dcc1916bccea922661c76b4e9fc24061f9b52",
        ),
        # The site's port, and it is published outside the loop when the machine
        # is on a private network (§7e): the edge is what the person reaches.
        # Everything else of the environment is on the loop or on nothing at
        # all: whoever reaches a container from outside goes through THIS port.
        ports=_caddy_ports,
        mounts=(Mount(CADDY_CONFIG), Mount(CADDY_DATA, host=CADDY_STORAGE)),
        writes=(("Caddyfile", _caddy_conf),),
    ),
)


# --------------------------------------------------------------- the state ---

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


def held() -> dict[str, dict]:
    """The folder's pin, as recorded.

    A record nobody can read reads as none, and that is not a hole: a folder
    that came back without knowing where it was is re-pinned against the
    binary's manifest — §3's own answer for a copied folder — and the reference
    the service runs says which image that turned out to be.
    """
    try:
        raw = files.read_json(pin_file(), default={})
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {name: entry for name, entry in raw.items() if isinstance(entry, dict)}


def _record(service: Service, image: Image) -> None:
    """Write the pin the folder is at now — the one it just ran."""
    pins = held()
    pins[service.name] = {"version": image.version, "digest": image.digest}
    body = json.dumps(pins, ensure_ascii=False, sort_keys=True)
    files.atomic_write_text(pin_file(), body + "\n")


def order(version: object) -> tuple[int, ...]:
    """A version as the numbers in it, for the one comparison §3 asks for.

    §3 does not ask for semver: it asks which of two pins is AHEAD, so that the
    instance ahead of the binary is warned about and never downgraded. The
    numbers decide it; a version that carries none sorts as nothing, and the
    digest is what pins anyway.
    """
    if not isinstance(version, str):
        return ()
    numbers: list[int] = []
    for part in version.replace("-", ".").replace("_", ".").split("."):
        digits = "".join(character for character in part if character.isdigit())
        if digits:
            numbers.append(int(digits))
    return tuple(numbers)


def decide(service: Service, pins: dict[str, dict]) -> str:
    """What the folder's pin is against the binary's (§3, Código e delivery).

    Three answers: the folder is at the pin, behind it (re-pin — the pin only
    moves forward), or AHEAD of it — and an instance ahead warns and proceeds,
    because it is not downgraded.
    """
    at = pins.get(service.name) or {}
    version, digest = at.get("version"), at.get("digest")
    if not isinstance(version, str) or not isinstance(digest, str):
        return OUTDATED
    if order(version) < order(service.image.version):
        return OUTDATED
    if order(version) > order(service.image.version):
        return AHEAD
    return CURRENT if digest == service.image.digest else OUTDATED


def running(service: Service, pins: dict[str, dict]) -> Image:
    """The image this service runs: the binary's pin, or the folder's when ahead."""
    if decide(service, pins) == AHEAD:
        at = pins[service.name]
        return Image(service.image.repo, at["version"], at["digest"])
    return service.image


# ---------------------------------------------------------- the environment ---

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


def address_ready(address: str) -> bool:
    """Whether this machine has that address yet.

    Asked by BINDING it, and not by listing the interfaces: an address that
    cannot be bound is precisely the address the container would fail to
    publish on, so the probe and the failure are the same question.
    """
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    probe = socket.socket(family, socket.SOCK_STREAM)
    try:
        probe.bind((address, 0))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def wait_for(address: str, grace: float | None = None) -> bool:
    """Wait for the address to exist, with a bound. Measured, not a guess (§7a).

    A container published on an address the machine does not have yet comes up
    RUNNING AND WITHOUT ITS PORT: the runtime reports the container up, the port
    was never bound, and `start-limit-hit` follows on the next attempt. So the
    orchestrator waits here — and an address that does not arrive is said, and
    the container is not started at all, because a container standing without
    its port is the worse of the two answers.
    """
    if address_ready(address):
        return True
    deadline = time.monotonic() + (GRACE if grace is None else grace)
    while time.monotonic() < deadline:
        time.sleep(STEP)
        if address_ready(address):
            return True
    return False


def run_argv(service: Service, image: Image, key: bytes | None = None) -> list[str]:
    """The `podman run` that IS the service: every decision about it, in one list.

    Detached, named, labeled, on its network, publishing what it declares and
    mounting what it mounts — and then the image at the pin, and the command
    when the service has one. There is no restart policy on purpose: §3 says AT
    has no watchdog and does not propose to have one, and a container that comes
    back on its own is one.

    `key` is the key this subida derived, or `None` — passed straight through to
    `env_of`, which is the one reader that knows what to do with it.
    """
    argv = [
        "run",
        "--detach",
        "--name", container(service.name),
        "--label", f"{LABEL}={service.name}",
        "--network", service.network,
    ]
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


def networks() -> tuple[str, ...]:
    """Every network the manifest's services are on, in the order declared.

    It is asked of the manifest and never written by hand, the way `blocked` is:
    a service that moves to another network tomorrow enters this question by
    existing, and a network nobody is on is a network nothing creates.
    """
    return tuple(dict.fromkeys(service.network for service in SERVICES))


def _networks() -> None:
    """The environment's networks, created if this machine does not have them."""
    for name in networks():
        if not podman.ok(["network", "exists", name]):
            podman.run(["network", "create", name])


def _state_of(service: Service) -> str:
    """Whether the service's container is running, stopped, or not there — the
    RUNTIME's answer, which the decisions below read and the report does not."""
    answer = podman.run([
        "container", "inspect", "--format", "{{.State.Running}}",
        container(service.name),
    ])
    if answer.returncode != 0:
        return ABSENT
    return RUNNING if answer.stdout.strip() == "true" else STOPPED


def _here(image: Image) -> bool:
    """Whether the image is in this machine's store — "instalado", measured."""
    return podman.run(["image", "exists", image.reference()]).returncode == 0


def _shown_state(service: Service, image: Image) -> str:
    """The service as a PERSON reads it: running, installed, or not installed.

    It is the runtime's answer folded into the three words a person asks with.
    A container that was stopped, one that was taken down and one that is about
    to be created are the same answer to "is it on?" — and the difference that
    matters is whether the thing is HERE at all, which is the image.
    """
    if _state_of(service) == RUNNING:
        return RUNNING
    return INSTALLED if _here(image) else MISSING


# How long a report waits for an address to answer. It is a question about NOW,
# and a machine that does not answer in a second is a machine that does not
# answer — waiting longer would make `status` slow to say what it already knows.
STATUS_TIMEOUT = 1.0


def published(host: str, port: int) -> bool:
    """Whether something actually ANSWERS at the address.

    **Derived is not the same as true**, and this is where the difference is
    measured. The address comes from the machine's private network — a fact
    about the CONFIGURATION — and the report said "reachable at" from it: a
    folder whose environment was down announced an address while nothing at all
    listened on the port. What is reachable is what answers, and that is asked
    here and never inferred.
    """
    try:
        with socket.create_connection((host, port), timeout=STATUS_TIMEOUT):
            return True
    except OSError:
        return False


def inside(url: str, headers: dict[str, str]) -> int | None:
    """Ask a service from INSIDE the environment's network — the deploy's probe.

    **The services answer on the network and nowhere else**, which is the fix the
    container path needed (§7c: an app on a container's own loop is reached by
    nobody) — and it has a consequence for whoever asks a question: a process on
    the host reaches nothing, so the question has to be asked from where the
    services are. A throwaway container on the network comes up, runs one `curl`
    and goes away — `--rm`, so nothing is left standing.

    The image is the EDGE's (`CADDY`), the one image of the manifest that carries
    an HTTP client — measured: `curl`, `wget` and `nc` — and it is already pulled
    by the time anything asks.

    **The headers travel on the command's INPUT and never on its argv**, the rule
    every value that reaches a command by stream follows, and for the same
    reason: an argv is a `ps` on this machine. A status comes back as a number;
    everything else — no network, no image, a container that did not come up — is
    `None`, which is the honest "could not tell" and never an invented refusal.

    It has the shape `core/gate.Answer`, so whoever asks through the gate's seam
    hands it over as the transport.
    """
    asked = podman.run(
        ["run", "--rm", "-i",
         "--network", NETWORK,
         "--entrypoint", "curl", _caddy_image().reference(),
         "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-K", "-", url],
        input=_as_curl_config(headers),
    )
    if asked.returncode != 0:
        return None
    answered = asked.stdout.strip()
    return int(answered) if answered.isdigit() else None


def through_edge(url: str, headers: dict[str, str]) -> int | None:
    """Ask the EDGE by NAME, from inside the environment's network (§7f).

    **A pergunta é por um NOME, e o nome tem de chegar à borda** — e é isto que
    este transporte faz sem depender do resolver de quem roda o comando. O
    `curl` roda num container descartável na rede do ambiente, e o `connect-to`
    troca o ENDEREÇO da conexão mantendo o nome no SNI e no `Host`: o nome que a
    pessoa digita continua sendo o que a borda vê e o que ela responde, e o
    resolver da máquina — que não é o resolver do celular — fica de fora. Foi
    MEDIDO: numa máquina cujo `resolv.conf` não é o do ambiente, o nome não
    resolve e `gate.real` responderia "não deu para saber" sobre uma borda que
    está de pé e serve o nome.

    `-k` é o preço que o seam do portão já paga (`gate.real`): o certificado é
    do AT e nenhuma máquina o conhece, e o que se pergunta aqui é QUAL NOME a
    borda serve e o que a ACL responde — se ela não tivesse certificado para o
    nome, o handshake não fecharia e a resposta não seria um número.

    Tem a forma de `inside` e a mesma razão de ser: quem pergunta não está onde
    as coisas estão, e o runtime é o que leva a pergunta até lá.
    """
    parts = urlsplit(url)
    name = parts.hostname or ""
    port = parts.port or PORT
    asked = podman.run(
        ["run", "--rm", "-i",
         "--network", NETWORK,
         "--entrypoint", "curl", _caddy_image().reference(),
         "-s", "-o", "/dev/null", "-w", "%{http_code}", "-k",
         "-K", "-", url],
        input=_as_curl_config(headers, connect=(name, port, container(CADDY))),
    )
    if asked.returncode != 0:
        return None
    answered = asked.stdout.strip()
    return int(answered) if answered.isdigit() else None


def _as_curl_config(headers: dict[str, str],
                    connect: tuple[str, int, str] | None = None) -> str:
    """The headers as curl's own configuration, for its INPUT.

    A value is escaped so that a name carrying a quote is the name and not the
    syntax around it — the same care `_quoted` takes with a name on its way into
    a YAML file. `connect` adds the `connect-to` line, which is how a URL keeps a
    name that nothing resolves while the connection goes to a container that the
    environment's own network knows.
    """
    lines = []
    if connect is not None:
        name, port, target = connect
        lines.append(f'connect-to = "{name}:{port}:{target}:{port}"')
    for name, value in headers.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'header = "{name}: {escaped}"')
    return "\n".join(lines) + "\n"


def _start(service: Service, pins: dict[str, dict], key: bytes | None) -> bool:
    """Put one service on its feet. `False` when it did not get there.

    `key` é a chave derivada desta subida, e ela só desce porque o que a pasta
    guarda dos valores sorteados é o envelope: quem monta o diretório de
    execução tem de abri-lo (`_materialize`).
    """
    name = tr(service.label)
    where = _prepare(service, key)

    image = running(service, pins)
    if decide(service, pins) == AHEAD:
        # §3: an instance ahead of the binary's pin warns and proceeds. It keeps
        # running what it has — the pin does not move backward.
        print(tr("services.up.ahead", service=name,
                 held=image.version, pin=service.image.version))

    if podman.run(["pull", image.reference()]).returncode != 0:
        print(tr("services.up.failed", service=name, image=image.shown()))
        return False

    for address in addresses(service):
        if not address_ready(address):
            print(tr("services.up.waiting", service=name, address=address))
        if not wait_for(address):
            print(tr("services.up.no_address", service=name, address=address))
            return False

    # Whatever carries that name is AT's and is about to be replaced: the name
    # is the service, and two containers cannot share one.
    podman.run(["rm", "--force", container(service.name)])
    if podman.run(run_argv(service, image, key)).returncode != 0:
        print(tr("services.up.failed", service=name, image=image.shown()))
        return False

    _record(service, image)
    print(tr("services.up.service", service=name, image=image.shown(),
             where=where))
    return True


def _state_trouble(
    services: tuple[Service, ...] = SERVICES,
) -> tuple[Service, Path, str] | None:
    """O primeiro caminho da pasta de estado com a forma que o serviço não lê.

    O `up` monta uma PASTA por serviço (`Mount` com `host`, ou um ARQUIVO quando
    o serviço o exige — o `file` do provedor) e escreve os ARQUIVOS que ele lê,
    e um caminho que existe com a forma trocada — um **arquivo** onde ele vai
    montar a pasta, uma **pasta** onde ele vai montar o arquivo, ou uma **pasta**
    onde ele vai escrever o arquivo — estoura no meio da subida como uma exceção
    do `pathlib` (`mkdir`, `os.replace`), que o PyInstaller entrega como
    traceback sem uma frase. **Ele é um estado que o AT consegue diagnosticar
    antes de tentar**, e é por isso que a resposta é uma recusa dita e não um
    estouro.

    **A recusa e não o conserto**: o caminho pode ser da pessoa — um arquivo que
    ela pôs ali, ou o resto de uma versão anterior do AT —, e §3 já diz que o AT
    não mexe no que não é dele. Quem move ou apaga é ela, e o que a frase faz é
    dizer o caminho e o que ele deveria ser.

    `services` é o que se confere: a subida inteira (`up`) ou um serviço só
    (`restart`), que monta o estado de um e não tem por que recusar pelos outros.
    """
    for service in services:
        where = state(service.name)
        for mount in service.mounts:
            if isinstance(mount, Mount) and mount.host:
                path = where / mount.host
                if mount.file and path.is_dir():
                    return service, path, "file"
                if not mount.file and path.exists() and not path.is_dir():
                    return service, path, "folder"
        for name, _ in service.writes:
            path = where / name
            if path.is_dir():
                return service, path, "file"
    return None


def _refuse_shape(trouble: tuple[Service, Path, str]) -> None:
    """Diz a recusa da forma do estado — o caminho, e o que ele deveria ser."""
    service, where, wanted = trouble
    print(tr("services.state.shape", service=tr(service.label), where=where,
             wanted=tr(f"services.state.{wanted}")))


def up(ask: Ask | None = None, secret: Ask | None = None) -> str:
    """`up` — the FIRST time only (2026-09-28): bring a folder's environment up.

    §3's word for a folder with none yet. A folder that already has one — this
    folder's own pin says so (`held`) — is not `up`'s to touch again: it is
    told which word is (`update`), and returns `PROVISIONED`, an outcome and
    not a failure — nothing here is broken, the person just reached for the
    other word. The actual work of bringing every service up is `bring_up`,
    shared with `update` and with the switch (§6): this function's whole job is
    deciding WHICH of the two is allowed to call it.
    """
    if not podman.present():
        return ways_out(ask)
    if held():
        print(tr("services.up.provisioned"))
        return PROVISIONED
    return bring_up(ask, secret)


def update(ask: Ask | None = None, secret: Ask | None = None) -> str:
    """`update` — every time AFTER the first (2026-09-28): the infra at the pin
    the BINARY in this folder carries.

    §3's word for the release that already replaced the binary: the images of
    every service are re-verified and re-pinned against the manifest this
    artifact carries, every container is recreated (`podman rm --force`, like
    `up`), and what AT writes for each service is rewritten — the mirror of
    `up`'s own work, and the same function does it (`bring_up`). **A instância
    à frente do pin avisa e segue** — a mesma regra de sempre (`decide`,
    `_start`): não é rebaixada.

    **Nenhum serviço fica de pé por exceção, e o provedor é um deles.** Ele
    guarda quem está logado só em MEMÓRIA (§7b), e isto recria o container
    dele como recria todo o resto — então isto DERRUBA toda sessão que estava
    aberta, do mesmo jeito que um crash ou um `podman restart` avulso já
    derrubava (`restart` paga o mesmo preço, por um reinício só do provedor).
    **O que persiste é a PASTA, e isto não a toca**: o cofre, `App/`, o estado
    de cada serviço, e o que já foi SORTEADO — o segredo do portão, os três
    do provedor, a credencial do AT no notificador. `bring_up` sorteia esses
    valores só quando faltam (`_drawn`, `draw_gate`): uma pasta que já os tem
    selados não vê nada mudar neles, e é por isso que o cookie de uma sessão
    aberta antes continua ASSINADO depois — só que o provedor novo não sabe
    mais o nome que esse cookie carrega, e a pessoa volta ao login.

    Uma pasta que NUNCA subiu — sem pin nenhum registrado (`held`) — não tem o
    que `update`: o word certo para ela é `up`, e é o que a recusa diz.
    """
    if not podman.present():
        return ways_out(ask)
    if not held():
        print(tr("services.update.unprovisioned"))
        return FAILED
    outcome = bring_up(ask, secret)
    if outcome == UP:
        print(tr("services.update.done"))
        return UPDATED
    return outcome


def bring_up(ask: Ask | None = None, secret: Ask | None = None) -> str:
    """The one engine `up`, `update` and the switch share — or the two ways out (§7a).

    **Three doors, one body.** `up` calls this when the folder has none yet;
    `update` calls it when the folder already does; the switch (`switch.to_gate`)
    calls it directly, unguarded by either — a folder going from Forms back to
    the gate is neither a true first time nor blocked by having been up before,
    so it takes the engine and not either of the two words built around it.

    The absence of the Podman is not a dry refusal: AT says the two ways out
    and takes neither, because neither is his to take. Installing is an act of
    the person's machine, and the hosted path is a decision about how this
    folder is used — both are the person's, and with no terminal to ask in
    neither is taken (§3: the fail-closed posture).

    **The machine's permission comes first, and it is the same posture**: the
    low-port rule is asked about before a secret is drawn or a container named, so
    that a refusal is a folder nobody touched (`elevate`, §3's Privilege).

    **E depois a Chave Principal** (§4, item 50): ela é pedida depois da
    permissão e antes de qualquer sorteio, porque é ela que sela o que este `up`
    vai sortear e que abre o que a pasta já guarda — e uma subida que não a tem,
    ou que recebe uma que não abre, não sobe e diz por quê (`unlock`). Ela é
    lida UMA vez por subida, e vive o tempo dela: nada a guarda, e nada a
    escreve. Uma pasta que já está inteiramente selada — nada a abrir, nada a
    sortear — não a pede. **E a pasta que nasceu antes do selo a pede**, porque
    ela tem o que MIGRAR (item 50, corte `f`): cada valor em claro é re-sorteado
    e selado nesta subida, e é por isso que a migração não é um efeito de trocar
    o binário — é um ato, e ele custa a Chave Principal.

    The environment is not the SWITCH, and it does not pretend to be one: a
    service that does not come up is said, and what did come up stays up for
    whoever wants to look. The switch — paths.md's transactional change from one
    path to the other, with Forms on until the gate is proved — is
    `at_deploy/switch.py`'s, and it is the one that rolls back; this is what it
    calls, and what a person who asks for the environment directly gets.
    """
    if not podman.present():
        return ways_out(ask)

    # A forma da pasta de estado é a primeira coisa conferida, e de propósito:
    # um caminho que o serviço não consegue usar derruba a subida NO MEIO dela
    # como uma exceção do `pathlib`, e o traceback que sai no lugar da frase não
    # diz nem o caminho nem o que ele devia ser (`_state_trouble`). Antes da
    # elevação e da Chave Principal, porque não se pede senha nem Chave para uma subida
    # que já se sabe que não sobe.
    trouble = _state_trouble()
    if trouble is not None:
        _refuse_shape(trouble)
        return MALFORMED

    # §3 (Privilege): the environment inevitably demands elevation somewhere, and
    # §7a's edge port is where. It is asked BEFORE anything is drawn or started,
    # so that a refusal leaves the folder exactly where it was.
    refusal = elevate(ask)
    if refusal is not None:
        return refusal

    # §4: a Chave Principal entra aqui, antes de qualquer sorteio e de qualquer
    # container. A Chave que sai dela é desta subida e de mais nada.
    key, refusal = unlock(secret)
    if refusal is not None:
        return refusal

    # §7b: the gate's secret is drawn at INSTALLATION — here, once — and kept in
    # the folder from then on. It is drawn before anything starts because the
    # Caddyfile is written by the service's own writer, and a Caddy that came up
    # without the line would be an edge that attaches nothing and a WebApp that
    # refuses every identity it is handed.
    #
    # **E só se sorteia com a Chave na mão**: os valores que faltam — o portão e
    # os três do provedor — são exatamente o que faz o `unlock` pedir a Chave
    # Principal, então quando não há Chave é porque eles todos já estão na pasta
    # — e o que já está lá, SELADO, não é sorteado de novo. Sortear sem Chave
    # seria escrever um valor em claro na pasta, que é o que este item existe
    # para não haver.
    #
    # **A pasta que nasceu antes do selo é a exceção, e é esta linha que a
    # migra** (item 50, corte `f`): um valor em CLARO não é mantido — ele é
    # re-sorteado, porque pode já ter sido copiado, e um valor que já viajou não
    # volta a ser segredo por ser selado depois. A decisão é declarada uma vez,
    # antes dos sorteios.
    if key is not None:
        born = _clear_drawn()
        if born:
            print(tr("services.migrated", count=len(born)))
        where = caddy_service.gate_file()
        drawing = not _held(where) or _clear(where)
        draw_gate(key)
        if drawing:
            print(tr("services.gate.drawn", where=where))
        # E os três do provedor, pela mesma razão de ordem: o `configuration.yml`
        # é composto a partir do que a pasta guarda, e o provedor lê esse arquivo
        # ao SUBIR.
        for name in IDENTITY_SECRETS:
            _drawn(IDENTITY, name, key)

    # O diretório de execução é reescrito inteiro a cada subida — ele é a cópia
    # que serve ESTA —, e o portão entra nele antes de qualquer serviço: o
    # WebApp o lê de lá (§ `GATE_MOUNT`), e o `_prepare` do WebApp não é quem o
    # escreve, porque o portão não é arquivo de serviço nenhum (`draw_gate`).
    _clear_run_dir()
    _materialize_gate(key)

    # **A poda do storage do Caddy vem antes de qualquer container subir**, e ela
    # é a única escrita do AT no que o container encheu: o conjunto de nomes é
    # dele (`names`), então o certificado de um nome que ele deixou de servir sai
    # agora — com a chave privada em claro que o portão do backup barraria sem
    # motivo. O que o container escreveu de um nome ainda servido fica intacto.
    pruned = _prune_names()
    if pruned:
        print(tr("services.storage.pruned", count=len(pruned)))

    pins = held()
    _networks()
    for service in SERVICES:
        if not _start(service, pins, key):
            return FAILED
    return UP


def _service(name: str) -> Service | None:
    """A service of the manifest by its name, or `None` — the manifest is the list."""
    return next((service for service in SERVICES if service.name == name), None)


def _caddy_image() -> Image:
    """The edge's pinned image — the manifest always carries the Caddy."""
    service = _service(CADDY)
    assert service is not None
    return service.image


def restart(name: str, secret: Ask | None = None) -> bool:
    """Put one service's container up again, with the files AT writes for it.

    It exists for the gate and for one reason (`set_credential`): the provider
    reads `users.yml` when it STARTS, so a derivation rewritten under a standing
    container is a derivation nothing proves — the act that changes a credential
    is only complete when the container has read the file again.

    **It is not `up`**: nothing is pulled (the container was standing, so the
    image is here) and the pin is not re-recorded. What it IS is `_prepare` —
    the service's own writers, run again — and then the container recreated from
    the same argv `_start` would use. A service whose container never stood is
    not restarted and answers `False`: there is nothing to start again, and what
    brings it up is `up`, with the pull and the pin (`set_credential` says so).

    **O segredo de sessão não é re-sorteado, e o cookie continua ASSINADO —
    mas quem está dentro não.** O provedor guarda o registro de quem está
    logado só na MEMÓRIA do container (§7b), e este reinício recria o
    container (`podman rm --force`, a mesma linha que `_start` roda): toda
    sessão que estava aberta cai, e a pessoa volta ao login com um cookie que
    o provedor novo não conhece. **Este é o preço que o reinício de uma
    credencial trocada paga**, e §3 declara esse preço onde o ato do operador
    é registrado — não há meio de trocar a credencial sem o provedor ler o
    arquivo de novo, e não há meio de ele ler o arquivo de novo sem recriar o
    container que o guardava em memória.

    **E ele PEDE a Chave Principal, porque ele monta de novo** (`unlock`): o
    `_prepare` reescreve o `configuration.yml` — os três do provedor entram
    nele, e o que a pasta guarda deles é o envelope — e o diretório de execução
    só recebe o arquivo ABERTO. Sem Chave Principal, o reinício não acontece e é dito por
    quê: a cópia que está lá é a da subida, e montar por cima dela o envelope
    seria entregar ao provedor o que ele não sabe ler.
    """
    service = _service(name)
    if service is None or not podman.present():
        return False
    if _state_of(service) == ABSENT:
        return False

    # A mesma recusa da subida, e só sobre ESTE serviço: o `_prepare` daqui monta
    # o estado dele e mais nada, e um caminho torto de outro serviço não é razão
    # para recusar o reinício deste (`_state_trouble`).
    trouble = _state_trouble((service,))
    if trouble is not None:
        _refuse_shape(trouble)
        return False

    key, refusal = unlock(secret)
    if refusal is not None:
        return False

    where = _prepare(service, key)
    image = running(service, held())

    for address in addresses(service):
        if not address_ready(address):
            print(tr("services.up.waiting", service=tr(service.label),
                     address=address))
        if not wait_for(address):
            print(tr("services.up.no_address", service=tr(service.label),
                     address=address))
            return False

    # The name is the service, and two containers cannot share one — the same
    # line `_start` runs, for the same reason.
    podman.run(["rm", "--force", container(service.name)])
    if podman.run(run_argv(service, image, key)).returncode != 0:
        print(tr("services.up.failed", service=tr(service.label),
                 image=image.shown()))
        return False

    print(tr("services.restarted", service=tr(service.label), where=where))
    return True


def set_credential(name: str, credential: str, secret: Ask | None = None) -> str:
    """Give a person the credential the gate proves — the operator's act (§7b).

    Item 27's second operator act, and the three things it is are one sentence:
    **who** is an actor belongs to AT, the row carries the credential, and the
    gate proves it — so the row is written (`actors.change_credential`, which
    derives it like every other), the `users.yml` is derived from it by the
    service's own writer (`_prepare`), and the provider is started again so that
    the derivation new is the one it proves (`restart`).

    **The hosted path has no gate, and that is not an error.** §3 says Basic and
    Forms are the same credential, so the row changes and there is nothing to
    restart: the door takes the new credential on the next request. It is SAID,
    because a person who changed a credential expects a door to take it, and
    being quiet about which door would be the lie.

    **The price of the restart is declared and not hidden.** The sessions
    already open are not evicted — the session secret is the same and the
    registry is the folder's — so a credential changed because it leaked leaves
    the sessions it had opened standing until they expire. §3 records it; this
    function says it on the screen (`services.credential.changed`), because
    whoever is changing a credential is the one who has to know.

    **E o reinício pede a Chave Principal** (`restart`, §4): ele monta o
    `configuration.yml` de novo, e o que a pasta guarda dos três do provedor é o
    envelope. Uma Chave Principal que não vem deixa a pasta com a credencial nova e o
    portão provando a antiga — que é o `PENDING` que já existia, e a palavra diz
    as duas coisas: o que mudou e o que ainda não foi provado.

    A name nobody wears is `CREDENTIAL_UNKNOWN` and not an error: `named` is the
    one lookup the entrance and the gate share, so this answers what the door
    would answer, with the words the deploy owns.
    """
    row = actors.named(name)
    if row is None:
        return CREDENTIAL_UNKNOWN
    who = str(row.get("name", "")).strip()

    actors.change_credential(row, credential)

    if not gate.on_gate():
        print(tr("services.credential.hosted", name=who))
        return CREDENTIAL_CHANGED
    if not restart(IDENTITY, secret):
        print(tr("services.credential.pending", name=who))
        return CREDENTIAL_PENDING

    print(tr("services.credential.changed", name=who,
             where=state(IDENTITY) / IDENTITY_USERS))
    return CREDENTIAL_CHANGED


def ways_out(ask: Ask | None = None) -> str:
    """The two ways out of a machine without Podman (§7a).

    A yes installs it: AT says how, and stops there — it does not install
    anything, because that is the person's machine and §3 spends elevation only
    on an explicit request. Anything else keeps the folder where it already
    works, on the hosted path (§6), which needs nothing beyond the binary.

    **A folder already on the container path gets a different question**, and it
    is the switch that asks it: for that folder "continue on the hosted path" is
    not nothing — the Forms is off, and AT is closed — so the second way out is
    restoring it, which moves the record. The import is inside the function
    because `switch` reads this module.
    """
    from at_deploy import switch  # noqa: PLC0415 — switch imports this module

    # The PATH is asked first, and it comes before the terminal is looked for:
    # which of the two questions is owed does not depend on whether anybody can
    # answer it, and a folder on the container path must never be told that
    # "continuing on the hosted path" is the way out of a machine with no Podman.
    if gate.on_gate():
        return switch.missing(ask)
    if ask is None:
        print(tr("services.no_podman.no_tty"))
        return NO_ANSWER
    if is_yes(ask(tr("services.no_podman.ask"))):
        print(tr("services.no_podman.install"))
        return INSTALL
    print(tr("services.no_podman.hosted"))
    return HOSTED


def down(say: bool = True) -> None:
    """Take the environment down: AT's containers and its network.

    The FOLDER stays exactly where it is — what comes down is what AT started,
    and nothing that lives in the folder moves (§3, the backup promise).

    `say=False` is the SWITCH's, and it is not a whisper: a switch that is undoing
    itself owes the person the reason, in its own words, and a "ambiente abaixo"
    in the middle of that report would read as the thing that worked.
    """
    if not podman.present():
        if say:
            print(tr("services.no_podman.down"))
        return
    for service in SERVICES:
        podman.run(["rm", "--force", container(service.name)])
    for name in networks():
        podman.run(["network", "rm", name])
    # E a cópia que servia a subida vai junto: o diretório de execução é a
    # metade que morre com o ambiente (`_clear_run_dir`). O que o container
    # encheu está na pasta de estado, que não é tocada.
    _clear_run_dir()
    if say:
        print(tr("services.down.done", where=paths.services_dir()))


def status() -> None:
    """What is standing: the path this folder is on, and each service.

    **This artifact is the CONTAINERS'**, and this report is the containers'
    state and nothing else. Whoever stays on the hosted path needs `at-cli`
    alone, and the AT served locally — `at-cli webapp` — is not this binary's to
    bring up, take down or report on. Which path the folder is on is the
    SWITCH's business (§6), and the words that change it — `switch`, `forms` —
    are where a person reads it; a report of what is standing does not have to
    repeat it.

    Two things may serve the same folder — the `at-cli` on the loop and the
    WebApp in a container — and this artifact does not arbitrate that: the
    conflict is named and is another problem.
    """
    if not podman.present():
        print(tr("services.no_podman.status"))
        return

    # **An address is said only when something ANSWERS at it.** A fact about the
    # machine's network is not a fact about being reachable, and the report used
    # to say "reachable at" from the first alone: an address nobody served was
    # announced as if the person could open it. What is reachable is what
    # answers, and an address that answers nothing is not said at all — it is
    # not the report's business to name a door that is not there.
    #
    # **A pergunta vai ao ENDEREÇO onde a borda publica e a resposta diz o
    # NOME**, e os dois não são a mesma coisa: o nome é o que `site_host`
    # resolve — o do Tailscale quando há um, `at.localhost` quando não há —,
    # e perguntar por ELE dependeria de um terceiro serviço (o agente, o
    # navegador) respondendo antes que esta função possa dizer que a borda está
    # de pé. O endereço é desta máquina sempre (§7e), e perguntar por ele não
    # depende de mais nada.
    served = published(vpn.address() or LOOP, PORT)
    if served:
        print(tr("services.status.site",
                 url=caddy_service.address(site_host(), PORT)))

    # The services are a TABLE — always, and that is the point. Three lines of
    # one shape in a column are what a person compares, and the drawing is
    # `ui/words.table`'s: the same one the `cli`'s listing uses, so the two
    # artifacts print a table the same way.
    pins = held()
    rows = [[
        tr("services.status.head.service"),
        tr("services.status.head.state"),
        tr("services.status.head.image"),
    ]]
    for service in SERVICES:
        image = running(service, pins)
        rows.append([
            tr(service.label),
            tr(f"services.status.{_shown_state(service, image)}"),
            image.shown(),
        ])
    # A linha em branco separa a tabela do que veio antes, e só existe quando
    # ALGO veio antes: a tabela é a primeira coisa do relatório na maioria das
    # vezes, e um relatório que começa com uma linha vazia começa torto.
    if served:
        print()
    print(words.table(rows))


def standing() -> bool:
    """Whether the environment is on its feet: every service's container running.

    It is the question §7a's checks end at, and the one thing an exit code
    cannot carry: choosing a way out of a machine with no Podman, or refusing
    the elevation, EXITS `0` — nothing failed — and leaves the environment
    standing nowhere. So it is asked of the CONTAINERS and not of the record,
    because what a person needs to know is what is running.

    `status` says the same thing one service at a time, and the Wizard of §7
    reads it as one answer (`at_deploy/wizard.py`): the step of §7a closed when
    the environment is standing, and not when the command happened to exit `0`.
    """
    if not podman.present():
        return False
    return all(_state_of(service) == RUNNING for service in SERVICES)
