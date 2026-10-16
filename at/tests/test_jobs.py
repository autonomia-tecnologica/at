"""The job that waits, and who approves — item 15's fourth slice (§4).

The demand filter is complete here: a demand carries a risk, the folder a
threshold, and the act that cannot run becomes a row of the `job` table instead
of a queue. What this module measures, in the order the item decided it:

- **the table.** `data/schema/job.json` ships, the first run seeds it, a folder
  that already exists gains it by migration, and the declaration says what the
  item says: the act, the arguments, the actor that owns it, the instant and the
  state of its life.
- **who waits is about presence, not about type.** The act a person types or
  clicks never waits — the act IS the approval — and an act that runs on its own
  waits at or above the threshold. The two marks of that absence are the via
  `engine` and an actor that is a machine.
- **the answer names the job**, and the demand that waited leaves NO line: §3
  writes a line for every write and every refusal, and a demand that waits is
  neither. What records it is the row.
- **the job runs by `at-cli job run`**, with the via `engine` and with the actor
  that owns it, so its ceiling is that actor's.
- **the approval is a line of its own**, with its actor and its via, separate
  from the job that waited — and no machine actor carries `job:approve` or
  `job:refuse`, for the reason §3 gives for `audit:read`.
- **and none of it needs a network**, which one test says out loud.

Every test aims AT at a throwaway folder with `AT_ROOT`, so the checkout's own
Working Folder is never touched.
"""

from __future__ import annotations

import io
import json
import os
import re
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    actors,
    audit,
    boot,
    clock,
    jobs,
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

# What §4 fixes for a point in time: the job's `when` is stamped like the log's.
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

# The fields the item names, and the whole of what a job may carry: the act it
# performs, the arguments it needs, the actor that owns it, the instant it
# arrived and the state of its life.
FIELDS = {"id", "what", "table", "arguments", "actor", "when", "status"}

CREDENTIAL = "uma-frase-bem-longa"


class JobCase(unittest.TestCase):
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

    # -- the doors a test reads as what it does -----------------------------

    def words(self, *args: str) -> tuple[int, str]:
        """One word through the real `cli`, so the actor and the via are the
        ones that surface resolves and not the ones a test hands in."""
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def lines(self) -> list[dict]:
        return store.load("audit")

    def held(self) -> list[dict]:
        return store.load(jobs.JOB)

    def job_row(self, number: int = 1) -> dict:
        return store.find(jobs.JOB, number) or {}

    # -- the two actors, so the presence rule has somebody to be about ------

    def person(self) -> dict:
        """The first administrator, which is the actor of an act typed at the
        terminal — and a person, which is what never waits."""
        return actors.create_admin("Rafael", CREDENTIAL)

    def machine(self, carried: str = "task:delete,task:create") -> dict:
        """An `agent` wearing a role of its own — a machine, and therefore
        somebody who is not there to answer."""
        role = tables.create("role", {"name": "runner", "permissions": carried})
        _, token = actors.mint_agent("runner", str(store.number_of(role)))
        return actors.authenticate_agent(token) or {}

    def bar(self, value: object) -> None:
        settings.save({**settings.load(), risk.KEY: value})

    def adjust(self, written: dict) -> None:
        """The per-action adjustment §5 promises, written the way the door does."""
        settings.save({**settings.load(), risk.BY_ACTION: written})


