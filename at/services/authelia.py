"""The Authelia the binary carries — the portal of the hosted path's own gate.

**TASK-177 (02/10/2026): the hosted path gains a portão PRÓPRIO.** §6 used to call
exposing the hosted path with an Authelia in front of it "modo avançado, não
suportado" — the gate was the container path's alone (§7b). The revision keeps
that sentence true for CONTAINMENT and makes it false for the GATE itself:
Authelia and ntfy travel vendorized inside `at-cli`, exactly like the Caddy
already does (`services/caddy.py`), and come up as subprocesses of this same
process tree — no Podman, no second artifact, no systemd unit. `at-cli webapp`
is the one trigger all three already answer to, by default — `--no-caddy`
turns it, and this module's unpacking and starting, off. The price, declared:
no container means no isolamento por raio de explosão (`paths.md`), which is
why the level this buys is `A` and never `S`.

**The payload is the vendor's tarball, byte for byte** — the same rule
`caddy.py` and `gitleaks.py` already answer, and the same reason: `at/vendor/
authelia/` carries the release named exactly as the vendor names it
(`authelia-v4.39.28-linux-amd64.tar.gz`, dashes and the `v` included, because
Authelia's own goreleaser spells it that way and not the way Caddy's does).
Linux only, for now (§9): Authelia itself ships no darwin or windows asset.

**No Redis, and it is a decision and not an omission.** Authelia keeps its
session registry in MEMORY on both paths (`at_deploy/environment.py`'s own
`_identity_conf` pays the same price, TASK-184) — neither carries a second
process to keep that registry alive across a restart. A bundle Authelia that
restarts drops its sessions, and the person logs in again.

**The secret is drawn once and kept in PLAINTEXT, beside this folder's own
binary.** This is the Caddy's own rule (`caddy.gate_file`) and not the
container environment's (`at_deploy/environment.py`'s item-50 sealing): that
sealing exists because the environment's state folder is COPIED into a
container's mount with no encryption of its own, and the Chave Principal is
what makes the copy safe. Nothing here is copied into a container — the
secrets live in `App/services/authelia/`, inside the Working Folder the backup already
covers, on the one machine that ever reads them. A plaintext file in `App/` is
exactly the trust Caddy's own gate secret already carries.

**The users file is the SAME derivation Forms and Basic already prove.**
`at.core.actors.people()` carries the row's `credential` field, which is never
a password — it is `nacl.pwhash.str`'s own crypt string (`encryption/
password.py`), and Authelia's file backend reads that exact format with no
conversion (measured against the real binary: `validate-config` and a live
`forward-auth` both accept it). An actor with no credential is not in the
file, the same filter `_identity_users` already applies.
"""

from __future__ import annotations

import os
import secrets as _secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from platform import machine

from at.core import actors, files, paths, tables
from at.i18n import tr
from at.services import caddy

# Where the payload travels: `at/vendor/authelia/`.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "authelia"

# `App/services/authelia/` — the instance folder, the Caddy's own arithmetic.
FOLDER = "authelia"

BINARY = "authelia"
STAMP = "platform"
CONFIG = "configuration.yml"
USERS = "users.yml"
ASSETS = "assets"
DB = "db.sqlite3"
NOTIFICATIONS = "notifications.txt"

# The three secrets the provider needs beyond the users it already proves —
# the session cookie's signature, the storage's own encryption, and what it
# signs an identity-validation token with. Each is drawn once and kept.
SESSION_SECRET = "session"
ENCRYPTION_SECRET = "encryption"
JWT_SECRET = "jwt"

LOOPBACK = "127.0.0.1"
SECRET_BYTES = 32

# Authelia ships no darwin or windows release (measured against the vendor's
# own `releases/latest`), so the pair is narrower than the Caddy's own —
# naming only what the vendor actually builds, and not what AT wishes it did.
SYSTEMS = {"linux": "linux"}
MACHINES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class AutheliaError(Exception):
    """The artifact carries no usable Authelia for this platform."""


def platform_name() -> str | None:
    """The vendor's word for this platform — `linux-amd64`, dashed like the
    vendor's own release names it, and not underscored like the Caddy's."""
    system = SYSTEMS.get(sys.platform)
    found = MACHINES.get(_machine())
    if system is None or found is None:
        return None
    return f"{system}-{found}"


def _machine() -> str:
    return machine().lower()


def label() -> str:
    """What to call this platform when it has no Authelia."""
    return f"{sys.platform}/{machine()}"


def payload() -> Path | None:
    """The vendor's tarball for this platform, or `None` when there is none."""
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"authelia-v*-{name}.tar.gz"))
    if len(found) != 1:
        return None
    return found[0]


def directory() -> Path:
    """`App/services/authelia/` — where everything this file writes lives."""
    return paths.service_dir(FOLDER)


def binary() -> Path:
    return directory() / BINARY


def stamp_file() -> Path:
    return directory() / STAMP


def unpacked() -> bool:
    """Whether the folder already carries the Authelia this platform runs."""
    if not binary().is_file() or not stamp_file().is_file():
        return False
    return stamp_file().read_text(encoding="utf-8").strip() == platform_name()


