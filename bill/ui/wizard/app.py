"""The Control Panel window.

This is only the door standing open: it proves that `bill` with no word has
where to go. What the panel governs — what is enabled, what is running, what is
installed — arrives with the environment, and it is the last item in the
backlog because it depends on everything before it.
"""

from __future__ import annotations

from collections.abc import Sequence

from bill.i18n import tr


def build(root) -> None:
    """Draw the panel on an existing Tk root.

    Separate from `open_wizard` so a test can build the window and destroy it
    without entering the event loop.
    """
    import tkinter as tk

    root.title(tr("wizard.window.title"))
    root.minsize(360, 200)

    panel = tk.Frame(root, padx=32, pady=32)
    panel.pack(fill="both", expand=True)
    tk.Label(panel, text=tr("wizard.hello")).pack(expand=True)
    tk.Button(panel, text=tr("wizard.close"), command=root.destroy).pack()


def open_wizard(argv: Sequence[str] | None = None) -> bool:
    """Open the panel and hold the process until it closes.

    `False` when there is no graphical interface to open — a machine without a
    display is a legitimate place to run Bill, and it must be told so plainly
    instead of by a traceback.
    """
    try:
        import tkinter as tk
    except ImportError as error:
        print(tr("wizard.unavailable", error=error))
        return False

    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(tr("wizard.unavailable", error=error))
        return False

    try:
        build(root)
        root.mainloop()
    finally:
        destroy(root, tk)
    return True


def destroy(root, tk) -> None:
    """Destroy the root, unless it is already gone — which it usually is.

    The Close button IS `root.destroy` (`build`), so by the time `mainloop`
    returns the person's own click has destroyed the root already, and asking it
    to destroy itself a second time is a `TclError` on the way out of a window
    that closed correctly. A display that went away mid-loop raises the same
    one. Neither is a failure — the window is closed either way — so the second
    call is refused instead of thrown.

    It is public because the deploy's Wizard closes its window the same way and
    the rule is one rule (item 27, `bill_deploy/wizard.py`): two artifacts with
    two windows have one way out of a window that is already gone.
    """
    try:
        root.destroy()
    except tk.TclError:
        pass
