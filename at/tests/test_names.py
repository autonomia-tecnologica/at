"""The names, held where a rename can quietly come apart.

Item 29 renames the product, and it decides two things no other test would
notice:

1. **the file each artifact IS** — `at-cli` on Linux and macOS, `at-cli.exe` on Windows,
   and the deploy wears the same pair. The rule lives in `at/core/paths.py`, the
   two specs spell it themselves (a spec runs before the package is importable)
   and §7c's WebApp container RUNS the app's file, by that name, through the
   folder it mounts. A build that named another file would be a container that
   never starts, and the failure would land at the far end of a switch, as a
   `No such file`. So the three are held to each other here.
2. **the retired spelling answers nowhere** — not an alias, not a second
   spelling, not preserved anywhere. The ONE reader that stays is
   `paths.instance_dir()`, which keeps finding `.bill/` on somebody's disk so an
   unmigrated instance can be recognised at all, and the gate says exactly that:
   the old spelling may appear preceded by a dot and by nothing else.

The scan is the code that ships and the files that build it — the two packages,
the two specs and the metadata. The documents have their own gate (`test_docs`),
and so do the sentences a person reads (`test_i18n`).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from at.core import paths

ROOT = Path(__file__).resolve().parents[2]

# The retired brand, built from parts on purpose: this module has to NAME it to
# forbid it, and a literal here would be the one file the gate could not scan
# without finding itself.
RETIRED = "B" + "ILL"

# What the gate reads: the two packages as they ship (their suites are not the
# product), the two specs and the metadata that names the package, the entry
# points and the payloads.
PACKAGES = ("at", "at_deploy")
EXTRA = ("at-cli.spec", "at-deploy.spec", "pyproject.toml")

# The three that are not the product: the suites (their own gate reads them), the
# vendored dependencies and the two DERIVED folders — `dist/` is what the build
# writes out of `src/`, and neither is checked into the repository.
SKIP = {"tests", "__pycache__", "node_modules", "dist"}


def sources() -> list[Path]:
    """Every file the product ships, or builds itself with."""
    found = [ROOT / name for name in EXTRA]
    for package in PACKAGES:
        found += [
            path for path in (ROOT / package).rglob("*")
            if path.is_file()
            and not SKIP.intersection(path.parts)
            and path.suffix in (".py", ".json")
        ]
    return sorted(found)


def bare(line: str) -> str | None:
    """The retired name used as a name, or `None`.

    A dot in front clears it: `.bill` is the retired instance FOLDER, which is
    the one reader that stays and is not the retired name. And an ordinary word
    that merely carries the letters — `billion` — is cleared too, by the letter
    that follows it; the product's code has none, and this is what keeps the gate
    honest if one day it has.
    """
    lowered = line.lower()
    needle = RETIRED.lower()
    at = lowered.find(needle)
    while at != -1:
        before = line[at - 1] if at else ""
        after = line[at + len(needle):at + len(needle) + 1]
        if before != "." and not (line[at:at + len(needle)].islower() and after.islower()):
            return line.strip()[:160]
        at = lowered.find(needle, at + 1)
    return None


class TheFileEachArtifactIs(unittest.TestCase):
    """§3, items 28 and 29: the pair is a rule of the FILE, and the runtime
    depends on it — and the app's name is one the machine did not already have."""

    def test_the_two_artifacts_are_not_the_same_file(self):
        self.assertNotEqual(paths.artifact_file(), paths.deploy_file())

    def test_the_extension_is_the_platforms(self):
        # `.exe` on Windows, and NO extension on Linux and macOS — where the
        # file's name is the command and the two are the same word. `.app` was
        # refused: on the Mac it is a BUNDLE, a folder, and the product promises
        # ONE file (§3).
        import sys

        if sys.platform == "win32":
            for name in (paths.artifact_file(), paths.deploy_file()):
                with self.subTest(file=name):
                    self.assertTrue(name.endswith(paths.WINDOWS))
        else:
            for name in (paths.artifact_file(), paths.deploy_file()):
                with self.subTest(file=name):
                    self.assertNotIn(".", name)

    def test_the_command_is_not_a_name_a_unix_machine_already_answers(self):
        # Item 28's whole reason, read off the declaration: `at` is the job
        # scheduler, one package away in this very distribution, and the
        # command is therefore NOT `at`. The gate stays a property of the SOURCE
        # and never asks the machine's PATH — what answers there is the running
        # machine's business, and the install is the door that reads it.
        self.assertEqual(paths.UNIX, "")
        self.assertNotEqual(paths.artifact_file(), "at")
        self.assertNotEqual(paths.ARTIFACT, "at")
        self.assertNotIn("-deploy", paths.ARTIFACT)

    def test_each_spec_names_the_file_of_its_artifact(self):
        # Both spellings, and not only the host's: a spec is what a release on
        # another platform runs, and that branch never executes here.
        for name, artifact in (("at-cli.spec", paths.ARTIFACT),
                               ("at-deploy.spec", paths.DEPLOY)):
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(spec=name):
                self.assertIn(f'"{artifact}{paths.WINDOWS}"', text)
                self.assertIn(f'"{artifact}{paths.UNIX}"', text)
                self.assertIn("name=NAME", text)

    def test_the_container_runs_the_file_paths_names(self):
        # §7c: the WebApp container executes the app's own artifact, by the name
        # this module just held the specs to.
        from at_deploy import environment

        self.assertTrue(environment.binary().endswith(paths.artifact_file()))


class TheRetiredNameDoesNotAnswer(unittest.TestCase):
    """Item 29: no alias, no second spelling, and nothing preserved."""

    def test_the_old_spelling_is_never_named(self):
        for path in sources():
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                found = bare(line)
                with self.subTest(source=path.relative_to(ROOT), line=number):
                    self.assertIsNone(
                        found,
                        f"{path.relative_to(ROOT)}:{number} names the retired "
                        f"spelling — «{found}». `at-cli` is the command and `AT` is "
                        f"the brand; the only reader that stays is "
                        f"`paths.instance_dir()`, which finds `.bill/`, preceded by "
                        f"a dot and by nothing else",
                    )


if __name__ == "__main__":
    unittest.main()
