"""The ntfy the binary carries — the bundle's own notifier, fronted by Authelia.

**TASK-177's bundle, the notifier's half.** The container path's ntfy is a
container from a pinned image (`at_deploy/environment.py`, `at_deploy/
notifier.py`); the bundle's is this module's — the vendor's tarball, byte for
byte, unpacked into `App/ntfy/` and run as a subprocess of `at-cli` itself, the
same arithmetic `caddy.py` and `authelia.py` already answer to. It comes up
with the same trigger they do: `at-cli webapp --include-caddy`.

**Account, topic and token are the container path's own names, unchanged.**
One account (`ACCOUNT`), one topic (`TOPIC`), read-write, because least
privilege for a notifier that only AT ever posts to and only AT ever reads
from does not need a second account to have none of (`_draw`'s own four
calls, mirrored here against the real binary and not a container's `exec`).

**Provisioning needs the server ALREADY RUNNING, and that is ntfy's own
rule, not AT's.** `ntfy user add` and `ntfy access` manage the very
`auth-file` the server opens at start — measured against the real binary: a
`server.yml` with `auth-file` set and no server ever started answers "auth-file
does not exist; please start the server at least once to create it" to every
one of them. So `provision` polls for that file exactly as `at_deploy/
notifier.py`'s own `_wait_auth` already does, then runs the three commands
against the config this module wrote, never against a container's `exec`.

**The M2M credential is drawn by `caddy.py`, not here.** `caddy.
draw_notify_secret` is this bundle's `draw_gate`-shaped plaintext draw — the
same relationship the container path's own `environment.draw_notify_gate`
has with its Caddy — and `provision` takes the raw password it returns on
stdin, for `ntfy user add`. The Caddyfile's own line base64-encodes the SAME
value as `user:password` before writing it (`webapp.run`, mirroring
`notifier.encode_m2m`'s shape): the two have to agree on the one value, and
AT choosing it before any account exists is what lets the Caddyfile be
written first.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from platform import machine

from at.core import files, paths

PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "ntfy"
FOLDER = "ntfy"
BINARY = "ntfy"
STAMP = "platform"
CONFIG = "server.yml"
AUTH_DB = "user.db"
CACHE_DB = "cache.db"
ATTACHMENTS = "attachments"

LOOPBACK = "127.0.0.1"

# The environment's own names (`at_deploy/notifier.py`), unchanged: one
# account, one topic, both the role and not the brand — the day another
# notifier serves this role, neither name has a reason to move.
ACCOUNT = "at"
TOPIC = "at"
LABEL = "at"

# How long `provision` waits for the auth database to exist, and how often it
# asks — the server's own startup, measured in the low hundreds of
# milliseconds on this machine, and not a network round trip.
GRACE = 10.0
STEP = 0.2

TOKEN_WORD = re.compile(r"tk_[a-z0-9]{10,}")

# The vendor's own word for each platform — the same scheme `caddy.py` reads,
# because ntfy's goreleaser spells it the same way Caddy's does
# (`ntfy_2.28.0_linux_amd64.tar.gz`).
SYSTEMS = {"linux": "linux", "darwin": "darwin", "win32": "windows"}
MACHINES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class NtfyError(Exception):
    """The artifact carries no usable ntfy for this platform."""


def platform_name() -> str | None:
    system = SYSTEMS.get(sys.platform)
    found = MACHINES.get(_machine())
    if system is None or found is None:
        return None
    return f"{system}_{found}"


def _machine() -> str:
    return machine().lower()


def label() -> str:
    return f"{sys.platform}/{machine()}"


def payload() -> Path | None:
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"ntfy_*_{name}.tar.gz"))
    if len(found) != 1:
        return None
    return found[0]


def directory() -> Path:
    """`App/ntfy/` — where everything this file writes lives."""
    return paths.app_dir() / FOLDER


def binary() -> Path:
    return directory() / BINARY


def stamp_file() -> Path:
    return directory() / STAMP


def unpacked() -> bool:
    if not binary().is_file() or not stamp_file().is_file():
        return False
    return stamp_file().read_text(encoding="utf-8").strip() == platform_name()


def _member(archive: tarfile.TarFile) -> tarfile.TarInfo | None:
    """The binary's own member, wherever the vendor nested it.

    ntfy's tarball holds it inside a release-named folder
    (`ntfy_2.28.0_linux_amd64/ntfy`) — unlike Authelia's and the Caddy's own,
    which carry it at the root — so the member is found by its TAIL and not
    by an exact name, which is what survives the version in the middle of the
    path changing release to release.
    """
    for member in archive.getmembers():
        if member.isfile() and (member.name == BINARY
                                 or member.name.endswith(f"/{BINARY}")):
            return member
    return None


def ensure() -> Path | None:
    """Unpack the ntfy into the instance folder; `None` without a payload."""
    if unpacked():
        return binary()

    source = payload()
    if source is None:
        return None

    where = directory()
    where.mkdir(parents=True, exist_ok=True)
    destination = binary()

    with tarfile.open(source, "r:gz") as archive:
        member = _member(archive)
        if member is None:
            raise NtfyError(f"{source.name} carries no {BINARY}")
        packed = archive.extractfile(member)
        if packed is None:  # pragma: no cover — a member that is not a file
            raise NtfyError(f"{source.name} carries no {BINARY}")
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


def free_port() -> int:
    """A loopback port nothing is on — ntfy's own, chosen before it exists."""
    holder = socket.socket()
    holder.bind((LOOPBACK, 0))
    port = holder.getsockname()[1]
    holder.close()
    return port




