"""The vocabulary and the mechanical tolerance — the data, and the algorithm.

Two halves of one subject, and they are checked as two. The DATA is the packed
pairs: both languages side by side, every canonical a name that exists somewhere
else in the product, and the first list covering the tables, their fields and
their closed vocabularies. The ALGORITHM is what forgives how a word was written:
case, accents, a plural, a typo — and the tie, which it does not forgive, because
a word that names two things names none.

Every canonical is checked against what the product declares, and the failure
names the one that does not: a vocabulary pointing at a word nobody declared is
the defect this file exists to catch by name.
"""

from __future__ import annotations

import json
import os
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import tables
from at.data import schema
from at.nlu import normalizer, vocabulary

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "at-cli.spec"


def universe() -> set[str]:
    """Every name a canonical may be: the actions, and the bundled declarations.

    The action words are the engine's (`tables.ACTIONS`); item 11 moves them into
    the permission catalogue, and this door moves with them. The rest come from
    the declarations the product ships: a table's id, a field's name, and every
    value of a closed vocabulary.
    """
    names: set[str] = set(tables.ACTIONS)
    for declared in schema.bundled().values():
        names.add(str(declared.get("id")))
        fields = declared.get("fields")
        if not isinstance(fields, dict):
            continue
        for name, field in fields.items():
            names.add(name)
            closed = field.get("enum") if isinstance(field, dict) else None
            if isinstance(closed, dict):
                names |= set(closed)
    return names


def entries() -> list[tuple[str, str, str]]:
    """Every pair as the files write it: language, expression, canonical.

    Read from the files and not from the merged map, because a duplicate is what
    this reads for — and a dict keeps the last one in silence.
    """
    found: list[tuple[str, str, str]] = []
    for block in vocabulary.files():
        data = json.loads(block.read_text(encoding="utf-8"))
        for language, section in data.items():
            for expression, canonical in (section.get("expressions") or {}).items():
                found.append((language, expression, canonical))
    return found


