"""The matcher, the proposal and the door (§9): the sentence becomes one action.

Three things are ruled here, and they are the slice's three halves. The MATCHER:
what a sentence becomes — the action, the table, the values, the residue — and
the refusal when the sentence is outside the catalogue. The DOOR: `ask`, with
`pedir` answering to it, running the proposal through the ENGINE and answering
with the words the engine would have used, never with a second sentence this
layer invented for the same thing. And the SWITCH: turning the interpreter off
takes the word out of the tree and the function out of the core API, and takes
nothing else.

The clock is injected into the matcher, as it is in `test_nlu`, so the same
sentence read twice is the same proposal. The `cli`'s door reads the machine's
clock — that is the clock of whoever is typing — and the tests that go through it
say `hoje`, the one day a test can know without owning the calendar.

Nothing here needs a network or a model.
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import boot, paths, settings, tables
from at.data import schema, store
from at.i18n import tr
from at.ui.cli import main, tree

# The clock every sentence hangs from: a Tuesday at ten in the morning, in the
# zone the ruler pins — the same one `test_nlu` reads in.
NOW = datetime(2026, 9, 22, 10, 0)
ZONE = "BRT3"

DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class MatcherCase(unittest.TestCase):
    """A Working Folder of the instance's own, in the language the test speaks."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR", "TZ": ZONE},
        )
        self.env.start()
        time.tzset()
        i18n.reset()
        schema.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        time.tzset()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def propose(self, sentence: str, language: str = "pt_BR"):
        """What the sentence proposes, read at the ruler's own clock."""
        with mock.patch.dict(os.environ, {"AT_LANG": language}):
            i18n.reset()
            return nlu.propose(sentence, language=language, now=NOW)

    def declares(self, table: str, fields: dict) -> None:
        """A table of the instance's own, written where the declarations live."""
        where = paths.data_dir() / schema.SCHEMA_DIR / f"{table}.json"
        where.write_text(
            json.dumps(
                {
                    "id": table,
                    "order": 90,
                    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
                    "store": f"data/{table}s.jsonl",
                    "primary": "text",
                    "columns": ["text"],
                    "fields": fields,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        schema.reset()


class TheProposal(MatcherCase):
    """What the sentence becomes: one action, one table, and what it sets."""

    def test_the_named_sentence_becomes_one_proposal(self):
        proposal = self.propose("cria uma tarefa pra sexta")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual(proposal.action, "create")
        self.assertEqual(proposal.table, "task")
        self.assertEqual(proposal.values, {"deadline": "2026-09-25"})

    def test_the_matcher_proposes_and_does_not_write(self):
        # The interpreter proposes; the core validates and writes. Nothing this
        # side of the door leaves a row behind.
        self.propose("cria uma tarefa pra sexta")
        self.assertEqual(store.load("task"), [])

    def test_the_same_sentence_reads_the_same_in_both_languages(self):
        self.assertEqual(
            self.propose("create a task for friday", "en_US").values,
            {"deadline": "2026-09-25"},
        )
        self.assertEqual(
            self.propose("cria uma tarefa pra sexta").values,
            {"deadline": "2026-09-25"},
        )

    def test_the_connecting_words_do_not_become_the_title(self):
        # `uma` and `pra` carry nothing: if the particle block did not exist they
        # would be residue, and the residue fills the field the table declares as
        # `primary` — a task called `uma pra`.
        proposal = self.propose("cria uma tarefa pra sexta")
        self.assertNotIn("text", proposal.values)

    def test_the_residue_fills_the_field_the_table_declares_as_primary(self):
        proposal = self.propose("cria uma tarefa comprar pão pra sexta")
        self.assertEqual(proposal.values["text"], "Comprar pão")
        self.assertEqual(proposal.values["deadline"], "2026-09-25")

    def test_the_widest_expression_the_vocabulary_knows_wins(self):
        # `em andamento` is one value, and never `em` and a word about progress:
        # it is the longest window that is spent, not the shortest.
        proposal = self.propose("cria uma tarefa em andamento")
        self.assertEqual(proposal.values, {"status": "doing"})

    def test_a_closed_value_fills_the_field_that_carries_it(self):
        proposal = self.propose("cria uma tarefa com prioridade alta")
        self.assertEqual(proposal.values, {"priority": "high"})

    def test_a_field_word_names_where_the_value_goes(self):
        # The day goes to the field the sentence names — and not to the one the
        # declaration leaves open, which is where a day said alone would land.
        self.assertEqual(
            self.propose("cria uma tarefa desde sexta").values,
            {"since": "2026-09-25"},
        )
        self.assertEqual(
            self.propose("cria uma tarefa com prazo sexta").values,
            {"deadline": "2026-09-25"},
        )


class TheWhen(MatcherCase):
    """O quando escrito junto do título — a data e a hora, não o texto."""

    def test_a_date_inside_the_title_leaves_the_title_alone(self):
        # "comprar pão amanhã" é o título e a data; o título não carrega o
        # "amanhã", e a data é a que a pessoa disse.
        self.assertEqual(
            self.propose("cria uma tarefa comprar pão amanhã").values,
            {"deadline": "2026-09-23", "text": "Comprar pão"},
        )

    def test_the_composed_day_phrase_arrives_whole(self):
        for sentence, expected in (
            ("cria uma tarefa comprar pão depois de amanhã", "2026-09-24"),
            ("cria uma tarefa comprar pão daqui a 3 dias", "2026-09-25"),
            ("cria uma tarefa comprar pão em duas semanas", "2026-10-06"),
            ("cria uma tarefa comprar pão hoje de manhã", "2026-09-22"),
            ("cria uma tarefa comprar pão amanhã à tarde", "2026-09-23"),
        ):
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence)
                self.assertEqual(proposal.values["deadline"], expected)
                self.assertEqual(proposal.values["text"], "Comprar pão")

    def test_english_reads_its_own_counted_days(self):
        for sentence, expected in (
            ("create a task buy bread in 3 days", "2026-09-25"),
            ("create a task buy bread day after tomorrow", "2026-09-24"),
            ("create a task buy bread next week", "2026-10-05"),
        ):
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence, "en_US")
                self.assertEqual(proposal.values["deadline"], expected)
                self.assertEqual(proposal.values["text"], "Buy bread")

    def test_an_hour_named_in_the_text_leaves_it(self):
        # A tarefa não declara hora e o quando não é o título: as 18h saem do
        # texto, e o que fica é o que a pessoa vai fazer.
        proposal = self.propose("cria uma tarefa comprar pão às 18h")
        self.assertEqual(proposal.values, {"text": "Comprar pão"})

    def test_a_count_in_the_title_is_not_an_hour(self):
        # `2 pães` e `item 5` são contingência do título: só a marca de relógio
        # (`18h`, `18:30`, `meio-dia`, o `às` antes do número) faz de um número
        # uma hora.
        for sentence, expected in (
            ("cria uma tarefa comprar 2 pães", "Comprar 2 pães"),
            ("cria uma tarefa revisar o item 5", "Revisar o item 5"),
            ("create a task buy 2 breads", "Buy 2 breads"),
        ):
            language = "en_US" if sentence.startswith("create") else "pt_BR"
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence, language)
                self.assertEqual(proposal.values.get("text"), expected)

    def test_the_announcer_leaves_with_the_hour(self):
        # `às 18` é uma hora; o `às` sai com ela, e o título fica o título.
        self.assertEqual(
            self.propose("me lembra de imprimir passagens às 18").values,
            {"at": ["18:00"], "text": "imprimir passagens"},
        )


