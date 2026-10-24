"""Item 27's operator act: the gate's credential.

`services credential` is §7b's — who is an actor is AT's, how it is proved is
the gate's — and it is the act that makes the two meet: the row, the
`users.yml` derived from it, and the restart that makes the new derivation the
one Authelia proves.

The provider is a container, so what is provable here is everything around it:
the calls the act makes through the runtime's seam (`podman.exec`), the files
it leaves in the folder, and what it says. Nothing touches the network, and
nothing here starts a container.

The rule this file exists for: **the restart does not evict the sessions
already open**, because the session secret is drawn once and kept. It is a
security decision and it is recorded in §3; here it is measured off the folder.
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
from at.core import actors, boot, gate
from at.encryption import vault
from at_deploy import environment as env
from at_deploy import podman, vpn
from at_deploy.cli import OK, REFUSED, USAGE, main, services

# What the person types when the act asks for a credential.
CREDENTIAL = "uma-frase-bem-longa"
NEW_CREDENTIAL = "outra-frase-bem-longa"

# A Chave Principal que a suíte digita (item 50, §4). O reinício do provedor a
# pede — ele monta o `configuration.yml` de novo —, e é ela que sela os três
# valores que o provedor assina, cifra e prova.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"

# Every sentence the two acts say, in either language: the words of both doors,
# and the messages each act prints on the way out. A key the catalog does not
# have answers with the KEY itself, which is why this list exists — a message
# added to `environment.py` or `cli.py` without a line here is a message nobody
# checks.
SAID = (
    "deploy.credential.about", "deploy.credential.ask",
    "services.credential.changed", "services.credential.hosted",
    "services.credential.unknown", "services.credential.pending",
    "services.credential.no_tty", "services.credential.secret",
    "services.credential.again", "services.restarted",
)


class FakeRuntime:
    """The runtime's seam: every call it was given, and the ones it refuses.

    `fails` names WORDS a call must carry to fail, so ONE step of an act can
    refuse without taking the others with it — which is what makes each step's
    failure provable as its own thing. And `running` is what a container says
    about itself — with `fails=("inspect",)` being a container that was never
    there at all.
    """

    def __init__(self, fails: tuple[str, ...] = (), running: str = "true") -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.fails = fails
        self.running = running

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append((call, kw))
        failed = any(word in call for word in self.fails)
        if call[:2] == ["container", "inspect"]:
            return SimpleNamespace(returncode=1 if failed else 0,
                                   stdout="" if failed else self.running,
                                   stderr="")
        return SimpleNamespace(returncode=1 if failed else 0, stdout="", stderr="")

    def argv(self) -> list[list[str]]:
        return [call for call, _ in self.calls]

    def said(self) -> list[str]:
        """Every argument every call was given — where a value must NOT be."""
        return [part for call, _ in self.calls for part in call]

    def streams(self) -> list[str]:
        """What travelled on a command's STDIN — the only place a value may go."""
        return [str(kw.get("input", "")) for _, kw in self.calls]


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
        self.env.start()
        i18n.reset()
        # The machine has NO Podman, always, and for the reason the other two
        # deploy suites give: the day one is installed, a test that read the
        # real machine would pull images from the network. `machine()` is what
        # turns it on, per test.
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        # And the machine's low-port rule ALLOWS every port, for the reason the
        # environment's suite gives: a suite that read the real floor would
        # answer `1024` on this machine and refuse to bring anything up.
        self.floor = mock.patch.object(env, "floor", lambda: 0)
        self.floor.start()
        self.addCleanup(self.floor.stop)
        # And on no private network, so the site is the loop's (§7e has a suite
        # of its own).
        self.no_vpn = mock.patch.object(vpn, "run", side_effect=FileNotFoundError)
        self.no_vpn.start()
        self.addCleanup(self.no_vpn.stop)
        # **E a pessoa digita a Chave Principal**: o `up` e o reinício do provedor a leem
        # de um leitor sem eco, e a suíte entrega o dela.
        self.phrase = lambda question: PHRASE
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

    def standing(self) -> None:
        """The environment up for real: the gate's secret, the files, the pins.

        The act is only meaningful over a folder that HAS an environment — the
        `users.yml` the provider reads and the session secret it keeps are both
        written when the environment comes up — so every test below starts from
        that state instead of from a folder that only looks like one.
        """
        gate.remember(gate.GATE)
        self.machine()
        self.quiet(env.up, secret=self.phrase)

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()

    def key(self) -> bytes:
        """A chave derivada da Chave Principal da suíte — o que abre o que ela selou (§4).

        As duas pontas do notificador são seladas na pasta (item 50), e é com
        esta Chave que os testes leem o valor de volta: derivada da Chave Principal, e
        nunca de um segundo sorteio.
        """
        if not hasattr(self, "_key"):
            self._key = vault.vault_key(PHRASE)
        return self._key


# ---------------------------------------------------------- the gate ---