class TheDeclaration(JobCase):
    """What the product ships, and the names the module holds it to."""

    def test_the_table_ships_with_the_product(self):
        self.assertTrue((paths.data_dir() / schema.SCHEMA_DIR / "job.json").is_file())
        self.assertIsNotNone(schema.of("job"))

    def test_the_id_is_singular_and_the_rows_go_in_the_plural(self):
        # §4, Tabelas: the identity is an id and the id is singular, and the file
        # of ROWS is the one that goes in the plural — which is why the schema is
        # `job.json` and the store is `jobs.jsonl`.
        declared = schema.of("job") or {}
        self.assertEqual(declared.get("id"), "job")
        self.assertEqual(declared.get("store"), "data/jobs.jsonl")
        self.assertEqual(store.path("job"), paths.data_dir() / "jobs.jsonl")

    def test_it_is_a_system_table_with_a_type_of_its_own(self):
        declared = schema.of("job") or {}
        self.assertEqual(declared.get("type"), "job")
        self.assertIn("job", [d.get("id") for d in schema.declared()])

    def test_the_module_and_the_declaration_name_the_same_fields(self):
        # Two files hold the names — the declaration and `core.jobs` — and this
        # is what keeps them together: a rename in one would write a row nobody
        # reads back.
        for name in (
            jobs.WHAT,
            jobs.TABLE,
            jobs.ARGUMENTS,
            jobs.ACTOR,
            jobs.WHEN,
            jobs.STATUS,
        ):
            with self.subTest(field=name):
                self.assertTrue(schema.field("job", name), name)

    def test_the_states_are_the_closed_list(self):
        # The four item 15 decided — the one that says it waits, and what each
        # answer leaves: a person approved it, a person refused it, or the engine
        # ran it — plus the one item 24 added, which is the state the clock
        # drives and the only one a job that recurs ever rests in.
        self.assertEqual(
            sorted(tables.enum_values("job", jobs.STATUS)), sorted(jobs.STATES)
        )
        self.assertEqual(
            jobs.STATES, ("waiting", "approved", "refused", "done", "scheduled")
        )

    def test_the_instant_is_declared_as_one(self):
        self.assertEqual(schema.field("job", jobs.WHEN).get("type"), "instant")

    def test_no_field_of_the_job_is_a_reference(self):
        # The actor it names is a raw number, exactly as the `audit` cites one:
        # a `ref` would make the job a reference, and a reference is what blocks
        # a `delete` (§4) — an actor nobody can remove because a finished job
        # still points at it would be the log arguing with the folder.
        fields = (schema.of("job") or {}).get("fields") or {}
        for name, field in fields.items():
            with self.subTest(field=name):
                self.assertNotIn("ref", field)

    def test_the_block_carries_every_word_in_both_languages(self):
        # A label is an `i18n` key and never the text (§4), so the declarations
        # are held to the blocks: the table's name, every field's label and every
        # closed value reads in the active language.
        # `Jobs` é o nome do produto e não se traduz: a mesma palavra nas duas
        # línguas (a pedido da pessoa, 2026-10-05).
        self.assertEqual(tables.table_name("job", many=True), "Jobs")
        self.assertEqual(tables.label("job", jobs.STATUS), "Estado")
        self.assertEqual(tables.enum_label("job", jobs.STATUS, jobs.WAITING), "Esperando")
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(tables.table_name("job", many=True), "Jobs")
            self.assertEqual(tables.enum_label("job", jobs.STATUS, jobs.DONE), "Done")


