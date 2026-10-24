"""The release: build where the floor is guaranteed, and prove it held.

Run from the repository root:

    python3 -m release.build

**Why this exists at all.** Building the release is `pyinstaller <spec>`, and
running that on whatever machine is at hand makes the artifact's portability an
accident of that machine — measured, the same source built on a rolling
distribution needed `GLIBC_2.44` and would not start on a Debian a year newer
than it; built on the base `builder.json` pins, it needed `2.35` and started.
Nothing in the code differs between the two. The BUILD differs, so the build is
what has to be pinned and reproducible.

**What it does, and nothing else.** Copies the tree to a scratch directory,
runs the pinned builder over it — the two specs, with the development
requirements installed from their hashes — and hands the result to the gate
(`release.floor`) before anything comes back. What lands in `dist/` is a release
that held the floor it declared, or nothing at all.

**The scratch copy is the point of the copy.** Building inside the person's
checkout would leave root-owned `build/` and `dist/` in it; and a builder that
writes into the tree it is reading is a builder nobody can run twice.

It refuses before it starts when the WebApp's `dist/` is not there: the spec
collects it, a source that is present but EMPTY is collected as nothing in
silence, and a binary that answers `500` on the front page is a worse answer
than a build that did not happen.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from release import fetch, floor, sbom

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# The declaration has ONE home and the gate reads it too — a floor written in
# two places is a floor that disagrees with itself.
DECLARED = floor.DECLARED

# Every spec this release publishes. One release, two artifacts (§3).
SPECS = ("at-cli.spec", "at-deploy.spec")

# The WebApp's build output — the DERIVATION, which the spec needs and the
# repository does not carry.
WEBAPP = Path("at") / "ui" / "webapp" / "dist"

# What never travels into the builder: the version control, the development
# environment, the generated trees, and the harness.
ALWAYS = frozenset({
    ".git", ".venv", "node_modules", "__pycache__", ".claude", "at.egg-info",
    "build",
})

# And what only the root carries — this checkout is also a Working Folder, and
# the person's folder is not the product. `dist/` is here and not in `ALWAYS`
# because the WebApp's own `dist/` DOES travel: excluding it would leave the
# binary without a front page.
AT_THE_ROOT = frozenset({
    "dist", "Tabelas", "App", "Arquivos", "Projetos", "Compartilhada",
    "Harness", "INSTANCE.md",
})


class BuildError(Exception):
    """The release did not happen, and says why before it tries."""


def declared() -> dict:
    """`builder.json` — the machine, the floor, and what must be installed."""
    data = json.loads(DECLARED.read_text(encoding="utf-8"))
    builder = data["builder"]
    return {
        "pinned": f"{builder['repo']}@{builder['digest']}",
        "version": builder["version"],
        "packages": list(builder.get("packages") or []),
        "floor": data["floor"],
    }


def _skip(where: str, names: list[str]) -> set[str]:
    here = Path(where)
    gone = {name for name in names if name in ALWAYS}
    if here == ROOT:
        gone |= {name for name in names if name in AT_THE_ROOT}
    return gone


def script(said: dict) -> str:
    """What the builder runs: the two artifacts, and then the gate.

    **The packages are the declaration's, and they are not decoration.** A slim
    base carries `_tkinter` and NOT the Tk libraries, and PyInstaller collects
    the libraries from the machine — so a builder missing them produces an
    artifact that quietly stopped carrying its own Wizard's runtime, thirteen
    megabytes lighter, with nothing said. What the machine has to install is
    therefore said where the machine is pinned, and the gate checks the result
    against what the release PROMISES to carry (`payload`).

    The rest is the pinned development environment, installed from the hashes
    the repository already carries (`--require-hashes`), so the builder's own
    pip cannot choose a version nobody pinned.
    """
    packages = " ".join(said["packages"])
    return "\n".join([
        "set -e",
        "apt-get update -qq",
        f"apt-get install -y -qq {packages}",
        "python3 -m venv /venv",
        "/venv/bin/pip install -q --require-hashes -r requirements.txt",
        "/venv/bin/pip install -q --require-hashes -r requirements-dev.txt",
        "/venv/bin/pip install -q -e . --no-deps",
        *[f"/venv/bin/pyinstaller --noconfirm {spec}" for spec in SPECS],
        # The gate runs HERE, and it has to: the manifest names the builder's
        # own paths, so only the builder can read what it packed.
        "python3 -m release.floor build",
    ])


def main(argv: list[str] | None = None) -> int:
    if argv:
        print("usage: python3 -m release.build")
        return 2
    try:
        said = declared()
    except (OSError, KeyError, ValueError) as error:
        print(f"builder.json is not readable: {error}")
        return 1

    if shutil.which("podman") is None:
        print("podman is not on this machine, and the release is built in a container.")
        return 1
    if not (ROOT / WEBAPP).is_dir():
        print(f"{WEBAPP} is not there: the WebApp has to be built first "
              f"(`npm run build` in at/ui/webapp), and the spec collects it.")
        return 1

    # The vendored payloads are pinned by manifest and NOT versioned: they are
    # pulled here, before the copy, so the scratch tree carries all of them and
    # the specs go on embedding `at/vendor/*` exactly as before. A payload that
    # could not be had with its pinned hash is no build at all.
    try:
        fetch.fetch()
    except fetch.FetchError as error:
        print(f"The vendored payloads are not all there: {error}")
        print("Run `python3 -m release.fetch` and fix what it reports.")
        return 1
    absent = fetch.missing()
    if absent:
        print("The vendored payloads are missing after the fetch: "
              + ", ".join(f"{i['service']}/{i['file']}" for i in absent))
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="at-release-"))
    print(f"Builder: {said['pinned']} ({said['version']}), floor glibc {said['floor']}")
    print(f"Scratch: {scratch}")
    shutil.copytree(ROOT, scratch / "at", ignore=_skip, symlinks=True)
    where = scratch / "at"

    argv = [
        "podman", "run", "--rm",
        "--volume", f"{where}:/w",
        "--workdir", "/w",
        said["pinned"],
        "bash", "-lc", script(said),
    ]
    result = subprocess.run(argv)
    if result.returncode != 0:
        print("The build did not finish: nothing was published, and dist/ is what it was.")
        return result.returncode

    (ROOT / "dist").mkdir(exist_ok=True)
    published = sorted((where / "dist").iterdir())
    for built in published:
        shutil.copy2(built, ROOT / "dist" / built.name)
    # Item 46: the SBOM, beside the binaries. Every number it carries is read
    # from the checkout at ROOT — `builder.json`, the two requirements files,
    # the vendored Caddy tarball, the frontend's lock — and none of it depends
    # on the container that just ran, so it is written from the HOST.
    manifest = sbom.write(said, ROOT / "dist")
    print("Published: " + ", ".join(built.name for built in published)
          + f", {manifest.name}")
    print(f"The scratch stays in {scratch} — root owns it, and the disk is cheap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
