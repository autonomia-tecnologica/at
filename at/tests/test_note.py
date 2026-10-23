"""A NOTA: the table, the conversation that writes it, and the door that
serves it (TASK-196, TASK-197).

A note is the thing said and kept: one text, the tags that sort it, and no
life of its own — a note is not work, it is not finished nor closed. This
module measures the three halves of that:

- **the TABLE** — `note` is a table of the system, with the shape the person
  decided: `id`, `text` and `tags`, `text` as the primary, and no `status` at
  all;
- **the CONVERSATION** — the word "nota" names the table, the verb "anota"
  carries it, and a sentence that names a reminder AND a note is refused,
  because one request names one table;
- **the DOOR** — `at-cli note create/list/view/edit/cancel/delete` go through
  the GENERIC door, with no command of their own: the word of a table is its
  own name, and the engine answers the six acts it has.

**The `cancel` is the engine's own refusal**, and the test says so: the note
declares no lifecycle, so `at-cli note cancel` reaches the engine and the
engine refuses it (`table.error.no_lifecycle`) — which is not the same thing
as a usage error, and the code says which one it was.

Every test aims AT a throwaway folder with `AT_ROOT`; none needs a network or
a model.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import actors, boot, permissions, tables
from at.data import schema, store
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import main, tree

# The words the conversation and the door speak, checked to exist in both
# languages.
SAID = (
    "table.note.name.one",
    "table.note.name.many",
    "table.note.field.text",
    "table.note.field.tags",
)


class NoteCase(unittest.TestCase):
    """A Working Folder of its own, born by this release."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
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

    def cli(self, *words: str) -> tuple[int, str]:
        """What the `cli` answers, and the code it exits with."""
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(words))
        return code, output.getvalue()


# --------------------------------------------------------------- the table ---


