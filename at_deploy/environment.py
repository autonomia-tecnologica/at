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
with them stands with them. The DNS is the one service that talks to nobody, and
it is the one service on `DMZ`; separating anything else would buy nothing, and
what keeps the WebApp closed on a network it shares is the gate secret (§7b),
not the segment.

**What each service runs.** `dnsmasq` is up: its configuration is the
environment's own, the names of access (§7a's own words for it). The `caddy` is
up as the edge that publishes AT — the same Caddyfile generator the hosted path
reads, because it is the same Caddy answering the same questions, and what the
two paths answer DIFFERENTLY is what an address means on each side: the storage
is a path and not a decision (§7a), and the backend, the provider and the bind
are the container path's (`_caddy_conf`). The `identity-provider` is up as §7b's
gate: Authelia, configured by AT to be the one that proves who is calling, with
AT standing behind it as an app and not as an exception — and the gate secret,
drawn at installation, is the line that says the request came through it. And
the `webapp` is up as §7c's container: the WebApp, moved off the person's
machine and behind the gate, answering on the network because the loop is a
place nobody in the environment can reach. And
§7f's `notifier` is up as the LAST of them: ntfy, configured by AT to keep
everything it remembers inside its own state folder, published on the loop, and
**out of the gate** — the one thing §7f inherits instead of deciding.

**The gate does NOT front the notifier, and that is a measurement.** The gate
authenticates by redirect and session cookie, and a headless phone app takes the
302 and never connects: measured in the retired environment, the notifier
answered `subscribers=0` behind Authelia and `101` without it. So the Caddyfile
the environment generates does not name the notifier and the identity provider's
access rule does not either — the notifier is not one more app behind the gate,
and its authentication, wherever it is exposed, is the token ACL §6 declares for
it. Putting it behind the gate is the one change here that has already been
measured to break it.

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

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from at.core import actors, files, gate, paths, tables
from at.core.migrations import is_yes
from at.i18n import tr
from at.services import caddy as caddy_service
from at.ui import words

from at_deploy import podman, vpn

# What a person answers with, injected the way `boot` and `lang` take theirs: a
# test asks the same question without a terminal.
Ask = Callable[[str], str]

# What spends an elevation, injected the same way — and the suite MUST inject it:
# a test that ran `sudo` would be a test that asked a person for a password.
Spend = Callable[..., None]

# The outcomes of `up`, and the CLI is what turns them into an exit code.
UP = "up"                 # the environment is standing
INSTALL = "install"       # the person installs the Podman; AT said how
HOSTED = "hosted"         # the folder stays on the hosted path, and nothing moved
NO_ANSWER = "no_answer"   # no terminal to ask in: neither way was taken
FAILED = "failed"         # a service did not come up

# The outcomes of the gate's credential change — item 27's operator act (§7b).
# The row is written in all three: what separates them is how far the change
# travelled, and the person is owed exactly that difference.
CREDENTIAL_CHANGED = "changed"   # the row, the derivation and the provider
CREDENTIAL_UNKNOWN = "unknown"   # nobody in this folder wears that name
CREDENTIAL_PENDING = "pending"   # the folder has it; the gate does not yet

# The port the edge is reached on, and it is 443 because that is the port a URL
# does not say: the person types `https://at.local`, and §7f's phone takes a URL
# and nothing more — a `:8443` in the middle of it is a port nobody asked to
# know. The Caddy is the edge, and its port is the ONE the environment publishes
# outside the loop (§7e).
#
# **It costs no elevation of its own, and that was measured the moment the
# manifest had a lower port**: a rootless container publishes nothing below the
# kernel's floor, and §7a's `dnsmasq` publishes DNS on `53` — so the floor has
# to move to `53` for the environment to come up at all (`elevate`), and `443`
# stands above it from then on. Before the DNS existed this port had to be an
# alternative one (`8443`); it does not any more, and the person's rule is that
# the environment is reached on `443` and on no other port.
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

# The network of the service that talks to NOBODY. A DMZ by what it is: the only
# thing it holds is the DNS, which answers and asks nothing, and what a service
# there cannot do is reach the WebApp — no route to the environment's network.
# Separating anything else would cost more than it buys: the notifier has
# business with the WebApp (§7f), and the edge has business with everything.
DMZ = "at-dmz"

# The prefix of every container AT creates. A container is named for the
# service it runs, and the name is AT's: `down` removes what the name says,
# and another AT on this machine has other names.
PREFIX = "at-"

# The label every container of this environment carries, for whoever reads the
# runtime by hand and wants to know whose it is.
LABEL = "at.service"

# The address a service publishes on when it declares none: the loop, because
# that is what closes the LAN (measured — see the module's docstring).
LOOP = "127.0.0.1"

