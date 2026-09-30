"""The deploy's Wizard: §7 walked in order, over the words the `cli` already has.

Two things are proved here and nothing else. **§5's one-way rule** — every step
is a word the `cli` offers, reached through the `cli`'s own dispatch, so the
screen cannot do anything the command line cannot. And **the sequence holds
itself back** — a required step that did not close does not open the next one,
and "closed" is the environment standing and not the exit code, which is the
whole reason §7a's way out needed its own answer.

The window is the `tkinter` that never draws, the way `at/tests/test_wizard.py`
does it: this machine HAS a display, so a test that opened a real one would be a
test that hangs the suite. What the fake records is what the wizard asked of it —
the buttons it built, what each command does, and what landed in the text area —
which is enough to walk the whole sequence without a screen ever appearing.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import actors, boot, gate
from at_deploy import environment as env
from at_deploy import notifier, podman, vpn, wizard
from at_deploy.cli import OK, REFUSED, USAGE, main

# The token the fake notifier draws, and it is nobody's: what the tests read is
# where it WENT.
DRAWN_TOKEN = "tk_abcdefghijklmnopqrstuvwxyz012"
TOKEN_LINE = f"token {DRAWN_TOKEN} created for user at, never expires"


class Answer:
    """A stand-in for the notifier's HTTP answer, for the `notify` step's own
    push — no socket, the way every other suite fakes `urlopen`."""

    def __init__(self, status: int = 200) -> None:
        self.status = status

    def __enter__(self) -> "Answer":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


CREDENTIAL = "uma-frase-bem-longa"
NEW_CREDENTIAL = "outra-frase-bem-longa"

# A Chave Principal que a suíte digita (item 50, §4). A subida e o reinício do
# provedor a pedem pelo leitor sem eco, e a janela entrega o dela: é o diálogo
# com o que se digita escondido (`simpledialog`, com o `show`) que a suíte
# substitui, e ele é o mesmo caminho do terminal.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"

# Every sentence the Wizard says, in both languages: the keys of the window
# itself. A key the catalog does not have answers with the KEY, which is why this
# list exists — a text added to `wizard.py` without a line here is a text nobody
# checks. The steps' own sentences are the words' (`deploy.<word>.about`)
# and the tree's suite already holds those.
SAID = (
    "deploy.wizard.title", "deploy.wizard.folder",
    "deploy.wizard.step.required", "deploy.wizard.step.optional",
    "deploy.wizard.run", "deploy.wizard.next", "deploy.wizard.finish",
    "deploy.wizard.close", "deploy.wizard.held",
    "deploy.wizard.credential.name",
)


class FakeSimpleDialog:
    """`tkinter.simpledialog`, answered by whatever the test put in `answers`.

    It is here because the window's two readers are its only customers, and the
    rule they carry — the second one hides what is typed — is a rule about THIS
    call and not about the dialog. An empty list answers with an empty string,
    which is what a dismissed dialog gives and what every question here reads as
    a refusal.
    """

    def __init__(self) -> None:
        self.answers: list[str] = []
        self.asked: list[tuple[str, dict]] = []

    def askstring(self, title: str, prompt: str, **kw: object) -> str:
        self.asked.append((prompt, kw))
        return self.answers.pop(0) if self.answers else ""


class Widget:
    """One fake widget: it records what it was told and never draws."""

    def __init__(self, tk: "FakeTkinter", kind: str, **kw: object) -> None:
        self.kind = kind
        self.kw = dict(kw)
        self.state = "normal"
        self.content = ""
        tk.made.append(self)

    def pack(self, *args: object, **kw: object) -> "Widget":
        return self

    def config(self, **kw: object) -> None:
        if "state" in kw:
            self.state = str(kw["state"])
        self.kw.update(kw)

    # What `tk.Text` is asked, and only that.
    def delete(self, *args: object) -> None:
        self.content = ""

    def insert(self, *args: object) -> None:
        self.content += str(args[-1]) if args else ""

    @property
    def text(self) -> str:
        return str(self.kw.get("text", ""))

    def press(self) -> None:
        """What the person's click does — the command the widget was built with."""
        command = self.kw.get("command")
        if command is not None:
            command()


