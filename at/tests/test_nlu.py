"""The interpreter's ruler (§9): the sentences of date, time and number.

The ruler has three lists, and they are the three this file carries: the
sentences that must work, the sentences that must be refused, and the ambiguous
ones that must come back as a question. A fourth is the rule underneath all
three — what does not resolve is **residue, never a guess** — and it is checked
on its own, because it is the one that fails silently when it fails.

Both languages are ruled, because the grammar is code per language and the same
word does not live in the same domain in the two: `duas` is two and two o'clock,
`meia` is half and is half past, and English says the half from the other end
(`half past two`). The clock is injected and the zone is the process's, the same
path `test_types` takes, so no sentence here depends on the day it is run.

Nothing in this file needs a network or a model, and one test says so out loud.
"""

from __future__ import annotations

import json
import os
import re
import socket
import tempfile
import time
import unittest
from contextlib import contextmanager, redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import boot, paths, tables
from at.data import schema, store
from at.nlu import grammar

# The clock every sentence below hangs from: a Tuesday at ten in the morning, in
# the zone the ruler pins. A month with thirty days, so `dia 31` has to look for
# the next month that carries it.
NOW = datetime(2026, 9, 22, 10, 0)
ZONE = "BRT3"

# What §4 fixes, and what every answer of the grammar must fit: a day is a local
# calendar day, an instant is UTC and always carries milliseconds.
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class RulerCase(unittest.TestCase):
    """The active language, and the zone the sentences are read in."""

    def setUp(self):
        self.env = mock.patch.dict(
            os.environ, {"AT_LANG": "pt_BR", "TZ": ZONE}
        )
        self.env.start()
        time.tzset()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        time.tzset()
        i18n.reset()

    @contextmanager
    def speaking(self, language: str):
        with mock.patch.dict(os.environ, {"AT_LANG": language}):
            i18n.reset()
            try:
                yield
            finally:
                i18n.reset()

    @contextmanager
    def zone(self, name: str):
        """The machine's zone — the one a clock time with no zone is read in."""
        previous = os.environ.get("TZ")
        os.environ["TZ"] = name
        time.tzset()
        try:
            yield
        finally:
            os.environ["TZ"] = previous if previous is not None else ZONE
            time.tzset()

    def read(self, phrase: str, kind: str, language: str = "pt_BR", now=NOW):
        """What the active language's grammar reads in a phrase."""
        with self.speaking(language):
            return nlu.resolve(phrase, kind, now=now)

    def value(self, phrase: str, kind: str, language: str = "pt_BR", now=NOW):
        """The value a phrase resolves to — loud when it does not resolve."""
        reading = self.read(phrase, kind, language, now)
        self.assertIsInstance(
            reading, nlu.Value, f"{phrase!r} did not resolve: {reading!r}"
        )
        return reading.value


