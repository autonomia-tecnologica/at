"""The deploy's Wizard: §7 walked in order, over the words the `cli` already has.

§6 says this artifact is a `cli` and a Wizard, and that HERE the Wizard is the
natural front, because deploying is a SEQUENCE and not a sentence: it checks the
requirements, brings one thing up, moves on to the next. This file is that
sequence, and it is made of the `cli`'s own words — `up`, `credential`, `switch`,
`notify`, `phone` — walked one screen at a time.

**A step is a word, and nothing else.** `run_step` spells the argv a person would
type and hands it to the same dispatch the command line walks (`cli.services`),
so §5's one-way rule is not a promise written here but a property of the file: a
step whose word the `cli` did not take would not compile into an argv. And the
window writes no sentence of its own for what a step did — what the person reads
under the step is what the word PRINTED, captured and drawn in the window. That
is the whole reason the readers are the window's (`ask`, `secret`) instead of the
terminal's: the same act, the same words, on a screen.

**A step that did not close does not open the next one**, and "closed" is not the
exit code: the two ways out of a machine with no Podman (§7a), and a refused
elevation, EXIT `0` — nothing failed — and leave the environment standing
nowhere. So the two environment steps ask the folder (`environment.standing`,
`gate.on_gate`) and the rest read the code. The screen never invents a second
sentence for a failure: every act already has its own (`services.no_podman.*`,
`services.elevation.*`, `services.switch.*`), and they are the ones the word
printed.

**The no-display answer is `at-cli`'s own sentence** (`wizard.unavailable`): a
machine without a display is a legitimate place to run the deploy — §5's one-way
rule is what makes that not a loss — and what it is owed is to be told so and
handed the words (`cli.main` prints the help after it).

**The phone's token appears here, and it is the one thing this window shows that
is a credential.** The `phone` step runs the word that draws it, and what lands
in the window is the message the word printed — so the value is drawn in the
instant it was born, and the next run of the step prints the "held" message and
never the value. The rule §3 declares for the phone is kept by the same code the
`cli` keeps it with, because it IS the same code.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass

from at.core import gate, paths
from at.i18n import tr
from at.ui.wizard import app as at_window

from at_deploy import cli, environment

# What a person answers with, injected the way every surface here injects its
# own readers: the window hands over a dialog, a test hands over a lambda, and
# nothing but the window needs a `Tk` to exist.
Ask = Callable[[str], str]

# The exit code the `cli` answers a word with, named here so the steps read as
# sentences and not as numbers.
OK = cli.OK


def _ok(code: int) -> bool:
    """The common case: the word's own exit code is what "closed" means."""
    return code == OK


def _up_settled(code: int) -> bool:
    """Whether §7a's step closed — and it is the environment STANDING, not the
    code.

    A person who chose a way out of a machine with no Podman, or who refused the
    elevation, exits `0`: nothing failed, and the environment is nowhere. Reading
    the code alone here would open §7b's step over an environment that is not
    there.
    """
    return code == OK and environment.standing()


def _switch_settled(code: int) -> bool:
    """Whether §6's switch committed — read off the folder's own record, which
    is the one `at-cli` reads too (`gate.mode`), so the screen and the app cannot
    disagree about which path this folder is on.
    """
    return code == OK and gate.on_gate()


@dataclass(frozen=True)
class Step:
    """One screen of §7: the `cli` word it runs, and what it owes the next one.

    `required` is §7's own marking — a, b and c are required, d, e and f are not
    — and it is what the Next button reads: a required step that did not close
    holds the sequence, while an optional one may be left for later. What a
    required step OWES is not always its exit code, which is what `settled` is
    for; the whole of it comes down to the two environment steps.

    `about` is the WORD's own sentence (`deploy.services.<word>.about`), shared
    with the help: a step described differently in the two surfaces would be two
    words wearing one name.
    """

    word: str
    about: str
    required: bool
    settled: Callable[[int], bool] = _ok


