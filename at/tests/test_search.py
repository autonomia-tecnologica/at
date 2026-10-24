"""The global search (B-21, fatia 1/3): the engine and `at-cli search`.

No network and no model. Each test has its own Working Folder in a scratch
directory, so what one writes is never what another finds.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, paths, search, tables
from at.ui.cli import main


class Search(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(Path(self.scratch.name)), "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def put(self, name: str, data: bytes | str) -> Path:
        where = paths.prose_dir() / name
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
        return where

    def run_words(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(words))
        return code, output.getvalue()


class TheEngine(Search):
    def test_a_file_is_found_by_its_name(self):
        self.put("Receitas/bolo-de-cenoura.md", "outra coisa")
        hits = search.search("CENOURA")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["kind"], "file")
        self.assertEqual(hits[0]["id"], "Receitas/bolo-de-cenoura.md")
        self.assertEqual(hits[0]["field"], "name")

    def test_a_text_file_is_found_by_its_content_with_the_line(self):
        self.put("nota.md", "primeira\nsegunda tem a Palavra rara\nterceira")
        hits = search.search("palavra rara")
        self.assertEqual([(h["field"], h["line"]) for h in hits], [("content", 2)])
        self.assertIn("Palavra rara", hits[0]["snippet"])

    def test_a_binary_is_not_read(self):
        self.put("dado.bin", b"\0\0segredo\0")
        self.assertEqual(search.search("segredo"), [])

    def test_a_file_over_the_ceiling_is_found_by_name_only(self):
        self.put("grande.txt", "agulha" + "x" * (search.MAX_CONTENT_BYTES + 1))
        hits = search.search("agulha")
        self.assertEqual(hits, [])
        self.assertEqual(len(search.search("grande")), 1)

    def test_a_hidden_file_is_not_searched(self):
        self.put(".oculto/nota.md", "tesouro")
        self.assertEqual(search.search("tesouro"), [])

    def test_an_empty_term_finds_nothing(self):
        self.put("nota.md", "algo")
        self.assertEqual(search.search("   "), [])

    def test_the_limit_caps_the_hits(self):
        self.put("a.md", "x\nx\nx\nx")
        self.assertEqual(len(search.search("x", limit=2)), 2)

    def test_a_searchable_field_of_a_row_is_found(self):
        with redirect_stdout(io.StringIO()):
            tables.create("note", {"text": "lembrar do guarda-chuva"})
        hits = [h for h in search.search("guarda-chuva") if h["kind"] == "row"]
        self.assertEqual(len(hits), 1)
        self.assertEqual((hits[0]["where"], hits[0]["field"]), ("note", "text"))
        self.assertTrue(hits[0]["id"].upper().endswith("-1"))

    def test_a_field_that_is_not_searchable_is_not_read(self):
        self.assertNotIn("nonexistent", search.searchable("note"))
        self.assertIn("text", search.searchable("note"))

    def test_an_opaque_field_never_answers(self):
        for declared in __import__("at.data.schema", fromlist=["x"]).declared():
            table = str(declared["id"])
            for name in search.searchable(table):
                self.assertIsNone(tables.opaque(table, name))


class TheWord(Search):
    def test_it_prints_the_hits_and_exits_zero(self):
        self.put("nota.md", "uma agulha no palheiro")
        code, text = self.run_words("search", "agulha")
        self.assertEqual(code, 0)
        self.assertIn("nota.md:1", text)

    def test_nothing_found_is_not_a_failure(self):
        code, text = self.run_words("search", "inexistente")
        self.assertEqual(code, 0)
        self.assertIn("inexistente", text)

    def test_the_term_is_one_argument(self):
        self.assertEqual(self.run_words("search")[0], 2)
        self.assertEqual(self.run_words("search", "a", "b")[0], 2)

    def test_json_carries_the_hits(self):
        self.put("nota.md", "uma agulha")
        code, text = self.run_words("search", "agulha", "--json")
        body = json.loads(text)
        self.assertEqual(code, 0)
        self.assertEqual(body["hits"][0]["id"], "nota.md")

    def test_the_help_offers_the_word(self):
        self.assertIn("search", self.run_words("help")[1])


if __name__ == "__main__":
    unittest.main()
