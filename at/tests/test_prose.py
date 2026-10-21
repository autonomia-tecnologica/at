"""The prose layer: what a file there is, and what may be done to it.

The rules that matter are the two doors asking the SAME question — a file the
reader shows has to be a file the writer takes, or the page offers an edit that
can never land.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from at.core import files
from at.prose import listing as prose


class TheDoor(unittest.TestCase):
    """A name is never JOINED as a path: what escapes `prose/` is refused before
    the disk is touched."""

    def test_a_name_that_escapes_is_refused(self):
        for name in ("../fora.md", "a/../../fora.md", "/etc/passwd", "a/\\b.md",
                     "", ".", "..", ".escondido/x.md", "a/.b/c.md"):
            self.assertIsNone(prose.inside(name), name)

    def test_a_name_inside_is_answered(self):
        self.assertEqual(prose.inside("nota.md"), prose.root() / "nota.md")
        self.assertEqual(prose.inside("sub/nota.md"), prose.root() / "sub" / "nota.md")


class TheReading(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"AT_ROOT": self.scratch.name})
        self.env.start()
        (prose.root() / "sub").mkdir(parents=True)
        (prose.root() / "nota.md").write_text("# oi\n", encoding="utf-8")
        (prose.root() / "sub" / "codigo.py").write_text("print(1)\n", encoding="utf-8")
        (prose.root() / ".escondido.md").write_text("shh\n", encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.scratch.cleanup()

    def test_the_tree_is_the_files_relative_to_the_folder(self):
        self.assertEqual(prose.listed(), ["nota.md", "sub/codigo.py"])

    def test_a_hidden_segment_is_not_offered(self):
        self.assertNotIn(".escondido.md", prose.listed())

    def test_the_bucket_is_the_tables_word_not_the_browser_s(self):
        self.assertEqual(prose.bucket("a.py"), "code")
        self.assertEqual(prose.bucket("a.md"), "text")
        self.assertEqual(prose.bucket("a.jsonl"), "data")
        self.assertEqual(prose.bucket("a.png"), "image")
        self.assertEqual(prose.bucket("a.zip"), "other")

    def test_the_kind_asks_the_name_before_the_suffix(self):
        self.assertEqual(prose.kind("Dockerfile", b"FROM x"), "dockerfile")
        self.assertEqual(prose.kind("a.md", b"# x"), "markdown")
        self.assertEqual(prose.kind("script", b"#!/usr/bin/env python3\n"), "python")

    def test_an_image_is_its_own_kind_and_bucket_regardless_of_bytes(self):
        # PNG bytes carry a NUL early — `is_text` would call it binary, and the
        # extension is what says otherwise (TASK-167).
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif"):
            with self.subTest(ext=ext):
                self.assertEqual(prose.kind("a" + ext, b"\x89PNG\0\0\0"), "image")
                self.assertEqual(prose.bucket("a" + ext), "image")

    def test_a_binary_that_is_neither_text_nor_image_is_not_supported(self):
        (prose.root() / "bin").write_bytes(b"a\0b")
        answer = prose.read("bin")
        self.assertFalse(answer["writable"])
        self.assertIsNone(answer["text"])
        self.assertEqual(answer["reason"], "prose.not_supported")

    def test_an_image_is_not_writable_but_carries_no_refusal_reason(self):
        (prose.root() / "foto.png").write_bytes(b"\x89PNG\0\0\0resto de bytes")
        answer = prose.read("foto.png")
        self.assertEqual(answer["kind"], "image")
        self.assertEqual(answer["bucket"], "image")
        self.assertFalse(answer["writable"])
        self.assertIsNone(answer["text"])
        self.assertIsNone(answer["reason"])
        self.assertEqual(answer["open"], "image")


class TheOpening(unittest.TestCase):
    """O QUE A PÁGINA FAZ COM O ARQUIVO — e o que ela NÃO carrega.

    A regra MAIOR é o teto da ABERTURA (`MAX_OPEN_BYTES`): acima dele o
    arquivo não abre no navegador de jeito nenhum, e a página diz que bateu no
    limite e oferece o download.
    """

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"AT_ROOT": self.scratch.name})
        self.env.start()
        (prose.root()).mkdir(parents=True)

    def tearDown(self):
        self.env.stop()
        self.scratch.cleanup()

    def test_a_markdown_over_the_edit_ceiling_opens_in_reading(self):
        # Acima de `MAX_FILE_BYTES` (a porta do EDIT) e abaixo de
        # `MAX_OPEN_BYTES` (a porta da ABERTURA): abre, e não se escreve.
        (prose.root() / "nota.md").write_text(
            "a" * (prose.MAX_FILE_BYTES + 1), encoding="utf-8")
        answer = prose.read("nota.md")
        self.assertEqual(answer["open"], "text")
        self.assertIsNotNone(answer["text"])
        self.assertFalse(answer["writable"])
        self.assertIsNone(answer["reason"])

    def test_a_file_over_the_open_ceiling_does_not_open(self):
        where = prose.root() / "grande.md"
        with where.open("wb") as handle:
            handle.truncate(prose.MAX_OPEN_BYTES + 1)
        answer = prose.read("grande.md")
        self.assertEqual(answer["open"], "download")
        self.assertIsNone(answer["text"])
        self.assertEqual(answer["reason"], "prose.over_limit")
        self.assertFalse(answer["writable"])

    def test_a_file_over_the_open_ceiling_is_never_read_whole(self):
        # The answer above is not enough: the file must NOT be loaded to be
        # refused — a 1,47 GB `.txt` read at once is the very thing this is
        # about.
        where = prose.root() / "grande.md"
        with where.open("wb") as handle:
            handle.truncate(prose.MAX_OPEN_BYTES + 1)
        with mock.patch.object(Path, "read_bytes",
                               side_effect=AssertionError("read the whole file")):
            answer = prose.read("grande.md")
        self.assertEqual(answer["open"], "download")

    def test_a_pdf_and_a_video_open_in_a_new_tab(self):
        (prose.root() / "nota.pdf").write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
        (prose.root() / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42resto")
        for name in ("nota.pdf", "clip.mp4"):
            with self.subTest(name=name):
                answer = prose.read(name)
                self.assertEqual(answer["open"], "tab")
                self.assertIsNone(answer["text"])
                self.assertIsNone(answer["reason"])

    def test_a_zip_and_a_strange_video_are_a_download(self):
        (prose.root() / "pacote.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 20)
        (prose.root() / "clip.mkv").write_bytes(b"\x1a\x45\xdf\xa3" + b"\x00" * 20)
        for name in ("pacote.zip", "clip.mkv"):
            with self.subTest(name=name):
                answer = prose.read(name)
                self.assertEqual(answer["open"], "download")
                self.assertEqual(answer["reason"], "prose.not_supported")


class TheWriting(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"AT_ROOT": self.scratch.name})
        self.env.start()
        (prose.root()).mkdir(parents=True)
        self.where = prose.root() / "nota.md"
        self.where.write_text("primeiro\n", encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.scratch.cleanup()

    def test_a_write_with_the_revision_it_read_lands(self):
        base = prose.read("nota.md")["rev"]
        status, answer = prose.write("nota.md", "segundo\n", base)
        self.assertEqual(status, 200)
        self.assertEqual(self.where.read_text(encoding="utf-8"), "segundo\n")
        # The revision comes BACK from the disk, so the page compares against the
        # file and not against what it sent.
        self.assertEqual(answer["rev"], prose.read("nota.md")["rev"])

    def test_a_write_against_a_stale_revision_is_refused_and_says_the_new_one(self):
        status, answer = prose.write("nota.md", "atropelo\n", "revisao-velha")
        self.assertEqual(status, 409)
        self.assertEqual(answer["rev"], prose.read("nota.md")["rev"])
        self.assertEqual(self.where.read_text(encoding="utf-8"), "primeiro\n")

    def test_an_empty_write_is_refused(self):
        # It is how a buffer that failed to load would save itself over a file.
        status, _ = prose.write("nota.md", "", prose.read("nota.md")["rev"])
        self.assertEqual(status, 400)
        self.assertEqual(self.where.read_text(encoding="utf-8"), "primeiro\n")

    def test_a_path_outside_the_folder_is_refused(self):
        status, _ = prose.write("../fora.md", "x", "")
        self.assertEqual(status, 404)

    def test_a_file_over_the_ceiling_is_refused(self):
        (prose.root() / "grande.md").write_text(
            "a" * (prose.MAX_FILE_BYTES + 1), encoding="utf-8")
        status, _ = prose.write("grande.md", "curto\n", prose.read("grande.md")["rev"])
        self.assertEqual(status, 413)

    def test_the_read_only_switch_refuses_before_writing(self):
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            status, answer = prose.write("nota.md", "x\n", prose.read("nota.md")["rev"])
        self.assertEqual(status, 403)
        self.assertEqual(answer["error"], "prose.read_only")
        self.assertEqual(self.where.read_text(encoding="utf-8"), "primeiro\n")


class TheCrud(unittest.TestCase):
    """Create, rename, delete (TASK-120, fatia 5/7) — the same door `write`
    already walks (`inside`, `files.guard`), never a rule of their own."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"AT_ROOT": self.scratch.name})
        self.env.start()
        (prose.root()).mkdir(parents=True)
        self.where = prose.root() / "nota.md"
        self.where.write_text("primeiro\n", encoding="utf-8")

    def tearDown(self):
        self.env.stop()
        self.scratch.cleanup()

    def test_a_file_is_created_empty(self):
        status, answer = prose.create("nova.md", False)
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nova.md")
        self.assertEqual((prose.root() / "nova.md").read_text(encoding="utf-8"), "")

    def test_a_folder_is_created(self):
        status, _ = prose.create("sub", True)
        self.assertEqual(status, 200)
        self.assertTrue((prose.root() / "sub").is_dir())

    def test_creating_over_a_taken_name_is_refused(self):
        status, answer = prose.create("nota.md", False)
        self.assertEqual(status, 409)
        self.assertEqual(answer["error"], "prose.exists")
        self.assertEqual(self.where.read_text(encoding="utf-8"), "primeiro\n")

    def test_a_name_that_escapes_is_refused(self):
        status, answer = prose.create("../fora.md", False)
        self.assertEqual(status, 400)
        self.assertEqual(answer["error"], "prose.invalid_name")

    def test_a_file_is_renamed(self):
        status, answer = prose.rename("nota.md", "nova.md")
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nova.md")
        self.assertFalse(self.where.exists())
        self.assertEqual((prose.root() / "nova.md").read_text(encoding="utf-8"), "primeiro\n")

    def test_renaming_onto_a_taken_name_is_refused(self):
        (prose.root() / "outra.md").write_text("x", encoding="utf-8")
        status, answer = prose.rename("nota.md", "outra.md")
        self.assertEqual(status, 409)
        self.assertEqual(answer["error"], "prose.exists")
        self.assertTrue(self.where.exists())

    def test_renaming_what_does_not_exist_is_refused(self):
        status, answer = prose.rename("nao-existe.md", "nova.md")
        self.assertEqual(status, 404)
        self.assertEqual(answer["error"], "prose.not_served")

    def test_a_file_is_deleted(self):
        status, answer = prose.delete("nota.md")
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nota.md")
        self.assertFalse(self.where.exists())

    def test_a_folder_is_deleted_whole(self):
        (prose.root() / "sub").mkdir()
        (prose.root() / "sub" / "dentro.md").write_text("x", encoding="utf-8")
        status, _ = prose.delete("sub")
        self.assertEqual(status, 200)
        self.assertFalse((prose.root() / "sub").exists())

    def test_deleting_what_does_not_exist_is_refused(self):
        status, answer = prose.delete("nao-existe.md")
        self.assertEqual(status, 404)
        self.assertEqual(answer["error"], "prose.not_served")

    def test_the_read_only_switch_refuses_create_rename_and_delete(self):
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            status, answer = prose.create("nova.md", False)
            self.assertEqual(status, 403)
            self.assertEqual(answer["error"], "prose.read_only")
            status, answer = prose.rename("nota.md", "nova.md")
            self.assertEqual(status, 403)
            self.assertEqual(answer["error"], "prose.read_only")
            status, answer = prose.delete("nota.md")
            self.assertEqual(status, 403)
            self.assertEqual(answer["error"], "prose.read_only")
        self.assertTrue(self.where.exists())
        self.assertFalse((prose.root() / "nova.md").exists())


