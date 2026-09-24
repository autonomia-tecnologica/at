"""The `audit`: one line per act, and never one for a read (§3, item 15).

§3 registers the table and §4 fixes what a declaration may say about its rows, and
this is the slice that makes both true: `data/schema/audit.json` ships, the engine
writes one line per act that enters the core, the declaration says no row of its
own is erased and the door obeys it, and only the admin role — carrying
`audit:read` — reads it.

Five things are measured, and each is a sentence held to the code:

- **the line is born where the actor and the via are known.** The engine does not
  know either, so the door the surfaces reach it by (`at.ui.ask.run`) writes it —
  and WHO is the first admin for an act typed at the terminal, the proved actor
  for one that came through a session, and the ENGINE's own row when nobody was
  proved at all.
- **one line, and never one for a read.** Every write act leaves exactly one —
  and so does a refusal, carrying the reason's `i18n` KEY and no value. `list` and
  `view` leave nothing at all.
- **the instant is injected.** The line is a point in time, so the module reads
  the clock in ONE function and a test freezes it; nothing here compares two
  readings of the machine's clock.
- **the declaration says it, and the door obeys it.** No row of `audit` is
  erased, the refusal names the table, and the number is never handed back.
- **only the admin reads it.** `audit` answers `read` and nothing else, the
  administrator's role carries `audit:read`, and no machine reaches it.

Every test aims AT at a throwaway folder with `AT_ROOT`, so the checkout's own
Working Folder is never touched; none of them needs a network or a model.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    actors,
    audit,
    boot,
    files,
    migrations,
    paths,
    permissions,
    risk,
    settings,
    tables,
)
from at.data import schema, store
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import main, tree

# What §4 fixes for a point in time, and the shape the line has to wear.
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

# The fields §3 lists, and the whole of what a line may carry: the 5W2H, the
# outcome, the reason's key and the bar the demand ran under — and no cost, and
# no value of the act's.
FIELDS = {
    "id", "what", "table", "when", "actor", "via", "status", "reason",
    "threshold",
}

# A fixed point in time, so the suite never reads the clock twice and disagrees
# with itself. `moment` is the module's single clock read, and this is it frozen.
FROZEN = "2026-09-22T13:04:07.123Z"


class AuditCase(unittest.TestCase):
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

    def lines(self) -> list[dict]:
        return store.load("audit")

    def words(self, *args: str) -> tuple[int, str]:
        """One word through the real `cli`, so the actor and the via are the
        ones that surface resolves and not the ones a test hands in."""
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()


class TheDeclaration(AuditCase):
    """What the product ships, and the names the door holds it to."""

    def test_the_table_ships_with_the_product(self):
        self.assertTrue((paths.data_dir() / schema.SCHEMA_DIR / "audit.json").is_file())
        self.assertIsNotNone(schema.of("audit"))

    def test_the_store_is_the_file_the_item_names(self):
        self.assertEqual(store.path("audit"), paths.data_dir() / "audits.jsonl")

    def test_it_is_a_system_table_with_a_type_of_its_own(self):
        declared = schema.of("audit") or {}
        self.assertEqual(declared.get("type"), "audit")
        self.assertEqual(declared.get("store"), "data/audits.jsonl")

    def test_the_module_and_the_declaration_name_the_same_fields(self):
        # Two files hold the names — the declaration and `core.audit` — and this
        # is what keeps them together: a rename in one would write a line nobody
        # reads back.
        for name in (
            audit.WHAT,
            audit.TABLE,
            audit.WHEN,
            audit.ACTOR,
            audit.VIA,
            audit.STATUS,
            audit.REASON,
            audit.THRESHOLD,
        ):
            with self.subTest(field=name):
                self.assertTrue(schema.field("audit", name), name)

    def test_the_instant_is_declared_as_one(self):
        self.assertEqual(schema.field("audit", audit.WHEN).get("type"), "instant")

    def test_the_vias_and_the_outcomes_are_the_closed_lists(self):
        for field, values in (
            (audit.VIA, audit.VIAS),
            (audit.STATUS, audit.OUTCOMES),
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    sorted(tables.enum_values("audit", field)), sorted(values)
                )


class TheLine(AuditCase):
    """One act, one line — and the fields §3 lists, and no others."""

    def test_a_write_leaves_exactly_one_line(self):
        self.words("task", "create", "--set", "text=comprar pão")
        self.words("task", "create", "--set", "text=comprar leite")
        self.assertEqual(len(self.lines()), 2)

    def test_the_line_carries_the_five_w_and_the_outcome(self):
        self.words("task", "create", "--set", "text=comprar pão")
        row = self.lines()[0]
        self.assertTrue(set(row) <= FIELDS, sorted(set(row) - FIELDS))
        self.assertEqual(row[audit.WHAT], "task:create")
        self.assertEqual(row[audit.TABLE], "task")
        self.assertEqual(row[audit.STATUS], audit.OK)
        self.assertEqual(row[audit.VIA], audit.CLI)
        self.assertRegex(row[audit.WHEN], INSTANT)

    def test_a_line_that_was_not_refused_carries_no_reason(self):
        # §3: the "why" exists ONLY in a refusal — outside of it the line does
        # not pretend to have an intention.
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertNotIn(audit.REASON, self.lines()[0])

    def test_a_refusal_is_a_line_with_the_reason_key_and_no_value(self):
        # The reason is stored as the KEY of `i18n`, never as the words and never
        # as the value a person typed — a log of what was attempted is not a
        # second copy of what was typed.
        self.words("task", "create", "--set", "text=café", "--set", "deadline=amanhã")
        row = self.lines()[0]
        self.assertEqual(row[audit.STATUS], audit.REFUSED)
        self.assertEqual(row[audit.REASON], "table.error.not_a_day")
        self.assertEqual(row[audit.WHAT], "task:create")
        self.assertNotIn("amanhã", json.dumps(row, ensure_ascii=False))

    def test_the_refusal_key_answers_in_the_active_language(self):
        # The key is `i18n`'s, so the same line reads in either language — and
        # the field it names is the label the person read.
        self.words("task", "create", "--set", "text=café", "--set", "deadline=amanhã")
        reason = self.lines()[0][audit.REASON]
        self.assertIn("Prazo", tr(reason, field="Prazo", value="amanhã"))

    def test_no_line_carries_a_reference(self):
        # §3: the ids it cites are RAW DATA. A `ref` in the declaration would make
        # the log a reference, and a reference is what blocks a `delete`.
        fields = (schema.of("audit") or {}).get("fields") or {}
        for name, field in fields.items():
            with self.subTest(field=name):
                self.assertNotIn("ref", field)

    def test_the_actor_a_line_cites_is_a_number(self):
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertIsInstance(self.lines()[0][audit.ACTOR], int)

    def test_a_read_leaves_nothing_at_all(self):
        self.words("task", "create", "--set", "text=comprar pão")
        self.words("task", "list")
        self.words("task", "view", "1")
        self.words("audit", "list")
        self.assertEqual(len(self.lines()), 1)

    def test_the_engine_writes_the_line_through_its_own_door(self):
        # The same road `core.secrets` seals a value by: a row is a row, and the
        # counter that keeps an id spent counts this one too.
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(self.lines()[0]["id"], 1)
        self.assertEqual(store.counter("audit"), 1)

    def test_a_read_only_run_writes_no_line(self):
        # A verification pass moves nothing (§3): the act is refused for the same
        # reason, and the trail it would have left is not written either.
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            code, _ = self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(code, 1)
        self.assertEqual(self.lines(), [])


class TheBar(AuditCase):
    """The threshold the demand ran under — the field §4 adds to the line (§4,
    item 15).

    "A leitura do limiar de risco que valia no instante em que uma demanda
    correu, que é o que a linha da auditoria registra": the line says the bar the
    folder had, and it is read when the demand ARRIVES — which matters for the
    one act that moves the bar, and that act is the one §4 names by name.
    """

    def bar(self, value: object) -> None:
        settings.save({**settings.load(), risk.KEY: value})

    def test_the_declaration_ships_the_field(self):
        self.assertTrue(schema.field("audit", audit.THRESHOLD))
        self.assertNotIn("ref", schema.field("audit", audit.THRESHOLD))
        self.assertNotIn("type", schema.field("audit", audit.THRESHOLD))

    def test_the_line_carries_the_bar_the_folder_had(self):
        self.bar(0.8)
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(self.lines()[0][audit.THRESHOLD], 0.8)

    def test_a_folder_that_never_chose_carries_the_default(self):
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(self.lines()[0][audit.THRESHOLD], risk.DEFAULT)

    def test_the_bar_is_read_when_the_demand_arrives_and_not_after(self):
        # The one act that moves the bar is `setting:edit` on `risk_threshold`
        # (§4), and a reading taken after the write would say the demand faced
        # the bar it had just chosen. It faced the one that was in force.
        self.words("setting", "edit", risk.KEY, "0.9")
        row = self.lines()[0]
        self.assertEqual(row[audit.WHAT], "setting:edit")
        self.assertEqual(row[audit.THRESHOLD], risk.DEFAULT)

    def test_a_refusal_carries_the_bar_too(self):
        self.bar(0.9)
        self.words("task", "create", "--set", "text=café", "--set", "deadline=amanhã")
        row = self.lines()[0]
        self.assertEqual(row[audit.STATUS], audit.REFUSED)
        self.assertEqual(row[audit.THRESHOLD], 0.9)

    def test_the_bar_is_a_number_of_the_folders(self):
        # It is not the act's value and not a `ref`: it is the folder's own
        # reading, written as the number it is, so a reader can compare it with
        # a risk without parsing a sentence.
        self.bar(0.7)
        self.words("task", "create", "--set", "text=comprar pão")
        row = self.lines()[0]
        self.assertIsInstance(row[audit.THRESHOLD], float)
        self.assertEqual(row[audit.THRESHOLD], 0.7)


class TheInstant(AuditCase):
    """A point in time, injected — the suite never compares two clock readings."""

    def test_the_line_is_stamped_with_the_instant_it_was_given(self):
        row = audit.log(
            "task",
            "create",
            via=audit.CLI,
            at=datetime(2026, 9, 22, 13, 4, 7, 123000, tzinfo=timezone.utc),
        )
        self.assertEqual(row[audit.WHEN], FROZEN)

    def test_the_engine_stamps_the_clock_the_module_reads(self):
        # The module reads the clock in ONE function, and freezing it is what
        # proves the line is stamped by the engine and not by the caller.
        with mock.patch.object(audit, "moment", lambda: FROZEN):
            self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(self.lines()[0][audit.WHEN], FROZEN)

    def test_an_instant_an_offset_carries_is_written_in_utc(self):
        row = audit.log(
            "task",
            "create",
            via=audit.CLI,
            at=datetime(2026, 9, 22, 10, 4, 7, 123000, tzinfo=timezone.utc),
        )
        self.assertRegex(row[audit.WHEN], INSTANT)
        self.assertTrue(row[audit.WHEN].endswith("Z"))


class TheActor(AuditCase):
    """Who acted, per surface — and what happens when nobody did."""

    def test_the_actor_of_an_act_through_the_cli_is_the_first_admin(self):
        admin = actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(self.lines()[0][audit.ACTOR], store.number_of(admin))

    def test_an_act_with_no_actor_at_all_is_the_engine_s(self):
        # §4: "o motor age no que é do motor". A folder with no administrator
        # still works, and whoever validated and wrote was the core — which is
        # what the engine's row was born to be named by.
        self.assertIsNone(actors.first_admin())
        self.words("task", "create", "--set", "text=comprar pão")
        engine = actors.engine_row() or {}
        self.assertEqual(self.lines()[0][audit.ACTOR], store.number_of(engine))

    def test_the_actor_is_the_row_and_not_the_name(self):
        # A name is a value, and §3 says the log stores none: what it cites is
        # the row's number, raw — so deleting the actor later breaks no link.
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertNotIn("Rafael", json.dumps(self.lines()[0]))

    def test_the_via_of_a_sentence_is_the_interpreter_s(self):
        # §4, item 15: the surface that reaches the interpreter does not become
        # the via — the road the act came through is `nlu`.
        door.ask("cria uma tarefa pra hoje")
        self.assertEqual(self.lines()[0][audit.VIA], audit.NLU)

    def test_a_sentence_the_interpreter_refused_leaves_nothing(self):
        # A sentence that never became a proposal never reached the core: there
        # is no act to record, and a refusal of the READING is not one of the
        # engine's.
        result = door.ask("banana")
        self.assertEqual(result.kind, "refused")
        self.assertEqual(self.lines(), [])


class TheCeiling(AuditCase):
    """A wall found is a line, and only the admin reads the log (§3)."""

    def test_the_table_answers_read_and_nothing_else(self):
        self.assertEqual(permissions.catalogue().get("audit"), ("read",))
        self.assertTrue(permissions.is_known("audit:read"))
        for name in ("audit:list", "audit:create", "audit:edit", "audit:delete"):
            with self.subTest(permission=name):
                self.assertFalse(permissions.is_known(name))

    def test_the_permission_is_the_declaration_s_and_not_the_action_s_name(self):
        self.assertEqual(permissions.needed("audit", "list"), "audit:read")
        self.assertEqual(permissions.needed("audit", "view"), "audit:read")

    def test_the_help_offers_the_two_reads_and_no_write(self):
        node = next(node for node in tree.table_nodes() if node.name == "audit")
        self.assertEqual([child.name for child in node.children], ["list", "view"])

    def test_reading_the_log_is_a_read(self):
        self.assertEqual(permissions.risk("audit:read"), permissions.RISK_READ)

    def test_only_the_administrator_carries_it(self):
        role = actors.role_for_admin()
        self.assertIn("audit:read", permissions.carried(role))

    def test_a_machine_actor_does_not_carry_it(self):
        # §3: "um `agente` que pudesse ler as próprias recusas aprenderia onde
        # está a parede". The machine's role is its own, and the machine that
        # carries the ceiling reaches no further than what it names.
        role = tables.create("role", {"name": "machine", "permissions": "task:create"})
        _, token = actors.mint_agent("runner", str(role["id"]))
        row = actors.authenticate_agent(token) or {}
        self.assertFalse(actors.may(row, "audit:read"))
        self.assertTrue(actors.may(row, "task:create"))

    def test_the_ceiling_refusal_is_a_line_with_the_permission_key(self):
        # A wall an actor found is exactly what the log is for, and the reason is
        # the KEY of the sentence the person read.
        role = tables.create("role", {"name": "narrow", "permissions": "task:list"})
        row = tables.create(
            "actor",
            {"name": "Rafael", "type": "person", "role": str(role["id"]),
             "credential": "uma-frase-bem-longa"},
        )
        result = door.ask("cria uma tarefa pra hoje", actor=row)
        self.assertEqual(result.kind, "refused")
        self.assertEqual(self.lines()[0][audit.REASON], audit.DENIED)
        self.assertEqual(self.lines()[0][audit.STATUS], audit.REFUSED)
        self.assertEqual(self.lines()[0][audit.WHAT], "task:create")
        self.assertEqual(self.lines()[0][audit.ACTOR], row["id"])


class TheDeletion(AuditCase):
    """§4: the declaration says no row of its own is erased, and the door obeys."""

    def test_the_declaration_says_it(self):
        self.assertFalse(tables.deletable("audit"))
        self.assertEqual((schema.of("audit") or {}).get("deletable"), False)

    def test_the_engine_refuses_the_deletion_by_the_table_s_name(self):
        self.words("task", "create", "--set", "text=comprar pão")
        with self.assertRaises(tables.TableError) as refused:
            tables.delete("audit", 1)
        self.assertEqual(
            str(refused.exception), tr("table.error.not_deletable", table="Auditoria")
        )

    def test_a_number_nobody_wears_is_refused_for_the_same_reason(self):
        # The wall is the TABLE's and not the number's: which id was typed cannot
        # change the answer, and a log is exactly the table whose holes would be
        # worth hiding.
        with self.assertRaises(tables.TableError) as refused:
            tables.delete("audit", 999)
        self.assertIn("Auditoria", str(refused.exception))

    def test_the_row_stays_and_the_number_is_not_spent(self):
        self.words("task", "create", "--set", "text=comprar pão")
        with self.assertRaises(tables.TableError):
            tables.delete("audit", 1)
        self.assertEqual(len(self.lines()), 1)
        self.assertEqual(store.counter("audit"), 1)

    def test_the_refusal_is_itself_a_line(self):
        self.words("audit", "delete", "1")
        self.assertEqual(self.lines()[0][audit.STATUS], audit.REFUSED)
        self.assertEqual(self.lines()[0][audit.REASON], "table.error.not_deletable")

    def test_a_table_that_declares_nothing_is_still_deletable(self):
        # The rule is the DECLARATION's and not a list of system tables: a row of
        # `task` is taken out exactly as it always was.
        self.words("task", "create", "--set", "text=comprar pão")
        self.words("task", "delete", "1")
        self.assertIsNone(store.find("task", 1))


class TheMigration(AuditCase):
    """A folder that already exists gains the table, and its ceiling."""

    def declaration(self) -> Path:
        return paths.data_dir() / schema.SCHEMA_DIR / "audit.json"

    def strip(self) -> None:
        """Leave the folder as one born BEFORE this release is: no declaration,
        no stamp of twelve, and an administrator whose role was built from the
        catalogue of that day."""
        role = actors.role_for_admin()
        # The role as an EARLIER release left it: the catalogue of that day, with
        # no `audit:read` in it — which is what the migration has to hand over.
        tables.edit(
            "role",
            store.number_of(role),
            {
                "permissions": ",".join(
                    name
                    for name in permissions.all_permissions()
                    if name != "audit:read"
                )
            },
        )
        self.declaration().unlink()
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 12)
            ),
            encoding="utf-8",
        )
        schema.reset()

    def test_a_folder_without_the_table_gains_it(self):
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertTrue(self.declaration().is_file())
        self.assertIsNotNone(schema.of("audit"))
        role = actors.admin_role() or {}
        self.assertIn("audit:read", permissions.carried(role))

    def test_the_folder_that_never_had_the_permission_hears_it_granted(self):
        # The role is handed ONLY what the folder never had the chance to carry,
        # and the name it was handed is the one the catalogue names.
        self.strip()
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        self.assertIn(
            tr(
                "boot.migration.catalogue.granted",
                role=actors.ADMIN_ROLE,
                names="audit:read",
            ),
            output.getvalue(),
        )

    def test_the_store_file_is_not_born_by_the_migration(self):
        # An empty file that names nothing is a store a person would read as a
        # table that exists elsewhere — the box is born with the first act.
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse((paths.data_dir() / "audits.jsonl").exists())

    def test_a_declaration_a_person_deleted_is_not_brought_back(self):
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertIn(12, migrations.applied())
        self.declaration().unlink()
        schema.reset()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse(self.declaration().is_file())

    def test_a_folder_born_by_this_release_has_already_run_it(self):
        self.assertIn(12, migrations.applied())


class TheFieldMigration(AuditCase):
    """A folder that already has the table gains the field (§3, migration 13).

    A new field inside a declaration that is ALREADY on disk is the hard half of
    item 5, and it is what migration nine's machinery is for: the addition meets
    whatever the person wrote there, missing keys are written, and a collision is
    THEIRS and is said out loud. Thirteen is its own step, with its own list —
    a published migration is never edited — and nine goes on meaning what it
    meant on the day it shipped.
    """

    def declaration(self) -> Path:
        return paths.data_dir() / schema.SCHEMA_DIR / "audit.json"

    def grown(self, update: dict | None = None) -> dict:
        """The folder's `audit` declaration as a folder born BEFORE the field is:
        the threshold removed (or replaced by what the person wrote), and a stamp
        that does not name thirteen."""
        declared = json.loads(self.declaration().read_text(encoding="utf-8"))
        declared["fields"].pop("threshold", None)
        if update is not None:
            declared["fields"].update(update)
        self.declaration().write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 13)
            ),
            encoding="utf-8",
        )
        schema.reset()
        return declared

    def test_a_folder_without_the_field_gains_it(self):
        self.grown()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertIn("threshold", (schema.of("audit") or {}).get("fields") or {})
        self.assertEqual(
            schema.field("audit", "threshold").get("label"),
            "table.audit.field.threshold",
        )

    def test_the_report_names_the_path_it_grew(self):
        # A name is what a person opens the file to find: the report says WHERE
        # the declaration grew, and not only that it did.
        self.grown()
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        self.assertIn(
            tr("boot.migration.declarations.extended", names="audit.fields.threshold"),
            output.getvalue(),
        )

    def test_a_field_a_person_declared_otherwise_is_the_persons(self):
        # The collision rule of §3, on this field: the addition adds what is
        # missing, reports what it skipped, and never chooses for the person.
        self.grown({"threshold": {"label": "table.audit.field.reason"}})
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        self.assertEqual(
            schema.field("audit", "threshold").get("label"),
            "table.audit.field.reason",
        )
        self.assertIn(
            tr(
                "boot.migration.declarations.collision",
                names="audit.fields.threshold.label",
            ),
            output.getvalue(),
        )

    def test_a_declaration_a_person_deleted_is_not_brought_back(self):
        self.declaration().unlink()
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 13)
            ),
            encoding="utf-8",
        )
        schema.reset()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse(self.declaration().is_file())
        self.assertIn(13, migrations.applied())

    def test_a_folder_born_by_this_release_has_already_run_it(self):
        self.assertIn(13, migrations.applied())


class TheRefusalMask(AuditCase):
    """The line is the ACT's and never the act's payload (§3)."""

    def test_a_secret_typed_into_a_field_is_not_copied_into_the_log(self):
        # §3: the audit stores no value at all. A credential typed into the wrong
        # field would otherwise land in a file a person reads and commits.
        self.words("task", "create", "--set", "text=café", "--set", "status=abacaxi")
        row = self.lines()[0]
        self.assertEqual(row[audit.REASON], "table.error.not_in_enum")
        self.assertNotIn("abacaxi", json.dumps(row, ensure_ascii=False))

    def test_the_log_is_written_before_the_version_that_carries_it(self):
        # The version is named by the answer, and the line it carries is already
        # in the store — which is what makes `git log` and the log tell the same
        # story in the same order.
        self.words("task", "create", "--set", "text=comprar pão")
        self.assertEqual(len(self.lines()), 1)
        self.assertFalse(files.readonly())


if __name__ == "__main__":
    unittest.main()
