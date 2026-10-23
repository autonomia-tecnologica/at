"""O terceiro eixo do Jev: a INTENÇÃO (conversa) — saudação, agradecimento,
ajuda… Tudo com um `transport` FALSO; nada toca a rede.

A intenção só vale quando ação e tabela dão `none`; abaixo do piso (0.7) é a
recusa orientadora de sempre; o cache lê a entrada antiga e a nova; e toda
chave `intent.*` existe nas duas trilhas.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import assist, boot, files, jev
from at.data import schema, store
from at.ui import ask as door

NOW = datetime(2026, 10, 23, 10, 0)
MAIN_KEY = "uma-frase-bem-longa-de-exemplo-mesmo"


def answers(action="none", table="none", intent="none", intent_confidence=0.0,
            subintent="none", confidence=0.9) -> bytes:
    def choice(value, conf):
        return {"type": "choice", "choice": value, "probabilities": {}, "confidence": conf}

    body = {
        "action": choice(action, confidence),
        "table": choice(table, confidence),
        "intent": choice(intent, intent_confidence),
        "subintent": choice(f"{intent}.{subintent}" if intent != "none" and subintent != "none"
                            else "none", intent_confidence),
    }
    return json.dumps({"answers": body}).encode("utf-8")


class IntentCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        store.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def decide(self, text, raw, language="pt_BR"):
        with mock.patch.object(assist, "_credential", return_value="k"):
            return assist.decide(text, language=language, now=NOW, main_key=MAIN_KEY,
                                 transport=lambda *a: raw)


class TheOutcome(IntentCase):
    def test_a_greeting_becomes_an_intent_with_its_message(self):
        found = self.decide("oi", answers(intent="greeting", intent_confidence=0.95,
                                          subintent="morning"))
        self.assertIsInstance(found, nlu.Intent)
        self.assertEqual((found.intent, found.subintent), ("greeting", "morning"))
        self.assertEqual(found.key, "intent.greeting.morning")
        self.assertTrue(i18n.tr(found.key).startswith("Bom dia"))

    def test_an_unknown_subintent_falls_to_plain(self):
        found = self.decide("oi", answers(intent="thanks", intent_confidence=0.9))
        self.assertEqual(found.key, "intent.thanks.plain")

    def test_an_action_wins_over_an_intent(self):
        found = self.decide("lista as tarefas",
                            answers(action="list", table="task", confidence=0.95,
                                    intent="greeting", intent_confidence=0.99))
        self.assertNotIsInstance(found, nlu.Intent)

    def test_below_the_floor_it_is_no_intent(self):
        found = self.decide("oi", answers(intent="greeting", intent_confidence=0.6))
        self.assertIsNone(found)

    def test_an_undeclared_intent_is_no_intent(self):
        found = self.decide("oi", answers(intent="banana", intent_confidence=0.99))
        self.assertIsNone(found)

    def test_below_the_floor_the_refusal_guides(self):
        with mock.patch.object(assist, "decide", return_value=None):
            with self.assertRaises(nlu.Refused) as refused:
                nlu.propose("oi", now=NOW)
        self.assertIn("listar tarefas", str(refused.exception))

    def test_the_door_answers_an_intent_not_a_refusal(self):
        intent = nlu.Intent("greeting", "plain", "intent.greeting.plain")
        with mock.patch.object(nlu, "propose", return_value=intent):
            result = door.ask("oi")
        self.assertEqual(result.kind, "intent")
        self.assertEqual(result.code, door.OK)
        self.assertEqual((result.intent, result.subintent), ("greeting", "plain"))
        self.assertTrue(result.text.startswith("Oi!"))


class TheCache(IntentCase):
    def test_the_intent_is_kept_and_served_without_the_network(self):
        raw = answers(intent="farewell", intent_confidence=0.9, subintent="plain")
        self.decide("tchau", raw)
        calls = []

        def boom(*args):
            calls.append(1)
            raise jev.JevError("sem rede")

        with mock.patch.object(assist, "_credential", return_value=None):
            found = assist.decide("tchau", language="pt_BR", now=NOW, transport=boom)
        self.assertEqual(calls, [])
        self.assertEqual(found.key, "intent.farewell.plain")

    def test_an_old_entry_without_intent_still_reads(self):
        entry = {"action": "list", "action_confidence": 0.9, "table": "task",
                 "table_confidence": 0.9, "action_span": "", "table_span": "",
                 "day_span": "none", "time_span": "none"}
        files.atomic_write_text(assist.cache_file(),
                                json.dumps({assist._key("lista as tarefas", "pt_BR"): entry}))
        guess = assist._cached(assist._key("lista as tarefas", "pt_BR"))
        self.assertEqual((guess.intent, guess.intent_confidence, guess.subintent),
                         ("none", 0.0, "none"))
        self.assertEqual(guess.action, "list")


class TheActs(IntentCase):
    """A intenção `act`: objeto.ação, com a fala humana de `intent.act.*`."""

    MAIN = ("task", "project", "note", "reminder")
    ACTIONS = ("list", "view", "create", "edit", "cancel", "delete")

    def test_every_main_combination_has_its_own_message_in_both_tracks(self):
        for language in i18n.SUPPORTED:
            for table in self.MAIN:
                for action in self.ACTIONS + ("list.empty",):
                    key = f"intent.act.{table}.{action}"
                    self.assertNotEqual(i18n.text(key, language), key, (language, key))
                    if "." not in action:
                        desc = f"intent.desc.act.{table}.{action}"
                        self.assertNotEqual(i18n.text(desc, language), desc, (language, desc))
            for action in self.ACTIONS + ("list.empty",):
                key = f"intent.act.{action}"
                self.assertNotEqual(i18n.text(key, language), key, (language, key))

    def test_act_is_never_an_option_of_the_intent_question(self):
        for language in i18n.SUPPORTED:
            self.assertNotIn(jev.ACT, jev.intents(language))
            self.assertNotIn(jev.ACT, jev.intent_criteria(language))
            self.assertFalse([k for k in jev.subintent_criteria(language) if k.startswith("act.")])

    def test_listing_answers_the_lead_of_list_task_and_the_act_intent(self):
        door.ask("criar tarefa comprar pão", now=NOW)
        result = door.ask("listar tarefas", now=NOW)
        self.assertEqual(result.lead, "Aqui estão as tarefas atuais.")
        self.assertEqual((result.intent, result.subintent), ("act", "task.list"))

    def test_an_empty_list_answers_the_empty_message(self):
        result = door.ask("listar projetos", now=NOW)
        self.assertEqual(result.lead, i18n.tr("intent.act.project.list.empty"))
        self.assertEqual(result.subintent, "project.list")

    def test_create_answers_the_create_message_with_the_id(self):
        result = door.ask("criar tarefa comprar pão", now=NOW)
        self.assertEqual(result.lead, i18n.tr("intent.act.task.create", id="TASK-1"))
        self.assertIn("TASK-1", result.lead)

    def test_without_its_own_message_the_action_one_answers(self):
        self.assertEqual(door.say("nothing", "view", id="X-1"),
                         i18n.tr("intent.act.view", id="X-1"))
        self.assertEqual(door.say("nothing", "list.empty"), i18n.tr("intent.act.list.empty"))


class TheCatalogue(unittest.TestCase):
    def test_every_intent_has_a_message_and_a_description_in_both_tracks(self):
        for language in i18n.SUPPORTED:
            intents = jev.intents(language)
            self.assertEqual(
                set(intents),
                {"greeting", "thanks", "farewell", "help", "complaint", "out_of_scope"},
            )
            for name in intents:
                subs = jev.subintents(name, language)
                self.assertIn(assist.PLAIN, subs)
                for sub in subs:
                    key = f"intent.{name}.{sub}"
                    self.assertNotEqual(i18n.text(key, language), key, (language, key))

    def test_the_two_tracks_declare_the_same_keys(self):
        self.assertEqual(i18n.keys_out_of_step().get("intent"), None)
        self.assertEqual(jev.subintent_criteria("pt_BR").keys(),
                         jev.subintent_criteria("en_US").keys())

    def test_the_criteria_carry_the_none_option(self):
        self.assertIn(jev.NONE, jev.intent_criteria("pt_BR"))
        self.assertIn("greeting.morning", jev.subintent_criteria("pt_BR"))

    def test_jev_reads_an_answer_with_no_intent_questions(self):
        raw = json.dumps({"answers": {
            "action": {"choice": "list", "confidence": 0.9},
            "table": {"choice": "task", "confidence": 0.9}}}).encode()
        read = jev._read(raw)
        self.assertEqual((read.intent, read.subintent), ("none", "none"))


if __name__ == "__main__":
    unittest.main()
