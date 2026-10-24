"""release.fetch — pulls the vendored payloads from outside, pinned by manifest.

The payloads under `at/vendor/*` (Caddy, gitleaks, Authelia, the spelling-checker)
are ~190 MB and are NOT versioned: what is versioned is each folder's
`manifest.json`, which names every file, its platform, the vendor's official URL
and the `sha256` it must have. This module is the one door that turns the pin
into bytes on disk, in the same place and under the same name the services and
the PyInstaller specs already read.

    python3 -m release.fetch [--platform linux-x64] [--cache DIR]

- **Idempotent.** A file that exists and whose hash is the pinned one is left
  alone: nothing is downloaded.
- **A wrong hash is never used.** The bad file is deleted and the run fails with
  a message that names the file, the hash found and the hash pinned.
- **The spelling-checker is generated, not downloaded.** Its manifest pins the
  upstream JDK and LanguageTool; `release.spelling_checker` downloads, trims and
  packs them, and the result must be the payload hash the manifest pins.

Platforms are the manifests' own words: `linux-x64`, `macos-arm64`,
`windows-x64`. Without `--platform` every platform is fetched, which is what the
release needs (the onefile carries them all).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "at" / "vendor"
GENERATED = "spelling-checker"
PLATFORM = "linux-x64"  # the only platform the generated payload exists for


class FetchError(Exception):
    """A payload could not be had with the pinned hash."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def entries(vendor: Path = VENDOR, platforms: set[str] | None = None) -> list[dict]:
    """Every pinned payload: `service`, `file`, `platform`, `url`, `sha256`, `path`."""
    found: list[dict] = []
    for manifest in sorted(vendor.glob("*/manifest.json")):
        folder = manifest.parent
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if "files" in data:
            for item in data["files"]:
                found.append({**item, "service": folder.name, "path": folder / item["file"]})
        elif "payload" in data:
            found.append({
                "service": folder.name, "platform": PLATFORM,
                "file": data["payload"]["file"], "sha256": data["payload"]["sha256"],
                "url": None, "path": folder / data["payload"]["file"],
            })
    if platforms:
        found = [item for item in found if item["platform"] in platforms]
    return found


def good(item: dict) -> bool:
    return item["path"].is_file() and sha256(item["path"]) == item["sha256"]


def missing(vendor: Path = VENDOR, platforms: set[str] | None = None) -> list[dict]:
    """The pinned payloads that are absent or do not match their hash."""
    return [item for item in entries(vendor, platforms) if not good(item)]


def _download(url: str, target: Path, opener) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with opener(url) as reply, target.open("wb") as out:
        shutil.copyfileobj(reply, out)


def _fetch_one(item: dict, cache: Path | None, opener) -> None:
    target: Path = item["path"]
    pinned = item["sha256"]
    source = target
    if cache is not None:
        source = cache / item["service"] / item["file"]
    if not (source.is_file() and sha256(source) == pinned):
        source.unlink(missing_ok=True)
        print(f"downloading {item['url']}")
        partial = source.with_name(source.name + ".part")
        try:
            _download(item["url"], partial, opener)
        except OSError as error:
            partial.unlink(missing_ok=True)
            raise FetchError(f"{item['service']}/{item['file']}: download failed: {error}") from error
        found = sha256(partial)
        if found != pinned:
            partial.unlink(missing_ok=True)
            raise FetchError(
                f"{item['service']}/{item['file']}: sha256 {found} is not the pinned "
                f"{pinned}; the file was deleted and is not used")
        partial.replace(source)
    if source != target:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _generate_spelling_checker(item: dict, cache: Path | None, vendor: Path) -> None:
    from release import spelling_checker

    manifest = vendor / GENERATED / "manifest.json"
    before = manifest.read_text(encoding="utf-8")
    argv = ["--cache", str(cache / GENERATED)] if cache else []
    try:
        spelling_checker.main(argv)
    except SystemExit as error:
        raise FetchError(f"{GENERATED}: {error.code}") from error
    finally:
        # The generator rewrites the pin; the pin is the person's, not the build's.
        manifest.write_text(before, encoding="utf-8")
    if not good(item):
        item["path"].unlink(missing_ok=True)
        raise FetchError(
            f"{GENERATED}/{item['file']}: the generated payload is not the pinned "
            f"sha256 {item['sha256']}; deleted. Rebuild is not reproducible on this "
            f"machine, or the pin is stale (`python3 -m release.spelling_checker`).")


def fetch(vendor: Path = VENDOR, platforms: set[str] | None = None,
          cache: Path | None = None, opener=urllib.request.urlopen) -> list[str]:
    """Ensure every pinned payload is on disk with its hash. Returns what it fetched."""
    done: list[str] = []
    for item in entries(vendor, platforms):
        label = f"{item['service']}/{item['file']}"
        if item["path"].is_file():
            if sha256(item["path"]) == item["sha256"]:
                continue
            item["path"].unlink()
            print(f"{label}: hash does not match the pin; deleted")
        if item["service"] == GENERATED:
            _generate_spelling_checker(item, cache, vendor)
        else:
            _fetch_one(item, cache, opener)
        done.append(label)
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m release.fetch")
    parser.add_argument("--platform", action="append",
                        help="only this platform (linux-x64, macos-arm64, windows-x64); repeatable")
    parser.add_argument("--cache", type=Path, default=None,
                        help="where downloads are kept between runs")
    args = parser.parse_args(argv)
    try:
        done = fetch(platforms=set(args.platform) if args.platform else None,
                     cache=args.cache)
    except FetchError as error:
        print(f"release.fetch: {error}", file=sys.stderr)
        return 1
    print(f"fetched {len(done)}: " + ", ".join(done) if done else "all payloads present and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