# The machine's rule about low ports, and the ONE thing §7 asks of it. A user
# process may only bind ports from this floor up, and §7a's first service
# publishes DNS on 53 — which is under it on every machine that ships the rule.
# The name is the DOTTED one the command takes; the file that ANSWERS it spells
# the same thing with slashes, and the two are not interchangeable.
SYSCTL_PORTS = "net.ipv4.ip_unprivileged_port_start"
SYSCTL_FILE = Path("/proc/sys") / SYSCTL_PORTS.replace(".", "/")

# Inside the containers, where each service reads what AT writes for it.
DNSMASQ_CONFIG = "/etc/dnsmasq.d"
CADDY_CONFIG = "/etc/caddy"
CADDY_DATA = "/data"

# A pasta do SERVIÇO que o Caddy monta em `CADDY_DATA`: o storage dele, com a CA
# local e os certificados emitidos contra ela. Ela é um nome e não a linha do
# `Mount` porque DOIS lugares têm de concordar sobre ela — o que o container
# monta, e onde a CA está para quem precisa confiar no certificado (`authority_file`).
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

# §7f's notifier, and the name is the ROLE and not the brand: ntfy serves it
# today, and the day another one serves it the rest of this file does not move.
# **Its port is AT's, and it is neither ntfy's default nor a low one.** ntfy
# listens on 80, under the kernel's low-port rule, and §3's elevation asks for
# the narrowest thing that works: the floor moves to the LOWEST port the
# environment publishes, DNS's 53 is the only one it names, and this is the same
# decision as the site's port being 8443 and not 443. What is left is the
# vendor's own other port — `:2586` is the one every example in ntfy's
# documentation uses for a listener behind a proxy — and the notifier publishes
# on the loop, where nothing fronts it.
NOTIFIER = "notifier"
NOTIFIER_PORT = 2586

# O nome que o notificador responde embaixo do domínio do ambiente — e ele é a
# MARCA, ao contrário do nome do SERVIÇO acima, que é o papel. A diferença é
# quem lê cada um: `NOTIFIER` nomeia o serviço para o AT (e o dia em que outro
# servir o papel, só ele se muda), e este é o nome que o CELULAR digita e que o
# app do ntfy guarda como servidor dele. **Medido, e é o que decide a forma**:
# o ntfy NÃO funciona sob um caminho (`at.local/ntfy`) — o mantenedor diz que é
# preciso um subdomínio, e o app e a interface quebram sob um prefixo —, então o
# notificador ganha o dele no mesmo domínio em vez de uma rota.
NOTIFIER_HOST = "ntfy"

# What the notifier's container sees of its own state folder: the configuration
# AT writes, and the ONE folder where everything it REMEMBERS lives. **The
# paths are the decision**, and not decoration: ntfy's `cache-file` has no
# default — an unset cache is a memory that dies with the container —, the
# attachments have none either, and the auth database lives in `/var/lib/ntfy`
# unless it is moved. §7f's sentence is that the topic and its memory survive a
# backup, and a backup covers the folder and nothing else (§3).
NOTIFIER_CONFIG = "/etc/ntfy"
NOTIFIER_DATA = "/var/cache/ntfy"
NOTIFIER_YAML = "server.yml"

# The authentication database, inside the notifier's own data folder: the
# accounts, and the HASHES of their tokens. It is named here because two things
# have to agree about it and neither owns the other — the line ntfy reads below,
# and the probe that waits for it to be born before the delivery writes its
# credential into it (`services/notifier.py`).
NOTIFIER_AUTH = "user.db"

# How much secret the identity provider's own drawing carries. The same price
# as the gate's (`caddy.GATE_BYTES`): it is a value a header and a cookie carry,
# never one a person types.
SECRET_BYTES = 32