class TheCatalogue(JobCase):
    """The object in the catalogue: six permissions, and seven words."""

    def test_it_answers_a_read_a_run_the_approval_and_the_schedule(self):
        self.assertEqual(
            permissions.catalogue().get("job"),
            ("read", "run", "approve", "refuse", "declare", "disable"),
        )
        for name, known in (
            ("job:read", True),
            ("job:run", True),
            ("job:approve", True),
            ("job:refuse", True),
            ("job:declare", True),
            ("job:disable", True),
            # The engine's six are NOT the job's: nothing creates a job by hand,
            # and nothing edits or deletes one — the row is the engine's record.
            ("job:list", False),
            ("job:create", False),
            ("job:edit", False),
            ("job:cancel", False),
            ("job:delete", False),
        ):
            with self.subTest(permission=name):
                self.assertIs(permissions.is_known(name), known)

    def test_the_permission_is_the_declaration_s_and_not_the_action_s_name(self):
        self.assertEqual(permissions.needed("job", "list"), "job:read")
        self.assertEqual(permissions.needed("job", "view"), "job:read")
        self.assertEqual(permissions.needed("job", "run"), "job:run")
        self.assertEqual(permissions.needed("job", "approve"), "job:approve")
        self.assertEqual(permissions.needed("job", "declare"), "job:declare")
        self.assertEqual(permissions.needed("job", "disable"), "job:disable")

    def test_the_tree_offers_the_seven_words(self):
        node = next(node for node in tree.table_nodes() if node.name == "job")
        self.assertEqual(
            [child.name for child in node.children],
            ["list", "view", "run", "approve", "refuse", "declare", "disable"],
        )
        # The six the engine does not have are named by the catalogue's block
        # and not by the engine's: a `Node.about` is an i18n KEY, and a key the
        # block does not carry would be drawn as the key itself.
        about = {child.name: child.about for child in node.children}
        self.assertEqual(about["run"], "permission.action.run")
        self.assertEqual(about["approve"], "permission.action.approve")
        self.assertEqual(about["refuse"], "permission.action.refuse")
        self.assertEqual(about["declare"], "permission.action.declare")
        self.assertEqual(about["disable"], "permission.action.disable")
        self.assertEqual(about["list"], "table.action.list")
        self.assertEqual(tr(about["approve"]), "Aprovar")
        self.assertEqual(tr(about["declare"]), "Declarar")
        self.assertEqual(tr(about["disable"]), "Desligar")

    def test_a_machine_actor_does_not_carry_the_approval(self):
        # §4: "nenhum ator de máquina carrega `job:approve` nem `job:refuse`",
        # for the reason §3 gives for `audit:read`: an agent that could release
        # its own waiting demand would have opened the door it was held behind.
        # The machine's role is its own, and it names no approval.
        row = self.machine("task:delete")
        self.assertFalse(actors.may(row, "job:approve"))
        self.assertFalse(actors.may(row, "job:refuse"))
        self.assertTrue(actors.may(row, "task:delete"))

    def test_only_the_administrator_carries_the_approval(self):
        role = actors.role_for_admin()
        for name in (
            "job:read", "job:run", "job:approve", "job:refuse",
            "job:declare", "job:disable",
        ):
            with self.subTest(permission=name):
                self.assertIn(name, permissions.carried(role))

    def test_the_run_is_a_write_and_the_approval_is_the_ceiling_s(self):
        # The numbers the catalogue declares, on §4's own scale: `run` and
        # `declare` are acts that write, approving or refusing is the person's
        # word over a demand the bar held — "the bar does not lower itself" —
        # and disabling removes what a schedule's rounds would still have been.
        self.assertEqual(permissions.risk("job:read"), permissions.RISK_READ)
        self.assertEqual(permissions.risk("job:run"), permissions.RISK_WRITE)
        self.assertEqual(permissions.risk("job:approve"), permissions.RISK_ALLOW)
        self.assertEqual(permissions.risk("job:refuse"), permissions.RISK_ALLOW)
        self.assertEqual(permissions.risk("job:declare"), permissions.RISK_WRITE)
        self.assertEqual(permissions.risk("job:disable"), permissions.RISK_REMOVE)
        # And approving/refusing are priced TOGETHER: a cheaper refusal would be
        # a way of learning about a dearer approval.
        for name in permissions.all_permissions():
            with self.subTest(permission=name):
                self.assertLess(permissions.risk(name), risk.CEILING)


