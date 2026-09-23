"""The window `bill` opens with no word: how it closes.

`test_cli` leaves this path alone on purpose — a suite that can pop a window is
a suite that hangs on a build machine — and so does this one: the `tkinter`
below is a window that never draws. It records what it was asked and closes
itself, which is the whole of what the bug was about.

The bug: the Close button IS `root.destroy`, so a window the person closes
correctly destroys its own root, and the `finally` of `open_wizard` used to
destroy it a second time — a `TclError` thrown on the way out of a window that
had already closed fine. The person saw a traceback for doing nothing wrong.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bill import i18n
from bill.ui.wizard import app as wizard


class _ClosedRoot:
    """A root that behaves like a real one about the only thing here that
    matters: the SECOND `destroy` raises, because the application is gone."""

    def __init__(self, tk: "_FakeTkinter"):
        self._tk = tk
        self.destroys = 0

    # What `build` asks of a root, and none of what it draws.
    def title(self, *args: object) -> None:
        pass

    def minsize(self, *args: object) -> None:
        pass

    def pack(self, *args: object, **kwargs: object) -> "_ClosedRoot":
        return self

    def mainloop(self) -> None:
        # The person clicks Close, whose command IS `root.destroy`, and the loop
        # returns with the root already gone — the state the guard exists for.
        self.destroy()

    def destroy(self) -> None:
        self.destroys += 1
        if self.destroys > 1:
            raise self._tk.TclError(
                'can\'t invoke "destroy" command: application has been destroyed'
            )


class _FakeTkinter:
    """Just enough `tkinter` for the panel to build and the root to close."""

    class TclError(Exception):
        pass

    def __init__(self) -> None:
        self.root = _ClosedRoot(self)

    def Tk(self) -> _ClosedRoot:
        return self.root

    def Frame(self, *args: object, **kwargs: object) -> _ClosedRoot:
        return self.root

    def Label(self, *args: object, **kwargs: object) -> _ClosedRoot:
        return self.root

    def Button(self, *args: object, **kwargs: object) -> _ClosedRoot:
        return self.root


class TheWindowCloses(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"BILL_ROOT": str(Path(self.scratch.name)), "BILL_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def test_a_window_the_person_closed_does_not_blow_up_on_the_way_out(self):
        fake = _FakeTkinter()
        with mock.patch.dict(sys.modules, {"tkinter": fake}):
            opened = wizard.open_wizard()
        self.assertTrue(opened)
        # Twice asked, once honoured: the click, and the way out of a window
        # that had already closed correctly.
        self.assertEqual(fake.root.destroys, 2)


if __name__ == "__main__":
    unittest.main()