class Root(Widget):
    """The `Tk` root: the loop returns, and the second `destroy` is the error
    a window that closed correctly raises on the way out."""

    def __init__(self, tk: "FakeTkinter") -> None:
        super().__init__(tk, "root")
        self.tk = tk
        self.destroys = 0

    def title(self, *args: object) -> None:
        pass

    def minsize(self, *args: object) -> None:
        pass

    def mainloop(self) -> None:
        pass

    def destroy(self) -> None:
        self.destroys += 1
        if self.destroys > 1:
            raise self.tk.TclError(
                'can\'t invoke "destroy" command: application has been destroyed'
            )


class FakeTkinter:
    """Just enough `tkinter` for the window to build, be walked, and close."""

    class TclError(Exception):
        pass

    def __init__(self) -> None:
        self.made: list[Widget] = []
        self.root = Root(self)
        self.simpledialog = FakeSimpleDialog()

    def Tk(self) -> Root:
        return self.root

    def Frame(self, *args: object, **kw: object) -> Widget:
        return Widget(self, "frame", **kw)

    def Label(self, *args: object, **kw: object) -> Widget:
        return Widget(self, "label", **kw)

    def Text(self, *args: object, **kw: object) -> Widget:
        return Widget(self, "text", **kw)

    def Button(self, *args: object, **kw: object) -> Widget:
        return Widget(self, "button", **kw)

    # What the tests read off the window it built.
    def button(self, text: str) -> Widget:
        return next(widget for widget in self.made
                    if widget.kind == "button" and widget.text == text)

    def area(self) -> Widget:
        return next(widget for widget in self.made if widget.kind == "text")


class FakeRuntime:
    """The runtime's seam, as the other deploy suites fake it: the notifier's
    own CLI answered, and a container that says it is running."""

    def __init__(self, answer: str = TOKEN_LINE) -> None:
        self.calls: list[list[str]] = []
        self.answer = answer

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        if call[:2] == ["container", "inspect"]:
            return SimpleNamespace(returncode=0, stdout="true", stderr="")
        if "test" in call:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        said = self.answer if "ntfy" in call and "token" in call else ""
        return SimpleNamespace(returncode=0, stdout=said, stderr="")


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
        # **E a pessoa digita a Chave Principal**: a subida a lê de um leitor sem eco, e a
        # suíte entrega o dela — o `getpass` do terminal, ou o diálogo da janela.
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

    def person(self, name: str = "Rafael") -> dict:
        return actors.create_admin(name, CREDENTIAL)

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()

    def window(self, **kw):
        """The wizard built over a fake window, and the walk it answers with."""
        fake = FakeTkinter()
        with mock.patch.dict(sys.modules, {"tkinter": fake}):
            walk = wizard.build(fake.root, **kw)
        return fake, walk


# ------------------------------------------------------- §5's one-way rule ---

class TheStepsAreTheClisWords(unittest.TestCase):
    """A step whose word the `cli` did not take is a screen with a second door."""

    def test_the_sequence_is_the_one_declared(self):
        # A list, so that a step added or moved here is a decision somebody makes
        # on purpose: §7a's is first because nothing stands before it, §7b's
        # follows (a witness has to exist before the gate can be proved), and
        # §7f's closes it.
        self.assertEqual([step.word for step in wizard.STEPS],
                         ["up", "credential", "switch", "notify"])
        self.assertEqual([step.argv for step in wizard.STEPS],
                         [(), (), (), ()])

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
        # comes back as text — the screen draws it and adds nothing.
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


class TheSentencesBothLanguages(unittest.TestCase):
    def test_every_sentence_of_the_window_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the window would show the key",
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
        # (`gate.mode`) — so the screen and the app cannot disagree about the
        # path this folder is on.
        code, _ = wizard.run_step("switch", lambda question: "", secret=self.phrase)
        self.assertFalse(gate.on_gate())
        self.assertFalse(wizard.STEPS[2].settled(code))

        gate.remember(gate.GATE)
        self.assertTrue(wizard.STEPS[2].settled(OK))


