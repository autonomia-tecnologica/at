"""O relógio — item 24's MOTOR slice (§4).

The `jobs` table of item 15 gives a job a definition and a life, and the job
runs when somebody asks. A job that only runs when asked is not the "scheduled
job" §4 already speaks of, and the approval that arrives on a phone only makes
sense if the thing that asked did so on its own. What this module measures, in
the order the item decided it:

- **the `when` is READ and REWRITTEN.** A job DECLARED with an instant carries
  the next one it must round in `when`, and `scheduled` is the state that says
  so — the demand that waited carries the instant it ARRIVED and waits for a
  person, and the clock reads the second and never the first. After every round
  the instant moves on by the cadence, which is what makes a job's life a series
  of rounds and what keeps a failed one from being retried in a loop.
- **the cadence is the clock's, and its granularity is the minute.** It is one
  number for the folder: the declaration says WHEN a job starts, and the rhythm
  after that belongs to the clock.
- **a round that ends waiting for approval waits as a job**, item 15's model
  exactly — the same row, the same state, and no second model: no queue, no
  lock, nothing new to learn.
- **a round AT was not up for is recovered once**, and the line says so: the
  next instant is measured from the round that happened and not from the
  appointment that was missed.
- **the clock is INJECTED**: the suite hands in the instant, and no test needs
  the machine's hour or a network.
- **and the WebApp is the process that keeps it**, which is where the clock
  lives until the engine leaves.

Every test aims AT at a throwaway folder with `AT_ROOT`, so the checkout's own
Working Folder is never touched.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
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
    risk,
    settings,
    strongbox,
    tables,
)
from at.data import schema, store
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import main
from at.ui.webapp import app as webapp
from at.ui.webapp import clock as webapp_clock
from at.ui.webapp import keys as webapp_keys
from at.ui.webapp import launch as webapp_launch

# The instant the suite's clock reads. It is handed in and never taken from the
# machine: a test that reads the clock twice is a test that disagrees with itself.
AT = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)

# The two other instants every test is placed between: one inside the cadence
# that just passed — a round that is merely DUE — and one well past it, which is
# a round AT was not up for.
DUE = AT - timedelta(minutes=1)
MISSED = AT - clock.CADENCE * 3
FUTURE = AT + timedelta(minutes=1)

CREDENTIAL = "uma-frase-bem-longa"

# The act the clock performs when it recovers a round. It is the module's own
# word, and it travels in the line's `what` like every other act.
RECOVERED = "job:recovered"


class ClockCase(unittest.TestCase):
    """A Working Folder of its own, born by this release."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.scratch.name), "AT_LANG": "pt_BR"}
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
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def lines(self) -> list[dict]:
        return store.load(audit.AUDIT)

    def held(self) -> list[dict]:
        return store.load(jobs.JOB)

    def job_row(self, number: int = 1) -> dict:
        return store.find(jobs.JOB, number) or {}

    def acts(self) -> list[str]:
        return [line[audit.WHAT] for line in self.lines()]

    # -- the actors, so the presence rule has somebody to be about ----------

    def asker(self) -> dict:
        """The first administrator, made once per test — a person, and the owner
        every declared job is given unless a test says otherwise."""
        if not hasattr(self, "_asker"):
            with redirect_stdout(StringIO()):
                self._asker = actors.create_admin("Rafael", CREDENTIAL)
        return self._asker

    def machine(self, carried: str = "task:create,task:edit,task:delete") -> dict:
        role = tables.create("role", {"name": "runner", "permissions": carried})
        _, token = actors.mint_agent("runner", str(store.number_of(role)))
        return actors.authenticate_agent(token) or {}

    def bar(self, value: object) -> None:
        settings.save({**settings.load(), risk.KEY: value})

    # -- the declaration, built where the row is built ----------------------
    #
    # The door that DECLARES a scheduled job is the `cli`'s and the page's (the
    # other two slices of the cut), so the row is built here: what this slice
    # owns is the RULE and the STATE, and a test places a job where a person
    # will one day place it.

    def declare(
        self,
        action: str,
        args: list[str],
        *,
        owner: dict,
        when: datetime,
        table: str = "task",
    ) -> dict:
        with redirect_stdout(StringIO()):
            return tables.create(
                jobs.JOB,
                {
                    jobs.WHAT: jobs.what(table, action),
                    jobs.TABLE: table,
                    jobs.ARGUMENTS: args,
                    jobs.ACTOR: store.number_of(owner),
                    jobs.WHEN: tables.utc(when),
                    jobs.STATUS: jobs.SCHEDULED,
                },
            )

    def declare_create(self, when: datetime, *, owner: dict | None = None) -> dict:
        """A declared job that creates a task — a write UNDER the bar, so its
        round runs without asking anybody."""
        return self.declare(
            "create",
            ["--set", "text=do relógio"],
            owner=owner or self.asker(),
            when=when,
        )

    def declare_delete(self, when: datetime, *, owner: dict | None = None) -> dict:
        """A declared job that deletes — a write AT the bar, so its round WAITS."""
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "para deletar"})
        return self.declare("delete", ["1"], owner=owner or self.asker(), when=when)

    def tick(self, at: datetime = AT) -> list[dict]:
        with redirect_stdout(StringIO()):
            return door.tick(at)

    def release(self, number: int = 1) -> None:
        """A person's word over a waiting demand — the release the clock then
        fires. It is `door.job`, the door the `cli` reads."""
        with redirect_stdout(StringIO()):
            door.job(
                "approve", [str(number)], actor=actors.first_admin(), via=audit.CLI
            )

    def arrival(self, when: datetime, number: int = 1) -> None:
        """Place a job's instant where the test's clock can see it.

        A demand that waited carries the instant it ARRIVED, and that instant is
        the MACHINE's — so a test that needs the clock to reach it says where it
        is, instead of reading the machine's hour beside it.
        """
        with redirect_stdout(StringIO()):
            tables.edit(jobs.JOB, number, {jobs.WHEN: tables.utc(when)})


