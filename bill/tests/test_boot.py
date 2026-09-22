"""The first run: what a folder gains, and what it does not.

Every test aims Bill at a throwaway folder with `BILL_ROOT`, so none of them
touches the checkout's own Working Folder.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from bill import i18n
from bill.core import boot, settings


class _NoTerminal:
    """A stdin that cannot be asked anything."""

    def isatty(self) -> bool:
        return False


class FirstRun(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"BILL_ROOT": str(self.root), "BILL_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def confirm(self, answer: str = "s") -> bool:
        with redirect_stdout(io.StringIO()):
            return boot.ensure_working_folder(ask=lambda question: answer)

    def test_an_empty_folder_is_not_configured(self):
        self.assertFalse(boot.is_configured())

    def test_confirming_creates_what_a_folder_is_born_with(self):
        self.assertTrue(self.confirm())
        self.assertTrue((self.root / ".bill" / "settings.json").is_file())
        self.assertTrue((self.root / ".bill" / "i18n" / "active").is_file())
        self.assertTrue((self.root / "data").is_dir())
        self.assertTrue((self.root / "prose").is_dir())
        self.assertEqual(settings.load()["schema"], settings.SCHEMA)

    def test_the_chosen_language_is_recorded_in_the_folder(self):
        self.confirm()
        recorded = (self.root / ".bill" / "i18n" / "active").read_text(encoding="utf-8")
        self.assertEqual(recorded.strip(), "pt_BR")

    def test_the_folder_decides_once_the_environment_is_silent(self):
        self.confirm()
        without_override = {
            name: value for name, value in os.environ.items() if name != i18n.LANG_ENV
        }
        with mock.patch.dict(os.environ, without_override, clear=True):
            i18n.reset()
            self.assertEqual(i18n.active_code(), "pt_BR")
            self.assertEqual(i18n.active_origin(), "folder")

    def test_the_folder_is_born_with_a_welcome_note_in_the_active_language(self):
        self.confirm()
        welcome = self.root / "prose" / i18n.tr("prose.welcome.filename")
        self.assertTrue(welcome.is_file())
        self.assertEqual(welcome.read_text(encoding="utf-8"), i18n.tr("prose.welcome.body"))

    def test_declining_writes_nothing(self):
        self.assertFalse(self.confirm("n"))
        self.assertFalse((self.root / ".bill").exists())
        self.assertFalse((self.root / "prose").exists())

    def test_without_a_terminal_it_refuses_rather_than_assume(self):
        with mock.patch.object(sys, "stdin", _NoTerminal()):
            with redirect_stdout(io.StringIO()):
                ready = boot.ensure_working_folder()
        self.assertFalse(ready)
        self.assertFalse((self.root / ".bill").exists())

    def test_a_configured_folder_is_never_asked_about_again(self):
        self.confirm()
        with redirect_stdout(io.StringIO()):
            ready = boot.ensure_working_folder(ask=lambda question: self.fail("asked again"))
        self.assertTrue(ready)

    def test_an_existing_data_folder_is_not_a_conflict(self):
        # Running Bill from a checkout is the normal case, not an exception.
        (self.root / "data").mkdir()
        self.assertTrue(self.confirm())
        self.assertTrue((self.root / "data").is_dir())


if __name__ == "__main__":
    unittest.main()