# ------------------------------------------------------------- the window ---

class TheWindow(FolderCase):
    """What the window draws, what it walks, and what it shows once."""

    def test_the_window_builds_on_the_first_step_with_the_next_one_held(self):
        fake, walk = self.window(ask=lambda q: "", secret=lambda q: PHRASE)
        self.assertEqual(walk.index, 0)
        self.assertEqual(fake.button(i18n.tr("deploy.wizard.next")).state,
                         "disabled", "a required step that was not run was passed")
        self.assertTrue(
            any(widget.kind == "label"
                and widget.text == i18n.tr("deploy.wizard.held")
                for widget in fake.made),
            "the window did not say why the next step is not open",
        )

    def test_the_window_keeps_no_words_of_a_step_that_was_not_run(self):
        fake, _ = self.window(ask=lambda q: "", secret=lambda q: PHRASE)
        self.assertEqual(fake.area().content, "",
                         "the window drew words no step had printed")

    def credential_step(self, fake, answers):
        """Run `credential` through the WINDOW's own readers.

        The dialog is imported when a question is asked and not when the pair of
        readers is built, so the fake `tkinter` has to be in place for the whole
        act — and it is why this is a helper and not three lines in each test.
        """
        fake.simpledialog.answers = list(answers)
        with mock.patch.object(env, "GRACE", 0.0), mock.patch.dict(
                sys.modules, {"tkinter": fake}):
            return wizard.run_step("credential", *wizard._readers(fake.root))

    def test_the_credential_is_read_with_what_is_typed_hidden(self):
        # The screen's way of saying what `getpass` says in a terminal: a
        # credential is not for whoever is looking at the screen — **e a Chave Principal
        # de Acesso também não** (item 50): o reinício do provedor a pede, e ela
        # entra pelo MESMO diálogo escondido, duas vezes na primeira vez, porque
        # uma Chave Principal que sela não tem como ser conferida depois.
        fake, _ = self.window()
        self.person()
        self.machine()
        gate.remember(gate.GATE)

        code, _ = self.credential_step(
            fake, ["Rafael", NEW_CREDENTIAL, NEW_CREDENTIAL, PHRASE, PHRASE])

        self.assertEqual(code, OK)
        hidden = [kw.get("show") for _, kw in fake.simpledialog.asked]
        self.assertEqual(hidden, [None, "*", "*", "*", "*"],
                         "a credencial ou a Chave Principal foram lidas em claro")
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))

    def test_a_name_nobody_gave_is_answered_by_the_words_own_sentence(self):
        fake, _ = self.window()
        code, said = self.credential_step(fake, [""])
        self.assertEqual(code, USAGE)
        self.assertIn(i18n.tr("deploy.credential.ask"), said)

    def test_the_whole_sequence_is_walked_by_pressing_its_buttons(self):
        # The one test that walks §7 end to end through the WINDOW: the first
        # step runs and closes, the optional ones are passed without running
        # (they are a person's decision), and the last one runs and prints. The
        # person never sees anything the words did not print.
        self.person()
        self.machine()

        def urlopen(request, timeout=None):
            return Answer(200)

        posted = mock.patch.object(notifier.urllib.request, "urlopen", urlopen)
        posted.start()
        self.addCleanup(posted.stop)

        fake = FakeTkinter()
        with mock.patch.object(env, "GRACE", 0.0), mock.patch.dict(
                sys.modules, {"tkinter": fake}):
            walk = wizard.build(fake.root, ask=lambda q: "", secret=lambda q: PHRASE)

            fake.button(i18n.tr("deploy.wizard.run")).press()
            self.assertTrue(walk.closed, "`up` did not close over a standing machine")
            for _ in range(len(wizard.STEPS) - 1):
                fake.button(i18n.tr("deploy.wizard.next")).press()
            self.assertEqual(walk.index, len(wizard.STEPS) - 1)

            fake.button(i18n.tr("deploy.wizard.run")).press()

        self.assertIn(i18n.tr("services.notifier.delivered", topic=notifier.TOPIC,
                              detail="200"),
                      fake.area().content)

    def test_the_finish_button_is_the_last_steps_next_and_closes_the_window(self):
        self.machine()
        fake = FakeTkinter()
        closes = lambda *a, **kw: (OK, "")  # noqa: E731 — a step that closes
        with mock.patch.object(wizard, "run_step", closes), mock.patch.dict(
                sys.modules, {"tkinter": fake}):
            walk = wizard.build(fake.root, ask=lambda q: "", secret=lambda q: PHRASE)
            fake.button(i18n.tr("deploy.wizard.run")).press()
            for _ in range(len(wizard.STEPS) - 1):
                fake.button(i18n.tr("deploy.wizard.next")).press()
            self.assertTrue(walk.last)
            # The last step's forward button is `finish`, and finish is what
            # closes the window the person is done with.
            fake.button(i18n.tr("deploy.wizard.finish")).press()
        self.assertEqual(fake.root.destroys, 1)