class TheFilter(JobCase):
    """Who waits: at or above the bar, and nobody present to answer (§4)."""

    def test_a_person_s_act_never_waits(self):
        # The act a person types or clicks IS the approval, and asking again
        # would be theatre. It is true AT the bar and above it.
        self.person()
        code, text = self.words("task", "delete", "1")
        self.assertNotIn(tr("job.waits", id="JOB-1"), text)
        self.assertEqual(self.held(), [])

    def test_the_person_s_act_above_the_bar_runs_too(self):
        # The bar is the person's own setting, and it is what a demand is
        # measured against — the act does not stop being the approval because the
        # number went up.
        self.bar(1.0)
        self.person()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "para deletar"})
        code, text = self.words("task", "delete", "1")
        self.assertEqual(code, 0)
        self.assertEqual(self.held(), [])
        self.assertIsNone(store.find("task", 1))

    def test_a_folder_that_asks_nobody_is_a_person_at_the_terminal(self):
        # §3's loopback with no credential is a person in front of the machine,
        # and the `cli` is local by construction: an act typed there is the
        # owner's, and it does not wait for somebody who is already there.
        self.assertIsNone(actors.first_admin())
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "para deletar"})
        code, _ = self.words("task", "delete", "1")
        self.assertEqual(code, 0)
        self.assertEqual(self.held(), [])

    def test_the_machine_s_act_at_the_bar_waits_and_the_answer_names_the_job(self):
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        code, answer, row, _, _ = door.run(
            "task", "delete", ["1"], actor=machine, via=audit.WEBAPP
        )
        self.assertEqual(code, 0)
        self.assertIsNone(row)
        self.assertEqual(answer, tr("job.waits", id="JOB-1"))
        self.assertEqual(len(self.held()), 1)

    def test_below_the_bar_the_machine_s_act_runs(self):
        machine = self.machine()
        code, answer, row, _, _ = door.run(
            "task", "create", ["--set", "text=do agente"], actor=machine, via=audit.WEBAPP
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.held(), [])
        self.assertIsNotNone(row)

    def test_the_via_engine_waits_with_a_person_s_own_actor(self):
        # The mark of an act that runs on its own is the VIA: what comes through
        # `engine` was not typed or clicked by anybody, whoever owns it. It is
        # how the person's own nightly job waits — and the act the person typed
        # beside it does not.
        person = self.person()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "para deletar"})
        with redirect_stdout(StringIO()):
            code, answer, _, _, _ = door.run(
                "task", "delete", ["1"], actor=person, via=audit.ENGINE
            )
        self.assertEqual(answer, tr("job.waits", id="JOB-1"))
        self.assertEqual(len(self.held()), 1)
        with redirect_stdout(StringIO()):
            code, answer, _, _, _ = door.run(
                "task", "delete", ["1"], actor=person, via=audit.CLI
            )
        self.assertEqual(code, 0)

    def test_a_sentence_through_the_interpreter_waits_for_a_machine(self):
        # The demand is the actor's and not the surface's: a sentence typed in
        # the WebApp is the person's, and the same sentence asked with a machine
        # as its actor is the machine's.
        machine = self.machine("task:create,task:list")
        self.bar(0.2)  # a create is a write, and the bar is the folder's own
        result = door.ask("cria uma tarefa pra amanhã", actor=machine)
        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, tr("job.waits", id="JOB-1"))
        self.assertEqual(len(self.held()), 1)
        self.assertEqual(self.job_row()[jobs.ACTOR], store.number_of(machine))
        # And the same sentence for the person IS the approval: it runs.
        result = door.ask("cria uma tarefa pra amanhã", actor=self.person())
        self.assertEqual(result.text, tr("table.created", id="TASK-1"))
        self.assertEqual(len(self.held()), 1)

    def test_the_folder_s_adjustment_is_what_the_demand_is_measured_against(self):
        # §5: "O risco de cada ação é ajustável em `settings.json`". The demand of
        # a machine is measured against the FOLDER's number and not the
        # catalogue's, so an action the catalogue prices at `0.2` waits once the
        # map lifts it over the bar — and the bar itself never moved.
        machine = self.machine()
        self.adjust({"task:create": 0.9})
        code, answer, row, _, _ = door.run(
            "task", "create", ["--set", "text=do agente"],
            actor=machine, via=audit.WEBAPP,
        )
        self.assertEqual(code, 0)
        self.assertIsNone(row)
        self.assertEqual(answer, tr("job.waits", id="JOB-1"))
        self.assertEqual(len(self.held()), 1)

    def test_an_action_the_folder_prices_under_the_bar_runs(self):
        # The other direction, and the one §4's "the bar does not lower itself"
        # does NOT govern: that rule is about the THRESHOLD, which is the wall
        # itself, and this is the folder pricing ONE action under its own hand.
        # A delete is `0.5` and the bar sits at `0.5`, so the machine's delete
        # waits; the map walks it under, and it runs.
        machine = self.machine("task:delete")
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "para deletar"})
        self.adjust({"task:delete": 0.1})
        with redirect_stdout(StringIO()):
            code, answer, _, _, _ = door.run(
                "task", "delete", ["1"], actor=machine, via=audit.WEBAPP
            )
        self.assertEqual(code, 0)
        self.assertEqual(self.held(), [])
        self.assertIsNone(store.find("task", 1))

    def test_a_read_never_waits(self):
        # §3: reading is not doing, and there is no line for one either. The
        # demand filter is the WRITES' — a bar at zero would otherwise make
        # every listing a job.
        machine = self.machine("task:list")
        self.bar(0.0)
        code, answer, _, _, _ = door.run("task", "list", [], actor=machine, via=audit.WEBAPP)
        self.assertEqual(code, 0)
        self.assertEqual(self.held(), [])
        self.assertEqual(self.lines(), [])

    def test_the_line_the_demand_owed_is_the_job_and_not_a_log_entry(self):
        # §3 writes a line for every WRITE and every REFUSAL, and a demand that
        # waits is neither: it did not run and it was not refused. What records
        # it is the ROW — the act, the owner and the instant — and the lines
        # arrive when it has an outcome.
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        self.assertEqual(self.lines(), [])

    def test_the_job_carries_the_definition_and_the_state_that_says_it_waits(self):
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        row = self.job_row()
        self.assertTrue(set(row) <= FIELDS, sorted(set(row) - FIELDS))
        self.assertEqual(row[jobs.WHAT], "task:delete")
        self.assertEqual(row[jobs.TABLE], "task")
        self.assertEqual(row[jobs.ARGUMENTS], ["1"])
        self.assertEqual(row[jobs.ACTOR], store.number_of(machine))
        self.assertEqual(row[jobs.STATUS], jobs.WAITING)
        self.assertRegex(row[jobs.WHEN], INSTANT)

    def test_the_arguments_travel_whole_and_come_back_whole(self):
        # The row is what the engine reads to run the act again, so the values
        # are written the way the door parses them back — commas, spaces and an
        # `=` inside a value included.
        machine = self.machine("task:edit,task:list")
        self.bar(0.2)
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "antes"})
        with redirect_stdout(StringIO()):
            code, answer, _, _, _ = door.run(
                "task",
                "edit",
                ["1", "--set", "text=pão, leite = café"],
                actor=machine,
                via=audit.WEBAPP,
            )
        self.assertEqual(answer, tr("job.waits", id="JOB-1"))
        self.assertEqual(
            self.job_row()[jobs.ARGUMENTS],
            ["1", "--set", "text=pão, leite = café"],
        )
        code, answer = self.approve_and_run()
        self.assertEqual(code, 0)
        self.assertEqual(
            (store.find("task", 1) or {}).get("text"), "pão, leite = café"
        )

    def test_the_arguments_a_person_needs_no_line_for_are_not_in_the_log(self):
        # The job carries the arguments because it has to run them again; the
        # AUDIT keeps no value at all (§3), and running a job does not change
        # that — the value is in the row and in nothing else.
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "segredo do dia"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        for row in self.lines():
            self.assertNotIn("segredo", json.dumps(row, ensure_ascii=False))

    # -- the two steps every test above needs ------------------------------

    def approve_and_run(self, number: int = 1) -> tuple[int, str]:
        self.person()
        with redirect_stdout(StringIO()):
            door.job("approve", [str(number)], actor=actors.first_admin(), via=audit.CLI)
        with redirect_stdout(StringIO()):
            return door.job("run", [str(number)], actor=actors.first_admin(), via=audit.CLI)


