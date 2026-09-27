"""Item 27's operator acts: the phone's credential, and the gate's.

Two things the environment has and had no door for, and each one is the other
end of something already built. `services phone` is §7f's read end — AT
publishes, the phone reads — and it is the one value this product PRINTS, once,
because it has to reach a phone. `services credential` is §7b's — who is an
actor is AT's, how it is proved is the gate's — and it is the act that makes
the two meet: the row, the `users.yml` derived from it, and the restart that
makes the new derivation the one Authelia proves.

The notifier is a container and the provider is one, so what is provable here is
everything around them: the calls the acts make through the runtime's seam
(`podman.exec`), the files they leave in the folder, and what each one says.
Nothing touches the network, and nothing here starts a container.

The two rules this file exists for: **the value travels to the phone and to
nowhere else** — printed once, never in an argv, never a second time —, and
**the restart does not evict the sessions already open**, because the session
secret is drawn once and kept. The second one is a security decision and it is
recorded in §3; here it is measured off the folder.
"""

from __future__ import annotations

import io
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import actors, boot, gate
from at_deploy import environment as env
from at_deploy import notifier, podman, vpn
from at_deploy.cli import OK, REFUSED, USAGE, services, main

# The token the fake notifier draws: `tk_` and 32 characters, which is ntfy's
# own rule. The value is nobody's — what the tests read is where it WENT.
DRAWN_TOKEN = "tk_abcdefghijklmnopqrstuvwxyz012"

# What `ntfy token add` prints on its own line, for the phone's account.
TOKEN_LINE = f"token {DRAWN_TOKEN} created for user phone, never expires"

# What the person types when the act asks for a credential.
CREDENTIAL = "uma-frase-bem-longa"
NEW_CREDENTIAL = "outra-frase-bem-longa"

# A Frase de Acesso que a suíte digita (item 50, §4). O reinício do provedor a
# pede — ele monta o `configuration.yml` de novo —, e é ela que sela os três
# valores que o provedor assina, cifra e prova.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"

# Every sentence the two acts say, in either language: the words of both doors,
# and the messages each act prints on the way out. A key the catalog does not
# have answers with the KEY itself, which is why this list exists — a message
# added to `notifier.py`, `environment.py` or `cli.py` without a line here is a
# message nobody checks.
SAID = (
    "deploy.services.phone.about", "deploy.services.credential.about",
    "deploy.services.credential.ask",
    "services.notifier.phone.drawn", "services.notifier.phone.held",
    "services.notifier.phone.at", "services.notifier.phone.absent",
    # §7f's read, proved at the end of the word: what closing looks like, and the
    # two sentences that name the half which did not close.
    "services.notifier.phone.proved", "services.notifier.phone.unread",
    "services.notifier.phone.unrefused",
    "services.credential.changed", "services.credential.hosted",
    "services.credential.unknown", "services.credential.pending",
    "services.credential.no_tty", "services.credential.secret",
    "services.credential.again", "services.restarted",
)


class FakeRuntime:
    """The runtime's seam: every call it was given, and the ones it refuses.

    `fails` names WORDS a call must carry to fail, so ONE step of an act can
    refuse without taking the others with it — which is what makes each step's
    failure provable as its own thing. The notifier's own CLI is answered here
    too, for the reason everything else is: the token is a value the act reads
    off the command's output. And two questions are answered by their own
    switches instead of by a word: `ready` is the notifier's database (the probe
    that waits for it), and `running` is what a container says about itself —
    with `fails=("inspect",)` being a container that was never there at all.
    """

    def __init__(self, fails: tuple[str, ...] = (), running: str = "true",
                 ready: bool = True, answer: str = TOKEN_LINE) -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.fails = fails
        self.running = running
        self.ready = ready
        self.answer = answer

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append((call, kw))
        failed = any(word in call for word in self.fails)
        if call[:2] == ["container", "inspect"]:
            return SimpleNamespace(returncode=1 if failed else 0,
                                   stdout="" if failed else self.running,
                                   stderr="")
        if "test" in call:
            # The notifier's own database. This answer comes BEFORE the words:
            # the path it probes ends in `user.db`, and a test refusing the
            # `user` step must not be read as a notifier that never stood.
            return SimpleNamespace(returncode=0 if self.ready else 1,
                                   stdout="", stderr="")
        said = self.answer if "ntfy" in call and "token" in call else ""
        return SimpleNamespace(returncode=1 if failed else 0, stdout=said, stderr="")

    def argv(self) -> list[list[str]]:
        return [call for call, _ in self.calls]

    def said(self) -> list[str]:
        """Every argument every call was given — where a value must NOT be."""
        return [part for call, _ in self.calls for part in call]

    def streams(self) -> list[str]:
        """What travelled on a command's STDIN — the only place a value may go."""
        return [str(kw.get("input", "")) for _, kw in self.calls]


