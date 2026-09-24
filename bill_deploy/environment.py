"""The container environment (§7a): the pinned images, the services, and the switch.

§7a is one switch and one rule. The switch: the person needs Podman, Bill checks
whether it exists, and if it does not it offers the two ways out — install it, or
continue on the hosted path. **Bill does not install it**, because installing a
package is an act of the person's machine and §3 spends elevation only on an
explicit request. The rule: from there on Bill orchestrates the environment and
the services, which come up as containers **from pinned images** (§3, Dependência
externa).

**The manifest is this file's table, and the folder has its own pin.** `SERVICES`
is what the binary carries: the services of §7a, each with the image it runs —
repository, version and digest. The folder records the pin it IS at in
`App/services/images.json`, and the difference between the two is §3's sentence
about updating: the pin only moves forward, and an instance AHEAD of the binary's
pin warns and proceeds, because it is not downgraded. That is why the comparison
exists at all: a folder carried to a machine running an older Bill keeps running
what it has.

**Every decision about a service is one argv.** `run_argv` is the whole of what
Bill decides about a container, and it is a list: what it is called, which network
it joins, where it publishes, what it mounts, and the image at the pin. Two of
those decisions come from the retired environment, measured there and inherited
here: a host deny-list does not cover a published container port — the port goes
through DNAT and the `input` hook never sees it — so **what closes the LAN is
publishing on loopback**, never a firewall rule; and a container published on an
address the machine does not have yet comes up **running and without its port**,
so the orchestrator waits for the address to exist before it binds.

**What each service runs.** `dnsmasq` is up: its configuration is the
environment's own, the names of access (§7a's own words for it). The `caddy` is
up as the edge that publishes Bill — the same Caddyfile generator the hosted path
reads, because it is the same Caddy answering the same questions, and the ONE
thing that differs between the two paths is the storage: the folder's, or the
container's. The `identity-provider` is up as §7b's gate: Authelia, configured by
Bill to be the one that proves who is calling, with Bill standing behind it as an
app and not as an exception — and the gate secret, drawn at installation, is the
line that says the request came through it. And the `webapp` is up as §7c's
container: the WebApp, moved off the person's machine and behind the gate. And
§7f's `notifier` is up as the LAST of them: ntfy, configured by Bill to keep
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

**The WebApp's image carries nothing of Bill's, and that is the decision.** The
app's own binary — `bill`, never the `bill-deploy` that is putting the container
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
a whole rollback when any step does not close — is `bill_deploy/switch.py`'s, and it
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

from bill.core import actors, files, gate, paths, tables
from bill.core.migrations import is_yes
from bill.i18n import tr
from bill.services import caddy as caddy_service

from bill_deploy import podman, vpn

# What a person answers with, injected the way `boot` and `lang` take theirs: a
# test asks the same question without a terminal.
Ask = Callable[[str], str]

# What spends an elevation, injected the same way — and the suite MUST inject it:
# a test that ran `sudo` would be a test that asked a person for a password.
Spend = Callable[..., None]

# The outcomes of `up`, and the CLI is what turns them into an exit code.
UP = "up"                 # the environment is standing
INSTALL = "install"       # the person installs the Podman; Bill said how
HOSTED = "hosted"         # the folder stays on the hosted path, and nothing moved
NO_ANSWER = "no_answer"   # no terminal to ask in: neither way was taken
FAILED = "failed"         # a service did not come up

# The outcomes of the gate's credential change — item 27's operator act (§7b).
# The row is written in all three: what separates them is how far the change
# travelled, and the person is owed exactly that difference.
CREDENTIAL_CHANGED = "changed"   # the row, the derivation and the provider
CREDENTIAL_UNKNOWN = "unknown"   # nobody in this folder wears that name
CREDENTIAL_PENDING = "pending"   # the folder has it; the gate does not yet

# Where the site is, and it is Bill's own (§3, §6): the environment's Caddy
# publishes Bill's site, and it publishes it on the loop until the gate exists —
# exposure demands authentication, and the container path's is the gate (§7b).
HOST = "localhost"
# The alternative HTTPS port, and not 443: the Caddy is the edge and shares the
# HOST's network (it publishes the machine's own address and proxies to the
# loop), so 443 would be the host's privileged port — and §3 spends elevation
# only on an explicit request. This is what the person types.
PORT = 8443
# The WebApp behind it: on the loop, at the port Bill serves by default (§6),
# which §7c keeps even after moving it into a container — exposing moves the
# address the person reaches, never the one the WebApp listens on. The Caddy
# shares the host's network and proxies to the loop, so publishing there is what
# lets the edge reach the container too; `test_environment` holds this pair to
# the WebApp's OWN constants, so the declaration cannot drift from the thing it
# names.
WEBAPP_HOST = "127.0.0.1"
WEBAPP_PORT = 12345

# The environment's network — what the services that are not on the host's talk
# over. The Caddy is not in it: it is the edge, and what it proxies to is the
# host's own loop.
NETWORK = "bill"
HOST_NETWORK = "host"

# The prefix of every container Bill creates. A container is named for the
# service it runs, and the name is Bill's: `down` removes what the name says,
# and another Bill on this machine has other names.
PREFIX = "bill-"

# The label every container of this environment carries, for whoever reads the
# runtime by hand and wants to know whose it is.
LABEL = "bill.service"

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

# Inside the containers, where each service reads what Bill writes for it.
DNSMASQ_CONFIG = "/etc/dnsmasq.d"
CADDY_CONFIG = "/etc/caddy"
CADDY_DATA = "/data"
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
# configuration Bill generates, the people it writes for it to prove, and the
# session secret drawn once and kept — Authelia signs its cookie with it, and a
# secret drawn per start would drop every session on the floor.
IDENTITY_YAML = "configuration.yml"
IDENTITY_USERS = "users.yml"
IDENTITY_SESSION = "session"

# The WebApp as a container (§7c), and what runs inside it is THIS artifact: the
# module's docstring holds the decision, and the test is what keeps it true —
# the folder is mounted at its own path, and the command names the binary the
# person is running.
WEBAPP = "webapp"

# The variable the environment hands the WebApp so it can find its gate. A
# container has no host's loop to ask — `127.0.0.1` inside it is the WebApp's
# own — so the environment is what says which name to use, and the name is the
# provider's on the network the two share (`core/gate.py`, which reads it).
GATE_ENV = "BILL_GATE"

# §7f's notifier, and the name is the ROLE and not the brand: ntfy serves it
# today, and the day another one serves it the rest of this file does not move.
# **Its port is Bill's, and it is neither ntfy's default nor a low one.** ntfy
# listens on 80, under the kernel's low-port rule, and §3's elevation asks for
# the narrowest thing that works: the floor moves to the LOWEST port the
# environment publishes, DNS's 53 is the only one it names, and this is the same
# decision as the site's port being 8443 and not 443. What is left is the
# vendor's own other port — `:2586` is the one every example in ntfy's
# documentation uses for a listener behind a proxy — and the notifier publishes
# on the loop, where nothing fronts it.
NOTIFIER = "notifier"
NOTIFIER_PORT = 2586

# What the notifier's container sees of its own state folder: the configuration
# Bill writes, and the ONE folder where everything it REMEMBERS lives. **The
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

# The name the environment answers for. The brand is not translated (§3), and
# `.local` is the name a machine answers to on its own network.
NAME = "bill.local"

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


# ------------------------------------------------------------ the manifest ---

@dataclass(frozen=True)
class Image:
    """One image at the pin: the repository, the version and the digest.

    All three, and the version is not decoration: `.reference()` hands over
    `repo:version@digest`, so whoever reads the line knows which release it is
    while the digest is what pins it — a tag moves, a digest does not (§3).
    """

    repo: str
    version: str
    digest: str

    def reference(self) -> str:
        return f"{self.repo}:{self.version}@{self.digest}"

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
    """A port published on the host, on an address Bill names out loud.

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
        is no SELinux it is ignored. It is the state folder Bill created, so the
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
    """The artifact the WebApp container runs — `bill`, the app's own (§7c).

    The binary IS the WebApp, so a container that ran another artifact would be a
    second product — and since item 27 that distinction is the whole point: what
    runs inside is `bill`, the artifact that keeps the folder and the app, and
    never `bill-deploy`, which is the tool that put the container there.

    It is reached through the folder both of them see at the same path, and the
    artifact running is NOT the one being named: `bill-deploy` is what brings the
    container up, and what goes inside it is `bill` (item 27). Frozen, the app
    sits beside the deploy at the folder's root, which is where §3 puts the
    binary and its Windows spelling. Run from a checkout, it is `dist/bill`,
    which is where `bill.spec` puts the artifact and which is inside the folder
    too — NOT `bill/`, which is the package, and a directory is not something a
    container can execute. A folder that never built the artifact names a path
    that is not there, and that is honest: the switch is what notices, by proving
    the WebApp answers instead of believing this line.
    """
    if getattr(sys, "frozen", False):
        return str(paths.working_folder() / ("bill.exe" if sys.platform == "win32" else "bill"))
    return str(paths.working_folder() / "dist" / "bill")


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
             for port in service.ports if port.port < below}
    return tuple(sorted(ports))


