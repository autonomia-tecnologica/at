"""`at.core.decisor`: the slang layer `nlu.propose` falls back to when the
deterministic matcher finds no action, no table, or neither (TASK-180, fatia
1/3 — the engine, proven with a FAKE Jev client and never a real one).

Three things are ruled: the SWITCH, born on and separate from `nlu.SWITCH`;
the TRIGGER, which fires on exactly the two refusals the matcher raises for a
missing action or table, and on nothing else real ambiguity or the grammar's
own question already cover; and the THREE TIERS the prototype
(`jev-test/slang_dispatch.py`) proved before this module existed — a read
auto-applies cheaper than a write, both confirm from the same floor, and a
guess that names nothing is the same as no guess at all.

Nothing here reaches a network: every call to Jev goes through an injected
`transport`, the same seam `test_jev.py` exercises on its own.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import boot, decisor, jev, secrets, settings
from at.data import schema, store

NOW = datetime(2026, 9, 22, 10, 0)
MAIN_KEY = "uma-frase-bem-longa-de-exemplo-mesmo"


class DecisorCase(unittest.TestCase):
    """A Working Folder of its own, so the Cofre and the switch are real."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def sealed(self, value: str = "a-chave-de-exemplo-do-jev") -> dict:
        return secrets.seal("jev", jev.SERVICE, value, MAIN_KEY)

    def fake(self, action: str, table: str, action_confidence: float, table_confidence: float):
        def post(url, body, headers, timeout):
            import json
            return json.dumps(
                {
                    "answers": {
                        "action": {
                            "type": "choice", "choice": action,
                            "probabilities": {}, "confidence": action_confidence,
                        },
                        "table": {
                            "type": "choice", "choice": table,
                            "probabilities": {}, "confidence": table_confidence,
                        },
                    },
                }
            ).encode("utf-8")
        return post

    def refused(self, key: str = decisor.NO_ACTION, **kw) -> nlu.Refused:
        return nlu.Refused(key, **kw)


