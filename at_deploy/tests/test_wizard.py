"""The deploy's Wizard: §7 walked in order, over the words the `cli` already has.

Two things are proved here and nothing else. **§5's one-way rule** — every step
is a word the `cli` offers, reached through the `cli`'s own dispatch, so the
sequence cannot do anything the command line cannot. And **the sequence holds
itself back** — a required step that did not close does not open the next one,
and "closed" is the environment standing and not the exit code, which is the
whole reason §7a's way out needed its own answer.

**There is no window here any more** (TASK-169, fatia 3/3): the Tkinter front
that used to walk this sequence is gone from both artifacts, and what proves
`Step`, `STEPS`, `run_step` and `Walk` below is the engine alone — whatever
front TASK-130 builds reaches the `cli` through the exact same `run_step`.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import boot, gate
from at_deploy import environment as env
from at_deploy import podman, vpn, wizard
from at_deploy.cli import OK, REFUSED, USAGE, main

# A Chave Principal que a suíte digita (item 50, §4). A subida e o reinício do
# provedor a pedem pelo leitor sem eco, e é o MESMO leitor — `secret` — que
# qualquer chamador de `run_step` entrega, seja o terminal ou o que TASK-130
# vier a desenhar.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"


class FakeRuntime:
    """The runtime's seam, as the other deploy suites fake it: a container that
    says it is running."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        if call[:2] == ["container", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="true", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class FolderCase(unittest.TestCase):
    """A scratch Working Folder, which is where every path below resolves to."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        # E o diretório de execução tem o rascunho dele: ele mora fora da Pasta
        # de Trabalho por definição, e sem um `XDG_RUNTIME_DIR` próprio o que o
        # `up` materializa cairia no de quem roda a suíte.
        self.execution = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR",
             env.RUN_ENV: self.execution.name},
        )
        self.phrase = lambda question: PHRASE
        self.env.start()
        i18n.reset()
        # The machine has NO Podman, always: the day one is installed, a test
        # that read the real machine would pull images from the network.
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        # And its low-port rule ALLOWS every port, so the elevation is never the
        # thing being asked about (the environment's own suite holds that).
        self.floor = mock.patch.object(env, "floor", lambda: 0)
        self.floor.start()
        self.addCleanup(self.floor.stop)
        # And it is on no private network, so the site is the loop's.
        self.no_vpn = mock.patch.object(vpn, "run", side_effect=FileNotFoundError)
        self.no_vpn.start()
        self.addCleanup(self.no_vpn.stop)
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.execution.cleanup()
        self.scratch.cleanup()

    def machine(self, **kw) -> FakeRuntime:
        """A machine WITH a Podman, and a runtime that answers instead of doing."""
        fake = FakeRuntime(**kw)
        for patch in (
            mock.patch.object(podman, "present", lambda: True),
            mock.patch.object(podman, "run", fake.run),
            mock.patch.object(podman, "ok",
                              lambda args: fake.run(args).returncode == 0),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


# ------------------------------------------------------- §5's one-way rule ---

class TheStepsAreTheClisWords(unittest.TestCase):
    """A step whose word the `cli` did not take is a screen with a second door."""

    def test_the_sequence_is_the_one_declared(self):
        # A list, so that a step added or moved here is a decision somebody makes
        # on purpose: §7a's is first because nothing stands before it, and §7b's
        # follows (a witness has to exist before the gate can be proved).
        self.assertEqual([step.word for step in wizard.STEPS],
                         ["up", "credential", "switch"])
        self.assertEqual([step.argv for step in wizard.STEPS],
                         [(), (), ()])

    def test_every_step_is_a_word_the_cli_offers(self):
        # `cli.WORDS` is read off the tree that OFFERS the words, so a step that
        # is not in it would be a screen with a word the command line does not
        # take — the second door §5's one-way rule forbids.
        from at_deploy import cli

        for step in wizard.STEPS:
            with self.subTest(word=step.word):
                self.assertIn(step.word, cli.WORDS)

    def test_only_the_first_step_is_required(self):
        # §7a and §7c are the required ones and `up` is both of them. Everything
        # else is a person's decision: §6 makes the switch the person's act, and
        # an environment up with the Forms still on is a supported state.
        self.assertEqual([step.word for step in wizard.STEPS if step.required],
                         ["up"])

    def test_every_step_sentence_is_written_in_both_languages(self):
        for step in wizard.STEPS:
            for code in i18n.SUPPORTED:
                with self.subTest(word=step.word, language=code):
                    self.assertNotEqual(i18n.text(step.about, code), step.about)

    def test_the_step_runs_the_words_a_person_would_type(self):
        # The step reaches the `cli`'s own dispatch with the words a person
        # would type at `at-deploy`'s root, and everything the word printed
        # comes back as text — whatever draws it adds nothing.
        seen: list[list[str]] = []

        def door(argv, ask=None, secret=None) -> int:
            seen.append(argv)
            print("o que a palavra disse")
            return USAGE

        with mock.patch.object(wizard.cli, "services", door):
            code, text = wizard.run_step("up", ask=lambda q: "", secret=lambda q: PHRASE)

        self.assertEqual(code, USAGE)
        self.assertEqual(seen, [["up"]])
        self.assertEqual(text, "o que a palavra disse\n")

    def test_the_one_word_that_takes_a_name_is_given_it(self):
        # The argv of the one word that has an argument, so that the `cli`'s own
        # rule for it (`deploy.credential.ask`) is what answers a name
        # nobody gave.
        seen: list[list[str]] = []

        def door(argv, ask=None, secret=None) -> int:
            seen.append(argv)
            return OK

        with mock.patch.object(wizard.cli, "services", door):
            wizard.run_step("credential", ask=lambda q: "Rafael",
                            secret=lambda q: PHRASE)
            wizard.run_step("credential", ask=lambda q: "", secret=lambda q: PHRASE)

        self.assertEqual(seen, [["credential", "Rafael"], ["credential"]])

    def test_the_credential_name_question_is_written_in_both_languages(self):
        for code in i18n.SUPPORTED:
            with self.subTest(language=code):
                self.assertNotEqual(
                    i18n.text("deploy.wizard.credential.name", code),
                    "deploy.wizard.credential.name",
                )


# ------------------------------------------------------------ the sequence ---

class TheSequenceHoldsItselfBack(FolderCase):
    """A required step that did not close does not open the next one."""

    def test_a_step_that_did_not_close_holds_the_next_one(self):
        walk = wizard.Walk(run=lambda *a, **kw: (REFUSED, "nada fechou"))
        code, said = walk.run()
        self.assertEqual(code, REFUSED)
        self.assertEqual(said, "nada fechou")
        self.assertTrue(walk.held())
        self.assertEqual(walk.advance(), wizard.Walk.BLOCKED)
        self.assertEqual(walk.index, 0, "the sequence walked past a held step")

    def test_a_step_that_closed_opens_the_next_one(self):
        self.machine()
        walk = wizard.Walk(run=lambda *a, **kw: (OK, "pronto"))
        walk.run()
        self.assertFalse(walk.held())
        self.assertEqual(walk.advance(), wizard.Walk.NEXT)
        self.assertEqual(walk.index, 1)
        self.assertFalse(walk.closed, "the next step starts unrun")

    def test_an_optional_step_may_be_left_for_later(self):
        # §7 marks d, e and f as the ones a person may leave, and the Wizard is a
        # sequence and not a gate: a required step holds the walk, an optional
        # one does not.
        walk = wizard.Walk(run=lambda *a, **kw: (REFUSED, ""))
        walk.index = 1  # `credential`, the first optional one
        walk.run()
        self.assertFalse(walk.held())
        self.assertEqual(walk.advance(), wizard.Walk.NEXT)

    def test_the_last_step_of_the_sequence_finishes(self):
        walk = wizard.Walk(run=lambda *a, **kw: (OK, ""))
        walk.index = len(wizard.STEPS) - 1
        walk.run()
        self.assertEqual(walk.advance(), wizard.Walk.FINISH)

    def test_a_way_out_of_a_machine_with_no_podman_is_not_a_closed_step(self):
        # §7a's two ways out EXIT `0` — nothing failed — and the environment is
        # standing nowhere: reading the code alone would open §7b's step over an
        # environment that is not there.
        code, said = wizard.run_step("up", lambda question: "n")
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.hosted"), said)
        self.assertFalse(env.standing())

    def test_the_environment_standing_is_what_closes_the_first_step(self):
        self.machine()
        code, _ = wizard.run_step("up", lambda question: "", secret=self.phrase)
        self.assertEqual(code, OK)
        self.assertTrue(env.standing())
        self.assertTrue(wizard.STEPS[0].settled(code))

    def test_a_gate_that_did_not_commit_is_not_a_closed_switch(self):
        # §6's switch is read off the folder's own record — the one `at-cli` reads
        # (`gate.mode`) — so a future front and the app cannot disagree about the
        # path this folder is on.
        code, _ = wizard.run_step("switch", lambda question: "", secret=self.phrase)
        self.assertFalse(gate.on_gate())
        self.assertFalse(wizard.STEPS[2].settled(code))

        gate.remember(gate.GATE)
        self.assertTrue(wizard.STEPS[2].settled(OK))


# --------------------------------------------------------------- the door ---

class TheDoor(FolderCase):
    """`at-deploy` with no word — and the `Tk` that is gone for good.

    The Wizard of §7 is item 27's third slice, and it stays BUILT
    (`at_deploy/wizard.py`) but has NO CALLER — no front draws it today, and
    none did even while the Tkinter one existed (TASK-169, fatia 3/3, made
    that permanent). A command with no word answers the help, and nothing
    opens a window, because there is no window left to open.
    """

    def test_the_wordless_command_answers_the_help(self):
        code, text = self.quiet(main, [])
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("deploy.help.usage"), text)
        self.assertIn("credential", text)

    def test_a_word_still_answers_a_word(self):
        code, text = self.quiet(main, ["help"])
        self.assertEqual(code, OK)
        self.assertIn("credential", text)


# ------------------------------------------------------------ the sentence ---

class TheSentenceOfTheStep(FolderCase):
    """The screen writes none of its own: what it says is what the word said."""

    def test_a_step_that_fails_says_what_the_word_said(self):
        # Sem Podman e sem terminal, `up` recusa — e o que a tela diz é o que a
        # palavra disse, nunca uma segunda frase escrita pela tela.
        _, said = wizard.run_step("up")
        self.assertIn(i18n.tr("services.no_podman.no_tty"), said)


if __name__ == "__main__":
    unittest.main()