# The DOMAIN of the environment — the name it owns and answers for — and the one
# every service that is reached by a name hangs its own under. The brand is not
# translated (§3), and `.local` is the name a machine answers to on its own
# network.
#
# **The site keeps this name and the others take theirs below it**, because the
# site is what a person types without thinking about it: `at.local` IS the
# environment (§7a), and the notifier is the one service that has to be reached
# by a name of its own — `NOTIFIER_HOST` below says why it cannot live under a
# path.
NAME = "at.local"

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
    """A folder of the instance, inside the container.

    `host` is relative to the service's own state folder — `App/services/<name>/`
    — and empty means the folder itself: §7 puts every service's persistent
    state there, so a service whose state does not fit is a service that does
    not enter, and what it mounts is always inside what the backup covers.
    """

    container: str
    host: str = ""

    def volume(self, where: Path) -> str:
        """The argument the runtime reads, with the SELinux label it needs.

        `:Z` is podman's word for "give this folder a private label": without it
        an enforcing host stops the container at the first read, and where there
        is no SELinux it is ignored. It is the state folder AT created, so the
        relabel touches nothing of the person's.
        """
        source = where / self.host if self.host else where
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
    asking, and it ignores the state folder it is handed: this folder is not the
    service's, it is the person's.
    """

    def volume(self, where: Path) -> str:
        root = paths.working_folder()
        return f"{root}:{root}:Z"


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
    for it. This is that implementation and this is the first entry of the list:
    §7a's `dnsmasq` publishes DNS on `53`, and a machine that ships the
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


def _webapp_env() -> tuple[tuple[str, str], ...]:
    """What §7c's WebApp is TOLD: where its gate is, and where its folder is.

    The gate, because a container cannot see the host's loop and the name is the
    environment's to say (`GATE_ENV`). And the FOLDER, which is the same lesson
    as the address and was measured the same way: run from a checkout, the
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
    """
    return (
        (GATE_ENV, f"{container(IDENTITY)}:{IDENTITY_PORT}"),
        (paths.ROOT_ENV, str(paths.working_folder())),
    )


def _notifier_command() -> tuple[str, ...]:
    """What §7f's container runs — and it is MEASURED, not read off the image.

    The image's entrypoint is `ntfy` and it carries **no `CMD` at all**: run with
    nothing after the image, it prints its own help and exits, which is a
    notifier that never comes up and an `at-deploy services status` that says so
    forever. So the subcommand is a decision of AT's, written where every other
    decision about a container is. It is a callable like the WebApp's even though
    it resolves nothing, because `Service.command` has one shape.
    """
    return ("serve",)


def site_host() -> str:
    """The NAME the environment's edge serves the site at — the environment's own.

    §7a is what this reads, and it is the environment's DOMAIN and not a fact
    about the machine: `at.local` is the name the DNS of the environment answers
    for, and it is a name — which was measured twice, once against each half of
    the environment. The gate refuses a cookie domain without a dot that is not
    an IP, so the word `localhost` is out; and TLS needs a NAME for the SNI — a
    client connecting to an ADDRESS sends none, and the Caddy answers the
    handshake with `internal error` because it has no certificate it can serve.

    **The private network does NOT name the site, and that is this piece's
    decision.** §7e is what the network changes, and what it changes is the
    ADDRESS the edge publishes on and that the DNS answers with — never the
    name. The name the network gives the machine (`vpn.name`) named the site
    while the site was the only thing the environment had; now that every
    service has its own name under one domain, a site that answered under the
    network's name would be a second domain, a second certificate and a gate
    whose `authelia_url` pointed at the other one — the portal a phone reached
    by the network's name would redirect it to a name the network cannot
    resolve. What the person points at the environment's DNS is the whole of
    it, and the backlog already says that is the person's act and not AT's.

    **It is a function and not a constant because every file that has to agree
    on the name is written when the environment comes up**: the Caddyfile, the
    identity provider's access rule and its cookie, and the URL the switch says.
    """
    return NAME


def notifier_host() -> str:
    """§7f's notifier by name — `ntfy.at.local`, under the environment's domain.

    It is a NAME of its own and not a path of the site's, and that is a
    measurement (`NOTIFIER_HOST`): the notifier's own clients do not work under
    a subpath. What serves it is the edge, with a certificate and WITHOUT the
    ask — the other half of the same measurement, because a headless phone app
    takes the gate's 302 and never connects.

    It is a function for the same reason `site_host` is: the files that have to
    agree about it — the DNS of the environment and the Caddyfile — are written
    when the environment comes up.
    """
    return f"{NOTIFIER_HOST}.{NAME}"


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
    """Every name the environment answers for, in the order of the manifest.

    It is asked of the manifest and never written by hand, the way `networks` is:
    a service that starts being reached by a name tomorrow enters this question
    by existing. What decides is whether a service HAS a name — the site keeps
    the domain's own, the notifier hangs its under it — and the services the
    edge and the WebApp reach by their container names (the gate, the WebApp
    itself) have none, because nobody types them.
    """
    return (site_host(), notifier_host())


def _dnsmasq_conf() -> str:
    """The names the environment answers for, in dnsmasq's words.

    §7a gives this service one job — customizing the access URLs — and the names
    are the environment's: `at.local`, which is the site, and `ntfy.at.local`,
    which is §7f's notifier. The ADDRESS it answers with is where the edge
    actually is: the private network's when the machine is on one (§7e), the
    loop otherwise — the network decides WHERE, never WHAT the names are.

    **Nome a nome, e não um curinga.** `address=/.at.local/…` responderia por
    qualquer nome embaixo do domínio — inclusive um que ninguém pediu, que é uma
    resposta que o ambiente não tem o que servir: a borda não tem certificado
    para ele e a pessoa levaria um erro de handshake em vez de um nome que não
    existe. Uma linha por nome é o que o ambiente responde, e ela cresce com o
    manifesto (`names`).
    """
    where = vpn.address() or LOOP
    lines = [f"# {tr('services.dnsmasq.file.header')}"]
    lines += [f"address=/{name}/{where}" for name in names()]
    return "\n".join(lines) + "\n"


def _dnsmasq_ports() -> tuple[Port, ...]:
    """A porta do DNS, no endereço onde a borda está.

    **Quem pergunta por estes nomes não está na máquina.** `at.local` e
    `ntfy.at.local` não existem em DNS público nenhum — são do ambiente, e este
    `dnsmasq` é o único que os responde —, então publicá-lo no laço é responder
    a quem já está dentro e a mais ninguém: o navegador de outra máquina e o
    celular não têm a quem perguntar, e o split-DNS do tailnet não tem endereço
    para onde apontar. O endereço é o mesmo da borda, pela mesma §7e: a rede
    decide onde, e `_caddy_ports` já é esta expressão.

    **É o segundo e último serviço que sai do laço, e ele sai pela mesma razão
    que o primeiro**: o que a pessoa alcança tem que estar alcançável. O que ele
    publica é um servidor de nomes do ambiente, na rede privada que a pessoa
    escolheu, e não em todo endereço.
    """
    where = vpn.address() or LOOP
    return (Port(53, "udp", address=where), Port(53, address=where))


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

    **E o SEGUNDO nome vem com eles**: §7f's notifier is served by this same
    edge, with its own certificate and WITHOUT the ask (`outside`), and it is
    reached by the container's name on the network like the WebApp — that is
    what the notifier joins the environment's network for, and what keeps the
    `subscribers=0` measurement respected: the edge fronting it is not the
    gate asking about it.
    """
    return caddy_service.caddyfile(
        site_host(), PORT, WEBAPP_PORT,
        gate=caddy_service.gate_secret(),
        storage=CADDY_DATA,
        auth=f"{container(IDENTITY)}:{IDENTITY_PORT}",
        bind=ALL,
        upstream=container(WEBAPP),
        outside=((notifier_host(), f"{container(NOTIFIER)}:{NOTIFIER_PORT}"),),
    )


