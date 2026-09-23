"""The two fixed types of §4 — `day` and `instant` — and the stamp that follows.

The engine knows two kinds of time, and they are not the same thing: a `day` is
a calendar day, with no time and no zone, and an `instant` is a point in time,
in UTC and always with milliseconds. Both are declared in the schema, both are
checked on the way in, and neither is guessed — what does not fit is refused by
the field's label, in the active language.

Every test aims Bill at a throwaway folder with `BILL_ROOT`, so none of them
touches the checkout's own Working Folder.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from bill import i18n
from bill.core import boot, paths, tables
from bill.data import schema, store
from bill.ui.cli import main

# What §4 fixes: an instant is UTC and always carries milliseconds, and a day is
# a date with nothing after it.
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")

# A table of the instance's own, written into the throwaway folder. The product's
# three carry a day and the log's instant; declaring a field of each type in a
# table nobody shipped is what proves the engine reads the TYPE and not a list of
# names. The labels are keys the product already ships, so what a refusal prints
# is the text a person reads — `Desde` and `Prazo`, in `pt_BR`.
MOMENT = {
    "id": "moment",
    "order": 90,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/moments.jsonl",
    "primary": "text",
    "columns": ["text"],
    "fields": {
        "id": {"label": "table.field.id"},
        "text": {"label": "table.task.field.text"},
        "since": {"label": "table.task.field.since", "type": "day"},
        "when": {"label": "table.task.field.deadline", "type": "instant"},
        "state": {
            "label": "table.task.field.status",
            "enum": {
                "todo": "table.task.field.status.todo",
                "doing": "table.task.field.status.doing",
            },
            "default": "todo",
        },
        "note": {"label": "table.task.field.desc"},
        # One log that declares its type, and one that declares none: the first
        # follows the declaration, and the second is what a log born before the
        # types existed keeps carrying — a day.
        "log_day": {
            "label": "table.task.field.modifications",
            "type": "list",
            "tracks": "state",
            "append": {"text": "state", "stamp": "at", "type": "day"},
            "default": [],
        },
        "log_plain": {
            "label": "table.task.field.modifications",
            "type": "list",
            "tracks": "note",
            "append": {"text": "note", "stamp": "at"},
            "default": [],
        },
    },
}


class TypeCase(unittest.TestCase):
    """A configured folder of its own, and the declared table that lives in it."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"BILL_ROOT": str(self.root), "BILL_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(StringIO()):
            boot.create_working_folder()
        self.declare(MOMENT)

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        # The declarations are cached per process and this folder is gone: a
        # cache left behind would hand the next test a table that is not there.
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def declare(self, table: dict) -> None:
        where = paths.data_dir() / schema.SCHEMA_DIR / f"{table['id']}.json"
        where.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()

    @contextmanager
    def zone(self, name: str):
        """The machine's zone, which is what a naive instant is read in.

        `tzset` is the only way to move the process's zone, and it is POSIX —
        which is why this is the one test that says out loud what machine it
        needs.
        """
        previous = os.environ.get("TZ")
        os.environ["TZ"] = name
        time.tzset()
        try:
            yield
        finally:
            if previous is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = previous
            time.tzset()

    def words(self, *args: str) -> tuple[int, str]:
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()