def spend_elevation(*argv: str) -> None:
    """Run one command as the machine's administrator, through `sudo`.

    **The terminal is INHERITED and that is the point**: `sudo` asks for the
    password itself, and a Bill that swallowed that prompt would look like a Bill
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
    §7a's `dnsmasq` publishes DNS on `127.0.0.1:53`, and a machine that ships the
    kernel's low-port rule — every Linux does — refuses the bind to a user
    process.

    **What is asked is the NARROWEST thing that works**: the floor moves to the
    LOWEST port the environment publishes and not to zero, so the machine grants
    exactly what Bill needs and nothing below it. And what it buys is not
    permanent — a `sysctl -w` is gone at the next boot, and Bill asks again then,
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
    """The name of the container Bill runs for that service.

    It is declared here — above the manifest that uses it, and far above the
    orchestration — because it is a NAME and not a step: the service's container,
    the gateway name another service reaches it by (§7c's `GATE_ENV`) and what
    `down` removes are the same word said once.
    """
    return f"{PREFIX}{name}"


def _webapp_command() -> tuple[str, ...]:
    """What §7c's container runs: the artifact, serving the WebApp on the loop.

    The port is the WebApp's own default, and it is the one the `Port` above
    publishes and the Caddyfile proxies to — the three are the same number, and
    `test_environment` is what holds them together.
    """
    return (binary(), "webapp", "--port", str(WEBAPP_PORT))


def _notifier_command() -> tuple[str, ...]:
    """What §7f's container runs — and it is MEASURED, not read off the image.

    The image's entrypoint is `ntfy` and it carries **no `CMD` at all**: run with
    nothing after the image, it prints its own help and exits, which is a
    notifier that never comes up and a `bill-deploy services status` that says so
    forever. So the subcommand is a decision of Bill's, written where every other
    decision about a container is. It is a callable like the WebApp's even though
    it resolves nothing, because `Service.command` has one shape.
    """
    return ("serve",)


def site_host() -> str:
    """The name the environment's edge serves — the private network's, or the loop's.

    §7e is what this reads, and it is asked of the manifest's own machine and not
    of a setting: when the machine is on a private network, the network answers
    for a NAME (`vpn.name`), and that name is what the Caddy is issued a
    certificate for and what the person types. With no network the site is
    `HOST`, the loop — which is the supported state and not a degraded one.

    **It is a function and not a constant because it is measured at the moment
    the environment comes up**, and every file that has to agree on it is written
    then: the Caddyfile, the identity provider's access rule and its cookie, and
    the URL the switch says. A name read once at import would be a name that
    stopped being true the moment the person joined a network.
    """
    return vpn.name() or HOST


def _dnsmasq_conf() -> str:
    """The names the environment answers for, in dnsmasq's words.

    §7a gives this service one job — customizing the access URLs — and the names
    are the environment's. It answers Bill's own name for this machine,
    `bill.local`, and the ADDRESS it answers with is where the edge actually is:
    the private network's when the machine is on one (§7e), the loop otherwise.
    The name the network itself answers for needs no help from here — the
    network's own DNS already resolves it.
    """
    lines = [
        f"# {tr('services.dnsmasq.file.header')}",
        f"address=/{NAME}/{vpn.address() or LOOP}",
    ]
    return "\n".join(lines) + "\n"


def _caddy_conf() -> str:
    """The Caddyfile the container's Caddy runs.

    The same generator the hosted path reads, because it is the same Caddy: the
    site, the TLS of Bill's own certificate, the admin endpoint off and the
    storage — the one line that is a path and not a decision (§7a). The two
    lines of the gate come along when there is a secret, and §7b is what draws
    it: the Caddy asks the identity provider who is calling, and tells the
    WebApp that the request came through here.
    """
    return caddy_service.caddyfile(
        site_host(), PORT, WEBAPP_PORT,
        gate=caddy_service.gate_secret(),
        storage=CADDY_DATA,
        auth=f"{LOOP}:{IDENTITY_PORT}",
    )


def draw_gate() -> str:
    """Draw the gate's secret, once, and answer with it — §7b's drawing.

    **It is the deploy's act and it moved here with the rest of §7** (item 27):
    §7b says Bill draws a secret per installation, and the installation is the
    environment's, which is the deploy tool's. The FILE it writes is still the
    Caddy's own — `App/caddy/gate`, beside the Caddyfile that is its only writer
    — and both artifacts read it: `bill` refuses the identity that arrives
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
    """Authelia's configuration — the gate, declared by Bill (§7b).

    Three things are decided here and nothing else. The **storage** is the
    container's data folder, which is a folder of the instance mounted into it,
    so the sessions and the registrations live in the folder the backup covers
    (§3). The **access control** denies by default and names Bill's own site as
    `one_factor`: Bill comes in as one more app behind the gate, and the app not
    named is the app that does not enter. And the **session secret** is drawn by
    Bill and kept beside this file, because it belongs to the installation and
    not to the process.

    **No OIDC provider is declared, and that is a decision and not an omission.**
    §7b has Authelia speaking OIDC with whoever speaks OIDC and forward-auth
    with whoever does not; every app of §7 reaches it by forward-auth, Bill
    included, and the one that speaks OIDC is the one the person adds later.
    Authelia refuses a provider with no clients — `clients` has to name one or
    more, and `jwks` an RSA key — so a block written today would be an identity
    provider that does not start, declaring a client that does not exist. The
    provider enters with the first service that speaks OIDC, and it is that
    slice's to write.
    """
    session = _drawn(IDENTITY, IDENTITY_SESSION)
    lines = [
        f"# {tr('services.identity-provider.file.header')}",
        "---",
        "theme: auto",
        # The container's own bind, and not a publication: what leaves the
        # container is the port the runtime maps onto the loop (§7a's measured
        # rule — what closes the LAN is publishing on loopback).
        "host: 0.0.0.0",
        f"port: {IDENTITY_PORT}",
        "log:",
        "  level: info",
        "session:",
        f"  secret: {_quoted(session)}",
        "  cookies:",
        # The domain and the URL are the SITE's — the name the person is at when
        # the portal hands them the cookie (§7e: the private network's name, when
        # there is one). A cookie issued for another name is a cookie the browser
        # will not send back, and a portal that redirects elsewhere is a login
        # that lands outside the edge.
        f"    - domain: {site_host()}",
        f"      authelia_url: {caddy_service.address(site_host(), PORT)}",
        "storage:",
        "  local:",
        f"    path: {IDENTITY_DATA}/db.sqlite3",
        "authentication_backend:",
        "  file:",
        f"    path: {IDENTITY_CONFIG}/{IDENTITY_USERS}",
        "access_control:",
        "  default_policy: deny",
        "  rules:",
        f"    - domain: {site_host()}",
        "      policy: one_factor",
    ]
    return "\n".join(lines) + "\n"


def _identity_users() -> str:
    """The people of the folder, in the gate's own words (§7b).

    It is where the split §7b declares actually meets: WHO is an actor belongs
    to Bill — the row of `actor`, with the role the ceiling is read from — and
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

    The configuration hands it back inside every notification it delivers, and
    the delivery POSTs to it (`services/notifier.py`), so it is a function with
    one body for that reason as well: the ONE place that decides the address is
    the same one the `Port` below publishes on, and a `base-url` naming another
    address would put a link leading nowhere inside every alert.
    """
    return f"http://{LOOP}:{NOTIFIER_PORT}"


def _notifier_conf() -> str:
    """ntfy's configuration — §7f's notifier, declared by Bill.

    Three things are decided here and nothing else. **Where the memory lives**:
    the cache, the attachments and the auth database are all pointed at the one
    folder the container mounts, which is what makes the topics — and what was
    sent to them — come back with a copied folder. **Where it listens**: the
    port Bill publishes, which is the port the `Port` and this line agree on.
    And **where it is**: the URL it hands back, which is the loop, because no
    edge fronts this service (the module docstring holds the measurement).

    **Authentication is ON, and the door is shut to whoever brings no token.**
    `auth-default-access: deny-all` is ntfy's own advice for a private instance,
    and it is the posture §6 declares for this service: Bill publishes, the phone
    reads, and each of them carries the token its own scope allows. The database
    is born empty and lives inside the mounted folder; a notifier nobody has
    written a token into answers nobody, which is the honest state of installed
    and not yet configured.
    """
    return "\n".join([
        f"# {tr('services.notifier.file.header')}",
        f"base-url: {_quoted(notifier_url())}",
        f"listen-http: {_quoted(f':{NOTIFIER_PORT}')}",
        f"cache-file: {_quoted(f'{NOTIFIER_DATA}/cache.db')}",
        f"attachment-cache-dir: {_quoted(f'{NOTIFIER_DATA}/attachments')}",
        f"auth-file: {_quoted(f'{NOTIFIER_DATA}/{NOTIFIER_AUTH}')}",
        'auth-default-access: "deny-all"',
    ]) + "\n"


@dataclass(frozen=True)
class Service:
    """A service of the environment: its image at the pin, and how it runs.

    `writes` is what Bill puts in the service's state folder before it starts —
    a name and the writer that produces the text, one pair per file — and every
    writer is the service's own, because what a service reads is the service's
    business and not the orchestration's.

    `command` is what the container RUNS after its image, and `None` means the
    image's own entrypoint — which is most of them. Two are not. §7c's WebApp is
    one: its image is a base with nothing of Bill's in it, so what it runs is the
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
    ports: tuple[Port, ...] = ()
    mounts: tuple[Mount | Mirror, ...] = ()
    command: Callable[[], tuple[str, ...]] | None = None
    # What the service is TOLD about the environment it is part of — the
    # environment's own words, handed to the container as its variables. A
    # container cannot see the host's loop, so a service that has to reach
    # another one is told the name to use instead of guessing (§7c's WebApp and
    # its gate).
    env: tuple[tuple[str, str], ...] = ()
    writes: tuple[tuple[str, Callable[[], str]], ...] = ()
    network: str = NETWORK


# The base the artifact runs on. It carries nothing of Bill's — no source, no
# payload, no configuration: the Working Folder is mounted, and the container's
# whole reach is that mount. **The base has to be one the artifact RUNS on**, and
# that is not a preference: a frozen binary links against the glibc of the
# machine that built it, and MEASURED, the artifact built in this folder needs
# `GLIBC_2.44` while `debian:13` carries `2.41` — the container dies on
# `libm.so.6: version GLIBC_2.44 not found` before Bill ever starts. A rolling
# distribution is what names the same floor here, and its `latest` is the
# vendor's own word: the DIGEST is what pins it, exactly like the Caddy's pin
# (§3), and moving it is a release act.
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
        ports=(Port(53, "udp"), Port(53)),
        mounts=(Mount(DNSMASQ_CONFIG),),
        writes=(("dnsmasq.conf", _dnsmasq_conf),),
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
        ports=(Port(IDENTITY_PORT),),
        mounts=(Mount(IDENTITY_CONFIG), Mount(IDENTITY_DATA, host="data")),
        writes=((IDENTITY_YAML, _identity_conf), (IDENTITY_USERS, _identity_users)),
    ),
    # §7c's WebApp, and it comes up after the gate and before the edge: the gate
    # is what stands in front of it, and the edge is what proxies to it.
    Service(
        name=WEBAPP,
        label=f"services.{WEBAPP}.name",
        image=WEBAPP_IMAGE,
        ports=(Port(WEBAPP_PORT),),
        mounts=(Mirror(),),
        command=_webapp_command,
        # The gate, reached the only way a container can reach it: by the name
        # the environment gave the provider, on the network the two share. The
        # host's loop is not visible from here, and `127.0.0.1` inside this
        # container is this container (`gate.GATE_ENV`).
        env=((GATE_ENV, f"{container(IDENTITY)}:{IDENTITY_PORT}"),),
    ),
    Service(
        name="caddy",
        label="services.caddy.name",
        image=Image(
            repo="docker.io/library/caddy",
            version="2.11.4",
            digest="sha256:0c994536bddb66445885237f1a5dcc1916bccea922661c76b4e9fc24061f9b52",
        ),
        # No published port: the Caddy is the edge, it shares the host's network
        # and binds Bill's own address itself (the site's port). What it proxies
        # to is the loop, which a container on a network of its own cannot see.
        mounts=(Mount(CADDY_CONFIG), Mount(CADDY_DATA, host="storage")),
        writes=(("Caddyfile", _caddy_conf),),
        network=HOST_NETWORK,
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

def addresses(service: Service) -> tuple[str, ...]:
    """The host addresses this service publishes on, in the order declared."""
    return tuple(dict.fromkeys(port.address for port in service.ports))


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
    when the service has one. There is no restart policy on purpose: §3 says Bill
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
    for port in service.ports:
        argv += ["--publish", port.published()]
    for mount in service.mounts:
        argv += ["--volume", mount.volume(state(service.name))]
    for key, value in service.env:
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
        # Working Folder, which exists — creating it would be Bill writing in
        # the person's folder for no reason.
        if isinstance(mount, Mount) and mount.host:
            (where / mount.host).mkdir(parents=True, exist_ok=True)
    for name, body in service.writes:
        files.atomic_write_text(where / name, body())
    return where


def _network() -> None:
    """The environment's network, created if this machine does not have it."""
    if not podman.ok(["network", "exists", NETWORK]):
        podman.run(["network", "create", NETWORK])


def _state_of(service: Service) -> str:
    """Whether the service's container is running, stopped, or never was."""
    answer = podman.run([
        "container", "inspect", "--format", "{{.State.Running}}",
        container(service.name),
    ])
    if answer.returncode != 0:
        return ABSENT
    return RUNNING if answer.stdout.strip() == "true" else STOPPED


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
        print(tr("services.up.failed", service=name, reference=image.reference()))
        return False

    for address in addresses(service):
        if not address_ready(address):
            print(tr("services.up.waiting", service=name, address=address))
        if not wait_for(address):
            print(tr("services.up.no_address", service=name, address=address))
            return False

    # Whatever carries that name is Bill's and is about to be replaced: the name
    # is the service, and two containers cannot share one.
    podman.run(["rm", "--force", container(service.name)])
    if podman.run(run_argv(service, image)).returncode != 0:
        print(tr("services.up.failed", service=name, reference=image.reference()))
        return False

    _record(service, image)
    print(tr("services.up.service", service=name, reference=image.reference(),
             where=where))
    return True


def up(ask: Ask | None = None) -> str:
    """Bring the environment up — or offer the two ways out (§7a).

    The absence of the Podman is not a dry refusal: Bill says the two ways out
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
    `bill_deploy/switch.py`'s, and it is the one that rolls back; this is what it
    calls, and what a person who asks for the environment directly gets.

    **§7f's credential is created here, and its failure is not this function's.**
    With the notifier standing, Bill makes its own credential in it — the account
    and the topic scope of §3, and the token the delivery carries
    (`services/notifier.py`). It runs after every service, because what it
    creates lives in the database the notifier's server writes when it starts and
    nothing can be created before that. And an environment whose services stood
    IS up: what a credential that did not get made costs is the delivery, which
    has its own door (`bill-deploy services notify`) and its own line in `status` —
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
    _network()
    for service in SERVICES:
        if not _start(service, pins):
            return FAILED

    # §7f's delivery: the notifier is standing, so Bill can make its own
    # credential inside it. The import is inside the function because the
    # delivery reads THIS module for the address it posts to and the folder the
    # credential lives in — the two are one subject, like `switch` and this file.
    from bill_deploy import notifier  # noqa: PLC0415 — see above

    notifier.provision()
    return UP


def _service(name: str) -> Service | None:
    """A service of the manifest by its name, or `None` — the manifest is the list."""
    return next((service for service in SERVICES if service.name == name), None)


def restart(name: str) -> bool:
    """Put one service's container up again, with the files Bill writes for it.

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
                 reference=image.reference()))
        return False

    print(tr("services.restarted", service=tr(service.label), where=where))
    return True