class TheDeclaration(ClockCase):
    """The fifth state, the cadence, and the words that carry them."""

    def test_the_state_the_clock_drives_is_declared(self):
        self.assertIn(jobs.SCHEDULED, tables.enum_values("job", jobs.STATUS))
        self.assertEqual(jobs.SCHEDULED, "scheduled")

    def test_every_state_reads_in_both_languages(self):
        self.assertEqual(
            tables.enum_label("job", jobs.STATUS, jobs.SCHEDULED), "Agendado"
        )
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(
                tables.enum_label("job", jobs.STATUS, jobs.SCHEDULED), "Scheduled"
            )

    def test_the_cadence_is_the_clock_s_and_it_is_read_in_minutes(self):
        # The granularity the slice decides: minutes, and one number for the
        # whole folder — the declaration says WHEN a job starts, and the rhythm
        # after that is the clock's. Um minuto (a pedido da pessoa, 2026-10-05):
        # o lembrete marca a HORA, e o passo que a cobre tem de caber no minuto.
        self.assertEqual(clock.CADENCE, timedelta(minutes=1))
        self.assertEqual(clock.next_instant(AT), tables.utc(AT + timedelta(minutes=1)))

    def test_the_words_a_recovered_round_is_named_by_read_in_both_languages(self):
        self.assertIn("Rodada recuperada", tr("job.recovered"))
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertIn("Recovered round", tr("job.recovered"))

    def test_the_cli_lists_the_new_state_and_needs_no_line_of_its_own(self):
        # The `job list|view|run|approve|refuse` the `cli` already has reads the
        # state off the declaration, so the door that DECLARES one is the other
        # slice's and nothing here has to change for it to read.
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do relógio"})
        self.declare_create(DUE)
        code, text = self.words("job", "list")
        self.assertEqual(code, 0)
        self.assertIn("JOB-1", text)
        self.assertIn(tables.enum_label("job", jobs.STATUS, jobs.SCHEDULED), text)

    def test_the_instant_is_read_and_never_trusted(self):
        # A row a hand edited to something that is not an instant is not DUE —
        # the rule failing closed, like every strange declaration in AT.
        self.assertIsNone(jobs.instant({jobs.WHEN: "ontem"}))
        self.assertIsNone(jobs.instant({jobs.WHEN: "2026-09-27"}))
        self.assertIsNone(jobs.instant({}))
        self.assertIsNotNone(jobs.instant({jobs.WHEN: tables.utc(AT)}))


