"""Configurar a credencial do Jev: o `secret` de escopo `jev`.

A chave do Jev é um valor que o AT USA (§4), então ela é selada na tabela
`secret`, com a Chave Principal derivando a chave do escopo. O que estes testes
prendem: sem linha o Jev não está configurado; configurar sela uma linha que a
MESMA Chave abre; reconfigurar reescreve a mesma linha (uma rotação, não duas
credenciais); e uma Chave Principal inválida é recusada, não estourada.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import assist, boot, jev, permissions, secrets
from at.data import schema, store

MAIN_KEY = "uma-frase-bem-longa"


class ConfigureCase(unittest.TestCase):
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

    def rows(self) -> list[dict]:
        return [r for r in store.load(permissions.SECRET)
                if r.get(secrets.SCOPE) == jev.SERVICE]


class TheState(ConfigureCase):
    def test_it_is_not_configured_to_start(self):
        self.assertFalse(assist.configured())

    def test_configuring_makes_it_configured(self):
        self.assertTrue(assist.configure("chave-do-jev", MAIN_KEY))
        self.assertTrue(assist.configured())


class TheSeal(ConfigureCase):
    def test_the_value_is_sealed_and_opens_with_the_same_key(self):
        assist.configure("chave-do-jev", MAIN_KEY)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("chave-do-jev", rows[0][secrets.SEALED])
        self.assertEqual(secrets.open_value(rows[0], MAIN_KEY), "chave-do-jev")

    def test_the_wrong_key_does_not_open_it(self):
        assist.configure("chave-do-jev", MAIN_KEY)
        self.assertIsNone(secrets.open_value(self.rows()[0], "outra-frase-bem-longa"))

    def test_reconfiguring_replaces_the_row_and_not_adds_one(self):
        assist.configure("primeira", MAIN_KEY)
        assist.configure("segunda", MAIN_KEY)
        rows = self.rows()
        self.assertEqual(len(rows), 1, "a pasta ficou com duas credenciais do Jev")
        self.assertEqual(secrets.open_value(rows[0], MAIN_KEY), "segunda")

    def test_a_main_key_below_the_floor_is_refused_not_raised(self):
        self.assertFalse(assist.configure("chave-do-jev", "curta"))
        self.assertFalse(assist.configured())


if __name__ == "__main__":
    unittest.main()