def _caddy_ports() -> tuple[Port, ...]:
    """The site's port, on the address §7e puts the site at.

    It is the port the person reaches, and it is published on the machine's
    PRIVATE NETWORK address when there is one — the same expression the DNS's
    own answer uses — and on the loop when there is not, which is the supported
    state and not a degraded one. **It is not `0.0.0.0`**: a port published on
    every address is a port on the LAN, and what §7a measured and this product
    promises is that nothing of AT's is out there except the edge on the network
    the person chose.

    It is a function and not a constant for the same reason `site_host` is: the
    address is measured when the environment comes up, and a value read at
    import would stop being true the moment the person joined a network.
    """
    return (Port(PORT, address=vpn.address() or LOOP),)


def authority_file() -> Path:
    """A CA que o certificado da borda carrega — e o arquivo que o CELULAR importa (§7f).

    A borda emite com `tls internal`, que é a CA do próprio Caddy, e é por isso
    que o certificado de `ntfy.at.local` não é de autoridade pública nenhuma: §3
    declara esse preço, e quem precisa confiar nele tem de ser apresentado à CA.
    O arquivo é o MESMO para os dois caminhos — a linha do Caddy que o escreve é
    dele e não muda (§ `caddy.authority_file`) —, e o que muda é onde ele está:
    aqui é o storage do serviço, dentro da pasta de estado, que é a pasta que o
    backup cobre.

    **Ele é nomeado porque o app do celular não usa o cofre do aparelho.** Medido:
    no Android um app moderno ignora a CA que a pessoa instalou no sistema, e o
    app do ntfy tem a gestão de certificados DELE (desde a v1.22.1). Então o que
    a pessoa importa é este arquivo, dentro do app — e sem esta linha ninguém
    teria como saber qual arquivo é (`notifier.py` o diz na mensagem do celular).
    """
    return caddy_service.authority_file(state(CADDY) / CADDY_STORAGE)


