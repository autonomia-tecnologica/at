"""The lembrete's recurrence — item 29's first slice (§4).

Item 29 promises "the configured reminders can be notified", and the half that
does the notifying (a phone, a push) is another slice's work, gated behind the
Main Key bridge (TASK-133) and the round that fires on its own (TASK-145).
What THIS module measures is the decision beneath it — pure, and checkable
without either:

- **`occurs` reads the ANCHOR the `freq` names, and only that one.** A row may
  carry `on_weekday`, `on_day`, `on_month` and `on_date` all at once, and `freq`
  alone decides which of them the recurrence consults — `weekly` reads
  `on_weekday`, `monthly` reads `on_day`, `yearly` reads `on_month` AND `on_day`
  together, `once` reads `on_date`, `daily` reads none of them. There is no
  priority to break, because each `freq` owns its own fields and nothing else.
- **`since` is the floor, and `paused` never occurs**, for every freq alike —
  the rule failing closed.
- **`due` splits a day's active reminders in two: the ones landing ON it, and
  the ones inside their OWN `warn_days`, ahead of it** — a hit on the first is
  never also counted on the second, for the same occurrence.
- **the date is INJECTED**, the way `clock.now` injects the instant: `today` is
  this module's one calendar read, and the seam a test freezes.
- **`at-cli reminder due --at <day>` is the one door this fatia opens**, and it
  is a READ: no line, no version, no ceiling moved — the same shape `secret
  scan` already carries, and the catalogue names it the same way.

Every test that touches the folder aims AT at a throwaway one with `AT_ROOT`, so
the checkout's own Working Folder is never touched; none of them needs a
network or a model.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, files, notifier, permissions, reminder, tables
from at.data import schema, store
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import main, tree

# The sentences this door owns, checked to exist in both languages.
SAID = ("reminder.due.today", "reminder.due.warn", "reminder.due.error.arguments")


def row(**values) -> dict:
    """A reminder row, `active` and dated well out of the way of `date.today`,
    unless a test says otherwise."""
    base = {"status": reminder.ACTIVE, "since": "2020-01-01"}
    base.update(values)
    return base


class Occurs(unittest.TestCase):
    """The recurrence, one `freq` at a time — no folder, no store."""

    def test_daily_lands_every_day_on_or_after_since(self):
        r = row(freq="daily")
        self.assertTrue(reminder.occurs(r, date(2026, 1, 1)))
        self.assertTrue(reminder.occurs(r, date(2026, 12, 31)))

    def test_daily_does_not_land_before_since(self):
        r = row(freq="daily", since="2026-06-01")
        self.assertFalse(reminder.occurs(r, date(2026, 5, 31)))
        self.assertTrue(reminder.occurs(r, date(2026, 6, 1)))

    def test_weekly_lands_on_the_named_weekdays(self):
        # Monday=0 .. Sunday=6, the convention `nlu.grammar` already uses.
        r = row(freq="weekly", on_weekday=[0, 2, 4])
        self.assertTrue(reminder.occurs(r, date(2026, 9, 28)))  # Monday
        self.assertFalse(reminder.occurs(r, date(2026, 9, 29)))  # Tuesday
        self.assertTrue(reminder.occurs(r, date(2026, 9, 30)))  # Wednesday

    def test_weekly_with_no_weekdays_never_lands(self):
        self.assertFalse(reminder.occurs(row(freq="weekly"), date(2026, 9, 28)))

    def test_monthly_lands_on_its_day_of_month(self):
        r = row(freq="monthly", on_day=5)
        self.assertTrue(reminder.occurs(r, date(2026, 3, 5)))
        self.assertTrue(reminder.occurs(r, date(2026, 4, 5)))
        self.assertFalse(reminder.occurs(r, date(2026, 3, 6)))

    def test_monthly_a_day_that_does_not_exist_in_a_shorter_month_never_lands(self):
        r = row(freq="monthly", on_day=31)
        self.assertFalse(reminder.occurs(r, date(2026, 2, 28)))
        self.assertTrue(reminder.occurs(r, date(2026, 1, 31)))

    def test_yearly_lands_on_month_and_day_together(self):
        r = row(freq="yearly", on_month=12, on_day=25)
        self.assertTrue(reminder.occurs(r, date(2026, 12, 25)))
        self.assertTrue(reminder.occurs(r, date(2030, 12, 25)))
        self.assertFalse(reminder.occurs(r, date(2026, 12, 24)))
        self.assertFalse(reminder.occurs(r, date(2026, 11, 25)))

    def test_once_lands_only_on_its_own_date(self):
        r = row(freq="once", on_date="2026-10-02")
        self.assertTrue(reminder.occurs(r, date(2026, 10, 2)))
        self.assertFalse(reminder.occurs(r, date(2026, 10, 3)))
        self.assertFalse(reminder.occurs(r, date(2026, 10, 1)))

    def test_paused_never_lands(self):
        r = row(freq="daily", status="paused")
        self.assertFalse(reminder.occurs(r, date(2026, 9, 28)))

    def test_an_unknown_freq_fails_closed(self):
        r = row(freq="hourly")
        self.assertFalse(reminder.occurs(r, date(2026, 9, 28)))

    def test_freq_alone_decides_the_anchor_the_other_fields_are_ignored(self):
        # A row carrying every anchor at once: only the one `freq` names is
        # read, whatever the day-of-month or the month happen to say.
        r = row(
            freq="weekly",
            on_weekday=[0],
            on_day=1,
            on_month=1,
            on_date="2026-09-28",
        )
        # Monday, 2026-09-28: the weekday matches, the others would not.
        self.assertTrue(reminder.occurs(r, date(2026, 9, 28)))
        # Thursday, 2026-10-01: matches on_day/on_month/on_date, not the weekday.
        self.assertFalse(reminder.occurs(r, date(2026, 10, 1)))


class Due(unittest.TestCase):
    """The day's split: what lands on it, and what is inside its warning."""

    def test_lands_today_and_excludes_paused(self):
        landing = row(freq="daily", text="a")
        paused = row(freq="daily", status="paused", text="b")
        found = reminder.due(date(2026, 9, 28), rows=[landing, paused])
        self.assertEqual(found["due"], [landing])
        self.assertEqual(found["warn"], [])

    def test_warn_window_catches_the_upcoming_occurrence(self):
        r = row(freq="once", on_date="2026-10-01", warn_days=[3, 1])
        found = reminder.due(date(2026, 9, 28), rows=[r])
        self.assertEqual(found["due"], [])
        self.assertEqual(found["warn"], [r])

    def test_a_day_outside_every_warn_window_is_neither(self):
        r = row(freq="once", on_date="2026-10-01", warn_days=[3, 1])
        found = reminder.due(date(2026, 9, 20), rows=[r])
        self.assertEqual(found["due"], [])
        self.assertEqual(found["warn"], [])

    def test_a_hit_on_due_is_never_also_counted_as_a_warning(self):
        # `warn_days` carries 0 on purpose: the occurrence itself would also
        # satisfy the warn check, and `due` must win the one slot it belongs in.
        r = row(freq="once", on_date="2026-10-01", warn_days=[0, 3])
        found = reminder.due(date(2026, 10, 1), rows=[r])
        self.assertEqual(found["due"], [r])
        self.assertEqual(found["warn"], [])

    def test_every_freq_is_covered_by_the_window_alike(self):
        weekly = row(freq="weekly", on_weekday=[0], warn_days=[2])
        # 2026-09-28 is a Monday; two days before is 2026-09-26, a Saturday.
        found = reminder.due(date(2026, 9, 26), rows=[weekly])
        self.assertEqual(found["warn"], [weekly])

    def test_a_reminder_with_no_warn_days_is_never_warned(self):
        r = row(freq="once", on_date="2026-10-01")
        found = reminder.due(date(2026, 9, 30), rows=[r])
        self.assertEqual(found["warn"], [])

    def test_today_defaults_to_the_injected_calendar(self):
        with mock.patch.object(reminder, "today", return_value=date(2026, 9, 28)):
            found = reminder.due(rows=[row(freq="daily")])
        self.assertEqual(len(found["due"]), 1)


