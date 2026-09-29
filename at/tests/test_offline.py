"""O motor offline: `edited_at` restampado a cada escrita, e a reconciliação
por last-write-wins que o compara (TASK-162, fatia 1/2).

Toda a suíte aqui é sem rede e sem navegador — a fila é construída à mão
(`offline.QueueEntry`), como a fatia 2 vai construí-la a partir do que o
IndexedDB guardou, e `offline.reconcile` é chamado direto, sem servidor no ar.
Cada teste aponta AT para uma pasta descartável (`AT_ROOT`), nunca a Pasta de
Trabalho do checkout.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, offline, tables
from at.data import schema, store


class Case(unittest.TestCase):
    """Uma Pasta de Trabalho descartável, com a tabela `task` do produto."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()


class TheTouch(Case):
    """`edited_at` é restampado em toda escrita da tarefa, mude ou não o
    `status` — o que `modifications[].at` nunca fez (§`tables._log_status`)."""

    def test_a_new_task_carries_the_instant_it_was_born(self):
        row = tables.create("task", {"text": "café"})
        self.assertIsInstance(row.get("edited_at"), str)
        self.assertTrue(row["edited_at"].endswith("Z"))

    def test_editing_a_field_the_status_log_does_not_track_still_touches_it(self):
        row = tables.create("task", {"text": "café"}, at="2026-01-01T10:00:00.000Z")
        edited = tables.edit(
            "task", row["id"], {"text": "chá"}, at="2026-01-01T10:00:01.000Z"
        )
        self.assertNotEqual(edited["edited_at"], row["edited_at"])
        # `status` não mudou, e o log de status não ganhou uma segunda linha —
        # a prova de que `modifications[].at` não serve para isto.
        self.assertEqual(edited.get("modifications"), row.get("modifications"))

    def test_an_explicit_instant_overrides_the_write_s_own_now(self):
        # O motor offline estampa o instante da EDIÇÃO, não o do reencontro
        # com o servidor — é isto que `at=` existe para.
        row = tables.create("task", {"text": "café"}, at="2020-01-01T00:00:00.000Z")
        self.assertEqual(row["edited_at"], "2020-01-01T00:00:00.000Z")
        edited = tables.edit(
            "task", row["id"], {"text": "chá"}, at="2021-06-01T00:00:00.000Z"
        )
        self.assertEqual(edited["edited_at"], "2021-06-01T00:00:00.000Z")

    def test_cancelling_touches_it_too(self):
        row = tables.create("task", {"text": "café"}, at="2020-01-01T00:00:00.000Z")
        closed = tables.cancel("task", row["id"], reason="não precisa mais")
        self.assertNotEqual(closed["edited_at"], row["edited_at"])


