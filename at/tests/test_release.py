"""The release's floor: the measurement, and the gate that reads it.

The release's portability is not a property of the code — it is a property of
where the release was built — so what the suite can hold is the instrument: the
reading of what a binary NEEDS, the reading of what a bundle CARRIES, and the
comparison that refuses a release which went past what it declared.

The trap is here too, and it is the one that cost a session: `objdump -T` lists
what a file defines AND what it needs, and the two read the same on the page.
Taking a library's own `GLIBC_2.44` for a requirement is how the machine that
built the artifact gets mistaken for the floor the artifact demands.
"""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from release import build, floor

# A REAL `objdump -T` of a machine whose glibc publishes `cosh` as an IFUNC: the
# versioned `UND` entries are what the object asks for, and the `g DF .text`
# ones are what the libm it linked against gives back. `cosh` and `sinh` appear
# on both sides, and only one side is a requirement.
LISTING = """\
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.2.5) memcpy
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.35) pthread_cond_wait
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.44) cosh
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.44) sinh
0000000000015d40 g    DF .text	0000000000000079  GLIBC_2.2.5  cosh
00000000000654d0 g   iD  .text	000000000000002e  GLIBC_2.44  cosh
0000000000065500 g   iD  .text	000000000000002e  GLIBC_2.44  sinh
"""

# The same file, built where the libm has no such IFUNC — which is the whole
# difference between a release that runs on a Debian and one that does not.
OLD_LISTING = """\
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.2.5) cosh
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.2.5) sinh
0000000000000000      DF *UND*	0000000000000000 (GLIBC_2.35) pthread_cond_wait
"""


class TheReading(unittest.TestCase):
    """What a binary NEEDS — and never what it gives."""

    def test_a_file_that_needs_nothing_versioned_answers_nothing(self):
        self.assertIsNone(floor.needed("0000 g DF .text 0000 GLIBC_2.44 cosh\n"))

    def test_the_highest_requirement_is_the_floor(self):
        self.assertEqual(floor.needed(LISTING), (2, 44))
        self.assertEqual(floor.needed(OLD_LISTING), (2, 35))

    def test_what_the_file_publishes_is_not_what_it_needs(self):
        # O defeito que isto tranca: as linhas DEFINIDAS trazem 2.44, e lê-las
        # como exigência é como a glibc da máquina de build vira o piso do
        # artefato. Só `*UND*` é exigência.
        published = "0000 g iD .text 0000 GLIBC_2.44 cosh\n"
        self.assertIsNone(floor.needed(published))
        mixed = published + "0000 DF *UND* 0000 (GLIBC_2.2.5) memcpy\n"
        self.assertEqual(floor.needed(mixed), (2, 2))

    def test_a_version_that_is_not_a_version_is_refused(self):
        for bad in ("", "2", "x.y", "2.35.1"):
            with self.subTest(bad=bad):
                with self.assertRaises(floor.FloorError):
                    floor.parse(bad)
        self.assertEqual(floor.parse("2.35"), (2, 35))
        self.assertEqual(floor.shown((2, 35)), "2.35")


class TheBundle(unittest.TestCase):
    """What the artifact CARRIES, read off the manifest the build wrote."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.elf = self.root / "libpython.so"
        self.elf.write_bytes(b"\x7fELF")
        self.data = self.root / "blocks.json"
        self.data.write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.scratch.cleanup()

    def manifest(self, entries) -> Path:
        """The manifest as the build writes it — ELEVEN fields, the entries
        among them. The shape is the real one on purpose: a fixture written to
        the reader's convenience is a test that agrees with the bug."""
        where = self.root / floor.MANIFEST
        where.write_text(
            repr(("pkg", {}, list(entries), "libpython.so", False, False, False,
                  [], None, None, None)),
            encoding="utf-8",
        )
        return where

    def test_only_the_things_that_can_link_are_measured(self):
        where = self.manifest([
            ("libpython.so", str(self.elf), "BINARY"),
            ("block", str(self.data), "DATA"),
            ("a.py", "/nowhere/a.py", "PYSOURCE"),
            ("pyi-contents-directory _internal", "", "OPTION"),
        ])
        self.assertEqual(floor.pieces(where), [self.elf])

    def test_the_promise_is_about_what_the_bundle_is_made_of(self):
        # O defeito que isto tranca: a promessa era conferida contra o que LIGA,
        # e os avisos dos terceiros são DADOS — um release que perdesse um
        # `LICENSE` passava pelo portão em silêncio. `pieces` continua sendo o
        # que o piso mede; `carried` é o que o artefato É.
        where = self.manifest([
            ("libpython.so", str(self.elf), "BINARY"),
            ("LICENSE.txt", str(self.data), "DATA"),
        ])
        self.assertEqual(floor.pieces(where), [self.elf])
        self.assertEqual(floor.carried(where), [self.elf, self.data])

    def test_a_manifest_nobody_can_read_is_an_error_and_not_a_pass(self):
        where = self.root / floor.MANIFEST
        where.write_text("não é um manifesto\n", encoding="utf-8")
        with self.assertRaises(floor.FloorError):
            floor.pieces(where)

    def test_a_machine_with_no_objdump_says_what_is_owed(self):
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(floor.FloorError) as caught:
                floor.measure([self.elf])
        self.assertIn("binutils", str(caught.exception))


