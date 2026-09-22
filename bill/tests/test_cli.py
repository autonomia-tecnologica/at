"""Dispatch: which word reaches what, and what an unknown one costs.

`bill` with no word opens a window, so it is the one path these tests leave
alone — a suite that can pop a window is a suite that hangs on a build machine.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from bill import __version__, i18n
from bill.core import boot
from bill.ui.cli import main, tree


class Dispatch(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"BILL_ROOT": str(Path(self.scratch.name)), "BILL_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def run_words(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(words))
        return code, output.getvalue()

    def test_help_offers_every_word_it_dispatches(self):
        code, text = self.run_words("help")
        self.assertEqual(code, 0)
        for node in tree.roots():
            self.assertIn(node.name, text)

    def test_version_answers_with_the_packaged_version(self):
        code, text = self.run_words("version")
        self.assertEqual(code, 0)
        self.assertIn(__version__, text)

    def test_an_unknown_word_is_a_usage_error(self):
        code, text = self.run_words("nowhere")
        self.assertEqual(code, 2)
        self.assertIn("nowhere", text)

    def test_a_word_that_takes_no_argument_says_so(self):
        code, _ = self.run_words("help", "extra")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