class TheImplied(MatcherCase):
    """O verbo que já diz o valor, e a cortesia que não é o objeto."""

    def test_a_verb_carries_the_value_and_the_action(self):
        for sentence in ("conclui a tarefa 1", "risca a tarefa 1"):
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence)
                self.assertEqual(proposal.action, "edit")
                self.assertEqual(proposal.values, {"status": "done"})
                self.assertEqual(proposal.row, 1)

    def test_an_english_verb_carries_it_the_same_way(self):
        for sentence in ("complete task 1", "check off task 1", "finish task 1"):
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence, "en_US")
                self.assertEqual(proposal.action, "edit")
                self.assertEqual(proposal.values, {"status": "done"})

    def test_a_written_action_still_wins(self):
        # `adiciona uma tarefa concluída` diz a ação e o valor; a ação escrita
        # é a que a pessoa quis, e o verbo não a troca.
        proposal = self.propose("adiciona uma tarefa concluída")
        self.assertEqual(proposal.action, "create")
        self.assertEqual(proposal.values, {"status": "done"})

    def test_a_courtesy_is_never_the_title(self):
        for sentence, expected in (
            ("quero criar uma tarefa comprar leite", "Comprar leite"),
            ("gostaria de criar uma tarefa comprar pão", "Comprar pão"),
            ("por favor cria uma tarefa comprar pão", "Comprar pão"),
            ("i want to create a task buy bread", "Buy bread"),
        ):
            language = "en_US" if sentence.startswith("i ") else "pt_BR"
            with self.subTest(sentence=sentence):
                proposal = self.propose(sentence, language)
                self.assertEqual(proposal.values.get("text"), expected)

    def test_a_hint_names_the_table_the_verb_implies(self):
        # "me lembra de X" não escreve "lembrete", e a linha é um lembrete.
        proposal = self.propose("me lembra de imprimir passagens")
        self.assertEqual(proposal.table, "reminder")
        self.assertEqual(proposal.values.get("text"), "imprimir passagens")