class FakeEdge:
    """A borda, sem socket — o seam `gate.Answer` da prova do celular (§7f).

    Ela responde pelo NOME: o pedido que traz o token do celular no cabeçalho lê
    o tópico, e o que não traz nenhum é recusado — as duas metades que a palavra
    `phone` prova. Cada metade tem a sua resposta, para que os dois defeitos
    possam ser encenados: um token que não lê, e um notificador que responde a
    quem não traz token nenhum. `nothing` é a borda que não respondeu: "não deu
    para saber", que não é prova de nada.
    """

    def __init__(self, read: int = 200, refused: int = 403,
                 nothing: bool = False) -> None:
        self.read = read
        self.refused = refused
        self.nothing = nothing
        self.asked: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> int | None:
        self.asked.append((url, dict(headers)))
        if self.nothing:
            return None
        return self.read if headers.get("Authorization") else self.refused

    def urls(self) -> list[str]:
        return [url for url, _ in self.asked]

    def headers(self) -> list[dict[str, str]]:
        return [headers for _, headers in self.asked]


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
        # And on no private network, so the site and the notifier's URL are the
        # loop's (§7e has a suite of its own).
        self.no_vpn = mock.patch.object(vpn, "run", side_effect=FileNotFoundError)
        self.no_vpn.start()
        self.addCleanup(self.no_vpn.stop)
        # **E a pessoa digita a Frase**: o `up` e o reinício do provedor a leem
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


# ------------------------------------------------------------ the phone ---