# --------------------------------------------------------------- the door ---

class TheDoor(FolderCase):
    """`at-deploy` with no word — and the `Tk` that stepped aside.

    The Wizard of §7 is item 27's third slice, and it stays BUILT
    (`at_deploy/wizard.py`) but has NO CALLER while the `Tk` is off — the very
    decision `at-cli` took in item 9. So the door below has one shape only: a
    command with no word answers the help, and nothing opens a window. What the
    window would say is still proved below, over the module itself.
    """

    def test_the_wordless_command_answers_the_help(self):
        fake = FakeTkinter()
        with mock.patch.dict(sys.modules, {"tkinter": fake}):
            code, text = self.quiet(main, [])
        self.assertEqual(code, OK)
        self.assertEqual([widget for widget in fake.made if widget.kind != "root"],
                         [], "a janela abriu sobre um comando sem palavra")
        self.assertIn(i18n.tr("deploy.help.usage"), text)
        self.assertIn("credential", text)

    def test_the_window_still_separates_a_machine_with_no_tkinter(self):
        # O módulo fica, e com ele a frase que o item 27 escreveu: uma máquina
        # sem `tkinter` é avisada numa frase e não num traceback. Sem chamador
        # hoje, quem a exercita é este teste — e é o que mantém a decisão viva
        # para a fatia que trouxer o `Tk` de volta.
        with mock.patch.dict(sys.modules, {"tkinter": None}):
            opened, text = self.quiet(wizard.open_wizard)
        self.assertFalse(opened)
        self.assertIn(i18n.tr("wizard.unavailable", error=""), text)

    def test_the_window_still_separates_a_machine_with_no_display(self):
        # Um `Tk` que não abre — sem `$DISPLAY` — é a mesma resposta.
        fake = FakeTkinter()

        def refuse() -> object:
            raise fake.TclError("no display name and no $DISPLAY environment variable")

        fake.Tk = refuse
        with mock.patch.dict(sys.modules, {"tkinter": fake}):
            opened, text = self.quiet(wizard.open_wizard)
        self.assertFalse(opened)
        self.assertIn(i18n.tr("wizard.unavailable", error=""), text)

    def test_a_word_still_answers_a_word(self):
        fake = FakeTkinter()
        with mock.patch.dict(sys.modules, {"tkinter": fake}):
            code, text = self.quiet(main, ["help"])
        self.assertEqual(code, OK)
        self.assertEqual([widget for widget in fake.made if widget.kind != "root"],
                         [], "a janela abriu sobre uma palavra")
        self.assertIn("credential", text)


# ------------------------------------------------------------ the sentence ---

class TheSentenceOfTheStep(FolderCase):
    """The screen writes none of its own: what it says is what the word said."""

    def test_a_step_that_fails_says_what_the_word_said(self):
        code, said = wizard.run_step("notify")
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.notifier.no_token",
                              where=notifier.token_file(),
                              topic=notifier.TOPIC), said)


if __name__ == "__main__":
    unittest.main()
