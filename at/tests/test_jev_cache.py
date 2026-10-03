"""O cache das leituras do Jev: a frase repetida não volta à rede.

O Jev é um serviço de FORA, e cada leitura é uma chamada. O cache guarda o que
ele respondeu, por frase normalizada + idioma, e a repetida responde sem rede e
sem chave — a decisão já está na pasta. O que estes testes prendem: o que o Jev
respondeu fica guardado, a segunda vez não toca o transporte, a chave do cache
ignora caixa/acento/pontuação, e uma entrada que o motor não reconhece mais é
um miss (o cache não serve lixo).
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

MAIN_KEY = "uma-frase-bem-longa"
NOW = datetime(2026, 10, 3, 9, 0)


def answer(action: str, table: str, confidence: float) -> bytes:
    return json.dumps(
        {
            "answers": {
                "action": {"type": "choice", "choice": action,
                           "probabilities": {}, "confidence": confidence},
                "table": {"type": "choice", "choice": table,
                          "probabilities": {}, "confidence": confidence},
            },
        }
    ).encode("utf-8")


class CacheCase(unittest.TestCase):
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

    def sealed(self) -> dict:
        return secrets.seal("jev", jev.SERVICE, "a-chave-do-jev", MAIN_KEY)

    def transport(self, action: str = "list", table: str = "task",
                  confidence: float = 0.99, calls: list | None = None):
        def post(url, body, headers, timeout):
            if calls is not None:
                calls.append(1)
            return answer(action, table, confidence)
        return post


class TheStore(CacheCase):
    def test_what_jev_answered_is_kept(self):
        self.sealed()
        assist.decide(
            "joga as pendencia", language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=self.transport(),
        )
        key = assist._key("joga as pendencia", "pt_BR")
        guess = assist._cached(key)
        self.assertIsNotNone(guess, "a leitura do Jev não foi guardada")
        self.assertEqual((guess.action, guess.table), ("list", "task"))

    def test_two_sentences_are_two_entries(self):
        self.sealed()
        assist.decide("joga as pendencia", language="pt_BR", now=NOW,
                      main_key=MAIN_KEY, transport=self.transport())
        assist.decide("bota uma penca", language="pt_BR", now=NOW,
                      main_key=MAIN_KEY, transport=self.transport("create", "task"))
        self.assertEqual(len(assist._entries()), 2)


class TheKey(CacheCase):
    def test_case_accent_and_punctuation_do_not_matter(self):
        self.assertEqual(
            assist._key("Listar  TAREFAS, por favor!", "pt_BR"),
            assist._key("listar tarefas por favor", "pt_BR"),
        )

    def test_the_language_is_part_of_the_key(self):
        self.assertNotEqual(
            assist._key("listar tarefas", "pt_BR"),
            assist._key("listar tarefas", "en_US"),
        )


class TheHit(CacheCase):
    def test_a_repeated_sentence_needs_no_key_and_no_network(self):
        self.sealed()
        calls: list = []
        first = assist.decide(
            "joga as pendencia", language="pt_BR", now=NOW,
            main_key=MAIN_KEY, transport=self.transport(calls=calls),
        )
        self.assertEqual(len(calls), 1)

        def boom(url, body, headers, timeout):
            raise AssertionError("a frase repetida foi à rede")

        # SEM chave e com um transporte que estoura: o cache responde sozinho.
        second = assist.decide(
            "joga as pendencia", language="pt_BR", now=NOW,
            main_key=None, transport=boom,
        )
        self.assertEqual(second, first)

    def test_the_switch_off_is_a_miss_even_with_a_cache(self):
        self.sealed()
        assist.decide("joga as pendencia", language="pt_BR", now=NOW,
                      main_key=MAIN_KEY, transport=self.transport())
        from at.core import settings
        settings.save({**settings.load(), assist.SWITCH: False})
        self.assertIsNone(
            assist.decide("joga as pendencia", language="pt_BR", now=NOW,
                          main_key=None, transport=self.transport())
        )


class TheStaleEntry(CacheCase):
    def test_an_entry_the_engine_does_not_know_is_a_miss(self):
        key = assist._key("frase velha", "pt_BR")
        assist._remember(
            key, jev.Decision("nao-existe", 0.99, "nope", 0.99)
        )
        self.assertIsNone(assist._cached(key), "uma ação morta foi servida do cache")
        # E o `decide` a trata como miss: sem chave, não há credencial, e a
        # frase volta ao matcher (None).
        self.assertIsNone(
            assist.decide("frase velha", language="pt_BR", now=NOW, main_key=None)
        )


if __name__ == "__main__":
    unittest.main()
