"""The Caddy the binary carries — the TLS that exposure demands (§3, §6).

The rule this file answers is one sentence of §3: exposing demands
authentication **and** TLS, the TLS is Caddy's, and Caddy travels inside the
binary. So `at-cli webapp` turns a loopback WebApp into an exposed one by
default (`--no-caddy` is the one way out), and the four things that happen
are these, in this order: the Caddy is unpacked into the instance folder, the
Caddyfile AT generates is written, the Caddy is put in front of the WebApp,
and the WebApp stays exactly where it always was — `127.0.0.1`. What leaves
the loop is the Caddy's port, never the WebApp's.

**The certificate is AT's own, and nothing here delivers HSTS.** Caddy's
`tls internal` issues against a local CA instead of a public one, because AT
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

**The gate secret is item 13's, and its absence is not an error.** §7b says AT
draws a secret per installation, writes it into the Caddyfile it generates,
Caddy attaches it to every request carrying an identity, and AT refuses
whoever does not bring it. The Caddyfile carries both lines when the secret is
there — the `header_up` that attaches it and the `forward_auth` that asks the
identity provider who is calling. **A folder with neither an installed
environment nor a running bundle has no gate**, so the file is absent and the
two lines are too — the one case this sentence still describes.

**The secret is READ here, and DRAWN in TWO different places now (TASK-177,
2026-10-02).** `gate_secret` and `gate_file` are below because the file is
this Caddy's own (`App/services/caddy/gate`), and both artifacts read them: `at-cli`
refuses the identity that arrives without it, and the WebApp's check is what
turns the M2M into a door. The container path's draw is `at-deploy`'s
installation act (§7b, item 27, sealed by the Chave Principal because that
state folder is copied into a container with no encryption of its own) — the
deploy tool writes the environment's state, and `at-cli` reads it with the
deploy artifact absent. **The bundle's draw is `draw_gate`, right below**: the
hosted path's own, in the clear, because nothing here ever crosses a
container boundary — the same `App/` the backup already covers.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from platform import machine

from at.core import files
from at.services.caddy_base import (  # noqa: F401
    AUTH_HEADERS,
    AUTH_URI,
    AUTHORITY,
    BINARY,
    CADDYFILE,
    CERTIFICATES,
    FOLDER,
    GATE_BYTES,
    GATE_FILE,
    GATE_HEADER,
    GATE_PATH_ENV,
    HTTPS,
    LOOPBACK,
    PORTAL,
    STAMP,
    STORAGE,
    CaddyError,
    authority_file,
    binary,
    caddyfile_path,
    certificates_dir,
    directory,
    stamp_file,
    storage_dir,
)
from at.services.caddy_file import (  # noqa: F401
    WILDCARDS,
    address,
    caddyfile,
    wildcard,
    write_caddyfile,
)
from at.services.caddy_gate import (  # noqa: F401
    _drawn_in_the_clear,
    draw_gate,
    gate_file,
    gate_handed,
    gate_secret,
)

# Where the payload travels: `at/vendor/caddy/`, and the same arithmetic
# `app.py` uses for its own payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/at/services/caddy.py`, which is where `at-cli.spec` lands it.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "caddy"


# The vendor's own word for each platform, which is what its release assets are
# named with. `sys.platform` first, then the machine: a pair that is not here is
# a platform whose Caddy this artifact does not carry, and that is said instead
# of guessed (§9: Windows and macOS build on their own runners).
# Caddy names macOS `mac`, not `darwin` (gitleaks does say `darwin`).
SYSTEMS = {"linux": "linux", "darwin": "mac", "win32": "windows"}
MACHINES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}



def platform_name() -> str | None:
    """The vendor's word for this platform — `linux_amd64`, `mac_arm64`.

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


def _extension(name: str) -> str:
    """The vendor ships a `.zip` for Windows and a `.tar.gz` for everything else."""
    return "zip" if name.startswith("windows") else "tar.gz"


def _open(source: Path):
    """The vendor's archive, whichever of the two shapes it came in."""
    if source.suffix == ".zip":
        return zipfile.ZipFile(source)
    return tarfile.open(source, "r:gz")


def _member(archive, name: str):
    """The named member as a file object; `KeyError` when the archive has none."""
    if isinstance(archive, zipfile.ZipFile):
        return archive.open(name)
    return archive.extractfile(name)


def payload() -> Path | None:
    """The vendor's tarball for this platform, or `None` when there is none.

    Found by the platform and not by a version: the version is the binary's, so
    the name is the vendor's to spell (§3, Dependência externa).
    """
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"caddy_*_{name}.{_extension(name)}"))
    if len(found) != 1:
        # None, and not the first of many: two Caddies for one platform is a
        # build that does not know which one it carries, and picking one would
        # be AT deciding what the artifact is made of.
        return None
    return found[0]



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
    with _open(source) as archive:
        try:
            packed = _member(archive, BINARY)
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



def start(config: Path, log: bool = True) -> subprocess.Popen:
    """Run the Caddy in the foreground of this process's terminal.

    Its output is inherited on purpose: Caddy says which addresses it bound and
    what it refuses, and an AT that swallowed it would leave the person with a
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
    fails in milliseconds. AT printing a URL for a port nothing is on would be
    the worst answer available: a promise with no way to tell it was not kept.
    Caddy's own words are on the terminal beside this — its output is inherited —
    and this only decides whether AT gets to announce anything.
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
