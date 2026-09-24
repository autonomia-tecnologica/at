"""Dispatch: which word reaches what, and what an unknown one costs.

`at-cli` with no word prints the help — the Control Panel is a screen for whoever
does not type commands, and it is not built yet. So there is no path here that
can pop a window, and the suite that runs on a build machine stays awake.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import __version__, i18n
from at.core import boot
from at.ui.cli import OK, USAGE, _lang, _webapp, main, tree
from at.ui.webapp import app as webapp


class Dispatch(unittest.TestCase):
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

    def test_no_word_at_all_answers_with_the_help(self):
        code, text = self.run_words()
        self.assertEqual(code, 0)
        self.assertIn(i18n.tr("cli.help.title", version=__version__), text)

    def test_an_unknown_word_is_a_usage_error(self):
        code, text = self.run_words("nowhere")
        self.assertEqual(code, 2)
        self.assertIn("nowhere", text)

    def test_a_word_that_takes_no_argument_says_so(self):
        code, _ = self.run_words("help", "extra")
        self.assertEqual(code, 2)

    def test_the_language_word_answers(self):
        code, text = self.run_words("lang")
        self.assertEqual(code, OK)
        self.assertIn("pt_BR", text)


class TheLanguage(unittest.TestCase):
    """`at-cli lang` — the language AT speaks, and the choice of it (item 7).

    A folder born under the machine's own locale has no door to another
    language: the resolution reads `$AT_LANG`, then the folder, then the
    system, and only the folder's own choice is the folder's. This is that
    door — and the rename that follows the language is offered in the SAME run,
    because the terminal that just chose is where the question can be asked.
    """

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def active(self) -> str:
        return (self.root / "App" / "i18n" / "active").read_text(encoding="utf-8").strip()

    def run_lang(self, *words: str, answer: str | None = None,
                 own: bool = True) -> tuple[int, str]:
        """`_lang` the way the command reads it.

        `own` is the folder's own choice: `$AT_LANG` is out of the way, because
        an override in the environment is not the folder's decision and the
        rename is never offered for one. `answer` is the person at the terminal;
        with none there is none, which is the state a build machine runs in.
        """
        environ = os.environ
        if own:
            environ = {key: value for key, value in os.environ.items() if key != "AT_LANG"}
        output = io.StringIO()
        with mock.patch.dict(os.environ, environ, clear=True):
            i18n.reset()
            ask = None if answer is None else (lambda question: answer)
            with redirect_stdout(output):
                code = _lang(list(words), ask=ask)
        return code, output.getvalue()

    def test_it_shows_the_code_and_the_folder_it_came_from(self):
        code, text = self.run_lang()
        self.assertEqual(code, OK)
        self.assertIn("pt_BR", text)
        self.assertIn(i18n.tr("cli.lang.origin.folder"), text)

    def test_it_names_the_override_when_the_environment_is_what_chose(self):
        # The origin is reported, and this is why: whoever reads the wrong
        # language learns WHICH thing to change, and `$AT_LANG` is not the
        # folder's own choice — it is the one that wins over it.
        code, text = self.run_lang(own=False)
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("cli.lang.origin.env"), text)

    def test_choosing_writes_the_file_and_answers_in_it_at_once(self):
        # The same process answers in the new language, because neither the
        # `cli` nor the server keeps a language of its own.
        code, text = self.run_lang("en_US", answer="n")
        self.assertEqual(code, OK)
        self.assertEqual(self.active(), "en_US")
        self.assertIn(
            i18n.text("cli.lang.chosen", "en_US").format(code="en_US"), text
        )

    def test_choosing_offers_the_rename_in_the_same_run(self):
        code, text = self.run_lang("en_US", answer="s")
        self.assertEqual(code, OK)
        self.assertIn("Tabelas → Tables", text)
        self.assertTrue((self.root / "Tables").is_dir())
        self.assertFalse((self.root / "Tabelas").exists())

    def test_without_a_terminal_nothing_moves(self):
        # The folders are the person's, and moving them where nobody could
        # answer is not a decision — the language changes, the names do not.
        code, text = self.run_lang("en_US")
        self.assertEqual(code, OK)
        self.assertEqual(self.active(), "en_US")
        self.assertIn(i18n.text("boot.migration.folders.no_tty", "en_US"), text)
        self.assertTrue((self.root / "Tabelas").is_dir())

    def test_an_unsupported_code_is_refused_and_writes_nothing(self):
        code, text = self.run_lang("es")
        self.assertEqual(code, USAGE)
        self.assertIn("es", text)
        self.assertEqual(self.active(), "pt_BR")

    def test_an_extra_argument_is_a_usage_error(self):
        code, text = self.run_lang("en_US", "extra")
        self.assertEqual(code, USAGE)
        self.assertIn("lang", text)

    def test_the_flag_renames_with_nobody_to_ask(self):
        # The flag IS the answer: the question the run would have asked is the
        # one the person typed, so a run with no terminal renames where the
        # plain command leaves the names alone (`test_without_a_terminal...`).
        code, text = self.run_lang("en_US", "--include-app-folders")
        self.assertEqual(code, OK)
        self.assertEqual(self.active(), "en_US")
        self.assertIn("Tabelas → Tables", text)
        self.assertTrue((self.root / "Tables").is_dir())
        self.assertFalse((self.root / "Tabelas").exists())

    def test_the_flag_does_not_reopen_a_decline_that_was_not_there(self):
        # The memory is of the OFFER, and a person who typed the decision is
        # deciding again: the same run twice moves nothing the second time,
        # because there is nothing left to move — not because it was remembered.
        self.run_lang("en_US", "--include-app-folders")
        code, text = self.run_lang("en_US", "--include-app-folders")
        self.assertEqual(code, OK)
        self.assertTrue((self.root / "Tables").is_dir())

    def test_the_flag_without_a_code_is_a_usage_error(self):
        # It decorates a CHOICE: there is no language for the folders to take
        # the names of, so the flag alone names nothing.
        code, text = self.run_lang("--include-app-folders")
        self.assertEqual(code, USAGE)
        self.assertIn("lang", text)


class TheWebappWords(unittest.TestCase):
    """`at-cli webapp` — the flags it takes, and what a word it does not take costs.

    Starting a server is `run`'s business and is not what is under test here, so
    `run` is replaced: what this reads is which words reach it. The refusals
    themselves — the loop, the wildcard, the payload for another platform — are
    `test_caddy.py`'s, where a folder and a real Caddy exist.
    """

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AT_LANG": "pt_BR"})
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()

    def run_webapp(self, *words: str) -> tuple[int, mock.Mock]:
        output = io.StringIO()
        with mock.patch.object(webapp, "run", return_value=OK) as started:
            with redirect_stdout(output):
                code = _webapp(list(words))
        return code, started

    def test_it_serves_the_loop_by_default(self):
        code, started = self.run_webapp()
        self.assertEqual(code, OK)
        started.assert_called_once_with(webapp.DEFAULT_PORT, host=None,
                                        include_caddy=False)

    def test_the_flag_and_the_port_reach_the_server(self):
        # `run` is what a person types as well, and the flags come in any order.
        code, started = self.run_webapp("run", "--port", "12399", "--include-caddy")
        self.assertEqual(code, OK)
        started.assert_called_once_with(12399, host=None, include_caddy=True)

    def test_the_host_reaches_the_server(self):
        code, started = self.run_webapp("--host", "192.168.1.10")
        self.assertEqual(code, OK)
        started.assert_called_once_with(webapp.DEFAULT_PORT, host="192.168.1.10",
                                        include_caddy=False)

    def test_the_port_keeps_its_other_spelling(self):
        code, started = self.run_webapp("--porta", "12399")
        self.assertEqual(code, OK)
        started.assert_called_once_with(12399, host=None, include_caddy=False)

    def test_a_word_it_does_not_take_is_a_usage_error(self):
        for words in (["--port", "abc"], ["--port"], ["--port", "0"],
                      ["--port", "70000"], ["--host"], ["--host", "--port"],
                      ["--include-caddy", "extra"], ["--caddy"]):
            with self.subTest(words=words):
                code, started = self.run_webapp(*words)
                self.assertEqual(code, USAGE)
                started.assert_not_called()


if __name__ == "__main__":
    unittest.main()
