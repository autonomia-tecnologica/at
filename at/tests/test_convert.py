"""`at.convert`: o motor que lê um Markdown e escreve DOCX/PDF (TASK-165,
fatia 1/4).

`markdown.py`, `docx.py` e `pdf.py` são funções puras — texto entra, bytes
saem — e não precisam de `AT_ROOT` nenhum; só `TheConvertDoor`, que escreve em
`Convertidos/`, precisa de uma Pasta de Trabalho descartável.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
import xml.dom.minidom as minidom
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.convert import convert, docx, markdown, pdf
from at.core import boot, files, paths
from at.data import schema, store


class TheMarkdownParser(unittest.TestCase):
    def test_a_heading_carries_its_level(self):
        blocks = markdown.parse("# Um\n## Dois\n###### Seis")
        self.assertEqual([(b.kind, b.level) for b in blocks],
                          [("heading", 1), ("heading", 2), ("heading", 6)])

    def test_consecutive_lines_join_into_one_paragraph(self):
        blocks = markdown.parse("linha um\nlinha dois\n\nlinha três")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].runs[0].text, "linha um linha dois")
        self.assertEqual(blocks[1].runs[0].text, "linha três")

    def test_unordered_and_ordered_items_are_told_apart(self):
        blocks = markdown.parse("- a\n* b\n1. c\n2. d")
        self.assertEqual([b.kind for b in blocks], ["item"] * 4)
        self.assertEqual([b.ordered for b in blocks], [False, False, True, True])
        self.assertEqual([b.number for b in blocks], [None, None, 1, 2])

    def test_bold_and_italic_are_read_apart_from_the_plain_text_around_them(self):
        blocks = markdown.parse("um **negrito** e um *itálico* e um _também_")
        runs = blocks[0].runs
        self.assertEqual(
            [(r.text, r.bold, r.italic) for r in runs],
            [
                ("um ", False, False),
                ("negrito", True, False),
                (" e um ", False, False),
                ("itálico", False, True),
                (" e um ", False, False),
                ("também", False, True),
            ],
        )

    def test_the_marker_itself_never_survives_into_a_run(self):
        blocks = markdown.parse("**tudo em negrito**")
        self.assertEqual(blocks[0].runs, [markdown.Run("tudo em negrito", bold=True)])


class TheDocxGenerator(unittest.TestCase):
    def _document(self, text: str) -> str:
        data = docx.generate(text)
        zf = zipfile.ZipFile(io.BytesIO(data))
        self.assertEqual(
            set(zf.namelist()),
            {"[Content_Types].xml", "_rels/.rels", "word/document.xml"},
        )
        return zf.read("word/document.xml").decode("utf-8")

    def test_it_is_a_well_formed_zip_of_well_formed_xml(self):
        document = self._document("# Título\n\nUm parágrafo.")
        parsed = minidom.parseString(document)  # raises on anything malformed
        self.assertEqual(parsed.documentElement.tagName, "w:document")

    def test_a_heading_is_bold_and_bigger_than_the_body(self):
        document = self._document("# Título")
        self.assertIn("<w:b/>", document)
        self.assertIn('w:sz w:val="32"', document)
        self.assertIn("Título", document)

    def test_bold_and_italic_runs_carry_their_own_properties(self):
        document = self._document("um **negrito** e um *itálico*")
        self.assertIn("<w:b/>", document)
        self.assertIn("<w:i/>", document)
        self.assertIn(">negrito<", document)
        self.assertIn(">itálico<", document)

    def test_a_list_item_carries_a_literal_marker(self):
        document = self._document("- primeiro\n1. numerado")
        self.assertIn("•", document)
        self.assertIn("1.", document)

    def test_special_characters_are_escaped(self):
        document = self._document("a & b < c")
        self.assertIn("a &amp; b &lt; c", document)
        self.assertNotIn("a & b", document)


class ThePdfGenerator(unittest.TestCase):
    def test_it_starts_with_the_pdf_header_and_ends_with_eof(self):
        data = pdf.generate("# Título\n\nUm parágrafo.")
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))

    def test_it_declares_the_four_base_fonts(self):
        data = pdf.generate("texto qualquer")
        for name in (b"/Helvetica", b"/Helvetica-Bold", b"/Helvetica-Oblique", b"/Helvetica-BoldOblique"):
            self.assertIn(name, data)

    def test_a_long_paragraph_spills_onto_a_second_page(self):
        short = pdf.generate("uma linha só")
        long_text = "uma palavra repetida muitas vezes " * 600
        long = pdf.generate(long_text)
        # `/Type /Page /Parent` names a PAGE and not the `/Type /Pages` tree
        # (which never says `/Parent`) — the one count that will not conflate
        # the two.
        self.assertEqual(short.count(b"/Type /Page /Parent"), 1)
        self.assertGreater(long.count(b"/Type /Page /Parent"), 1)

    def test_accented_text_reaches_the_stream_as_cp1252(self):
        data = pdf.generate("café, ação, órgão")
        self.assertIn("café".encode("cp1252"), data)

    def test_the_width_table_knows_every_printable_ascii_character(self):
        for code in range(32, 127):
            self.assertIn(chr(code), pdf._HELVETICA)
            self.assertIn(chr(code), pdf._HELVETICA_BOLD)


class TheConvertDoor(unittest.TestCase):
    """`convert()`: lê um Markdown, escreve em `Convertidos/`, resolve
    colisão de nome — a única parte de fatia 1 que toca a Pasta de Trabalho."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"})
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def _source(self, name: str = "nota.md") -> Path:
        where = paths.prose_dir() / name
        where.write_text("# Título\n\nUm parágrafo.", encoding="utf-8")
        return where

    def test_an_unknown_format_is_refused(self):
        with self.assertRaises(ValueError):
            convert(self._source(), "epub")

    def test_it_writes_into_convertidos_named_after_the_source(self):
        target = convert(self._source(), "pdf")
        self.assertEqual(target, paths.convert_dir() / "nota.pdf")
        self.assertTrue(target.is_file())
        self.assertTrue(target.read_bytes().startswith(b"%PDF"))

    def test_docx_lands_in_convertidos_too(self):
        target = convert(self._source(), "docx")
        self.assertEqual(target, paths.convert_dir() / "nota.docx")
        self.assertTrue(zipfile.is_zipfile(target))

    def test_a_second_conversion_of_the_same_name_does_not_overwrite_the_first(self):
        first = convert(self._source(), "pdf")
        second = convert(self._source(), "pdf")
        self.assertEqual(second, paths.convert_dir() / "nota (1).pdf")
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())

    def test_the_write_is_counted_like_any_other_product_write(self):
        files.reset_writes()
        convert(self._source(), "pdf")
        self.assertEqual(files.writes(), 1)
