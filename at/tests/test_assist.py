"""`at.core.assist`: a leitura PRIMÁRIA — o que o Jev lê de uma frase, com o
matcher determinístico como apoio (TASK-180; invertido a pedido da pessoa,
03/10/2026 — o motor é provado com um cliente Jev FALSO, nunca um real).

Três coisas são regradas: o SWITCH, nascido ligado e separado do `nlu.SWITCH`;
o JEV PRIMEIRO, consultado para TODA frase (`nlu.propose` pergunta a ele antes
de tentar o matcher determinístico — não há mais gatilho); e os TRÊS TIERS que
o protótipo (`jev-test/slang_dispatch.py`) provou antes deste módulo existir —
uma leitura auto-aplica mais barato que uma escrita, as duas confirmam a partir
do mesmo piso, e um palpite que não nomeia nada é o mesmo que palpite nenhum.

Nada aqui toca a rede: toda chamada ao Jev passa por um `transport` injetado,
o mesmo seam que `test_jev.py` exercita sozinho.
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
from at.core import boot, assist, jev, secrets, settings, tables
from at.data import schema, store
from at.ui.cli import OK, REFUSED, USAGE, _assist, main

NOW = datetime(2026, 9, 22, 10, 0)
MAIN_KEY = "uma-frase-bem-longa-de-exemplo-mesmo"


class AssistCase(unittest.TestCase):
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


class TheSwitch(AssistCase):
    """Born on, separate from the interpreter's own."""

    def test_the_switch_is_born_on(self):
        self.assertTrue(assist.enabled())

    def test_it_is_not_the_interpreter_s_switch(self):
        self.assertNotEqual(assist.SWITCH, nlu.SWITCH)
        settings.save({**settings.load(), assist.SWITCH: False})
        self.assertTrue(nlu.enabled())
        self.assertFalse(assist.enabled())

    def test_turning_it_off_leaves_the_sentence_to_the_matcher(self):
        # O Jev deixou de ser consultado — `decide` devolve `None` e quem
        # responde (no `propose`) é o matcher determinístico.
        self.sealed()
        settings.save({**settings.load(), assist.SWITCH: False})
        result = assist.decide(
            "joga uma tarefa",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_turning_it_back_on_restores_it(self):
        self.sealed()
        settings.save({**settings.load(), assist.SWITCH: False})
        settings.save({**settings.load(), assist.SWITCH: True})
        result = assist.decide(
            "joga uma tarefa",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNotNone(result)


class TheCredential(AssistCase):
    """It lives in the Cofre, scoped to `jev.SERVICE`, and a read never raises."""

    def test_no_main_key_is_no_credential(self):
        self.sealed()
        result = assist.decide(
            "x", language="pt_BR", now=NOW, main_key=None,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_no_row_sealed_yet_is_no_credential(self):
        result = assist.decide(
            "x", language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.99, 0.99),
        )
        self.assertIsNone(result)

    def test_the_wrong_main_key_opens_nothing(self):
        self.sealed()
        result = assist.decide(
            "x", language="pt_BR", now=NOW,
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

        result = assist.decide(
            "joga uma tarefa aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY, transport=post,
        )
        # Not `None`: the credential opened and Jev answered. Whether that
        # becomes an applied `Proposal` or a `Question` asking to confirm is
        # the folder's `MODE` (`TheMode`, below) and not this test's concern.
        self.assertIsNotNone(result)

    def test_a_service_that_does_not_answer_stands_by_the_refusal(self):
        self.sealed()

        def failing(url, body, headers, timeout):
            raise jev.JevError("503")

        result = assist.decide(
            "x", language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=failing,
        )
        self.assertIsNone(result)


class TheTiers(AssistCase):
    """The prototype's own scale: reads are cheaper to auto-apply than writes.

    Read off `preview`, which answers the RAW tier — `decide`'s own tier is
    folded through the folder's `MODE` before it is acted on (`TheMode`,
    below), and this class is about the engine's scale, not the folder's
    taste.
    """

    def setUp(self):
        super().setUp()
        self.sealed()

    def tier(self, text: str, action: str, table: str, confidence: float) -> str:
        found = assist.preview(
            text, language="pt_BR", main_key=MAIN_KEY,
            transport=self.fake(action, table, confidence, confidence),
        )
        return found.tier

    def test_a_read_auto_applies_from_point_seven(self):
        self.assertEqual(self.tier("joga as pendencia", "list", "task", 0.7), assist.AUTO)

    def test_a_read_below_point_seven_confirms_down_to_point_five(self):
        self.assertEqual(self.tier("joga as pendencia", "list", "task", 0.69), assist.CONFIRM)
        self.assertEqual(self.tier("joga as pendencia", "list", "task", 0.5), assist.CONFIRM)

    def test_a_read_below_point_five_refuses(self):
        self.assertEqual(self.tier("joga as pendencia", "list", "task", 0.49), assist.REFUSE)

    def test_a_write_needs_point_nine_to_auto_apply(self):
        self.assertEqual(self.tier("bota uma penca aqui", "create", "task", 0.89), assist.CONFIRM)
        self.assertEqual(self.tier("bota uma penca aqui", "create", "task", 0.9), assist.AUTO)

    def test_a_write_below_point_five_refuses(self):
        self.assertEqual(self.tier("bota uma penca aqui", "create", "task", 0.49), assist.REFUSE)

    def test_either_half_named_none_refuses_regardless_of_confidence(self):
        self.assertEqual(self.tier("oi", jev.NONE, "task", 0.99), assist.REFUSE)
        self.assertEqual(self.tier("oi", "create", jev.NONE, 0.99), assist.REFUSE)


class TheMode(AssistCase):
    """TASK-180, fatia 3/3: the folder's OTHER choice — what `decide` does
    once Jev has answered, separate from whether it is asked at all."""

    def setUp(self):
        super().setUp()
        self.sealed()

    def decide(self, text: str, action: str, table: str, confidence: float):
        return assist.decide(
            text, language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=self.fake(action, table, confidence, confidence),
        )

    def test_the_key_is_not_the_switch(self):
        self.assertNotEqual(assist.MODE, assist.SWITCH)

    def test_cautious_is_the_default(self):
        self.assertEqual(assist.mode(), assist.CAUTIOUS)

    def test_a_strange_value_reads_as_cautious(self):
        settings.save({**settings.load(), assist.MODE: "qualquer-coisa"})
        self.assertEqual(assist.mode(), assist.CAUTIOUS)

    def test_cautious_asks_even_for_a_tier_that_would_have_auto_applied(self):
        settings.save({**settings.load(), assist.MODE: assist.CAUTIOUS})
        # 0.99 on a read clears `READ_THRESHOLD` by a wide margin, and the raw
        # tier is `AUTO` (`TheTiers` proves it) — cautious asks all the same.
        result = self.decide("joga as pendencia", "list", "task", 0.99)
        self.assertIsInstance(result, nlu.Question)

    def test_automatic_applies_even_a_tier_that_would_only_have_confirmed(self):
        settings.save({**settings.load(), assist.MODE: assist.AUTOMATIC})
        # 0.6 on a write never reaches `WRITE_THRESHOLD`, and the raw tier is
        # `CONFIRM` (`TheTiers` proves the write's own boundary) — automatic
        # applies it outright all the same.
        result = self.decide("bota uma penca aqui", "create", "task", 0.6)
        self.assertIsInstance(result, nlu.Proposal)

    def test_refuse_does_not_move_in_either_mode(self):
        for value in (assist.CAUTIOUS, assist.AUTOMATIC):
            with self.subTest(mode=value):
                settings.save({**settings.load(), assist.MODE: value})
                self.assertIsNone(self.decide("oi", jev.NONE, "task", 0.99))
                self.assertIsNone(self.decide("oi", "create", "task", 0.2))

    def test_it_is_reached_through_the_generic_setting_edit(self):
        self.assertEqual(assist.mode(), assist.CAUTIOUS)
        self.assertEqual(main(["setting", "edit", "assist_mode", "automatic"]), OK)
        self.assertEqual(assist.mode(), assist.AUTOMATIC)
        self.assertEqual(main(["setting", "edit", "assist_mode", "cautious"]), OK)
        self.assertEqual(assist.mode(), assist.CAUTIOUS)

    def test_it_is_listed_by_setting_list(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["setting", "list"])
        self.assertEqual(code, OK)
        self.assertIn("assist_mode", output.getvalue())


class TheRewrite(AssistCase):
    """Auto plants the canonical words and resubmits to the REAL matcher."""

    def setUp(self):
        super().setUp()
        self.sealed()

    def test_the_date_is_still_read_normally_after_the_rewrite(self):
        # Forced to `AUTOMATIC`: this is about what the `AUTO` tier DOES once
        # reached, and the folder's own default (`CAUTIOUS`) folds it into
        # `CONFIRM` before the rewrite ever runs (`TheMode`).
        settings.save({**settings.load(), assist.MODE: assist.AUTOMATIC})
        result = assist.decide(
            "bota uma penca pra sexta",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.95, 0.95),
        )
        self.assertIsInstance(result, nlu.Proposal)
        self.assertEqual(result.values.get("deadline"), "2026-09-25")

    def test_a_row_number_is_still_needed_before_it_can_apply(self):
        # O rewrite do Jev (`editar tarefa ...`) ainda precisa do número da
        # linha: o matcher não resolve, então `decide` devolve `None` — não
        # aplica, e quem tenta a frase ORIGINAL como apoio é o `propose`.
        settings.save({**settings.load(), assist.MODE: assist.AUTOMATIC})
        result = assist.decide(
            "resolve essa penca", language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("edit", "task", 0.95, 0.95),
        )
        self.assertIsNone(result)

    def test_a_confirm_tier_question_carries_the_rewritten_sentence(self):
        result = assist.decide(
            "bota uma penca aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.6, 0.6),
        )
        self.assertIsInstance(result, nlu.Question)
        self.assertEqual(result.key, assist.ASK_KEY)
        self.assertTrue(result.text.startswith("criar tarefa"))
        self.assertIn("bota uma penca aqui", result.text)

    def test_the_confirmed_sentence_reads_deterministically_on_its_own(self):
        question = assist.decide(
            "bota uma penca aqui",
            language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.6, 0.6),
        )
        # Repeating the question's own text is the ordinary deterministic road
        # — no Jev, no credential, no switch needed the second time.
        proposal = nlu.propose(question.text, now=NOW)
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertEqual(proposal.action, "create")
        self.assertEqual(proposal.table, "task")


class ThePropose(AssistCase):
    """`nlu.propose` pergunta ao Jev PRIMEIRO e cai no matcher quando `decide`
    devolve `None` — a inversão (03/10/2026)."""

    def test_propose_asks_jev_first_for_any_sentence(self):
        # Toda frase — inclusive uma que o matcher leria sozinho — vai ao Jev
        # primeiro. `decide` é chamado com o TEXTO (não mais uma recusa).
        sentinel = nlu.Proposal(action="create", table="task", values={}, row=None)
        with mock.patch.object(assist, "decide", return_value=sentinel) as mocked:
            self.assertIs(
                nlu.propose("lista as tarefas do projeto", now=NOW), sentinel
            )
            self.assertEqual(mocked.call_args.args, ("lista as tarefas do projeto",))
            self.assertEqual(mocked.call_args.kwargs["language"], "pt_BR")
            self.assertIsNone(mocked.call_args.kwargs["main_key"])

    def test_with_no_decision_the_matcher_answers(self):
        # `decide` devolve `None`: quem responde é o matcher determinístico,
        # como sempre respondeu — o apoio.
        with mock.patch.object(assist, "decide", return_value=None):
            found = nlu.propose("lista as tarefas", now=NOW)
        self.assertIsInstance(found, nlu.Proposal)

    def test_with_no_main_key_the_matcher_answers_as_before(self):
        # Sem chave o Jev não é consultado — nem com credencial selada e switch
        # ligado —, e uma frase que o matcher não lê segue recusada como antes.
        self.sealed()
        with self.assertRaises(nlu.Refused) as refused:
            nlu.propose("banana", now=NOW)
        self.assertEqual(refused.exception.key, "nlu.error.no_action")

    def test_the_jev_reading_is_what_propose_answers(self):
        # O ponto da inversão: com chave, o Jev é consultado ANTES do matcher e
        # a leitura dele é a resposta — aqui uma frase que o matcher sozinho
        # recusaria. O seam é `jev._post`, o mesmo que a palavra da CLI patcheia.
        self.sealed()
        settings.save({**settings.load(), assist.MODE: assist.AUTOMATIC})
        with mock.patch.object(jev, "_post", self.fake("list", "task", 0.99, 0.99)):
            found = nlu.propose("joga as pendencia", now=NOW, main_key=MAIN_KEY)
        self.assertIsInstance(found, nlu.Proposal)
        self.assertEqual(found.action, "list")
        self.assertEqual(found.table, "task")


class TheDeclaredRisk(AssistCase):
    """The act of asking Jev carries a declared risk, like any other act."""

    def test_the_permission_is_known_and_priced_like_the_generic_ask(self):
        from at.core import permissions
        self.assertTrue(permissions.is_known("assist:ask"))
        self.assertEqual(permissions.risk("assist:ask"), permissions.RISK_WRITE)


class ThePreview(AssistCase):
    """`assist.preview` — the raw guess and its tier, never applied,
    rewritten or handed to the matcher (TASK-180, fatia 2/3)."""

    def setUp(self):
        super().setUp()
        self.sealed()

    def test_it_shows_the_action_the_table_and_the_tier(self):
        found = assist.preview(
            "bota uma penca aqui", language="pt_BR", main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.95, 0.95),
        )
        self.assertEqual(found.action, "create")
        self.assertEqual(found.table, "task")
        self.assertEqual(found.action_confidence, 0.95)
        self.assertEqual(found.table_confidence, 0.95)
        self.assertEqual(found.tier, assist.AUTO)

    def test_the_tier_is_the_same_scale_decide_uses(self):
        found = assist.preview(
            "bota uma penca aqui", language="pt_BR", main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.6, 0.6),
        )
        self.assertEqual(found.tier, assist.CONFIRM)

    def test_a_guess_that_names_nothing_is_the_refuse_tier(self):
        found = assist.preview(
            "oi", language="pt_BR", main_key=MAIN_KEY,
            transport=self.fake(jev.NONE, "task", 0.99, 0.99),
        )
        self.assertEqual(found.tier, assist.REFUSE)

    def test_the_switch_off_shows_nothing(self):
        settings.save({**settings.load(), assist.SWITCH: False})
        found = assist.preview(
            "bota uma penca aqui", language="pt_BR", main_key=MAIN_KEY,
            transport=self.fake("create", "task", 0.95, 0.95),
        )
        self.assertIsNone(found)

    def test_no_main_key_shows_nothing(self):
        found = assist.preview(
            "bota uma penca aqui", language="pt_BR", main_key=None,
            transport=self.fake("create", "task", 0.95, 0.95),
        )
        self.assertIsNone(found)

    def test_a_service_that_does_not_answer_shows_nothing(self):
        def failing(url, body, headers, timeout):
            raise jev.JevError("503")

        found = assist.preview(
            "x", language="pt_BR", main_key=MAIN_KEY, transport=failing,
        )
        self.assertIsNone(found)