class TheWords(JobCase):
    """`at-cli job list|view|run|approve|refuse` — the door of the object."""

    def held_one(self) -> int:
        """A waiting job, made the way one is made: a machine's demand at the
        bar. It returns the number the person would type."""
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        return store.number_of(self.job_row())

    def test_the_listing_shows_the_job_and_its_state(self):
        self.held_one()
        code, text = self.words("job", "list")
        self.assertEqual(code, 0)
        self.assertIn("JOB-1", text)
        self.assertIn(tr("table.job.field.status.waiting"), text)

    def test_view_answers_one_job(self):
        self.held_one()
        code, text = self.words("job", "view", "1")
        self.assertEqual(code, 0)
        self.assertIn("JOB-1", text)
        self.assertIn("task:delete", text)
        self.assertIn(tr("table.job.field.status.waiting"), text)

    def test_a_read_leaves_nothing_at_all(self):
        self.held_one()
        before = len(self.lines())
        self.words("job", "list")
        self.words("job", "view", "1")
        self.assertEqual(len(self.lines()), before)

    def test_a_word_the_object_does_not_answer_is_a_usage_error(self):
        code, text = self.words("job", "delete", "1")
        self.assertEqual(code, 2)
        self.assertIn(tr("table.error.unknown_action", action="delete"), text)

    def test_the_wrong_number_of_arguments_is_a_usage_error(self):
        for words in (["job", "run"], ["job", "approve", "1", "2"], ["job", "list", "x"]):
            with self.subTest(words=words):
                code, _ = self.words(*words)
                self.assertEqual(code, 2)

    def test_a_job_nobody_has_is_refused_by_the_engine_s_own_words(self):
        code, text = self.words("job", "approve", "99")
        self.assertEqual(code, 1)
        self.assertIn(
            tr("table.error.unknown_row", id="99", table="Jobs"), text
        )
        self.assertEqual(self.lines()[0][audit.STATUS], audit.REFUSED)
        self.assertEqual(self.lines()[0][audit.REASON], "table.error.unknown_row")

    def test_the_run_refuses_a_job_that_still_waits(self):
        self.held_one()
        code, text = self.words("job", "run", "1")
        self.assertEqual(code, 1)
        self.assertEqual(
            text.strip(),
            tr(
                "job.error.not_approved",
                id="JOB-1",
                status=tr("table.job.field.status.waiting"),
            ),
        )
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.assertEqual(self.lines()[0][audit.REASON], "job.error.not_approved")


