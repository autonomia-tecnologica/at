"""The resolution of a folder's name: every face, and the internal name.

`paths.candidates` is the whole promise that a folder that keeps an old name is
still the folder AT reads (§3). These tests hold the ORDER it tries and the fact
that a retired face answers — the two things a rename can break.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import paths


class Resolution(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def test_a_folder_under_the_retired_name_is_still_found(self):
        # A pessoa não perde os arquivos: a resolução aceita a grafia que a
        # pasta ainda carrega, e `prose_dir()` a devolve.
        old = self.root / "Arquivos"
        old.mkdir()
        (old / "nota.md").write_text("olá\n", encoding="utf-8")
        self.assertEqual(paths.folder("prose"), old)
        self.assertEqual(paths.prose_dir(), old)
        self.assertEqual(
            (paths.prose_dir() / "nota.md").read_text(encoding="utf-8"), "olá\n"
        )

    def test_the_candidates_try_every_face_then_the_internal_name(self):
        # A língua ativa, a outra língua, as faces aposentadas na ordem em que
        # foram declaradas, e o nome interno por último.
        self.assertEqual(
            paths.candidates("prose"),
            ("Biblioteca", "Library", "Arquivos", "Files", "prose"),
        )

    def test_the_current_candidates_leave_the_retired_faces_out(self):
        self.assertEqual(
            paths.current_candidates("prose"),
            ("Biblioteca", "Library", "prose"),
        )


if __name__ == "__main__":
    unittest.main()