class TheGate(unittest.TestCase):
    """The comparison: a release that went past what it declared does not leave."""

    def bundle(self, name: str, entries) -> Path:
        where = self.root / name
        where.mkdir(parents=True, exist_ok=True)
        (where / floor.MANIFEST).write_text(repr(("pkg", {}, entries)), encoding="utf-8")
        return where

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.elf = self.root / "pc.so"
        self.elf.write_bytes(b"\x7fELF")

    def tearDown(self):
        self.scratch.cleanup()

    def measure(self, version):
        return {self.elf: version}

    def held(self, measured, ceiling) -> bool:
        with mock.patch.object(floor, "measure", lambda paths: measured):
            return bool(floor.report(self.root, ceiling, out=io.StringIO()))

    def test_a_release_that_holds_the_floor_says_so(self):
        self.bundle("at-cli", [("pc.so", str(self.elf), "EXTENSION")])
        self.assertTrue(self.held(self.measure((2, 35)), (2, 35)))

    def test_a_release_that_went_past_does_not(self):
        self.bundle("at-cli", [("pc.so", str(self.elf), "EXTENSION")])
        self.assertFalse(self.held(self.measure((2, 44)), (2, 35)))
        self.assertEqual(floor.past(self.measure((2, 44)), (2, 35)), [(self.elf, (2, 44))])
        self.assertEqual(floor.past(self.measure((2, 35)), (2, 35)), [])

    def test_a_bundle_nobody_could_measure_fails_the_gate(self):
        # Medir nada não é não haver o que temer: um bundle que ninguém leu é um
        # bundle que ninguém provou, e o portão não passa o que não foi provado.
        self.bundle("at-deploy", [("a.py", "/nowhere/a.py", "PYSOURCE")])
        self.assertFalse(self.held({}, (2, 35)))

    def test_what_the_release_promises_to_carry_is_checked(self):
        # O defeito que isto tranca, medido: um builder sem Tk produziu um
        # `at-deploy` treze megabytes mais leve, SEM o runtime do próprio Wizard
        # — e nada disse. Uma promessa que ninguém confere é uma promessa que se
        # perde em silêncio.
        carried = [Path("/x/libtk8.6.so"), Path("/x/libpython3.14.so.1.0")]
        self.assertEqual(floor.missing(carried, ["libtcl", "libtk"]), ["libtcl"])
        self.assertEqual(floor.missing(carried, ["libtcl"]), ["libtcl"])
        self.assertEqual(floor.missing([Path("/x/libtcl8.6.so")], ["libtcl"]), [])

    def test_a_missing_payload_fails_the_gate_and_says_which(self):
        self.bundle("at-cli", [("pc.so", str(self.elf), "EXTENSION")])
        with mock.patch.object(floor, "measure", lambda paths: {}):
            held = floor.report(self.root, (2, 35), out=io.StringIO(),
                                wanted={"at-cli": ["libtcl"]})
        self.assertFalse(held)

    def test_each_artifact_promises_its_own_payload(self):
        # Os dois specs não prometem a mesma coisa: `at-deploy` nomeia `tkinter`
        # (`hiddenimports`) pelo Wizard que carrega sem chamar, e `at-cli` não
        # carrega Tk nenhum. Uma promessa só, para os dois, acusaria o errado.
        self.bundle("at-cli", [("pc.so", str(self.elf), "EXTENSION")])
        with mock.patch.object(floor, "measure",
                               lambda paths: {self.elf: (2, 35)}):
            held = floor.report(self.root, (2, 35), out=io.StringIO(),
                                wanted={"at-deploy": ["libtcl"]})
        self.assertTrue(held)

    def test_a_notice_the_release_promised_and_lost_fails_the_gate(self):
        # §3: o que a licença de um terceiro exige viaja com ele, e o release
        # promete os avisos. Distribuir o trabalho de alguém sem os termos dele
        # é o defeito que isto tranca — e ele é de DADO, não de binário.
        notice = self.root / "LICENSE.txt"
        notice.write_text("MIT", encoding="utf-8")
        self.bundle("at-cli", [
            ("pc.so", str(self.elf), "EXTENSION"),
            ("LICENSE.txt", str(notice), "DATA"),
        ])
        with mock.patch.object(floor, "measure", lambda paths: {self.elf: (2, 35)}):
            kept = floor.report(self.root, (2, 35), out=io.StringIO(),
                                wanted={"at-cli": ["LICENSE.txt"]})
            lost = floor.report(self.root, (2, 35), out=io.StringIO(),
                                wanted={"at-cli": ["COPYING.txt"]})
        self.assertTrue(kept)
        self.assertFalse(lost)

    def test_the_command_refuses_a_floor_that_is_not_one(self):
        # A medida é lida da DECLARAÇÃO e não da linha de comando: uma versão
        # digitada em dois lugares é uma versão que discorda de si mesma.
        with redirect_stdout(io.StringIO()):
            self.assertEqual(floor.main([]), 2)
            self.assertEqual(floor.main([".", "--floor", "2.35"]), 2)


