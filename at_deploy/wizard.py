"""The deploy's Wizard: §7 walked in order, over the words the `cli` already has.

§6 says this artifact is a `cli` and a Wizard, and that HERE the Wizard is the
natural front, because deploying is a SEQUENCE and not a sentence: it checks the
requirements, brings one thing up, moves on to the next. This file is that
sequence, made of the `cli`'s own words — `up`, `credential`, `switch` —
walked one step at a time. **It draws nothing itself** (TASK-169, fatia 3/3):
the Tkinter window that used to walk it died with the rest of the Tkinter in
the product, and what shows this sequence to a person is TASK-130's, still to
come.

**A step is a word (and, since 2026-09-28, an optional fixed tail after it), and
nothing else.** `run_step` spells the argv a person would type and hands it to
the same dispatch the command line walks (`cli.services`), so §5's one-way rule
is not a promise written here but a property of the file: a step whose word the
`cli` did not take would not compile into an argv, and neither would one whose
tail (`Step.argv`) is not a shape `cli.services` accepts. And whatever shows a
step writes no sentence of its own for what it did — what the person reads is
what the word PRINTED, captured and handed back as text. That is the whole
reason the readers (`ask`, `secret`) are injected rather than fixed to a
terminal: the same act, the same words, wherever they end up drawn.

**A step that did not close does not open the next one**, and "closed" is not the
exit code: the two ways out of a machine with no Podman (§7a), and a refused
elevation, EXIT `0` — nothing failed — and leave the environment standing
nowhere. So the two environment steps ask the folder (`environment.standing`,
`gate.on_gate`) and the rest read the code. No step invents a second sentence
for a failure: every act already has its own (`services.no_podman.*`,
`services.elevation.*`, `services.switch.*`), and they are the ones the word
printed.

**A credential of the phone's own does not appear here** (TASK-187): the edge
fronts the site, and the SAME Chave Principal the person already types for it
proves them everywhere — one name, no second credential to hold.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass

from at.core import gate
from at.i18n import tr
from at_deploy import cli, environment

# What a person answers with, injected the way every surface here injects its
# own readers: whatever draws this sequence hands over a pair of readers, a
# test hands over a lambda, and nothing here needs any toolkit to exist.
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
    is the one `at-cli` reads too (`gate.mode`), so whatever shows this sequence
    and the app cannot disagree about which path this folder is on.
    """
    return code == OK and gate.on_gate()


@dataclass(frozen=True)
class Step:
    """One step of §7: the `cli` word it runs, and what it owes the next one.

    `required` is §7's own marking — a, b and c are required, d, e and f are not
    — and it is what the next step reads: a required step that did not close
    holds the sequence, while an optional one may be left for later. What a
    required step OWES is not always its exit code, which is what `settled` is
    for; the whole of it comes down to the two environment steps.

    `about` is the WORD's own sentence (`deploy.<word>.about`), shared
    with the help: a step described differently in the two surfaces would be two
    words wearing one name.
    """

    word: str
    about: str
    required: bool
    settled: Callable[[int], bool] = _ok
    # The fixed words after `word`, for a step whose act is not the word ALONE.
    # No step needs one today, and the field stays generic for the shape
    # `cli.services` already accepts.
    argv: tuple[str, ...] = ()


# The sequence, in §7's order and cut by what each step ACHIEVES.
#
# `up` is §7a and §7c at once — the environment checks the Podman, asks for the
# elevation and brings every service of the manifest up, the WebApp included —
# and it is the one required step, because nothing else has anything to stand on
# before it. `credential` and `switch` are §7b: who the gate proves, and the gate
# proved in front of AT before the folder records that its authenticator is the
# gate.
#
# `switch` is optional and not a step that forces itself: §6 makes the switch the
# person's act, and a folder with the environment up and the Forms still on is a
# supported state and not a half-done one. `down` and `forms` are not here at
# all: they are the way BACK, and a sequence that walks forward has no step for
# them — the `cli` reaches both (§5).
STEPS: tuple[Step, ...] = (
    Step("up", "deploy.up.about", True, _up_settled),
    Step("credential", "deploy.credential.about", False),
    Step("switch", "deploy.switch.about", False, _switch_settled),
)


def run_step(word: str, ask: Ask | None = None, secret: Ask | None = None,
             name: str | None = None,
             argv: tuple[str, ...] = ()) -> tuple[int, str]:
    """Run ONE step and hand back what it said.

    **The step IS the `cli`'s word**, reached through the door the command line
    reaches it through: what is spelled here are the words a person would type
    at `at-deploy`'s own root, and the caller's own readers stand in
    for the terminal's. Everything the word prints comes back as text — whatever
    draws it adds nothing, which is §5's one-way rule visible in the code instead
    of promised in a comment.

    `name` is for the one word that takes an argument: when it is not given,
    `ask` is asked for it first, and a name nobody gave is left for the word's
    OWN sentence to answer (`deploy.credential.ask`) rather than a second one
    written here. `argv` is a step's fixed trailing words (`Step.argv`) — the
    part of the line that is not the argument door, and not a name either.
    """
    call = [word, *argv]
    if word == cli.ARGUMENT:
        if name is None and ask is not None:
            name = ask(tr("deploy.wizard.credential.name"))
        if name:
            call.append(name)

    said = io.StringIO()
    with redirect_stdout(said):
        code = cli.services(call, ask, secret)
    return code, said.getvalue()


class Walk:
    """The sequence, and the rule that holds it back.

    The state lives apart from whatever draws it, for the one reason that
    matters: a suite can walk every step of §7 without a front to draw it.
    """

    # What `advance` answers, and whatever draws this is what turns each one
    # into an action.
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
        code, said = self._run(self.step.word, ask, secret, name,
                               self.step.argv)
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