def set_credential(name: str, credential: str) -> str:
    """Give a person the credential the gate proves — the operator's act (§7b).

    Item 27's second operator act, and the three things it is are one sentence:
    **who** is an actor belongs to Bill, the row carries the credential, and the
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

    A yes installs it: Bill says how, and stops there — it does not install
    anything, because that is the person's machine and §3 spends elevation only
    on an explicit request. Anything else keeps the folder where it already
    works, on the hosted path (§6), which needs nothing beyond the binary.

    **A folder already on the container path gets a different question**, and it
    is the switch that asks it: for that folder "continue on the hosted path" is
    not nothing — the Forms is off, and Bill is closed — so the second way out is
    restoring it, which moves the record. The import is inside the function
    because `switch` reads this module.
    """
    from bill_deploy import switch  # noqa: PLC0415 — switch imports this module

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
    """Take the environment down: Bill's containers and its network.

    The FOLDER stays exactly where it is — what comes down is what Bill started,
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
    podman.run(["network", "rm", NETWORK])
    if say:
        print(tr("services.down.done", where=paths.services_dir()))


def status() -> None:
    """What is standing: the path this folder is on, and each service.

    The PATH comes first, and it is said even where there is no Podman at all:
    which authenticator this folder is on is a fact the folder carries
    (`gate.mode`, the app's own reader of the same record), and it is the one
    line that tells a person whether the environment is supposed to be standing.
    The credential's import is inside the function because `notifier` reads THIS
    module — the two are one subject.

    §7f's credentials close the report, and each line closes with the FILE and
    never with the value: Bill's token is a secret and the phone's is printed
    once, at the moment it is drawn (`bill_deploy/notifier.py`), and what a
    person needs from this report is that each one exists and where it lives.
    """
    from bill_deploy import notifier  # noqa: PLC0415 — it reads this module

    print(tr("services.status.mode", mode=tr(f"services.mode.{gate.mode()}")))
    # Where the environment is reached from OUTSIDE this machine (§7e), and it is
    # said only when there is such a place: a loopback Bill has no second address
    # to announce, and announcing the loop would be naming the machine the person
    # is already sitting at.
    if site_host() != HOST:
        print(tr("services.status.site",
                 url=caddy_service.address(site_host(), PORT)))
    if not podman.present():
        print(tr("services.no_podman.status"))
        return
    pins = held()
    for service in SERVICES:
        image = running(service, pins)
        print(tr(
            "services.status.line",
            service=tr(service.label),
            state=tr(f"services.status.{_state_of(service)}"),
            reference=image.reference(),
        ))

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
    reads it as one answer (`bill_deploy/wizard.py`): the step of §7a closed when
    the environment is standing, and not when the command happened to exit `0`.
    """
    if not podman.present():
        return False
    return all(_state_of(service) == RUNNING for service in SERVICES)