class TheRuler(RulerCase):
    """The sentences that must work, in both languages."""

    def test_the_named_sentences_resolve_in_portuguese(self):
        # The item's own list — `sexta`, `amanhã`, `dia 3`, `duas` and `meia` —
        # each in the type that settles what it means.
        for phrase, kind, expected in (
            ("sexta", "day", "2026-09-25"),
            ("amanhã", "day", "2026-09-23"),
            ("dia 3", "day", "2026-10-03"),
            ("duas", "number", 2),
            ("meia", "number", 0.5),
        ):
            with self.subTest(phrase=phrase, kind=kind):
                self.assertEqual(self.value(phrase, kind), expected)

    def test_the_named_sentences_resolve_in_english(self):
        for phrase, kind, expected in (
            ("friday", "day", "2026-09-25"),
            ("tomorrow", "day", "2026-09-23"),
            ("the 3rd", "day", "2026-10-03"),
            ("two", "number", 2),
            ("half", "number", 0.5),
        ):
            with self.subTest(phrase=phrase, kind=kind):
                self.assertEqual(self.value(phrase, kind, "en_US"), expected)

    def test_a_word_that_lives_in_two_domains_answers_the_declared_one(self):
        # `duas` is two and is two o'clock: the field's type is what decides, and
        # both answers come from the same word.
        self.assertEqual(self.value("duas", "number"), 2)
        self.assertEqual(self.value("duas", "instant"), "2026-09-22T05:00:00.000Z")
        self.assertEqual(self.value("two", "number", "en_US"), 2)
        self.assertEqual(self.value("two", "instant", "en_US"), "2026-09-22T05:00:00.000Z")

    def test_half_is_half_of_something_and_half_past_an_hour(self):
        # The pair the item names: `meia` is metade and são trinta minutos. In a
        # number field it is half of a dozen; in an instant field it is half of
        # the hour it is said with.
        self.assertEqual(self.value("meia", "number"), 0.5)
        self.assertEqual(self.value("duas e meia", "number"), 2.5)
        self.assertEqual(self.value("duas e meia", "instant"), "2026-09-22T05:30:00.000Z")
        self.assertEqual(self.value("meio-dia e meia", "instant"), "2026-09-22T15:30:00.000Z")
        self.assertEqual(self.value("half", "number", "en_US"), 0.5)
        self.assertEqual(self.value("two and a half", "number", "en_US"), 2.5)
        self.assertEqual(
            self.value("half past two", "instant", "en_US"), "2026-09-22T05:30:00.000Z"
        )

    def test_the_weekday_is_the_coming_one_and_today_counts(self):
        # The 22nd is a Tuesday: `terça` is today itself, and the week follows.
        for phrase, expected in (
            ("terça", "2026-09-22"),
            ("quarta", "2026-09-23"),
            ("quinta", "2026-09-24"),
            ("sexta", "2026-09-25"),
            ("sexta-feira", "2026-09-25"),
            ("sábado", "2026-09-26"),
            ("domingo", "2026-09-27"),
            ("segunda", "2026-09-28"),
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.value(phrase, "day"), expected)

    def test_the_day_of_the_month_is_the_coming_one(self):
        self.assertEqual(self.value("dia 22", "day"), "2026-09-22")   # today counts
        self.assertEqual(self.value("dia 23", "day"), "2026-09-23")
        self.assertEqual(self.value("dia 3", "day"), "2026-10-03")    # this month's has gone
        self.assertEqual(self.value("dia três", "day"), "2026-10-03")
        self.assertEqual(self.value("dia 31", "day"), "2026-10-31")   # September is too short
        self.assertEqual(self.value("the 22nd", "day", "en_US"), "2026-09-22")
        self.assertEqual(self.value("the 31st", "day", "en_US"), "2026-10-31")

    def test_a_clock_time_is_read_to_the_minute(self):
        for phrase in ("14:30", "14h30"):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.value(phrase, "instant"), "2026-09-22T17:30:00.000Z")
        self.assertEqual(self.value("14h", "instant"), "2026-09-22T17:00:00.000Z")
        self.assertEqual(self.value("2:30 pm", "instant", "en_US"), "2026-09-22T17:30:00.000Z")
        self.assertEqual(self.value("2pm", "instant", "en_US"), "2026-09-22T17:00:00.000Z")
        self.assertEqual(self.value("11am", "instant", "en_US"), "2026-09-22T14:00:00.000Z")

    def test_the_two_hours_the_language_writes_whole(self):
        self.assertEqual(self.value("meia-noite", "instant"), "2026-09-22T03:00:00.000Z")
        self.assertEqual(self.value("meio-dia", "instant"), "2026-09-22T15:00:00.000Z")
        self.assertEqual(self.value("midnight", "instant", "en_US"), "2026-09-22T03:00:00.000Z")
        self.assertEqual(self.value("noon", "instant", "en_US"), "2026-09-22T15:00:00.000Z")

    def test_a_written_numeral_is_read_in_the_language_of_the_reader(self):
        # The separator is the language's: a Portuguese `3.5` is three thousand
        # and a half of nothing, and reading it as three and a half would be a
        # defect dressed up as a feature.
        self.assertEqual(self.value("3,5", "number"), 3.5)
        self.assertEqual(self.value("3.5", "number", "en_US"), 3.5)
        self.assertEqual(self.value("três", "number"), 3)
        self.assertEqual(self.value("vinte", "number"), 20)
        self.assertEqual(self.value("twenty", "number", "en_US"), 20)

    def test_case_and_accents_are_the_writers_to_skip(self):
        self.assertEqual(self.value("SEXTA", "day"), "2026-09-25")
        self.assertEqual(self.value("Sabado", "day"), "2026-09-26")
        self.assertEqual(self.value("amanha", "day"), "2026-09-23")
        self.assertEqual(self.value("FRIDAY", "day", "en_US"), "2026-09-25")