def draw_gate() -> str:
    """Draw the gate's secret, once, and answer with it — §7b's drawing.

    **It is the deploy's act and it moved here with the rest of §7** (item 27):
    §7b says AT draws a secret per installation, and the installation is the
    environment's, which is the deploy tool's. The FILE it writes is still the
    Caddy's own — `App/caddy/gate`, beside the Caddyfile that is its only writer
    — and both artifacts read it: `at-cli` refuses the identity that arrives
    without it, and the WebApp's check is what turns the M2M into a door.

    **A secret already drawn is not drawn again**, and that is the whole of the
    function: rotating it would take the running Caddy and the running WebApp
    apart — the first would attach a value the second no longer takes, and every
    identity would be refused (`webapp.gate_refused`) until both were restarted
    from the same file. Whoever wants a new secret removes this one and brings
    the environment up again, which is the same act as changing it, said out
    loud.

    It is the CALLER that decides when — `up` draws it at installation, which is
    the moment §7b names — because a file written on import would be a secret in
    the folder of whoever never asked for one.
    """
    held = caddy_service.gate_secret()
    if held is not None:
        return held
    drawn = secrets.token_urlsafe(caddy_service.GATE_BYTES)
    files.atomic_write_text(caddy_service.gate_file(), f"{drawn}\n")
    return drawn


