"""O Jev escolhe os TRECHOS: a gíria da ação não vira `text`.

O Jev decide a ação e a tabela (o canônico) e aponta ONDE, na frase, elas
estão escritas (o trecho). O código gasta os trechos apontados antes de ler os
argumentos — que é o que impede `joga` de virar o `text` da tarefa. E quando o
matcher determinístico lê a PRÓPRIA frase e concorda com o Jev, a leitura é a
dele: não é palpite, não pede confirmação, e a frase canônica que o "Confirmar"
reenvia fecha em vez de re-perguntar ao Jev para sempre.
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

from at import i18n
from at.core import assist, boot, jev, secrets
from at.data import schema, store
from at.nlu.reading import Question
from at.nlu.proposal import Proposal

MAIN_KEY = "uma-frase-bem-longa"
NOW = datetime(2026, 10, 3, 9, 0)


class SpanCase(unittest.TestCase):
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
        secrets.seal("jev", jev.SERVICE, "a-chave-do-jev", MAIN_KEY)

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def answer(self, action: str, table: str, action_span: str = jev.NONE,
               table_span: str = jev.NONE, confidence: float = 0.99):
        def post(url, body, headers, timeout):
            return json.dumps({"answers": {
                "action": {"choice": action, "confidence": confidence},
                "table": {"choice": table, "confidence": confidence},
                "action_span": {"choice": action_span, "confidence": confidence},
                "table_span": {"choice": table_span, "confidence": confidence},
            }}).encode("utf-8")
        return post

    def read(self, text: str, action: str, table: str,
             action_span: str = jev.NONE, table_span: str = jev.NONE):
        return assist.decide(
            text, language="pt_BR", now=NOW, main_key=MAIN_KEY,
            transport=self.answer(action, table, action_span, table_span),
        )


class TheAgreement(SpanCase):
    def test_a_readable_sentence_the_matcher_agrees_with_is_a_proposal(self):
        # Nada de confirmação para uma frase que o matcher já lê — o Jev
        # concordando não é palpite.
        found = self.read("lista as tarefas", "list", "task", "lista", "tarefas")
        self.assertIsInstance(found, Proposal)
        self.assertEqual((found.action, found.table), ("list", "task"))

    def test_the_spans_are_stored_with_the_decision(self):
        self.read("joga as pendencia", "list", "task", "joga", "pendencia")
        guess = assist._cached(assist._key("joga as pendencia", "pt_BR"))
        self.assertEqual((guess.action_span, guess.table_span), ("joga", "pendencia"))


class TheSlang(SpanCase):
    def test_it_confirms_with_a_canonical_sentence_and_not_the_slang(self):
        found = self.read("joga as pendencia", "list", "task", "joga", "pendencia")
        self.assertIsInstance(found, Question)
        self.assertEqual(found.key, assist.ASK_KEY)
        self.assertNotIn("joga", found.text)
        self.assertNotIn("pendencia", found.text)

    def test_the_canonical_sentence_reads_on_its_own_and_does_not_loop(self):
        # O que o "Confirmar" reenvia: a frase canônica. Ela NÃO pode voltar a
        # ser uma pergunta, senão confirmar nunca fecha.
        found = self.read("listar tarefa as", "list", "task")
        self.assertIsInstance(found, Proposal)

    def test_the_slang_action_does_not_leak_into_the_text(self):
        # `bota` é a ação em gíria; ela não pode virar o `text` da tarefa nova.
        found = self.read("bota uma penca", "create", "task", "bota", "penca")
        if isinstance(found, Proposal):
            self.assertNotIn("bota", found.values.get("text", ""))
        else:
            self.assertNotIn("bota", found.text)


if __name__ == "__main__":
    unittest.main()