# The sequence, in §7's order and cut by what each step ACHIEVES.
#
# `up` is §7a and §7c at once — the environment checks the Podman, asks for the
# elevation and brings every service of the manifest up, the WebApp included —
# and it is the one required step, because nothing else has anything to stand on
# before it. `credential` and `switch` are §7b: who the gate proves, and the gate
# proved in front of AT before the folder records that its authenticator is the
# gate. `notify` and `phone` are §7f, the two ends of the delivery — and the
# phone's is the one that prints.
#
# `switch` is optional and not a step that forces itself: §6 makes the switch the
# person's act, and a folder with the environment up and the Forms still on is a
# supported state and not a half-done one. `down` and `forms` are not here at
# all: they are the way BACK, and a sequence that walks forward has no step for
# them — the `cli` reaches both (§5).
STEPS: tuple[Step, ...] = (
    Step("up", "deploy.services.up.about", True, _up_settled),
    Step("credential", "deploy.services.credential.about", False),
    Step("switch", "deploy.services.switch.about", False, _switch_settled),
    Step("notify", "deploy.services.notify.about", False),
    Step("phone", "deploy.services.phone.about", False),
)


def run_step(word: str, ask: Ask | None = None, secret: Ask | None = None,
             name: str | None = None) -> tuple[int, str]:
    """Run ONE step and hand back what it said.

    **The step IS the `cli`'s word**, reached through the door the command line
    reaches it through: what is spelled here are the words that follow
    `at-deploy services` on the command line, and the window's readers stand in
    for the terminal's. Everything the word prints comes back as text — the
    screen draws it and adds nothing, which is §5's one-way rule visible in the
    code instead of promised in a comment.

    `name` is for the one word that takes an argument: when it is not given, the
    window asks for it first, and a name nobody gave is left for the word's OWN
    sentence to answer (`services.credential.ask`) rather than a second one
    written here.
    """
    argv = [word]
    if word == cli.ARGUMENT:
        if name is None and ask is not None:
            name = ask(tr("deploy.wizard.credential.name"))
        if name:
            argv.append(name)

    said = io.StringIO()
    with redirect_stdout(said):
        code = cli.services(argv, ask, secret)
    return code, said.getvalue()


class Walk:
    """The sequence, and the rule that holds it back.

    The state lives apart from the drawing for the one reason that matters: a
    suite can walk every step of §7 without ever opening a window, which is what
    keeps a `Tk` test from being a hung suite.
    """

    # What `advance` answers, and the window is what turns each one into a button.
    NEXT = "next"       # there is a step after this one
    FINISH = "finish"   # this was the last one
    BLOCKED = "blocked"  # a required step that did not close

    def __init__(self, steps: Sequence[Step] = STEPS,
                 run: Callable[..., tuple[int, str]] | None = None) -> None:
        self.steps = tuple(steps)
        self._run = run or run_step
        self.index = 0
        self.closed = False

    @property
    def step(self) -> Step:
        return self.steps[self.index]

    @property
    def last(self) -> bool:
        return self.index == len(self.steps) - 1

    def run(self, ask: Ask | None = None, secret: Ask | None = None,
            name: str | None = None) -> tuple[int, str]:
        """Run the current step, and record whether it closed."""
        code, said = self._run(self.step.word, ask, secret, name)
        self.closed = self.step.settled(code)
        return code, said

    def held(self) -> bool:
        """Whether this step keeps the sequence: §7's required one that did not
        close. An optional step never holds it — §7 marks d, e and f as the ones
        a person may leave — and the Wizard is a sequence and not a gate.
        """
        return self.step.required and not self.closed

    def advance(self) -> str:
        """`next`, `finish`, or the refusal — and never past a held step."""
        if self.held():
            return self.BLOCKED
        if self.last:
            return self.FINISH
        self.index += 1
        self.closed = False
        return self.NEXT


