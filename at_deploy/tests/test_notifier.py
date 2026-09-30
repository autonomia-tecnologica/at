"""§7f's delivery: AT's credential in the notifier, the scope, and the push.

The notifier is a container, so what is provable here is everything around it:
the words the environment asks the notifier's own CLI with (`podman exec`, the
runtime's seam), the file the credential ends up in, and the POST an alert
leaves as. Nothing touches the network — the one call that would is patched, and
what the test reads is the REQUEST, which is where the delivery is readable.

The rule this file exists for is §3's: the credential AT carries to the
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

from at import i18n
from at.core import boot, files
from at.encryption import vault
from at_deploy import environment as env
from at_deploy import notifier, podman, vpn

# The token the fake notifier draws: `tk_` and 32 characters, which is ntfy's own
# rule. The value is nobody's — what the tests read is where it was KEPT.
DRAWN_TOKEN = "tk_abcdefghijklmnopqrstuvwxyz012"

# A Chave Principal da suíte (item 50, §4). Ela é quem sela as duas pontas na
# pasta e quem as abre de volta, e é por isso que ela é uma só: um teste que
# lesse o valor selado com OUTRA Chave Principal não leria nada.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"

# What `ntfy token add` prints on its own line, measured against the image at the
# pin. The delivery reads the token out of it, so the shape is the contract.
TOKEN_LINE = f"token {DRAWN_TOKEN} created for user at, never expires"

# Every sentence the delivery says out loud, in both languages. A key the catalog
# does not have answers with the key itself, which is why this list exists: a
# message added to `notifier.py` without a line here is a message nobody checks.
SAID = (
    "services.notifier.drawn", "services.notifier.not_ready",
    "services.notifier.undrawn", "services.notifier.no_token",
    "services.notifier.unsealed",
    "services.notifier.delivered", "services.notifier.undelivered",
    "services.notifier.test.title", "services.notifier.test.body",
    "deploy.notify.about",
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
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.execution.cleanup()
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

    def key(self) -> bytes:
        """A chave derivada da Chave Principal da suíte — o que abre o que ela selou (§4).

        Derivada uma vez por teste: `vault.vault_key` custa o que a derivação de
        uma frase custa, e a mesma Chave Principal dentro do mesmo teste é a mesma Chave.
        """
        if not hasattr(self, "_key"):
            self._key = vault.vault_key(PHRASE)
        return self._key

    def opened(self, where: Path) -> str | None:
        """O valor CLARO que um arquivo da pasta guarda selado.

        Ele é lido ABRINDO o envelope com a Chave Principal da suíte, e nunca de um
        segundo sorteio: um valor sorteado de novo não provaria nada sobre o
        arquivo, e é o arquivo que estes testes leem.
        """
        envelope = where.read_text(encoding="utf-8").strip()
        return vault.unseal(envelope,
                            vault.derived_key(self.key(), notifier.VAULT_SCOPE))


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

    def test_the_value_is_kept_SEALED_at_0600_and_read_back_without_its_newline(self):
        # **O que a pasta guarda é o envelope** (item 50): um arquivo que ninguém
        # mais lê, e que nem a pessoa lê numa cópia da pasta — quem o abre é a
        # chave derivada, e é ela que faz uma pasta copiada publicar de novo.
        notifier.write_token(f"  {DRAWN_TOKEN}  ", self.key())
        where = notifier.token_file()
        kept = where.read_text(encoding="utf-8")
        self.assertEqual(stat.S_IMODE(where.stat().st_mode), 0o600)
        self.assertNotIn(DRAWN_TOKEN, kept)
        self.assertTrue(vault.envelopes(kept))
        self.assertEqual(self.opened(where), DRAWN_TOKEN)
        self.assertEqual(notifier.token(self.key()), DRAWN_TOKEN)

    def test_a_folder_with_no_credential_answers_none_and_not_an_empty_string(self):
        # `None` and not `""`: an empty file is nobody's credential, and the
        # caller has to be able to tell "there is none" from "there is one".
        self.assertFalse(notifier.has_token())
        self.assertIsNone(notifier.token(self.key()))
        files.atomic_write_text(notifier.token_file(), "")
        self.assertFalse(notifier.has_token())
        self.assertIsNone(notifier.token(self.key()))

    def test_a_value_born_before_the_seal_reads_back_as_itself(self):
        # **A pasta que nasceu antes do selo** — o corte `f` do item 50 é quem a
        # migra —, e a leitura não pode depender de o selo já ter acontecido: um
        # arquivo sem envelope É o valor, e é assim que a instância de hoje
        # continua entregando.
        files.atomic_write_text(notifier.token_file(), f"{DRAWN_TOKEN}\n")
        self.assertTrue(notifier.has_token())
        self.assertEqual(notifier.token(None), DRAWN_TOKEN)

    def test_a_sealed_value_does_not_open_without_the_key(self):
        # **Um envelope que ninguém abriu não vira cabeçalho**: a leitura
        # responde "não há com o que autenticar", e não manda o selo para o
        # notificador recusar — a alternativa que `push` recusa em voz alta.
        notifier.write_token(DRAWN_TOKEN, self.key())
        outra = vault.vault_key("outra frase de acesso, e ela e bem longa")
        self.assertIsNone(notifier.token(None))
        self.assertIsNone(notifier.token(outra))
        self.assertEqual(notifier.token(self.key()), DRAWN_TOKEN)

    def test_the_scope_is_read_write_since_the_edge_fronts_the_notifier(self):
        # §3 delimits the scope of a service that talks to AT; this is the
        # mirror — AT talks to the service, and the credential is the ONE the
        # edge's M2M swap authenticates as for everybody, so it has to both
        # publish and read.
        self.assertEqual(notifier.SCOPE, "read-write")

    def test_the_target_is_the_topic_at_the_address_the_environment_publishes(self):
        # The address is the environment's own, and the two modes of it — where
        # the notifier listens and where AT posts — cannot drift.
        self.assertEqual(notifier.target(), f"{env.notifier_url()}/{notifier.TOPIC}")
        self.assertEqual(notifier.target(),
                         f"http://{env.LOOP}:{env.NOTIFIER_PORT}/at")

    def test_the_delivery_stays_on_the_loop_even_on_a_private_network(self):
        # **A entrega fica no LAÇO, mesmo numa rede privada** (esta fatia): o
        # notificador não sai mais para fora dele — quem chega de fora passa
        # pela borda —, então esta porta só precisa responder a ESTA máquina,
        # que é o laço sempre. O endereço continua CRU: sem nome, sem borda e
        # sem o certificado do AT no caminho, que é a propriedade que
        # `notifier_url` existe para guardar.
        network = "100.64.0.1"
        with mock.patch.object(vpn, "address", lambda call=None: network):
            self.assertEqual(env.notifier_url(),
                             f"http://{env.LOOP}:{env.NOTIFIER_PORT}")
            self.assertEqual(
                notifier.target(),
                f"http://{env.LOOP}:{env.NOTIFIER_PORT}/{notifier.TOPIC}")


class TheProvision(FolderCase):
    """The credential is created by AT, inside the notifier, once.

    **The password is not drawn here any more.** Caddy's own M2M credential is
    what `provision` hands `ntfy user add` (`environment.notify_gate_password`)
    — drawn before any container exists, exactly as `up` draws it — so every
    test below draws it first, the way `up` would.
    """

    def setUp(self):
        super().setUp()
        self.secret = "uma-senha-sorteada-que-ninguem-guarda"
        self.drawn = mock.patch.object(env.secrets, "token_urlsafe",
                                       lambda size: self.secret)
        self.drawn.start()
        self.addCleanup(self.drawn.stop)

    def provision(self, **kw):
        fake = self.runtime(**kw)
        env.draw_notify_gate(self.key())
        with mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(notifier.provision, self.key())
        return fake, outcome, text

    def test_the_credential_is_created_and_the_value_comes_from_the_notifier(self):
        # AT never invents the token: ntfy draws it and prints it, and that line
        # is the one place AT ever reads it (`token add` has no flag to set it).
        fake, outcome, text = self.provision()
        self.assertEqual(outcome, notifier.DRAWN)
        self.assertEqual(notifier.token(self.key()), DRAWN_TOKEN)
        self.assertIn(i18n.tr("services.notifier.drawn",
                              where=notifier.token_file(), topic=notifier.TOPIC,
                              scope=notifier.SCOPE), text)
        # **E o que fica na pasta é o ENVELOPE** (item 50): o valor não se lê
        # numa cópia da pasta, e quem o abre é a Chave Principal — a mesma que o `up` pede
        # porque esta credencial é um dos arquivos que faltam.
        kept = notifier.token_file().read_text(encoding="utf-8")
        self.assertNotIn(DRAWN_TOKEN, kept)
        self.assertTrue(vault.envelopes(kept))

    def test_a_draw_without_the_phrase_is_refused_and_leaves_nothing(self):
        # Um sorteio SELA, e sem Chave não há selo: gravar o valor em claro seria
        # o que este item existe para não haver. É a recusa que o `up` torna
        # inalcançável — ele pede a Chave Principal quando a credencial falta (`_drawn_files`).
        fake = self.runtime()
        outcome, text = self.quiet(notifier.provision, None)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertFalse(notifier.has_token())
        self.assertIn(i18n.tr("services.notifier.unsealed",
                              where=notifier.token_file()), text)
        self.assertEqual(fake.calls, [])

    def test_a_draw_with_no_m2m_credential_yet_is_refused(self):
        # A ordem que `up` sempre segue — a M2M do Caddy nasce ANTES de
        # qualquer container — não é garantida por este teste sozinho, então
        # `provision` tem de recusar em voz alta se ela faltar, e não sortear
        # uma senha às pressas que o Caddyfile já escrito não teria.
        fake = self.runtime()
        with mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(notifier.provision, self.key())
        self.assertEqual(outcome, notifier.FAILED)
        self.assertFalse(notifier.has_token())
        self.assertIn(i18n.tr("services.notifier.unsealed",
                              where=env.notify_gate_file()), text)
        self.assertFalse(
            [call for call in fake.argv() if call[:2] == ["exec", "-i"]])

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
                self.assertIsNone(notifier.token(self.key()))
                self.assertIn(f"ntfy {word}", text)

    def test_a_notifier_that_never_stands_is_said_and_not_guessed(self):
        # The CLI refuses to run before the server has written its database
        # (measured), so the delivery waits — and says so when it gives up.
        fake, outcome, text = self.provision(ready=False)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIsNone(notifier.token(self.key()))
        self.assertIn(i18n.tr("services.notifier.not_ready",
                              where=f"{env.NOTIFIER_DATA}/{env.NOTIFIER_AUTH}"), text)
        self.assertNotIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy", "user",
                          "remove", notifier.USER], fake.argv())

    def test_a_credential_already_kept_is_left_alone(self):
        # The file is the truth, and a secret is not re-drawn behind the person's
        # back: whoever wants a new one deletes the file and brings the
        # environment up again.
        notifier.write_token(DRAWN_TOKEN, self.key())
        fake, outcome, _ = self.provision()
        self.assertEqual(outcome, notifier.HELD)
        self.assertEqual(fake.calls, [])
        self.assertEqual(notifier.token(self.key()), DRAWN_TOKEN)

    def test_the_line_the_notifier_prints_has_to_hold_a_token(self):
        # A CLI that answered something else is a credential that was not made —
        # and never a file with a sentence in it.
        fake, outcome, text = self.provision(answer="token: nada")
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIsNone(notifier.token(self.key()))
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
        notifier.write_token(DRAWN_TOKEN, self.key())
        ok, detail = notifier.publish("AT", "corpo", self.key())
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
        notifier.publish("AT", "corpo", self.key())
        request = sent[0]
        self.assertEqual(request.get_header("Title"), "AT")
        self.assertEqual(request.get_header("Priority"), notifier.PRIORITY)
        self.assertEqual(request.get_header("Tags"), notifier.TAGS)

    def test_push_says_what_the_notifier_answered_and_never_the_value(self):
        self.post()
        notifier.write_token(DRAWN_TOKEN, self.key())
        outcome, text = self.quiet(notifier.push, "AT", "corpo",
                                           lambda question: PHRASE)
        self.assertEqual(outcome, notifier.SENT)
        self.assertIn(i18n.tr("services.notifier.delivered", topic=notifier.TOPIC,
                              detail="200"), text)
        self.assertNotIn(DRAWN_TOKEN, text)

    def test_a_notifier_that_refuses_is_a_failure_and_not_a_crash(self):
        self.post(status=403)
        notifier.write_token(DRAWN_TOKEN, self.key())
        outcome, text = self.quiet(notifier.push, "AT", "corpo",
                                           lambda question: PHRASE)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIn(i18n.tr("services.notifier.undelivered", detail="403"), text)

    def test_a_network_that_does_not_answer_is_the_same_kind_of_answer(self):
        # An alert that failed is not a crash: whoever asked for it decides what
        # to do about it (§7f: the delivery is the best-effort part).
        self.post(boom=urllib.error.URLError("recusado"))
        notifier.write_token(DRAWN_TOKEN, self.key())
        outcome, text = self.quiet(notifier.push, "AT", "corpo",
                                           lambda question: PHRASE)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIn("recusado", text)

    def test_without_a_credential_nothing_is_sent_and_the_file_is_named(self):
        sent = self.post()
        outcome, text = self.quiet(notifier.push, "AT", "corpo",
                                           lambda question: PHRASE)
        self.assertEqual(outcome, notifier.NO_TOKEN)
        self.assertEqual(sent, [])
        self.assertIn(i18n.tr("services.notifier.no_token",
                              where=notifier.token_file(), topic=notifier.TOPIC), text)

    def test_without_the_phrase_the_alert_does_not_go_out(self):
        # **O preço, dito** (§7f, item 50): a credencial está SELADA na pasta, e
        # quem a abre é a Chave Principal. Sem terminal não se pergunta, e o alerta não sai
        # — a entrega é a parte de melhor esforço, e um alerta que não sai é um
        # alerta que não sai. O que ele NÃO faz é mandar o envelope no cabeçalho
        # para o notificador recusar.
        sent = self.post()
        notifier.write_token(DRAWN_TOKEN, self.key())
        envelope = notifier.token_file().read_text(encoding="utf-8").strip()
        outcome, text = self.quiet(notifier.push, "AT", "corpo")
        self.assertEqual(outcome, notifier.FAILED)
        self.assertEqual(sent, [])
        self.assertIn(i18n.tr("services.phrase.no_tty"), text)
        self.assertNotIn(envelope, text)


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