class ThePass(ClockCase):
    """Who comes round, and in which order."""

    def test_only_a_declared_job_comes_round(self):
        declared = self.declare_create(DUE)
        self.assertEqual(
            [store.number_of(row) for row in clock.due(jobs.SCHEDULED, AT)],
            [store.number_of(declared)],
        )

    def test_a_job_whose_instant_has_not_arrived_does_not(self):
        self.declare_create(FUTURE)
        self.assertEqual(clock.due(jobs.SCHEDULED, AT), [])

    def test_a_demand_that_waited_is_not_the_clock_s_to_round(self):
        # A `waiting` job waits for a PERSON: rounding it would run an act nobody
        # released. It is the clock's own state that decides, and nothing else.
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.arrival(DUE)
        self.assertEqual(clock.due(jobs.SCHEDULED, AT), [])

    def test_the_order_is_the_instant_s_and_not_the_file_s(self):
        # Two jobs that came round together are rounded in the order they were
        # due, so the log reads the way the schedule did.
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "antes"})
        self.declare(
            "create",
            ["--set", "text=depois"],
            owner=self.asker(),
            when=AT - timedelta(minutes=1),
        )
        self.declare(
            "edit",
            ["1", "--set", "text=primeiro"],
            owner=self.asker(),
            when=AT - timedelta(minutes=5),
        )
        self.tick()
        self.assertEqual(
            [what for what in self.acts() if what in ("task:create", "task:edit")],
            ["task:edit", "task:create"],
        )

    def test_a_round_missed_by_more_than_one_cadence_is_recovered(self):
        punctual = self.declare_create(DUE)
        late = self.declare_create(MISSED)
        self.assertFalse(clock.missed(punctual, AT))
        self.assertTrue(clock.missed(late, AT))


