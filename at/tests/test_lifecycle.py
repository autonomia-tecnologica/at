"""Closing a row: `cancel` with history, and `delete` with the declaration in hand.

The two actions are one item because they answer the same question from opposite
sides — a table that only grows is a table nobody trusts. `cancel` keeps the row
and writes the ending where the table says its story lives; `delete` takes the
row out, refusing while anything NAMES it, and never gives the number back.

What the engine may assume is only what a table DECLARES: the terminal status,
the field the reason lands in, whether a reason is required, and which fields can
point at a row. A table that declares no `lifecycle` has no closing, and says so
instead of having one invented for it.

Every test aims AT at a throwaway folder with `AT_ROOT`, so none of them
touches the checkout's own Working Folder.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, paths, tables
from at.data import schema, store
from at.ui.cli import main, tree

# A table of the instance's own whose reason lands in the field the engine's own
# log writes: `history` is what `tracks`/`append` stamps, and the closure line
# has to sit beside the log without taking its place.
PARCEL = {
    "id": "parcel",
    "order": 90,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/parcels.jsonl",
    "primary": "text",
    "columns": ["status", "text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text", "required": True},
        "status": {
            "label": "table.task.field.status",
            "enum": {
                "todo": "table.task.field.status.todo",
                "done": "table.task.field.status.done",
                "cancelled": "table.task.field.status.cancelled",
            },
            "default": "todo",
        },
        "history": {
            "label": "table.task.field.modifications",
            "type": "list",
            "tracks": "status",
            "append": {"text": "status", "stamp": "at", "type": "instant"},
            "default": [],
        },
    },
    "lifecycle": {
        "cancel": {
            "status": "cancelled",
            "reason": {"into": "history", "text": "table.closed.reason"},
            "reason_required": False,
        }
    },
}

# The same table with the two decisions made the other way: the reason is a
# requirement and it lands in a field of prose, not in the log.
RECEIPT = {
    "id": "receipt",
    "order": 91,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/receipts.jsonl",
    "primary": "text",
    "columns": ["status", "text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text", "required": True},
        "status": {
            "label": "table.task.field.status",
            "enum": {
                "todo": "table.task.field.status.todo",
                "cancelled": "table.task.field.status.cancelled",
            },
            "default": "todo",
        },
        "note": {"label": "table.task.field.desc"},
    },
    "lifecycle": {
        "cancel": {
            "status": "cancelled",
            "reason": {"into": "note", "text": "table.closed.reason"},
            "reason_required": True,
        }
    },
}

# A table that DECLARES a field called `reason`: the closing's own argument is
# not a field the table has to name, but when it names one the field wins and the
# same text answers both.
TICKET = {
    "id": "ticket",
    "order": 94,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/tickets.jsonl",
    "primary": "text",
    "columns": ["status", "text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text", "required": True},
        "status": {
            "label": "table.task.field.status",
            "enum": {
                "todo": "table.task.field.status.todo",
                "cancelled": "table.task.field.status.cancelled",
            },
            "default": "todo",
        },
        "reason": {"label": "table.task.field.desc"},
        "note": {"label": "table.task.field.desc"},
    },
    "lifecycle": {
        "cancel": {
            "status": "cancelled",
            "reason": {"into": "note", "text": "table.closed.reason"},
            "reason_required": True,
        }
    },
}

# A lifecycle naming a status no field of the table carries: the declaration is a
# person's file and may be wrong, and the closing says which line is.
BROKEN = {
    "id": "broken",
    "order": 92,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/brokens.jsonl",
    "primary": "text",
    "columns": ["text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text"},
        "state": {
            "label": "table.task.field.status",
            "enum": {"todo": "table.task.field.status.todo"},
            "default": "todo",
        },
    },
    "lifecycle": {"cancel": {"status": "cancelled"}},
}

# A field that can name a row of either table, which is what makes it store the
# `[table, number]` pair instead of the bare number.
LINK = {
    "id": "link",
    "order": 93,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/links.jsonl",
    "primary": "text",
    "columns": ["text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text"},
        "to": {"label": "table.task.field.project", "ref": ["project", "task"]},
    },
}


class Closing(unittest.TestCase):
    """A folder of its own, the product's three tables, and the declared ones."""

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
        for declared in (PARCEL, RECEIPT, TICKET, BROKEN, LINK):
            self.declare(declared)

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def declare(self, table: dict) -> None:
        where = paths.data_dir() / schema.SCHEMA_DIR / f"{table['id']}.json"
        where.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()

    def write(self, table: str, rows: list[dict]) -> None:
        """Rows put in the store by hand — a folder restored from a backup, or a
        file a person edited, carries rows the counter never saw."""
        where = store.path(table)
        where.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )

    def words(self, *args: str) -> tuple[int, str]:
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()


