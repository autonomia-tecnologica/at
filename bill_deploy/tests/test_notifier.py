"""§7f's delivery: Bill's credential in the notifier, the scope, and the push.

The notifier is a container, so what is provable here is everything around it:
the words the environment asks the notifier's own CLI with (`podman exec`, the
runtime's seam), the file the credential ends up in, and the POST an alert
leaves as. Nothing touches the network — the one call that would is patched, and
what the test reads is the REQUEST, which is where the delivery is readable.

The rule this file exists for is §3's: the credential Bill carries to the
service is delimited — it publishes to the topic and does nothing else — and it
is a secret, so it is never printed and never travels in an argv. Every test
below that touches it asserts one of those two.
"""

from __future__ import annotations

import io
import os
import stat
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from bill import i18n
from bill.core import boot
from bill_deploy import environment as env
from bill_deploy import notifier, podman

# The token the fake notifier draws: `tk_` and 32 characters, which is ntfy's own
# rule. The value is nobody's — what the tests read is where it was KEPT.
DRAWN_TOKEN = "tk_abcdefghijklmnopqrstuvwxyz012"

# What `ntfy token add` prints on its own line, measured against the image at the
# pin. The delivery reads the token out of it, so the shape is the contract.
TOKEN_LINE = f"token {DRAWN_TOKEN} created for user bill, never expires"

# Every sentence the delivery says out loud, in both languages. A key the catalog
# does not have answers with the key itself, which is why this list exists: a
# message added to `notifier.py` without a line here is a message nobody checks.
SAID = (
    "services.notifier.drawn", "services.notifier.not_ready",
    "services.notifier.undrawn", "services.notifier.no_token",
    "services.notifier.delivered", "services.notifier.undelivered",
    "services.notifier.test.title", "services.notifier.test.body",
    # §7f's other end: the phone's credential, and the two sentences that carry
    # it — one of them carrying the VALUE, which is what makes it the one
    # message of this product a person has to be able to read twice.
    "services.notifier.phone.drawn", "services.notifier.phone.held",
    "deploy.services.notify.about", "deploy.services.phone.about",
)


class Runtime:
    """The runtime's seam: the calls it was given, and the ones it refuses.

    `refuses` names WORDS a call must carry to fail, so one step of the delivery
    can refuse without taking the others with it — which is what makes each
    step's failure provable as its own thing. `ready` is the notifier's own
    database: the probe that waits for it is the only call it answers `no` to.
    """

    def __init__(self, refuses: tuple[str, ...] = (), ready: bool = True,
                 answer: str = TOKEN_LINE) -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.refuses = refuses
        self.ready = ready
        self.answer = answer

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append((call, kw))
        if "test" in call and not self.ready:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        failed = any(word in call for word in self.refuses)
        said = self.answer if "ntfy" in call and "token" in call else ""
        return SimpleNamespace(returncode=1 if failed else 0, stdout=said, stderr="")

    def argv(self) -> list[list[str]]:
        return [call for call, _ in self.calls]

    def said(self) -> list[str]:
        """Every argument every call was given — where the credential must NOT be."""
        return [part for call, _ in self.calls for part in call]

    def streams(self) -> list[str]:
        """What travelled on a command's STDIN — the only place a value may go."""
        return [str(kw.get("input", "")) for _, kw in self.calls]


class FolderCase(unittest.TestCase):
    """A scratch Working Folder, which is where every path below resolves to."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"BILL_ROOT": str(self.root), "BILL_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def runtime(self, **kw) -> Runtime:
        """A machine WITH a Podman, and a runtime that answers instead of doing."""
        fake = Runtime(**kw)
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
        """Run something and answer with what it printed."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


