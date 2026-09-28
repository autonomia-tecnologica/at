"""release.sbom — the composition of AT, published as one CycloneDX artifact.

**Item 46's whole reason.** `release.build` already reads where every number of
this release comes from — `builder.json` (the pinned interpreter), the two
`requirements*.txt` (runtime and build/dev dependencies, hash and all), the
vendored Caddy tarball (its version is its own filename, §3 Dependência
externa), and the frontend's lock (`package-lock.json`, the RESOLVED version a
declared range like `^3.5.43` never was) — but publishes none of it. A scanner
that wants to audit what shipped has nowhere to read it from. This file is
that publication: one line per component, and every version and hash read
from the SAME place `release.build` already trusts it from — never typed here.

**What is OUT, on purpose.** The container images `at_deploy` pins (§7): there
is no container path to describe yet, and this is the artifact's own
composition, not the environment's. And a component whose version has no
declared home — `builder.json`'s apt packages carry a NAME (`binutils`) and no
pinned version — does not enter until it earns one: a line half made would be
a number this file typed instead of read.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

from at import __version__ as AT_VERSION
from at.services import caddy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_DEV = ROOT / "requirements-dev.txt"
PACKAGE_LOCK = ROOT / "at" / "ui" / "webapp" / "package-lock.json"

# Where it lands, beside the binaries `release.build` already copies to `dist/`.
FILENAME = "at.cdx.json"

# `name==version`, on the requirements file's own pinning line — the one line
# per package that is never a continuation (`_HASH_RE`'s lines start with
# spaces, this one never does).
_PIN_RE = re.compile(r"^([A-Za-z0-9._-]+)==([^\s\\]+)")
# One pinned wheel's hash, on a continuation line. A package pins MORE than
# one when a wheel differs per platform, and every one of them travels — a
# scanner comparing a single artifact only ever matches one.
_HASH_RE = re.compile(r"--hash=sha256:([0-9a-f]{64})")


def _packages(path: Path, scope: str) -> list[dict]:
    """Every package a requirements file pins, each with every hash it carries."""
    found: list[dict] = []
    current: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        pinned = _PIN_RE.match(line)
        if pinned is not None:
            current = {
                "type": "library",
                "name": pinned.group(1),
                "version": pinned.group(2),
                "scope": scope,
                "hashes": [],
            }
            found.append(current)
            continue
        if current is None:
            continue
        for digest in _HASH_RE.findall(line):
            current["hashes"].append({"alg": "SHA-256", "content": digest})
    return found


def _interpreter(said: dict) -> dict:
    """The builder's own Python — the one every artifact of this release runs
    on, read from `builder.json` (`release.build.declared`) and not typed here.
    """
    _, _, digest = said["pinned"].partition("@sha256:")
    return {
        "type": "framework",
        "name": "python",
        "version": said["version"],
        "hashes": [{"alg": "SHA-256", "content": digest}],
        "scope": "required",
    }


def _caddy() -> dict | None:
    """Caddy — versioned by its own vendored tarball's NAME, hashed from its
    own bytes (§3: "there is no version to pin here", the name is the vendor's
    to spell). `None` when this machine's platform has no vendored Caddy — the
    same rule as an apt package with no pinned version: it does not enter
    until it has a home to read.
    """
    tarball = caddy.payload()
    if tarball is None:
        return None
    name = caddy.platform_name()
    version = tarball.name.removeprefix("caddy_").removesuffix(f"_{name}.tar.gz")
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    return {
        "type": "application",
        "name": "caddy",
        "version": version,
        "hashes": [{"alg": "SHA-256", "content": digest}],
        "scope": "required",
    }


def _frontend() -> dict | None:
    """The WebApp's one runtime dependency — read from the LOCK and not the
    range `package.json` declares: `^3.5.43` is a promise, and the lock is
    what actually got resolved and built into `at/ui/webapp/dist`.
    """
    if not PACKAGE_LOCK.is_file():
        return None
    lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
    entry = lock.get("packages", {}).get("node_modules/vue")
    if not isinstance(entry, dict):
        return None
    algorithm, _, encoded = str(entry.get("integrity", "")).partition("-")
    alg = {"sha512": "SHA-512", "sha384": "SHA-384", "sha256": "SHA-256"}.get(algorithm)
    hashes = ([{"alg": alg, "content": base64.b64decode(encoded).hex()}]
              if alg and encoded else [])
    return {
        "type": "library",
        "name": "vue",
        "version": entry.get("version", ""),
        "hashes": hashes,
        "scope": "required",
    }


def build(said: dict) -> dict:
    """The whole CycloneDX document — one line per component, read and not typed."""
    components = [_interpreter(said)]
    caddy_component = _caddy()
    if caddy_component is not None:
        components.append(caddy_component)
    components += _packages(REQUIREMENTS, "required")
    components += _packages(REQUIREMENTS_DEV, "excluded")
    frontend = _frontend()
    if frontend is not None:
        components.append(frontend)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "at", "version": AT_VERSION},
        },
        "components": components,
    }


def write(said: dict, out: Path) -> Path:
    """Write the SBOM into `out` (the release's own `dist/`) and answer its path."""
    where = out / FILENAME
    where.write_text(
        json.dumps(build(said), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return where