class ThePairs(unittest.TestCase):
    """The data: what it names, and that the two languages name the same thing."""

    def test_every_canonical_is_a_name_the_product_declares(self):
        declared = universe()
        for language, expression, canonical in entries():
            with self.subTest(language=language, expression=expression):
                self.assertIn(
                    canonical,
                    declared,
                    f"the vocabulary names {canonical!r} for {expression!r}, and no "
                    f"table, field, closed value or action of the product has that "
                    f"name — item 15, slice 5",
                )

    def test_an_expression_never_names_two_canonicals(self):
        # Two files may name the same word (`projeto` is the table and the
        # field), and then they must agree: a word with two meanings is grammar's
        # business, not data's.
        seen: dict[tuple[str, str], set[str]] = {}
        for language, expression, canonical in entries():
            seen.setdefault((language, normalizer.fold(expression)), set()).add(canonical)
        ambiguous = {
            f"{language}:{expression}": sorted(found)
            for (language, expression), found in seen.items()
            if len(found) > 1
        }
        self.assertEqual(ambiguous, {})

    def test_the_two_languages_name_the_same_canonicals(self):
        # A translation that lags is a defect, not a state — the same gate the
        # i18n blocks answer to.
        named: dict[str, set[str]] = {language: set() for language in i18n.SUPPORTED}
        for language, _, canonical in entries():
            named[language].add(canonical)
        for language in i18n.SUPPORTED:
            other = next(code for code in i18n.SUPPORTED if code != language)
            with self.subTest(language=language):
                self.assertEqual(
                    sorted(named[language] - named[other]),
                    [],
                    f"{language} names canonicals {other} does not",
                )

    def test_every_language_says_where_its_words_belong(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                self.assertTrue(vocabulary.locality(language))

    def test_the_payload_travels_in_the_wheel_and_in_the_binary(self):
        # A payload no import graph sees: left out, the whole vocabulary is
        # missing and the interpreter names nothing — in silence.
        with SPEC.open(encoding="utf-8") as handle:
            spec = handle.read()
        self.assertIn('"at/i18n/vocabulary"', spec)
        with (ROOT / "pyproject.toml").open("rb") as handle:
            packed = tomllib.load(handle)["tool"]["setuptools"]["package-data"]
        self.assertIn("vocabulary/*.json", packed["at.i18n"])


class TheFirstList(unittest.TestCase):
    """What the first list claims to cover: the product's own declarations."""

    def test_it_covers_every_table_its_fields_and_its_closed_values(self):
        covered: dict[str, set[str]] = {}
        for language in i18n.SUPPORTED:
            covered[language] = set(vocabulary.of(language).values())
        for name in sorted(universe() - set(tables.ACTIONS)):
            for language in i18n.SUPPORTED:
                with self.subTest(language=language, name=name):
                    self.assertIn(
                        name,
                        covered[language],
                        f"no expression of {language} names {name!r}; the first list "
                        f"covers the tables, their fields and their closed values",
                    )


class TheParticles(unittest.TestCase):
    """The block that names nothing: the words that only connect.

    It is a block of the same directory and not a shape of the same kind, and
    the difference is the whole reason these tests exist: a particle carries no
    meaning, so there is no canonical for it to name — and the gates above, which
    read `expressions` and ask every canonical to be a name the product declares,
    walk past it untouched.
    """

    def test_both_languages_carry_particles(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                self.assertTrue(vocabulary.particles(language))

    def test_the_particles_are_written_under_a_key_of_their_own(self):
        blocks = {
            block.name: json.loads(block.read_text(encoding="utf-8"))
            for block in vocabulary.files()
        }
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                self.assertIn("particles", blocks["particle.json"][language])
                self.assertNotIn("expressions", blocks["particle.json"][language])

    def test_a_particle_is_never_also_an_expression(self):
        # A word cannot carry a meaning and carry none at once: the segmentation
        # would spend it as one of the two, in silence.
        for language in i18n.SUPPORTED:
            spoken = {normalizer.fold(word) for word in vocabulary.of(language)}
            for particle in vocabulary.particles(language):
                with self.subTest(language=language, particle=particle):
                    self.assertNotIn(normalizer.fold(particle), spoken)


class TheTolerance(unittest.TestCase):
    """The mechanical tolerance: the same word, however it was written."""

    def test_case_accent_and_typo_arrive_at_the_same_canonical(self):
        for written in ("criar", "cria", "CRIAR", "crIar", "criarr"):
            with self.subTest(written=written):
                self.assertEqual(nlu.canonical(written, "pt_BR"), "create")

    def test_a_plural_is_the_same_word(self):
        for written, language, expected in (
            ("tarefas", "pt_BR", "task"),
            ("prazos", "pt_BR", "deadline"),
            ("alterações", "pt_BR", "modifications"),
            ("horários", "pt_BR", "at"),
            ("tasks", "en_US", "task"),
            ("weekdays", "en_US", "on_weekday"),
            ("changes", "en_US", "modifications"),
        ):
            with self.subTest(written=written):
                self.assertEqual(nlu.canonical(written, language), expected)

    def test_an_accent_left_out_is_the_same_word(self):
        for written in ("situacao", "situação", "SITUACAO"):
            with self.subTest(written=written):
                self.assertEqual(nlu.canonical(written, "pt_BR"), "status")
        self.assertEqual(nlu.canonical("canceled", "en_US"), "cancelled")

    def test_a_word_that_is_two_words_is_still_the_word(self):
        for written in ("em andamento", "EM  ANDAMENTO", "em-andamento"):
            with self.subTest(written=written):
                self.assertEqual(nlu.canonical(written, "pt_BR"), "doing")
        self.assertEqual(nlu.canonical("due date", "en_US"), "deadline")

    def test_the_active_language_is_the_one_that_names(self):
        with mock.patch.dict(os.environ, {"AT_LANG": "pt_BR"}):
            i18n.reset()
            self.assertEqual(nlu.canonical("tarefa"), "task")
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(nlu.canonical("task"), "task")
        i18n.reset()


class TheResidue(unittest.TestCase):
    """What it does not know, it does not name — and it never guesses."""

    def test_a_word_the_product_does_not_know_names_nothing(self):
        for written in ("banana", "xyz", "", "   ", "42"):
            with self.subTest(written=written):
                self.assertIsNone(nlu.canonical(written, "pt_BR"))

    def test_a_word_of_the_other_language_names_nothing_here(self):
        self.assertIsNone(nlu.canonical("task", "pt_BR"))
        self.assertIsNone(nlu.canonical("tarefa", "en_US"))
        self.assertIsNone(nlu.canonical("deadline", "pt_BR"))
        self.assertIsNone(nlu.canonical("prazo", "en_US"))

    def test_a_short_word_is_not_forgiven_a_letter(self):
        # `vrr` is one letter from `ver` and `idz` is one from `id`, and a word
        # that short is not forgiven a letter: at that size the typo IS another
        # word, and the floor is what keeps the tolerance from inventing one.
        self.assertEqual(nlu.canonical("ver", "pt_BR"), "view")
        self.assertIsNone(nlu.canonical("vrr", "pt_BR"))
        self.assertIsNone(nlu.canonical("idz", "pt_BR"))

    def test_a_word_it_does_not_know_names_nothing_even_one_letter_off(self):
        # `fechadura` is a word of the language and not one of the product's,
        # and it is five letters from the nearest expression — past the one
        # letter the tolerance forgives, and it stays a residue. `fecharr`, on
        # the other hand, is one letter from `fechar` now that the vocabulary
        # carries the verb: the tolerance is mechanical, and it reads it.
        self.assertIsNone(nlu.canonical("fechadura", "pt_BR"))
        self.assertEqual(nlu.canonical("fecharr", "pt_BR"), "cancel")


class TheTie(unittest.TestCase):
    """Two candidates at the same distance: the rule is neither of them.

    The dictionary is this case's own, because the tie is a property of the rule
    and not of the words the product happens to ship — the same way the type
    tests prove the engine reads a declared type and not a list of names.
    """

    def test_the_nearer_word_wins_when_it_is_alone(self):
        self.assertEqual(
            normalizer.nearest("trazo", {"prazo": "deadline", "quadro": "board"}),
            "deadline",
        )

    def test_a_tie_names_nothing(self):
        self.assertIsNone(
            normalizer.nearest("trazo", {"prazo": "deadline", "brazo": "arm"})
        )

    def test_a_tie_between_two_words_that_name_one_thing_is_still_one_thing(self):
        self.assertEqual(
            normalizer.nearest("baixx", {"baixa": "low", "baixo": "low"}), "low"
        )

    def test_a_word_too_far_from_everything_names_nothing(self):
        self.assertIsNone(
            normalizer.nearest("quadro", {"prazo": "deadline", "baixa": "low"})
        )


if __name__ == "__main__":
    unittest.main()