def ensure() -> Path | None:
    """Unpack the Authelia into the instance folder; `None` without a payload.

    The vendor's tarball holds the binary at its root — unlike ntfy's, which
    nests it inside a folder named after the release — so the extraction is
    the Caddy's own arithmetic, unchanged.
    """
    if unpacked():
        return binary()

    source = payload()
    if source is None:
        return None

    where = directory()
    where.mkdir(parents=True, exist_ok=True)
    destination = binary()

    with tarfile.open(source, "r:gz") as archive:
        try:
            packed = archive.extractfile(BINARY)
        except KeyError as error:
            raise AutheliaError(f"{source.name} carries no {BINARY}") from error
        if packed is None:  # pragma: no cover — a member that is not a file
            raise AutheliaError(f"{source.name} carries no {BINARY}")
        handle, temporary = tempfile.mkstemp(dir=where, prefix=f".{BINARY}.")
        try:
            with os.fdopen(handle, "wb") as out, packed:
                shutil.copyfileobj(packed, out)
            os.chmod(temporary, 0o755)
            os.replace(temporary, destination)
        except BaseException:
            os.unlink(temporary)
            raise

    files.atomic_write_text(stamp_file(), f"{platform_name()}\n")
    return destination


def valid_cookie_domain(host: str) -> bool:
    """Whether Authelia accepts `host` as a session cookie domain.

    Measured against the real binary: it refuses a domain with no dot that is
    not an IP (`validate-config` says so in just those words). `at.localhost`
    carries the dot a bare `localhost` does not, which is why the bundle's own
    default host is that and not the WebApp's usual loopback word.
    """
    if "." in host:
        return True
    import ipaddress

    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _drawn(path: Path) -> str:
    """The value a file already keeps, or one drawn now and kept from here on.

    Plaintext, and on purpose (module docstring): nothing here crosses a
    container boundary, so nothing here needs the Chave Principal's envelope.
    """
    try:
        held = path.read_text(encoding="utf-8").strip()
        if held:
            return held
    except FileNotFoundError:
        pass
    value = _secrets.token_urlsafe(SECRET_BYTES)
    path.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(path, f"{value}\n")
    return value


def session_secret() -> str:
    return _drawn(directory() / SESSION_SECRET)


def encryption_secret() -> str:
    return _drawn(directory() / ENCRYPTION_SECRET)


def jwt_secret() -> str:
    return _drawn(directory() / JWT_SECRET)


def free_port() -> int:
    """A loopback port nothing is on, handed straight back.

    Authelia is an external binary and not a Python `socket` this process
    can read an ephemeral port back from after the fact (the way `make_server`
    lets the WebApp's own backend do) — so a port is chosen BEFORE the process
    exists, the same way a free TCP port is always found when nothing can ask
    the thing that will bind it.
    """
    holder = socket.socket()
    holder.bind((LOOPBACK, 0))
    port = holder.getsockname()[1]
    holder.close()
    return port


# A PORTA lembrada. O Authelia é um serviço que FICA DE PÉ entre subidas — a
# sessão da pessoa vive nele, e reiniciar o `at-cli` NÃO o reinicia. A porta
# escolhida na primeira subida é guardada aqui, e a subida seguinte a REUSA em
# vez de abrir um segundo Authelia (que perderia as sessões abertas). Quem
# reinicia o Authelia é a pessoa, quando ela quiser.
PORT = "port"


def port_file() -> Path:
    return directory() / PORT


def remember(port: int) -> None:
    files.atomic_write_text(port_file(), f"{port}\n")