class TheRound(ClockCase):
    """The act that fires on its own, and what it leaves behind."""

    def test_a_declared_job_rounds_alone_and_leaves_its_line(self):
        owner = self.asker()
        self.declare_create(DUE, owner=owner)
        self.tick()
        # The act ran with nobody asking: the task is there.
        self.assertEqual((store.find("task", 1) or {}).get("text"), "do relógio")
        line = self.lines()[0]
        self.assertEqual(line[audit.WHAT], "task:create")
        self.assertEqual(line[audit.TABLE], "task")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.STATUS], audit.OK)
        self.assertEqual(line[audit.ACTOR], store.number_of(owner))
        # And the job lives on: it is still the clock's, and its instant moved.
        row = self.job_row()
        self.assertEqual(row[jobs.STATUS], jobs.SCHEDULED)
        self.assertEqual(row[jobs.WHEN], clock.next_instant(AT))

    def test_a_punctual_round_leaves_only_the_act_s_line(self):
        self.declare_create(DUE)
        self.tick()
        self.assertEqual(self.acts(), ["task:create"])

    def test_the_clock_rounds_again_when_the_next_instant_arrives(self):
        self.declare_create(DUE)
        self.tick()
        later = AT + clock.CADENCE
        with redirect_stdout(StringIO()):
            door.tick(later)
        self.assertEqual(self.acts(), ["task:create", "task:create"])
        self.assertEqual(self.job_row()[jobs.WHEN], clock.next_instant(later))

    def test_a_job_that_has_not_come_round_yet_is_not_rounded(self):
        self.declare_create(FUTURE)
        self.assertEqual(self.tick(), [])
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.lines(), [])

    # -- the round that ends waiting for approval ---------------------------

    def test_a_round_at_the_bar_waits_as_a_job(self):
        # §4: what runs on its own waits at the threshold. The round is not a
        # queue and not a lock — it is THIS row, in the state that says it waits,
        # and no second row is born: item 15's model, and the whole of "no
        # second model".
        self.declare_delete(DUE)
        self.tick()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.assertEqual(len(self.held()), 1)
        # The act did not run, and a demand that waits leaves NO line (§3).
        self.assertIsNotNone(store.find("task", 1))
        self.assertEqual(self.lines(), [])

    def test_the_via_engine_waits_with_a_person_s_own_actor(self):
        # The mark of an act that runs on its own is the VIA and not the actor: a
        # person's own nightly job waits, because nobody is there to answer it.
        self.declare_delete(DUE, owner=self.asker())
        self.tick()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)

    def test_the_bar_is_the_folder_s_and_it_can_hold_a_round(self):
        # §5: the folder adjusts the catalogue's numbers, and the demand is
        # measured against them. A create is `0.2` and the bar sits at `0.5`, so
        # the round runs; the folder lifts the bar onto it and the same job
        # waits — the clock reads the FOLDER's number and not the catalogue's.
        self.bar(0.2)
        self.declare_create(DUE)
        self.tick()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.lines(), [])

    def test_the_waiting_round_is_released_by_a_person_and_the_clock_fires_it(self):
        self.declare_delete(DUE)
        self.tick()
        self.asker()
        self.release()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.APPROVED)
        # And now the clock performs it — the road `job run` walks, with nobody
        # typing it.
        self.tick()
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.DONE)
        line = self.lines()[-1]
        self.assertEqual(line[audit.WHAT], "task:delete")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.STATUS], audit.OK)

    def test_the_round_of_a_job_whose_owner_is_gone_reaches_nothing(self):
        machine = self.machine()
        self.declare_create(DUE, owner=machine)
        with redirect_stdout(StringIO()):
            tables.delete("actor", store.number_of(machine))
        self.tick()
        self.assertIsNone(store.find("task", 1))
        line = self.lines()[-1]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], "job.error.ceiling")
        # The round ENDS: a ceiling its owner cannot clear is not one the clock
        # waits out, and `refused` is the state `disable` already leaves.
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)

    def test_a_round_whose_owner_lost_the_permission_is_refused_by_name(self):
        machine = self.machine("task:create")
        self.declare_create(DUE, owner=machine)
        role = actors.role_of(machine) or {}
        with redirect_stdout(StringIO()):
            tables.edit("role", store.number_of(role), {"permissions": "task:list"})
        self.tick()
        self.assertIsNone(store.find("task", 1))
        line = self.lines()[-1]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], "job.error.ceiling")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.ACTOR], store.number_of(machine))
        # The round ENDS: the job leaves `scheduled`, so reviving it is a
        # person's declaration and never the clock's.
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)

    def test_a_round_refused_by_the_ceiling_does_not_come_back(self):
        # The defect the transition closes: a refused round that rescheduled
        # itself wrote the same line every cadence, for ever. Now the job is no
        # longer `scheduled`, so the next pass does not find it — no new line,
        # and the instant it was about stays where it was.
        machine = self.machine("task:create")
        self.declare_create(DUE, owner=machine)
        role = actors.role_of(machine) or {}
        with redirect_stdout(StringIO()):
            tables.edit("role", store.number_of(role), {"permissions": "task:list"})
        self.tick()
        lines = len(self.lines())
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)
        self.tick(AT + clock.CADENCE)
        self.assertEqual(len(self.lines()), lines)
        self.assertEqual(self.job_row()[jobs.WHEN], tables.utc(DUE))

    def test_a_folder_under_the_read_only_switch_applies_nothing(self):
        # §3: a verification pass must not move a folder. A round is a write like
        # any other, so the clock passes over the folder and leaves it as it found
        # it — no act, no line, no instant moved.
        self.declare_create(DUE)
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            self.assertEqual(self.tick(), [])
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.job_row()[jobs.WHEN], tables.utc(DUE))

    def test_the_clock_does_not_overwrite_a_word_that_arrived_after_it_looked(self):
        # A pass reads a snapshot, and the store is the truth: a person may have
        # answered the job while the round was being prepared, and the clock
        # leaves a row it no longer drives exactly where it is.
        row = self.declare_create(DUE)
        with redirect_stdout(StringIO()):
            tables.edit(jobs.JOB, store.number_of(row), {jobs.STATUS: jobs.REFUSED})
        jobs.reschedule(row, clock.next_instant(AT))
        jobs.waits(row)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.REFUSED)
        self.assertEqual(self.job_row()[jobs.WHEN], tables.utc(DUE))

    def test_an_act_the_engine_refuses_leaves_the_job_scheduled(self):
        # The row the act names is gone, and the refusal is its own line — the
        # rule `job run` follows, so the round is tried again on the next pass.
        self.declare("edit", ["99", "--set", "text=x"], owner=self.asker(), when=DUE)
        self.tick()
        line = self.lines()[-1]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], "table.error.unknown_row")
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.SCHEDULED)


