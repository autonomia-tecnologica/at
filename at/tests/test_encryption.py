"""The password derivation, and the pin that carries it (§4, item 8).

The hashed field stores a derivation, and deriving is not the standard library's
to give: this is the product's first runtime dependency. The module holds the two
halves together — the primitive's contract, and the pin — and the pin's half is
the one that fails the day `requirements.txt` and `pyproject.toml` stop naming
the same version. It also holds the closed list of files that speak to
`libsodium`, which item 14's first slice grew to two (`password` and `vault`):
the door into the library is a list somebody extends on purpose.

Nothing here touches a folder: the comparison reads its two arguments and
nothing else, which is exactly what makes a credential verifiable while the
Main Key is untyped.
"""

from __future__ import annotations

import ast
import inspect
import re
import tomllib
import unittest
from pathlib import Path

from at.encryption import password

ROOT = Path(__file__).resolve().parents[2]

# What the method fixes (§4): the interactive limits, written here as NUMBERS so
# the test is what holds the module to them, and not the other way around.
OPSLIMIT = 2
MEMLIMIT = 64 * 1024 * 1024

# The derivation's own answer names the algorithm and the price it cost:
# `$argon2id$v=19$m=65536,t=2,p=1$…`, with the memory in KiB. `v` is argon2's
# version and `p` libsodium's parallelism, neither of them the method's choice.
ANSWER = re.compile(r"^\$argon2id\$v=\d+\$m=(\d+),t=(\d+),p=\d+\$")

# `libsodium` has one door into the product, and the whole of it is the closed
# list below: `password` derives what is compared, and `vault` derives the Vault
# Key and seals what AT uses. The day a third file imports `nacl`, the cost of
# a derivation gains a place it can be changed from — and that is a decision,
# never an accident.
SPEAKS = re.compile(r"^\s*(?:import|from)\s+nacl\b", re.MULTILINE)
SPEAKERS = ("at/encryption/password.py", "at/encryption/vault.py")

PIN = ROOT / "requirements.txt"
METADATA = ROOT / "pyproject.toml"


def requirements() -> list[tuple[str, list[str]]]:
    """`requirements.txt` as logical lines: the pinned name, and its hashes."""
    logical: list[tuple[str, list[str]]] = []
    spec: str | None = None
    hashes: list[str] = []
    for line in PIN.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("--hash="):
            hashes.append(stripped)
            continue
        if spec is not None:
            logical.append((spec, hashes))
        spec, hashes = stripped.rstrip("\\").strip(), []
    if spec is not None:
        logical.append((spec, hashes))
    return logical


def pinned() -> dict[str, str]:
    """The version the pin carries, per package name."""
    return {
        spec.partition("==")[0]: spec.partition("==")[2]
        for spec, _ in requirements()
    }


def named() -> dict[str, str]:
    """The version the metadata carries, per package name."""
    with METADATA.open("rb") as handle:
        dependencies = tomllib.load(handle)["project"]["dependencies"]
    return {
        entry.partition("==")[0]: entry.partition("==")[2] for entry in dependencies
    }


class TheMethod(unittest.TestCase):
    def test_the_price_is_the_interactive_limits(self):
        self.assertEqual((password.OPSLIMIT, password.MEMLIMIT), (OPSLIMIT, MEMLIMIT))

    def test_the_answer_names_the_algorithm_and_the_cost(self):
        found = ANSWER.match(password.derive("um segredo"))
        self.assertIsNotNone(
            found, "the derivation does not answer with argon2id and its price"
        )
        memory, operations = found.group(1), found.group(2)
        self.assertEqual(int(memory), MEMLIMIT // 1024)
        self.assertEqual(int(operations), OPSLIMIT)

    def test_it_answers_a_text(self):
        self.assertIsInstance(password.derive("um segredo"), str)

    def test_two_derivations_of_one_text_are_unequal(self):
        # The salt is the library's and travels inside its own answer, so two
        # equal credentials already produce two unequal rows.
        self.assertNotEqual(password.derive("um segredo"), password.derive("um segredo"))

    def test_the_price_is_not_a_parameter(self):
        # A knob that changed the cost would be "no choice per field" with a hole
        # in it: the module fixes the price, and no caller names one.
        self.assertEqual(list(inspect.signature(password.derive).parameters), ["value"])


class TheComparison(unittest.TestCase):
    def setUp(self):
        self.stored = password.derive("um segredo")

    def test_the_right_candidate_comes_back_true(self):
        self.assertIs(password.verify("um segredo", self.stored), True)

    def test_the_wrong_candidate_comes_back_false(self):
        self.assertIs(password.verify("outro segredo", self.stored), False)

    def test_the_derivation_itself_fails_as_a_candidate(self):
        # The door compares, it does not match strings: the stored derivation
        # handed back as its own candidate derives to something else.
        self.assertIs(password.verify(self.stored, self.stored), False)

    def test_a_hand_edited_row_is_no_and_not_an_exception(self):
        for stored in ("", "nao-e-uma-derivacao", "$argon2id$v=19$m=1$xxx$yyy", None, 3):
            with self.subTest(stored=stored):
                self.assertIs(password.verify("um segredo", stored), False)

    def test_a_candidate_that_is_not_text_is_no_too(self):
        for candidate in (None, 3, b"um segredo"):
            with self.subTest(candidate=candidate):
                self.assertIs(password.verify(candidate, self.stored), False)

    def test_the_comparison_needs_nothing_but_its_two_arguments(self):
        # No Main Key, no setting, no Working Folder: the module that
        # answers reaches for no other module to answer with.
        tree = ast.parse(
            (ROOT / "at/encryption/password.py").read_text(encoding="utf-8")
        )
        reached: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                reached.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                reached.add(node.module.split(".")[0])
        self.assertEqual(reached - {"__future__"}, {"nacl"})
        self.assertEqual(
            list(inspect.signature(password.verify).parameters), ["candidate", "stored"]
        )


class ThePin(unittest.TestCase):
    def test_the_pin_and_the_metadata_name_the_same_version(self):
        # The two runtime dependencies: the libsodium binding the derivation
        # needs, and `cryptography`, whose P-256 the browser push needs.
        for name in ("PyNaCl", "cryptography"):
            with self.subTest(package=name):
                self.assertIn(name, pinned())
                self.assertIn(name, named())
                self.assertEqual(pinned()[name], named()[name])

    def test_every_package_in_the_pin_carries_a_hash(self):
        # `--require-hashes` refuses a file without one, and this file is what
        # installs at run time: what is not listed is not what gets installed.
        for spec, hashes in requirements():
            with self.subTest(package=spec):
                self.assertTrue(spec.partition("==")[2], f"{spec} is not pinned in version")
                self.assertTrue(
                    any(h.startswith("--hash=sha256:") for h in hashes),
                    f"{spec} carries no sha256 hash",
                )

    def test_the_pin_names_what_the_binding_needs(self):
        # `PyNaCl` is the reason; `cffi` and `pycparser` are what it loads
        # libsodium through, and `--require-hashes` wants every one of them here.
        self.assertLessEqual({"PyNaCl", "cffi", "pycparser"}, set(pinned()))

    def test_the_files_that_speak_to_libsodium_are_the_closed_list(self):
        # Sorted, because the filesystem hands the files over in an order of its
        # own and the list below is the declaration, not a directory listing.
        speakers = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "at").rglob("*.py")
            if "tests" not in path.parts and SPEAKS.search(path.read_text(encoding="utf-8"))
        )
        self.assertEqual(speakers, sorted(SPEAKERS))


if __name__ == "__main__":
    unittest.main()