class TheCeiling(unittest.TestCase):
    def test_a_nul_byte_in_the_head_makes_it_a_binary(self):
        self.assertTrue(prose.is_text(b"texto comum"))
        self.assertFalse(prose.is_text(b"a\x00b"))
        # The head is what is looked at: a NUL far inside is not read.
        self.assertTrue(prose.is_text(b"a" * 5000 + b"\x00"))

    def test_the_size_is_not_part_of_being_text(self):
        # A markdown of 300 KB is TEXT — it opens and it is not edited here.
        # The size has its own question, and the two ceilings are two.
        self.assertTrue(prose.is_text(b"a" * prose.MAX_FILE_BYTES))
        self.assertTrue(prose.is_text(b"a" * (prose.MAX_FILE_BYTES + 1)))
        self.assertLess(prose.MAX_FILE_BYTES, prose.MAX_OPEN_BYTES)


class TheModel(unittest.TestCase):
    def test_the_writer_is_the_single_writer(self):
        # A prose write goes through the one door every other write goes through,
        # so `$AT_READONLY` covers it without a rule of its own.
        self.assertTrue(hasattr(files, "atomic_write_text"))
        self.assertIs(prose.files.atomic_write_text, files.atomic_write_text)


if __name__ == "__main__":
    unittest.main()