class TheCatchUp(ClockCase):
    """The round AT was not up for — recovered, once."""

    def test_the_missed_round_runs_on_the_next_pass_and_the_line_says_so(self):
        owner = self.asker()
        self.declare_create(MISSED, owner=owner)
        self.tick()
        self.assertEqual((store.find("task", 1) or {}).get("text"), "do relógio")
        recovery = self.lines()[0]
        self.assertEqual(recovery[audit.WHAT], RECOVERED)
        self.assertEqual(recovery[audit.TABLE], jobs.JOB)
        self.assertEqual(recovery[audit.STATUS], audit.OK)
        self.assertEqual(recovery[audit.VIA], audit.ENGINE)
        self.assertEqual(recovery[audit.ACTOR], store.number_of(owner))
        self.assertEqual(self.acts(), [RECOVERED, "task:create"])

    def test_the_missed_round_runs_once_and_not_once_per_cadence(self):
        # An AT that was off for a week comes back to ONE round: the instant it
        # leaves behind is the next one after now, and not a week of them.
        self.declare_create(MISSED)
        self.tick()
        self.assertEqual(self.acts(), [RECOVERED, "task:create"])
        self.assertEqual(len(store.load("task")), 1)
        self.assertEqual(self.job_row()[jobs.WHEN], clock.next_instant(AT))

    def test_a_punctual_round_is_not_recovered(self):
        self.declare_create(DUE)
        self.tick()
        self.assertNotIn(RECOVERED, self.acts())

    def test_the_round_that_waits_after_being_missed_still_says_it_was_recovered(self):
        self.declare_delete(MISSED)
        self.tick()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.assertEqual(self.acts(), [RECOVERED])


class TheReleased(ClockCase):
    """What a person released — `job run`, with nobody typing it."""

    def held_one(self) -> dict:
        machine = self.machine()
        with redirect_stdout(StringIO()):
            tables.create("task", {"text": "do agente"})
        with redirect_stdout(StringIO()):
            door.run("task", "delete", ["1"], actor=machine, via=audit.WEBAPP)
        return machine

    def test_the_clock_fires_what_a_person_released(self):
        machine = self.held_one()
        self.asker()
        self.release()
        self.arrival(DUE)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.APPROVED)
        self.tick()
        self.assertIsNone(store.find("task", 1))
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.DONE)
        line = self.lines()[-1]
        self.assertEqual(line[audit.WHAT], "task:delete")
        self.assertEqual(line[audit.VIA], audit.ENGINE)
        self.assertEqual(line[audit.ACTOR], store.number_of(machine))

    def test_the_clock_leaves_what_still_waits_alone(self):
        # A demand that waited is not fired: it waits AS A JOB, item 15's model,
        # until a person releases it. The clock invents no second way to wait.
        self.held_one()
        self.arrival(DUE)
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.tick()
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.WAITING)
        self.assertEqual(len(self.held()), 1)
        self.assertEqual(self.lines(), [])