class TheDeclaration(Closing):
    def test_the_bundled_tables_declare_their_lifecycle(self):
        bundled = schema.bundled()
        for table, into in (("task", "desc"), ("project", "desc")):
            with self.subTest(table=table):
                spec = bundled[table]["lifecycle"]["cancel"]
                self.assertEqual(spec["status"], "cancelled")
                self.assertEqual(spec["reason"]["into"], into)
                self.assertTrue(spec["reason_required"])

    def test_the_terminal_status_is_one_the_field_already_carries(self):
        # The closing never writes a status into an enum that does not hold it:
        # `cancelled` is declared in both, and that is what lets the engine find
        # the field without a list of names of its own.
        for table in ("task", "project"):
            with self.subTest(table=table):
                declared = schema.bundled()[table]["fields"]["status"]
                self.assertIn(
                    schema.bundled()[table]["lifecycle"]["cancel"]["status"],
                    declared["enum"],
                )

    def test_the_reason_is_a_key_and_not_a_sentence(self):
        # The declaration carries no text a person reads (§4): `reason.text` is
        # an i18n key, and it answers in both languages.
        key = schema.bundled()["task"]["lifecycle"]["cancel"]["reason"]["text"]
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                self.assertNotEqual(i18n.text(key, language), key)

    def test_a_table_that_declares_none_answers_with_nothing(self):
        self.assertEqual(tables.lifecycle("reminder"), {})
        self.assertEqual(tables.lifecycle("task")["status"], "cancelled")

    def test_every_action_is_in_the_list_the_surfaces_read(self):
        self.assertEqual(
            tables.ACTIONS, ("list", "view", "create", "edit", "cancel", "delete")
        )


