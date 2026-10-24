"""release.spelling_checker — builds the `spelling-checker` payload AT vendors.

The service is fulfilled today by LanguageTool, which is Java, so the payload
is two upstream artifacts joined into ONE tarball: a minimal JRE cut with
`jlink` from a Temurin JDK, and the LanguageTool server with only what the
languages AT answers (English and Portuguese) need. Neither upstream archive
is committed — they are 250 MB and 200 MB — so this script is where the pin
lives: it downloads each one, refuses it unless its `sha256` is the one
`at/vendor/spelling-checker/manifest.json` declares, builds the tarball
deterministically, and writes the payload's own `sha256` back to that
manifest. `at/services/spelling_checker.py` then refuses to unpack any payload
whose hash is not the manifest's.

    python3 -m release.spelling_checker [--cache DIR]

Linux x64 only: Temurin and LanguageTool publish more, but the trimming and
the smoke here were measured on Linux x64 alone, and the precedent for a
platform that is not measured is the Authelia's (`paths.md`): unavailable.

What is removed from LanguageTool, and why it is safe (each was measured by
running the server and checking en-US and pt-BR): the other languages'
resource folders (spelling and tagging dictionaries) except `common_words.txt`,
which the language identifier loads for every language at startup; the other
languages' grammar and data files under `rules/`, `tagging/`, `tokenizers/`
and the like (their `.class` files stay, because the language registry
instantiates every language); the dictionaries
jars of other languages; and two jars (`icu4j`, `grpc-netty-shaded`) the
server never loads. No LanguageTool jar is modified, so the LGPL's relink
promise is untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import lzma
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "at" / "vendor" / "spelling-checker"
MANIFEST = FOLDER / "manifest.json"

# Modules the LanguageTool server needs, found with `jdeps` over the server
# jar and `libs/*` and widened by what the smoke showed (`java.xml`,
# `java.logging`, `java.management`, `java.prefs` are reached by reflection).
MODULES = (
    "java.base,java.compiler,java.desktop,java.instrument,java.naming,"
    "java.scripting,java.sql,java.xml,java.logging,java.management,java.prefs,"
    "jdk.httpserver,jdk.management,jdk.unsupported"
)

OTHER_LANGUAGES = (
    "ar ast be br ca crh da de de-DE-x-simple-language el eo es fa fr ga gl "
    "it ja km nl pl ro ru sk sl sv ta tl uk zh"
).split()
DATA_FOLDERS = ("resource", "rules", "synthesis", "tagging", "tokenizers",
                "chunking", "disambiguation")
DROPPED_JARS = (
    "dutch-pos-dict", "languagetool-ga-dicts", "catalan-pos-dict",
    "spanish-pos-dict", "german-pos-dict", "french-pos-dict",
    "asturian-pos-dict", "morfologik-ukrainian-lt", "morfologik-crh-lt",
    "hanlp", "lucene-gosen-ipadic", "morphology-el", "languagetool-core-tests",
    "languagetool-tools", "junit", "icu4j", "grpc-netty-shaded",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(entry: dict, cache: Path) -> Path:
    """The upstream archive, from the cache or the network, hash-checked."""
    target = cache / entry["file"]
    if not target.is_file():
        print(f"downloading {entry['url']}")
        with urllib.request.urlopen(entry["url"]) as reply, target.open("wb") as out:
            shutil.copyfileobj(reply, out)
    found = sha256(target)
    if found != entry["sha256"]:
        target.unlink()
        raise SystemExit(f"{entry['file']}: sha256 {found} is not the pinned {entry['sha256']}")
    return target


def trim_languagetool(root: Path) -> None:
    base = root / "org" / "languagetool"
    for folder in DATA_FOLDERS:
        for code in OTHER_LANGUAGES:
            target = base / folder / code
            if not target.is_dir():
                continue
            if folder == "resource":
                for item in target.iterdir():
                    if item.name == "common_words.txt":
                        continue
                    shutil.rmtree(item) if item.is_dir() else item.unlink()
            else:
                for item in sorted(target.rglob("*"), reverse=True):
                    if item.is_file() and item.suffix != ".class":
                        item.unlink()
                    elif item.is_dir() and not any(item.iterdir()):
                        item.rmdir()
    for name in DROPPED_JARS:
        (root / "libs" / f"{name}.jar").unlink(missing_ok=True)


def add_tree(archive: tarfile.TarFile, root: Path, prefix: str) -> None:
    for path in sorted(root.rglob("*")):
        info = archive.gettarinfo(str(path), f"{prefix}/{path.relative_to(root).as_posix()}")
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as handle:
                archive.addfile(info, handle)
        else:
            archive.addfile(info)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m release.spelling_checker")
    parser.add_argument("--cache", type=Path, default=None,
                        help="where upstream archives are kept between runs")
    args = parser.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cache = args.cache or Path(tempfile.mkdtemp(prefix="at-spelling-cache-"))
    cache.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="at-spelling-build-"))
    try:
        jdk_zip = fetch(manifest["jdk"], cache)
        lt_zip = fetch(manifest["languagetool"], cache)

        with tarfile.open(jdk_zip, "r:gz") as archive:
            archive.extractall(work / "jdk", filter="data")
        jdk = next((work / "jdk").iterdir())
        with zipfile.ZipFile(lt_zip) as archive:
            archive.extractall(work / "lt")
        lt = next((work / "lt").iterdir())

        subprocess.run(
            [str(jdk / "bin" / "jlink"), "--add-modules", MODULES, "--strip-debug",
             "--no-header-files", "--no-man-pages", "--compress=zip-9",
             "--output", str(work / "jre")],
            check=True,
        )
        trim_languagetool(lt)

        FOLDER.mkdir(parents=True, exist_ok=True)
        payload = FOLDER / manifest["payload"]["file"]
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as archive:
            add_tree(archive, work / "jre", "jre")
            add_tree(archive, lt, "languagetool")
        payload.write_bytes(lzma.compress(raw.getvalue(), preset=9 | lzma.PRESET_EXTREME))
        manifest["payload"]["sha256"] = sha256(payload)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"{payload.name}: {payload.stat().st_size} bytes, sha256 {manifest['payload']['sha256']}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