def _drawn(service: str, name: str) -> str:
    """A secret drawn once and kept, in the service's own state folder.

    The same rule `caddy.draw_gate` follows and for the same reason: a value a
    service signs or proves with has to outlive the container, and one drawn per
    start would take everything it had issued down with it. Whoever wants a new
    one removes the file and brings the environment up again.
    """
    where = state(service) / name
    try:
        held = where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        held = ""
    if held:
        return held
    drawn = secrets.token_urlsafe(SECRET_BYTES)
    files.atomic_write_text(where, f"{drawn}\n")
    return drawn


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

    Each secret is drawn once and kept beside this file (`_drawn`), because they
    belong to the installation and not to a start: one drawn per start would
    drop every session on the floor and make every record it had written
    unreadable. The notifier's file lives in the state folder, which is the
    folder the backup covers (§3), so a notice survives a copied folder.

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
    session = _drawn(IDENTITY, IDENTITY_SESSION)
    encryption = _drawn(IDENTITY, IDENTITY_ENCRYPTION)
    signature = _drawn(IDENTITY, IDENTITY_JWT)
    site = site_host()
    lines = [
        f"# {tr('services.identity-provider.file.header')}",
        "---",
        "theme: auto",
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


def notifier_url() -> str:
    """Where the notifier is reached — and it is read by the two things that use it.

    The `Port` below publishes here and the configuration listens here, so it is
    a function for that reason: the ONE place that decides the address is the
    same one the container publishes on, and the delivery POSTs to it
    (`services/notifier.py`).

    **Ele NÃO é o endereço que a pessoa digita**, e desde que o notificador tem
    nome os dois se separaram de propósito (`notifier_public_url`): AT fala com
    o serviço no laço, onde um alerta não depende do DNS interno, da borda nem
    do certificado do AT — se qualquer um dos três cair, o alerta ainda sai. O
    que a PESSOA e o celular usam é o nome.
    """
    return f"http://{LOOP}:{NOTIFIER_PORT}"


def notifier_public_url() -> str:
    """Where a PERSON and the phone reach the notifier — its own name, at the edge.

    §7f's two ends are AT and the phone, and they reach the service by different
    roads on purpose. This is the phone's: the name `ntfy.at.local` resolved by
    the environment's DNS, at the port the edge publishes, with the certificate
    the edge serves it under. It is what ntfy hands back inside every
    notification it delivers — a link that leads nowhere is worse than no link —
    and it is what `services phone` tells the person to point the app at.
    """
    return caddy_service.address(notifier_host(), PORT)


def _notifier_conf() -> str:
    """ntfy's configuration — §7f's notifier, declared by AT.

    Three things are decided here and nothing else. **Where the memory lives**:
    the cache, the attachments and the auth database are all pointed at the one
    folder the container mounts, which is what makes the topics — and what was
    sent to them — come back with a copied folder. **Where it listens**: the
    port AT publishes, which is the port the `Port` and this line agree on.
    And **where it is**: the URL it hands back, which is its own NAME at the
    edge and not the loop (`notifier_public_url`) — a link inside an alert is
    read by the phone, and a loop is a place no phone is. The loop stays the
    address AT POSTS to, which is the other half of the same decision.

    **`behind-proxy` is ON, and it is not a preference**: the edge stands in
    front of this service, and without the flag ntfy reads every request as
    coming from the edge's own address — one visitor bucket for everybody, which
    is what ntfy's own documentation calls out as the thing the flag is for.

    **Authentication is ON, and the door is shut to whoever brings no token.**
    `auth-default-access: deny-all` is ntfy's own advice for a private instance,
    and it is the posture §6 declares for this service: AT publishes, the phone
    reads, and each of them carries the token its own scope allows. The database
    is born empty and lives inside the mounted folder; a notifier nobody has
    written a token into answers nobody, which is the honest state of installed
    and not yet configured. **A borda na frente não muda isso**: ela não
    pergunta nada (o `forward_auth` não o nomeia), então quem chega continua
    batendo na ACL por tópico — o token é a porta, e ela é a mesma.
    """
    return "\n".join([
        f"# {tr('services.notifier.file.header')}",
        f"base-url: {_quoted(notifier_public_url())}",
        f"listen-http: {_quoted(f':{NOTIFIER_PORT}')}",
        f"cache-file: {_quoted(f'{NOTIFIER_DATA}/cache.db')}",
        f"attachment-cache-dir: {_quoted(f'{NOTIFIER_DATA}/attachments')}",
        f"auth-file: {_quoted(f'{NOTIFIER_DATA}/{NOTIFIER_AUTH}')}",
        "behind-proxy: true",
        'auth-default-access: "deny-all"',
    ]) + "\n"


@dataclass(frozen=True)
class Service:
    """A service of the environment: its image at the pin, and how it runs.

    `writes` is what AT puts in the service's state folder before it starts —
    a name and the writer that produces the text, one pair per file — and every
    writer is the service's own, because what a service reads is the service's
    business and not the orchestration's.

    `command` is what the container RUNS after its image, and `None` means the
    image's own entrypoint — which is most of them. Two are not. §7c's WebApp is
    one: its image is a base with nothing of AT's in it, so what it runs is the
    artifact the folder carries (`binary`). And §7f's notifier is the other, for
    the opposite reason: its image carries an entrypoint and **no `CMD`**, so
    what it would run with nothing written here is nothing at all. It is a
    callable for the same reason `writes` is: it reads where the folder is, and
    where the folder is is resolved at RUN time and not when this file was
    imported.
    """

    name: str
    label: str
    image: Image
    # A tuple, or a callable that answers one when the environment comes up —
    # the SITE's is the second, and `ports_of` is the one reader that knows.
    ports: Callable[[], tuple[Port, ...]] | tuple[Port, ...] = ()
    mounts: tuple[Mount | Mirror, ...] = ()
    command: Callable[[], tuple[str, ...]] | None = None
    # What the service is TOLD about the environment it is part of — the
    # environment's own words, handed to the container as its variables. A
    # container cannot see the host's loop, so a service that has to reach
    # another one is told the name to use instead of guessing (§7c's WebApp and
    # its gate). It is a callable for the same reason `ports` is, where a value
    # is not a word but a path: what one of them names is the folder.
    env: Callable[[], tuple[tuple[str, str], ...]] | tuple[tuple[str, str], ...] = ()
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

# The manifest of pinned images: §7a's first services, §7b's gate, §7c's WebApp
# and §7f's notifier. Every pin is the registry's own index for that version —
# the digest covers every platform the image is published for, and the runtime
# picks the one this machine is. Moving a pin is a release's act, and it moves
# forward (§3).
SERVICES: tuple[Service, ...] = (
    Service(
        name="dnsmasq",
        label="services.dnsmasq.name",
        image=Image(
            repo="docker.io/dockurr/dnsmasq",
            version="2.93",
            digest="sha256:b40fbaa3a9c3742d5943a4bec789dabc6c5c932b2db76a4e052c84f0b8d173a2",
        ),
        ports=_dnsmasq_ports,
        mounts=(Mount(DNSMASQ_CONFIG),),
        writes=(("dnsmasq.conf", _dnsmasq_conf),),
        # The one service of the environment that talks to nobody: it answers,
        # and what it asks of the environment is nothing. That is why it is the
        # one service alone on `DMZ` — and why nothing else is.
        network=DMZ,
    ),
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
        mounts=(Mount(IDENTITY_CONFIG), Mount(IDENTITY_DATA, host="data")),
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
        mounts=(Mirror(),),
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
        # The DNS's `53` is the other one, and it leaves the loop for the other
        # half of the same reason — the names it answers exist nowhere else
        # (`_dnsmasq_ports`). Everything else of the environment is on the loop
        # or on nothing at all.
        ports=_caddy_ports,
        mounts=(Mount(CADDY_CONFIG), Mount(CADDY_DATA, host=CADDY_STORAGE)),
        writes=(("Caddyfile", _caddy_conf),),
    ),
    # §7f's notifier, and it comes up LAST: nothing the environment fronts
    # depends on it — no edge proxies to it and no gate asks it anything — and
    # §7f is the last step of §7, the cherry on the cake in the step's own
    # words. It is also the ONE service that is not behind the gate, and that is
    # measured and not a preference (the module docstring).
    Service(
        name=NOTIFIER,
        label=f"services.{NOTIFIER}.name",
        image=Image(
            repo="docker.io/binwiederhier/ntfy",
            version="v2.28",
            digest="sha256:6ef4b819f722fccdc036af611c4774cfdc2de821ab74fdd48bbf4c9d6f8973da",
        ),
        ports=(Port(NOTIFIER_PORT),),
        mounts=(Mount(NOTIFIER_CONFIG), Mount(NOTIFIER_DATA, host="data")),
        command=_notifier_command,
        writes=((NOTIFIER_YAML, _notifier_conf),),
    ),
)


