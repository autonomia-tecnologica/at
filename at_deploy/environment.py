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

# ruff: noqa: F401 — this file is the facade: it re-exports every name the product reads from here

from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

from at.core import actors, files, gate, paths
from at.core.migrations import is_yes
from at.encryption import vault
from at.i18n import tr
from at.services import caddy as caddy_service
from at.ui import words
from at_deploy import podman, vpn
from at_deploy.environment_base import (
    ABSENT,
    AHEAD,
    ALL,
    CADDY,
    CADDY_CONFIG,
    CADDY_DATA,
    CADDY_STORAGE,
    CREDENTIAL_CHANGED,
    CREDENTIAL_PENDING,
    CREDENTIAL_UNKNOWN,
    CURRENT,
    FAILED,
    FALLBACK_HOST,
    GATE_DIR,
    GATE_ENV,
    GATE_MOUNT,
    GRACE,
    HOSTED,
    IDENTITY,
    IDENTITY_CONFIG,
    IDENTITY_DATA,
    IDENTITY_ENCRYPTION,
    IDENTITY_JWT,
    IDENTITY_NOTIFICATIONS,
    IDENTITY_PORT,
    IDENTITY_SECRETS,
    IDENTITY_SESSION,
    IDENTITY_USERS,
    IDENTITY_YAML,
    INSTALL,
    INSTALLED,
    LABEL,
    LOOP,
    MALFORMED,
    MISSING,
    NETWORK,
    NO_ANSWER,
    OUTDATED,
    PIN_DIGITS,
    PIN_PREFIX,
    PORT,
    PREFIX,
    PROVISIONED,
    RUN_ENV,
    RUN_ID,
    RUN_SERVICES,
    RUNNING,
    SECRET_BYTES,
    STEP,
    STOPPED,
    SYSCTL_FILE,
    SYSCTL_PORTS,
    UNREADABLE,
    UP,
    UPDATED,
    WEBAPP,
    WEBAPP_HOST,
    WEBAPP_PORT,
    Ask,
    SealedRefused,
    Spend,
)
from at_deploy.environment_edge import (
    _caddy_conf,
    _caddy_ports,
    _prune_names,
    names,
    portal_url,
    site_host,
)
from at_deploy.environment_identity import (
    _identity_conf,
    _identity_users,
    _quoted,
)
from at_deploy.environment_models import (
    Gate,
    Image,
    Mirror,
    Mount,
    Port,
    Service,
)
from at_deploy.environment_paths import (
    _folder_id,
    container,
    gate_materialized,
    gate_opened,
    materialized,
    pin_file,
    run_dir,
    state,
)
from at_deploy.environment_pins import (
    _record,
    decide,
    held,
    order,
    running,
)
from at_deploy.environment_probe import (
    STATUS_TIMEOUT,
    _as_curl_config,
    _here,
    _shown_state,
    _state_of,
    published,
)
from at_deploy.environment_run import (
    _clear_run_dir,
    _materialize,
    _materialize_gate,
    _prepare,
    _run_place,
    addresses,
    env_of,
    ports_of,
    run_argv,
)
from at_deploy.environment_secrets import (
    _clear,
    _clear_drawn,
    _derived_b64,
    _drawn,
    _drawn_files,
    _held,
    _kept,
    _opened,
    _text,
    draw_gate,
)
from at_deploy.environment_webapp import (
    _webapp_command,
    _webapp_env,
    binary,
)

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