class TheDeclaration(unittest.TestCase):
    """`builder.json`: a máquina, pinada como qualquer dependência externa."""

    def declared(self) -> dict:
        return json.loads(build.DECLARED.read_text(encoding="utf-8"))

    def test_the_builder_is_pinned_in_version_and_hashing(self):
        # §3: "Dependências de pacotes e imagens são fixadas em versão e
        # hashing". Uma tag se move; o digest não.
        builder = self.declared()["builder"]
        self.assertTrue(builder["version"])
        self.assertTrue(builder["digest"].startswith("sha256:"))
        self.assertEqual(len(builder["digest"].removeprefix("sha256:")), 64)

    def test_the_floor_is_one_the_gate_can_read(self):
        self.assertEqual(floor.parse(self.declared()["floor"]), (2, 35))

    def test_the_builder_wears_the_release_s_own_specs(self):
        for spec in build.SPECS:
            with self.subTest(spec=spec):
                self.assertTrue((build.ROOT / spec).is_file())

    def test_the_gate_runs_inside_the_builder(self):
        # O manifesto nomeia os caminhos DO builder, então é lá que ele se lê.
        said = build.script(build.declared())
        self.assertIn("python3 -m release.floor build", said)
        self.assertIn("--require-hashes", said)

    def test_the_builder_installs_what_it_declares_it_needs(self):
        # Um builder sem o que o artefato coleta produz um artefato que perdeu
        # um pedaço em silêncio: o pacote vai declarado, e o script o instala.
        said = build.script(build.declared())
        self.assertIn("binutils", said)

    def test_the_release_declares_what_each_artifact_promises(self):
        # A promessa do `Tk` continua VAZIA — ele saiu de cena nos dois artefatos
        # (item 9, e o `at-deploy` junto), então o runtime do Wizard não viaja, e
        # o que não viaja não se promete. O que esta promessa passou a carregar
        # (item 27) são os AVISOS: o artefato é um arquivo só, a licença de cada
        # terceiro viaja dentro dele, e o portão recusa um release que os perdeu
        # — cada substring é um nome de arquivo que o `PKG-00.toc` tem de trazer.
        payload = self.declared()["payload"]
        self.assertEqual(sorted(payload), ["at-cli", "at-deploy"])
        for artifact in ("at-cli", "at-deploy"):
            with self.subTest(artifact=artifact):
                self.assertEqual(
                    payload[artifact],
                    ["LICENSE.md", "LICENSE.txt", "COPYING.txt", "manifest.json"],
                )


if __name__ == "__main__":
    unittest.main()