class ReminderCase(unittest.TestCase):
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
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["reminder", "due", *words])
        return code, output.getvalue()


class TheDoor(ReminderCase):
    """`at-cli reminder due`, on the store the folder actually carries."""

    def test_lists_what_lands_on_a_given_day(self):
        tables.create(
            "reminder",
            {"text": "Regar a planta", "freq": "once", "on_date": "2026-10-05", "at": "09:00"},
        )
        code, text = self.cli("--at", "2026-10-05")
        self.assertEqual(code, 0)
        self.assertIn("Regar a planta", text)

    def test_accepts_a_day_in_the_past(self):
        tables.create(
            "reminder",
            {
                "text": "Já passou",
                "freq": "once",
                "on_date": "2020-01-05",
                "since": "2019-01-01",
                "at": "09:00",
            },
        )
        code, text = self.cli("--at", "2020-01-05")
        self.assertEqual(code, 0)
        self.assertIn("Já passou", text)

    def test_defaults_to_today_when_at_is_not_given(self):
        with mock.patch.object(reminder, "today", return_value=date(2026, 9, 28)):
            code, text = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("2026-09-28", text)

    def test_an_empty_day_says_nothing_here_yet(self):
        code, text = self.cli("--at", "2026-01-01")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.word.empty"), text)

    def test_a_day_that_is_not_a_day_is_a_usage_error(self):
        code, text = self.cli("--at", "não-é-uma-data")
        self.assertEqual(code, 2)
        self.assertIn(tr("reminder.due.error.arguments"), text)

    def test_an_at_with_no_value_is_a_usage_error(self):
        code, text = self.cli("--at")
        self.assertEqual(code, 2)

    def test_an_extra_argument_is_a_usage_error(self):
        code, text = self.cli("--at", "2026-09-28", "--all")
        self.assertEqual(code, 2)

    def test_it_leaves_no_line_and_no_version(self):
        # §3: reading is not doing. `due` writes nothing, so there is no audit
        # line to keep.
        before = files.writes()
        self.cli()
        self.assertEqual(files.writes(), before)
        self.assertEqual(
            [line for line in store.load("audit") if line.get("what") == "reminder:due"],
            [],
        )

    def test_the_door_itself_needs_no_actor_and_no_via(self):
        code, text = door.reminder_due(["--at", "2026-01-01"])
        self.assertEqual(code, 0)

    def test_every_sentence_speaks_both_languages(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                with mock.patch.dict(os.environ, {"AT_LANG": language}):
                    i18n.reset()
                    for key in SAID:
                        self.assertNotEqual(tr(key), key)


class TheNotified(ReminderCase):
    """The round's own guard, per (day, HOUR) (TASK-145)."""

    def marked(self):
        # Two hours in one day: the guard has to tell them apart.
        return tables.create(
            "reminder", row(freq="daily", text="Regar", at=["09:00", "18:00"])
        )

    def test_a_row_never_marked_answers_false(self):
        made = self.marked()
        self.assertFalse(reminder.notified(made, date(2026, 9, 28), "09:00"))

    def test_marking_writes_the_day_and_hour_and_reads_it_true(self):
        made = self.marked()
        reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        held = store.find("reminder", store.number_of(made))
        self.assertEqual(held.get("notified"), ["2026-09-28 09:00"])
        self.assertTrue(reminder.notified(held, date(2026, 9, 28), "09:00"))

    def test_the_other_hour_of_the_same_day_is_not_notified(self):
        made = self.marked()
        reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        held = store.find("reminder", store.number_of(made))
        self.assertFalse(reminder.notified(held, date(2026, 9, 28), "18:00"))

    def test_a_different_day_is_not_notified(self):
        made = self.marked()
        reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        held = store.find("reminder", store.number_of(made))
        self.assertFalse(reminder.notified(held, date(2026, 9, 29), "09:00"))

    def test_marking_writes_no_line_and_no_actor_is_needed(self):
        # The engine's own bookkeeping (§3): the same posture `jobs.reschedule`
        # keeps for the one field the clock owns on a job's row.
        made = self.marked()
        before = [line for line in store.load("audit")]
        reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        self.assertEqual(store.load("audit"), before)

    def test_a_row_deleted_between_the_read_and_the_write_is_handed_back_untouched(self):
        made = self.marked()
        tables.delete("reminder", store.number_of(made))
        same = reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        self.assertEqual(same, made)


class TheRound(ReminderCase):
    """`door.remind`: the clock's OTHER schedule, with the network taken away
    (TASK-145).

    Every row here is dated by `row()` (`since` in 2020) rather than by a
    bare dict: the engine dates `since` to the REAL day when the row does not
    carry one, so a hardcoded day this class names would be green the day it
    was written and red every day after it receded behind that default.
    """

    def sent(self, ok: bool = True):
        """A `send` seam that answers instead of reaching a real notifier."""
        calls: list[tuple[str, str, object]] = []

        def push(title: str, body: str, key):
            calls.append((title, body, key))
            return ok, "200" if ok else "failed"

        return calls, push

    def test_a_due_reminder_is_pushed_once_and_marked(self):
        made = tables.create(
            "reminder",
            row(text="Regar a planta", freq="once", on_date="2026-10-05",
                at=["09:00"]),
        )
        calls, push = self.sent()
        fired = door.remind(datetime(2026, 10, 5, 9, 0), key=b"k" * 32, send=push)
        self.assertEqual(fired, [made])
        self.assertEqual(len(calls), 1)
        title, body, key = calls[0]
        self.assertIn("Regar a planta", body)
        self.assertEqual(key, b"k" * 32)
        held = store.find("reminder", store.number_of(made))
        self.assertEqual(held.get("notified"), ["2026-10-05 09:00"])

    def test_a_hour_the_pass_does_not_cover_is_not_pushed(self):
        tables.create("reminder", row(freq="daily", text="Regar", at=["09:00"]))
        calls, push = self.sent()
        # 09:00 é devida à passada que cobre o SEU minuto; a das 09:20 cobre o
        # minuto 09:20, e o de 09:00 passou.
        fired = door.remind(datetime(2026, 9, 28, 9, 20), send=push)
        self.assertEqual(fired, [])
        self.assertEqual(calls, [])

    def test_each_hour_of_the_day_gets_its_own_push(self):
        tables.create("reminder", row(freq="daily", text="Regar", at=["09:00", "18:00"]))
        calls, push = self.sent()
        self.assertEqual(len(door.remind(datetime(2026, 9, 28, 9, 0), send=push)), 1)
        self.assertEqual(door.remind(datetime(2026, 9, 28, 9, 0), send=push), [])
        self.assertEqual(len(door.remind(datetime(2026, 9, 28, 18, 0), send=push)), 1)
        self.assertEqual(len(calls), 2)

    def test_a_warned_reminder_gets_its_own_text_and_is_marked(self):
        tables.create(
            "reminder",
            row(text="Pagar o boleto", freq="once", on_date="2026-10-05",
                warn_days=[2], at=["09:00"]),
        )
        calls, push = self.sent()
        fired = door.remind(datetime(2026, 10, 3, 9, 0), send=push)
        self.assertEqual(len(fired), 1)
        self.assertEqual(len(calls), 1)
        _, body, _ = calls[0]
        self.assertIn("Pagar o boleto", body)
        self.assertNotEqual(
            tr("reminder.push.warn", text="x"), tr("reminder.push.due", text="x")
        )

    def test_a_reminder_already_notified_this_hour_is_not_pushed_again(self):
        made = tables.create(
            "reminder",
            row(text="Regar a planta", freq="daily", at=["09:00"]),
        )
        reminder.mark_notified(made, date(2026, 9, 28), "09:00")
        calls, push = self.sent()
        fired = door.remind(datetime(2026, 9, 28, 9, 0), send=push)
        self.assertEqual(fired, [])
        self.assertEqual(calls, [])

    def test_a_push_that_fails_is_not_marked_and_is_retried_next_pass(self):
        tables.create(
            "reminder",
            row(text="Regar a planta", freq="daily", at=["09:00"]),
        )
        calls, push = self.sent(ok=False)
        fired = door.remind(datetime(2026, 9, 28, 9, 0), send=push)
        self.assertEqual(fired, [])
        self.assertEqual(len(calls), 1)
        held = store.find("reminder", 1)
        self.assertNotIn("notified", held)

    def test_nothing_due_or_warned_pushes_nothing(self):
        calls, push = self.sent()
        fired = door.remind(datetime(2026, 1, 1, 9, 0), send=push)
        self.assertEqual(fired, [])
        self.assertEqual(calls, [])

    def test_a_readonly_folder_applies_nothing(self):
        tables.create(
            "reminder",
            row(text="Regar a planta", freq="daily", at=["09:00"]),
        )
        calls, push = self.sent()
        with mock.patch.dict(os.environ, {files.ENV_READONLY: "1"}):
            fired = door.remind(datetime(2026, 9, 28, 9, 0), send=push)
        self.assertEqual(fired, [])
        self.assertEqual(calls, [])

    def test_with_no_send_it_reaches_the_real_publish_door(self):
        # No network in the suite: with no subscriber the real `notifier
        # .publish` answers `no_subscribers` on its own, without a seam and
        # without touching the wire.
        tables.create(
            "reminder",
            row(text="Regar a planta", freq="daily", at=["09:00"]),
        )
        fired = door.remind(datetime(2026, 9, 28, 9, 0))
        self.assertEqual(fired, [])


class TheWord(ReminderCase):
    """The act in the catalogue, in the tree and in the role."""

    def test_the_catalogue_keeps_the_six_and_adds_due(self):
        self.assertEqual(
            permissions.catalogue().get("reminder"),
            ("list", "view", "create", "edit", "cancel", "delete", "due"),
        )
        self.assertTrue(permissions.is_known("reminder:due"))
        # It is a read: it reports and corrects nothing, so it moves no ceiling.
        self.assertEqual(permissions.risk("reminder:due"), permissions.RISK_READ)
        self.assertEqual(permissions.needed("reminder", "due"), "reminder:due")

    def test_the_ordinary_six_still_read_their_own_names(self):
        for action in ("list", "view", "create", "edit", "cancel", "delete"):
            self.assertEqual(permissions.needed("reminder", action), f"reminder:{action}")

    def test_the_tree_offers_it_beside_the_engine_s_acts(self):
        node = next(node for node in tree.table_nodes() if node.name == "reminder")
        self.assertEqual(
            [child.name for child in node.children],
            ["list", "view", "create", "edit", "cancel", "delete", "due"],
        )

    def test_the_administrator_carries_it(self):
        role = actors.role_for_admin()
        self.assertIn("reminder:due", permissions.carried(role))


class TheListing(ReminderCase):
    """A bare day in a `list` reads the day's OCCURRENCES, the generalization
    `ask._bare_day` gives `nlu.matcher.open_day_field` for this table alone —
    the field it leaves open (`on_date`) only ever covers a `once` reminder read
    literally, and "lembretes de hoje" names no field at all."""

    def test_a_bare_day_finds_what_occurs_on_it_not_just_on_date(self):
        today = reminder.today()
        tomorrow = today + timedelta(days=1)
        tables.create("reminder", {
            "text": "beber agua", "freq": "daily", "at": ["09:00"],
            "status": "active", "since": "2020-01-01",
        })
        tables.create("reminder", {
            "text": "pagar aluguel", "freq": "once", "at": ["09:00"],
            "status": "active", "since": "2020-01-01", "on_date": today.isoformat(),
        })
        tables.create("reminder", {
            "text": "consulta", "freq": "once", "at": ["09:00"],
            "status": "active", "since": "2020-01-01", "on_date": tomorrow.isoformat(),
        })
        result = door.ask("listar lembretes hoje")
        self.assertEqual(result.kind, "answer")
        self.assertIn("beber agua", result.text)
        self.assertIn("pagar aluguel", result.text)
        self.assertNotIn("consulta", result.text)

    def test_a_range_keeps_the_literal_field_comparison(self):
        # "até sexta" is a RANGE, and folding a range through the recurrence is
        # not this fatia's: the old, literal `on_date` comparison still answers
        # it, so a `once` reminder dated past the range is correctly left out
        # and one with no `on_date` at all (a `daily`) matches nothing either —
        # exactly what the field comparison always did.
        far = reminder.today() + timedelta(days=30)
        tables.create("reminder", {
            "text": "viagem", "freq": "once", "at": ["09:00"],
            "status": "active", "since": "2020-01-01", "on_date": far.isoformat(),
        })
        tables.create("reminder", {
            "text": "beber agua", "freq": "daily", "at": ["09:00"],
            "status": "active", "since": "2020-01-01",
        })
        result = door.ask("listar lembretes até amanhã")
        self.assertEqual(result.kind, "answer")
        # Not the generic "nada aqui ainda": a range still names itself
        # (`ask._described`), the same way the exact-day case already did.
        self.assertIn("até", result.text)


if __name__ == "__main__":
    unittest.main()
