"""The migration framework: a folder that already exists changes under it.

Updating AT is replacing the binary inside the folder, so a release that
changes the folder's structure has to bring the change with it and apply it on
the first start after the swap (§3). These tests build folders in the shapes
earlier releases left them in and prove three things:

- a folder that has NOT migrated is still read as a Working Folder — never as a
  folder that is new, which is the defect migration number one exists for;
- the rename that touches the person's own folders asks first, says what breaks
  outside, and whoever declines keeps the name they had;
- the stamp keeps a migration from running twice, and a read-only run from
  running at all;
- a folder that already existed gains the note that presents it, and a note the
  folder already carried is never overwritten.

Every test aims AT at a throwaway folder with `AT_ROOT`.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, migrations, paths, permissions, reminder, settings, tables
from at.data import schema, store
from at.ui import ask as door


class FolderCase(unittest.TestCase):
    """A throwaway folder, and the answers a person would give."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.answers: list[str] = []
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def answer(self, question: str) -> str:
        """What a person reads so far, kept at the moment of the question — the
        whole point of the notice is that it comes BEFORE the answer."""
        self.answers.append(question)
        self.said.append(self.buffer.getvalue())
        return self.asked.pop(0) if self.asked else "s"

    def caught_up(self, *answers: str) -> str:
        self.asked = list(answers)
        self.answers = []
        self.said = []
        self.buffer = StringIO()
        with redirect_stdout(self.buffer):
            boot.ensure_working_folder(ask=self.answer)
        return self.buffer.getvalue()

    def born(self, language: str = "pt_BR") -> None:
        """A folder in the shape this release writes: the CURRENT structure."""
        with redirect_stdout(StringIO()):
            boot.create_working_folder()
        (self.root / "App" / "i18n" / "active").write_text(
            language + "\n", encoding="utf-8"
        )
        i18n.reset()

    def forgotten(self) -> None:
        """Forget the stamp, so every migration runs as on the first start after
        a binary swap — which is the state the whole door exists for."""
        (self.root / "App" / "migrations").unlink()
        schema.reset()

    def declaration(self, table: str) -> Path:
        """The folder's copy of a table's declaration, where a person edits it."""
        return self.root / "Tabelas" / "schema" / f"{table}.json"

    def rewrite(self, where: Path, declared: dict) -> None:
        """A declaration written the way a hand would write it: the folder's, and
        not AT's. The indent is deliberately not the one `seed` writes, so a
        test that says "the file was not touched" reads the bytes and not the
        content."""
        where.write_text(
            json.dumps(declared, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        schema.reset()

    def legacy(self, instance: str = "app", language: str = "pt_BR") -> None:
        """A folder as an earlier release left it: the instance in `instance/`
        and the person's folders under their OLD spelling."""
        where = self.root / instance
        (where / "i18n").mkdir(parents=True)
        (where / "settings.json").write_text('{"schema": 1}\n', encoding="utf-8")
        (where / "i18n" / "active").write_text(language + "\n", encoding="utf-8")
        for name in ("data", "prose"):
            (self.root / name).mkdir(exist_ok=True)
        # The system tables an earlier release seeded, under their OLD spelling:
        # the declaration carries the internal name `data/`, so it travels with
        # the rename without being rewritten.
        schema.seed(self.root / "data" / schema.SCHEMA_DIR)
        (self.root / "data" / "tasks.jsonl").write_text(
            json.dumps({"id": 1, "text": "café", "status": "todo"}) + "\n",
            encoding="utf-8",
        )
        i18n.reset()


# --------------------------------------------------- a folder is found ---


class AnOldFolderIsStillAWorkingFolder(FolderCase):
    """The defect the framework exists to close: a folder that has not migrated
    must never read as a folder that is new — AT would otherwise offer to
    create a Working Folder on top of the one that is already there."""

    def test_the_old_instance_folder_is_read_as_configured(self):
        self.legacy(".bill")
        self.assertTrue(boot.is_configured())

    def test_the_first_run_is_never_offered(self):
        self.legacy("app")
        output = self.caught_up()
        self.assertNotIn(i18n.tr("boot.first_run.notice", folder=self.root), output)

    def test_the_settings_survive_the_move(self):
        self.legacy("app")
        self.caught_up()
        self.assertTrue((self.root / "App" / "settings.json").is_file())
        self.assertEqual(settings.load()["schema"], settings.SCHEMA)


# ------------------------------------------------------------ the moves ---


class TheInstanceFolderMoves(FolderCase):
    def test_the_hidden_spelling_becomes_the_visible_one(self):
        self.legacy(".bill")
        output = self.caught_up()
        self.assertFalse((self.root / ".bill").exists())
        self.assertTrue((self.root / "App" / "settings.json").is_file())
        self.assertIn(i18n.tr("boot.migration.legacy.moved"), output)

    def test_both_moves_land_in_one_start(self):
        # `.bill/` is two renames away from `App/`, and a folder that jumped
        # both used to be told about neither.
        self.legacy(".bill")
        output = self.caught_up()
        self.assertIn(i18n.tr("boot.migration.legacy.moved"), output)
        self.assertIn(i18n.tr("boot.migration.capital.moved"), output)

    def test_a_folder_already_named_right_is_not_touched(self):
        # A folder from a release between the two renames: `App/` already, and
        # the person's folders still under their old spelling.
        self.legacy("App")
        output = self.caught_up("s")
        self.assertIn(i18n.tr("boot.migration.capital.kept"), output)
        self.assertTrue((self.root / "App" / "settings.json").is_file())

    def test_a_filesystem_that_cannot_tell_the_two_spellings_apart(self):
        # macOS and Windows: `App/` and `app/` are ONE name, so the second
        # exists before there is anything to move. A symlink is that case made
        # portable — `samefile` is what tells it from a real collision.
        self.legacy("app")
        (self.root / "App").symlink_to(self.root / "app", target_is_directory=True)
        output = self.caught_up("s")
        self.assertIn(i18n.tr("boot.migration.capital.same"), output)
        self.assertTrue((self.root / "App" / "settings.json").is_file())

    def test_two_folders_with_one_name_are_reported_and_not_merged(self):
        self.legacy("app")
        (self.root / "App").mkdir()
        (self.root / "App" / "settings.json").write_text('{"schema": 9}\n', encoding="utf-8")
        output = self.caught_up("s")
        self.assertIn(i18n.tr("boot.migration.capital.collision"), output)
        # Neither wins: the migration does not choose between two instances, and
        # both are left exactly where they were for the person to settle.
        self.assertEqual(
            (self.root / "app" / "settings.json").read_text(encoding="utf-8"),
            '{"schema": 1}\n',
        )
        self.assertEqual(
            (self.root / "App" / "settings.json").read_text(encoding="utf-8"),
            '{"schema": 9}\n',
        )


# ------------------------------------------------ the person's folders ---


class TheFoldersFollowTheLanguage(FolderCase):
    def test_each_report_arrives_with_its_own_migration(self):
        # The notice belongs to the third migration. A report collected into a
        # list and printed at the end arrives AFTER the question it does not
        # belong to — which is what the folders migration would then be
        # explaining backwards.
        self.legacy("app")
        output = self.caught_up("s")
        self.assertLess(
            output.index(i18n.tr("boot.migration.capital.moved")),
            output.index(i18n.tr("boot.migration.folders.notice", names="data → Tabelas, prose → Arquivos")),
        )

    def test_the_rename_is_offered_and_applied(self):
        self.legacy("app")
        output = self.caught_up("s")
        self.assertTrue((self.root / "Tabelas").is_dir())
        self.assertTrue((self.root / "Arquivos").is_dir())
        self.assertFalse((self.root / "data").exists())
        self.assertFalse((self.root / "prose").exists())
        self.assertIn("data → Tabelas", output)

    def test_what_breaks_outside_is_said_before_the_question(self):
        self.legacy("app")
        self.caught_up("n")
        names = "data → Tabelas, prose → Arquivos"
        self.assertIn(i18n.tr("boot.migration.folders.notice", names=names), self.said[0])
        self.assertEqual(self.answers[0], i18n.tr("boot.migration.folders.confirm", names=names))

    def test_whoever_declines_keeps_the_name_and_hears_the_cost(self):
        self.legacy("app")
        output = self.caught_up("n")
        self.assertTrue((self.root / "data").is_dir())
        self.assertFalse((self.root / "Tabelas").exists())
        self.assertIn(i18n.tr("boot.migration.folders.declined", names="data → Tabelas, prose → Arquivos"), output)

    def test_a_declined_folder_is_still_found_and_used(self):
        # The whole point of the tolerance: declining must leave AT WORKING,
        # not leave it looking at a folder that is not there.
        self.legacy("app")
        self.caught_up("n")
        self.assertEqual(paths.data_dir(), self.root / "data")
        self.assertTrue(store.path("task").parent == self.root / "data")
        self.assertEqual(tables.rows("task")[0]["text"], "café")

    def test_without_a_terminal_nothing_moves(self):
        self.legacy("app")
        output = StringIO()
        with mock.patch("sys.stdin.isatty", return_value=False):
            with redirect_stdout(output):
                boot.ensure_working_folder()
        self.assertTrue((self.root / "data").is_dir())
        self.assertFalse((self.root / "Tabelas").exists())
        self.assertIn(i18n.tr("boot.migration.folders.no_tty"), output.getvalue())

    def test_a_terminal_in_front_is_asked(self):
        # `at-cli <word>` passes no `ask`: the door to the terminal belongs to
        # boot. Without it the migration would decline to move a folder with
        # the person sitting right in front of it.
        self.legacy("app")
        with mock.patch("sys.stdin.isatty", return_value=True):
            with mock.patch("builtins.input", return_value="s"):
                with redirect_stdout(StringIO()):
                    boot.ensure_working_folder()
        self.assertTrue((self.root / "Tabelas").is_dir())

    def test_the_two_that_are_only_named_are_born(self):
        self.legacy("app")
        output = self.caught_up("s")
        self.assertTrue((self.root / "Projetos").is_dir())
        self.assertTrue((self.root / "Compartilhada").is_dir())
        self.assertEqual(list((self.root / "Compartilhada").iterdir()), [])
        self.assertIn(i18n.tr("boot.migration.folders.born", names="Projetos, Compartilhada"), output)

    def test_the_harness_folder_arrives_by_its_own_migration(self):
        # A folder from the release before this one: the two named folders are
        # there, the stamp is at four, and `Harness/` does not exist. Migration
        # three is published — folders have already run it — so the third name
        # is born by a step of its own instead of by an edit to that one.
        self.born()
        (self.root / "Harness").rmdir()
        migrations.stamp_file().write_text(
            json.dumps([1, 2, 3, 4]) + "\n", encoding="utf-8"
        )
        output = self.caught_up()
        self.assertTrue((self.root / "Harness").is_dir())
        self.assertEqual(list((self.root / "Harness").iterdir()), [])
        self.assertIn(i18n.tr("boot.migration.folders.born", names="Harness"), output)

    def test_two_folders_for_one_internal_name_are_not_chosen_between(self):
        self.legacy("app")
        (self.root / "Tabelas").mkdir()
        output = self.caught_up("s")
        self.assertIn(i18n.tr("boot.migration.folders.collision", names="data"), output)
        self.assertTrue((self.root / "data").is_dir())

    def test_the_cofre_folder_arrives_by_its_own_migration(self):
        # TASK-152/TASK-154: uma pasta nascida antes deste release não tem
        # `Cofre/`, e é a migração 19 que a traz — a mesma forma da 5
        # (`Harness/`), publicada e nunca editada.
        self.born()
        (self.root / "Cofre").rmdir()
        migrations.stamp_file().write_text(
            json.dumps(list(range(1, 19))) + "\n", encoding="utf-8"
        )
        output = self.caught_up()
        self.assertTrue((self.root / "Cofre").is_dir())
        self.assertEqual(list((self.root / "Cofre").iterdir()), [])
        self.assertIn(i18n.tr("boot.migration.folders.born", names="Cofre"), output)

    def test_the_convert_folder_arrives_by_its_own_migration(self):
        # TASK-165: uma pasta nascida antes deste release não tem
        # `Convertidos/`, e é a migração 22 que a traz — a mesma forma da 19
        # (`Cofre/`), publicada e nunca editada.
        self.born()
        (self.root / "Convertidos").rmdir()
        migrations.stamp_file().write_text(
            json.dumps(list(range(1, 22))) + "\n", encoding="utf-8"
        )
        output = self.caught_up()
        self.assertTrue((self.root / "Convertidos").is_dir())
        self.assertEqual(list((self.root / "Convertidos").iterdir()), [])
        self.assertIn(i18n.tr("boot.migration.folders.born", names="Convertidos"), output)


class TheServicesFindTheirHouse(FolderCase):
    """Migration vinte e seis: os serviços do caminho hospedado passam a morar
    sob `App/services/` (§7), a mesma casa dos serviços do caminho container."""

    def loose(self) -> None:
        """Uma pasta como o caminho hospedado a deixava: os serviços soltos na
        raiz de `App/`, e o cache do Jev como um arquivo."""
        app = self.root / "App"
        for name in ("caddy", "authelia", "push", "gitleaks"):
            (app / name).mkdir(parents=True, exist_ok=True)
            (app / name / "stamp").write_text("x\n", encoding="utf-8")
        (app / "jev-cache.json").write_text("{}\n", encoding="utf-8")

    def test_every_service_loose_in_app_moves_under_their_house(self):
        self.born()
        self.loose()
        self.forgotten()
        output = self.caught_up()
        app = self.root / "App"
        for name in ("caddy", "authelia", "push", "gitleaks"):
            self.assertTrue((app / "services" / name / "stamp").is_file())
            self.assertFalse((app / name).exists())
        self.assertFalse((app / "jev-cache.json").exists())
        self.assertTrue((app / "services" / "jev" / "cache.json").is_file())
        self.assertIn(
            i18n.tr(
                "boot.migration.services.moved",
                names="caddy, authelia, push, gitleaks, jev-cache.json",
            ),
            output,
        )

    def test_a_destination_that_already_existed_keeps_what_it_had(self):
        self.born()
        self.loose()
        # O caminho container já tinha posto o Caddyfile dele no destino; o do
        # caminho hospedado tem o MESMO nome, e o que chegou primeiro fica.
        container = self.root / "App" / "services" / "caddy"
        container.mkdir(parents=True, exist_ok=True)
        (container / "Caddyfile").write_text("container\n", encoding="utf-8")
        (self.root / "App" / "caddy" / "Caddyfile").write_text("hosted\n", encoding="utf-8")
        self.forgotten()
        output = self.caught_up()
        self.assertEqual(
            (container / "Caddyfile").read_text(encoding="utf-8"), "container\n"
        )
        self.assertTrue((container / "stamp").is_file())
        self.assertIn(
            i18n.tr("boot.migration.services.collision", names="caddy/Caddyfile"),
            output,
        )

    def test_a_folder_with_nothing_loose_has_nothing_to_move(self):
        self.born()
        self.forgotten()
        output = self.caught_up()
        self.assertIn(i18n.tr("boot.migration.services.kept"), output)


# ------------------------------------------------------- the declaration ---


class ADeclaredPathResolvesByName(FolderCase):
    """§3: a folder that changes its name changes a path, and every declared
    path changes with it, in the same move. The declaration carries the
    INTERNAL name, and the resolution is what knows the face."""

    def test_the_store_follows_the_folder(self):
        self.legacy("app")
        self.caught_up("s")
        self.assertEqual(store.path("task"), self.root / "Tabelas" / "tasks.jsonl")

    def test_a_declaration_the_instance_wrote_itself_is_taken_as_written(self):
        self.born()
        self.assertEqual(store.path("task"), self.root / "Tabelas" / "tasks.jsonl")
        (self.root / "Tabelas" / "schema" / "meu.json").write_text(
            json.dumps({
                "id": "meu", "order": 90, "store": "minhas/coisas.jsonl",
                "fields": {"id": {"label": "table.field.id"}},
            }),
            encoding="utf-8",
        )
        schema.reset()
        self.assertEqual(store.path("meu"), self.root / "minhas" / "coisas.jsonl")


class TheDeclarationGrows(FolderCase):
    """The hard half of item 5: a migration that touches the DECLARATION.

    A release that adds a key to a declaration of the product carries the
    addition and merges it into the folder's copy — a file a PERSON edits. This
    is where "never overwrites" gets its real test, because a rename has nothing
    to collide with: what is missing is added, the person's edit beats AT at
    every collision, and the report names the path instead of choosing.

    The folder is born by this release and then worn back to the shape an
    earlier one left it in — a declaration is the one thing a fixture can age
    without a filesystem.
    """

    def worn(self, table: str, drop) -> Path:
        """The folder's declaration of `table`, as an earlier release left it."""
        where = self.declaration(table)
        declared = json.loads(where.read_text(encoding="utf-8"))
        drop(declared)
        self.rewrite(where, declared)
        return where

    def test_the_type_a_field_was_missing_arrives(self):
        self.born()

        def before(declared):
            for field in ("since", "deadline"):
                declared["fields"][field].pop("type", None)
            declared["fields"]["modifications"]["append"].pop("type", None)
            declared.pop("lifecycle", None)

        where = self.worn("task", before)
        self.forgotten()
        output = self.caught_up()
        declared = json.loads(where.read_text(encoding="utf-8"))
        self.assertEqual(declared["fields"]["since"]["type"], "day")
        self.assertEqual(declared["fields"]["deadline"]["type"], "day")
        self.assertEqual(declared["fields"]["modifications"]["append"]["type"], "instant")
        self.assertEqual(declared["lifecycle"]["cancel"]["status"], "cancelled")
        self.assertIn(
            i18n.tr(
                "boot.migration.declarations.extended",
                names="task.fields.since.type, task.fields.deadline.type, "
                      "task.fields.modifications.append.type, task.lifecycle",
            ),
            output,
        )

    def test_the_edit_a_person_made_survives_the_merge(self):
        self.born()

        def before(declared):
            declared["fields"]["text"]["max_length"] = 200
            declared["fields"]["meu_campo"] = {"label": "table.field.id"}
            declared.pop("lifecycle", None)

        where = self.worn("task", before)
        self.forgotten()
        self.caught_up()
        declared = json.loads(where.read_text(encoding="utf-8"))
        # What the person wrote is theirs, and what the release adds lands beside
        # it: the two are not the same kind of thing, and the merge keeps both.
        self.assertEqual(declared["fields"]["text"]["max_length"], 200)
        self.assertIn("meu_campo", declared["fields"])
        self.assertEqual(declared["lifecycle"]["cancel"]["status"], "cancelled")

    def test_a_collision_is_named_and_the_edit_wins(self):
        self.born()

        def before(declared):
            declared["fields"]["since"]["type"] = "text"
            declared.pop("lifecycle", None)

        where = self.worn("task", before)
        self.forgotten()
        output = self.caught_up()
        declared = json.loads(where.read_text(encoding="utf-8"))
        self.assertEqual(declared["fields"]["since"]["type"], "text")
        self.assertIn(
            i18n.tr(
                "boot.migration.declarations.collision",
                names="task.fields.since.type",
            ),
            output,
        )
        # The report does not stop the rest: what did not collide still arrives.
        self.assertEqual(declared["lifecycle"]["cancel"]["status"], "cancelled")

    def test_a_declaration_the_person_deleted_is_not_brought_back(self):
        self.born()
        where = self.declaration("task")
        where.unlink()
        schema.reset()
        self.forgotten()
        output = self.caught_up()
        self.assertFalse(where.exists())
        self.assertIn(
            i18n.tr("boot.migration.declarations.missing", names="task"), output
        )

    def test_a_declaration_left_unreadable_is_not_touched(self):
        self.born()
        where = self.declaration("task")
        where.write_text("{ isto não é json\n", encoding="utf-8", newline="\n")
        schema.reset()
        self.forgotten()
        output = self.caught_up()
        # Rewriting it would destroy whatever the person put there — and a file
        # that is there and does not parse is not the same thing as one absent.
        self.assertEqual(where.read_text(encoding="utf-8"), "{ isto não é json\n")
        self.assertIn(
            i18n.tr("boot.migration.declarations.unreadable", names="task"), output
        )

    def test_a_folder_that_already_carried_everything_is_not_rewritten(self):
        self.born()
        where = self.declaration("task")
        declared = json.loads(where.read_text(encoding="utf-8"))
        self.rewrite(where, declared)
        before = where.read_text(encoding="utf-8")
        self.forgotten()
        output = self.caught_up()
        # Nothing to add means no write at all: reformatting the file of somebody
        # who did not need migrating would be AT editing what it may only read.
        self.assertEqual(where.read_text(encoding="utf-8"), before)
        self.assertIn(i18n.tr("boot.migration.declarations.unchanged"), output)


class TheMechanismGrowsAnyDeclaration(FolderCase):
    """The primitive behind the migration, on a table of the INSTANCE's own.

    The product's additions are dated and named at module level, so the three
    kinds a release may add — a field, a value of a closed vocabulary, an entry
    of a list — are proved here, on a declaration this test writes, the same way
    item 15's first slice proved the declared types on a table of its own.
    """

    def declare(self, declared: dict) -> Path:
        where = self.root / "Tabelas" / "schema" / f"{declared['id']}.json"
        where.parent.mkdir(parents=True, exist_ok=True)
        self.rewrite(where, declared)
        return where

    def mine(self) -> Path:
        return self.declare(
            {
                "id": "meu",
                "order": 90,
                "store": "minhas/coisas.jsonl",
                "columns": ["nome"],
                "fields": {
                    "id": {"label": "table.field.id"},
                    "nome": {"label": "table.field.id", "type": "number"},
                    "status": {"label": "table.field.id", "enum": {"aberto": "x"}},
                },
            }
        )

    def test_a_field_a_closed_value_and_an_entry_all_arrive(self):
        where = self.mine()
        grown = schema.extend(
            "meu",
            {
                "fields": {
                    "peso": {"label": "table.field.id", "type": "number"},
                    "status": {"enum": {"fechado": "y"}},
                },
                "columns": ["status"],
            },
        )
        self.assertEqual(grown.state, "written")
        self.assertEqual(
            list(grown.added),
            ["fields.peso", "fields.status.enum.fechado", "columns"],
        )
        self.assertEqual(grown.collisions, ())
        declared = json.loads(where.read_text(encoding="utf-8"))
        self.assertEqual(declared["fields"]["peso"]["type"], "number")
        # The vocabulary gains the value it lacked and keeps the ones it had.
        self.assertEqual(declared["fields"]["status"]["enum"]["fechado"], "y")
        self.assertEqual(declared["fields"]["status"]["enum"]["aberto"], "x")
        # An entry is APPENDED, never reordered: the order is the declaration's.
        self.assertEqual(declared["columns"], ["nome", "status"])

    def test_an_entry_the_list_already_carried_is_not_repeated(self):
        self.mine()
        grown = schema.extend("meu", {"columns": ["nome"]})
        self.assertEqual(grown.added, ())
        self.assertEqual(grown.collisions, ())
        declared = json.loads(self.declaration("meu").read_text(encoding="utf-8"))
        self.assertEqual(declared["columns"], ["nome"])

    def test_a_collision_is_named_and_the_file_is_not_rewritten(self):
        where = self.mine()
        before = where.read_text(encoding="utf-8")
        grown = schema.extend("meu", {"fields": {"nome": {"type": "text"}}})
        self.assertEqual(grown.added, ())
        self.assertEqual(grown.collisions, ("fields.nome.type",))
        self.assertEqual(where.read_text(encoding="utf-8"), before)
        declared = json.loads(before)
        self.assertEqual(declared["fields"]["nome"]["type"], "number")

    def test_what_is_not_there_to_grow_says_which_of_the_two_it_is(self):
        where = self.mine()
        where.unlink()
        schema.reset()
        self.assertEqual(schema.extend("meu", {"columns": ["x"]}).state, "missing")
        where.write_text("não é json\n", encoding="utf-8", newline="\n")
        grown = schema.extend("meu", {"columns": ["x"]})
        self.assertEqual(grown.state, "unreadable")
        self.assertEqual(where.read_text(encoding="utf-8"), "não é json\n")


class TheBacklogArrives(FolderCase):
    """Migration fifteen: a folder that already exists gains what the queue needs.

    The backlog moving into the tables is a DECLARATION change and nothing else —
    the `priority` the order is computed from, the `planned` step between
    "decided" and "started", the declared order itself, and the `project` column
    the task listing was missing. A row is never touched: a project written
    before the field landed reads as the declared default where the order is
    computed, and that is the one place an old row and a new one have to agree.
    """

    def old_project(self) -> dict:
        """`project.json` as the release before this one wrote it."""
        declared = json.loads(self.declaration("project").read_text(encoding="utf-8"))
        declared["fields"].pop("priority", None)
        declared["fields"]["status"]["enum"].pop("planned", None)
        declared["fields"]["status"]["show"] = ["idea", "active", "paused"]
        declared.pop("sort", None)
        declared["columns"] = ["status", "name"]
        return declared

    def old_task(self) -> dict:
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        declared["columns"] = ["status", "priority", "text"]
        return declared

    def old_folder(self) -> None:
        """A folder born before this release, with the rows it already had."""
        self.born()
        self.rewrite(self.declaration("project"), self.old_project())
        self.rewrite(self.declaration("task"), self.old_task())
        (self.root / "Tabelas" / "projects.jsonl").write_text(
            json.dumps({"id": 1, "name": "Autonomia", "status": "active"}) + "\n",
            encoding="utf-8",
        )
        self.forgotten()

    def test_an_old_folder_gains_the_field_the_queue_is_ordered_by(self):
        self.old_folder()
        said = self.caught_up()
        declared = json.loads(self.declaration("project").read_text(encoding="utf-8"))
        self.assertEqual(declared["sort"], {"by": "priority", "direction": "desc", "then": "id"})
        self.assertEqual(declared["fields"]["priority"]["default"], "medium")
        self.assertIn("priority", declared["columns"])
        self.assertIn("project.fields.priority", said)
        self.assertIn("project.sort", said)

    def test_an_old_folder_gains_the_step_between_decided_and_started(self):
        self.old_folder()
        self.caught_up()
        status = json.loads(self.declaration("project").read_text(encoding="utf-8"))["fields"]["status"]
        self.assertIn("planned", status["enum"])
        self.assertIn("planned", status["show"])

    def test_the_task_listing_gains_the_project_column(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        self.assertIn("project", declared["columns"])

    def test_a_row_that_predates_the_field_gains_the_declared_default(self):
        # A linha não é sobrescrita: ela RECEBE o valor que a declaração já dava
        # a ela — o mesmo que a ordem vinha lendo de lá —, e todo o resto dela
        # fica como estava.
        self.old_folder()
        where = self.root / "Tabelas" / "projects.jsonl"
        said = self.caught_up()
        rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["priority"], "medium")
        self.assertEqual(rows[0]["name"], "Autonomia")
        self.assertEqual(rows[0]["status"], "active")
        self.assertIn("PROJECT-1", said)

    def test_a_priority_the_person_already_wrote_is_not_overwritten(self):
        self.old_folder()
        where = self.root / "Tabelas" / "projects.jsonl"
        where.write_text(
            json.dumps({"id": 1, "name": "Autonomia", "status": "active",
                        "priority": "critical"}) + "\n",
            encoding="utf-8",
        )
        self.caught_up()
        rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[0]["priority"], "critical")

    def test_an_edit_the_person_made_is_not_overwritten(self):
        self.old_folder()
        declared = self.old_project()
        # A person who put an entry of their own in the listing keeps it, and
        # what arrives lands BESIDE it — the merge only ever adds.
        declared["columns"] = ["status", "name", "deadline"]
        self.rewrite(self.declaration("project"), declared)
        self.caught_up()
        columns = json.loads(self.declaration("project").read_text(encoding="utf-8"))["columns"]
        self.assertEqual(columns, ["status", "name", "deadline", "priority"])

    def test_a_folder_that_already_carried_everything_is_not_rewritten(self):
        self.born()
        self.forgotten()
        where = self.declaration("project")
        before = where.read_text(encoding="utf-8")
        self.caught_up()
        self.assertEqual(where.read_text(encoding="utf-8"), before)


class TheTagsArrive(FolderCase):
    """Migration seventeen: a task carries the tag the backlog is sliced by.

    The fatia stops being a project or a subproject and becomes the set of tasks
    that carry the same tag. It is a DECLARATION change and nothing else — the
    `tags` list and the column the listing shows it in — and no row is touched:
    a task without the field already reads as the empty list the default names.
    """

    def old_task(self) -> dict:
        """`task.json` as the release before this one wrote it."""
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        declared["fields"].pop("tags", None)
        declared["columns"] = ["status", "priority", "text", "project"]
        return declared

    def old_folder(self) -> None:
        self.born()
        self.rewrite(self.declaration("task"), self.old_task())
        self.forgotten()

    def test_an_old_folder_gains_the_field_the_backlog_is_sliced_by(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        tags = declared["fields"]["tags"]
        self.assertEqual(tags["type"], "list")
        self.assertEqual(tags["default"], [])
        self.assertTrue(tags["filterable"])
        self.assertTrue(tags["searchable"])
        # Who writes a tag is the backlog session, and not the screen.
        self.assertNotIn("editable", tags)

    def test_the_task_listing_gains_the_tag_column(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        self.assertIn("tags", declared["columns"])

    def test_a_row_that_predates_the_field_is_not_rewritten(self):
        # A decisão: o default é lista VAZIA, e uma linha sem o campo já lê como
        # vazia — a listagem junta o que encontra, e um campo ausente não junta
        # nada. Encher toda tarefa com `[]` seria a migração reescrevendo o
        # arquivo inteiro para dizer o que a leitura já diz.
        self.born()
        self.rewrite(self.declaration("task"), self.old_task())
        where = self.root / "Tabelas" / "tasks.jsonl"
        where.write_text(
            json.dumps({"id": 1, "text": "café", "status": "todo"}) + "\n",
            encoding="utf-8",
        )
        self.forgotten()
        self.caught_up()
        rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]
        self.assertNotIn("tags", rows[0])
        self.assertEqual(rows[0]["text"], "café")


class TheEditedAtArrives(FolderCase):
    """Migration vinte e um: a tarefa carrega o instante que o motor offline
    compara (TASK-162, fatia 1)."""

    def old_task(self) -> dict:
        """`task.json` como a versão anterior a esta escrevia."""
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        declared["fields"].pop("edited_at", None)
        return declared

    def old_folder(self) -> None:
        self.born()
        self.rewrite(self.declaration("task"), self.old_task())
        self.forgotten()

    def test_an_old_folder_gains_the_field_the_offline_motor_compares(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("task").read_text(encoding="utf-8"))
        edited_at = declared["fields"]["edited_at"]
        self.assertEqual(edited_at["type"], "instant")
        self.assertTrue(edited_at["touch"])

    def test_a_row_that_predates_the_field_is_not_rewritten(self):
        self.born()
        self.rewrite(self.declaration("task"), self.old_task())
        where = self.root / "Tabelas" / "tasks.jsonl"
        where.write_text(
            json.dumps({"id": 1, "text": "café", "status": "todo"}) + "\n",
            encoding="utf-8",
        )
        self.forgotten()
        self.caught_up()
        rows = [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]
        self.assertNotIn("edited_at", rows[0])
        self.assertEqual(rows[0]["text"], "café")

    def test_the_next_write_of_that_row_touches_it(self):
        self.born()
        self.rewrite(self.declaration("task"), self.old_task())
        where = self.root / "Tabelas" / "tasks.jsonl"
        where.write_text(
            json.dumps({"id": 1, "text": "café", "status": "todo"}) + "\n",
            encoding="utf-8",
        )
        self.forgotten()
        self.caught_up()
        row = tables.edit("task", 1, {"text": "café, agora com leite"})
        self.assertIn("edited_at", row)


class TheNotificationGuardArrives(FolderCase):
    """Migration vinte e três: a declaração da pasta aprende o que duas trocas
    anteriores acrescentaram ao produto em silêncio.

    O caso que a fez existir é o LEMBRETE. `at.ui.ask.remind` empurra e só então
    marca a linha (`reminder.mark_notified`), e é a marca que impede o mesmo
    lembrete de ser empurrado a cada passagem do relógio. Numa pasta cuja
    declaração não tem `notified`, `tables.edit` recusa o nome: o push SAI e a
    marca não fica — e o lembrete volta a cada cadência, dez minutos, para
    sempre.
    """

    def old_reminder(self) -> dict:
        """`reminder.json` como a versão anterior a esta escrevia."""
        declared = json.loads(self.declaration("reminder").read_text(encoding="utf-8"))
        declared["fields"].pop("notified", None)
        return declared

    def old_folder(self) -> None:
        """A pasta de antes: a declaração do lembrete sem a marca, e as duas
        que carregam o preço de editar um papel sem o número."""
        self.born()
        self.rewrite(self.declaration("reminder"), self.old_reminder())
        for table, field in (("actor", "role"), ("role", "permissions")):
            declared = json.loads(self.declaration(table).read_text(encoding="utf-8"))
            declared["fields"][field].pop("risk", None)
            self.rewrite(self.declaration(table), declared)
        self.forgotten()

    def a_reminder(self) -> dict:
        return tables.create(
            "reminder",
            {"text": "Beber água", "freq": "daily", "at": ["09:00"],
             "status": "active", "since": "2026-09-01"},
        )

    def sent(self):
        """O `send` do round: o que saiu, e sem rede nenhuma."""
        calls: list[str] = []

        def push(title: str, body: str, key) -> tuple[bool, str]:
            calls.append(body)
            return True, "200"

        return calls, push

    def test_an_old_folder_gains_the_field_the_round_marks_with(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("reminder").read_text(encoding="utf-8"))
        notified = declared["fields"]["notified"]
        self.assertEqual(notified["label"], "table.reminder.field.notified")
        self.assertTrue(notified["filterable"])
        # Sem `type`: o campo é do round e nunca é digitado por uma pessoa — a
        # mesma razão que `at/core/reminder.py` escreve.
        self.assertNotIn("type", notified)

    def test_without_the_field_the_mark_is_refused_which_is_the_bug(self):
        # A razão de a migração existir, provada pelo lado que dói: nesta pasta a
        # marca não pode ser escrita, e o push que já saiu voltaria a sair.
        self.born()
        self.rewrite(self.declaration("reminder"), self.old_reminder())
        made = self.a_reminder()
        with self.assertRaises(tables.TableError):
            reminder.mark_notified(made, date(2026, 9, 29), "09:00")

    def test_once_the_field_arrives_the_round_marks_and_the_push_stops(self):
        self.old_folder()
        self.caught_up()
        made = self.a_reminder()
        calls, push = self.sent()
        moment = datetime(2026, 9, 29, 9, 0)  # the pass that covers the 09:00 hour
        self.assertEqual(door.remind(moment, send=push), [made])
        self.assertEqual(len(calls), 1)
        held = store.find("reminder", store.number_of(made))
        self.assertEqual(held.get("notified"), ["2026-09-29 09:00"])
        # O segundo passe não repete: é isto que a migração entrega.
        self.assertEqual(door.remind(moment, send=push), [])
        self.assertEqual(len(calls), 1)

    def test_an_old_folder_gains_the_price_of_editing_a_role(self):
        self.old_folder()
        self.caught_up()
        for table, field in (("actor", "role"), ("role", "permissions")):
            with self.subTest(table=table):
                declared = json.loads(
                    self.declaration(table).read_text(encoding="utf-8")
                )
                self.assertEqual(declared["fields"][field]["risk"], 0.95)

    def test_a_price_the_person_already_wrote_is_kept_and_named(self):
        self.born()
        declared = json.loads(self.declaration("role").read_text(encoding="utf-8"))
        declared["fields"]["permissions"]["risk"] = 0.5
        self.rewrite(self.declaration("role"), declared)
        self.forgotten()
        output = self.caught_up()
        declared = json.loads(self.declaration("role").read_text(encoding="utf-8"))
        self.assertEqual(declared["fields"]["permissions"]["risk"], 0.5)
        self.assertIn(
            i18n.tr(
                "boot.migration.declarations.collision",
                names="role.fields.permissions.risk",
            ),
            output,
        )


class TheNotesArrive(FolderCase):
    """Migração trinta: a tabela das notas, e o nome que o lembrete perdeu.

    A palavra "nota" nomeia UMA coisa — a TABELA. O `reminder` tinha um campo
    com esse nome, e uma palavra que nomeia duas não nomeia nenhuma: o
    interpretador recusa a frase que diz as duas (`nlu.error.two_tables`).

    A migração traz a tabela nova (a declaração é empacotada e o `seed` a
    escreve onde está AUSENTE), renomeia o campo do lembrete na DECLARAÇÃO e
    nas LINHAS — o motor sabe mudar o valor de um campo e não sabe TIRAR uma
    chave de uma linha, e uma renomeação é exatamente isso —, e dá ao papel do
    administrador as permissões que a tabela nova acrescenta.
    """

    def old_reminder(self) -> dict:
        """`reminder.json` como a versão anterior a esta escrevia: o campo
        chamava-se `note`."""
        declared = json.loads(self.declaration("reminder").read_text(encoding="utf-8"))
        fields = declared["fields"]
        fields["note"] = fields.pop("remark")
        fields["note"]["label"] = "table.reminder.field.note"
        return declared

    def a_role_of_the_day_before(self) -> None:
        """O papel do administrador, como ele nasceu ANTES da tabela nova: com
        o catálogo que existia naquele dia, e sem uma permissão `note:`."""
        tables.create(
            "role",
            {
                "name": "admin",
                "permissions": [
                    permission
                    for permission in permissions.all_permissions()
                    if not permission.startswith("note:")
                ],
            },
        )

    def old_folder(self) -> None:
        """A pasta de antes: a declaração do lembrete com o nome velho, a
        declaração das notas ausente, e um lembrete que dizia o que dizia."""
        self.born()
        self.rewrite(self.declaration("reminder"), self.old_reminder())
        (self.root / "Tabelas" / "schema" / "note.json").unlink()
        self.a_role_of_the_day_before()
        (self.root / "Tabelas" / "reminders.jsonl").write_text(
            json.dumps(
                {
                    "id": 1,
                    "text": "Beber água",
                    "note": "depois do almoço",
                    "freq": "daily",
                    "at": ["09:00"],
                    "status": "active",
                    "since": "2026-09-01",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        self.forgotten()

    def reminders(self) -> list[dict]:
        where = self.root / "Tabelas" / "reminders.jsonl"
        return [json.loads(line) for line in where.read_text(encoding="utf-8").splitlines()]

    def test_an_old_folder_gains_the_declaration_of_the_notes(self):
        self.old_folder()
        self.caught_up()
        self.assertTrue(self.declaration("note").is_file())
        declared = json.loads(self.declaration("note").read_text(encoding="utf-8"))
        self.assertEqual(declared["primary"], "text")
        self.assertEqual(declared["columns"], ["text", "tags"])

    def test_the_declaration_of_the_reminder_carries_the_new_name(self):
        self.old_folder()
        self.caught_up()
        fields = json.loads(
            self.declaration("reminder").read_text(encoding="utf-8")
        )["fields"]
        self.assertIn("remark", fields)
        self.assertNotIn("note", fields)
        # O rótulo segue o nome quando ele é o do produto — a convenção
        # `table.<tabela>.field.<nome>` — e uma mão que escreveu o seu fica.
        self.assertEqual(fields["remark"]["label"], "table.reminder.field.remark")

    def test_the_line_keeps_what_it_said(self):
        self.old_folder()
        self.caught_up()
        rows = self.reminders()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("note", rows[0])
        self.assertEqual(rows[0]["remark"], "depois do almoço")
        self.assertEqual(rows[0]["text"], "Beber água")

    def test_the_output_names_the_line_that_changed(self):
        self.old_folder()
        output = self.caught_up()
        self.assertIn(
            i18n.tr("boot.migration.reminder.renamed", names="Beber água"), output
        )

    def test_the_administrator_carries_the_permissions_of_the_new_table(self):
        self.old_folder()
        self.caught_up()
        held = permissions.carried(actors.admin_role())
        for action in tables.ACTIONS:
            self.assertIn(f"note:{action}", held)

    def test_a_declaration_carrying_both_names_is_left_alone(self):
        # A COLISÃO: a pasta que já tem os DOIS nomes é uma pasta em que o
        # nome velho ainda existe, e aí nada é escrito — nem na declaração nem
        # nas linhas. A migração diz isso e não escolhe.
        self.born()
        declared = json.loads(self.declaration("reminder").read_text(encoding="utf-8"))
        declared["fields"]["note"] = {
            "label": "table.reminder.field.note",
            "type": "markdown",
            "searchable": True,
        }
        self.rewrite(self.declaration("reminder"), declared)
        (self.root / "Tabelas" / "schema" / "note.json").unlink()
        self.forgotten()
        self.caught_up()
        fields = json.loads(
            self.declaration("reminder").read_text(encoding="utf-8")
        )["fields"]
        self.assertIn("note", fields)
        self.assertIn("remark", fields)

    def test_a_folder_born_today_is_not_rewritten(self):
        # Uma pasta que já fala o nome novo não tem linha nenhuma para mover, e
        # o arquivo das linhas não é reescrito para dizer o que a leitura já
        # diz.
        self.born()
        where = self.root / "Tabelas" / "reminders.jsonl"
        where.write_text(
            json.dumps(
                {"id": 1, "text": "Beber água", "freq": "daily", "at": ["09:00"]},
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        before = where.read_text(encoding="utf-8")
        self.forgotten()
        self.caught_up()
        self.assertEqual(where.read_text(encoding="utf-8"), before)


# ------------------------------------------------------------- the stamp ---


class TheStamp(FolderCase):
    def test_a_migration_runs_once(self):
        self.legacy("app")
        self.caught_up("s")
        # The second start has nothing left to do, so it asks nothing.
        again = StringIO()
        with redirect_stdout(again):
            boot.ensure_working_folder(ask=lambda question: self.fail("asked again"))
        self.assertNotIn(i18n.tr("boot.migration.folders.notice", names="data → Tabelas, prose → Arquivos"), again.getvalue())

    def test_the_stamp_names_what_ran(self):
        self.legacy("app")
        self.caught_up("s")
        stamp = json.loads((self.root / "App" / "migrations").read_text(encoding="utf-8"))
        self.assertEqual(stamp, sorted(item.ident for item in migrations.MIGRATIONS))

    def test_a_read_only_run_moves_nothing(self):
        self.legacy("app")
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            self.caught_up("s")
        self.assertTrue((self.root / "app").is_dir())
        self.assertFalse((self.root / "App").exists())


# ---------------------------------------------------------- the language ---


class TheLanguageOffer(FolderCase):
    """Not a migration: a migration runs once, and the language changes again
    tomorrow. What is remembered is the decision."""

    def silent(self, *answers: str) -> str:
        """A start with no `$AT_LANG`: the folder's language is the one that
        speaks, which is the only one that may move the person's folders."""
        without = {name: value for name, value in os.environ.items() if name != i18n.LANG_ENV}
        self.asked = list(answers)
        self.answers = []
        self.said = []
        self.buffer = StringIO()
        with mock.patch.dict(os.environ, without, clear=True):
            i18n.reset()
            with redirect_stdout(self.buffer):
                boot.ensure_working_folder(ask=self.answer)
        return self.buffer.getvalue()

    def changed_to(self, language: str) -> None:
        (self.root / "App" / "i18n" / "active").write_text(language + "\n", encoding="utf-8")
        i18n.reset()

    def test_a_new_language_offers_the_rename(self):
        self.born("pt_BR")
        self.changed_to("en_US")
        output = self.silent("s")
        self.assertTrue((self.root / "Tables").is_dir())
        self.assertIn("Tabelas → Tables", output)

    def test_declining_keeps_the_name_and_is_not_asked_again(self):
        self.born("pt_BR")
        self.changed_to("en_US")
        first = self.silent("n")
        # All four folders follow the language, and the cost is said for each of
        # them: whoever declines keeps the names and hears what that costs.
        self.assertIn(
            i18n.tr(
                "boot.migration.folders.declined",
                names="Tabelas → Tables, Arquivos → Files, "
                      "Projetos → Projects, Compartilhada → Shared",
            ),
            first,
        )
        self.assertTrue((self.root / "Tabelas").is_dir())
        # The decision is recorded, so the next start is silent about it.
        second = self.silent("n")
        self.assertEqual(second, "")
        self.assertEqual(settings.get("folders"), "en_US")

    def test_the_named_folders_follow_the_language_too(self):
        # `Projetos/` and `Compartilhada/` are spelled by the language like the
        # other two, and a folder that changed language carries all four — it
        # does not keep one spelling and gain a twin in the other.
        self.born("pt_BR")
        self.changed_to("en_US")
        self.silent("s")
        for name in ("Tables", "Files", "Projects", "Shared"):
            with self.subTest(folder=name):
                self.assertTrue((self.root / name).is_dir(), name)
        for name in ("Tabelas", "Arquivos", "Projetos", "Compartilhada"):
            with self.subTest(folder=name):
                self.assertFalse((self.root / name).exists(), name)

    def test_a_declined_folder_gains_no_empty_twin(self):
        # The refusal is the person's, and the folder they kept is the one AT
        # reads: `paths` answers with the active language's name first, so a
        # twin born empty beside it would take the old one's place — which is
        # the contents of the folder they refused to move, gone from view.
        self.born("pt_BR")
        self.changed_to("en_US")
        self.silent("n")
        self.assertTrue((self.root / "Projetos").is_dir())
        self.assertFalse((self.root / "Projects").exists())
        self.assertEqual(paths.projects_dir(), self.root / "Projetos")
        self.assertEqual(paths.shared_dir(), self.root / "Compartilhada")

    def test_the_environment_never_moves_the_folders(self):
        # `$AT_LANG` is not the folder's decision, and renaming the person's
        # folders to follow something that temporary is not the promise.
        self.born("pt_BR")
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.caught_up()
        self.assertTrue((self.root / "Tabelas").is_dir())
        self.assertFalse((self.root / "Tables").exists())


# ------------------------------------------------------------- the note ---


class TheFolderPresentsItself(FolderCase):
    """`AGENT.md` — the note whoever starts inside the folder reads (§0).

    A folder born now carries it from `boot`; a folder that was already on disk
    when the note was decided gains it here. It is the plainest case of "adds
    what is missing and overwrites nothing", which is why it does not ask.
    """

    def test_a_folder_that_already_existed_gains_the_note(self):
        self.legacy("app")
        self.assertFalse((self.root / "AGENT.md").exists())
        output = self.caught_up()
        note = self.root / "AGENT.md"
        self.assertTrue(note.is_file())
        self.assertEqual(note.read_text(encoding="utf-8"), i18n.tr("folder.agent.body"))
        self.assertIn(i18n.tr("boot.migration.note.written"), output)

    def test_a_note_the_folder_already_carried_is_left_alone(self):
        self.legacy("app")
        (self.root / "AGENT.md").write_text("o que eu escrevi\n", encoding="utf-8", newline="\n")
        output = self.caught_up()
        self.assertEqual(
            (self.root / "AGENT.md").read_text(encoding="utf-8"), "o que eu escrevi\n"
        )
        self.assertIn(i18n.tr("boot.migration.note.kept"), output)

    def test_the_note_arrives_once(self):
        # The stamp is what makes the second start silent: a note that came back
        # would be a note arguing with whoever deleted it.
        self.legacy("app")
        self.caught_up()
        (self.root / "AGENT.md").unlink()
        output = self.caught_up()
        self.assertFalse((self.root / "AGENT.md").exists())
        self.assertNotIn(i18n.tr("boot.migration.note.written"), output)


class TheProjectDescriptionGainsATeto(FolderCase):
    """Migration vinte e quatro: o projeto não é a task — o resumo é dele, a
    prosa mora na task. Uma pasta antiga, sem o teto, ganha o `max_length`."""

    def old_project(self) -> dict:
        declared = json.loads(self.declaration("project").read_text(encoding="utf-8"))
        declared["fields"]["desc"].pop("max_length", None)
        return declared

    def old_folder(self) -> None:
        self.born()
        self.rewrite(self.declaration("project"), self.old_project())
        self.forgotten()

    def test_an_old_folder_gains_the_ceiling(self):
        self.old_folder()
        self.caught_up()
        declared = json.loads(self.declaration("project").read_text(encoding="utf-8"))
        self.assertEqual(declared["fields"]["desc"]["max_length"], 200)

    def test_without_the_ceiling_a_biblia_is_accepted_which_is_the_bug(self):
        self.born()
        self.rewrite(self.declaration("project"), self.old_project())
        made = tables.create("project", {"name": "AT", "status": "active"})
        tables.edit("project", made["id"], {"desc": "x" * 500})

    def test_once_the_ceiling_arrives_a_biblia_is_refused(self):
        self.old_folder()
        self.caught_up()
        made = tables.create("project", {"name": "AT", "status": "active"})
        with self.assertRaises(tables.TableError):
            tables.edit("project", made["id"], {"desc": "x" * 500})


if __name__ == "__main__":
    unittest.main()