def _quoted(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def configuration_yaml(port: int, public_url: str) -> str:
    """ntfy's configuration — `_notifier_conf`'s own shape, without a container.

    `port` is the LOOPBACK port this ntfy listens on, published nowhere else
    — the bundle's Caddy is the only caller that ever reaches it, the same
    posture the container path's `_notifier_ports` already measured into a
    rule ("fica no laço — nunca mais na rede privada"). `public_url` is what
    the PHONE is told to point at: the Caddy's own name for this service, with
    the certificate and the `forward_auth` both in front of it.
    """
    return "\n".join([
        f"base-url: {_quoted(public_url)}",
        f"listen-http: {_quoted(f'{LOOPBACK}:{port}')}",
        f"cache-file: {_quoted(str(directory() / CACHE_DB))}",
        f"attachment-cache-dir: {_quoted(str(directory() / ATTACHMENTS))}",
        f"auth-file: {_quoted(str(directory() / AUTH_DB))}",
        "behind-proxy: true",
        'auth-default-access: "deny-all"',
    ]) + "\n"


def write(port: int, public_url: str) -> Path:
    directory().mkdir(parents=True, exist_ok=True)
    where = directory() / CONFIG
    files.atomic_write_text(where, configuration_yaml(port, public_url))
    return where


def start(config: Path, log: bool = True) -> subprocess.Popen:
    sink = None if log else subprocess.DEVNULL
    return subprocess.Popen([str(binary()), "serve", "--config", str(config)],
                            stdout=sink, stderr=sink)


def started(process: subprocess.Popen, grace: float = 0.3) -> bool:
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        return True
    return False


def stop(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_auth_db(config: Path, grace: float = GRACE) -> bool:
    """Whether the server this module started wrote its own auth database.

    `provision` cannot run before this — ntfy's own refusal, measured
    (module docstring) — and the file's path is this same `config`'s own
    `auth-file` line, which is always `directory() / AUTH_DB`.
    """
    where = directory() / AUTH_DB
    deadline = time.monotonic() + grace
    while True:
        if where.is_file():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(STEP)


def _run(config: Path, *argv: str, input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(binary()), argv[0], "--config", str(config), *argv[1:]],
        input=input, capture_output=True, text=True,
    )


def provision(config: Path, password: str) -> str | None:
    """Create AT's credential in this ntfy — the bundle's own act of §7f.

    The same four calls `at_deploy/notifier.py`'s `_draw` makes, against this
    binary directly instead of a container's `exec`: the account starts
    clean (`user remove`, a missing account is not a failure), the account is
    made with `password` on stdin and never in the argv, the scope is
    granted, and the token is drawn by ntfy itself and read off its own line.
    `None` is any one of the four refusing — the caller already printed which.
    """
    _run(config, "user", "remove", ACCOUNT)
    added = _run(config, "user", "add", "--role=user", ACCOUNT,
                 input=f"{password}\n{password}\n")
    if added.returncode != 0:
        return None

    scoped = _run(config, "access", ACCOUNT, TOPIC, "read-write")
    if scoped.returncode != 0:
        return None

    created = _run(config, "token", "add", f"--label={LABEL}", ACCOUNT)
    found = TOKEN_WORD.search(created.stdout or "")
    if created.returncode != 0 or found is None:
        return None
    return found.group(0)
