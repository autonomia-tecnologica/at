"""The first run: what a folder gains, and what it does not.

Every test aims AT at a throwaway folder with `AT_ROOT`, so none of them
touches the checkout's own Working Folder.

The names here are the ones `pt_BR` gives, and they are written out on purpose:
a test that asked `paths` what a folder is called would agree with whatever
`paths` did, which is the one thing this file has to hold still. The names are
the FACE; the resolution through the internal name is `test_migrations`.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, migrations, settings
from at.data import store


class _NoTerminal:
    """A stdin that cannot be asked anything."""

    def isatty(self) -> bool:
        return False


class FirstRun(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
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
        self.assertTrue((self.root / "App" / "settings.json").is_file())
        self.assertTrue((self.root / "App" / "i18n" / "active").is_file())
        self.assertTrue((self.root / "Tabelas").is_dir())
        self.assertTrue((self.root / "Biblioteca").is_dir())
        self.assertEqual(settings.load()["schema"], settings.SCHEMA)

    def test_the_folder_is_born_with_the_engines_row_and_no_person(self):
        """Every act of the engine needs a row to be named in the `audit` (item
        15) — and the FIRST ADMIN does not: it is asked for, because a seeded
        credential is a published password (§3, item 9).
        """
        self.confirm()
        rows = store.load("actor")
        self.assertEqual([row.get("type") for row in rows], ["engine"])
        self.assertEqual(actors.people(), [])
        self.assertFalse(actors.can_expose())

    def test_the_first_run_says_where_the_admin_is_born(self):
        """The bridge the `cli` fatia keeps: the first start does NOT ask for
        the Main Key — it says where the admin is born, and names the word that
        asks for it (`at-cli admin`). Inventing a second door here would be a
        word the tree does not carry (§4, item 176).
        """
        output = io.StringIO()
        with redirect_stdout(output):
            boot.ensure_working_folder(ask=lambda question: "s")
        said = output.getvalue()
        self.assertIn(i18n.tr("boot.first_run.admin_needed"), said)
        self.assertIn("at-cli admin", said)
        # And the sentence is the bridge, not a promise already kept: the
        # folder it just made has nobody in it.
        self.assertEqual(actors.admins(), [])

    def test_the_folders_that_are_only_named_are_born_empty(self):
        self.confirm()
        self.assertTrue((self.root / "Projetos").is_dir())
        self.assertTrue((self.root / "Compartilhada").is_dir())
        self.assertTrue((self.root / "Harness").is_dir())
        self.assertTrue((self.root / "Cofre").is_dir())
        self.assertTrue((self.root / "Convertidos").is_dir())
        self.assertEqual(list((self.root / "Projetos").iterdir()), [])
        self.assertEqual(list((self.root / "Compartilhada").iterdir()), [])
        self.assertEqual(list((self.root / "Harness").iterdir()), [])
        self.assertEqual(list((self.root / "Cofre").iterdir()), [])
        self.assertEqual(list((self.root / "Convertidos").iterdir()), [])

    def test_a_folder_born_now_has_nothing_to_catch_up_on(self):
        # The stamp exists so the first start of an OLD folder differs from the
        # first start of a new one, and this is that difference.
        self.confirm()
        stamp = json.loads((self.root / "App" / "migrations").read_text(encoding="utf-8"))
        self.assertEqual(stamp, sorted(migration.ident for migration in migrations.MIGRATIONS))

    def test_the_chosen_language_is_recorded_in_the_folder(self):
        self.confirm()
        recorded = (self.root / "App" / "i18n" / "active").read_text(encoding="utf-8")
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
        welcome = self.root / "Biblioteca" / i18n.tr("prose.welcome.filename")
        self.assertTrue(welcome.is_file())
        self.assertEqual(welcome.read_text(encoding="utf-8"), i18n.tr("prose.welcome.body"))

    def test_the_folder_is_born_with_a_note_that_presents_it(self):
        """`AGENT.md`, at the root — where whoever works in the folder looks.

        Not inside `Biblioteca/`: that folder is the person's material, and the
        note is the folder's own (§0, item 25).
        """
        self.confirm()
        note = self.root / "AGENT.md"
        self.assertTrue(note.is_file())
        self.assertEqual(note.read_text(encoding="utf-8"), i18n.tr("folder.agent.body"))
        self.assertFalse((self.root / "Biblioteca" / "AGENT.md").exists())

    def test_the_note_keeps_its_name_in_every_language(self):
        """The TEXT follows the language; the NAME does not.

        A note whose name moved with the translation is a note whatever works in
        the folder stops finding — the same reason `README.md` keeps its spelling
        everywhere, and the opposite of `Bem-vindo.md`.
        """
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.confirm()
        self.assertTrue((self.root / "AGENT.md").is_file())
        self.assertEqual(
            (self.root / "AGENT.md").read_text(encoding="utf-8"),
            i18n.tr("folder.agent.body"),
        )

    def test_the_note_is_written_once_and_only_once(self):
        """An edit is the person's, and a deletion was meant.

        Both halves matter and they pull in opposite directions: a note that
        overwrote an edit argues with its owner, and one that came back after
        being deleted does the same.
        """
        self.confirm()
        note = self.root / "AGENT.md"
        note.write_text("o que eu escrevi aqui\n", encoding="utf-8", newline="\n")

        with redirect_stdout(io.StringIO()):
            boot.ensure_working_folder(ask=lambda question: self.fail("asked again"))
        self.assertEqual(note.read_text(encoding="utf-8"), "o que eu escrevi aqui\n")

        note.unlink()
        with redirect_stdout(io.StringIO()):
            boot.ensure_working_folder(ask=lambda question: self.fail("asked again"))
        self.assertFalse(note.exists())

    def test_declining_writes_nothing(self):
        self.assertFalse(self.confirm("n"))
        self.assertFalse((self.root / "App").exists())
        self.assertFalse((self.root / "Biblioteca").exists())

    def test_without_a_terminal_it_refuses_rather_than_assume(self):
        with mock.patch.object(sys, "stdin", _NoTerminal()):
            with redirect_stdout(io.StringIO()):
                ready = boot.ensure_working_folder()
        self.assertFalse(ready)
        self.assertFalse((self.root / "App").exists())

    def test_a_configured_folder_is_never_asked_about_again(self):
        self.confirm()
        with redirect_stdout(io.StringIO()):
            ready = boot.ensure_working_folder(ask=lambda question: self.fail("asked again"))
        self.assertTrue(ready)

    def test_an_existing_data_folder_is_not_a_conflict(self):
        # Running AT from a checkout is the normal case, not an exception.
        (self.root / "Tabelas").mkdir()
        self.assertTrue(self.confirm())
        self.assertTrue((self.root / "Tabelas").is_dir())

    def test_the_folders_follow_the_language_of_the_folder(self):
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.confirm()
        self.assertTrue((self.root / "Tables").is_dir())
        self.assertTrue((self.root / "Library").is_dir())
        self.assertTrue((self.root / "Projects").is_dir())
        self.assertTrue((self.root / "Shared").is_dir())
        self.assertTrue((self.root / "Vault").is_dir())
        # `Harness/` does not move with the language either: pt_BR took the word
        # whole, so both languages spell it the same way.
        self.assertTrue((self.root / "Harness").is_dir())
        # The instance folder is the one name that does not move with the
        # language: the language is recorded INSIDE it.
        self.assertTrue((self.root / "App" / "settings.json").is_file())


if __name__ == "__main__":
    unittest.main()