class TheDay(TypeCase):
    def test_a_declared_day_round_trips_as_text(self):
        row = tables.create("moment", {"text": "café", "since": "2026-10-03"})
        self.assertEqual(row["since"], "2026-10-03")
        self.assertEqual(store.find("moment", row["id"])["since"], "2026-10-03")
        self.assertRegex(row["since"], DAY)

    def test_today_is_the_local_day_of_whoever_writes(self):
        row = tables.create("moment", {"text": "café", "since": "today"})
        self.assertEqual(row["since"], date.today().isoformat())
        self.assertRegex(row["since"], DAY)

    def test_the_declared_default_of_a_day_field_is_a_day(self):
        row = tables.create("task", {"text": "café"})
        self.assertEqual(row["since"], date.today().isoformat())
        self.assertRegex(row["since"], DAY)

    def test_what_is_not_a_day_is_refused_by_its_label(self):
        with self.assertRaises(tables.TableError) as refused:
            tables.create("moment", {"text": "café", "since": "03/10/2026"})
        self.assertIn("Desde", str(refused.exception))
        self.assertIn("03/10/2026", str(refused.exception))

    def test_a_day_that_does_not_exist_is_refused(self):
        with self.assertRaises(tables.TableError) as refused:
            tables.create("moment", {"text": "café", "since": "2026-02-30"})
        self.assertIn("Desde", str(refused.exception))

    def test_an_instant_is_not_a_day(self):
        with self.assertRaises(tables.TableError) as refused:
            tables.create("moment", {"text": "café", "since": "2026-10-03T10:00:00Z"})
        self.assertIn("Desde", str(refused.exception))

    def test_a_refused_value_is_answered_in_the_active_language(self):
        with mock.patch.dict(os.environ, {"BILL_LANG": "en_US"}):
            i18n.reset()
            with self.assertRaises(tables.TableError) as refused:
                tables.create("moment", {"text": "coffee", "since": "03/10/2026"})
        self.assertIn("Since", str(refused.exception))
        self.assertNotIn("table.task.field.since", str(refused.exception))


class TheInstant(TypeCase):
    def test_an_instant_round_trips_as_utc_with_milliseconds(self):
        row = tables.create(
            "moment", {"text": "café", "when": "2026-09-22T13:04:07.123-03:00"}
        )
        self.assertEqual(row["when"], "2026-09-22T16:04:07.123Z")
        self.assertEqual(store.find("moment", row["id"])["when"], row["when"])
        self.assertRegex(row["when"], INSTANT)

    def test_an_instant_with_no_offset_is_read_in_the_machine_zone(self):
        with self.zone("BRT3"):
            here = tables.create(
                "moment", {"text": "café", "when": "2026-09-22T13:04:07"}
            )["when"]
        with self.zone("UTC"):
            there = tables.create(
                "moment", {"text": "café", "when": "2026-09-22T13:04:07"}
            )["when"]
        self.assertEqual(here, "2026-09-22T16:04:07.000Z")
        self.assertEqual(there, "2026-09-22T13:04:07.000Z")

    def test_now_is_the_instant_the_machine_is_in(self):
        row = tables.create("moment", {"text": "café", "when": "now"})
        self.assertRegex(row["when"], INSTANT)
        written = datetime.fromisoformat(row["when"].replace("Z", "+00:00"))
        self.assertLess(abs((datetime.now(timezone.utc) - written).total_seconds()), 60)

    def test_a_bare_day_is_not_an_instant(self):
        with self.assertRaises(tables.TableError) as refused:
            tables.create("moment", {"text": "café", "when": "2026-09-22"})
        self.assertIn("Prazo", str(refused.exception))

    def test_what_is_not_an_instant_is_refused_by_its_label(self):
        with self.assertRaises(tables.TableError) as refused:
            tables.create("moment", {"text": "café", "when": "meio-dia"})
        self.assertIn("Prazo", str(refused.exception))


