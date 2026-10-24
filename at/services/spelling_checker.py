"""The `spelling-checker` service, fulfilled today by LanguageTool — spawned by AT.

Not a container: the same arithmetic as the Caddy and the Authelia
(`caddy.py`, `authelia.py`). A vendored payload is unpacked into
`App/services/spelling-checker/` on demand and run as a subprocess of
`at-cli webapp`, which stops it when it goes down. The question the rest of AT
asks it is `at.core.spelling` (`available`, `check`).

**The payload is built, not byte-for-byte.** LanguageTool is Java, so what
travels is one tarball with a minimal JRE (`jlink`, Temurin) and a trimmed
LanguageTool server, built by `python3 -m release.spelling_checker`. Both
upstream archives are pinned by `sha256` in `at/vendor/spelling-checker/
manifest.json`, and so is the payload itself: this module refuses to unpack a
tarball whose hash is not the manifest's.

**Unavailable never takes anything down.** No payload for the platform, a
payload that does not match its pin, a process that does not start: every one
is `None`/`False` here, a line said, and AT goes on. The service listens on
`127.0.0.1` only, on a port chosen at spawn and remembered while it is up
(`core.spelling.remember`), and it does not outlive the process that spawned
it. Offline by construction: the server is local, there are no n-grams and
nothing is uploaded.

Linux x64 only. Windows and macOS follow the Authelia's precedent (`paths.md`):
unavailable, and said.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path
from platform import machine

from at.core import files, paths, spelling
from at.services import authelia

PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "spelling-checker"
MANIFEST = "manifest.json"
STAMP = "stamp"
HEAP = "-Xmx512m"

# Whether `at-cli webapp` spawns it. The suite turns it off (`at/tests/__init__.py`):
# a test that runs the WebApp must not spawn a JVM.
AUTOSTART = True


def platform_name() -> str | None:
    if sys.platform == "linux" and machine().lower() in ("x86_64", "amd64"):
        return "linux-x64"
    return None


def label() -> str:
    return f"{sys.platform}/{machine()}"


def manifest() -> dict:
    return json.loads((PAYLOAD / MANIFEST).read_text(encoding="utf-8"))


def payload() -> Path | None:
    """The payload tarball for this platform, or `None` without one."""
    try:
        said = manifest()
    except (OSError, ValueError):
        return None
    if said.get("platform") != platform_name():
        return None
    found = PAYLOAD / said["payload"]["file"]
    return found if found.is_file() else None


def pinned() -> str:
    return str(manifest()["payload"]["sha256"])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def directory() -> Path:
    return paths.service_dir(spelling.FOLDER)


def java() -> Path:
    return directory() / "jre" / "bin" / "java"


def unpacked() -> bool:
    stamp = directory() / STAMP
    if not java().is_file() or not stamp.is_file():
        return False
    try:
        return stamp.read_text(encoding="utf-8").strip() == pinned()
    except (OSError, ValueError, KeyError):
        return False


def ensure() -> Path | None:
    """Unpack the payload into the instance folder; `None` when it cannot.

    `None` covers: no payload for this platform, and a payload whose hash is
    not the pinned one (nothing is unpacked from a tarball that does not match
    its pin). The unpacking happens aside and is moved onto the target, so a
    half-unpacked JRE is never one the folder would try to run.
    """
    if unpacked():
        return java()
    source = payload()
    if source is None:
        return None
    try:
        if _sha256(source) != pinned():
            return None
    except (OSError, KeyError, ValueError):
        return None

    where = directory()
    where.mkdir(parents=True, exist_ok=True)
    aside = Path(tempfile.mkdtemp(dir=where, prefix=".unpack."))
    try:
        with tarfile.open(source, "r:xz") as archive:
            archive.extractall(aside, filter="data")
        for name in ("jre", "languagetool"):
            target = where / name
            if target.exists():
                shutil.rmtree(target)
            os.replace(aside / name, target)
        files.atomic_write_text(where / STAMP, f"{pinned()}\n")
    except (OSError, tarfile.TarError):
        return None
    finally:
        shutil.rmtree(aside, ignore_errors=True)
    return java() if java().is_file() else None


def command(port: int) -> list[str]:
    root = directory() / "languagetool"
    return [
        str(java()), HEAP, "-Djava.net.preferIPv4Stack=true",
        "-cp", f"{root / 'languagetool-server.jar'}{os.pathsep}{root / 'libs' / '*'}"
               f"{os.pathsep}{root}",
        "org.languagetool.server.HTTPServer", "--port", str(port),
    ]


def start(port: int, log: bool = False) -> subprocess.Popen:
    """Spawn the server on the loopback. It binds `127.0.0.1` only (no `--public`)."""
    sink = None if log else subprocess.DEVNULL
    return subprocess.Popen(command(port), stdout=sink, stderr=sink,
                            cwd=str(directory()))


def started(process: subprocess.Popen, grace: float = 0.5) -> bool:
    """Whether the process survived the blink in which a bad start fails."""
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        return True
    return False


def ready(port: int, timeout: float = 30.0) -> bool:
    """Whether the server answers a request within `timeout` seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{spelling.LOOPBACK}:{port}/v2/languages", timeout=1
            ):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def bring_up(log: bool = False) -> subprocess.Popen | None:
    """Unpack, spawn and remember. `None` — and a stale port forgotten — when
    any step cannot be done. It never raises: this service is never a reason
    for AT not to come up."""
    try:
        spelling.forget()
        if ensure() is None:
            return None
        port = authelia.free_port()
        process = start(port, log=log)
        if not started(process):
            return None
        spelling.remember(port)
        return process
    except Exception:  # noqa: BLE001 — unavailable must never take AT down
        return None


def stop(process: subprocess.Popen | None) -> None:
    """Stop the process this run spawned, and forget its port."""
    try:
        spelling.forget()
    except OSError:
        pass
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