class TheApproval(JobCase):
    """A line of its own, with its actor and its via (§5)."""

    def held_one(self) -> None:
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)

    def test_approving_leaves_one_line_with_its_actor_and_its_via(self):
        self.held_one()
        admin = self.person()
        code, text = self.words("job", "approve", "1")
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), tr("job.approved", id="JOB-1"))
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.APPROVED)
        line = self.lines()[0]
        self.assertEqual(line[audit.WHAT], "job:approve")
        self.assertEqual(line[audit.TABLE], jobs.JOB)
        self.assertEqual(line[audit.STATUS], audit.OK)
        self.assertEqual(line[audit.VIA], audit.CLI)
        self.assertEqual(line[audit.ACTOR], store.number_of(admin))

    def test_the_approval_is_a_line_separate_from_the_job_that_waited(self):
        # The row carries the STATE, and the trail carries who decided and by
        # which road: the two are not the same record, and the approval is not
        # written into the job.
        self.held_one()
        self.person()
        with redirect_stdout(StringIO()):
            door.job("approve", ["1"], actor=actors.first_admin(), via=audit.CLI)
        row = self.job_row()
        # The row carries the STATE and the definition, and nothing of the
        # decision: no actor, no via and no reason of the approval live in it.
        self.assertTrue(set(row) <= FIELDS, sorted(set(row) - FIELDS))
        self.assertEqual([line[audit.WHAT] for line in self.lines()], ["job:approve"])

    def test_refusing_leaves_its_own_line_and_keeps_the_row(self):
        self.held_one()
        self.person()
        code, text = self.words("job", "refuse", "1")
        self.assertEqual(code, 0)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)
        self.assertEqual(self.lines()[0][audit.WHAT], "job:refuse")
        # A job is the record of a demand that could not run, and it is not
        # deleted when it is answered: a log with holes is not one.
        self.assertEqual(len(self.held()), 1)

    def test_a_job_that_already_has_an_outcome_is_refused_by_name(self):
        self.held_one()
        self.person()
        self.words("job", "approve", "1")
        code, text = self.words("job", "approve", "1")
        self.assertEqual(code, 1)
        self.assertEqual(
            text.strip(),
            tr(
                "job.error.not_waiting",
                id="JOB-1",
                status=tr("table.job.field.status.approved"),
            ),
        )
        self.assertEqual(self.lines()[-1][audit.REASON], "job.error.not_waiting")

    def test_a_machine_is_refused_the_approval_by_name(self):
        # §4: no machine actor carries `job:approve` or `job:refuse`. The role is
        # one wall; the other is the door's own, and it is the one a role cannot
        # say — the word over a demand is a PRESENCE, and a machine is exactly
        # the absence of one.
        self.held_one()
        machine = self.machine()
        with redirect_stdout(StringIO()):
            code, text = door.job("approve", ["1"], actor=machine, via=audit.CLI)
        self.assertEqual(code, 1)
        self.assertEqual(
            text,
            tr(
                "job.error.machine",
                permission=permissions.label("job:approve"),
            ),
        )
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        # A wall an actor found is a line (§3), and the reason is the KEY.
        line = self.lines()[-1]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], "job.error.machine")
        self.assertEqual(line[audit.ACTOR], store.number_of(machine))

    def test_a_machine_is_refused_the_refusal_too(self):
        self.held_one()
        machine = self.machine()
        with redirect_stdout(StringIO()):
            code, _ = door.job("refuse", ["1"], actor=machine, via=audit.CLI)
        self.assertEqual(code, 1)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)

    def test_the_approval_reads_in_the_language_of_the_reader(self):
        self.held_one()
        self.person()
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            code, text = self.words("job", "approve", "1")
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), "JOB-1 approved.")