class TheGateCredential(FolderCase):
    """§7b: the row, the `users.yml` derived from it, and the restart."""

    def setUp(self):
        super().setUp()
        self.person()
        self.standing()

    def change(self, name: str = "Rafael", credential: str = NEW_CREDENTIAL,
               **kw):
        fake = self.machine(**kw)
        outcome, text = self.quiet(env.set_credential, name, credential,
                                   secret=self.phrase)
        return fake, outcome, text

    def users(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_USERS).read_text("utf-8")

    def test_the_row_is_rewritten_and_the_new_credential_is_the_one_that_opens(self):
        # The credential never lands in the row as typed: the engine derives it
        # on the way in, and the comparison is against the derivation.
        self.change()
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))
        self.assertIsNone(actors.authenticate("Rafael", CREDENTIAL))

    def test_the_derivation_the_gate_reads_is_the_one_the_row_now_holds(self):
        # The `users.yml` is the service's own writer, and the derivation in it
        # is the row's — a value that is only ever compared (§7b).
        before = self.users()
        self.change()
        after = self.users()
        self.assertNotEqual(before, after)
        self.assertIn(actors.named("Rafael")["credential"], after)
        self.assertNotIn(CREDENTIAL, after)
        self.assertIn("Rafael", after)

    def test_the_provider_is_started_again_so_the_file_is_the_one_it_reads(self):
        # Authelia reads `users.yml` at START: a derivation rewritten under a
        # standing container is a derivation nothing proves.
        fake, outcome, text = self.change()
        self.assertEqual(outcome, env.CREDENTIAL_CHANGED)
        calls = fake.argv()
        self.assertIn(["rm", "--force", env.container(env.IDENTITY)], calls)
        self.assertTrue(
            any(call[:2] == ["run", "--detach"]
                and call[call.index("--name") + 1] == env.container(env.IDENTITY)
                for call in calls),
            "the provider was not started again: it would keep proving the old file",
        )
        self.assertIn(i18n.tr("services.credential.changed", name="Rafael",
                              where=env.state(env.IDENTITY) / env.IDENTITY_USERS),
                      text)

    def test_without_the_phrase_the_row_changes_and_the_gate_stays_behind(self):
        # **A Chave Principal é o preço do reinício, e ele é declarado** (item 50): ele
        # monta o `configuration.yml` de novo, e o que a pasta guarda dos três
        # do provedor é o envelope. Sem Chave Principal o reinício não acontece — e o que
        # o ato deixa é o que o `PENDING` já dizia: a pasta tem a credencial
        # nova, o portão ainda prova a antiga.
        fake = self.machine()
        outcome, text = self.quiet(env.set_credential, "Rafael", NEW_CREDENTIAL)
        self.assertEqual(outcome, env.CREDENTIAL_PENDING)
        self.assertIn(i18n.tr("services.credential.pending", name="Rafael"), text)
        self.assertIn(i18n.tr("services.phrase.no_tty"), text)
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))
        self.assertFalse([call for call in fake.argv() if call[:1] == ["rm"]])

    def test_the_restart_does_not_pull_and_does_not_re_pin(self):
        # It is a restart and not `up`: the container was standing, so the image
        # is here — and the pin is a fact of the folder, not of this act.
        fake, _, _ = self.change()
        self.assertFalse([call for call in fake.argv() if call[:1] == ["pull"]])
        self.assertFalse(
            [call for call in fake.argv() if call[:1] == ["network"]])

    def test_the_session_secret_is_the_same_one_so_nobody_inside_is_logged_out(self):
        # §3's declared price, measured off the folder: the restart does not
        # evict the sessions already open. The secret is drawn once and kept
        # (`_drawn`), and it is what seals the session cookie — so the same
        # value across a restart keeps every session that was open, and the
        # registry those sessions live in is the folder's too.
        session = env.state(env.IDENTITY) / env.IDENTITY_SESSION
        before = session.read_text("utf-8")
        self.change()
        self.assertEqual(session.read_text("utf-8"), before)

    def test_a_provider_that_did_not_come_back_is_said_as_pending(self):
        # The row is the folder's and it is already the new one; the gate is
        # not. Saying "changed" here would be a lie about the door.
        _, outcome, text = self.change(fails=("--detach",))
        self.assertEqual(outcome, env.CREDENTIAL_PENDING)
        self.assertIn(i18n.tr("services.credential.pending", name="Rafael"), text)
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))

    def test_a_provider_that_never_stood_is_the_same_pending(self):
        # A container that was never there is not a restart: what brings it up
        # is `up`, with the pull and the pin — and until then the folder has the
        # new credential and the gate has none.
        _, outcome, text = self.change(fails=("inspect",))
        self.assertEqual(outcome, env.CREDENTIAL_PENDING)
        self.assertIn(i18n.tr("services.credential.pending", name="Rafael"), text)

    def test_a_pending_change_does_not_rewrite_the_derivation(self):
        # Nothing is proving the file, so nothing is rewritten for a provider
        # that is not there: `up` re-derives it from the row when it comes back.
        self.change(fails=("inspect",))
        self.assertNotIn(actors.named("Rafael")["credential"], self.users())

    def test_nobody_wearing_that_name_is_the_deploys_own_answer(self):
        _, outcome, _ = self.change(name="Ninguem")
        self.assertEqual(outcome, env.CREDENTIAL_UNKNOWN)

    def test_the_hosted_path_changes_the_row_and_has_no_gate_to_restart(self):
        # §3: Basic and Forms are the SAME credential — so on the hosted path
        # the act is complete without a container, and it is said.
        gate.remember(gate.FORMS)
        fake, outcome, text = self.change()
        self.assertEqual(outcome, env.CREDENTIAL_CHANGED)
        self.assertEqual(fake.calls, [])
        self.assertIn(i18n.tr("services.credential.hosted", name="Rafael"), text)
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))

    def test_giving_a_credential_to_somebody_who_had_none_is_the_same_act(self):
        # A person born through the table door carries no credential, and is
        # therefore not in the `users.yml` — the act is what they get.
        from at.core import tables

        tables.create("actor", {"name": "Ana", "type": "person"})
        self.assertNotIn("Ana", self.users())
        self.change(name="Ana")
        self.assertIn("Ana", self.users())
        self.assertIsNotNone(actors.authenticate("Ana", NEW_CREDENTIAL))


