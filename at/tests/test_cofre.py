"""O Cofre: o que entra em `Cofre/` sela sozinho (TASK-154, fatia 1/3).

Toda a suíte aqui é sem rede e sem tocar a instância — cada teste vigia uma
pasta descartável, e a chave é derivada da mesma Chave Principal de teste que o resto da
suíte usa (`vault.vault_key`), nunca uma chave de verdade de ninguém.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from at.core import cofre
from at.encryption import vault

PHRASE = "uma-frase-de-dezesseis-caracteres"


class TheSeal(unittest.TestCase):
    """`seal_file`/`open_file`: o claro vira `.enc`, com fingerprint, e volta."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.key = vault.derived_key(vault.vault_key(PHRASE), cofre.SCOPE)

    def test_a_sealed_file_carries_the_fingerprint_and_the_name_grows_enc(self):
        where = self.folder / "nota.txt"
        where.write_text("segredo de verdade", encoding="utf-8")
        sealed = cofre.seal_file(where, self.key)
        self.assertEqual(sealed, self.folder / "nota.txt.enc")
        self.assertTrue(sealed.is_file())
        self.assertFalse(where.exists())
        self.assertTrue(cofre.fingerprinted(sealed))

    def test_the_clear_value_is_in_no_byte_of_the_sealed_file(self):
        where = self.folder / "nota.txt"
        where.write_text("um segredo bem específico e comprido", encoding="utf-8")
        sealed = cofre.seal_file(where, self.key)
        self.assertNotIn(b"um segredo bem espec", sealed.read_bytes())

    def test_open_file_answers_the_clear_it_sealed(self):
        where = self.folder / "nota.txt"
        where.write_bytes(b"conteudo binario \x00\x01")
        sealed = cofre.seal_file(where, self.key)
        self.assertEqual(cofre.open_file(sealed, self.key), b"conteudo binario \x00\x01")

    def test_open_file_with_the_wrong_key_answers_none(self):
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        sealed = cofre.seal_file(where, self.key)
        other = vault.derived_key(vault.vault_key(PHRASE), "outro-escopo")
        self.assertIsNone(cofre.open_file(sealed, other))

    def test_a_plain_file_is_not_fingerprinted(self):
        where = self.folder / "nota.txt.enc"
        where.write_bytes(b"nao passou por aqui")
        self.assertFalse(cofre.fingerprinted(where))

    def test_a_missing_file_is_not_fingerprinted(self):
        self.assertFalse(cofre.fingerprinted(self.folder / "nao-existe.enc"))


class TheWatcher(unittest.TestCase):
    """`Watcher.tick`: a escrita que PAROU vira `.enc` sozinha."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.key = vault.derived_key(vault.vault_key(PHRASE), cofre.SCOPE)

    def test_a_settled_write_is_sealed_after_one_full_tick_of_quiet(self):
        watcher = cofre.Watcher(self.folder)
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        # A primeira rodada VÊ a escrita e a põe na fila — não sela ainda.
        self.assertEqual(watcher.tick(self.key), ())
        self.assertTrue(where.exists())
        # A segunda, sem mais nada mudar, é a que sela.
        settled = watcher.tick(self.key)
        self.assertEqual(settled, (self.folder / "nota.txt.enc",))
        self.assertFalse(where.exists())
        self.assertTrue(cofre.fingerprinted(settled[0]))

    def test_a_write_still_in_progress_is_not_sealed(self):
        watcher = cofre.Watcher(self.folder)
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        watcher.tick(self.key)
        # Tocado de novo antes da rodada que selaria — a espera reinicia.
        where.write_text("a bem mais comprido que antes, ainda escrevendo", encoding="utf-8")
        self.assertEqual(watcher.tick(self.key), ())
        self.assertTrue(where.exists())
        settled = watcher.tick(self.key)
        self.assertEqual(settled, (self.folder / "nota.txt.enc",))

    def test_with_no_key_the_watcher_still_scans_and_seals_nothing(self):
        watcher = cofre.Watcher(self.folder)
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        watcher.tick(None)
        self.assertEqual(watcher.tick(None), ())
        self.assertTrue(where.exists())
        # Uma chave que chega DEPOIS ainda sela o que ficou parado — nada foi
        # perdido por não ter chave nas rodadas de antes.
        self.assertEqual(watcher.tick(self.key), (self.folder / "nota.txt.enc",))

    def test_an_already_sealed_file_is_never_resealed(self):
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        sealed = cofre.seal_file(where, self.key)
        before = sealed.read_bytes()
        watcher = cofre.Watcher(self.folder)
        watcher.tick(self.key)
        watcher.tick(self.key)
        self.assertEqual(sealed.read_bytes(), before)

    def test_a_file_dropped_before_the_watcher_was_born_still_seals(self):
        # `_seed`: largar o arquivo e só depois subir o WebApp não pode deixar
        # o arquivo esquecido para sempre.
        where = self.folder / "ja-estava.txt"
        where.write_text("a", encoding="utf-8")
        watcher = cofre.Watcher(self.folder)
        settled = watcher.tick(self.key)
        self.assertEqual(settled, (self.folder / "ja-estava.txt.enc",))

    def test_a_file_removed_before_it_settles_is_dropped_quietly(self):
        watcher = cofre.Watcher(self.folder)
        where = self.folder / "nota.txt"
        where.write_text("a", encoding="utf-8")
        watcher.tick(self.key)
        where.unlink()
        # Não estoura, e não há o que selar.
        self.assertEqual(watcher.tick(self.key), ())

    def test_a_folder_that_does_not_exist_yet_seals_nothing_and_does_not_raise(self):
        watcher = cofre.Watcher(self.folder / "ainda-nao-existe")
        self.assertEqual(watcher.tick(self.key), ())


if __name__ == "__main__":
    unittest.main()
