"""The Caddy the binary carries — the TLS that exposure demands (§3, §6).

The rule this file answers is one sentence of §3: exposing demands
authentication **and** TLS, the TLS is Caddy's, and Caddy travels inside the
binary. So `bill webapp --include-caddy` is what turns a loopback WebApp into an
exposed one, and the four things that happen are these, in this order: the Caddy
is unpacked into the instance folder, the Caddyfile Bill generates is written,
the Caddy is put in front of the WebApp, and the WebApp stays exactly where it
always was — `127.0.0.1`. What leaves the loop is the Caddy's port, never the
WebApp's.

**The certificate is Bill's own, and nothing here delivers HSTS.** Caddy's
`tls internal` issues against a local CA instead of a public one, because Bill
does not depend on a public domain and cannot promise a trusted certificate; the
browser's warning is the honest price of that. HSTS would turn that warning into
an error with no way out, which is why §3 forbids it — the person can click
through a warning, and cannot click through a pinned failure.

**The payload is the vendor's tarball, byte for byte.** Caddy's version is the
binary's (§3, Dependência externa), so there is no version to pin here and none
is written: the tarball's own name carries the release, and the code finds it by
the platform it serves. Unpacking happens into `App/` and only when the platform
stamp does not match, which is what makes a folder carried from one system to
another re-unpack what no longer serves there — and what makes a folder whose
extracted Caddy was deleted unpack it again instead of refusing to run (§3: what
was extracted lives in the folder, and the folder is the backup).

**The gate secret is item 13's, and its absence is not an error.** §7b says Bill
draws a secret per installation, writes it into the Caddyfile it generates,
Caddy attaches it to every request carrying an identity, and Bill refuses
whoever does not bring it. That is the container path's M2M: the Caddyfile
carries both lines when the secret is there — the `header_up` that attaches it
and the `forward_auth` that asks the identity provider who is calling. The
hosted path has no gate, so the file is absent and the two lines are too.

**The secret is READ here and DRAWN there.** `gate_secret` and `gate_file` are
below because the file is this Caddy's own (`App/caddy/gate`), and both
artifacts read them: `bill` refuses the identity that arrives without it, and
the WebApp's check is what turns the M2M into a door. The DRAWING is the
environment's installation act and belongs to `bill-deploy` (§7b, item 27) —
the deploy tool is the one that writes the environment's state, and `bill` is
the one that reads it with the deploy artifact absent.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from platform import machine

from bill.core import files, paths
from bill.i18n import tr

# Where the payload travels: `bill/vendor/caddy/`, and the same arithmetic
# `app.py` uses for its own payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/bill/services/caddy.py`, which is where `bill.spec` lands it.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "caddy"

# The instance folder the unpacking goes to: `App/caddy/`. It is `App/` and not
# the person's folders because it is what Bill wrote to run, and it holds the
# four things the Caddy needs to live inside the folder: the binary, the stamp
# that says which platform it serves, the Caddyfile Bill generates, and the
# Caddy's OWN storage — its local CA and the certificates issued against it —
# which is redirected here so that the folder's copy still brings everything
# back (§3, the backup promise).
FOLDER = "caddy"

# Inside that folder. The stamp is the platform word, and the Caddyfile keeps
# Caddy's own name so that the adapter is inferred from it.
BINARY = "caddy"
STAMP = "platform"
CADDYFILE = "Caddyfile"
STORAGE = "storage"

# The header Caddy attaches to the requests it carries an identity on, and the
# file the secret is drawn into. The file sits beside the Caddyfile that is the
# only thing reading it — the Caddy's own folder, and not `App/services/`, which
# is where the state of the SERVICES of the container path lives (§7); this
# Caddy is a process of the folder that has no container around it.
GATE_HEADER = "X-Bill-Gate"
GATE_FILE = "gate"

# How much secret Bill draws. It is a value no person types and no person
# remembers — a header carries it — so it costs what `token_urlsafe` carries in
# bytes, and it says nothing about the folder it belongs to.
GATE_BYTES = 32

# Where the identity provider is asked, and what the ask is: §7b's
# forward-auth. `uri` is Authelia's own endpoint for it, and the four headers
# are the ones it answers with — `Remote-User` is the identity Bill reads
# (`ui/webapp/app.py`), and the other three travel because Authelia's answer
# carries them, not because anything here reads them.
AUTH_URI = "/api/authz/forward-auth"
AUTH_HEADERS = ("Remote-User", "Remote-Groups", "Remote-Name", "Remote-Email")

# The vendor's own word for each platform, which is what its release assets are
# named with. `sys.platform` first, then the machine: a pair that is not here is
# a platform whose Caddy this artifact does not carry, and that is said instead
# of guessed (§9: Windows and macOS build on their own runners).
SYSTEMS = {"linux": "linux", "darwin": "darwin", "win32": "windows"}
MACHINES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class CaddyError(Exception):
    """The artifact carries no usable Caddy for this platform."""


def platform_name() -> str | None:
    """The vendor's word for this platform — `linux_amd64`, `darwin_arm64`.

    `None` when the pair is not one the release names, which is a real answer and
    not a failure: the build froze a Caddy for one system, and this is another.
    """
    system = SYSTEMS.get(sys.platform)
    machine = MACHINES.get(_machine())
    if system is None or machine is None:
        return None
    return f"{system}_{machine}"


def _machine() -> str:
    """This machine, in lower case — `x86_64` on Linux, `AMD64` on Windows."""
    return machine().lower()


def label() -> str:
    """What to call this platform when it has no Caddy: the pair, in the words
    the system uses, so the refusal names what was looked for."""
    return f"{sys.platform}/{machine()}"


def payload() -> Path | None:
    """The vendor's tarball for this platform, or `None` when there is none.

    Found by the platform and not by a version: the version is the binary's, so
    the name is the vendor's to spell (§3, Dependência externa).
    """
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"caddy_*_{name}.tar.gz"))
    if len(found) != 1:
        # None, and not the first of many: two Caddies for one platform is a
        # build that does not know which one it carries, and picking one would
        # be Bill deciding what the artifact is made of.
        return None
    return found[0]


def directory() -> Path:
    """`App/caddy/` — where everything this file writes lives."""
    return paths.app_dir() / FOLDER


def binary() -> Path:
    """The unpacked Caddy, inside the folder."""
    return directory() / BINARY


def stamp_file() -> Path:
    """The platform the unpacked Caddy serves, written at unpacking time."""
    return directory() / STAMP


def caddyfile_path() -> Path:
    """The Caddyfile Bill generates — rewritten on every start."""
    return directory() / CADDYFILE


def storage_dir() -> Path:
    """The Caddy's own storage, inside the folder: the local CA and the
    certificates issued against it. Left outside, a copied folder would come
    back with a certificate nobody's browser had ever been told about."""
    return directory() / STORAGE