# ------------------------------------------------------------- the door ---

class TheDoor(FolderCase):
    """The credential word, reached the way a person reaches it."""

    def answer(self, *values: str):
        """A secret reader that hands over the values in order."""
        said = list(values)
        return lambda question: said.pop(0) if said else ""

    def test_the_credential_door_reads_it_twice_and_without_echo(self):
        # The two readers are the account's own (`at-cli admin`): the credential
        # does not travel through the command line, so it stays out of the
        # shell's history and out of anybody's `ps`.
        self.person()
        self.standing()
        asked: list[str] = []

        def secret(question: str) -> str:
            """A mesma pessoa digitando sem eco: a credencial nas perguntas dela,
            e a Chave Principal onde a Chave Principal é pedida — o reinício do provedor a pede, e
            ela entra pelo mesmo leitor (item 50, §4)."""
            if question == i18n.tr("services.phrase"):
                return PHRASE
            asked.append(question)
            return NEW_CREDENTIAL

        code, text = self.quiet(services, ["credential", "Rafael"],
                                ask=lambda question: "", secret=secret)
        self.assertEqual(code, OK)
        self.assertEqual(len(asked), 2)
        self.assertIn(i18n.tr("services.credential.secret"), asked)
        self.assertIn(i18n.tr("services.credential.again"), asked)
        self.assertIsNotNone(actors.authenticate("Rafael", NEW_CREDENTIAL))
        self.assertNotIn(NEW_CREDENTIAL, text)

    def test_a_mismatch_is_the_cores_own_refusal_and_changes_nothing(self):
        self.person()
        code, text = self.quiet(
            services, ["credential", "Rafael"],
            ask=lambda question: "",
            secret=self.answer(NEW_CREDENTIAL, "outra-coisa"),
        )
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("admin.error.mismatch"), text)
        self.assertIsNotNone(actors.authenticate("Rafael", CREDENTIAL))

    def test_a_credential_too_short_is_refused_by_the_rule_and_not_by_the_door(self):
        # §3: whoever asks does not get to decide the rule — the length is the
        # core's, and so is the sentence.
        self.person()
        code, text = self.quiet(
            services, ["credential", "Rafael"],
            ask=lambda question: "", secret=self.answer("curta", "curta"),
        )
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("admin.error.short", min=actors.MIN_CREDENTIAL), text)
        self.assertIsNotNone(actors.authenticate("Rafael", CREDENTIAL))

    def test_the_word_without_a_name_says_which_word_needs_one(self):
        code, text = self.quiet(services, ["credential"])
        self.assertEqual(code, USAGE)
        self.assertIn(i18n.tr("deploy.credential.ask"), text)

    def test_a_word_that_takes_no_argument_still_takes_none(self):
        for words in (["down", "extra"], ["credential", "a", "b"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_no_terminal_means_no_credential_to_change(self):
        # The suite runs with no tty, which is the state the door refuses in.
        self.person()
        code, text = self.quiet(main, ["container", "credential", "Rafael"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.credential.no_tty"), text)

    def test_a_name_nobody_wears_is_refused_in_the_deploys_words(self):
        self.person()
        code, text = self.quiet(
            services, ["credential", "Ninguem"],
            ask=lambda question: "", secret=self.answer(NEW_CREDENTIAL,
                                                        NEW_CREDENTIAL),
        )
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.credential.unknown", name="Ninguem"), text)


class TheWords(unittest.TestCase):
    """The door, and every sentence it says, in both languages."""

    def test_every_sentence_of_the_act_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the screen would show the key",
                    )


if __name__ == "__main__":
    unittest.main()