class TheReadToken(FolderCase):
    """§7f's other end: the phone's credential, drawn once and printed once."""

    def setUp(self):
        super().setUp()
        self.secret = "uma-senha-do-celular-que-ninguem-guarda"
        drawn = mock.patch.object(notifier.secrets, "token_urlsafe",
                                  lambda size: self.secret)
        drawn.start()
        self.addCleanup(drawn.stop)

    def subscribe(self, edge: FakeEdge | None = None, **kw):
        fake = self.machine(**kw)
        with mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(notifier.subscribe,
                                       edge if edge is not None else FakeEdge())
        return fake, outcome, text

    def test_the_two_ends_of_the_acl_are_two_accounts_with_two_scopes(self):
        # §6: "AT publishes, the phone reads, and neither token serves for
        # anything else". ntfy's access is per user AND per topic, so one
        # account cannot be both at once — the two ends are two credentials.
        self.assertNotEqual(notifier.PHONE_USER, notifier.USER)
        self.assertEqual(notifier.SCOPE, "write-only")
        self.assertEqual(notifier.PHONE_SCOPE, "read-only")

    def test_the_phone_gets_its_own_account_with_the_read_scope_on_the_topic(self):
        fake, outcome, _ = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_DRAWN)
        self.assertIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy",
                       "access", notifier.PHONE_USER, notifier.TOPIC,
                       notifier.PHONE_SCOPE], fake.argv())
        self.assertIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy",
                       "user", "add", "--role", "user", notifier.PHONE_USER],
                      fake.argv())

    def test_the_value_is_printed_once_and_it_is_the_one_the_notifier_drew(self):
        # The token has to reach a phone, and the only road there is the
        # person's eyes: this is the one message of the product that carries a
        # credential, and it carries it because there is no other way it could
        # travel.
        _, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_DRAWN)
        self.assertIn(DRAWN_TOKEN, text)
        # What a person needs beside the value: where the alert comes from, and
        # which topic to subscribe to.
        self.assertIn(notifier.TOPIC, text)
        # O endereço que vai para o celular é o NOME — e não o laço, que é onde
        # o AT publica e onde nenhum celular chega.
        self.assertIn(env.notifier_public_url(), text)
        self.assertNotIn(env.notifier_url(), text)

    def test_the_message_names_the_certificate_the_app_must_import(self):
        # **O certificado é do AT, e o app do ntfy não usa o cofre do aparelho**
        # (medido: no Android um app moderno ignora a CA que a pessoa instalou no
        # sistema, e o app do ntfy tem a gestão de certificados dele). Então a
        # mensagem não diz só para onde apontar: ela diz QUAL arquivo importar, e
        # onde — sem isso a pessoa chega no aparelho e leva um erro de TLS sem
        # saber que arquivo é.
        _, _, text = self.subscribe()
        self.assertIn(str(env.authority_file()), text)
        # E o arquivo é a CA que a borda emite, dentro da pasta de estado do
        # serviço — a pasta que o backup cobre.
        self.assertEqual(env.authority_file(),
                         env.state(env.CADDY) / env.CADDY_STORAGE
                         / "pki" / "authorities" / "local" / "root.crt")

    def test_a_second_run_still_names_the_road_and_the_certificate(self):
        # A segunda rodada não imprime o valor, e continua dizendo o que fazer no
        # aparelho: quem reabre isto é quem está com o celular na mão.
        self.subscribe()
        _, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_HELD)
        self.assertIn(env.notifier_public_url(), text)
        self.assertIn(str(env.authority_file()), text)

    def test_the_value_lands_in_a_file_at_0600_beside_the_notifiers_state(self):
        self.subscribe()
        where = notifier.phone_file()
        self.assertEqual(where, env.state(env.NOTIFIER) / "phone-token")
        self.assertEqual(stat.S_IMODE(where.stat().st_mode), 0o600)
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)

    def test_a_second_run_never_prints_the_value_again(self):
        # The rule is once, and it is the rule because the value came out in a
        # scrollback the first time: what is kept is what the phone kept, and
        # the file is where a person reads it a second time.
        self.subscribe()
        fake, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_HELD)
        self.assertNotIn(DRAWN_TOKEN, text)
        self.assertIn(str(notifier.phone_file()), text)
        self.assertEqual(fake.calls, [])
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)

    def test_the_value_never_travels_in_an_argv(self):
        # The argv is what the whole machine reads through `ps`, and the
        # account's password goes on the command's own input stream — the token
        # is drawn inside the container and never typed anywhere.
        fake, _, _ = self.subscribe()
        self.assertNotIn(DRAWN_TOKEN, fake.said())
        self.assertNotIn(self.secret, fake.said())
        self.assertTrue(any(self.secret in stream for stream in fake.streams()))

    def test_the_account_is_removed_first_so_a_rotation_kills_the_old_value(self):
        # Deleting the file and running again IS a rotation, and the only way
        # the value it replaced stops working is the account that carries it
        # going with it.
        fake, _, _ = self.subscribe()
        calls = fake.argv()
        removed = ["exec", "-i", env.container(env.NOTIFIER), "ntfy", "user",
                   "remove", notifier.PHONE_USER]
        self.assertIn(removed, calls)
        self.assertLess(calls.index(removed), len(calls))

    def test_deleting_the_file_is_the_way_to_a_new_credential(self):
        self.subscribe()
        notifier.phone_file().unlink()
        _, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_DRAWN)
        self.assertIn(DRAWN_TOKEN, text)
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)

    def test_a_step_that_refuses_is_said_and_leaves_nothing_behind(self):
        # A half-made credential would be a file with a token in it that
        # authenticates nothing.
        for word in ("user", "access", "token"):
            with self.subTest(step=word):
                notifier.phone_file().unlink(missing_ok=True)
                _, outcome, text = self.subscribe(fails=(word,))
                self.assertEqual(outcome, notifier.FAILED)
                self.assertIsNone(notifier.phone_token())
                self.assertIn(f"ntfy {word}", text)

    def test_a_notifier_that_never_stands_is_said_and_not_guessed(self):
        # The CLI refuses to run before the server has written its database
        # (measured), so the act waits — and says so when it gives up.
        _, outcome, text = self.subscribe(ready=False)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIsNone(notifier.phone_token())
        self.assertIn(i18n.tr("services.notifier.not_ready",
                              where=f"{env.NOTIFIER_DATA}/{env.NOTIFIER_AUTH}"),
                      text)

    def test_a_machine_with_no_runtime_is_told_the_two_ways_out_and_not_made_to_wait(self):
        # The operator's word is reachable before the environment ever stood, so
        # a machine with no Podman has nothing to wait for — the wait would be
        # ten seconds of asking a runtime that is not there.
        outcome, text = self.quiet(notifier.subscribe)
        self.assertEqual(outcome, notifier.FAILED)
        self.assertIn(i18n.tr("services.no_podman.status"), text)
        self.assertIsNone(notifier.phone_token())

    def test_the_status_report_names_the_file_and_never_the_value(self):
        self.subscribe()
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.notifier.phone.at",
                              where=notifier.phone_file(), topic=notifier.TOPIC,
                              scope=notifier.PHONE_SCOPE), text)
        self.assertNotIn(DRAWN_TOKEN, text)

    def test_the_delivery_still_uses_bills_own_credential(self):
        # The two ends do not borrow each other: the phone's token is drawn and
        # the write end is untouched — and a folder with only the phone's is a
        # folder AT cannot publish from.
        self.subscribe()
        self.assertIsNone(notifier.token())
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)


