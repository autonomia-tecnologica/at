"""O vigia: detecta a mudança numa pasta e despacha a consumidores (TASK-152).

Toda a suíte aqui é sem rede e sem tocar a instância — cada teste vigia uma
pasta descartável (`tempfile`), e o `Vigia` não lê `AT_ROOT` nem coisa nenhuma
do resto do produto: ele só sabe da pasta que a própria instância recebeu.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from at.core import vigia


class TheFirstScan(unittest.TestCase):
    """A primeira varredura grava o retrato e não despacha nada."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def test_a_file_already_there_before_the_first_scan_is_not_an_event(self):
        (self.folder / "ja-estava.txt").write_text("velho", encoding="utf-8")
        watcher = vigia.Vigia(self.folder)
        seen: list[vigia.Event] = []
        watcher.watch(seen.append)
        self.assertEqual(watcher.scan(), ())
        self.assertEqual(seen, [])

    def test_a_folder_that_does_not_exist_yet_scans_as_empty(self):
        missing = self.folder / "ainda-nao-existe"
        watcher = vigia.Vigia(missing)
        self.assertEqual(watcher.scan(), ())
        missing.mkdir()
        (missing / "novo.txt").write_text("a", encoding="utf-8")
        self.assertEqual(len(watcher.scan()), 1)


class TheDispatch(unittest.TestCase):
    """A escrita que aconteceu DEPOIS do retrato é o que dispara o consumidor."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)
        self.watcher = vigia.Vigia(self.folder)
        self.watcher.scan()  # a primeira, que só grava o retrato

    def test_a_new_file_is_dispatched_with_its_own_absolute_path(self):
        seen: list[vigia.Event] = []
        self.watcher.watch(seen.append)
        where = self.folder / "arquivo.txt"
        where.write_text("conteúdo", encoding="utf-8")
        events = self.watcher.scan()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].path, where)
        self.assertEqual(seen, list(events))

    def test_a_rewritten_file_is_dispatched_again(self):
        where = self.folder / "arquivo.txt"
        where.write_text("um", encoding="utf-8")
        self.watcher.scan()
        where.write_text("dois, mais comprido que o primeiro", encoding="utf-8")
        events = self.watcher.scan()
        self.assertEqual([event.path for event in events], [where])

    def test_a_quiet_scan_dispatches_nothing(self):
        (self.folder / "arquivo.txt").write_text("um", encoding="utf-8")
        self.watcher.scan()
        self.assertEqual(self.watcher.scan(), ())

    def test_every_registered_consumer_is_called(self):
        first: list[vigia.Event] = []
        second: list[vigia.Event] = []
        self.watcher.watch(first.append)
        self.watcher.watch(second.append)
        (self.folder / "arquivo.txt").write_text("a", encoding="utf-8")
        self.watcher.scan()
        self.assertEqual(len(first), 1)
        self.assertEqual(first, second)

    def test_a_removed_file_dispatches_nothing(self):
        # Fora do escopo desta fatia (§ módulo): só a escrita é vista.
        where = self.folder / "arquivo.txt"
        where.write_text("a", encoding="utf-8")
        self.watcher.scan()
        where.unlink()
        self.assertEqual(self.watcher.scan(), ())

    def test_two_files_written_in_the_same_scan_are_both_dispatched(self):
        (self.folder / "a.txt").write_text("a", encoding="utf-8")
        (self.folder / "b.txt").write_text("b", encoding="utf-8")
        events = self.watcher.scan()
        self.assertEqual(
            {event.path for event in events},
            {self.folder / "a.txt", self.folder / "b.txt"},
        )

    def test_a_subfolders_file_is_seen_too(self):
        nested = self.folder / "sub"
        nested.mkdir()
        where = nested / "arquivo.txt"
        where.write_text("a", encoding="utf-8")
        events = self.watcher.scan()
        self.assertEqual([event.path for event in events], [where])


class TheIsolation(unittest.TestCase):
    """Duas pastas vigiadas não se enxergam."""

    def test_two_vigias_of_different_folders_do_not_cross(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            first = vigia.Vigia(Path(one))
            second = vigia.Vigia(Path(two))
            first.scan()
            second.scan()
            seen_first: list[vigia.Event] = []
            seen_second: list[vigia.Event] = []
            first.watch(seen_first.append)
            second.watch(seen_second.append)
            (Path(one) / "arquivo.txt").write_text("a", encoding="utf-8")
            first.scan()
            second.scan()
            self.assertEqual(len(seen_first), 1)
            self.assertEqual(seen_second, [])


if __name__ == "__main__":
    unittest.main()