class WhatIsRefused(RulerCase):
    """An expression of the kind that names a value no calendar or clock has."""

    def test_a_day_no_month_carries_is_refused(self):
        for phrase, language in (
            ("dia 32", "pt_BR"),
            ("dia 0", "pt_BR"),
            ("the 32nd", "en_US"),
        ):
            with self.subTest(phrase=phrase):
                with self.assertRaises(nlu.Refused) as refused:
                    self.read(phrase, "day", language)
                self.assertEqual(refused.exception.key, "nlu.error.no_such_day")

    def test_an_hour_no_clock_has_is_refused(self):
        for phrase, language in (
            ("25:00", "pt_BR"),
            ("14:75", "pt_BR"),
            ("25:00", "en_US"),
            ("13pm", "en_US"),
        ):
            with self.subTest(phrase=phrase):
                with self.assertRaises(nlu.Refused) as refused:
                    self.read(phrase, "instant", language)
                self.assertEqual(refused.exception.key, "nlu.error.no_such_clock")

    def test_the_refusal_speaks_the_active_language(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.read("dia 32", "day")
        self.assertEqual(str(refused.exception), "Não existe o dia 32.")
        with self.speaking("en_US"):
            with self.assertRaises(nlu.Refused) as refused:
                self.read("the 32nd", "day", "en_US")
        self.assertEqual(str(refused.exception), "There is no day 32.")

    def test_the_reason_of_a_refusal_is_in_the_catalogue_of_both_languages(self):
        # A refusal leaves a key, and a key that has no text is a raw key on the
        # screen — so the two languages carry it or the ruler fails here.
        for key in ("nlu.error.no_such_day", "nlu.error.no_such_clock"):
            for language in i18n.SUPPORTED:
                with self.subTest(key=key, language=language):
                    self.assertNotEqual(i18n.text(key, language), key)


class WhatIsAskedBack(RulerCase):
    """A phrase with more than one reading that the declared kind settles none of."""

    def test_half_past_without_its_hour_comes_back_as_a_question(self):
        question = self.read("meia", "instant")
        self.assertIsInstance(question, nlu.Question)
        self.assertEqual(question.key, "nlu.ask.which_hour")
        self.assertEqual(question.text, "meia")

    def test_english_asks_the_same_way(self):
        question = self.read("half", "instant", "en_US")
        self.assertIsInstance(question, nlu.Question)
        self.assertEqual(question.key, "nlu.ask.which_hour")
        self.assertEqual(question.text, "half")

    def test_the_question_is_never_the_likeliest_reading(self):
        # The same word answers where the type does settle it, and asks where it
        # does not: nothing is filled in for the hour that was not said.
        self.assertEqual(self.value("meia", "number"), 0.5)
        self.assertEqual(self.value("duas e meia", "instant"), "2026-09-22T05:30:00.000Z")
        self.assertIsInstance(self.read("meia", "instant"), nlu.Question)
        self.assertIsInstance(self.read("half", "instant", "en_US"), nlu.Question)

    def test_the_question_is_in_the_catalogue_of_both_languages(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                text = i18n.text("nlu.ask.which_hour", language)
                self.assertNotEqual(text, "nlu.ask.which_hour")
                self.assertIn("hora" if language == "pt_BR" else "hour", text)


class TheResidue(RulerCase):
    """What does not resolve is residue, and it comes back as it went in."""

    def test_a_phrase_outside_the_three_domains_is_residue(self):
        for phrase in ("banana", "uma tarefa", "", "  "):
            with self.subTest(phrase=phrase):
                reading = self.read(phrase, "day")
                self.assertIsInstance(reading, nlu.Residue)
                self.assertEqual(reading.text, phrase)

    def test_a_word_of_the_other_language_is_residue(self):
        # The grammar is the active language's, and a word of the other one is
        # not half-read: it is not a date here at all.
        self.assertIsInstance(self.read("friday", "day"), nlu.Residue)
        self.assertIsInstance(self.read("sexta", "day", "en_US"), nlu.Residue)
        self.assertIsInstance(self.read("amanhã", "day", "en_US"), nlu.Residue)

    def test_a_word_of_another_domain_is_residue(self):
        # A day asked of an instant field is not turned into midnight: the clock
        # is not invented, which is §4's own rule for the type.
        self.assertIsInstance(self.read("sexta", "instant"), nlu.Residue)
        self.assertIsInstance(self.read("amanhã", "instant"), nlu.Residue)
        self.assertIsInstance(self.read("dia 3", "instant"), nlu.Residue)
        # And a number asked of a day field is not a day of the month.
        self.assertIsInstance(self.read("duas", "day"), nlu.Residue)
        self.assertIsInstance(self.read("3", "day"), nlu.Residue)
        self.assertIsInstance(self.read("14:30", "day"), nlu.Residue)

    def test_a_number_no_clock_has_is_not_read_as_an_hour(self):
        # A bare number is not a clock expression: outside the hours that exist
        # it is a residue, and not a guessed period of the day.
        self.assertIsInstance(self.read("99", "instant"), nlu.Residue)
        self.assertIsInstance(self.read("noventa", "instant"), nlu.Residue)


class TheType(RulerCase):
    """The answer is written the way §4 writes the type the field declares."""

    def test_a_day_answers_as_a_local_day(self):
        for phrase in ("sexta", "amanhã", "dia 3", "hoje"):
            with self.subTest(phrase=phrase):
                self.assertRegex(self.value(phrase, "day"), DAY)

    def test_an_instant_answers_as_utc_with_milliseconds(self):
        for phrase in ("duas", "14:30", "meia-noite", "duas e meia"):
            with self.subTest(phrase=phrase):
                self.assertRegex(self.value(phrase, "instant"), INSTANT)

    def test_a_kind_no_reader_answers_to_is_loud(self):
        with self.assertRaises(ValueError):
            self.read("sexta", "gender")


class TheField(RulerCase):
    """The answer goes into the field it was read for, and the field keeps it.

    A table of the instance's own, declaring the three kinds side by side: what
    is read here is the TYPE the declaration carries, and not a list of names.
    """

    def setUp(self):
        super().setUp()
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        with mock.patch.dict(os.environ, {"AT_ROOT": str(self.root)}):
            with redirect_stdout(StringIO()):
                boot.create_working_folder()
            self.where = paths.data_dir() / schema.SCHEMA_DIR / "moment.json"
            self.where.write_text(
                json.dumps(
                    {
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
                            "count": {"label": "table.task.field.priority", "type": "number"},
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        schema.reset()
        self.inside = mock.patch.dict(os.environ, {"AT_ROOT": str(self.root)})
        self.inside.start()

    def tearDown(self):
        self.inside.stop()
        schema.reset()
        store.reset()
        self.scratch.cleanup()
        super().tearDown()

    def test_the_answer_is_what_the_field_stores(self):
        row = tables.create(
            "moment",
            {
                "text": "café",
                "since": self.value("sexta", "day"),
                "when": self.value("duas", "instant"),
                "count": self.value("meia", "number"),
            },
        )
        self.assertEqual(row["since"], "2026-09-25")
        self.assertEqual(row["when"], "2026-09-22T05:00:00.000Z")
        self.assertEqual(row["count"], 0.5)
        self.assertEqual(store.find("moment", row["id"])["when"], row["when"])
        self.assertRegex(row["since"], DAY)
        self.assertRegex(row["when"], INSTANT)


class TheClock(RulerCase):
    """The writer's today, and the zone of the machine that read the sentence."""

    def test_the_zone_moves_the_instant_and_never_the_day(self):
        with self.zone("UTC"):
            here = self.value("duas", "instant")
        with self.zone("BRT3"):
            there = self.value("duas", "instant")
        self.assertEqual(here, "2026-09-22T02:00:00.000Z")
        self.assertEqual(there, "2026-09-22T05:00:00.000Z")
        # The day is the writer's calendar day, and the zone does not move it —
        # a day has no zone to be read in.
        self.assertEqual(self.value("hoje", "day"), "2026-09-22")

    def test_today_is_the_day_of_the_clock_it_was_read_at(self):
        late = datetime(2026, 9, 22, 23, 59)
        early = datetime(2026, 9, 23, 0, 1)
        self.assertEqual(self.value("hoje", "day", now=late), "2026-09-22")
        self.assertEqual(self.value("amanhã", "day", now=late), "2026-09-23")
        self.assertEqual(self.value("hoje", "day", now=early), "2026-09-23")
        self.assertEqual(self.value("sexta", "day", now=early), "2026-09-25")

    def test_with_no_clock_injected_the_machine_is_the_one_read(self):
        value = self.value("hoje", "day", now=None)
        self.assertRegex(value, DAY)
        self.assertEqual(value, datetime.now().date().isoformat())


class TheLanguage(RulerCase):
    """The two grammars, and the active language choosing between them."""

    def test_both_languages_carry_the_same_readers(self):
        for code in i18n.SUPPORTED:
            module = grammar.of(code)
            for kind, reader in grammar.KINDS.items():
                with self.subTest(language=code, kind=kind):
                    self.assertTrue(callable(getattr(module, reader, None)))

    def test_a_language_without_a_grammar_reads_in_the_source_language(self):
        # The fallback is `i18n`'s own: a translation that lags must not leave a
        # sentence unreadable.
        self.assertEqual(self.value("sexta", "day", "fr_FR"), "2026-09-25")

    def test_the_named_language_and_the_active_one_agree(self):
        self.assertEqual(self.value("friday", "day", "en_US"), "2026-09-25")
        self.assertEqual(nlu.resolve("friday", "day", language="en_US", now=NOW).value,
                         "2026-09-25")


class TheRulerIsDeterministic(RulerCase):
    """No network, no model, and the same sentence read twice is the same reading."""

    SENTENCES = (
        ("sexta", "day"),
        ("dia 3", "day"),
        ("duas", "instant"),
        ("meia", "number"),
        ("friday", "day"),
        ("half past two", "instant"),
    )

    def test_the_same_sentence_gives_the_same_reading(self):
        for phrase, kind in self.SENTENCES:
            with self.subTest(phrase=phrase):
                self.assertEqual(self.read(phrase, kind), self.read(phrase, kind))

    def test_reading_a_sentence_needs_no_network(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("the ruler needs no network")
        ):
            for phrase, kind in self.SENTENCES:
                with self.subTest(phrase=phrase):
                    self.assertIsInstance(
                        self.read(phrase, kind), (nlu.Value, nlu.Residue, nlu.Question)
                    )


if __name__ == "__main__":
    unittest.main()