class TheReadProved(FolderCase):
    """A leitura do celular, provada pelo NOME — com o token e sem ele.

    `TheReadToken` prova que o token nasce e fica guardado; isto prova o que a
    ponta da ACL precisa dizer, e que um arquivo com um token dentro não é a
    mesma coisa: o celular não é a máquina onde o ambiente roda, então a palavra
    `phone` pergunta à BORDA, pelo nome que o aparelho vai digitar, e diz o que
    não fechou. As duas metades são o token lendo e o token sendo a porta.
    """

    def setUp(self):
        super().setUp()
        self.secret = "uma-senha-do-celular-que-ninguem-guarda"
        drawn = mock.patch.object(notifier.secrets, "token_urlsafe",
                                  lambda size: self.secret)
        drawn.start()
        self.addCleanup(drawn.stop)

    def subscribe(self, edge: FakeEdge | None = None, **kw):
        fake = self.machine(**kw)
        edge = edge if edge is not None else FakeEdge()
        with mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(notifier.subscribe, edge)
        return fake, edge, outcome, text

    def test_without_a_seam_the_question_goes_through_the_edge(self):
        # **O transporte padrão é o do AMBIENTE e não o do portão** (`gate.real`),
        # e a diferença é medido: o nome do celular não é resolvido pela máquina
        # que roda o comando — o resolver dela não é o do aparelho —, então o
        # `gate.real` responderia "não deu para saber" sobre uma borda de pé.
        asked: list[str] = []

        def edge(url: str, headers: dict[str, str]) -> int:
            asked.append(url)
            return 200 if headers.get("Authorization") else 403

        self.machine()
        with mock.patch.object(env, "through_edge", edge), \
                mock.patch.object(env, "GRACE", 0.0):
            outcome, _ = self.quiet(notifier.subscribe)
        self.assertEqual(outcome, notifier.PHONE_DRAWN)
        self.assertEqual(asked, [notifier.phone_url()] * 2)

    def test_the_two_halves_are_asked_by_the_name_and_never_on_the_loop(self):
        # **A estrada que se prova é a do aparelho.** O laço é a estrada do AT
        # (`target`), que funciona por construção e não diria nada sobre o
        # celular; o nome, na borda, é o que a pessoa digita no app.
        _, edge, _, _ = self.subscribe()
        self.assertEqual(edge.urls(), [notifier.phone_url()] * 2)
        for url in edge.urls():
            self.assertTrue(url.startswith(env.notifier_public_url()), url)
            self.assertNotIn(env.notifier_url(), url)

    def test_the_token_travels_in_the_header_and_never_in_an_argv_or_a_url(self):
        # A mesma regra da entrega: o argv é um `ps` na máquina, e uma URL vai
        # parar no log de quem quer que esteja no caminho.
        fake, edge, _, _ = self.subscribe()
        self.assertEqual(edge.headers()[0].get("Authorization"),
                         f"Bearer {DRAWN_TOKEN}")
        self.assertEqual(edge.headers()[1], {})
        self.assertNotIn(DRAWN_TOKEN, fake.said())
        self.assertNotIn(DRAWN_TOKEN, "".join(edge.urls()))

    def test_the_two_halves_closing_is_what_proves_the_read(self):
        _, edge, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_DRAWN)
        self.assertTrue(notifier.proved(edge))
        self.assertIn(i18n.tr("services.notifier.phone.proved",
                              url=notifier.phone_url(), topic=notifier.TOPIC),
                      text)

    def test_a_token_that_does_not_read_is_said_and_the_word_is_a_refusal(self):
        # O token fica — ele foi sorteado, e o arquivo é dele —, e o que não
        # fechou é a leitura. A palavra promete a leitura, então ela recusa.
        _, _, outcome, text = self.subscribe(FakeEdge(read=403))
        self.assertEqual(outcome, notifier.PHONE_UNPROVED)
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)
        self.assertIn(i18n.tr("services.notifier.phone.unread",
                              url=notifier.phone_url(), topic=notifier.TOPIC,
                              host=env.notifier_host(),
                              authority=env.authority_file(),
                              code=notifier.NO_TOKEN_REFUSED), text)

    def test_a_notifier_that_answers_whoever_comes_is_not_a_door(self):
        # Um `200` a quem não traz token nenhum é o notificador aberto, e é o
        # defeito que a metade do `deny-all` existe para pegar: sem ela, "o
        # celular lê" estaria provado num serviço que qualquer um lê.
        _, _, outcome, text = self.subscribe(FakeEdge(refused=200))
        self.assertEqual(outcome, notifier.PHONE_UNPROVED)
        self.assertIn(i18n.tr("services.notifier.phone.unrefused",
                              url=notifier.phone_url(), topic=notifier.TOPIC,
                              code=notifier.NO_TOKEN_REFUSED), text)
        self.assertNotIn(i18n.tr("services.notifier.phone.proved",
                                 url=notifier.phone_url(), topic=notifier.TOPIC),
                         text)

    def test_an_edge_that_does_not_answer_proves_nothing(self):
        # "Não deu para saber" não é "provado" — a mesma regra da virada (§6).
        _, _, outcome, text = self.subscribe(FakeEdge(nothing=True))
        self.assertEqual(outcome, notifier.PHONE_UNPROVED)
        self.assertIn(i18n.tr("services.notifier.phone.unread",
                              url=notifier.phone_url(), topic=notifier.TOPIC,
                              host=env.notifier_host(),
                              authority=env.authority_file(),
                              code=notifier.NO_TOKEN_REFUSED), text)

    def test_a_second_run_proves_the_read_again_and_prints_no_value(self):
        self.subscribe()
        _, _, outcome, text = self.subscribe()
        self.assertEqual(outcome, notifier.PHONE_HELD)
        self.assertNotIn(DRAWN_TOKEN, text)
        self.assertIn(i18n.tr("services.notifier.phone.proved",
                              url=notifier.phone_url(), topic=notifier.TOPIC),
                      text)


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
        # **A Frase é o preço do reinício, e ele é declarado** (item 50): ele
        # monta o `configuration.yml` de novo, e o que a pasta guarda dos três
        # do provedor é o envelope. Sem Frase o reinício não acontece — e o que
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
    """The two words, reached the way a person reaches them."""

    def setUp(self):
        super().setUp()
        self.secret = "uma-senha-do-celular-que-ninguem-guarda"
        drawn = mock.patch.object(notifier.secrets, "token_urlsafe",
                                  lambda size: self.secret)
        drawn.start()
        self.addCleanup(drawn.stop)

    def answer(self, *values: str):
        """A secret reader that hands over the values in order."""
        said = list(values)
        return lambda question: said.pop(0) if said else ""

    def test_the_phone_door_answers_ok_and_draws_the_credential(self):
        self.machine()
        with mock.patch.object(env, "GRACE", 0.0):
            code, text = self.quiet(services, ["phone"], answer=FakeEdge())
        self.assertEqual(code, OK)
        self.assertIn(DRAWN_TOKEN, text)
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)

    def test_the_phone_door_is_a_refusal_when_the_credential_is_not_made(self):
        self.machine(fails=("access",))
        with mock.patch.object(env, "GRACE", 0.0):
            code, _ = self.quiet(services, ["phone"], answer=FakeEdge())
        self.assertEqual(code, REFUSED)

    def test_the_phone_door_is_a_refusal_when_the_read_is_not_proved(self):
        # A palavra promete a LEITURA, e não o arquivo: um token que não lê pelo
        # nome é uma credencial sorteada e um celular que não alcança o tópico —
        # a mesma resposta que `notify` dá quando o alerta não sai.
        self.machine()
        with mock.patch.object(env, "GRACE", 0.0):
            code, text = self.quiet(services, ["phone"],
                                    answer=FakeEdge(read=403))
        self.assertEqual(code, REFUSED)
        self.assertIn(DRAWN_TOKEN, text)   # o valor saiu uma vez, e fica no arquivo
        self.assertEqual(notifier.phone_token(), DRAWN_TOKEN)

    def test_the_credential_door_reads_it_twice_and_without_echo(self):
        # The two readers are the account's own (`at-cli admin`): the credential
        # does not travel through the command line, so it stays out of the
        # shell's history and out of anybody's `ps`.
        self.person()
        self.standing()
        asked: list[str] = []

        def secret(question: str) -> str:
            """A mesma pessoa digitando sem eco: a credencial nas perguntas dela,
            e a Frase onde a Frase é pedida — o reinício do provedor a pede, e
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
        self.assertIn(i18n.tr("deploy.services.credential.ask"), text)

    def test_a_word_that_takes_no_argument_still_takes_none(self):
        for words in (["services", "phone", "extra"], ["services", "credential",
                                                       "a", "b"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_no_terminal_means_no_credential_to_change(self):
        # The suite runs with no tty, which is the state the door refuses in.
        self.person()
        code, text = self.quiet(main, ["services", "credential", "Rafael"])
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
    """Both doors, and every sentence either of them says, in both languages."""

    def test_every_sentence_of_the_two_acts_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the screen would show the key",
                    )

    def test_the_value_the_phone_reads_has_a_place_in_the_drawn_message(self):
        # The one message that carries a credential, and the one that has to be
        # readable twice: what it prints is the value, the topic it belongs to,
        # and where the address it comes from is.
        for code in i18n.SUPPORTED:
            text = i18n.text("services.notifier.phone.drawn", code)
            for placeholder in ("{token}", "{topic}", "{url}", "{where}",
                                "{scope}", "{authority}"):
                with self.subTest(key=placeholder, language=code):
                    self.assertIn(placeholder, text)


if __name__ == "__main__":
    unittest.main()