class TheNumberedRow(MatcherCase):
    """B-57: o número de um campo é valor, a pontuação não é do número."""

    def test_a_number_tied_to_a_field_is_its_value_never_the_row(self):
        for _ in range(3):
            tables.create("project", {"name": "Macro"})
        proposal = self.propose("editar o projeto 56: nome Comunidade LLM, pai 3")
        self.assertEqual(proposal.action, "edit")
        self.assertEqual(proposal.row, 56)
        self.assertEqual(proposal.values["name"], "Comunidade LLM")
        self.assertEqual(proposal.values["parent"], 3)

    def test_a_trailing_comma_or_colon_leaves_the_text_and_a_period_stays(self):
        tables.create("project", {"name": "Macro"})
        self.assertEqual(self.propose("editar projeto 1 nome Fase 1.").values["name"], "Fase 1.")
        self.assertEqual(self.propose("editar projeto 1 nome Fase 1:").values["name"], "Fase 1")

    def test_a_trailing_mark_is_not_part_of_the_number(self):
        for sentence in ("editar projeto 56, nome X", "editar projeto 56. nome X"):
            self.assertEqual(self.propose(sentence).row, 56)

    def test_a_field_number_alone_does_not_name_the_row(self):
        asked = self.propose("editar projeto nome X pai 3")
        self.assertEqual(asked.key, "nlu.ask.no_row")

    def test_a_row_that_does_not_exist_is_still_a_refusal(self):
        from at.ui import ask as door
        result = door.ask("editar o projeto 56: nome X")
        self.assertNotEqual(result.kind, "question")
        self.assertIn("56", result.text)
        self.assertEqual(store.load("project"), [])

    def test_two_loose_numbers_come_back_as_a_question(self):
        asked = self.propose("editar 56 projeto 7 nome X")
        self.assertIsInstance(asked, nlu.Question)
        self.assertEqual(asked.key, "nlu.ask.which_number")