class TheTable(NoteCase):
    """`note` as a table of the system, with the shape that was decided."""

    def test_the_note_is_a_table_of_the_system(self):
        # The declaration ships with the product, and the folder it is born in
        # carries its own copy — a table of the system is one every folder has.
        self.assertIn("note", schema.bundled())
        self.assertTrue((self.root / "Tabelas" / "schema" / "note.json").is_file())
        self.assertIsNotNone(schema.of("note"))

    def test_the_shape_is_the_one_that_was_decided(self):
        # `text` and `tags`, reused from the tables that already had them: no
        # new word, no gate broken.
        declared = schema.of("note")
        self.assertEqual(declared["primary"], "text")
        self.assertEqual(declared["columns"], ["text", "tags"])
        self.assertEqual(list(declared["fields"]), ["id", "text", "tags"])

    def test_the_text_is_what_the_note_says_and_it_is_required(self):
        text = schema.field("note", "text")
        self.assertEqual(text["label"], "table.note.field.text")
        self.assertTrue(text["required"])
        self.assertTrue(text["searchable"])

    def test_the_tags_are_a_list_and_sort_the_note(self):
        tags = schema.field("note", "tags")
        self.assertEqual(tags["type"], "list")
        self.assertEqual(tags["default"], [])
        self.assertTrue(tags["filterable"])

    def test_the_note_has_no_life_of_its_own(self):
        # A note is not work: it is not finished nor closed, and so it declares
        # no `status` and no lifecycle. The engine says so when someone asks it
        # to close one.
        declared = schema.of("note")
        self.assertNotIn("status", declared["fields"])
        self.assertNotIn("lifecycle", declared)
        with self.assertRaises(tables.TableError) as caught:
            tables.cancel("note", 1)
        self.assertEqual(caught.exception.key, "error.no_lifecycle")

    def test_the_rows_live_in_the_plural_of_its_name(self):
        tables.create("note", {"text": "o banco ligou"})
        self.assertTrue((self.root / "Tabelas" / "notes.jsonl").is_file())
        self.assertEqual(len(store.load("note")), 1)

    def test_the_catalogue_gives_the_note_the_six_acts(self):
        self.assertEqual(
            permissions.catalogue().get("note"),
            ("list", "view", "create", "edit", "cancel", "delete"),
        )
        self.assertTrue(permissions.is_known("note:create"))

    def test_the_administrator_carries_them(self):
        role = actors.role_for_admin()
        for action in tables.ACTIONS:
            self.assertIn(f"note:{action}", permissions.carried(role))

    def test_the_tree_offers_the_note_beside_the_engine_s_acts(self):
        node = next(node for node in tree.table_nodes() if node.name == "note")
        self.assertEqual(
            [child.name for child in node.children],
            ["list", "view", "create", "edit", "cancel", "delete"],
        )

    def test_every_sentence_speaks_both_languages(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                with mock.patch.dict(os.environ, {"AT_LANG": language}):
                    i18n.reset()
                    for key in SAID:
                        self.assertNotEqual(tr(key), key)


# ---------------------------------------------------------- the conversation ---


class TheConversation(NoteCase):
    """What the sentence says becomes a row of the table it names."""

    def test_the_verb_that_carries_the_table_creates_the_note(self):
        # "anota" does not write "nota": the verb already says what the line is,
        # and the content that is left is what the note says.
        result = door.ask("anota que o banco ligou")
        self.assertEqual(result.kind, "answer")
        rows = store.load("note")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "banco ligou")

    def test_the_word_nota_names_the_table(self):
        result = door.ask("cria uma nota sobre o deploy")
        self.assertEqual(result.kind, "answer")
        rows = store.load("note")
        self.assertEqual(len(rows), 1)
        self.assertIn("deploy", rows[0]["text"])

    def test_a_sentence_naming_a_reminder_and_a_note_is_refused(self):
        # The word "nota" names ONE thing — the table. A sentence that names
        # the reminder AND the note names two tables, and one request names
        # one table.
        result = door.ask("cria um lembrete com nota importante")
        self.assertEqual(result.kind, "refused")
        self.assertIn(tr("table.note.name.one"), result.text)
        self.assertIn(tr("table.reminder.name.one"), result.text)
        self.assertEqual(store.load("note"), [])
        self.assertEqual(store.load("reminder"), [])

    def test_the_remark_of_the_reminder_is_named_by_its_own_word(self):
        # "observação" is the word the reminder's own field answers to, and it
        # is SPENT: the sentence reads as a reminder, and what the field says
        # is the text the person wrote. (The hour is there because the reminder
        # asks for one — a reminder without a time is not a reminder.)
        result = door.ask("cria um lembrete com observacao importante às 19:00")
        self.assertEqual(result.kind, "answer")
        rows = store.load("reminder")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "importante")
        self.assertEqual(store.load("note"), [])

    def test_listing_the_notes_reads_them(self):
        tables.create("note", {"text": "o banco ligou"})
        result = door.ask("lista as notas")
        self.assertEqual(result.kind, "answer")
        self.assertIn("o banco ligou", result.text)

    def test_the_listing_shows_the_identifier_beside_the_title(self):
        tables.create("note", {"text": "Numero 2323 protocolo"})
        result = door.ask("listar notas")
        self.assertEqual(result.bullets, ["NOTE-1 · Numero 2323 protocolo"])

    def test_a_row_is_named_by_its_title(self):
        tables.create("note", {"text": "Numero 2323 protocolo"})
        tables.create("note", {"text": "o banco ligou"})
        for sentence in ("deletar nota numero 2323 protocolo", "apagar a nota PROTOCOLO"):
            proposal = nlu.propose(sentence, language="pt_BR")
            self.assertEqual((proposal.action, proposal.row), ("delete", 1))
        proposal = nlu.propose("ver nota banco ligou", language="pt_BR")
        self.assertEqual((proposal.action, proposal.row), ("view", 2))

    def test_2323_inside_a_title_is_never_the_id(self):
        # No row 2323 exists; the number alone would have been read as the id.
        tables.create("note", {"text": "Numero 2323 protocolo"})
        proposal = nlu.propose("deletar nota numero 2323 protocolo", language="pt_BR")
        self.assertEqual(proposal.row, 1)
        proposal = nlu.propose("deletar nota numero 1", language="pt_BR")
        self.assertEqual(proposal.row, 1)

    def test_a_title_that_matches_many_comes_back_as_a_question(self):
        tables.create("note", {"text": "protocolo do banco"})
        tables.create("note", {"text": "protocolo da prefeitura"})
        result = door.ask("deletar nota protocolo")
        self.assertEqual(result.kind, "question")
        self.assertIn("1. NOTE-1 · protocolo do banco", result.text)
        self.assertIn("2. NOTE-2 · protocolo da prefeitura", result.text)
        self.assertEqual(len(store.load("note")), 2)

    def test_a_title_that_matches_none_is_refused_in_its_own_words(self):
        tables.create("note", {"text": "o banco ligou"})
        result = door.ask("deletar nota xyzzy")
        self.assertEqual(result.kind, "refused")
        self.assertEqual(result.text, tr("nlu.error.no_title", table=tr("table.note.name.one"), text="xyzzy"))
        self.assertNotEqual(result.text, tr("nlu.error.no_row", table=tr("table.note.name.one")))

    def test_no_name_at_all_is_still_no_row(self):
        result = door.ask("deletar nota")
        self.assertEqual(result.kind, "refused")
        self.assertIn(tr("nlu.error.no_row", table=tr("table.note.name.one")), result.text)

    def test_the_new_keys_speak_both_languages(self):
        for key in ("nlu.error.no_title", "nlu.ask.which_row"):
            for language in i18n.SUPPORTED:
                self.assertNotEqual(i18n.text(key, language), key)

    def test_a_note_with_no_text_is_a_question(self):
        # "anota", alone, does not say what to write: the matcher asks back for
        # the field the person has not filled, and nothing is written.
        result = door.ask("anota")
        self.assertEqual(result.kind, "question")
        self.assertIn(tr("table.note.field.text"), result.text)
        self.assertEqual(store.load("note"), [])

    def test_the_matcher_proposes_and_does_not_write(self):
        # The interpreter proposes; the core validates and writes (§9).
        proposal = nlu.propose("anota que o banco ligou", language="pt_BR")
        self.assertEqual(proposal.action, "create")
        self.assertEqual(proposal.table, "note")
        self.assertEqual(proposal.values, {"text": "banco ligou"})
        self.assertEqual(store.load("note"), [])


