"""The prose layer: what a file there is, and what may be done to it.

The rules that matter are the two doors asking the SAME question — a file the
reader shows has to be a file the writer takes, or the page offers an edit that
can never land.
"""

from __future__ import annotations

import os
import tempfile
import unittest
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
        self.assertEqual(prose.bucket("a.png"), "other")

    def test_the_kind_asks_the_name_before_the_suffix(self):
        self.assertEqual(prose.kind("Dockerfile", b"FROM x"), "dockerfile")
        self.assertEqual(prose.kind("a.md", b"# x"), "markdown")
        self.assertEqual(prose.kind("script", b"#!/usr/bin/env python3\n"), "python")

    def test_a_binary_is_not_text_and_says_so(self):
        (prose.root() / "bin").write_bytes(b"a\0b")
        answer = prose.read("bin")
        self.assertFalse(answer["writable"])
        self.assertIsNone(answer["text"])
        self.assertEqual(answer["reason"], "prose.not_text")


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


class TheCeiling(unittest.TestCase):
    def test_a_nul_byte_in_the_head_makes_it_a_binary(self):
        self.assertTrue(prose.is_text(b"texto comum"))
        self.assertFalse(prose.is_text(b"a\x00b"))
        # The head is what is looked at: a NUL far inside is not read.
        self.assertTrue(prose.is_text(b"a" * 5000 + b"\x00"))

    def test_the_ceiling_is_the_same_for_the_reader_and_the_writer(self):
        self.assertTrue(prose.is_text(b"a" * prose.MAX_FILE_BYTES))
        self.assertFalse(prose.is_text(b"a" * (prose.MAX_FILE_BYTES + 1)))


class TheModel(unittest.TestCase):
    def test_the_writer_is_the_single_writer(self):
        # A prose write goes through the one door every other write goes through,
        # so `$AT_READONLY` covers it without a rule of its own.
        self.assertTrue(hasattr(files, "atomic_write_text"))
        self.assertIs(prose.files.atomic_write_text, files.atomic_write_text)


if __name__ == "__main__":
    unittest.main()