# --------------------------------------------------------------- the state ---

def state(name: str) -> Path:
    """`App/services/<serviço>/` — where that service's state lives (§7)."""
    return paths.services_dir() / name


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

    `ports` is a tuple for every service but two, and the exceptions are the
    SITE's and the DNS's: what address each of them publishes on is §7e's, and
    §7e is measured when the environment comes up — the machine's address on the
    private network, or the loop. A value read at import would be a value that
    stopped being true the moment the person joined a network. It is a callable
    for the same reason `command` and `writes` are.
    """
    return service.ports() if callable(service.ports) else service.ports


def env_of(service: Service) -> tuple[tuple[str, str], ...]:
    """The variables a service is handed, resolved NOW — the same shape, the same
    reason (`ports_of`): what one of them names is the folder."""
    return service.env() if callable(service.env) else service.env


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


def run_argv(service: Service, image: Image) -> list[str]:
    """The `podman run` that IS the service: every decision about it, in one list.

    Detached, named, labeled, on its network, publishing what it declares and
    mounting what it mounts — and then the image at the pin, and the command
    when the service has one. There is no restart policy on purpose: §3 says AT
    has no watchdog and does not propose to have one, and a container that comes
    back on its own is one.
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
        argv += ["--volume", mount.volume(state(service.name))]
    for key, value in env_of(service):
        argv += ["--env", f"{key}={value}"]
    argv.append(image.reference())
    if service.command is not None:
        argv += list(service.command())
    return argv


