"""The map of the functions (item 44): the `function` table, its seed and its
reader. The core does not resolve folders through it yet.

Every test aims AT a throwaway folder with `AT_ROOT`; none needs a network or a
model.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, functions, migrations, paths, tables
from at.core.tables_base import TableError
from at.data import schema, store


class FunctionCase(unittest.TestCase):
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


class TestTable(FunctionCase):
    def test_declaration_is_seeded_and_editable_table(self):
        declared = schema.of("function")
        self.assertIsNotNone(declared)
        self.assertEqual(declared["columns"], ["function", "folders", "enabled"])
        self.assertEqual(declared["primary"], "function")

    def test_labels_exist_in_both_languages(self):
        keys = (
            "table.function.name.one",
            "table.function.field.function.code",
            "table.function.field.folders",
            "table.function.field.enabled.disabled",
            "table.function.error.one_folder",
        )
        for language in ("pt_BR", "en_US"):
            with mock.patch.dict(os.environ, {"AT_LANG": language}):
                i18n.reset()
                for key in keys:
                    self.assertNotEqual(i18n.tr(key), key, (language, key))
        i18n.reset()
        self.assertEqual(i18n.keys_out_of_step(), {})


class TestSeed(FunctionCase):
    def test_born_folder_is_seeded_with_todays_folders(self):
        self.assertEqual(functions.folders("library"), ["Biblioteca"])
        self.assertEqual(functions.folders("strongbox"), ["Cofre"])
        self.assertEqual(functions.folders("harness"), ["Harness"])

    def test_code_has_no_folder_until_chosen(self):
        self.assertEqual(functions.folders("code"), [])
        self.assertTrue(functions.enabled("code"))

    def test_the_four_functions_and_nothing_else(self):
        self.assertEqual(
            [row["function"] for row in functions.rows()],
            ["library", "strongbox", "code", "harness"],
        )

    def test_seed_twice_changes_nothing(self):
        self.assertEqual(functions.seed(), [])
        self.assertEqual(len(functions.rows()), 4)

    def test_seed_never_overwrites_a_row_a_person_edited(self):
        functions.set_folders("strongbox", ["Elsewhere"])
        functions.seed()
        self.assertEqual(functions.folders("strongbox"), ["Elsewhere"])

    def test_seed_follows_the_spelling_the_folder_carries(self):
        # An instance that kept the retired face of the library keeps it.
        (self.root / "Biblioteca").rename(self.root / "Arquivos")
        for row in store.load("function"):
            tables.delete("function", row["id"])
        functions.seed()
        self.assertEqual(functions.folders("library"), ["Arquivos"])

    def test_old_name_is_not_a_function(self):
        self.assertNotIn("Arquivos", [row["function"] for row in functions.rows()])
        with self.assertRaises(TableError):
            functions.row("files")

    def test_base_structure_is_outside_the_map(self):
        for name in ("projects", "shared", "app", "data", "convert"):
            self.assertNotIn(name, functions.FUNCTIONS)
            with self.assertRaises(TableError):
                functions.row(name)


class TestFolders(FunctionCase):
    def test_library_takes_several_folders(self):
        functions.set_folders("library", ["Biblioteca", "Notes/More", "/srv/docs"])
        self.assertEqual(
            functions.folders("library"), ["Biblioteca", "Notes/More", "/srv/docs"]
        )

    def test_the_others_take_one(self):
        for name in ("strongbox", "code", "harness"):
            with self.assertRaises(TableError):
                functions.set_folders(name, ["a", "b"])
        self.assertEqual(functions.folders("harness"), ["Harness"])

    def test_relative_resolves_against_the_working_folder(self):
        functions.set_folders("code", ["src/mine"])
        self.assertEqual(functions.resolved("code"), [paths.working_folder() / "src/mine"])

    def test_absolute_stays_where_it_is(self):
        outside = self.scratch.name + "-outside"
        functions.set_folders("code", [outside])
        self.assertEqual(functions.resolved("code"), [Path(outside)])

    def test_the_table_door_accepts_a_comma_list(self):
        row = functions.row("library")
        tables.edit("function", row["id"], {"folders": "A, /b"})
        self.assertEqual(functions.folders("library"), ["A", "/b"])


class TestEnabled(FunctionCase):
    def test_disabled_function_is_preserved_in_the_table(self):
        functions.set_folders("library", ["Biblioteca", "Extra"])
        functions.set_enabled("library", False)
        self.assertFalse(functions.enabled("library"))
        self.assertEqual(functions.folders("library"), ["Biblioteca", "Extra"])
        self.assertIn("library", [row["function"] for row in functions.rows()])

    def test_enable_again(self):
        functions.set_enabled("harness", False)
        functions.set_enabled("harness", True)
        self.assertTrue(functions.enabled("harness"))


class TestMigration(FunctionCase):
    def test_an_old_folder_gains_the_table_seeded_and_the_ceiling(self):
        for row in store.load("function"):
            tables.delete("function", row["id"])
        (self.root / "Tabelas" / "schema" / "function.json").unlink()
        schema.reset()
        store.reset()
        stamp = migrations.stamp_file()
        stamp.write_text("[" + ",".join(str(n) for n in range(1, 35)) + "]\n")
        with redirect_stdout(StringIO()):
            migrations.run()
        self.assertIsNotNone(schema.of("function"))
        self.assertEqual(functions.folders("library"), ["Biblioteca"])
        self.assertIn("function:edit", migrations.FUNCTION_PERMISSIONS)


if __name__ == "__main__":
    unittest.main()