class TheSchedule(JobCase):
    """The row a person DECLARES, and the one a person turns OFF (item 24,
    fatia 2/3) — the declaration's own `when`, and the clock that stops
    finding what was turned off."""

    def test_declaring_creates_a_row_born_scheduled(self):
        self.person()
        code, text = self.words(
            "job", "declare", "task", "create", "--set", "text=lembrete",
            "--when", "2026-10-20T09:00",
        )
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), tr("job.declared", id="JOB-1"))
        row = self.job_row()
        self.assertEqual(row[jobs.STATUS], jobs.SCHEDULED)
        self.assertEqual(row[jobs.WHAT], "task:create")
        self.assertEqual(row[jobs.TABLE], "task")
        self.assertEqual(row[jobs.ARGUMENTS], ["--set", "text=lembrete"])
        self.assertTrue(INSTANT.match(row[jobs.WHEN]))

    def test_the_declared_row_shows_up_in_the_listing_as_scheduled(self):
        self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        code, text = self.words("job", "list")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.job.field.status.scheduled"), text)

    def test_declaring_leaves_one_line_and_one_version(self):
        admin = self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        self.assertEqual(len(self.lines()), 1)
        line = self.lines()[0]
        self.assertEqual(line[audit.WHAT], "job:declare")
        self.assertEqual(line[audit.TABLE], jobs.JOB)
        self.assertEqual(line[audit.STATUS], audit.OK)
        self.assertEqual(line[audit.VIA], audit.CLI)
        self.assertEqual(line[audit.ACTOR], store.number_of(admin))

    def test_declaring_with_no_when_is_a_usage_error(self):
        self.person()
        code, _ = self.words("job", "declare", "task", "create")
        self.assertEqual(code, 2)

    def test_declaring_with_a_when_that_is_not_an_instant_is_refused(self):
        self.person()
        code, _ = self.words(
            "job", "declare", "task", "create", "--when", "não é data",
        )
        self.assertEqual(code, 1)
        self.assertEqual(self.held(), [])

    def test_disabling_turns_a_scheduled_job_into_a_refused_one(self):
        self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        code, text = self.words("job", "disable", "1")
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), tr("job.disabled", id="JOB-1"))
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)
        # Not a deletion, for the same reason a refusal never is one.
        self.assertEqual(len(self.held()), 1)

    def test_disabling_stops_the_clock_from_finding_it(self):
        self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        self.assertEqual(len(clock.due(jobs.SCHEDULED)), 1)
        self.words("job", "disable", "1")
        self.assertEqual(clock.due(jobs.SCHEDULED), [])

    def test_disabling_a_job_that_is_not_scheduled_is_refused_by_name(self):
        self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        self.words("job", "disable", "1")
        code, text = self.words("job", "disable", "1")
        self.assertEqual(code, 1)
        self.assertEqual(
            text.strip(),
            tr(
                "job.error.not_scheduled",
                id="JOB-1",
                status=tr("table.job.field.status.refused"),
            ),
        )

    def test_a_machine_is_refused_the_disable_too(self):
        # §4's reason for `approve`/`refuse` is the same for `disable`: the
        # word over a round is a presence, and a machine is the absence of one.
        self.person()
        self.words("job", "declare", "task", "create", "--when", "now")
        machine = self.machine()
        with redirect_stdout(StringIO()):
            code, _ = door.job("disable", ["1"], actor=machine, via=audit.CLI)
        self.assertEqual(code, 1)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.SCHEDULED)


class TheRun(JobCase):
    """`at-cli job run` — the engine performs the act the row holds (§4)."""

    def held_one(self, carried: str = "task:delete") -> dict:
        machine = self.machine(carried)
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        self.person()
        with redirect_stdout(StringIO()):
            door.job("approve", ["1"], actor=actors.first_admin(), via=audit.CLI)
        return machine

    def test_the_run_performs_the_act_and_marks_the_job_done(self):
        self.held_one()
        code, text = self.words("job", "run", "1")
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), tr("table.deleted", id="TASK-1"))
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.DONE)

    def test_the_line_carries_the_via_engine_and_the_actor_that_owns_it(self):
        # "O job corre com a via `engine` e com o ator que o possui, então o teto
        # dele é o daquele ator": the trail says the ENGINE ran it, and WHO it
        # was running it for is the owner — never whoever typed `job run`.
        machine = self.held_one()
        admin = actors.first_admin()
        self.words("job", "run", "1")
        line = self.lines()[-1]
        self.assertEqual(line[audit.WHAT], "task:delete")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.ACTOR], store.number_of(machine))
        self.assertNotEqual(line[audit.ACTOR], store.number_of(admin))
        self.assertEqual(line[audit.STATUS], audit.OK)

    def test_the_run_leaves_one_line_and_one_version(self):
        from at.core import versioning

        self.held_one()
        self.words("job", "approve", "1")
        before = len(self.lines())
        with mock.patch.object(versioning, "commit") as committed:
            self.words("job", "run", "1")
        committed.assert_called_once()
        self.assertEqual(len(self.lines()), before + 1)

    def test_the_ceiling_of_the_run_is_the_owner_s(self):
        # The owner's role is read AGAIN when the job runs and not trusted from
        # the approval: a role edited under a waiting job is read on the next
        # read like any other row. A job whose owner lost the permission is
        # refused by name, and the refusal is a line.
        machine = self.held_one()
        role = actors.role_of(machine) or {}
        tables.edit("role", store.number_of(role), {"permissions": "task:list"})
        code, text = self.words("job", "run", "1")
        self.assertEqual(code, 1)
        self.assertIn(permissions.label("task:delete"), text)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.APPROVED)
        line = self.lines()[-1]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], "job.error.ceiling")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.ACTOR], store.number_of(machine))

    def test_a_job_whose_owner_is_gone_answers_a_ceiling_of_nothing(self):
        # Fail closed, like `permissions.carries` everywhere else: a job nobody
        # owns reaches nothing, and the run says so instead of running it.
        machine = self.held_one()
        tables.delete("actor", store.number_of(machine))
        code, text = self.words("job", "run", "1")
        self.assertEqual(code, 1)
        self.assertIn(permissions.label("task:delete"), text)

    def test_an_act_the_engine_refuses_leaves_the_job_released(self):
        # The job ran and the ACT did not go through: the refusal is its own
        # line, and the job stays released so the same act can be asked for
        # again once whatever refused it has been dealt with.
        self.held_one()
        with redirect_stdout(StringIO()):
            tables.delete("task", 1)
        code, _ = self.words("job", "run", "1")
        self.assertEqual(code, 1)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.APPROVED)
        self.assertEqual(self.lines()[-1][audit.STATUS], audit.REFUSED)
        self.assertEqual(self.lines()[-1][audit.REASON], "table.error.unknown_row")

    def test_running_a_job_does_not_make_another_job(self):
        # The filter's own acts are the filter's: a demand that already waited
        # and was released walks the engine's door with `released=True`, and
        # holding it again would ask for the same approval forever.
        self.bar(0.0)
        self.held_one()
        code, _ = self.words("job", "run", "1")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.held()), 1)