class Answer:
    """A stand-in for the notifier's HTTP answer."""

    def __init__(self, status: int = 200) -> None:
        self.status = status

    def __enter__(self) -> "Answer":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class TheCredential(FolderCase):
    """§3's delimited scope, and where the value it lives on is kept."""

    def test_the_file_sits_beside_the_notifiers_own_state(self):
        # §7: every service's persistent state lives in `App/services/<service>/`
        # — and it is the folder the container mounts and the backup covers.
        self.assertEqual(notifier.token_file(), env.state(env.NOTIFIER) / "token")

    def test_the_value_is_kept_at_0600_and_read_back_without_its_newline(self):
        # The interim while the vault does not exist (item 14): a file nobody but
        # the person can read.
        notifier.write_token(f"  {DRAWN_TOKEN}  ")
        self.assertEqual(stat.S_IMODE(notifier.token_file().stat().st_mode), 0o600)
        self.assertEqual(notifier.token(), DRAWN_TOKEN)

    def test_a_folder_with_no_credential_answers_none_and_not_an_empty_string(self):
        # `None` and not `""`: an empty file is nobody's credential, and the
        # caller has to be able to tell "there is none" from "there is one".
        self.assertIsNone(notifier.token())
        notifier.write_token("")
        self.assertIsNone(notifier.token())

    def test_the_scope_is_write_only_and_that_is_the_mirror_of_sections_sentence(self):
        # §3 delimits the scope of a service that talks to Bill; this is the
        # mirror — Bill talks to the service, and the credential publishes and
        # does nothing else. `read-write` here would make the scope decorative.
        self.assertEqual(notifier.SCOPE, "write-only")

    def test_the_target_is_the_topic_at_the_address_the_environment_publishes(self):
        # The address is the environment's own, and the two modes of it — where
        # the notifier listens and where Bill posts — cannot drift.
        self.assertEqual(notifier.target(), f"{env.notifier_url()}/{notifier.TOPIC}")
        self.assertEqual(notifier.target(),
                         f"http://{env.LOOP}:{env.NOTIFIER_PORT}/bill")


class TheProvision(FolderCase):
    """The credential is created by Bill, inside the notifier, once."""

    def setUp(self):
        super().setUp()
        self.secret = "uma-senha-sorteada-que-ninguem-guarda"
        self.drawn = mock.patch.object(notifier.secrets, "token_urlsafe",
                                       lambda size: self.secret)
        self.drawn.start()
        self.addCleanup(self.drawn.stop)

    def provision(self, **kw):
        fake = self.runtime(**kw)
        with mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(notifier.provision)
        return fake, outcome, text

    def test_the_credential_is_created_and_the_value_comes_from_the_notifier(self):
        # Bill never invents the token: ntfy draws it and prints it, and that line
        # is the one place Bill ever reads it (`token add` has no flag to set it).
        fake, outcome, text = self.provision()
        self.assertEqual(outcome, notifier.DRAWN)
        self.assertEqual(notifier.token(), DRAWN_TOKEN)
        self.assertIn(i18n.tr("services.notifier.drawn",
                              where=notifier.token_file(), topic=notifier.TOPIC,
                              scope=notifier.SCOPE), text)

    def test_the_scope_is_granted_in_ntfys_own_word(self):
        fake, _, _ = self.provision()
        self.assertIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy", "access",
                       notifier.USER, notifier.TOPIC, notifier.SCOPE], fake.argv())

    def test_the_command_gets_its_stdin_attached_and_that_is_measured(self):
        # `-i` is not decoration: MEASURED against the image at the pin, without
        # it the runtime does not attach the command's input and `ntfy user add`
        # dies with `inappropriate ioctl for device` instead of reading the
        # password — which is exactly where the password is supposed to travel.
        fake, _, _ = self.provision()
        cli = [call for call in fake.argv() if "ntfy" in call]
        self.assertEqual(len(cli), 4)  # remove, add, access and token add
        for call in cli:
            with self.subTest(call=call[:4]):
                self.assertEqual(call[:2], ["exec", "-i"])

    def test_the_account_is_removed_first_so_a_rotation_kills_the_old_credential(self):
        # A token file that went away is a rotation, and the only way the old
        # credential stops working is the account that carries it going with it.
        fake, _, _ = self.provision()
        removed = ["exec", "-i", env.container(env.NOTIFIER), "ntfy", "user",
                   "remove", notifier.USER]
        calls = fake.argv()
        self.assertIn(removed, calls)
        self.assertLess(calls.index(removed),
                        calls.index(["exec", "-i", env.container(env.NOTIFIER),
                                     "ntfy", "user", "add", "--role", "user",
                                     notifier.USER]))

    def test_the_password_travels_on_stdin_and_never_in_the_argv(self):
        # The argv is what the whole machine reads through `ps`, and the account's
        # password is handed over on the command's own input stream — where the
        # token never goes either, because ntfy draws it.
        fake, _, _ = self.provision()
        self.assertNotIn(self.secret, fake.said())
        self.assertTrue(any(self.secret in stream for stream in fake.streams()))
        self.assertNotIn(DRAWN_TOKEN, fake.said())

    def test_a_step_that_refuses_is_said_as_its_own_thing(self):
        # Each step of the four is provable on its own, and a step that refused
        # leaves no credential behind — a half-made one would be a file with a
        # token in it that authenticates nothing.
        for word in ("user", "access", "token"):
            with self.subTest(step=word):
                fake, outcome, text = self.provision(refuses=(word,))
                self.assertEqual(outcome, notifier.FAILED)
                self.assertIsNone(notifier.token())
                self.assertIn(f"ntfy {word}", text)

    def test_a_notifier_that_never_stands_is_said_and_not_guessed(self):
        # The CLI refuses to run before the server has written its database
        # (measured), so the delivery waits — and says so when it gives up.
        fake, outcome, text = self.provision(ready=False)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIsNone(notifier.token())
        self.assertIn(i18n.tr("services.notifier.not_ready",
                              where=f"{env.NOTIFIER_DATA}/{env.NOTIFIER_AUTH}"), text)
        self.assertNotIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy", "user",
                          "remove", notifier.USER], fake.argv())

    def test_a_credential_already_kept_is_left_alone(self):
        # The file is the truth, and a secret is not re-drawn behind the person's
        # back: whoever wants a new one deletes the file and brings the
        # environment up again.
        notifier.write_token(DRAWN_TOKEN)
        fake, outcome, _ = self.provision()
        self.assertEqual(outcome, notifier.HELD)
        self.assertEqual(fake.calls, [])
        self.assertEqual(notifier.token(), DRAWN_TOKEN)

    def test_the_line_the_notifier_prints_has_to_hold_a_token(self):
        # A CLI that answered something else is a credential that was not made —
        # and never a file with a sentence in it.
        fake, outcome, text = self.provision(answer="token: nada")
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIsNone(notifier.token())
        self.assertIn("ntfy token add", text)