class TheProcess(ClockCase):
    """The WebApp is where the clock lives, and it is injected there too."""

    def test_one_pass_ticks_and_waits_the_cadence(self):
        paused: list[float] = []
        with mock.patch.object(door, "tick") as ticked, \
             mock.patch.object(door, "remind") as reminded:
            webapp.beat(times=2, pause=paused.append)
        self.assertEqual(ticked.call_count, 2)
        self.assertEqual(reminded.call_count, 2)
        # A pausa é ALINHADA à borda da cadência: positiva e nunca maior que um
        # passo inteiro — um passo que derrapa perderia o minuto marcado.
        self.assertEqual(len(paused), 1)
        self.assertGreater(paused[0], 0)
        self.assertLessEqual(paused[0], clock.CADENCE.total_seconds())

    def test_the_reminders_round_shares_the_pass_and_the_notifiers_key(self):
        held = webapp_keys._keys.get(webapp_keys.NOTIFIER_KEY_ENV)
        webapp_keys._keys[webapp_keys.NOTIFIER_KEY_ENV] = b"n" * 32
        self.addCleanup(webapp_keys._keys.pop, webapp_keys.NOTIFIER_KEY_ENV, None)
        if held is not None:
            self.addCleanup(webapp_keys._keys.__setitem__,
                            webapp_keys.NOTIFIER_KEY_ENV, held)
        with mock.patch.object(door, "tick"), \
             mock.patch.object(door, "remind") as reminded:
            webapp.beat(times=1, pause=lambda seconds: None)
        reminded.assert_called_once_with(key=b"n" * 32)

    def test_a_reminder_pass_that_raises_does_not_take_the_clock_down_either(self):
        output = StringIO()
        with mock.patch.object(door, "tick"), \
             mock.patch.object(door, "remind", side_effect=RuntimeError("quebrou")):
            with redirect_stdout(output):
                webapp.beat(times=1)
        self.assertIn("quebrou", output.getvalue())

    def test_the_strongbox_round_shares_the_pass_and_its_own_key(self):
        held = webapp_keys._keys.get(webapp_keys.STRONGBOX_KEY_ENV)
        webapp_keys._keys[webapp_keys.STRONGBOX_KEY_ENV] = b"c" * 32
        self.addCleanup(webapp_keys._keys.pop, webapp_keys.STRONGBOX_KEY_ENV, None)
        if held is not None:
            self.addCleanup(webapp_keys._keys.__setitem__,
                            webapp_keys.STRONGBOX_KEY_ENV, held)
        with mock.patch.object(door, "tick"), mock.patch.object(door, "remind"), \
                mock.patch.object(strongbox.Watcher, "tick") as ticked:
            webapp.beat(times=1, pause=lambda seconds: None)
        ticked.assert_called_once_with(b"c" * 32)

    def test_a_cofre_pass_that_raises_does_not_take_the_clock_down_either(self):
        output = StringIO()
        with mock.patch.object(door, "tick"), mock.patch.object(door, "remind"), \
                mock.patch.object(strongbox.Watcher, "tick",
                                   side_effect=RuntimeError("quebrou")):
            with redirect_stdout(output):
                webapp.beat(times=1)
        self.assertIn("quebrou", output.getvalue())

    def test_with_no_server_the_page_vigia_round_does_not_run(self):
        # TASK-128, fatia 2/3: sem `server` não há `Broadcaster` para publicar,
        # e a rodada simplesmente não nasce — o mesmo `beat()` de sempre, das
        # chamadas acima, que nunca passam um servidor. O `Watcher` do Cofre
        # cria o SEU PRÓPRIO `vigia.Vigia` (por `strongbox.Cofre/`)
        # incondicionalmente — o que esta rodada NÃO cria é um segundo, para
        # `Biblioteca/`.
        with mock.patch.object(door, "tick"), mock.patch.object(door, "remind"), \
                mock.patch.object(strongbox.Watcher, "tick"), \
                mock.patch.object(webapp.vigia, "Vigia") as made:
            webapp.beat(times=1, pause=lambda seconds: None)
        self.assertNotIn(mock.call(paths.prose_dir()), made.call_args_list)

    def test_the_page_vigia_round_publishes_when_arquivos_changes(self):
        # A pasta vigiada é `Biblioteca/` (`paths.prose_dir()`) — a mesma que
        # `FileTree.vue` relê hoje ao cutucar. A PRIMEIRA varredura é muda
        # (`vigia.Vigia`'s own docstring), então a escrita entra ENTRE a
        # primeira e a segunda rodada — é para isso que `pause` existe aqui.
        server = mock.Mock()
        target = paths.prose_dir() / "nota.txt"

        def write_between_rounds(seconds: float) -> None:
            target.write_text("a", encoding="utf-8")

        with mock.patch.object(door, "tick"), mock.patch.object(door, "remind"), \
                mock.patch.object(strongbox.Watcher, "tick"):
            webapp.beat(server, times=2, pause=write_between_rounds)
        server.events.publish.assert_called_once()

    def test_a_page_vigia_pass_that_raises_does_not_take_the_clock_down(self):
        output = StringIO()
        server = mock.Mock()
        server.events.publish.side_effect = RuntimeError("quebrou")
        target = paths.prose_dir() / "nota.txt"

        def write_between_rounds(seconds: float) -> None:
            target.write_text("a", encoding="utf-8")

        with mock.patch.object(door, "tick"), mock.patch.object(door, "remind"), \
                mock.patch.object(strongbox.Watcher, "tick"):
            with redirect_stdout(output):
                webapp.beat(server, times=2, pause=write_between_rounds)
        self.assertIn("quebrou", output.getvalue())

    def test_a_pass_that_raises_does_not_take_the_clock_down(self):
        output = StringIO()
        with mock.patch.object(door, "tick", side_effect=RuntimeError("quebrou")), \
             mock.patch.object(door, "remind"):
            with redirect_stdout(output):
                webapp.beat(times=1)
        self.assertIn("quebrou", output.getvalue())

    def test_the_webapp_process_starts_the_clock(self):
        # The clock is kept by the process that is already up (§4, item 24), and
        # it is born in `run`. The raw server the route tests build does NOT
        # start it — nothing of theirs may move with an hour the machine chose.
        self.asker()
        reached = threading.Event()
        server = mock.Mock()
        server.server_address = ("127.0.0.1", 0)
        with mock.patch.object(webapp_launch, "make_server", return_value=server):
            with mock.patch.object(
                webapp_clock, "beat", side_effect=lambda *_a, **_kw: reached.set()
            ):
                with redirect_stdout(StringIO()):
                    webapp.run(0, include_caddy=False)
        self.assertTrue(reached.wait(timeout=5))
        server.server_close.assert_called_once()

    def test_the_raw_server_does_not_start_it(self):
        # The route tests build a bare server, and nothing of theirs may read an
        # hour the machine chose: the clock is `run`'s, and only `run`'s.
        with mock.patch.object(webapp_clock, "beat") as beaten:
            server = webapp.make_server(0)
        try:
            beaten.assert_not_called()
        finally:
            server.server_close()