class TheMigration(JobCase):
    """A folder that already exists gains the table, and its ceiling."""

    def declaration(self) -> Path:
        return paths.data_dir() / schema.SCHEMA_DIR / "job.json"

    def strip(self) -> None:
        """Leave the folder as one born BEFORE this release is: no declaration,
        no stamp of fourteen, and an administrator whose role was built from the
        catalogue of that day."""
        role = actors.role_for_admin()
        tables.edit(
            "role",
            store.number_of(role),
            {
                "permissions": ",".join(
                    name
                    for name in permissions.all_permissions()
                    if name not in migrations.JOB_PERMISSIONS
                )
            },
        )
        self.declaration().unlink()
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 14)
            ),
            encoding="utf-8",
        )
        schema.reset()

    def test_a_folder_without_the_table_gains_it(self):
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertTrue(self.declaration().is_file())
        self.assertIsNotNone(schema.of("job"))
        role = actors.admin_role() or {}
        for name in migrations.JOB_PERMISSIONS:
            with self.subTest(permission=name):
                self.assertIn(name, permissions.carried(role))

    def test_the_folder_that_never_had_the_permissions_hears_them_granted(self):
        self.strip()
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        self.assertIn(
            tr(
                "boot.migration.catalogue.granted",
                role=actors.ADMIN_ROLE,
                names=", ".join(migrations.JOB_PERMISSIONS),
            ),
            output.getvalue(),
        )

    def test_the_store_file_is_not_born_by_the_migration(self):
        # An empty file that names nothing is a store a person would read as a
        # table that exists elsewhere — the box is born with the first demand.
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse((paths.data_dir() / "jobs.jsonl").exists())

    def test_a_declaration_a_person_deleted_is_not_brought_back(self):
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertIn(14, migrations.applied())
        self.declaration().unlink()
        schema.reset()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse(self.declaration().is_file())

    def test_a_folder_born_by_this_release_has_already_run_it(self):
        self.assertIn(14, migrations.applied())


class TheNetwork(JobCase):
    """The whole of the slice, with the socket taken away."""

    def test_the_demand_the_job_and_the_approval_need_no_network(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("the job needs no network")
        ):
            machine = self.machine()
            with redirect_stdout(StringIO()):
                tables.create("task", {"text": "do agente"})
            with redirect_stdout(StringIO()):
                door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
            self.person()
            with redirect_stdout(StringIO()):
                door.job("approve", ["1"], actor=actors.first_admin(), via=audit.CLI)
            with redirect_stdout(StringIO()):
                code, answer = door.job(
                    "run", ["1"], actor=actors.first_admin(), via=audit.CLI
                )
        self.assertEqual(code, 0)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.DONE)


if __name__ == "__main__":
    unittest.main()
