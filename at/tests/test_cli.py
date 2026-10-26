"""Dispatch: which word reaches what, and what an unknown one costs.

`at-cli` with no word opens the Control Panel (§5, TASK-169 fatia 1/3) — the
browser, on the app itself. The module under test here is dispatch, not the
local mode's own server/browser/idle-death machinery (`test_webapp_local.py`
is that), so every test that reaches the wordless path replaces
`local.run` the same way `TheWebappWords` already replaces `webapp.run` — no
path here pops a real window, and the suite that runs on a build machine
stays awake.
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
from at.core import boot, paths
from at.ui.cli import OK, USAGE, _lang, _webapp, main, tree
from at.ui.webapp import app as webapp
from at.ui.webapp import local


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

    def test_ajuda_is_help(self):
        self.assertEqual(self.run_words("ajuda"), self.run_words("help"))
        code, _ = self.run_words("ajuda", "extra")
        self.assertEqual(code, 2)

    def test_version_answers_with_the_packaged_version(self):
        code, text = self.run_words("version")
        self.assertEqual(code, 0)
        self.assertIn(__version__, text)

    def test_no_word_at_all_opens_the_local_app(self):
        with mock.patch.object(local, "run", return_value=OK) as started:
            code, text = self.run_words()
        self.assertEqual(code, OK)
        started.assert_called_once_with()
        self.assertEqual(text, "")

    def test_no_word_at_all_never_asks_the_terminal_for_the_folder(self):
        # TASK-169, fatia 2/3: o modo local não tem terminal, e é por isso
        # que ele corre ANTES de `ensure_working_folder` — mesmo numa pasta
        # que ainda não existe (o `boot.create_working_folder` do `setUp`
        # desta classe fica sem efeito aqui, porque este caminho nem olha
        # para ele).
        with mock.patch.object(boot, "ensure_working_folder") as asked, \
             mock.patch.object(local, "run", return_value=OK):
            code, _ = self.run_words()
        self.assertEqual(code, OK)
        asked.assert_not_called()

    def test_an_unknown_word_is_a_usage_error(self):
        code, text = self.run_words("nowhere")
        self.assertEqual(code, 2)
        self.assertIn("nowhere", text)

    def test_a_word_that_takes_no_argument_says_so(self):
        code, _ = self.run_words("help", "extra")
        self.assertEqual(code, 2)

    def test_a_word_help_shows_only_its_subtree(self):
        code, text = self.run_words("backup", "help")
        self.assertEqual(code, OK)
        self.assertIn("at-cli backup", text)
        self.assertIn("make", text)
        self.assertIn("restore", text)
        # nothing of the rest of the tree
        for other in ("webapp", "license", "install"):
            self.assertNotIn(other, text)
        self.assertNotIn(i18n.tr("cli.help.no_args"), text)
        # a table is a word with a subtree too
        code, text = self.run_words("task", "help")
        self.assertEqual(code, OK)
        self.assertIn("create", text)
        self.assertNotIn("backup", text)

    def test_a_word_help_with_something_after_it_names_what_failed(self):
        code, text = self.run_words("backup", "help", "extra")
        self.assertEqual(code, 2)
        self.assertIn(i18n.tr("cli.error.surplus_argument", word="help", argument="extra"), text)

    def test_a_word_that_takes_an_argument_keeps_help_as_the_argument(self):
        code, text = self.run_words("search", "help")
        self.assertEqual(code, OK)
        self.assertNotIn("at-cli search", text)

    def test_the_rejection_names_the_word_that_failed(self):
        code, text = self.run_words("backup", "nope")
        self.assertEqual(code, 2)
        self.assertIn(i18n.tr("cli.error.unknown_word", word="nope"), text)
        code, text = self.run_words("help", "extra")
        self.assertIn(i18n.tr("cli.error.surplus_argument", word="help", argument="extra"), text)
        code, text = self.run_words("backup", "make", "a", "b")
        self.assertEqual(code, 2)
        self.assertIn(i18n.tr("cli.error.surplus_argument", word="make", argument="b"), text)

    def test_the_language_word_answers(self):
        code, text = self.run_words("lang")
        self.assertEqual(code, OK)
        self.assertIn("pt_BR", text)


class TheConvertWord(Dispatch):
    """`at-cli convert <arquivo> --to pdf|docx` (TASK-165, fatia 2/4)."""

    def _source(self, name: str = "nota.md") -> None:
        (paths.prose_dir() / name).write_text("# Título\n\nUm parágrafo.", encoding="utf-8")

    def test_it_writes_into_convertidos_and_says_so(self):
        self._source()
        code, text = self.run_words("convert", "nota.md", "--to", "pdf")
        self.assertEqual(code, OK)
        self.assertTrue((paths.convert_dir() / "nota.pdf").is_file())
        self.assertIn("nota.pdf", text)

    def test_docx_too(self):
        self._source()
        code, _ = self.run_words("convert", "nota.md", "--to", "docx")
        self.assertEqual(code, OK)
        self.assertTrue((paths.convert_dir() / "nota.docx").is_file())

    def test_an_unknown_format_is_a_usage_error(self):
        self._source()
        code, _ = self.run_words("convert", "nota.md", "--to", "epub")
        self.assertEqual(code, USAGE)

    def test_a_file_outside_arquivos_is_refused_not_crashed(self):
        code, _ = self.run_words("convert", "../fora.md", "--to", "pdf")
        self.assertNotEqual(code, OK)

    def test_a_file_that_does_not_exist_is_refused(self):
        code, text = self.run_words("convert", "nao-existe.md", "--to", "pdf")
        self.assertNotEqual(code, OK)
        self.assertIn(i18n.tr("prose.not_served"), text)

    def test_the_wrong_shape_is_a_usage_error(self):
        self._source()
        code, _ = self.run_words("convert", "nota.md")
        self.assertEqual(code, USAGE)
        code, _ = self.run_words("convert", "nota.md", "para", "pdf")
        self.assertEqual(code, USAGE)


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

    def test_include_subcommands_says_the_spelled_words(self):
        code, text = self.run_lang("pt_BR", "--include-subcommands")
        self.assertEqual(code, OK)
        self.assertIn("help → ajuda", text)
        self.assertIn("task → tarefa", text)
        code, text = self.run_lang("en_US", "--include-subcommands")
        self.assertEqual(code, OK)
        self.assertIn("no subcommand word", text)

    def test_include_subcommands_without_a_code_is_a_usage_error(self):
        code, _ = self.run_lang("--include-subcommands")
        self.assertEqual(code, USAGE)

    def test_the_flag_without_a_code_is_a_usage_error(self):
        # It decorates a CHOICE: there is no language for the folders to take
        # the names of, so the flag alone names nothing.
        code, text = self.run_lang("--include-app-folders")
        self.assertEqual(code, USAGE)
        self.assertIn("lang", text)


class TheSubcommandWords(unittest.TestCase):
    """`at-cli lang <code> --include-subcommands` — the table, the choice kept in
    the settings, and help and dispatch following it."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        environ = {key: value for key, value in os.environ.items() if key != "AT_LANG"}
        environ["AT_ROOT"] = str(Path(self.scratch.name))
        self.env = mock.patch.dict(os.environ, environ, clear=True)
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        self.say("lang", "pt_BR", "--include-subcommands")

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def say(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        i18n.reset()
        with redirect_stdout(output):
            code = main(list(words))
        i18n.reset()
        return code, output.getvalue()

    def test_the_table_is_complete_and_plain_ascii(self):
        table = tree.SUBCOMMAND_WORDS["pt_BR"]
        self.assertEqual(len(table), 9 + 14 + 16)
        for own in table.values():
            self.assertTrue(own.isascii(), own)
        self.assertEqual(table["install-hooks"], "instalar-ganchos")
        self.assertEqual(table["backup"], "copia")
        self.assertEqual(tree.SUBCOMMAND_WORDS["en_US"], {})

    def test_every_table_word_is_a_word_of_the_tree(self):
        known = {"ask", "help"}
        for node in tree.roots():
            known.add(node.name)
            known |= {child.name for child in node.children}
        self.assertLessEqual(set(tree.SUBCOMMAND_WORDS["pt_BR"]), known)

    def test_the_flag_records_the_choice_in_the_settings(self):
        from at.core import settings

        self.assertEqual(settings.get(tree.SUBCOMMANDS_KEY), "pt_BR")

    def test_without_the_flag_nothing_is_recorded(self):
        from at.core import settings

        self.say("lang", "pt_BR")
        self.assertIsNone(settings.get(tree.SUBCOMMANDS_KEY))
        code, text = self.say("help")
        self.assertIn("task", text)
        self.assertNotIn("tarefa", text)

    def test_help_speaks_the_language(self):
        code, text = self.say("ajuda")
        self.assertEqual(code, OK)
        for word in ("tarefa", "copia", "configuracao", "licenca", "versao"):
            self.assertIn(word, text)
        self.assertIn("listar", text)
        self.assertNotIn("  task ", text)

    def test_a_word_help_speaks_the_language(self):
        code, text = self.say("tarefa", "ajuda")
        self.assertEqual(code, OK)
        self.assertIn("tarefa", text)
        self.assertIn("criar", text)
        self.assertIn("apagar", text)

    def test_dispatch_accepts_both_spellings(self):
        for words in (("tarefa", "listar"), ("task", "list"),
                      ("tarefa", "list"), ("task", "listar")):
            with self.subTest(words=words):
                code, _ = self.say(*words)
                self.assertEqual(code, OK)

    def test_the_actions_of_an_own_act_dispatch_in_both_spellings(self):
        for words in (("segredo", "varrer"), ("secret", "scan"),
                      ("lembrete", "vencidos")):
            with self.subTest(words=words):
                code, _ = self.say(*words)
                self.assertEqual(code, OK)

    def test_the_loose_words_dispatch_in_both_spellings(self):
        for words in (("versao",), ("version",), ("idioma",), ("configuracao", "listar"),
                      ("licenca",)):
            with self.subTest(words=words):
                code, _ = self.say(*words)
                self.assertEqual(code, OK)

    def test_pedir_reads_back_to_the_interpreters_word(self):
        # Not run: the interpreter is a model. What dispatch sees is the point.
        self.assertEqual(tree.canonical(["pedir", "uma frase"]), ["ask", "uma frase"])
        self.assertEqual(tree.canonical(["ask", "uma frase"]), ["ask", "uma frase"])
        self.assertEqual(tree.canonical(["copia", "restaurar", "x"]),
                         ["backup", "restore", "x"])

    def test_an_unknown_word_still_costs_a_usage_error(self):
        code, _ = self.say("tarefas")
        self.assertEqual(code, USAGE)

    def test_changing_the_language_without_the_flag_goes_back_to_en_US(self):
        self.say("lang", "en_US")
        code, text = self.say("help")
        self.assertNotIn("tarefa", text)
        self.assertIn("task", text)
        code, _ = self.say("tarefa", "listar")
        self.assertEqual(code, USAGE)
        code, _ = self.say("task", "list")
        self.assertEqual(code, OK)

    def test_the_completion_stays_canonical(self):
        names = {name for name, _ in tree.completion()}
        self.assertIn("task", names)
        self.assertNotIn("tarefa", names)


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

    def test_it_bundles_the_caddy_by_default(self):
        code, started = self.run_webapp()
        self.assertEqual(code, OK)
        started.assert_called_once_with(webapp.DEFAULT_PORT, public_port=None,
                                        host=None, include_caddy=True)

    def test_the_flag_and_the_port_reach_the_server(self):
        # `run` is what a person types as well, and the flags come in any order.
        code, started = self.run_webapp("run", "--port", "12399", "--no-caddy")
        self.assertEqual(code, OK)
        started.assert_called_once_with(12399, public_port=None, host=None,
                                        include_caddy=False)

    def test_the_host_reaches_the_server(self):
        code, started = self.run_webapp("--host", "192.168.1.10")
        self.assertEqual(code, OK)
        started.assert_called_once_with(webapp.DEFAULT_PORT, public_port=None,
                                        host="192.168.1.10", include_caddy=True)

    def test_the_port_keeps_its_other_spelling(self):
        code, started = self.run_webapp("--porta", "12399")
        self.assertEqual(code, OK)
        started.assert_called_once_with(12399, public_port=None, host=None,
                                        include_caddy=True)

    def test_the_public_port_reaches_the_server_untouched(self):
        # Left unsaid, it stays `None` — `webapp.run` is the one that falls
        # back to `port` itself, not this parsing.
        code, started = self.run_webapp("--port", "8443", "--public-port", "443")
        self.assertEqual(code, OK)
        started.assert_called_once_with(8443, public_port=443, host=None,
                                        include_caddy=True)

    def test_the_public_port_keeps_its_other_spelling(self):
        code, started = self.run_webapp("--porta-publica", "443")
        self.assertEqual(code, OK)
        started.assert_called_once_with(webapp.DEFAULT_PORT, public_port=443,
                                        host=None, include_caddy=True)

    def test_a_word_it_does_not_take_is_a_usage_error(self):
        for words in (["--port", "abc"], ["--port"], ["--port", "0"],
                      ["--port", "70000"], ["--host"], ["--host", "--port"],
                      ["--no-caddy", "extra"], ["--caddy"],
                      ["--public-port", "abc"], ["--public-port"],
                      ["--public-port", "0"], ["--public-port", "70000"]):
            with self.subTest(words=words):
                code, started = self.run_webapp(*words)
                self.assertEqual(code, USAGE)
                started.assert_not_called()


if __name__ == "__main__":
    unittest.main()