class TheCLIWord(AssistCase):
    """`at-cli assist ask "<frase>"` — the dry run, through the real door
    and the real `cli` dispatch."""

    def run_verb(self, args: list[str], phrase: str = MAIN_KEY, transport=None):
        """Through `_assist`, with the Main Key injected like `backup`'s own
        CLI test injects it, and the network seam patched at `jev._post` —
        the one place `decide` would otherwise reach a socket."""
        if transport is None:
            transport = self.fake("create", "task", 0.95, 0.95)
        output = io.StringIO()
        with redirect_stdout(output):
            with mock.patch.object(jev, "_post", transport):
                code = _assist(args, secret=lambda question: phrase)
        return code, output.getvalue()

    def test_it_shows_the_preview_and_writes_nothing(self):
        self.sealed()
        code, text = self.run_verb(["bota uma penca aqui"])
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("table.action.create"), text)
        self.assertIn(tables.table_name("task"), text)
        self.assertEqual(store.load("audit"), [])

    def test_the_switch_off_refuses_before_asking_for_the_phrase(self):
        self.sealed()
        settings.save({**settings.load(), assist.SWITCH: False})
        # The switch is read BEFORE the secret reader is called at all — a
        # folder with it off never gets as far as asking for the phrase.
        asked: list[str] = []
        output = io.StringIO()
        with redirect_stdout(output):
            code = _assist(
                ["bota uma penca aqui"],
                secret=lambda question: asked.append(question) or MAIN_KEY,
            )
        self.assertEqual(code, REFUSED)
        self.assertEqual(asked, [])
        self.assertIn(i18n.tr("assist.preview.off"), output.getvalue())

    def test_no_credential_answers_in_its_own_words(self):
        code, text = self.run_verb(["bota uma penca aqui"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("assist.preview.none"), text)

    def test_without_a_terminal_it_refuses_rather_than_assume(self):
        class _NoTerminal:
            def isatty(self) -> bool:
                return False

        self.sealed()
        output = io.StringIO()
        with mock.patch("sys.stdin", _NoTerminal()):
            with redirect_stdout(output):
                code = _assist(["bota uma penca aqui"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("assist.preview.no_tty"), output.getvalue())

    def test_the_wrong_shape_is_a_usage_error(self):
        code, _ = self.run_verb([])
        self.assertEqual(code, USAGE)
        code, _ = self.run_verb(["uma", "frase", "em", "pedacos"])
        self.assertEqual(code, USAGE)

    def test_the_word_is_offered_by_the_help(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["help"])
        self.assertEqual(code, OK)
        self.assertIn("assist", output.getvalue())

    def test_main_dispatches_the_word_without_a_terminal(self):
        class _NoTerminal:
            def isatty(self) -> bool:
                return False

        self.sealed()
        with mock.patch("sys.stdin", _NoTerminal()):
            self.assertEqual(main(["assist", "x"]), REFUSED)


class TheSwitchThroughSetting(AssistCase):
    """The generic `setting edit` already reaches the assist's own switch —
    proven through the real `cli`, and independent of the interpreter's."""

    def test_setting_edit_turns_it_off_and_on(self):
        self.assertTrue(assist.enabled())
        self.assertEqual(main(["setting", "edit", "assist", "false"]), OK)
        self.assertFalse(assist.enabled())
        self.assertTrue(nlu.enabled())
        self.assertEqual(main(["setting", "edit", "assist", "true"]), OK)
        self.assertTrue(assist.enabled())

    def test_it_is_listed_by_setting_list(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["setting", "list"])
        self.assertEqual(code, OK)
        self.assertIn("assist", output.getvalue())


if __name__ == "__main__":
    unittest.main()