class TheSwitch(DecisorCase):
    """Born on, separate from the interpreter's own."""

    def test_the_switch_is_born_on(self):
        self.assertTrue(decisor.enabled())

    def test_it_is_not_the_interpreter_s_switch(self):
        self.assertNotEqual(decisor.SWITCH, nlu.SWITCH)
        settings.save({**settings.load(), decisor.SWITCH: False})
        self.assertTrue(nlu.enabled())
        self.assertFalse(decisor.enabled())

    def test_turning_it_off_stands_by_the_refusal_even_with_a_credential(self):
        self.sealed()
        settings.save({**settings.load(), decisor.SWITCH: False})
        result = decisor.decide(
            self.refused(text="joga uma tarefa"), "joga uma tarefa",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_turning_it_back_on_restores_it(self):
        self.sealed()
        settings.save({**settings.load(), decisor.SWITCH: False})
        settings.save({**settings.load(), decisor.SWITCH: True})
        result = decisor.decide(
            self.refused(text="joga uma tarefa"), "joga uma tarefa",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNotNone(result)


class TheTrigger(DecisorCase):
    """Only the two refusals the matcher raises for a missing action/table."""

    def test_it_fires_on_no_action_and_no_table(self):
        self.sealed()
        for key in (decisor.NO_ACTION, decisor.NO_TABLE):
            with self.subTest(key=key):
                result = decisor.decide(
                    self.refused(key, text="x"), "x", language="pt_BR", now=NOW,
                    main_key=MAIN_KEY, transport=self.fake("create", "task", 0.99, 0.99),
                )
                self.assertIsNotNone(result)

    def test_it_never_fires_on_real_ambiguity_or_a_grammar_question(self):
        self.sealed()
        for key in ("nlu.error.two_actions", "nlu.error.two_tables", "nlu.error.no_row"):
            with self.subTest(key=key):
                result = decisor.decide(
                    self.refused(key, first="a", second="b", table="task"),
                    "x", language="pt_BR", now=NOW, main_key=MAIN_KEY,
                    transport=self.fake("create", "task", 0.99, 0.99),
                )
                self.assertIsNone(result)


class TheCredential(DecisorCase):
    """It lives in the Cofre, scoped to `jev.SERVICE`, and a read never raises."""

    def test_no_main_key_is_no_credential(self):
        self.sealed()
        result = decisor.decide(
            self.refused(text="x"), "x", language="pt_BR", now=NOW, main_key=None,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_no_row_sealed_yet_is_no_credential(self):
        result = decisor.decide(
            self.refused(text="x"), "x", language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_the_wrong_main_key_opens_nothing(self):
        self.sealed()
        result = decisor.decide(
            self.refused(text="x"), "x", language="pt_BR", now=NOW,
            main_key="outra-frase-tambem-bem-longa", transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_the_right_main_key_opens_it_and_reaches_jev(self):
        self.sealed("a-chave-real-do-jev")

        def post(url, body, headers, timeout):
            self.assertEqual(headers["Authorization"], "Bearer a-chave-real-do-jev")
            import json
            return json.dumps({
                "answers": {
                    "action": {"type": "choice", "choice": "create",
                               "probabilities": {}, "confidence": 0.95},
                    "table": {"type": "choice", "choice": "task",
                              "probabilities": {}, "confidence": 0.95},
                },
            }).encode("utf-8")

        result = decisor.decide(
            self.refused(text="joga uma tarefa aqui"), "joga uma tarefa aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY, transport=post,
        )
        self.assertIsInstance(result, nlu.Proposal)

    def test_a_service_that_does_not_answer_stands_by_the_refusal(self):
        self.sealed()

        def failing(url, body, headers, timeout):
            raise jev.JevError("503")

        result = decisor.decide(
            self.refused(text="x"), "x", language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=failing,
        )
        self.assertIsNone(result)


class TheTiers(DecisorCase):
    """The prototype's own scale: reads are cheaper to auto-apply than writes."""

    def setUp(self):
        super().setUp()
        self.sealed()

    def decide(self, text: str, action: str, table: str, confidence: float):
        return decisor.decide(
            self.refused(text=text), text, language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=self.fake(action, table, confidence, confidence),
        )

    def test_a_read_auto_applies_from_point_seven(self):
        result = self.decide("joga as pendencia", "list", "task", 0.7)
        self.assertIsInstance(result, nlu.Proposal)
        self.assertEqual(result.action, "list")
        self.assertEqual(result.table, "task")

    def test_a_read_below_point_seven_confirms_down_to_point_five(self):
        result = self.decide("joga as pendencia", "list", "task", 0.69)
        self.assertIsInstance(result, nlu.Question)
        result = self.decide("joga as pendencia", "list", "task", 0.5)
        self.assertIsInstance(result, nlu.Question)

    def test_a_read_below_point_five_refuses(self):
        self.assertIsNone(self.decide("joga as pendencia", "list", "task", 0.49))

    def test_a_write_needs_point_nine_to_auto_apply(self):
        result = self.decide("bota uma penca aqui", "create", "task", 0.89)
        self.assertIsInstance(result, nlu.Question)
        result = self.decide("bota uma penca aqui", "create", "task", 0.9)
        self.assertIsInstance(result, nlu.Proposal)

    def test_a_write_below_point_five_refuses(self):
        self.assertIsNone(self.decide("bota uma penca aqui", "create", "task", 0.49))

    def test_either_half_named_none_refuses_regardless_of_confidence(self):
        self.assertIsNone(self.decide("oi", jev.NONE, "task", 0.99))
        self.assertIsNone(self.decide("oi", "create", jev.NONE, 0.99))


class TheRewrite(DecisorCase):
    """Auto plants the canonical words and resubmits to the REAL matcher."""

    def setUp(self):
        super().setUp()
        self.sealed()

    def test_the_date_is_still_read_normally_after_the_rewrite(self):
        result = decisor.decide(
            self.refused(text="bota uma penca pra sexta"), "bota uma penca pra sexta",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.95, 0.95),
        )
        self.assertIsInstance(result, nlu.Proposal)
        self.assertEqual(result.values.get("deadline"), "2026-09-25")

    def test_a_row_number_is_still_needed_for_an_action_that_acts_on_one(self):
        with self.assertRaises(nlu.Refused) as refused:
            decisor.decide(
                self.refused(key=decisor.NO_TABLE, text="resolve essa penca"),
                "resolve essa penca", language="pt_BR", now=NOW, main_key=MAIN_KEY,
                transport=self.fake("edit", "task", 0.95, 0.95),
            )
        self.assertEqual(refused.exception.key, "nlu.error.no_row")

    def test_a_confirm_tier_question_carries_the_rewritten_sentence(self):
        result = decisor.decide(
            self.refused(text="bota uma penca aqui"), "bota uma penca aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.6, 0.6),
        )
        self.assertIsInstance(result, nlu.Question)
        self.assertEqual(result.key, decisor.ASK_KEY)
        self.assertTrue(result.text.startswith("criar tarefa"))
        self.assertIn("bota uma penca aqui", result.text)

    def test_the_confirmed_sentence_reads_deterministically_on_its_own(self):
        question = decisor.decide(
            self.refused(text="bota uma penca aqui"), "bota uma penca aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.6, 0.6),
        )
        # Repeating the question's own text is the ordinary deterministic road
        # — no Jev, no credential, no switch needed the second time.
        proposal = nlu.propose(question.text, now=NOW)
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual(proposal.action, "create")
        self.assertEqual(proposal.table, "task")


class ThePropose(DecisorCase):
    """`nlu.propose`'s own delegation — and the fact that it never fires when
    nothing wires a `main_key` in, which is exactly `cli` and the WebApp today."""

    def test_propose_delegates_to_the_decisor_for_the_two_triggers(self):
        with mock.patch.object(decisor, "decide", return_value=None) as mocked:
            with self.assertRaises(nlu.Refused):
                nlu.propose("banana", now=NOW)
            self.assertTrue(mocked.called)
            refused, text = mocked.call_args.args
            self.assertEqual(refused.key, "nlu.error.no_action")
            self.assertEqual(text, "banana")
            self.assertEqual(mocked.call_args.kwargs["language"], "pt_BR")
            self.assertIsNone(mocked.call_args.kwargs["main_key"])

    def test_propose_returns_what_the_decisor_answers(self):
        sentinel = nlu.Proposal(action="create", table="task", values={}, row=None)
        with mock.patch.object(decisor, "decide", return_value=sentinel):
            self.assertIs(nlu.propose("banana", now=NOW), sentinel)

    def test_with_no_main_key_cli_and_webapp_keep_their_old_refusal(self):
        # `at.ui.ask.ask` never passes `main_key` — this fatia does not touch it
        # — so even a sealed credential and a switch left on change nothing of
        # what `cli`/WebApp already do.
        self.sealed()
        with self.assertRaises(nlu.Refused) as refused:
            nlu.propose("banana", now=NOW)
        self.assertEqual(refused.exception.key, "nlu.error.no_action")

    def test_a_non_trigger_refusal_is_untouched_even_with_a_credential(self):
        # `decide` is reached (every `Refused` is) but answers `None` for a
        # reason that is not one of the two triggers — `TheTrigger` already
        # proves that from the decisor's own side; this is the end-to-end one.
        self.sealed()
        with self.assertRaises(nlu.Refused) as refused:
            nlu.propose("cria e lista uma tarefa", now=NOW, main_key=MAIN_KEY)
        self.assertEqual(refused.exception.key, "nlu.error.two_actions")


class TheDeclaredRisk(DecisorCase):
    """The act of asking Jev carries a declared risk, like any other act."""

    def test_the_permission_is_known_and_priced_like_the_generic_ask(self):
        from at.core import permissions
        self.assertTrue(permissions.is_known("decisor:ask"))
        self.assertEqual(permissions.risk("decisor:ask"), permissions.RISK_WRITE)


if __name__ == "__main__":
    unittest.main()