class TheReconciliation(Case):
    """`offline.reconcile`: quem venceu, entrada por entrada."""

    def test_a_clean_edit_with_no_conflict_applies(self):
        row = tables.create("task", {"text": "café"}, at="2026-01-01T10:00:00.000Z")
        entry = offline.QueueEntry(
            action="edit",
            id=row["id"],
            values={"text": "chá"},
            edited_at="2026-01-01T11:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertEqual(len(resolved), 1)
        self.assertTrue(resolved[0].applied)
        self.assertEqual(resolved[0].row["text"], "chá")

    def test_a_stale_edit_is_dropped_and_the_servers_row_comes_back(self):
        row = tables.create("task", {"text": "café"}, at="2026-01-01T10:00:00.000Z")
        # Alguém (outro dispositivo, ainda com rede) escreveu DEPOIS do
        # instante que a entrada offline carrega.
        current = tables.edit(
            "task", row["id"], {"text": "vencedor"}, at="2026-01-01T12:00:00.000Z"
        )
        entry = offline.QueueEntry(
            action="edit",
            id=row["id"],
            values={"text": "perdedor"},
            edited_at="2026-01-01T11:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertFalse(resolved[0].applied)
        self.assertEqual(resolved[0].row["text"], "vencedor")
        # E a linha de fato não mudou.
        self.assertEqual(tables.find("task", row["id"])["text"], current["text"])

    def test_a_tie_is_kept_by_the_server(self):
        row = tables.create("task", {"text": "café"}, at="2026-01-01T10:00:00.000Z")
        entry = offline.QueueEntry(
            action="edit",
            id=row["id"],
            values={"text": "empate"},
            edited_at="2026-01-01T10:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertFalse(resolved[0].applied)
        self.assertEqual(resolved[0].row["text"], "café")

    def test_a_create_always_applies_because_nothing_could_conflict(self):
        entry = offline.QueueEntry(
            action="create",
            values={"text": "nova, feita sem rede"},
            edited_at="2026-01-01T09:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertTrue(resolved[0].applied)
        self.assertEqual(resolved[0].row["text"], "nova, feita sem rede")
        self.assertEqual(resolved[0].row["edited_at"], "2026-01-01T09:00:00.000Z")

    def test_an_edit_queued_right_after_its_own_offline_create_finds_it(self):
        made = offline.QueueEntry(
            action="create",
            values={"text": "primeira versão"},
            edited_at="2026-01-01T09:00:00.000Z",
            local_id="local-1",
        )
        touched = offline.QueueEntry(
            action="edit",
            id="local-1",
            values={"text": "segunda versão, ainda offline"},
            edited_at="2026-01-01T09:05:00.000Z",
        )
        resolved = offline.reconcile([made, touched])
        self.assertTrue(resolved[0].applied)
        self.assertTrue(resolved[1].applied)
        self.assertEqual(resolved[1].row["text"], "segunda versão, ainda offline")
        self.assertEqual(resolved[1].row["id"], resolved[0].row["id"])

    def test_an_edit_whose_local_id_never_arrived_is_dropped_with_no_row(self):
        entry = offline.QueueEntry(
            action="edit",
            id="local-nunca-veio",
            values={"text": "x"},
            edited_at="2026-01-01T09:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertFalse(resolved[0].applied)
        self.assertIsNone(resolved[0].row)

    def test_an_edit_of_a_row_deleted_while_offline_is_dropped_with_no_row(self):
        row = tables.create("task", {"text": "vai sumir"})
        tables.delete("task", row["id"])
        entry = offline.QueueEntry(
            action="edit",
            id=row["id"],
            values={"text": "tarde demais"},
            edited_at="2026-01-01T09:00:00.000Z",
        )
        resolved = offline.reconcile([entry])
        self.assertFalse(resolved[0].applied)
        self.assertIsNone(resolved[0].row)

    def test_a_malformed_instant_is_refused_in_the_engines_own_words(self):
        row = tables.create("task", {"text": "café"})
        entry = offline.QueueEntry(
            action="edit",
            id=row["id"],
            values={"text": "chá"},
            edited_at="não é uma data",
        )
        with self.assertRaises(tables.TableError):
            offline.reconcile([entry])

    def test_a_batch_reconciles_two_unrelated_tasks_independently(self):
        one = tables.create("task", {"text": "um"}, at="2026-01-01T10:00:00.000Z")
        two = tables.create("task", {"text": "dois"}, at="2026-01-01T10:00:00.000Z")
        entries = [
            offline.QueueEntry(
                action="edit", id=one["id"], values={"text": "um, editado"},
                edited_at="2026-01-01T11:00:00.000Z",
            ),
            offline.QueueEntry(
                action="edit", id=two["id"], values={"text": "dois, editado"},
                edited_at="2026-01-01T09:00:00.000Z",  # anterior — perde
            ),
        ]
        resolved = offline.reconcile(entries)
        self.assertTrue(resolved[0].applied)
        self.assertFalse(resolved[1].applied)
        self.assertEqual(tables.find("task", one["id"])["text"], "um, editado")
        self.assertEqual(tables.find("task", two["id"])["text"], "dois")


if __name__ == "__main__":
    unittest.main()