class TheCancel(Closing):
    def test_the_status_becomes_the_terminal_one_and_the_row_stays(self):
        row = tables.create("task", {"text": "café"})
        closed = tables.cancel("task", row["id"], "acabou o café")
        self.assertEqual(closed["status"], "cancelled")
        self.assertEqual(store.find("task", row["id"])["status"], "cancelled")
        self.assertEqual(len(store.load("task")), 1)

    def test_the_reason_is_readable_where_the_table_says_history_lives(self):
        row = tables.create("task", {"text": "café"})
        closed = tables.cancel("task", row["id"], "acabou o café")
        self.assertIn("acabou o café", closed["desc"])
        self.assertIn("2026", closed["desc"])

    def test_the_closing_is_also_a_line_of_the_status_log(self):
        row = tables.create("task", {"text": "café"})
        closed = tables.cancel("task", row["id"], "acabou o café")
        self.assertEqual(closed["modifications"][-1]["status"], "cancelled")

    def test_a_reason_and_the_log_do_not_take_each_others_place(self):
        # The declared field IS the field the engine's log writes: the closing
        # line is appended to it, so the status entries stay where they were.
        row = tables.create("parcel", {"text": "encomenda"})
        closed = tables.cancel("parcel", row["id"], "extraviada")
        log = closed["history"]
        self.assertEqual(sum(isinstance(entry, dict) for entry in log), 2)
        self.assertEqual(log[0]["status"], "todo")
        self.assertEqual(log[1]["status"], "cancelled")
        self.assertIn("extraviada", log[-1])

    def test_a_required_reason_is_required(self):
        row = tables.create("receipt", {"text": "café"})
        with self.assertRaises(tables.TableError) as refused:
            tables.cancel("receipt", row["id"])
        self.assertIn("reason", str(refused.exception))
        self.assertEqual(store.find("receipt", row["id"])["status"], "todo")

    def test_a_reason_the_table_does_not_require_may_be_left_out(self):
        row = tables.create("parcel", {"text": "encomenda"})
        closed = tables.cancel("parcel", row["id"])
        self.assertEqual(closed["status"], "cancelled")
        self.assertNotIn("", [str(entry) for entry in closed["history"]])

    def test_the_reason_joins_the_prose_already_there_instead_of_replacing_it(self):
        row = tables.create("task", {"text": "café", "desc": "primeira linha"})
        closed = tables.cancel("task", row["id"], "acabou")
        self.assertTrue(closed["desc"].startswith("primeira linha"))
        self.assertIn("acabou", closed["desc"])

    def test_a_table_that_declares_no_lifecycle_says_so(self):
        row = tables.create("reminder", {"text": "café", "at": "08:00"})
        with self.assertRaises(tables.TableError) as refused:
            tables.cancel("reminder", row["id"], "chega")
        self.assertIn("lifecycle", str(refused.exception))

    def test_a_lifecycle_naming_an_undeclared_status_says_which_one(self):
        row = tables.create("broken", {"text": "café"})
        with self.assertRaises(tables.TableError) as refused:
            tables.cancel("broken", row["id"], "chega")
        self.assertIn("cancelled", str(refused.exception))

    def test_a_reason_sent_to_a_field_the_table_does_not_declare_is_refused(self):
        # The declaration is a person's file and may carry a typo. Writing the
        # line anyway would put a key in the row that nobody declared.
        stray = json.loads(json.dumps(RECEIPT))
        stray["id"] = "stray"
        stray["store"] = "data/strays.jsonl"
        stray["lifecycle"]["cancel"]["reason"]["into"] = "nowhere"
        self.declare(stray)
        row = tables.create("stray", {"text": "café"})
        with self.assertRaises(tables.TableError) as refused:
            tables.cancel("stray", row["id"], "acabou")
        self.assertIn("nowhere", str(refused.exception))

    def test_a_row_already_closed_is_not_closed_twice(self):
        row = tables.create("task", {"text": "café"})
        tables.cancel("task", row["id"], "acabou")
        with self.assertRaises(tables.TableError) as refused:
            tables.cancel("task", row["id"], "de novo")
        self.assertIn(tables.format_id("task", row["id"]), str(refused.exception))
        self.assertEqual(len(store.find("task", row["id"])["modifications"]), 2)

    def test_the_fields_a_cancel_also_sets_go_through_the_engine(self):
        row = tables.create("task", {"text": "café"})
        closed = tables.cancel("task", row["id"], "acabou", {"priority": "high"})
        self.assertEqual(closed["priority"], "high")
        self.assertEqual(closed["status"], "cancelled")

    def test_a_field_the_cancel_does_not_know_is_refused(self):
        row = tables.create("task", {"text": "café"})
        with self.assertRaises(tables.TableError):
            tables.cancel("task", row["id"], "acabou", {"nope": "x"})