def standing() -> tuple[int, Path] | None:
    """O Authelia que já está DE PÉ — `(porta, config)` — ou `None`.

    Lê a porta lembrada e confirma que alguém responde nela. Um Authelia de uma
    subida anterior continua vivo (a sessão vive nele), e é ele que esta subida
    reusa; subir um segundo em outra porta seria perder quem está dentro.
    """
    try:
        port = int(port_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if not _listening(port):
        return None
    return port, directory() / CONFIG


def _listening(port: int) -> bool:
    try:
        with socket.create_connection((LOOPBACK, port), timeout=1):
            return True
    except OSError:
        return False


def users_yaml() -> str:
    """The people of the folder, in Authelia's own words — `_identity_users`'s
    exact shape, reused and not reinvented: the field is the derivation
    already proved by Forms and Basic, and never a password."""
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


def _quoted(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def palette() -> str:
    """The one of Authelia's four palettes (`light`, `dark`, `grey`, `auto`)
    that the instance's active theme maps to.

    A theme that ships both sides (`at`) wears `auto`, which follows the
    browser's own scheme exactly as the AT's pages do; a theme with one side
    pins that side. `grey` is never chosen: no AT theme maps to it.
    """
    from at.ui.webapp import look

    row = look.active_theme(None)
    sides = look.theme_sides(str(row.get("id"))) if row else []
    if sides == ["light"]:
        return "light"
    if sides == ["dark"]:
        return "dark"
    return "auto"


def _brand_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "ui" / "webapp" / "assets" / "icons"


def favicon_ico(png: bytes) -> bytes:
    """A one-image `.ico` that wraps a PNG (the format allows it), so the
    favicon is the AT's own mark and not a second drawing."""
    width = int.from_bytes(png[16:20], "big")
    height = int.from_bytes(png[20:24], "big")
    header = (0).to_bytes(2, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
    entry = bytes([width % 256, height % 256, 0, 0]) + (1).to_bytes(2, "little") \
        + (32).to_bytes(2, "little") + len(png).to_bytes(4, "little") \
        + (22).to_bytes(4, "little")
    return header + entry + png


def assets_directory() -> Path:
    """`App/services/authelia/assets/` — what Authelia's `server.asset_path`
    reads: `logo.png` and `favicon.ico`, the only brand files it accepts."""
    return directory() / ASSETS


def write_brand() -> Path:
    """Put the AT's mark where Authelia reads its logo and favicon."""
    where = assets_directory()
    where.mkdir(parents=True, exist_ok=True)
    png = (_brand_dir() / "icon-192.png").read_bytes()
    files.atomic_write_bytes(where / "logo.png", png)
    files.atomic_write_bytes(where / "favicon.ico", favicon_ico(png))
    return where


def configuration_yaml(host: str, listen_port: int, public_port: int,
                       rules: tuple[str, ...] = ()) -> str:
    """Authelia's configuration — the bundle's own gate, declared by `at-cli`.

    `listen_port` is the LOOPBACK port this Authelia listens on — the Caddy
    fronting it is the only caller that ever reaches it, exactly as the
    container path's provider is only ever reached by its own Caddy at its
    own `IDENTITY_PORT`. `public_port` is the Caddy's own — 443 when nothing
    says otherwise — because the cookie's domain and the portal's own address
    are what the PERSON's browser sees, and that is the edge's port and
    never the loopback one the two ports would otherwise collide on being the
    same value. `rules` names every extra domain (ntfy's own) that the
    access control also has to let through — each `one_factor`, the same
    policy the site itself gets, because it is the same Chave Principal
    proving the same person.

    **No `session.redis` block**, which is the module docstring's own trade:
    the bundle keeps sessions in Authelia's memory, and a restart of this one
    process drops them.
    """
    portal_url = f"{caddy.address(host, public_port)}{caddy.PORTAL}"
    lines = [
        f"theme: {palette()}",
        "server:",
        f"  address: {_quoted(f'tcp://{LOOPBACK}:{listen_port}{caddy.PORTAL}')}",
        f"  asset_path: {_quoted(str(assets_directory()))}",
        "log:",
        "  level: info",
        "session:",
        f"  secret: {_quoted(session_secret())}",
        "  cookies:",
        f"    - domain: {host}",
        f"      authelia_url: {_quoted(portal_url)}",
        "storage:",
        f"  encryption_key: {_quoted(encryption_secret())}",
        "  local:",
        f"    path: {directory() / DB}",
        "authentication_backend:",
        "  file:",
        f"    path: {directory() / USERS}",
        "access_control:",
        "  default_policy: deny",
        "  rules:",
        "    - domain: " + host,
        "      policy: one_factor",
    ]
    for extra in rules:
        lines += [f"    - domain: {extra}", "      policy: one_factor"]
    lines += [
        "notifier:",
        "  filesystem:",
        f"    filename: {directory() / NOTIFICATIONS}",
        "identity_validation:",
        "  reset_password:",
        f"    jwt_secret: {_quoted(jwt_secret())}",
    ]
    return "\n".join(lines) + "\n"


def write(host: str, listen_port: int, public_port: int,
          rules: tuple[str, ...] = ()) -> Path:
    """Write the configuration and the users file; answer where the config is."""
    directory().mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(directory() / USERS, users_yaml())
    write_brand()
    where = directory() / CONFIG
    files.atomic_write_text(
        where, configuration_yaml(host, listen_port, public_port, rules)
    )
    return where


def start(config: Path, log: bool = True) -> subprocess.Popen:
    """Run the Authelia in the foreground of this process's terminal.

    `log=False` is the suite's — a run whose output nobody reads, same reason
    `caddy.start` carries the same flag.
    """
    sink = None if log else subprocess.DEVNULL
    return subprocess.Popen([str(binary()), "--config", str(config)],
                            stdout=sink, stderr=sink)


def validate(config: Path) -> bool:
    """Whether Authelia itself accepts the configuration this module wrote.

    It runs the vendor's own `validate-config`, which parses and checks every
    rule the binary enforces at startup — the users file, the access control,
    the cookie domain — without opening a single port. This is what the test
    suite asks instead of guessing that a generated file is one Authelia
    reads the way this module hopes.
    """
    result = subprocess.run(
        [str(binary()), "validate-config", "--config", str(config)],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def stop(process: subprocess.Popen | None) -> None:
    """Stop the Authelia this process started, and only that one."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def started(process: subprocess.Popen, grace: float = 0.3) -> bool:
    """Whether the Authelia survived the blink in which it fails."""
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        return True
    return False