class TheNetwork(ClockCase):
    """The whole of the slice, with the socket taken away."""

    def test_the_declared_job_and_the_recovery_need_no_network(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("o relógio não usa rede")
        ):
            self.declare_create(MISSED)
            self.declare_delete(DUE)
            self.tick()
            self.asker()
            self.release(2)
            self.arrival(AT, 2)
            self.tick()
        self.assertEqual(self.job_row(1)[jobs.WHEN], clock.next_instant(AT))
        self.assertEqual(self.job_row(2)[jobs.STATUS], jobs.DONE)


class TheMigration(ClockCase):
    """A folder that already exists gains the state, and its words."""

    def declaration(self) -> Path:
        return paths.data_dir() / schema.SCHEMA_DIR / "job.json"

    def strip(self) -> None:
        """Leave the folder as one born BEFORE this release is: a declaration
        without the fifth state, and a stamp that never ran eighteen."""
        where = self.declaration()
        declared = json.loads(where.read_text(encoding="utf-8"))
        del declared["fields"]["status"]["enum"]["scheduled"]
        where.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(
                    item.ident for item in migrations.MIGRATIONS if item.ident != 18
                )
            ),
            encoding="utf-8",
        )
        schema.reset()

    def test_a_folder_without_the_state_gains_it(self):
        self.strip()
        self.assertNotIn("scheduled", tables.enum_values("job", jobs.STATUS))
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertIn("scheduled", tables.enum_values("job", jobs.STATUS))
        self.assertEqual(
            tables.enum_label("job", jobs.STATUS, jobs.SCHEDULED), "Agendado"
        )

    def test_a_value_a_person_edited_is_not_overwritten(self):
        # The merge only ever ADDS (§3, migration): a state a person wrote stays
        # where it is, and the report names what was skipped.
        self.strip()
        where = self.declaration()
        declared = json.loads(where.read_text(encoding="utf-8"))
        declared["fields"]["status"]["enum"]["scheduled"] = "table.job.field.status.done"
        where.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        self.assertIn("job.fields.status.enum.scheduled", output.getvalue())

    def test_the_entry_point_is_at_the_end_of_the_enum(self):
        # The merge only ever ADDS, so the bundled declaration places the new
        # state where the migration can put it: at the end. An insertion in the
        # middle would be an edit to the person's file, and the two folders —
        # the one that migrated and the one born now — would disagree.
        self.assertEqual(
            list((schema.field("job", jobs.STATUS).get("enum") or {})),
            ["waiting", "approved", "refused", "done", "scheduled"],
        )

    def test_a_folder_born_by_this_release_has_already_run_it(self):
        self.assertIn(18, migrations.applied())


if __name__ == "__main__":
    unittest.main()