# ----------------------------------------------------------------- the door ---


class TheDoor(NoteCase):
    """`at-cli note …` — the generic door, with the word of the table as its
    own name. The line is built by the test, and the door is the one every
    table already has."""

    def make(self) -> int:
        """The line the test builds: a note that says something."""
        code, text = self.cli("note", "create", "--set", "text=o banco ligou")
        self.assertEqual(code, 0)
        self.assertIn("NOTE-1", text)
        return 1

    def test_the_word_of_the_table_is_its_own_name(self):
        self.make()
        code, text = self.cli("note", "list")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.note.field.text"), text)
        self.assertIn(tr("table.note.field.tags"), text)

    def test_it_creates_a_line(self):
        code, text = self.cli(
            "note", "create", "--set", "text=o banco ligou", "--set", "tags=casa,urgente"
        )
        self.assertEqual(code, 0)
        rows = store.load("note")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "o banco ligou")
        self.assertEqual(rows[0]["tags"], ["casa", "urgente"])

    def test_a_note_with_no_text_is_refused(self):
        code, text = self.cli("note", "create")
        self.assertEqual(code, 1)
        self.assertIn(tr("table.note.field.text"), text)
        self.assertEqual(store.load("note"), [])

    def test_it_lists_what_it_carries(self):
        self.make()
        code, text = self.cli("note", "list")
        self.assertEqual(code, 0)
        self.assertIn("o banco ligou", text)

    def test_it_shows_one_line(self):
        self.make()
        code, text = self.cli("note", "view", "1")
        self.assertEqual(code, 0)
        self.assertIn("o banco ligou", text)
        self.assertIn("NOTE-1", text)

    def test_it_edits_one_line(self):
        self.make()
        code, text = self.cli("note", "edit", "1", "--set", "text=o banco nao ligou")
        self.assertEqual(code, 0)
        rows = store.load("note")
        self.assertEqual(rows[0]["text"], "o banco nao ligou")

    def test_it_deletes_one_line(self):
        self.make()
        code, text = self.cli("note", "delete", "1")
        self.assertEqual(code, 0)
        self.assertEqual(store.load("note"), [])

    def test_the_cancel_reaches_the_engine_and_the_engine_refuses_it(self):
        # A note declares no lifecycle, so there is no closing to do. The
        # refusal is the ENGINE's own (`table.error.no_lifecycle`), and not a
        # usage error: the door dispatched the act, and the code says which one
        # refused it — a usage error would be 2, and this one is 1.
        self.make()
        code, text = self.cli("note", "cancel", "1")
        self.assertEqual(code, 1)
        self.assertIn(tr("table.error.no_lifecycle", table=tr("table.note.name.one")), text)
        # The line is still there: a refused closing is not a deleted line.
        self.assertEqual(len(store.load("note")), 1)

    def test_an_act_the_engine_does_not_have_is_a_usage_error(self):
        code, text = self.cli("note", "close", "1")
        self.assertEqual(code, 2)
        self.assertIn(tr("table.error.unknown_action", action="close"), text)

    def test_every_act_leaves_a_line_of_its_own(self):
        # §3, item 15: what the door does is written down, and the refusal is
        # a line like any other.
        self.make()
        self.cli("note", "cancel", "1")
        lines = [line for line in store.load("audit") if line.get("what") == "note:cancel"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["status"], "refused")
        self.assertEqual(lines[0]["reason"], "table.error.no_lifecycle")


if __name__ == "__main__":
    unittest.main()