def _prepare(service: Service) -> Path:
    """The service's state folder, ready: the folders it mounts, and its files.

    The files go in the order the manifest declares them, which is the order a
    writer that reads what another one wrote depends on — and each writer is the
    service's own (§ `Service.writes`), so nothing here knows what a Caddyfile
    or an Authelia configuration is.
    """
    where = state(service.name)
    where.mkdir(parents=True, exist_ok=True)
    for mount in service.mounts:
        # Only the service's OWN folders are born here: a `Mirror` mounts the
        # Working Folder, which exists — creating it would be AT writing in
        # the person's folder for no reason.
        if isinstance(mount, Mount) and mount.host:
            (where / mount.host).mkdir(parents=True, exist_ok=True)
    for name, body in service.writes:
        files.atomic_write_text(where / name, body())
    return where


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
    the notifier's password follows (`services/notifier.py`) and for the same
    reason: an argv is a `ps` on this machine. A status comes back as a number;
    everything else — no network, no image, a container that did not come up — is
    `None`, which is the honest "could not tell" and never an invented refusal.

    It has the shape `core/gate.Answer`, so whoever asks through the gate's seam
    hands it over as the transport.
    """
    asked = podman.run(
        ["run", "--rm", "-i",
         "--network", NETWORK,
         "--entrypoint", "curl", _service(CADDY).image.reference(),
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
         "--entrypoint", "curl", _service(CADDY).image.reference(),
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


def _start(service: Service, pins: dict[str, dict]) -> bool:
    """Put one service on its feet. `False` when it did not get there."""
    name = tr(service.label)
    where = _prepare(service)

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
    if podman.run(run_argv(service, image)).returncode != 0:
        print(tr("services.up.failed", service=name, image=image.shown()))
        return False

    _record(service, image)
    print(tr("services.up.service", service=name, image=image.shown(),
             where=where))
    return True


def up(ask: Ask | None = None) -> str:
    """Bring the environment up — or offer the two ways out (§7a).

    The absence of the Podman is not a dry refusal: AT says the two ways out
    and takes neither, because neither is his to take. Installing is an act of
    the person's machine, and the hosted path is a decision about how this
    folder is used — both are the person's, and with no terminal to ask in
    neither is taken (§3: the fail-closed posture).

    **The machine's permission comes first, and it is the same posture**: the
    low-port rule is asked about before a secret is drawn or a container named, so
    that a refusal is a folder nobody touched (`elevate`, §3's Privilege).

    The environment is not the SWITCH, and it does not pretend to be one: a
    service that does not come up is said, and what did come up stays up for
    whoever wants to look. The switch — paths.md's transactional change from one
    path to the other, with Forms on until the gate is proved — is
    `at_deploy/switch.py`'s, and it is the one that rolls back; this is what it
    calls, and what a person who asks for the environment directly gets.

    **§7f's credential is created here, and its failure is not this function's.**
    With the notifier standing, AT makes its own credential in it — the account
    and the topic scope of §3, and the token the delivery carries
    (`services/notifier.py`). It runs after every service, because what it
    creates lives in the database the notifier's server writes when it starts and
    nothing can be created before that. And an environment whose services stood
    IS up: what a credential that did not get made costs is the delivery, which
    has its own door (`at-deploy services notify`) and its own line in `status` —
    rolling the containers back over it would be undoing the environment the
    person asked for in the name of the cherry on the cake.
    """
    if not podman.present():
        return ways_out(ask)

    # §3 (Privilege): the environment inevitably demands elevation somewhere, and
    # §7a's DNS port is where. It is asked BEFORE anything is drawn or started, so
    # that a refusal leaves the folder exactly where it was.
    refusal = elevate(ask)
    if refusal is not None:
        return refusal

    # §7b: the gate's secret is drawn at INSTALLATION — here, once — and kept in
    # the folder from then on. It is drawn before anything starts because the
    # Caddyfile is written by the service's own writer, and a Caddy that came up
    # without the line would be an edge that attaches nothing and a WebApp that
    # refuses every identity it is handed.
    fresh = caddy_service.gate_secret() is None
    draw_gate()
    if fresh:
        print(tr("services.gate.drawn", where=caddy_service.gate_file()))

    pins = held()
    _networks()
    for service in SERVICES:
        if not _start(service, pins):
            return FAILED

    # §7f's delivery: the notifier is standing, so AT can make its own
    # credential inside it. The import is inside the function because the
    # delivery reads THIS module for the address it posts to and the folder the
    # credential lives in — the two are one subject, like `switch` and this file.
    from at_deploy import notifier  # noqa: PLC0415 — see above

    notifier.provision()
    return UP


def _service(name: str) -> Service | None:
    """A service of the manifest by its name, or `None` — the manifest is the list."""
    return next((service for service in SERVICES if service.name == name), None)


def restart(name: str) -> bool:
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

    **The session secret is not re-drawn, and that is what makes this cheap.**
    It is drawn once and kept (`_drawn`), and it is what seals the session
    cookie: the same value across a restart keeps every session that was open,
    and the registry those sessions live in is the folder's (`IDENTITY_DATA`).
    §3 declares that price where the operator's act is recorded, because it is
    the one thing a person changing a credential has to know.
    """
    service = _service(name)
    if service is None or not podman.present():
        return False
    if _state_of(service) == ABSENT:
        return False

    where = _prepare(service)
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
    if podman.run(run_argv(service, image)).returncode != 0:
        print(tr("services.up.failed", service=tr(service.label),
                 image=image.shown()))
        return False

    print(tr("services.restarted", service=tr(service.label), where=where))
    return True


def set_credential(name: str, credential: str) -> str:
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
    if not restart(IDENTITY):
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

    The credential's import is inside the function because `notifier` reads THIS
    module — the two are one subject.

    §7f's credentials close the report, and each line closes with the FILE and
    never with the value: AT's token is a secret and the phone's is printed
    once, at the moment it is drawn (`at_deploy/notifier.py`), and what a
    person needs from this report is that each one exists and where it lives.
    """
    from at_deploy import notifier  # noqa: PLC0415 — it reads this module

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
    # NOME**, e desde que o site é `at.local` os dois não são a mesma coisa: o
    # nome só resolve numa máquina que use o DNS do ambiente, e o endereço onde
    # a borda publica é desta máquina sempre (§7e). Perguntar pelo nome diria
    # "não há nada" sobre uma borda de pé, e a linha que a pessoa mais precisa
    # ler é justamente a URL.
    served = published(vpn.address() or LOOP, PORT)
    if served:
        print(tr("services.status.site",
                 url=caddy_service.address(site_host(), PORT)))

    # The services are a TABLE — always, and that is the point. Five lines of
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

    # The notifier's credentials are said WITH the notifier, and only then: they
    # are facts about a service that is up, and listing where a credential would
    # live for a notifier nobody brought is a report about a thing that is not
    # there.
    served = _service(NOTIFIER)
    if served is None or _state_of(served) != RUNNING:
        return
    where = notifier.token_file()
    print(tr("services.notifier.credential.at", where=where, topic=notifier.TOPIC,
             scope=notifier.SCOPE)
          if notifier.token() is not None
          else tr("services.notifier.credential.absent", where=where))

    phone = notifier.phone_file()
    print(tr("services.notifier.phone.at", where=phone, topic=notifier.TOPIC,
             scope=notifier.PHONE_SCOPE)
          if notifier.phone_token() is not None
          else tr("services.notifier.phone.absent", where=phone))


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