def unpacked() -> bool:
    """Whether the folder already carries the Caddy this platform runs."""
    if not binary().is_file() or not stamp_file().is_file():
        return False
    return stamp_file().read_text(encoding="utf-8").strip() == platform_name()


def ensure() -> Path | None:
    """Unpack the Caddy into the instance folder; `None` without a payload.

    It runs only when the stamp and the machine disagree, so the common path is
    one `read_text` and no writing at all.
    """
    if unpacked():
        return binary()

    source = payload()
    if source is None:
        return None

    where = directory()
    where.mkdir(parents=True, exist_ok=True)
    destination = binary()

    # Written beside the target and moved onto it, so a Caddy that is half
    # unpacked is never a Caddy the folder would try to run.
    with tarfile.open(source, "r:gz") as archive:
        try:
            packed = archive.extractfile(BINARY)
        except KeyError as error:
            raise CaddyError(f"{source.name} carries no {BINARY}") from error
        if packed is None:  # pragma: no cover — a member that is not a file
            raise CaddyError(f"{source.name} carries no {BINARY}")
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


def gate_file() -> Path:
    """`App/caddy/gate` — the secret's file, drawn by `bill-deploy` (§7b)."""
    return directory() / GATE_FILE


def gate_secret() -> str | None:
    """The M2M secret between the Caddy and the WebApp, when there is a gate.

    §7b: the secret is drawn by Bill at installation, written into the Caddyfile
    Bill generates, attached by the Caddy to every request carrying an identity,
    and refused by Bill to whoever does not bring it (`ui/webapp/app.py`). The
    line in the Caddyfile is this file's, and it is written only when the secret
    is there — a hosted folder with no gate has no file and gets no line.
    """
    try:
        secret = gate_file().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return secret or None


# Every way a person says "all of them". None of them can be a site address:
# `tls internal` issues a certificate FOR A NAME, and a wildcard is the absence
# of one — Caddy accepts `https://:443` and then cannot complete a handshake,
# which is a failure that only shows up in the browser (`run` refuses it before
# anything starts, and says what to name instead).
WILDCARDS = ("0.0.0.0", "::", "*")


def wildcard(host: str) -> bool:
    """Whether that address is "every address", which a certificate cannot name."""
    return host in WILDCARDS


def address(host: str, port: int) -> str:
    """The site address Caddy serves: the name the browser will use.

    It is a name and an IP both, because §3's certificate is Bill's own: Caddy's
    local CA issues for `localhost`, for a hostname and for an address alike, so
    exposing to the local network means naming the address the person reaches —
    `--host 192.168.1.10` — and not opening every one of them.
    """
    return f"https://{host}:{port}"