class TheStamp(TypeCase):
    """The `tracks`/`append` log: the engine stamps it, in the declared type."""

    def test_the_three_declarations_name_their_types(self):
        bundled = schema.bundled()
        for table, field in (
            ("task", "since"),
            ("task", "deadline"),
            ("project", "since"),
            ("reminder", "since"),
            ("reminder", "on_date"),
        ):
            with self.subTest(table=table, field=field):
                self.assertEqual(bundled[table]["fields"][field]["type"], "day")
        appended = bundled["task"]["fields"]["modifications"]["append"]
        self.assertEqual(appended["type"], "instant")

    def test_the_status_log_is_stamped_with_the_declared_instant(self):
        row = tables.create("task", {"text": "café"})
        edited = tables.edit("task", row["id"], {"status": "done"})
        self.assertEqual(edited["modifications"][-1]["status"], "done")
        self.assertRegex(edited["modifications"][-1]["at"], INSTANT)

    def test_a_log_that_declares_a_day_is_stamped_with_a_day(self):
        row = tables.create("moment", {"text": "café", "state": "doing"})
        self.assertEqual(row["log_day"][-1]["at"], date.today().isoformat())

    def test_a_log_that_declares_nothing_keeps_the_day(self):
        row = tables.create("moment", {"text": "café", "note": "primeira"})
        self.assertEqual(row["log_plain"][-1]["at"], date.today().isoformat())

    def test_no_instant_in_the_store_is_a_naive_local_one(self):
        row = tables.create("task", {"text": "café"})
        tables.edit("task", row["id"], {"status": "doing"})
        body = (paths.data_dir() / "tasks.jsonl").read_text(encoding="utf-8")
        found = re.findall(r"\d{4}-\d{2}-\d{2}T[^\"]*", body)
        self.assertTrue(found)
        for value in found:
            self.assertRegex(value, INSTANT)


class TheDisplay(TypeCase):
    """What a person reads: the reader's shape, in the reader's clock (§4)."""

    def test_a_day_reads_in_the_locale_order(self):
        row = tables.create("moment", {"text": "café", "since": "2026-10-03"})
        self.assertEqual(tables.text_of("moment", "since", row["since"]), "03/10/2026")

    def test_the_other_language_reads_the_same_day_its_own_way(self):
        row = tables.create("moment", {"text": "coffee", "since": "2026-10-03"})
        with mock.patch.dict(os.environ, {"BILL_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(
                tables.text_of("moment", "since", row["since"]), "10/03/2026"
            )

    def test_an_instant_reads_in_the_readers_clock(self):
        written = "2026-09-22T20:40:52.295Z"
        with self.zone("BRT3"):
            self.assertEqual(
                tables.text_of("moment", "when", written), "22/09/2026 17:40"
            )
        with self.zone("UTC"):
            self.assertEqual(
                tables.text_of("moment", "when", written), "22/09/2026 20:40"
            )

    def test_the_log_stamp_reads_like_a_field_does(self):
        row = tables.create("task", {"text": "café"})
        edited = tables.edit("task", row["id"], {"status": "done"})
        with self.zone("BRT3"):
            read = tables.text_of("task", "modifications", edited["modifications"])
        self.assertEqual(len(edited["modifications"]), 2)
        self.assertRegex(read, r"status=done, at=\d{2}/\d{2}/\d{4} \d{2}:\d{2}$")
        self.assertNotIn("Z", read)

    def test_a_row_written_before_the_types_is_still_readable(self):
        # A folder that predates the declaration keeps its rows, and a value the
        # display cannot parse is shown as it is stored instead of hidden.
        self.assertEqual(tables.text_of("task", "since", "today"), "today")
        self.assertEqual(tables.text_of("task", "deadline", ""), "")
        old = [{"status": "todo", "at": "2026-09-21"}]
        self.assertEqual(
            tables.text_of("task", "modifications", old), "status=todo, at=2026-09-21"
        )


class TheDoor(TypeCase):
    def test_the_cli_the_person_types_in_refuses_the_bad_day(self):
        code, text = self.words(
            "task", "create", "--set", "text=café", "--set", "deadline=amanhã"
        )
        self.assertEqual(code, 1)
        self.assertIn("Prazo", text)

    def test_the_cli_takes_the_good_day(self):
        code, text = self.words(
            "task", "create", "--set", "text=café", "--set", "deadline=2026-10-03"
        )
        self.assertEqual(code, 0)
        self.assertEqual(tables.find("task", 1)["deadline"], "2026-10-03")


if __name__ == "__main__":
    unittest.main()