class TheRefusal(MatcherCase):
    """A sentence the catalogue does not reach is refused by name."""

    def test_a_sentence_with_no_action_is_refused_by_name(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("banana")
        self.assertEqual(refused.exception.key, "nlu.error.no_action")
        self.assertIn("banana", str(refused.exception))

    def test_a_sentence_with_an_action_and_no_table_is_refused_by_name(self):
        # "sexta" is residue, but it reads as a DAY with nowhere to land — the
        # same incompleteness a bare "cria" has, and not a guess at an
        # object's name (`no_such_table` is the OTHER test, below).
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("cria pra sexta")
        self.assertEqual(refused.exception.key, "nlu.error.no_table_bare")
        self.assertIn(tables.table_name("task"), str(refused.exception))

    def test_a_sentence_naming_an_unknown_object_points_at_the_word(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("lista teste")
        self.assertEqual(refused.exception.key, "nlu.error.no_such_table")
        self.assertIn("teste", str(refused.exception))

    def test_two_actions_are_refused_and_not_disambiguated(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("cria e lista uma tarefa")
        self.assertEqual(refused.exception.key, "nlu.error.two_actions")

    def test_two_tables_are_refused_the_same_way(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("cria uma tarefa num projeto")
        self.assertEqual(refused.exception.key, "nlu.error.two_tables")

    def test_an_action_that_acts_on_a_row_needs_the_row(self):
        asked = self.propose("edita a tarefa pra amanhã")
        self.assertIsInstance(asked, nlu.Question)
        self.assertEqual(asked.key, "nlu.ask.no_row")

    def test_the_refusal_speaks_the_active_language(self):
        with self.assertRaises(nlu.Refused) as refused:
            self.propose("banana")
        self.assertTrue(str(refused.exception).startswith('Não entendi o que fazer com "banana".'))
        self.assertIn("listar tarefas", str(refused.exception))
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            with self.assertRaises(nlu.Refused) as refused:
                nlu.propose("banana", language="en_US", now=NOW)
        self.assertTrue(str(refused.exception).startswith('I did not understand what to do with "banana".'))
        self.assertIn("list tasks", str(refused.exception))

    def test_every_new_key_is_in_the_catalogue_of_both_languages(self):
        # A key with no text is a raw key on the screen, which is exactly what a
        # refusal must never be.
        for key in (
            "nlu.error.no_action",
            "nlu.error.no_table",
            "nlu.error.two_actions",
            "nlu.error.two_tables",
            "nlu.ask.no_row",
            "nlu.error.interpreter_off",
            "nlu.ask.which_field",
            "nlu.ask.what",
            "nlu.proposal",
        ):
            for language in i18n.SUPPORTED:
                with self.subTest(key=key, language=language):
                    self.assertNotEqual(i18n.text(key, language), key)


class TheQuestion(MatcherCase):
    """A sentence the reading does not settle comes back as a question."""

    def test_a_day_with_no_field_to_land_in_comes_back_as_a_question(self):
        # A `project` declares no day the declaration leaves open — its only day
        # is `since`, which is born with `today`. So a day said alone has nowhere
        # to go, and the sentence asks instead of picking a field.
        question = self.propose("cria um projeto pra sexta")
        self.assertIsInstance(question, nlu.Question)
        self.assertEqual(question.key, "nlu.ask.which_field")
        self.assertEqual(question.text, "sexta")

    def test_the_grammar_s_own_question_reaches_the_door(self):
        # The type the FIELD declares is what decides what a word means: `meia`
        # in a number field is half, and in an instant field it is half of an
        # hour nobody named — so it is asked back, and no row is proposed.
        self.declares(
            "moment",
            {
                "id": {"label": "table.field.id"},
                "text": {"label": "table.task.field.text"},
                "when": {"label": "table.task.field.deadline", "type": "instant"},
            },
        )
        question = self.propose("cria um moment com when meia")
        self.assertIsInstance(question, nlu.Question)
        self.assertEqual(question.key, "nlu.ask.which_hour")

    def test_a_question_writes_nothing(self):
        self.propose("cria um projeto pra sexta")
        self.assertEqual(store.load("project"), [])

    def test_a_create_that_names_no_title_asks_what_the_title_is(self):
        # `cria uma tarefa` names the table and the action and nothing else. An
        # empty row is not a row: the field the person still has to write is the
        # table's PRIMARY, and the sentence comes back as the question for it.
        question = self.propose("cria uma tarefa")
        self.assertIsInstance(question, nlu.Question)
        self.assertEqual(question.key, "nlu.ask.what")
        self.assertEqual(question.text, tables.label("task", "text"))


class TheCreateFamily(MatcherCase):
    """`criar tarefa ... em projeto X` e `escrever nota ...`: a família de
    verbos de criar vale para qualquer objeto, e o projeto se acha pelo nome."""

    def setUp(self):
        super().setUp()
        tables.create("project", {"name": "TR4"})
        tables.create("project", {"name": "TR4 antigo"})
        tables.create("project", {"name": "Casa"})

    def test_create_a_task_in_a_project_by_folded_name(self):
        proposal = self.propose("criar tarefa limpar carro em projeto tr4")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual((proposal.action, proposal.table), ("create", "task"))
        self.assertEqual(proposal.values, {"project": 1, "text": "Limpar carro"})

    def test_the_same_sentence_in_english(self):
        proposal = self.propose("create task clean car in project tr4", "en_US")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual((proposal.action, proposal.table), ("create", "task"))
        self.assertEqual(proposal.values, {"project": 1, "text": "Clean car"})

    def test_a_folded_accent_and_case_still_resolve(self):
        proposal = self.propose("criar tarefa x em projeto CASÁ".replace("Á", "A"))
        self.assertEqual(proposal.values["project"], 3)

    def test_write_a_note_keeps_the_particle_inside_the_text(self):
        proposal = self.propose("escrever nota nao falar com fulano")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual((proposal.action, proposal.table), ("create", "note"))
        self.assertEqual(proposal.values, {"text": "Nao falar com fulano"})

    def test_write_a_note_in_english(self):
        proposal = self.propose("write note do not talk to john", "en_US")
        self.assertEqual((proposal.action, proposal.table), ("create", "note"))
        self.assertEqual(proposal.values, {"text": "Do not talk to john"})

    def test_every_verb_of_the_family_creates_any_object(self):
        for verb in ("criar", "nova", "novo", "adicionar", "escrever", "anotar"):
            for noun in ("tarefa", "nota"):
                proposal = self.propose(f"{verb} {noun} comprar pão")
                self.assertEqual(proposal.action, "create", (verb, noun))
        for verb in ("create", "new", "add", "write"):
            proposal = self.propose(f"{verb} note buy bread", "en_US")
            self.assertEqual(proposal.action, "create", verb)

    def test_only_the_first_letter_is_raised(self):
        proposal = self.propose("criar nota falar com a TR4 sobre o iPhone")
        self.assertEqual(proposal.values["text"], "Falar com a TR4 sobre o iPhone")

    def test_a_word_one_letter_off_a_setting_stays_in_the_title(self):
        # `limpar` is one letter from `limiar`; the typo tolerance must not eat it.
        proposal = self.propose("criar tarefa limpar carro")
        self.assertEqual(proposal.values, {"text": "Limpar carro"})

    def test_a_project_that_does_not_exist_is_refused_and_lists_what_exists(self):
        with self.assertRaises(nlu.Refused) as caught:
            self.propose("criar tarefa limpar carro em projeto zzz")
        self.assertEqual(caught.exception.key, "nlu.error.no_ref")
        self.assertIn("TR4", str(caught.exception))
        self.assertEqual(store.load("task"), [])

    def test_an_ambiguous_project_comes_back_as_a_question(self):
        asked = self.propose("criar tarefa limpar carro em projeto tr")
        self.assertIsInstance(asked, nlu.Question)
        self.assertEqual(asked.key, "nlu.ask.which_ref")
        self.assertIn("TR4 antigo", asked.text)
        self.assertEqual(store.load("task"), [])

    def test_two_projects_with_the_same_name_are_ambiguous(self):
        tables.create("project", {"name": "casa"})
        asked = self.propose("criar tarefa x em projeto casa")
        self.assertIsInstance(asked, nlu.Question)

    def test_a_bare_project_sentence_still_names_one_table(self):
        proposal = self.propose("criar projeto Novo site")
        self.assertEqual((proposal.table, proposal.values), ("project", {"name": "Novo site"}))


class TheDoor(MatcherCase):
    """`at-cli ask` and `at-cli pedir`: the proposal, then the engine's own answer."""

    def run_words(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(words))
        return code, output.getvalue()

    def test_the_door_runs_the_proposal_and_answers_with_the_engine_words(self):
        code, text = self.run_words("pedir", "cria uma tarefa pra hoje")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.created", id="TASK-1"), text)
        row = store.find("task", 1)
        self.assertEqual(row["deadline"], date.today().isoformat())
        self.assertRegex(row["deadline"], DAY)

    def test_the_proposal_comes_before_the_answer(self):
        # The proposal is what a person checks; the answer is what the engine
        # did. Both, in that order, and neither instead of the other.
        _, text = self.run_words("pedir", "cria uma tarefa pra hoje")
        self.assertLess(text.index("Tarefa"), text.index(tr("table.created", id="TASK-1")))

    def test_ask_is_the_same_door_as_pedir(self):
        for number, spelling in enumerate(("ask", "pedir"), start=1):
            with self.subTest(word=spelling):
                code, text = self.run_words(spelling, "cria uma tarefa pra hoje")
                self.assertEqual(code, 0)
                self.assertIn(tr("table.created", id=f"TASK-{number}"), text)

    def test_pedir_after_ask_is_the_same_door_written_out(self):
        code, text = self.run_words("ask", "pedir", "cria uma tarefa pra hoje")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.created", id="TASK-1"), text)

    def test_the_residue_becomes_the_title_the_engine_stores(self):
        code, _ = self.run_words("ask", "cria uma tarefa comprar pão pra hoje")
        self.assertEqual(code, 0)
        self.assertEqual(store.find("task", 1)["text"], "Comprar pão")

    def test_a_sentence_outside_the_catalogue_is_refused_by_name(self):
        code, text = self.run_words("ask", "banana")
        self.assertEqual(code, 1)
        self.assertIn("banana", text)

    def test_a_question_comes_back_as_a_question(self):
        code, text = self.run_words("ask", "cria um projeto pra sexta")
        self.assertEqual(code, 1)
        self.assertIn(tr("nlu.ask.which_field", text="sexta"), text)
        self.assertEqual(store.load("project"), [])

    def test_the_engine_is_the_one_that_validates(self):
        # What the sentence proposes and the declaration refuses comes back in
        # the ENGINE's words: this surface invents no second sentence for it.
        code, text = self.run_words("ask", "cria um lembrete pra hoje")
        self.assertEqual(code, 1)
        self.assertIn(
            tr("table.error.required", field=tables.label("reminder", "text")), text
        )

    def test_a_sentence_that_lists_reaches_the_listing(self):
        # No "tabela" in the sentence: the person's own default (03/10/2026)
        # is a bullet, the row's TITLE and no id — the grid is "tabela"'s own.
        tables.create("task", {"text": "write the README"})
        code, text = self.run_words("ask", "lista as tarefas")
        self.assertEqual(code, 0)
        self.assertIn("write the README", text)

    def test_the_row_is_named_the_way_a_person_names_one(self):
        tables.create("task", {"text": "write the README"})
        code, text = self.run_words("ask", "veja a tarefa 1")
        self.assertEqual(code, 0)
        self.assertIn(tables.format_id("task", 1), text)
        code, text = self.run_words("ask", "edita a tarefa TASK-1 pra hoje")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.edited", id="TASK-1"), text)

    def test_the_door_takes_one_sentence_and_no_more(self):
        code, _ = self.run_words("ask")
        self.assertEqual(code, 2)
        code, _ = self.run_words("ask", "cria uma tarefa", "pra hoje")
        self.assertEqual(code, 2)


class TheSwitch(MatcherCase):
    """Turning the interpreter off: the word leaves the tree, and nothing else."""

    def turn(self, on: bool) -> None:
        settings.save({**settings.load(), nlu.SWITCH: on})

    def offered(self) -> set[str]:
        """Every word the help offers, read off the help itself.

        A line carries the word, what it is, and — after the `·` — the other
        spellings that reach the same door, which are words too.
        """
        found: set[str] = set()
        for line in tree.as_text().splitlines():
            if not line.startswith("  ") or not line.strip():
                continue
            head, _, tail = line.partition("·")
            found.add(head.split()[0])
            found |= set(tail.replace(",", " ").split())
        return found

    def run_words(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(words))
        return code, output.getvalue()

    def test_the_switch_is_born_on(self):
        self.assertTrue(nlu.enabled())
        self.assertIn("ask", {node.name for node in tree.roots()})
        self.assertIn("ask", self.offered())
        self.assertIn("pedir", self.offered())

    def test_turning_it_off_takes_the_word_out_of_the_tree(self):
        self.turn(False)
        self.assertNotIn("ask", {node.name for node in tree.roots()})
        self.assertNotIn("ask", self.offered())
        self.assertNotIn("pedir", tree.as_text())

    def test_turning_it_off_takes_the_word_out_of_the_dispatch(self):
        self.turn(False)
        for spelling in ("ask", "pedir"):
            with self.subTest(word=spelling):
                code, text = self.run_words(spelling, "cria uma tarefa pra hoje")
                self.assertEqual(code, 2)
                self.assertIn(spelling, text)

    def test_turning_it_off_takes_the_function_out_of_the_core_api(self):
        self.turn(False)
        with self.assertRaises(nlu.Refused) as refused:
            nlu.propose("cria uma tarefa pra hoje")
        self.assertEqual(refused.exception.key, "nlu.error.interpreter_off")

    def test_turning_it_off_takes_nothing_else(self):
        # The tables, their words and the language they answer in are not the
        # interpreter's: the switch is a subtraction, and never a different
        # behaviour for what stays.
        before = [node.name for node in tree.table_nodes()]
        self.turn(False)
        self.assertEqual([node.name for node in tree.table_nodes()], before)
        self.assertIsNotNone(schema.of("task"))
        code, text = self.run_words("task", "create", "--set", "text=uma")
        self.assertEqual(code, 0)
        self.assertIn(tr("table.created", id="TASK-1"), text)

    def test_turning_it_back_on_gives_the_word_back(self):
        self.turn(False)
        self.turn(True)
        self.assertTrue(nlu.enabled())
        self.assertIn("ask", self.offered())


if __name__ == "__main__":
    unittest.main()