class ThePush(FolderCase):
    """What actually pushes an alert: the POST, and what the phone receives."""

    def post(self, status: int = 200, boom: Exception | None = None):
        """A `urlopen` that answers instead of reaching the network."""
        sent: list[urllib.request.Request] = []

        def urlopen(request, timeout=None):
            sent.append(request)
            if boom is not None:
                raise boom
            if status >= 400:
                raise urllib.error.HTTPError(request.full_url, status,
                                             "recusado", {}, None)
            return Answer(status)

        patch = mock.patch.object(notifier.urllib.request, "urlopen", urlopen)
        patch.start()
        self.addCleanup(patch.stop)
        return sent

    def test_the_alert_is_a_post_on_the_topic_with_the_credential_beside_it(self):
        sent = self.post()
        notifier.write_token(DRAWN_TOKEN)
        ok, detail = notifier.publish("Bill", "corpo")
        self.assertTrue(ok)
        self.assertEqual(detail, "200")
        request = sent[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, notifier.target())
        self.assertEqual(request.data, b"corpo")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {DRAWN_TOKEN}")

    def test_the_alert_announces_itself_so_the_phone_notices_it(self):
        # At the default priority the message arrives silently on the phone, and
        # a message nobody notices is a message not delivered.
        sent = self.post()
        notifier.publish("Bill", "corpo")
        request = sent[0]
        self.assertEqual(request.get_header("Title"), "Bill")
        self.assertEqual(request.get_header("Priority"), notifier.PRIORITY)
        self.assertEqual(request.get_header("Tags"), notifier.TAGS)

    def test_push_says_what_the_notifier_answered_and_never_the_value(self):
        self.post()
        notifier.write_token(DRAWN_TOKEN)
        outcome, text = self.quiet(notifier.push, "Bill", "corpo")
        self.assertEqual(outcome, notifier.SENT)
        self.assertIn(i18n.tr("services.notifier.delivered", topic=notifier.TOPIC,
                              detail="200"), text)
        self.assertNotIn(DRAWN_TOKEN, text)

    def test_a_notifier_that_refuses_is_a_failure_and_not_a_crash(self):
        self.post(status=403)
        notifier.write_token(DRAWN_TOKEN)
        outcome, text = self.quiet(notifier.push, "Bill", "corpo")
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIn(i18n.tr("services.notifier.undelivered", detail="403"), text)

    def test_a_network_that_does_not_answer_is_the_same_kind_of_answer(self):
        # An alert that failed is not a crash: whoever asked for it decides what
        # to do about it (§7f: the delivery is the best-effort part).
        self.post(boom=urllib.error.URLError("recusado"))
        notifier.write_token(DRAWN_TOKEN)
        outcome, text = self.quiet(notifier.push, "Bill", "corpo")
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIn("recusado", text)

    def test_without_a_credential_nothing_is_sent_and_the_file_is_named(self):
        sent = self.post()
        outcome, text = self.quiet(notifier.push, "Bill", "corpo")
        self.assertEqual(outcome, notifier.NO_TOKEN)
        self.assertEqual(sent, [])
        self.assertIn(i18n.tr("services.notifier.no_token",
                              where=notifier.token_file(), topic=notifier.TOPIC), text)


class TheWords(unittest.TestCase):
    """Every sentence of the delivery, written in both languages."""

    def test_every_sentence_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the screen would show the key",
                    )


if __name__ == "__main__":
    unittest.main()