class TheDelete(Closing):
    def test_a_row_nothing_names_goes(self):
        row = tables.create("task", {"text": "café"})
        gone = tables.delete("task", row["id"])
        self.assertEqual(gone["id"], row["id"])
        self.assertEqual(store.load("task"), [])

    def test_the_next_row_does_not_take_the_number_of_the_one_that_went(self):
        first = tables.create("task", {"text": "café"})
        tables.delete("task", first["id"])
        self.assertEqual(tables.create("task", {"text": "chá"})["id"], first["id"] + 1)

    def test_a_number_the_counter_never_saw_stays_spent_all_the_same(self):
        # A store restored from a backup carries a row the counter never handed
        # out. Taking it out is what makes the number spent — otherwise the next
        # `create` starts again from the highest row still standing.
        self.write("task", [{"id": 7, "text": "café", "status": "todo"}])
        tables.delete("task", 7)
        self.assertEqual(store.counter("task"), 7)
        self.assertEqual(tables.create("task", {"text": "chá"})["id"], 8)

    def test_a_named_row_is_refused_and_the_refusal_names_the_namer(self):
        project = tables.create("project", {"name": "Casa"})
        task = tables.create("task", {"text": "café", "project": str(project["id"])})
        with self.assertRaises(tables.TableError) as refused:
            tables.delete("project", project["id"])
        message = str(refused.exception)
        self.assertIn(tables.format_id("task", task["id"]), message)
        self.assertIn("project", message)
        self.assertNotEqual(store.find("project", project["id"]), None)

    def test_it_goes_once_nothing_names_it_anymore(self):
        project = tables.create("project", {"name": "Casa"})
        task = tables.create("task", {"text": "café", "project": str(project["id"])})
        tables.delete("task", task["id"])
        tables.delete("project", project["id"])
        self.assertEqual(store.load("project"), [])

    def test_a_row_that_names_itself_does_not_block_its_own_delete(self):
        row = tables.create("project", {"name": "Casa"})
        tables.edit("project", row["id"], {"parent": str(row["id"])})
        tables.delete("project", row["id"])
        self.assertIsNone(store.find("project", row["id"]))

    def test_a_field_that_declares_no_ref_does_not_block_a_delete(self):
        # The number lives in `on_day`, which points at nothing. Read off the
        # declarations, that is not a link — and a scan for the digit would say
        # it was.
        project = tables.create("project", {"name": "Casa"})
        tables.create("reminder", {"text": "café", "at": "08:00", "on_day": "1"})
        tables.delete("project", project["id"])
        self.assertEqual(store.load("project"), [])

    def test_a_reference_that_names_more_than_one_table_blocks_by_its_pair(self):
        # A field that may point at more than one table stores `[table, number]`,
        # so the row says which table it meant — and the refusal reads the pair.
        project = tables.create("project", {"name": "Casa"})
        link = tables.create("link", {"text": "café", "to": str(project["id"])})
        self.assertEqual(store.find("link", link["id"])["to"], ["project", 1])
        with self.assertRaises(tables.TableError) as refused:
            tables.delete("project", project["id"])
        self.assertIn(tables.format_id("link", link["id"]), str(refused.exception))

    def test_a_pair_that_names_another_table_does_not_block(self):
        # The pair says which table was meant, and a task's number is not a
        # project's — however much the two digits look alike.
        project = tables.create("project", {"name": "Casa"})
        self.write("link", [{"id": 1, "text": "café", "to": ["task", project["id"]]}])
        tables.delete("project", project["id"])
        self.assertEqual(store.load("project"), [])

    def test_an_unknown_row_is_still_an_unknown_row(self):
        with self.assertRaises(tables.TableError):
            tables.delete("task", 404)


class TheDoor(Closing):
    def test_the_cli_closes_and_says_so(self):
        tables.create("task", {"text": "café"})
        code, text = self.words("task", "cancel", "1", "--set", "reason=acabou")
        self.assertEqual(code, 0)
        self.assertIn("TASK-1", text)
        self.assertEqual(store.find("task", 1)["status"], "cancelled")

    def test_a_cancel_without_an_id_is_a_usage_error(self):
        code, _ = self.words("task", "cancel", "--set", "reason=acabou")
        self.assertEqual(code, 2)

    def test_the_cli_refuses_the_delete_that_is_named(self):
        tables.create("project", {"name": "Casa"})
        tables.create("task", {"text": "café", "project": 1})
        code, text = self.words("project", "delete", "1")
        self.assertEqual(code, 1)
        self.assertIn("TASK-1", text)
        self.assertIsNotNone(store.find("project", 1))

    def test_the_cli_deletes_what_nothing_names(self):
        tables.create("task", {"text": "café"})
        code, text = self.words("task", "delete", "1")
        self.assertEqual(code, 0)
        self.assertIn("TASK-1", text)
        self.assertEqual(store.load("task"), [])

    def test_the_cli_says_so_when_the_table_declares_no_closing(self):
        code, text = self.words("reminder", "cancel", "1", "--set", "reason=chega")
        self.assertEqual(code, 1)
        self.assertIn("lifecycle", text)

    def test_the_help_offers_the_two_words_under_every_table(self):
        code, text = self.words("help")
        self.assertEqual(code, 0)
        for node in tree.table_nodes():
            with self.subTest(table=node.name):
                for action in ("cancel", "delete"):
                    self.assertIn(action, [child.name for child in node.children])
                self.assertIn(f"{node.name}", text)

    def test_a_field_of_the_tables_own_named_reason_is_not_taken_from_it(self):
        tables.create("ticket", {"text": "café"})
        code, _ = self.words("ticket", "cancel", "1", "--set", "reason=acabou")
        self.assertEqual(code, 0)
        row = store.find("ticket", 1)
        self.assertEqual(row["reason"], "acabou")
        self.assertIn("acabou", row["note"])

    def test_a_refusal_reads_in_the_language_of_the_reader(self):
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            code, text = self.words("reminder", "cancel", "1")
        self.assertEqual(code, 1)
        self.assertIn("no lifecycle", text)


if __name__ == "__main__":
    unittest.main()