def caddyfile(host: str, port: int, backend: int, gate: str | None = None,
              storage: str | Path | None = None, auth: str | None = None) -> str:
    """The Caddyfile Bill generates: TLS in front, the WebApp behind.

    `backend` is the WebApp's own port, always on the loop: exposing moves the
    port the person reaches, never the address the WebApp listens on. The gate
    lines exist only when there is a secret to carry, and `admin off` is not
    decoration — an admin endpoint would be a local port that rewrites the
    running configuration with no credential at all.

    **The two gate lines travel together, and both are §7b.** `forward_auth` is
    the Caddy asking the identity provider who is calling, before it hands
    anything to the WebApp; `header_up` is the Caddy telling the WebApp, in the
    secret only it and Bill know, that the request came through here. `auth` is
    the provider's address — `host:port`, where the container path publishes it
    — and without it there is nobody to ask, so the block is not written: a
    hosted folder with a secret but no provider would otherwise ask a question
    with no answer and answer every request with a failure.

    `storage` is the ONE line that differs between the two paths, and it differs
    because a path is not a decision: the Caddy unpacked into the folder keeps
    its CA and its certificates there (§3, the backup promise), and the Caddy
    running as a container keeps them in the container's own data directory,
    which is a folder of the instance mounted into it (§7a). Every other line is
    the same Caddy answering the same questions, so it is written once.
    """
    proxy = [f"\treverse_proxy 127.0.0.1:{backend}"]
    if gate:
        proxy[0] += " {"
        proxy += [f"\t\theader_up {GATE_HEADER} {gate}", "\t}"]
    lines = [
        f"# {tr('caddy.file.header')}",
        "{",
        "\tadmin off",
        # And no autosave either: the running configuration is copied to Caddy's
        # own config directory, which is outside the folder — and the gate secret
        # is IN this file, so a copy of it living under `~/.config` would be the
        # secret leaving the folder and the backup (§3, §7b).
        "\tpersist_config off",
        # Bill does not enter the machine's trust store, and that is the same
        # decision as the missing HSTS: the root would have to be installed with
        # elevation, and §3 spends elevation only on an explicit request. The
        # browser keeps warning, which is the declared price of a certificate
        # that is Bill's own.
        "\tskip_install_trust",
        # Caddy's automatic HTTPS opens the redirect listener on :80 and refuses
        # to start when it cannot — a privileged port this product never serves.
        # The person reaches the URL Bill printed, and nothing redirects to it.
        "\tauto_https disable_redirects",
        f'\tstorage file_system "{storage or storage_dir()}"',
        "}",
        "",
        f"{address(host, port)} {{",
        "\ttls internal",
    ]
    if gate and auth:
        # Bill is ONE MORE APP here and not an exception (§7b): the same block
        # that would stand in front of Sonarr stands in front of Bill, and what
        # makes it Bill is only the secret on the line below.
        lines += [
            f"\tforward_auth {auth} {{",
            f"\t\turi {AUTH_URI}",
            f"\t\tcopy_headers {' '.join(AUTH_HEADERS)}",
            "\t}",
        ]
    lines += [*proxy, "}"]
    return "\n".join(lines) + "\n"


def write_caddyfile(host: str, port: int, backend: int,
                    auth: str | None = None) -> Path:
    """Write the Caddyfile the Caddy is started with, and answer where it is."""
    where = caddyfile_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where,
                            caddyfile(host, port, backend, gate_secret(), auth=auth))
    return where


def start(config: Path, log: bool = True) -> subprocess.Popen:
    """Run the Caddy in the foreground of this process's terminal.

    Its output is inherited on purpose: Caddy says which addresses it bound and
    what it refuses, and a Bill that swallowed it would leave the person with a
    port that answers nothing and no reason why. `log=False` is the suite's: the
    Caddy speaks JSON, line per line, for whoever runs the server and not for
    whoever reads a test's output.
    """
    sink = None if log else subprocess.DEVNULL
    return subprocess.Popen([str(binary()), "run", "--config", str(config)],
                            stdout=sink, stderr=sink)


def started(process: subprocess.Popen, grace: float = 0.3) -> bool:
    """Whether the Caddy survived the blink in which it fails.

    The way it fails is binding a port somebody else already answers on, and it
    fails in milliseconds. Bill printing a URL for a port nothing is on would be
    the worst answer available: a promise with no way to tell it was not kept.
    Caddy's own words are on the terminal beside this — its output is inherited —
    and this only decides whether Bill gets to announce anything.
    """
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        return True
    return False


def stop(process: subprocess.Popen | None) -> None:
    """Stop the Caddy this process started, and only that one."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
