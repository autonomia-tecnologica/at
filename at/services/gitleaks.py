"""The `gitleaks` the binary carries — the scanner the folder is walked with (§3, item 51).

The rule this file answers is one sentence of §3 (Dependência externa): a package
is pinned in version and in hashing, and the artifact that carries it is where the
pin lives. `gitleaks` is MIT, so it may travel inside the binary — and it does,
in `at-cli` only (`at-deploy` has no scanning word, so embedding it there would
pay the megabytes for a door nobody knocks on). This module is the half that
makes that travel real: the vendor's tarball goes into `at/vendor/gitleaks/`, the
scanner unpacks it into `App/services/gitleaks/`, and `at/core/scanner.py` runs what came
out. Nothing here reaches a network, and nothing here runs the program.

**The payload is the vendor's tarball, byte for byte.** Found by the platform and
not by a version, exactly as the Caddy's is: the tarball's own name carries the
release, and the version that stood behind a scan is the one the tool answers
(`scanner.named`). It was verified where it entered — the `sha256` of the archive
against the release's own `checksums.txt`, and the binary inside it against the
`gitleaks 8.30.1` the person already had — and what travels from here on is those
same bytes. **The vendor spells the machine differently**: `linux_x64`, where the
Caddy spells `linux_amd64`, and `windows_x64` is a `.zip` — which the glob below
carries too (`_extension`), with `gitleaks.exe` as its member.

**The unpacking is the Caddy's own arithmetic.** It lands in `App/` and only when
the platform stamp does not match, which is what makes a folder carried from one
system to another re-unpack what no longer serves there — and what makes a folder
whose extracted tool was deleted unpack it again instead of refusing to scan
(§3: what was extracted lives in the folder, and the folder is the backup). The
stamp is written beside the target and the binary is moved onto it, so a half
unpacked scanner is never one the folder would try to run.

**Extracting is what a scan pays once.** The common path is one `is_file` and one
`read_text` and no writing at all; the first scan after the payload or the
platform changes unpacks into `App/services/gitleaks/`, which is AT's own folder in the
same sense `App/services/caddy/` is. It is not the person's data, it is not versioned by
the scan, and it leaves no `audit` line — the read's promise (§3, item 51) is
untouched.
"""

from __future__ import annotations

import os
import shutil
import sys
import tarfile
import zipfile
import tempfile
from pathlib import Path
from platform import machine

from at.core import files, paths

# Where the payload travels: `at/vendor/gitleaks/`, and the same arithmetic
# `app.py` uses for its own payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/at/services/gitleaks.py`, which is where `at-cli.spec` lands it.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "gitleaks"

# The instance folder the unpacking goes to: `App/services/gitleaks/`. It is `App/` and
# not the person's folders for the reason the Caddy's is: it is what AT wrote to
# run, and a folder carried to another machine carries the tool with it (§3, the
# backup promise).
FOLDER = "gitleaks"

# Inside that folder: the binary and the stamp that says which platform it serves.
# The member's name inside the vendor's archive, which is also the unpacked file:
# Windows spells it with the `.exe` its loader needs.
BINARY = "gitleaks.exe" if sys.platform == "win32" else "gitleaks"
STAMP = "platform"

# The vendor's own word for each platform, which is what its release assets are
# named with — and it is NOT the Caddy's: gitleaks spells the machine `x64` where
# Caddy spells it `amd64`. `sys.platform` first, then the machine: a pair that is
# not here is a platform whose gitleaks this artifact does not carry, and that is
# answered instead of guessed (§9: Windows and macOS build on their own runners).
SYSTEMS = {"linux": "linux", "darwin": "darwin", "win32": "windows"}
MACHINES = {
    "x86_64": "x64",
    "amd64": "x64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class GitleaksError(Exception):
    """The tarball this artifact carries is not one this module can unpack."""


def platform_name() -> str | None:
    """The vendor's word for this platform — `linux_x64`, `darwin_arm64`.

    `None` when the pair is not one the release names, which is a real answer and
    not a failure: the build froze a gitleaks for one system, and this is another.
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
    """What to call this platform when it has no gitleaks: the pair, in the words
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

    Found by the platform and not by a version, for the reason the Caddy's is:
    the version is the binary's, so the name is the vendor's to spell.
    """
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"gitleaks_*_{name}.{_extension(name)}"))
    if len(found) != 1:
        # None, and not the first of many: two scanners for one platform is a
        # build that does not know which one it carries, and picking one would be
        # AT deciding what the artifact is made of.
        return None
    return found[0]


def directory() -> Path:
    """`App/services/gitleaks/` — where everything this file writes lives."""
    return paths.service_dir(FOLDER)


def binary() -> Path:
    """The unpacked gitleaks, inside the folder."""
    return directory() / BINARY


def stamp_file() -> Path:
    """The platform the unpacked gitleaks serves, written at unpacking time."""
    return directory() / STAMP


def unpacked() -> bool:
    """Whether the folder already carries the gitleaks this platform runs."""
    if not binary().is_file() or not stamp_file().is_file():
        return False
    return stamp_file().read_text(encoding="utf-8").strip() == platform_name()


def ensure() -> Path | None:
    """Unpack the gitleaks into the instance folder; `None` without a payload.

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

    # Written beside the target and moved onto it, so a scanner that is half
    # unpacked is never a scanner the folder would try to run.
    with _open(source) as archive:
        try:
            packed = _member(archive, BINARY)
        except KeyError as error:
            raise GitleaksError(f"{source.name} carries no {BINARY}") from error
        if packed is None:  # pragma: no cover — a member that is not a file
            raise GitleaksError(f"{source.name} carries no {BINARY}")
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