def build(root: object, ask: Ask | None = None, secret: Ask | None = None) -> Walk:
    """Draw the window on an existing `Tk` root, and answer with its `Walk`.

    Separate from `open_wizard` so a test can build the window and destroy it
    without entering the event loop — and the `Walk` comes back so that a test
    can drive the sequence without asking a widget anything.
    """
    import tkinter as tk

    walk = Walk()
    if ask is None or secret is None:
        ask, secret = _readers(root)

    root.title(tr("deploy.wizard.title"))
    root.minsize(560, 400)

    head = tk.Frame(root, padx=16, pady=12)
    head.pack(fill="x")
    # The folder first: the deploy is what writes `App/services/` inside it, and
    # which folder that is is the one thing a person has to be able to see.
    tk.Label(head, text=tr("deploy.wizard.folder", folder=paths.working_folder()),
             anchor="w").pack(fill="x")
    where = tk.Label(head, anchor="w")
    where.pack(fill="x")
    what = tk.Label(head, anchor="w", justify="left")
    what.pack(fill="x")
    note = tk.Label(head, anchor="w", justify="left", foreground="gray")
    note.pack(fill="x")

    # What the step PRINTED, and nothing else: replaced on every run, so a value
    # that comes out once (`phone`) is on the screen while the step is and is
    # gone with it.
    said = tk.Text(root, height=14, width=72, wrap="word")
    said.pack(fill="both", expand=True, padx=16)

    foot = tk.Frame(root, padx=16, pady=12)
    foot.pack(fill="x")

    def show() -> None:
        """Redraw what belongs to the current step — its name, its sentence, and
        whether the next one may start."""
        where.config(text=tr(
            "deploy.wizard.step.required" if walk.step.required
            else "deploy.wizard.step.optional",
            n=walk.index + 1, total=len(walk.steps), word=walk.step.word))
        what.config(text=tr(walk.step.about))
        note.config(text=tr("deploy.wizard.held") if walk.held() else "")
        forward.config(
            text=tr("deploy.wizard.finish") if walk.last
            else tr("deploy.wizard.next"),
            state="disabled" if walk.held() else "normal",
        )

    def on_run() -> None:
        _, text = walk.run(ask, secret)
        said.delete("1.0", "end")
        said.insert("end", text)
        show()

    def on_forward() -> None:
        if walk.advance() == Walk.FINISH:
            root.destroy()
            return
        said.delete("1.0", "end")
        show()

    tk.Button(foot, text=tr("deploy.wizard.run"), command=on_run).pack(side="left")
    forward = tk.Button(foot, text=tr("deploy.wizard.next"), command=on_forward)
    forward.pack(side="right")
    tk.Button(foot, text=tr("deploy.wizard.close"),
              command=root.destroy).pack(side="right", padx=(0, 8))

    show()
    return walk


def _readers(root: object) -> tuple[Ask, Ask]:
    """The window's two readers, and they are ONE door.

    `ask` is what a terminal would read with `input` and `secret` is what it
    would read with `getpass`: the same question, and the second one hides what
    is typed — the screen's way of saying that a credential is not for whoever is
    looking at the screen, which is the rule every credential door here follows.

    The yes/no questions travel through the same door, so the person answers them
    the way the terminal words them — `s` or `n`. A dialog that was dismissed is
    an empty answer, and an empty answer is a refusal everywhere it lands.
    """
    def one(question: str, hidden: bool) -> str:
        from tkinter import simpledialog

        answer = simpledialog.askstring(tr("deploy.wizard.title"), question,
                                        parent=root,
                                        show="*" if hidden else None)
        return "" if answer is None else answer

    return (lambda question: one(question, False),
            lambda question: one(question, True))


def open_wizard() -> bool:
    """Open the window and hold the process until it closes.

    `False` when there is no graphical interface to open — a machine with no
    display is a legitimate place to run the deploy, and it must be told so
    plainly instead of by a traceback. The sentence is `at-cli`'s own: the Control
    Panel is one thing with two fronts, and a refusal that read differently on
    each artifact would be two.
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
        at_window.destroy(root, tk)
    return True
