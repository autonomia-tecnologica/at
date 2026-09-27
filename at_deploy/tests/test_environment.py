"""The container environment (§7a, §7b): the pins, the argv, and the two ways out.

Podman does not exist on the machine this suite runs on — the build's, and the
person's — so what is proved here is the whole of the orchestration against the
runtime's SEAM (`services/podman.py`): the manifest's pins, the arithmetic of the
folder's own pin, the argv of every service, and the state the environment writes
into the folder. What is not proved, and cannot be, is that a container comes up:
the argv IS the claim, and it is where every security decision of the environment
is readable.

The gate (§7b) is read the same way, and one step further: what Authelia is told
is a FILE AT writes, so the tests read the file — the gate's declaration, the
people and the derivation each of them wears — and never a running portal, which
would be a claim about a container that cannot come up here.

Nothing here touches the network. The one probe that leaves the process is the
address check, and it binds a port on this machine and nothing else.
"""

from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import actors, boot, files, tables
from at.encryption import vault
from at.services import caddy
from at.ui.webapp import app as webapp

from at_deploy import environment as env
from at_deploy import notifier, podman, tree, vpn
from at_deploy.cli import OK, REFUSED, USAGE, services, main

# An address that is nobody's: RFC 5737's block for documentation. Whoever binds
# it fails with EADDRNOTAVAIL, which is exactly the answer the orchestrator
# waits against.
NOBODY = "192.0.2.1"

# Every sentence the environment says out loud. The list is the reminder this
# gate needs: a message added to `environment.py` without a line here is a
# message nobody checks, and the catalog would answer with the raw key.
SAID = (
    "services.no_podman.ask", "services.no_podman.install",
    "services.no_podman.hosted", "services.no_podman.no_tty",
    "services.no_podman.status", "services.no_podman.down",
    "services.up.ahead", "services.up.waiting", "services.up.no_address",
    "services.up.failed", "services.up.service",
    "services.down.done", "services.status.site",
    "services.status.running", "services.status.installed", "services.status.missing",
    "services.status.head.service", "services.status.head.state",
    "services.status.head.image",
    "services.dnsmasq.file.header", "services.gate.drawn",
    # §4's Access Phrase, pedida pela subida (item 50): a pergunta, a segunda
    # leitura da primeira vez, e as três recusas. **A da frase curta é do
    # COFRE** — `secrets.error.phrase`, a mesma sentença que o `core.secrets`
    # diz —, e ela entra aqui porque quem a imprime é esta superfície.
    "services.phrase", "services.phrase.again", "services.phrase.mismatch",
    "services.phrase.no_tty", "services.phrase.unopened",
    "secrets.error.phrase",
    "services.elevation.ask", "services.elevation.refused",
    "services.elevation.no_tty", "services.elevation.failed",
    "services.elevation.spent",
    # The two files of the gate carry a written-by-AT line each, and both are
    # IN the files Authelia reads — which is what makes a missing translation a
    # key showing up inside a configuration file.
    "services.identity-provider.file.header",
    "services.identity-provider.users.header",
    # §7f's notifier, whose own header sits INSIDE the configuration ntfy reads.
    "services.notifier.file.header",
    # And where the delivery's credential lives, said by `status` — the file and
    # never the value. The delivery's own sentences are gated beside it, in
    # `test_notifier.py`.
    "services.notifier.credential.at", "services.notifier.credential.absent",
    "services.notifier.phone.at", "services.notifier.phone.absent",
    # Item 27's second operator act (§7b): the credential, the derivation the
    # provider reads, and the restart that makes the new one the one it proves.
    "services.credential.changed", "services.credential.hosted",
    "services.credential.unknown", "services.credential.pending",
    "services.restarted",
)


# The token the fake runtime's notifier draws when §7f's delivery asks it for
# one. The shape is ntfy's own — `tk_` and 32 characters — and the value is
# nobody's: what the tests read is that it was KEPT, at 0600, and never printed.
DRAWN_TOKEN = "tk_abcdefghijklmnopqrstuvwxyz012"

# A Frase de Acesso que a suíte digita (item 50, §4). **Ela é quem sela o que a
# pasta guarda e quem o abre**, e é por isso que ela é uma só em toda esta
# suíte: um teste que lesse o valor selado com OUTRA Frase não leria nada — que
# é exatamente o que a conferência da Frase prova, no teste que a prova.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"


class FakeRuntime:
    """The runtime's seam, answered by a list.

    Every call is recorded — that is what most of this file reads — and the
    answers are the test's: which verbs fail, and what a container says about
    itself. The notifier's CLI is here too, for the same reason the rest is: §7f's
    delivery creates its credential through `podman exec`, and the answer to that
    command is what the runtime would print.
    """

    def __init__(self, fails: tuple[str, ...] = (), running: str = "true") -> None:
        self.calls: list[list[str]] = []
        # **Os argumentos NOMEADOS de cada chamada, e eles são a metade da
        # pergunta.** O segredo que a prova carrega não pode entrar no argv, e
        # onde ele entra é no `input` do comando — um argv é um `ps` nesta
        # máquina. Sem esta lista, o que os testes leem é só a metade visível.
        self.given: list[dict] = []
        self.fails = set(fails)
        self.running = running

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        self.given.append(kw)
        failed = bool(call) and call[0] in self.fails
        said = ""
        if call[:2] == ["container", "inspect"]:
            said = self.running
        elif "ntfy" in call and "token" in call:
            said = f"token {DRAWN_TOKEN} created for user at, never expires"
        return SimpleNamespace(returncode=1 if failed else 0, stdout=said, stderr="")

    def verbs(self) -> list[str]:
        """The first word of every call, in order — the shape of the run."""
        return [call[0] for call in self.calls]


class FolderCase(unittest.TestCase):
    """A scratch Working Folder, which is what every path below resolves to."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        # **E o diretório de execução tem o rascunho dele**, porque ele mora fora
        # da Pasta de Trabalho por definição: sem um `XDG_RUNTIME_DIR` próprio, o
        # que cada teste materializa cairia no diretório de execução de quem roda
        # a suíte, com o id de uma pasta temporária que já não existe.
        self.execution = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR",
             env.RUN_ENV: self.execution.name},
        )
        self.env.start()
        i18n.reset()
        # **The machine is taken to have NO Podman, always.** The alternative is
        # the suite reading the machine it runs on, and that is not a detail: the
        # day a Podman is installed, every test that "proved" the two ways out
        # starts pulling images from the network — which is the one thing the
        # suite is forbidden to do. A `runtime()` is what turns it on, per test.
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        # And the machine's low-port rule ALLOWS every port, for the same reason
        # and by the same rule: `ThePermission` is what turns it on, per test,
        # because a suite that read the real floor would answer `1024` on this
        # machine and refuse to start the environment in half of these tests.
        self.floor = mock.patch.object(env, "floor", lambda: 0)
        self.floor.start()
        self.addCleanup(self.floor.stop)
        # **E a pessoa digita a Frase**, pelo mesmo desenho: o `up` a lê de um
        # leitor sem eco, e a suíte entrega o dela — é o `getpass` do terminal
        # que ela substitui. Uma subida sem leitor nenhum é o caso que os testes
        # da recusa exercitam, e eles passam `secret=None` de propósito.
        self.phrase = lambda question: PHRASE
        self._vault_key: bytes | None = None
        # And the machine is on NO private network, by the same rule again: the
        # day this suite runs on a machine that is, half of these tests would be
        # writing the tailnet's name into the files they compare (§7e).
        # It is the SUBPROCESS that is taken away and not the questions: the
        # parsing stays the real one, and `ThePrivateNetwork` is what hands the
        # questions an answer.
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

    def runtime(self, fails: tuple[str, ...] = (), running: str = "true") -> FakeRuntime:
        """A machine WITH a Podman, and a runtime that answers instead of doing."""
        fake = FakeRuntime(fails, running)
        started = mock.patch.object(podman, "present", lambda: True)
        calls = mock.patch.object(podman, "run", fake.run)
        asked = mock.patch.object(podman, "ok", lambda args: fake.run(args).returncode == 0)
        for patch in (started, calls, asked):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def quiet(self, call, *args, **kw):
        """Run something and answer with what it printed."""
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()

    def phrase_key(self) -> bytes:
        """A Chave do Cofre da Frase da suíte — derivada uma vez por teste.

        `vault.vault_key` é a derivação de uma frase e custa o que ela custa
        (§4); a mesma Frase dentro do mesmo teste é a mesma Chave.
        """
        if self._vault_key is None:
            self._vault_key = vault.vault_key(PHRASE)
        return self._vault_key

    def value(self, where: Path, scope: str) -> str | None:
        """O valor CLARO que um arquivo da pasta guarda SELADO (item 50).

        Ele é lido ABRINDO o envelope com a Frase da suíte, e nunca de um
        segundo sorteio: um valor sorteado de novo não provaria nada sobre o
        arquivo, e é o arquivo que estes testes leem. Um arquivo que não existe
        responde `None`: nem todo valor já nasceu em toda pasta.
        """
        try:
            envelope = where.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        if not envelope:
            return None
        return vault.unseal(envelope, vault.derived_key(self.phrase_key(), scope))

    def secrets(self) -> dict[str, str | None]:
        """Os valores que o deploy sorteou, em CLARO, lidos da própria pasta.

        Os SEIS são lidos ABRINDO o envelope que a pasta guarda (`value`), e
        nunca de um segundo sorteio: um valor sorteado de novo pelo teste não
        provaria nada sobre o arquivo. As duas pontas do notificador entraram
        aqui nesta fatia — elas eram as últimas que a pasta guardava em claro.
        """
        return {name: self.value(where, scope)
                for name, (where, scope) in _sealed_values().items()}

    def marks(self) -> dict[str, str]:
        """O texto que IDENTIFICA cada valor dentro da pasta.

        Para os SEIS que o AT sela é o ENVELOPE — a pasta guarda o selo, e é ele
        que a linha do catálogo promete. Um arquivo que não existe identifica
        nada, e é `""` que o diz.
        """
        marks = {}
        for name, (where, _) in _sealed_values().items():
            try:
                marks[name] = where.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                marks[name] = ""
        return marks

    def copy_of(self, where: Path) -> Path | None:
        """A cópia que o diretório de execução fez de um arquivo da pasta.

        `App/services/<serviço>/<arquivo>` vira `<run>/services/<serviço>/<arquivo>`,
        e o portão — que não é arquivo de serviço nenhum — tem cópia com nome
        próprio (`gate_materialized`). O que não é lido por container nenhum
        responde `None`: não há cópia nenhuma dele.
        """
        if where == caddy.gate_file():
            return env.gate_materialized()
        try:
            service = where.relative_to(env.paths.services_dir()).parts[0]
        except ValueError:
            return None
        return env.materialized(service) / where.name


class TheManifest(unittest.TestCase):
    """What the binary carries: the services of §7a, pinned in version and digest."""

    def test_the_services_of_the_section_are_declared(self):
        # §7a: "dnsmasq e o Caddy são os primeiros serviços". §7b adds the gate
        # and §7c the WebApp, and the order is the ORDER THINGS COME UP: the
        # edge asks the provider about every request and proxies to the WebApp,
        # so both stand before it. §7f's notifier stands last, and it is the one
        # nothing in front of it depends on.
        self.assertEqual([service.name for service in env.SERVICES],
                         ["dnsmasq", env.IDENTITY, env.WEBAPP, "caddy", env.NOTIFIER])

    def test_every_image_is_pinned_in_version_and_hashing(self):
        # §3 (Dependência externa): "Dependências de pacotes e imagens são
        # fixadas em versão e hashing". A tag alone moves; the digest is what
        # pins.
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertTrue(
                    service.image.at_the_pin(),
                    f"{service.name} is not pinned: {service.image.reference()} — an "
                    f"image that can move under the person's feet is what §3 forbids",
                )

    def test_the_reference_carries_both_the_version_and_the_digest(self):
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                reference = service.image.reference()
                self.assertIn(f":{service.image.version}@", reference)
                self.assertTrue(reference.endswith(service.image.digest))

    def test_a_person_reads_the_image_without_the_pin(self):
        # DUAS LEITURAS, DOIS LEITORES. O digest é o que fixa, e é por isso que
        # o `podman run` e o registro da pasta não podem viver sem ele — mas
        # sessenta e quatro caracteres de hexadecimal não dizem nada a quem só
        # quer saber qual imagem e qual release. O que fixa a imagem é ela ser
        # USADA com o digest, não ele ser impresso.
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                image = service.image
                self.assertEqual(image.shown(),
                                 f"{image.repo}:{image.version}")
                self.assertNotIn(image.digest, image.shown())

    def test_a_tag_that_moves_is_not_a_pin(self):
        # The rule this reads is the shape of the digest, so a pin written by
        # hand has to pass the same door.
        moving = env.Image("docker.io/library/caddy", "latest", "sha256:abc")
        self.assertFalse(moving.at_the_pin())
        nothing = env.Image("docker.io/library/caddy", "2.11.4", "")
        self.assertFalse(nothing.at_the_pin())

    def test_every_port_is_published_on_the_loop_or_on_the_private_network(self):
        # Medido no ambiente aposentado e herdado: uma deny-list do host não
        # cobre uma porta publicada de container — a porta passa por DNAT e o
        # hook `input` nunca a vê —, então o que fecha a LAN é publicar no laço.
        # A exceção é a porta do SITE, e ela é o §7e: o endereço da rede privada
        # quando a máquina está numa, o laço quando não está. `0.0.0.0` não é
        # nenhum dos dois, e é o que esta linha existe para proibir.
        for service in env.SERVICES:
            for port in env.ports_of(service):
                with self.subTest(service=service.name, port=port.port):
                    self.assertIn(port.address, (env.LOOP, env.vpn.address() or env.LOOP))
                    self.assertNotIn(port.address, ("0.0.0.0", "::"))

    def test_the_caddy_publishes_the_site_and_the_environment_nothing_else(self):
        # A borda é o que a pessoa alcança: ela publica a porta do SITE, e o
        # resto do ambiente fica no laço ou em nada. O que decide a rede de cada
        # serviço é só com quem ele fala (o módulo diz por quê).
        caddy = _service("caddy")
        self.assertEqual(caddy.network, env.NETWORK)
        self.assertEqual([port.port for port in env.ports_of(caddy)], [env.PORT])

    def test_the_dns_is_the_one_service_of_the_dmz(self):
        # O dnsmasq é o único que não fala com ninguém, e é o único sozinho na
        # rede que não tem rota para a do ambiente.
        alone = [service.name for service in env.SERVICES
                 if service.network == env.DMZ]
        self.assertEqual(alone, ["dnsmasq"])

    def test_every_service_reads_what_the_folder_is(self):
        # §7: every service's persistent state lives under `App/services/`, and
        # a service whose state does not fit there does not come in — so a
        # service mounts its own state folder and comes up reading a file AT
        # wrote for it. §7c's WebApp is the one that mounts the Working Folder
        # ITSELF instead (the absolute-path contract), and that folder is
        # already everything AT wrote; it declares no file of its own.
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                mirrors = [mount for mount in service.mounts
                           if isinstance(mount, env.Mirror)]
                self.assertTrue(
                    service.writes or mirrors,
                    f"{service.name} declares no file and mounts no folder: it "
                    f"would come up reading nothing AT wrote",
                )
                if not mirrors:
                    self.assertIn(
                        "", [mount.host for mount in service.mounts],
                        f"{service.name} does not mount its own state folder",
                    )

    def test_the_dnsmasq_publishes_dns_on_both_protocols(self):
        # UDP e TCP, na mesma porta, e o endereço é um dos dois que §7e permite:
        # o laço quando a máquina não está em rede nenhuma, o dela quando está.
        # O DNS é o segundo serviço a sair do laço, e é isso que torna os nomes
        # do ambiente — `at.local`, `ntfy.at.local` — perguntáveis de fora da
        # máquina. Onde cada endereço vale é o que `ThePrivateNetwork` e `TheUp`
        # provam, com o agente fora do caminho; aqui a pergunta é outra.
        ports = env.ports_of(_service("dnsmasq"))
        self.assertEqual([(port.port, port.protocol) for port in ports],
                         [(53, "udp"), (53, "tcp")])
        for port in ports:
            self.assertIn(port.address, (env.LOOP, env.vpn.address() or env.LOOP))


def _service(name: str) -> env.Service:
    return next(service for service in env.SERVICES if service.name == name)


class ThePin(FolderCase):
    """§3: the pin only moves forward, and an instance ahead is not downgraded."""

    def test_a_folder_that_never_pinned_is_behind(self):
        self.assertEqual(env.decide(_service("dnsmasq"), {}), env.OUTDATED)

    def test_a_folder_at_the_pin_is_at_the_pin(self):
        service = _service("dnsmasq")
        pins = {"dnsmasq": {"version": service.image.version,
                            "digest": service.image.digest}}
        self.assertEqual(env.decide(service, pins), env.CURRENT)

    def test_a_folder_behind_the_binary_is_re_pinned(self):
        self.assertEqual(
            env.decide(_service("dnsmasq"), {"dnsmasq": {"version": "2.89", "digest": "sha256:" + "a" * 64}}),
            env.OUTDATED,
        )

    def test_a_folder_ahead_of_the_binary_warns_and_proceeds(self):
        service = _service("dnsmasq")
        ahead = {"version": "9.99", "digest": "sha256:" + "b" * 64}
        self.assertEqual(env.decide(service, {"dnsmasq": ahead}), env.AHEAD)
        # And what it runs is what it HAS: the pin does not move backward.
        self.assertEqual(env.running(service, {"dnsmasq": ahead}).version, "9.99")

    def test_a_digest_that_moved_at_the_same_version_is_out_of_date(self):
        service = _service("dnsmasq")
        moved = {"version": service.image.version, "digest": "sha256:" + "c" * 64}
        self.assertEqual(env.decide(service, {"dnsmasq": moved}), env.OUTDATED)

    def test_a_record_nobody_can_read_is_no_record(self):
        env.pin_file().parent.mkdir(parents=True, exist_ok=True)
        env.pin_file().write_text("{ this is not JSON", encoding="utf-8")
        self.assertEqual(env.held(), {})

    def test_the_pin_is_read_as_versions_and_not_as_words(self):
        self.assertLess(env.order("2.9"), env.order("2.11"))
        self.assertGreater(env.order("2.93"), env.order("2.11.4"))
        self.assertEqual(env.order("2.92_p2"), (2, 92, 2))
        self.assertEqual(env.order(None), ())


class TheOffer(FolderCase):
    """§7a: with no Podman, the two ways out — and AT takes neither."""

    def test_with_no_terminal_neither_way_is_taken(self):
        # §3: a decision made where nobody could answer is not one.
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.no_podman.no_tty"), text)

    def test_the_two_ways_are_both_in_the_question(self):
        said = []
        outcome, text = self.quiet(env.up, secret=self.phrase, ask=lambda question: (said.append(question), "n")[1])
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)
        self.assertEqual(len(said), 1)

    def test_installing_is_the_persons_act_and_bill_only_says_how(self):
        outcome, text = self.quiet(env.up, secret=self.phrase, ask=lambda question: "s")
        self.assertEqual(outcome, env.INSTALL)
        self.assertIn(i18n.tr("services.no_podman.install"), text)

    def test_neither_way_out_writes_anything(self):
        for answer in ("s", "n"):
            with self.subTest(answer=answer):
                self.quiet(env.up, secret=self.phrase, ask=lambda question, answer=answer: answer)
        self.assertFalse(env.pin_file().exists())
        self.assertFalse(env.state("dnsmasq").exists())

    def test_nothing_is_asked_of_the_runtime_without_a_podman(self):
        with mock.patch.object(podman, "run", mock.Mock()) as called:
            self.quiet(env.up, secret=self.phrase)
        called.assert_not_called()


class TheUp(FolderCase):
    """`up` with a Podman: the argv is the whole of what AT decides."""

    def test_every_service_runs_the_image_at_the_pin(self):
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.UP)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(service.image.reference(), [call[-1] for call in fake.calls])
                self.assertIn(i18n.tr(
                    "services.up.service", service=i18n.tr(service.label),
                    image=service.image.shown(), where=env.state(service.name),
                ), text)

    def test_no_line_a_person_reads_carries_the_pin(self):
        # O defeito que isto tranca: `services up` imprimia
        # `repo:version@sha256:…` para quem estava lendo. O digest continua indo
        # para onde ele é OBRIGATÓRIO — o `podman run` e o registro da pasta, que
        # o teste acima prova —, e some de toda frase que uma pessoa lê.
        self.runtime()
        _, text = self.quiet(env.up, secret=self.phrase)
        self.assertNotIn("sha256:", text)

    def test_the_dnsmasq_publishes_dns_and_mounts_its_own_folder(self):
        # O laço é o endereço de quem não tem rede privada — o estado suportado
        # —, e o `podman run` é onde a decisão de §7e aparece: com rede, este
        # mesmo argumento traz o endereço dela (`TheTwoNames`).
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        argv = _call(fake, "at-dnsmasq")
        self.assertIn("--network", argv)
        self.assertIn(env.DMZ, argv)
        self.assertIn("127.0.0.1:53:53/udp", argv)
        # O que o container LÊ vem do diretório de execução: a pasta de estado é
        # a fonte, e o que ele monta é a cópia que serve a subida (item 50).
        self.assertIn(f"{env.materialized('dnsmasq')}:{env.DNSMASQ_CONFIG}:Z", argv)
        self.assertNotIn(f"{env.state('dnsmasq')}:{env.DNSMASQ_CONFIG}:Z", argv)

    def test_the_caddy_joins_the_network_and_publishes_the_site(self):
        # A borda é um container como os outros, e as duas coisas que a fazem a
        # borda são a rede em que ela está — onde o WebApp e o portão estão — e
        # a única porta que ela publica.
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        argv = _call(fake, "at-caddy")
        self.assertIn(env.NETWORK, argv)
        self.assertIn(f"{env.LOOP}:{env.PORT}:{env.PORT}/tcp", argv)
        # O `Caddyfile` sai do diretório de execução e o storage da CA NÃO: o
        # primeiro o container só lê, e o segundo é o que ele ENCHE — e o que
        # ele enche tem de sobreviver ao container (item 50).
        self.assertIn(f"{env.materialized('caddy')}:{env.CADDY_CONFIG}:Z", argv)
        self.assertIn(f"{env.state('caddy') / 'storage'}:{env.CADDY_DATA}:Z", argv)

    def test_the_containers_are_named_and_labeled_as_bills(self):
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                argv = _call(fake, env.container(service.name))
                self.assertIn(env.container(service.name), argv)
                self.assertIn(f"{env.LABEL}={service.name}", argv)

    def test_the_configuration_lands_in_the_state_folder(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        self.assertIn("address=/", (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"))
        self.assertIn("reverse_proxy", (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"))

    def test_the_caddyfile_of_the_container_keeps_its_storage_in_the_container(self):
        # §7a: the same Caddy, the same generator — and the one line that is a
        # path and not a decision is where the folder is inside the container.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f'storage file_system "{env.CADDY_DATA}"', text)
        self.assertNotIn(str(self.root / "App" / "caddy" / "storage"), text)

    def test_the_pin_is_recorded_once_the_service_is_up(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        recorded = env.held()
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertEqual(recorded[service.name]["version"], service.image.version)
                self.assertEqual(recorded[service.name]["digest"], service.image.digest)

    def test_a_service_already_there_is_replaced_and_not_refused(self):
        # Two containers cannot share a name, and the name is the service.
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        self.assertIn(["rm", "--force", "at-caddy"], fake.calls)

    def test_an_image_that_does_not_arrive_stops_the_service(self):
        fake = self.runtime(fails=("pull",))
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn("dnsmasq", text)
        self.assertNotIn("run", fake.verbs())
        self.assertFalse(env.pin_file().exists())

    def test_an_instance_ahead_warns_and_runs_what_the_folder_has(self):
        # §3: "Uma instância à frente do pino do binário avisa e prossegue: ela
        # não é rebaixada."
        ahead = {"version": "9.99", "digest": "sha256:" + "d" * 64}
        env.pin_file().parent.mkdir(parents=True, exist_ok=True)
        env.pin_file().write_text(
            json.dumps({"dnsmasq": ahead}), encoding="utf-8"
        )
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.UP)
        self.assertIn(i18n.tr(
            "services.up.ahead", service=i18n.tr("services.dnsmasq.name"),
            held="9.99", pin=_service("dnsmasq").image.version,
        ), text)
        self.assertIn(f"docker.io/dockurr/dnsmasq:9.99@{ahead['digest']}",
                      [call[-1] for call in fake.calls])
        # And the pin it leaves behind is the one it is at, still ahead.
        self.assertEqual(env.held()["dnsmasq"]["version"], "9.99")

    def test_the_network_is_created_when_the_machine_does_not_have_it(self):
        fake = self.runtime(fails=("network",))
        self.quiet(env.up, secret=self.phrase)
        self.assertIn(["network", "exists", env.NETWORK], fake.calls)
        self.assertIn(["network", "create", env.NETWORK], fake.calls)

    def test_the_read_only_folder_refuses_the_write(self):
        self.runtime()
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                self.quiet(env.up, secret=self.phrase)


def _call(fake: FakeRuntime, name: str) -> list[str]:
    """The `run` that starts that container."""
    return next(
        call for call in fake.calls
        if call[:1] == ["run"] and name in call
    )


class TheIdentityProvider(FolderCase):
    """§7b's gate: the container, and the two files it reads.

    What is provable on a machine without a Podman is what Authelia is handed,
    so this class reads the files AT writes into the service's own state
    folder — the gate's declaration, and the people it is going to prove.
    """

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        return fake

    def conf(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")

    def users(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_USERS).read_text(encoding="utf-8")

    def secret(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_SESSION).read_text(encoding="utf-8")

    def test_the_provider_publishes_nothing_and_mounts_its_state(self):
        # Quem chega no provedor é o Caddy (`forward_auth`) e o WebApp (a
        # checagem dele) — e os dois o alcançam pelo NOME na rede, então a porta
        # no laço que ele mantinha para um Caddy no host não existe mais.
        service = _service(env.IDENTITY)
        self.assertEqual(env.ports_of(service), ())
        hosts = [mount.host for mount in service.mounts]
        self.assertIn("", hosts)       # `/config`: what AT wrote for it
        self.assertIn("data", hosts)   # `/data`: what the provider keeps itself

    def test_the_configuration_puts_bill_behind_the_gate_as_one_more_app(self):
        # §7b: "o AT entra por forward-auth como um app a mais, nunca como
        # exceção". Deny by default, and AT's own site named as one_factor.
        self.up()
        text = self.conf()
        self.assertIn("default_policy: deny", text)
        self.assertIn(f"    - domain: {env.NAME}", text)
        self.assertIn("      policy: one_factor", text)
        self.assertIn(f"authelia_url: {env.portal_url()}", text)

    def test_the_portal_has_a_path_and_the_provider_is_told_it(self):
        # **O caminho é o que tira o portal de dentro do `forward_auth`**: a
        # borda roteia o caminho direto no provedor, e o provedor serve a página
        # sob ele. Sem o caminho, o redirecionamento do portão volta para a
        # borda, a borda pergunta sobre o portal, e os dois se reescrevem até o
        # `431` — medido contra o container, e ninguém atravessava.
        self.up()
        text = self.conf()
        self.assertTrue(caddy.PORTAL.startswith("/"))
        self.assertIn(
            f'address: "tcp://{env.ALL}:{env.IDENTITY_PORT}{caddy.PORTAL}"', text)
        self.assertIn(f"authelia_url: {env.portal_url()}", text)
        self.assertTrue(env.portal_url().endswith(f"{caddy.PORTAL}/"))
        # E o caminho não entra no `access_control`: o portal não passa pela
        # pergunta, então não passa pela regra que a responde.
        self.assertNotIn(caddy.PORTAL, text[text.index("access_control:"):])

    def test_the_access_control_keeps_naming_the_site_alone(self):
        # A regra responde pelo SITE — o domínio que a pergunta traz. O portal é
        # roteado fora da pergunta, então uma regra para ele seria uma regra que
        # nada consulta.
        self.up()
        text = self.conf()
        rules = text[text.index("access_control:"):text.index("notifier:")]
        self.assertEqual(rules.count("- domain:"), 1)
        self.assertIn(f"- domain: {env.site_host()}", rules)

    def test_the_storage_and_the_users_are_where_bill_mounts_them(self):
        # §7: the persistent state of the service lives in the folder, and this
        # is the line that says so inside the container.
        self.up()
        text = self.conf()
        self.assertIn(f"path: {env.IDENTITY_DATA}/db.sqlite3", text)
        self.assertIn(f"path: {env.IDENTITY_CONFIG}/{env.IDENTITY_USERS}", text)

    def test_no_oidc_provider_is_declared_while_no_service_speaks_oidc(self):
        # §7b has Authelia speaking OIDC with whoever speaks OIDC — and every
        # app of §7 comes in by forward-auth, AT included, so the client list
        # is empty today. Authelia refuses a provider with no client (`clients`
        # must name one, `jwks` an RSA key), so a block written now would be a
        # configuration that does not start, naming a client that does not
        # exist. It enters with the first service that speaks OIDC.
        self.up()
        self.assertNotIn("identity_providers", self.conf())

    def test_the_secrets_the_provider_needs_are_drawn_once_and_kept(self):
        # **Medido contra o container**: o Authelia recusa subir sem a chave com
        # que ele CIFRA os próprios registros e sem o segredo com que ele assina
        # um token de validação de identidade. Os dois são da INSTALAÇÃO e não de
        # uma subida — desenhados por subida, o que ele já escreveu ficaria
        # ilegível —, então moram na pasta de estado, como o da sessão.
        self.up()
        drawn = {name: (env.state(env.IDENTITY) / name).read_text(encoding="utf-8").strip()
                 for name in (env.IDENTITY_ENCRYPTION, env.IDENTITY_JWT)}
        text = self.conf()
        for name, value in drawn.items():
            with self.subTest(secret=name):
                self.assertTrue(value, f"{name} nao foi sorteado")
                self.assertIn(f'"{value}"', text)
        self.up()
        for name, value in drawn.items():
            with self.subTest(secret=name):
                self.assertEqual(
                    (env.state(env.IDENTITY) / name).read_text(encoding="utf-8").strip(),
                    value)

    def test_the_notifier_the_provider_needs_is_a_file_in_the_folder(self):
        # O Authelia exige um notificador — um smtp ou um arquivo — porque ele
        # tem de poder contar alguma coisa a alguém, e o caso do dia é uma
        # identidade validando um segundo fator. §7 não tem smtp, então é um
        # arquivo, e ele mora na pasta de estado, que é a pasta do backup (§3).
        self.up()
        self.assertIn(f"filename: {env.IDENTITY_CONFIG}/{env.IDENTITY_NOTIFICATIONS}",
                      self.conf())

    def test_the_provider_listens_on_the_container_and_not_on_a_publication(self):
        # O endereço do container, e não uma publicação: o que sai dele é o que
        # o runtime mapeia (§7a) — e o NOME do serviço é como a borda e o WebApp
        # o alcançam. O CAMINHO faz parte do endereço: é o que o Authelia lê
        # para servir o portal sob ele (`server.address`), e é essa a ponta que
        # a borda roteia sem perguntar.
        self.up()
        self.assertIn(
            f'address: "tcp://{env.ALL}:{env.IDENTITY_PORT}{caddy.PORTAL}"',
            self.conf())

    def test_the_session_secret_is_drawn_once_and_kept(self):
        # Authelia signs its cookie with it: drawn per start, every session
        # would die on the next `at-cli services up`.
        self.up()
        drawn = self.secret()
        self.assertTrue(drawn.strip())
        self.assertIn(f'secret: "{drawn.strip()}"', self.conf())
        self.up()
        self.assertEqual(self.secret(), drawn)

    def test_the_users_file_carries_the_people_and_the_derivation_the_row_holds(self):
        # §7b's split, written out: who is an actor is AT's, how it is proved
        # is the gate's — and the derivation is the row's own, so the credential
        # is the same one Forms proves and never travels as a value.
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.up()
        text = self.users()
        self.assertIn('  "Rafael":', text)
        self.assertIn('displayname: "Rafael"', text)
        self.assertIn(f'password: "{actors.admins()[0]["credential"]}"', text)

    def test_a_name_that_would_break_the_yaml_is_quoted(self):
        actors.create_admin('Rafael: o "chefe"', "uma-frase-bem-longa")
        self.up()
        self.assertIn('  "Rafael: o \\"chefe\\"":', self.users())

    def test_a_folder_with_nobody_gets_the_empty_map(self):
        self.up()
        self.assertIn("users: {}", self.users())

    def test_a_person_with_no_credential_is_not_an_account(self):
        # An entry with an empty derivation would be an account nobody holds
        # and anybody could try.
        tables.create("actor", {"name": "Sem credencial", "type": "person"})
        self.up()
        self.assertIn("users: {}", self.users())


class TheGate(FolderCase):
    """§7b: the secret drawn at installation, and the two lines it becomes."""

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        return fake

    def caddyfile(self) -> str:
        return (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")

    def identity(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")

    def test_up_draws_the_secret_and_says_where_it_is(self):
        # §7b: "um valor sorteado pelo AT na instalação". The installation is
        # the environment coming up, and this is the one message it owes.
        self.runtime()
        _, text = self.quiet(env.up, secret=self.phrase)
        self.assertTrue(caddy.gate_secret())
        self.assertIn(i18n.tr("services.gate.drawn", where=caddy.gate_file()), text)

    def test_a_secret_already_drawn_is_not_drawn_again(self):
        # Two different secrets are a Caddy attaching one value and a WebApp
        # taking another: every identity would be refused until both restarted
        # from the same file.
        self.up()
        held = caddy.gate_secret()
        _, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(caddy.gate_secret(), held)
        self.assertNotIn(i18n.tr("services.gate.drawn", where=caddy.gate_file()), text)

    def test_the_caddyfile_carries_the_secret_and_asks_the_gate(self):
        self.up()
        text = self.caddyfile()
        self.assertIn(f"header_up {caddy.GATE_HEADER} {caddy.gate_secret()}", text)
        # And the ask comes first: the Caddy finds out who is calling before it
        # hands anything to the WebApp. O proxy do WebApp é o do NOME na rede —
        # o do portal é o outro, e ele vem antes de tudo (`PORTAL`).
        behind = f"reverse_proxy {env.container(env.WEBAPP)}:{env.WEBAPP_PORT}"
        self.assertLess(text.index("forward_auth"), text.index(behind))
        self.assertIn(
            f"forward_auth {env.container(env.IDENTITY)}:{env.IDENTITY_PORT}", text)
        self.assertIn(f"uri {caddy.AUTH_URI}", text)
        self.assertIn("copy_headers Remote-User", text)

    def test_the_portal_of_the_container_goes_around_the_ask(self):
        # O `handle` do portal vai DIRETO no provedor — é a volta por fora da
        # pergunta que fecha o laço do `431`, e é a única rota do site que não
        # passa pelo `forward_auth`.
        self.up()
        text = self.caddyfile()
        provider = f"{env.container(env.IDENTITY)}:{env.IDENTITY_PORT}"
        self.assertIn(f"\t@portal path {caddy.PORTAL} {caddy.PORTAL}/*", text)
        self.assertIn("\thandle @portal {", text)
        portal = text[text.index("handle @portal {"):text.index("\thandle {")]
        self.assertEqual(portal.count("reverse_proxy"), 1)
        self.assertIn(f"reverse_proxy {provider}", portal)
        self.assertNotIn("forward_auth", portal)
        # O portal antes da pergunta: o `handle` casado vence o fallback.
        self.assertLess(text.index("handle @portal"), text.index("forward_auth"))

    def test_the_portal_the_caddy_routes_is_the_one_the_gate_sends_people_to(self):
        # Uma fonte só para o endereço do portal (`portal_url`): o `authelia_url`
        # que o portão emite e o caminho que a borda roteia não podem divergir —
        # divergir é a pessoa ser mandada a um lugar que a borda não serve.
        self.up()
        self.assertIn(f"authelia_url: {env.portal_url()}", self.identity())
        self.assertIn(f"\t@portal path {caddy.PORTAL} {caddy.PORTAL}/*",
                      self.caddyfile())
        self.assertTrue(env.portal_url().endswith(f"{caddy.PORTAL}/"))

    def test_without_a_podman_no_gate_is_drawn(self):
        # The folder that never took the container path has no gate, and a
        # secret drawn for a path nobody took would be a file nobody reads.
        self.quiet(env.up, secret=self.phrase)
        self.assertFalse(caddy.gate_file().exists())


class ThePermission(FolderCase):
    """§3, Privilege: the environment's one elevation, asked and never assumed.

    §7a's `dnsmasq` publishes DNS on `53`, and a machine that ships the kernel's
    low-port rule refuses that bind to a user process — which is every Linux, and
    the one measured here (`ip_unprivileged_port_start = 1024`). The rule says
    the elevation happens "through an explicit request, with the reason on
    display", and this is that door.
    """

    def machine(self, value: int = 1024):
        """This machine's low-port floor, at the value the test chooses."""
        return mock.patch.object(env, "floor", lambda: value)

    def test_the_file_that_answers_is_the_name_in_its_spelling(self):
        # The sysctl is asked by its DOTTED name and read from a path spelled
        # with slashes, and the two are not interchangeable: the first version of
        # this read `floor()` as `0` on a machine whose floor is `1024`, which is
        # the answer that would have skipped the request in silence.
        self.assertEqual(env.SYSCTL_PORTS, "net.ipv4.ip_unprivileged_port_start")
        self.assertEqual(str(env.SYSCTL_FILE),
                         "/proc/sys/net/ipv4/ip_unprivileged_port_start")

    def test_a_machine_that_allows_the_port_asks_nothing(self):
        asked: list[str] = []
        with self.machine(0):
            self.assertEqual(env.blocked(), ())
            self.assertIsNone(env.elevate(lambda question: asked.append(question) or "s"))
        self.assertEqual(asked, [])

    def test_what_is_blocked_is_asked_of_the_manifest(self):
        # Not a hand-written list: a service that starts publishing a low port
        # tomorrow enters this question by existing. **E a porta 443 entra por
        # isso**: o site publica nela, ela é baixa, e a resposta não é tratada
        # em lugar nenhum como um caso à parte — o piso se move UMA vez, para a
        # mais baixa que o ambiente publica, e as duas passam a caber.
        with self.machine(1024):
            self.assertEqual(env.blocked(), (53, 443))
        with self.machine(444):
            self.assertEqual(env.blocked(), (53, 443))
        with self.machine(443):
            self.assertEqual(env.blocked(), (53,))
        with self.machine(53):
            self.assertEqual(env.blocked(), ())

    def test_the_request_carries_the_reason_and_the_narrowest_value(self):
        # The reason on display (§3), and the floor moves to the LOWEST port the
        # environment publishes — 53, not 0: the machine grants exactly what AT
        # needs and nothing below it.
        said, spent = [], []
        box = {"floor": 1024}

        def spend(*argv: str) -> None:
            spent.append(argv)
            box["floor"] = 53  # the machine moved

        with mock.patch.object(env, "floor", lambda: box["floor"]):
            outcome = self.quiet(
                env.elevate, lambda question: (said.append(question), "s")[1],
                spend=spend,
            )[0]
        self.assertIsNone(outcome)
        self.assertEqual(spent, [("sysctl", "-w", f"{env.SYSCTL_PORTS}=53")])
        self.assertIn(env.SYSCTL_PORTS, said[0])
        self.assertIn("53", said[0])

    def test_declining_moves_nothing_and_says_which_port_is_out_of_reach(self):
        spent = []
        with self.machine(1024):
            outcome, text = self.quiet(
                env.elevate, lambda question: "n", spend=lambda *argv: spent.append(argv)
            )
        self.assertEqual(outcome, env.HOSTED)
        self.assertEqual(spent, [])
        self.assertIn(i18n.tr("services.elevation.refused", ports="53, 443"), text)

    def test_with_no_terminal_the_permission_is_not_requested(self):
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.elevation.no_tty", ports="53, 443"), text)

    def test_a_machine_that_does_not_move_says_so_instead_of_announcing(self):
        # Asking and getting nothing is the one answer that must not be called a
        # success: the services would come up and fail to bind.
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate, lambda question: "s",
                                       spend=lambda *argv: None)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr("services.elevation.failed", ports="53, 443"), text)

    def test_up_asks_before_it_starts_anything_and_leaves_the_folder_alone(self):
        # A refusal is the folder's previous state untouched: no secret drawn, no
        # network created, no service started.
        fake = self.runtime()
        with self.machine(1024):
            outcome, text = self.quiet(env.up, secret=self.phrase, ask=lambda question: "n")
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.elevation.refused", ports="53, 443"), text)
        self.assertFalse(caddy.gate_file().exists())
        self.assertEqual(fake.calls, [])

    def test_a_machine_that_already_allows_it_goes_straight_to_the_services(self):
        fake = self.runtime()
        with self.machine(0):
            outcome, _ = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.UP)
        self.assertTrue(fake.calls)


class ThePrivateNetwork(FolderCase):
    """§7e: the environment is reachable where the private network puts it.

    The questions the VPN agent answers are local ones — this machine's address
    on the network, and the name the network answers for it — and the suite asks
    them through the seam for the same reason it asks the runtime through its
    own: a test never runs the machine's agent.
    """

    def agent(self, stdout: str = "", returncode: int = 0):
        """One answer from the agent, without an agent."""
        return lambda args: SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    def test_the_address_is_the_networks_and_not_somethings_else(self):
        # An agent on several networks reports several addresses; the FIRST is
        # the network's, and an AT that guessed between them would be picking a
        # network nobody named.
        self.assertEqual(vpn.address(self.agent("100.64.0.1\nfd7a:115c::1\n")),
                         "100.64.0.1")

    def test_the_name_comes_without_its_trailing_root_dot(self):
        # `host.example-tailnet.ts.net.` is the record; the name is what is typed.
        payload = json.dumps({"Self": {"DNSName": "host.example-tailnet.ts.net."}})
        self.assertEqual(vpn.name(self.agent(payload)), "host.example-tailnet.ts.net")

    def test_no_agent_and_an_agent_that_is_not_up_are_the_same_answer(self):
        # §7e is optional: neither of the two is a machine that is on a network.
        for answer in (self.agent("", 1), lambda args: None):
            with self.subTest(answer=answer):
                self.assertIsNone(vpn.address(answer))
                self.assertIsNone(vpn.name(answer))
        self.assertFalse(vpn.present(lambda args: None))

    def test_an_answer_nobody_can_read_is_no_answer(self):
        # The name comes out of JSON, and a payload that is not one — or one with
        # no node in it — is a machine AT cannot say anything about. Saying
        # nothing is the honest answer, and it is the one that keeps the
        # environment on the loop instead of writing a name nobody verified.
        self.assertIsNone(vpn.name(self.agent("{ this is not json")))
        self.assertIsNone(vpn.name(self.agent('{"Self": {}}')))
        self.assertIsNone(vpn.address(self.agent("")))

    def test_the_network_changes_the_address_and_never_the_name(self):
        # **A decisão desta fatia, e ela é uma linha**: a rede privada decide
        # ONDE a borda publica e o que o DNS responde, e nunca QUAIS são os
        # nomes. O nome da rede (`vpn.name`) nomeava o site enquanto ele era a
        # única coisa que o ambiente tinha; agora que cada serviço tem o seu
        # embaixo de um domínio só, um site que respondesse pelo nome da rede
        # seria um segundo domínio, um segundo certificado, e um portão cujo
        # `authelia_url` mandaria o celular para um nome que a rede não resolve.
        #
        # O endereço da rede privada não existe nesta máquina — quem responde
        # por ele é o seam —, então quem responde pela PERGUNTA ao endereço
        # também: `TheAddress` prova a pergunta, e aqui o que se lê é o que a
        # subida ESCREVE.
        with mock.patch.object(vpn, "name", lambda call=None: "host.example-tailnet.ts.net"), \
                mock.patch.object(vpn, "address", lambda call=None: "100.64.0.1"), \
                mock.patch.object(env, "address_ready", lambda address: True):
            self.assertEqual(env.site_host(), env.NAME)
            fake = self.runtime()
            self.quiet(env.up, secret=self.phrase)
            caddyfile = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
            self.assertIn(f"https://{env.NAME} {{", caddyfile)
            self.assertNotIn("host.example-tailnet.ts.net", caddyfile)
            identity = (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")
            self.assertIn(f"domain: {env.NAME}", identity)
            # O portal segue o mesmo nome — e carrega o caminho dele, que é o
            # endereço em que a borda o roteia fora do `forward_auth`.
            self.assertIn(
                f"authelia_url: https://{env.NAME}{caddy.PORTAL}/", identity)
            # The name AT answers for points at where the edge actually is.
            self.assertIn(f"address=/{env.NAME}/100.64.0.1",
                          (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"))
            # **E a porta do site é publicada no endereço DA REDE**, que é como a
            # pessoa chega: no caminho container quem publica é o container, e o
            # §7e só vale se o endereço for o da rede.
            self.assertIn(f"100.64.0.1:{env.PORT}:{env.PORT}/tcp",
                          _call(fake, "at-caddy"))
            # **E o DNS sai do laço pela outra metade da mesma razão**: os nomes
            # que ele responde — `at.local` e `ntfy.at.local` — não existem em
            # DNS público nenhum, então o navegador de outra máquina e o celular
            # só os resolvem perguntando a ELE, e é para cá que o split-DNS do
            # tailnet aponta. Sem isso o nome não resolve fora da máquina, e a
            # URL que a pessoa digita não abre.
            dns = _call(fake, "at-dnsmasq")
            self.assertIn("100.64.0.1:53:53/udp", dns)
            self.assertIn("100.64.0.1:53:53/tcp", dns)

    def test_without_a_network_the_site_is_bills_own_name(self):
        # O estado suportado, e não um degradado: a máquina não está em rede
        # privada nenhuma, e o site é o nome que o AT responde (§7a) — um
        # NOME, e não o laço, porque o portão recusa um domínio de cookie sem
        # ponto e o TLS precisa de um nome para o SNI. Os dois foram medidos.
        self.assertEqual(env.site_host(), env.NAME)
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        self.assertIn(f"https://{env.NAME} {{",
                      (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"))
        self.assertIn(f"address=/{env.NAME}/{env.LOOP}",
                      (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"))


class TheAddress(FolderCase):
    """The race the retired environment measured, inherited by the orchestrator."""

    def test_an_address_this_machine_has_is_ready(self):
        self.assertTrue(env.address_ready(env.LOOP))

    def test_an_address_that_is_nobodys_is_not(self):
        self.assertFalse(env.address_ready(NOBODY))

    def test_the_wait_gives_up_and_says_so_instead_of_starting_a_dead_port(self):
        # A container published on an address the machine does not have comes up
        # RUNNING AND WITHOUT ITS PORT — so it is not started at all.
        lost = env.Service(
            name="dnsmasq",
            label="services.dnsmasq.name",
            image=_service("dnsmasq").image,
            ports=(env.Port(53, "udp", address=NOBODY),),
        )
        self.runtime()
        with mock.patch.object(env, "SERVICES", (lost,)), \
                mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr(
            "services.up.no_address", service=i18n.tr("services.dnsmasq.name"),
            address=NOBODY,
        ), text)


class TheProbe(FolderCase):
    """`environment.inside` — como o deploy pergunta a um serviço de dentro da rede.

    Os serviços respondem na rede e em lugar nenhum mais (§7c), então uma
    pergunta feita do host não alcança nada. Esta é a estrada, e o que se lê aqui
    é o argv do container que ela usa — e o fato de o segredo nunca entrar nele.
    """

    def answered(self, stdout: str, returncode: int = 0):
        """Uma resposta do runtime sem runtime: só o que a leitura consome."""
        answer = SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")
        return mock.patch.object(podman, "run", lambda args, **kw: answer)

    def test_the_probe_stands_on_the_environments_network_and_goes_away(self):
        fake = self.runtime()
        env.inside("http://at-webapp:12345/api/state", {})
        argv = fake.calls[0]
        self.assertEqual(argv[:2], ["run", "--rm"])
        self.assertIn(env.NETWORK, argv)
        self.assertIn("--entrypoint", argv)
        self.assertIn(_service(env.CADDY).image.reference(), argv)

    def test_the_headers_never_enter_the_argv(self):
        # Um argv é um `ps` nesta máquina, e os dois headers da identidade selada
        # são o segredo do portão e um nome. O que os carrega é a ENTRADA do
        # comando — a mesma regra que a senha do notificador segue.
        fake = self.runtime()
        env.inside("http://at-webapp:12345/api/state",
                   {"Remote-User": "Rafael", caddy.GATE_HEADER: "segredo"})
        argv = fake.calls[0]
        self.assertNotIn("segredo", argv)
        self.assertNotIn("Rafael", argv)
        self.assertIn(f'header = "{caddy.GATE_HEADER}: segredo"',
                      fake.given[0]["input"])
        self.assertIn('header = "Remote-User: Rafael"', fake.given[0]["input"])

    def test_a_name_with_a_quote_is_the_name_and_not_the_syntax(self):
        fake = self.runtime()
        env.inside("http://x/y", {"Remote-User": 'Rafael "chefe"'})
        self.assertIn('header = "Remote-User: Rafael \\"chefe\\""',
                      fake.given[0]["input"])

    def test_the_status_comes_back_as_a_number(self):
        for stdout, expected in (("403\n", 403), ("200", 200),
                                 ("", None), ("curl: (7) refused", None)):
            with self.subTest(stdout=stdout):
                with self.answered(stdout):
                    self.assertEqual(env.inside("http://x/y", {}), expected)

    def test_a_probe_that_could_not_run_is_not_a_status(self):
        # "Não deu para saber" não é "foi recusado": um runtime que não conseguiu
        # rodar o container responde nada, e quem pergunta trata isso como a
        # própria falha — e nunca como uma recusa inventada.
        with self.answered("200", returncode=1):
            self.assertIsNone(env.inside("http://x/y", {}))

    def test_the_edge_probe_keeps_the_name_and_goes_to_the_container(self):
        # §7f: a estrada do celular é um NOME, e o `connect-to` é o que deixa o
        # nome no SNI e no `Host` enquanto a conexão vai para a borda — o
        # resolver de quem roda o comando fica de fora, e o do celular é outro.
        fake = self.runtime()
        env.through_edge("https://ntfy.at.local/at/json?poll=1", {})
        argv = fake.calls[0]
        self.assertEqual(argv[:2], ["run", "--rm"])
        self.assertIn(env.NETWORK, argv)
        self.assertIn(_service(env.CADDY).image.reference(), argv)
        self.assertIn("https://ntfy.at.local/at/json?poll=1", argv)
        self.assertIn(f'connect-to = "ntfy.at.local:{env.PORT}:'
                      f'{env.container(env.CADDY)}:{env.PORT}"',
                      fake.given[0]["input"])

    def test_the_edge_probe_carries_the_token_on_the_input_and_not_the_argv(self):
        # A mesma regra do `inside`: um argv é um `ps` nesta máquina.
        fake = self.runtime()
        env.through_edge("https://ntfy.at.local/at/json?poll=1",
                         {"Authorization": "Bearer tk_segredo"})
        self.assertNotIn("tk_segredo", fake.calls[0])
        self.assertIn('header = "Authorization: Bearer tk_segredo"',
                      fake.given[0]["input"])

    def test_the_edge_probe_answers_a_number_and_nothing_else(self):
        for stdout, expected in (("200\n", 200), ("403", 403),
                                 ("", None), ("curl: (7) refused", None)):
            with self.subTest(stdout=stdout):
                with self.answered(stdout):
                    self.assertEqual(
                        env.through_edge("https://ntfy.at.local/at/json?poll=1", {}),
                        expected)
        with self.answered("200", returncode=1):
            self.assertIsNone(
                env.through_edge("https://ntfy.at.local/at/json?poll=1", {}))


class TheDown(FolderCase):
    """`down` takes the containers, and the folder stays where it is."""

    def test_every_container_bill_started_is_removed(self):
        fake = self.runtime()
        _, text = self.quiet(env.down)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(["rm", "--force", env.container(service.name)], fake.calls)
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)
        self.assertIn(i18n.tr("services.down.done", where=env.state("dnsmasq").parent), text)

    def test_the_folder_is_not_touched(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        before = (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8")
        self.quiet(env.down)
        self.assertEqual((env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"), before)

    def test_without_a_podman_there_is_nothing_to_bring_down(self):
        _, text = self.quiet(env.down)
        self.assertIn(i18n.tr("services.no_podman.down"), text)


class TheStatus(FolderCase):
    """What is standing, read off the runtime and said in AT's words."""

    def test_the_status_line_a_person_reads_carries_no_pin(self):
        self.runtime(running="true")
        _, text = self.quiet(env.status)
        self.assertNotIn("sha256:", text)

    def test_a_running_service_is_said_to_be_up(self):
        self.runtime(running="true")
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.status.running"), text)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(i18n.tr(service.label), text)
                self.assertIn(service.image.shown(), text)

    def test_the_services_are_a_table_and_not_a_sentence_each(self):
        # Cinco linhas com a mesma forma são cinco linhas que ninguém compara, e
        # o que se lê aqui é a COLUNA. O desenho é o mesmo da listagem da `cli`
        # (`ui/words.table`), para os dois artefatos imprimirem tabela igual.
        self.runtime(running="true")
        _, text = self.quiet(env.status)
        lines = text.splitlines()
        # O relatório COMEÇA na tabela: nada antes dela, nem linha vazia — o
        # estado dos serviços é a resposta inteira.
        self.assertTrue(lines[0].startswith(i18n.tr("services.status.head.service")),
                        f"o relatório não começa na tabela: {lines[0]!r}")
        head = next(
            line for line in lines
            if i18n.tr("services.status.head.state") in line
        )
        for name in ("service", "state", "image"):
            with self.subTest(column=name):
                self.assertIn(i18n.tr(f"services.status.head.{name}"), head)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                row = next(line for line in lines
                           if line.startswith(i18n.tr(service.label)))
                self.assertIn(service.image.shown(), row)

    def test_a_service_that_is_there_and_stopped_is_still_installed(self):
        # O container parou, mas a coisa ESTÁ aqui — e é isso que a pessoa
        # pergunta. Criado, parado, removido: esse é o vocabulário do runtime, e
        # um relatório que responde nele responde o que ninguém perguntou.
        self.runtime(running="false")
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.status.installed"), text)

    def test_a_service_whose_image_is_not_here_is_not_installed(self):
        # "não instalado" CONTÉM "instalado": o que se lê é a linha do serviço,
        # e não a presença da palavra em qualquer lugar do texto.
        self.runtime(fails=("container", "image"))
        _, text = self.quiet(env.status)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                row = next(line for line in text.splitlines()
                           if line.startswith(i18n.tr(service.label)))
                self.assertIn(i18n.tr("services.status.missing"), row)
                self.assertIn(service.image.shown(), row)

    def test_a_service_that_is_up_says_so(self):
        self.runtime(running="true")
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.status.running"), text)

    def test_the_three_states_are_the_whole_vocabulary(self):
        # O que a tabela responde, e nada mais: **não instalado, instalado, em
        # execução**. As três são conferidas — a imagem no disco, o container
        # rodando — e não inferidas de um pino ou de uma história.
        for fails, expected in (
            (("container", "image"), "missing"),
            (("container",), "installed"),
            ((), "running"),
        ):
            with self.subTest(expected=expected):
                self.runtime(fails=fails)
                _, text = self.quiet(env.status)
                self.assertIn(i18n.tr(f"services.status.{expected}"), text)

    def test_the_notifiers_credentials_are_said_only_with_the_notifier_up(self):
        # O relato: as duas linhas do notificador apareciam para quem nem tem o
        # ntfy. Elas são fatos sobre um serviço DE PÉ, e um credencial que
        # existiria para um notificador que ninguém subiu não é um fato.
        self.runtime(fails=("container",))
        _, text = self.quiet(env.status)
        self.assertNotIn(
            i18n.tr("services.notifier.credential.absent", where=notifier.token_file()),
            text,
        )
        self.assertNotIn(
            i18n.tr("services.notifier.phone.absent", where=notifier.phone_file()),
            text,
        )

    def test_without_a_podman_the_environment_has_nothing_standing(self):
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.no_podman.status"), text)

    def test_the_deliverys_credential_is_reported_by_its_file_and_never_its_value(self):
        # §7f: what a person needs to know is that the credential exists and
        # WHERE it lives — the value is a secret and is never printed.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr(
            "services.notifier.credential.at", where=notifier.token_file(),
            topic=notifier.TOPIC, scope=notifier.SCOPE,
        ), text)
        self.assertNotIn(DRAWN_TOKEN, text)

    def test_a_notifier_that_never_got_a_credential_says_so(self):
        self.runtime()
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.notifier.credential.absent",
                              where=notifier.token_file()), text)


class TheWebappContainer(FolderCase):
    """§7c: the WebApp as a container, in the folder it already runs from."""

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        return fake

    def test_the_webapp_publishes_nothing_and_answers_on_the_networks_address(self):
        # **O defeito que isto tranca, medido**: com o app no laço, nem a porta
        # publicada nem a borda o alcançam — a porta publicada entrega no
        # endereço de rede do container, e a borda é outro container cujo
        # `127.0.0.1` é ela mesma. Então o app atende na rede.
        #
        # A porta é a do PRÓPRIO app (§7c): o que a exposição move é o endereço
        # que a PESSOA alcança, nunca o que o WebApp ouve.
        service = _service(env.WEBAPP)
        self.assertEqual(env.ports_of(service), ())
        self.assertEqual(env.WEBAPP_PORT, webapp.DEFAULT_PORT)
        self.assertEqual(env.WEBAPP_HOST, env.ALL)

    def test_the_container_mounts_the_working_folder_at_the_same_path(self):
        # §7a's contract, measured in the retired environment and inherited: the
        # app's own database stores the absolute path, so the same path has to
        # exist inside the container or every row points at nothing.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        root = str(env.paths.working_folder())
        self.assertIn(f"{root}:{root}:Z", argv)

    def test_what_runs_inside_is_the_artifact_the_folder_carries(self):
        # §7c: the container is not a second AT. What it executes is the
        # binary this folder holds, told to serve the WebApp on the network.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        self.assertEqual(argv[-6:],
                         [env.binary(), "webapp", "--port", str(env.WEBAPP_PORT),
                          "--host", env.WEBAPP_HOST])
        self.assertTrue(argv[-6].startswith(str(env.paths.working_folder())))

    def test_the_image_carries_nothing_of_bills_and_is_pinned(self):
        # The blast radius §7c is about: what the container can reach is the
        # mount, and the base is a pin like every other (§3).
        service = _service(env.WEBAPP)
        self.assertTrue(service.image.at_the_pin())
        self.assertEqual(service.image, env.WEBAPP_IMAGE)
        self.assertNotIn("at", service.image.repo)

    def test_the_webapp_comes_up_before_the_edge_that_proxies_to_it(self):
        names = [service.name for service in env.SERVICES]
        self.assertLess(names.index(env.WEBAPP), names.index("caddy"))

    def test_the_webapp_is_told_where_its_gate_is(self):
        # A container cannot see the host's loop, so the environment names the
        # provider's address itself — the provider's container name, on the
        # network the two share (§7c). Asking `127.0.0.1` from inside would be
        # asking the WebApp's own loop.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        self.assertIn("--env", argv)
        self.assertIn(f"{env.GATE_ENV}={env.container(env.IDENTITY)}:{env.IDENTITY_PORT}",
                      argv)

    def test_the_webapp_is_told_which_folder_it_serves(self):
        # **O defeito que isto tranca, medido num ensaio**: rodando de um
        # checkout, o artefato que o container executa mora em
        # `<pasta>/dist/at-cli`, e o app que lesse a pasta de onde o binário
        # está tomaria `<pasta>/dist` pela pasta da pessoa — sem `App/`, ele
        # pediria confirmação de uma Pasta de Trabalho nova, e um container não
        # tem terminal para responder. É um WebApp que nunca serve.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        self.assertIn(f"{env.paths.ROOT_ENV}={env.paths.working_folder()}", argv)

    def test_a_service_that_needs_nothing_is_told_nothing(self):
        fake = self.up()
        for name in ("dnsmasq", env.IDENTITY, "caddy", env.NOTIFIER):
            with self.subTest(service=name):
                self.assertNotIn("--env", _call(fake, env.container(name)))


class TheWebappBehindIt(FolderCase):
    """The Caddy publishes the WebApp, and this is where that pair cannot drift."""

    def test_the_site_the_container_caddy_serves_is_bills_and_reaches_it_by_name(self):
        # O site continua sendo o do §7e, e o que muda é o que "127.0.0.1" quer
        # dizer deste lado: o backend é o NOME do WebApp na rede, e o site se
        # liga em todos os endereços do container — porque o nome que o
        # certificado carrega não é um endereço que o container tenha.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f"https://{env.NAME} {{", text)
        self.assertIn(f"\tbind {env.ALL}", text)
        self.assertIn(
            f"reverse_proxy {env.container(env.WEBAPP)}:{env.WEBAPP_PORT}", text)
        self.assertNotIn(f"reverse_proxy {env.LOOP}:", text)


class TheNames(FolderCase):
    """Os nomes do ambiente: o do site, o do notificador e o da CA (§7a, §7f).

    O ambiente responde por UM domínio (`at.local`) e cada serviço que é
    alcançado por um nome pendura o dele embaixo: o site fica com o domínio, o
    notificador responde em `ntfy.at.local`, e a CA do AT em `cert.at.local` —
    o único que não tem serviço atrás, e que existe para o aparelho que precisa
    confiar no certificado poder BUSCÁ-lo em vez de receber um caminho de
    arquivo. Quem responde os três é o `dnsmasq`, com o endereço onde a borda
    está de fato — e o que se lê aqui é o que a subida ESCREVE, que é a única
    coisa que esta suíte pode ler.
    """

    def test_the_environment_owns_one_domain_and_the_services_hang_under_it(self):
        self.assertEqual(env.NAME, "at.local")
        self.assertEqual(env.site_host(), env.NAME)
        self.assertEqual(env.notifier_host(), f"{env.NOTIFIER_HOST}.{env.NAME}")
        self.assertEqual(env.cert_host(), f"{env.CERT_HOST}.{env.NAME}")

    def test_the_dns_answers_every_name_with_the_address_the_edge_is_at(self):
        # **Nome a nome, e não um curinga.** `address=/.at.local/…` responderia
        # por um nome que ninguém pediu — a borda não tem certificado para ele,
        # e a pessoa levaria um erro de handshake em vez de "esse nome não
        # existe". Uma linha por nome é o que o ambiente responde.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        conf = (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8")
        for name in env.names():
            with self.subTest(name=name):
                self.assertIn(f"address=/{name}/{env.LOOP}", conf)
        self.assertNotIn("*", conf)
        self.assertEqual(env.names(),
                         (env.site_host(), env.notifier_host(), env.cert_host()))

    def test_the_dns_follows_the_edge_and_not_the_loop_when_there_is_a_network(self):
        # O endereço é o da rede quando há uma (§7e) — para os TRÊS nomes, que é
        # o que diz que a rede decide onde e não quais.
        with mock.patch.object(vpn, "address", lambda call=None: "100.64.0.1"), \
                mock.patch.object(env, "address_ready", lambda address: True):
            self.runtime()
            self.quiet(env.up, secret=self.phrase)
            conf = (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8")
        for name in env.names():
            with self.subTest(name=name):
                self.assertIn(f"address=/{name}/100.64.0.1", conf)

    def test_the_edge_serves_the_second_name_with_its_own_certificate(self):
        # A borda serve o nome do notificador num bloco de site dele, com o
        # `tls internal` que emite o certificado POR NOME, e com o `bind` do
        # container — a mesma razão do site: o nome não é um endereço que o
        # container tenha.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f"https://{env.notifier_host()} {{", text)
        self.assertIn(f"reverse_proxy {env.container(env.NOTIFIER)}:{env.NOTIFIER_PORT}",
                      text)
        # Três blocos de site, e cada um com o `tls internal` — o certificado de
        # cada nome é emitido por nome.
        self.assertEqual(text.count("\ttls internal"), 3)
        self.assertEqual(text.count(f"\tbind {env.ALL}"), 3)

    def test_the_edge_serves_the_ca_of_the_at_out_of_a_file(self):
        # **O terceiro nome não tem serviço atrás: ele tem um ARQUIVO.** Quem
        # responde é a borda, e o que ela devolve é o `root.crt` que ela mesma
        # emitiu — o MESMO arquivo que a pessoa importa no aparelho
        # (`authority_file`), dito aqui com o caminho de DENTRO do container, que
        # é quem lê o arquivo: a pasta de estado vira `/data` lá dentro.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f"https://{env.cert_host()} {{", text)
        authority = caddy.authority_file(env.CADDY_DATA)
        self.assertEqual(authority, Path(env.CADDY_DATA) / caddy.AUTHORITY)
        self.assertIn(f"\trewrite * {authority}", text)
        self.assertIn("\tfile_server", text)

    def test_the_ca_is_not_a_folder_and_neither_name_goes_through_the_ask(self):
        # **A pasta da CA carrega a CHAVE PRIVADA ao lado do certificado** —
        # `root.key`, `intermediate.key` —, então o site é o ARQUIVO e nunca o
        # diretório: todo pedido é reescrito sobre ele, e não há caminho que
        # alcance o resto do storage. E a pergunta fica fora dos DOIS: quem
        # precisa da CA é um aparelho que ainda não confia nela, e um
        # `forward_auth` ali seria uma pergunta cujo certificado é a resposta.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        block = text[text.index(f"https://{env.cert_host()} {{"):]
        self.assertNotIn("forward_auth", block)
        self.assertNotIn(caddy.GATE_HEADER, block)
        self.assertNotIn("reverse_proxy", block)
        self.assertNotIn(f"\troot * {env.CADDY_DATA}", block)

    def test_the_notifier_name_never_goes_through_the_ask(self):
        # A medição que esta fatia NÃO repete: atrás do portão o notificador
        # responde `subscribers=0`, porque o app do celular pega o 302 e nunca
        # conecta. O bloco dele é um dos que não têm pergunta nenhuma.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        start = text.index(f"https://{env.notifier_host()} {{")
        block = text[start:text.index(f"https://{env.cert_host()} {{")]
        self.assertNotIn("forward_auth", block)
        self.assertNotIn(caddy.GATE_HEADER, block)
        # E a pergunta continua no site: os nomes não se confundem.
        self.assertIn("forward_auth", text[:text.index(f"https://{env.notifier_host()} {{")])

    def test_the_public_url_of_the_notifier_is_its_name(self):
        # O `base-url` que o ntfy devolve dentro de cada alerta é o que o
        # CELULAR abre, então é o nome — e não o laço, que é onde o AT publica.
        self.assertEqual(env.notifier_public_url(),
                         f"https://{env.notifier_host()}")
        self.assertIn(env.notifier_host(), env.notifier_public_url())
        self.assertNotEqual(env.notifier_public_url(), env.notifier_url())

    def test_the_default_port_is_not_written_and_another_one_is(self):
        # `https://at.local` e `https://at.local:443` são o mesmo endereço, e o
        # primeiro é o que a pessoa digita; outro porto aparece, porque aí ele é
        # a informação.
        self.assertEqual(caddy.address(env.site_host(), env.PORT),
                         f"https://{env.site_host()}")
        self.assertEqual(caddy.address("at.local", 8443), "https://at.local:8443")


class TheNotifier(FolderCase):
    """§7f's notifier: the service, the memory it keeps, and the rule it inherits.

    The notifier is the one service of §7 the edge fronts WITHOUT asking about,
    and the rule that keeps it out of the gate is a MEASUREMENT and not a
    preference — which is why it is read here as the absence of the gate in
    everything the environment writes around it: no `forward_auth`, no gate
    secret, and no line of it in the provider's access rule.
    """

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        return fake

    def conf(self) -> str:
        return (env.state(env.NOTIFIER) / env.NOTIFIER_YAML).read_text(encoding="utf-8")

    def test_the_notifier_publishes_on_the_loop_at_bills_own_port(self):
        # §7f: "publicado no loop". The address is the measured rule (§7a) and
        # the port is AT's: ntfy's own default is 80, under the kernel's
        # low-port rule, and §3's elevation asks for DNS's 53 and nothing else.
        service = _service(env.NOTIFIER)
        self.assertEqual([port.published() for port in service.ports],
                         [f"127.0.0.1:{env.NOTIFIER_PORT}:{env.NOTIFIER_PORT}/tcp"])
        self.assertGreater(env.NOTIFIER_PORT, 1024)

    def test_the_notifier_is_told_to_serve(self):
        # MEASURED against the image at the pin: its entrypoint is `ntfy` and it
        # carries no `CMD` — run with nothing after the image, it prints its own
        # help and exits, which is a notifier that never comes up. So the
        # subcommand is a decision of AT's and not the image's.
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        argv = _call(fake, env.container(env.NOTIFIER))
        self.assertEqual(argv[-1], "serve")
        self.assertEqual(argv[-2], _service(env.NOTIFIER).image.reference())

    def test_the_notifier_comes_up_after_everything_it_does_not_front(self):
        # Nothing the environment fronts depends on it: no edge proxies to it
        # and no gate asks it anything — so it stands after all of them, which
        # is also §7f's own place as the last step of §7.
        names = [service.name for service in env.SERVICES]
        self.assertEqual(names[-1], env.NOTIFIER)

    def test_everything_the_notifier_remembers_lives_in_the_folder(self):
        # §7f: "o estado dele vive em `App/services/<serviço>/` como todo outro,
        # que é o que faz o tópico e a memória dele sobreviverem a um backup".
        # The cache has no default in ntfy — an unset one is a memory that dies
        # with the container —, and the auth database defaults to `/var/lib/ntfy`,
        # outside the folder the backup covers.
        service = _service(env.NOTIFIER)
        hosts = [mount.host for mount in service.mounts]
        self.assertIn("", hosts)       # `/etc/ntfy`: what AT wrote for it
        self.assertIn("data", hosts)   # `/var/cache/ntfy`: what it keeps
        self.up()
        text = self.conf()
        for held in ("cache.db", "attachments", "user.db"):
            with self.subTest(file=held):
                self.assertIn(f'"{env.NOTIFIER_DATA}/{held}"', text)

    def test_it_listens_where_it_publishes_and_says_where_it_is(self):
        # The port is decided once, in the `Port` the container publishes and in
        # the line ntfy reads. **E o endereço que ele DEVOLVE é outro de
        # propósito**: quem lê o link de dentro do alerta é o celular, então é o
        # NOME; quem publica é o AT, e ele fala com o serviço pelo laço
        # (`notifier_url`), onde o alerta não depende do DNS nem da borda.
        self.up()
        text = self.conf()
        self.assertIn(f'listen-http: ":{env.NOTIFIER_PORT}"', text)
        self.assertIn(f'base-url: "{env.notifier_public_url()}"', text)
        self.assertNotIn(f"base-url: \"http://{env.LOOP}", text)

    def test_the_edge_in_front_of_it_is_declared_to_ntfy(self):
        # O ntfy exige `behind-proxy` quando há um proxy na frente — sem a
        # linha, ele lê todo pedido como vindo do endereço da borda, e a
        # limitação por visitante vira um balde só para todo mundo.
        self.up()
        self.assertIn("behind-proxy: true", self.conf())

    def test_the_door_is_shut_to_whoever_brings_no_token(self):
        # §6: "No `ntfy`, isso é a ACL por tópico: o AT publica, o celular lê,
        # e nenhum dos dois tokens serve para o resto". A default of read-write
        # would make the token decorative.
        self.up()
        self.assertIn('auth-default-access: "deny-all"', self.conf())

    def test_the_certificate_the_phone_imports_is_the_edges_own_ca(self):
        # O certificado da borda é `tls internal` — a CA do próprio Caddy —, e o
        # app do ntfy não usa o cofre de certificados do aparelho (medido): o que
        # a pessoa importa é ESTE arquivo, e ele mora na pasta de estado do
        # serviço, que é a pasta que o backup cobre (§3). É o mesmo storage que o
        # container monta, e é o `notifier` quem o nomeia na mensagem do celular.
        caddy_service = _service(env.CADDY)
        self.assertEqual(caddy_service.mounts[1].host, env.CADDY_STORAGE)
        self.assertEqual(env.authority_file(),
                         env.state(env.CADDY) / env.CADDY_STORAGE
                         / "pki" / "authorities" / "local" / "root.crt")
        self.assertTrue(str(env.authority_file()).startswith(
            str(env.state(env.CADDY))))

    def test_the_gate_does_not_front_the_notifier(self):
        # Measured in the retired environment and inherited: behind Authelia the
        # notifier answered `subscribers=0` — the gate authenticates by redirect
        # and session cookie, and the phone app takes the 302 and never connects
        # —, and `101` without it. **A borda passa a servi-lo, e a porta que ela
        # não abre é a pergunta**: o bloco dele é um site sem `forward_auth` e
        # sem o segredo, e a regra de acesso do provedor não o nomeia. Quem
        # chega nele continua batendo na ACL por tópico.
        fake = self.up()
        caddyfile = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        block = caddyfile[caddyfile.index(f"https://{env.notifier_host()} {{"):]
        self.assertNotIn("forward_auth", block)
        self.assertNotIn(caddy.GATE_HEADER, block)
        identity = (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")
        # O NOME que o ambiente dá ao serviço, e não a palavra: o `notifier` do
        # Authelia é uma chave DELE — é assim que ele diz o que tem a contar a
        # alguém —, e não §7f entrando na borda.
        self.assertNotIn(env.container(env.NOTIFIER), identity)
        self.assertNotIn(env.notifier_host(), identity)
        argv = _call(fake, env.container(env.NOTIFIER))
        self.assertNotIn(env.GATE_ENV, argv)
        self.assertNotIn(caddy.GATE_HEADER, argv)

    # ------------------------------------------------------ §7f's delivery ---

    def test_up_creates_the_deliverys_credential_in_the_notifier(self):
        # §7f's other half, and the reason the environment comes up COMPLETE: the
        # service, and AT's own credential inside it — the account, the scope,
        # and the token (`services/notifier.py`).
        self.runtime()
        _, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(notifier.token(self.phrase_key()), DRAWN_TOKEN)
        self.assertIn(i18n.tr(
            "services.notifier.drawn", where=notifier.token_file(),
            topic=notifier.TOPIC, scope=notifier.SCOPE,
        ), text)
        # The value is a secret: it is kept, and it is never said.
        self.assertNotIn(DRAWN_TOKEN, text)
        # **E o que fica na pasta é o ENVELOPE** (item 50): o mesmo valor que o
        # `phone-token` do celular, selado sob o escopo do serviço dono.
        kept = notifier.token_file().read_text(encoding="utf-8")
        self.assertNotIn(DRAWN_TOKEN, kept)
        self.assertTrue(vault.envelopes(kept))
        # E quem o abre é a Frase: o que a pasta guarda volta a ser o valor.
        self.assertEqual(self.value(notifier.token_file(), env.NOTIFIER),
                         DRAWN_TOKEN)

    def test_the_credential_is_kept_SEALED_at_0600_and_never_in_an_argv(self):
        # O que a pasta guarda de um valor que o AT sorteia é o envelope (§4), e
        # o arquivo é um `0600` de sempre: nunca impresso, nunca no argv — o que
        # nesta máquina quer dizer nunca num `ps`.
        fake = self.up()
        mode = stat.S_IMODE(notifier.token_file().stat().st_mode)
        self.assertEqual(mode, 0o600, f"the credential is readable by others: {mode:o}")
        self.assertNotIn(DRAWN_TOKEN, [part for call in fake.calls for part in call])
        self.assertNotIn(DRAWN_TOKEN,
                         notifier.token_file().read_text(encoding="utf-8"))

    def test_the_credential_is_scoped_to_the_topic(self):
        # §3's delimited scope, mirrored: AT talks to the service, and the
        # credential it carries publishes and does nothing else. `write-only` on
        # the topic is the scope, in ntfy's own word.
        fake = self.up()
        self.assertIn(["exec", "-i", env.container(env.NOTIFIER), "ntfy", "access",
                       notifier.USER, notifier.TOPIC, notifier.SCOPE], fake.calls)

    def test_a_credential_already_kept_is_not_drawn_again(self):
        # Two credentials are an old token still valid in a database nobody
        # looks at; whoever wants a new one deletes the file and brings the
        # environment up again — the same rule the gate's secret follows.
        self.up()
        held = notifier.token(self.phrase_key())
        _, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(notifier.token(self.phrase_key()), held)
        self.assertNotIn(i18n.tr(
            "services.notifier.drawn", where=notifier.token_file(),
            topic=notifier.TOPIC, scope=notifier.SCOPE,
        ), text)


# ------------------------------------------------------ the state, sealed ---

# The names the catalogue below uses for the values the deploy DRAWS — each one a
# value a service signs or proves with, kept in the folder so that it outlives
# the container (§7b). They are names and not values: what the catalogue says is
# WHICH of them each file carries, and `TheClearState` reads the values back to
# PROVE the claim — a classification nobody measures is a comment.
GATE = "the gate's secret"
SESSION = "the provider's session secret"
ENCRYPTION = "the provider's storage key"
SIGNATURE = "the provider's reset-password signature"
TOKEN = "AT's notifier credential"
PHONE = "the phone's notifier credential"

# Nobody's phone credential: the shape is ntfy's own, and what the catalogue
# reads is that the deploy keeps it at 0600 — the one value it also SAYS, once,
# because a phone is not the machine and the only road there is a person's eyes
# (`notifier.subscribe`).
DRAWN_PHONE = "tk_zyxwvutsrqponmlkjihgfedcba9876"

# The three folders a CONTAINER fills and the deploy only creates: the Caddy's
# storage (the local CA, and the private keys of it), the provider's `data` (its
# database) and the notifier's (the auth database). What lands in them is the
# container's act and not AT's write — which is the whole reason they are
# asserted EMPTY below, and the reason the audit of item 50 names them apart.
FILLED_BY_CONTAINERS = (
    (env.CADDY, env.CADDY_STORAGE),
    (env.IDENTITY, "data"),
    # O aviso que o provedor dá, e ele é do container como os outros: o arquivo
    # de configuração o aponta para `/config/notifications`, e é a pasta de
    # estado que o guarda porque a cópia materializada de `/config` morre com a
    # subida (`Mount` com `host`).
    (env.IDENTITY, env.IDENTITY_NOTIFICATIONS),
    (env.NOTIFIER, "data"),
)


def _sealed_values() -> dict[str, tuple[Path, str]]:
    """Onde cada valor que o AT SELA mora, e o escopo da chave que o abre (item 50).

    São os SEIS deste corte — o portão, que é do Caddy, os três do provedor e
    **as duas pontas do notificador** (§7f, o corte `d`) —, e o par
    `(arquivo, escopo)` é o que a subida usa para os abrir: o escopo é o serviço
    dono do valor (§4), e é o nome dele que a pasta não precisa carregar porque o
    arquivo já o diz.
    """
    return {
        GATE: (caddy.gate_file(), env.CADDY),
        SESSION: (env.state(env.IDENTITY) / env.IDENTITY_SESSION, env.IDENTITY),
        ENCRYPTION: (env.state(env.IDENTITY) / env.IDENTITY_ENCRYPTION,
                     env.IDENTITY),
        SIGNATURE: (env.state(env.IDENTITY) / env.IDENTITY_JWT, env.IDENTITY),
        TOKEN: (notifier.token_file(), env.NOTIFIER),
        PHONE: (notifier.phone_file(), env.NOTIFIER),
    }


def _catalogue() -> tuple[tuple[Path, int | None, frozenset[str]], ...]:
    """What the deploy writes into the folder: the file, the mode, the secrets.

    **This is item 50's audit, turned into a gate.** The philosophy of the folder
    is that it is copied WITHOUT encryption and that what a PERSON writes in it is
    theirs — so what the AT creates is the part that has to stop being readable in
    a copy, and this is the measurement of what that part is today: **os SEIS
    valores que o AT sorteia saem daqui como o envelope do cofre** — os quatro do
    corte `c` e as duas pontas do notificador, que este corte selou. The scanner
    does not delimit it: measured on a folder the deploy filled,
    `gitleaks 8.30.1` flags
    ONE of these files — the provider's YAML, where each value has its keyword on
    the line — and is BLIND to the Caddyfile, to the three bare-valued files and
    to the two notifier credentials, because its default rules read a keyword
    beside the value and those six are the value and nothing else. So the scan
    confirms a leak and never delimits one; the delimitation is this list.

    The mode is `None` where the writer left it to the umask — which is every
    file but the two notifier credentials, and that is the finding: the deploy
    already knows how to keep a secret to itself at `0600` (`notifier._sealed`) and
    does it in one place only.

    **A linha não mudou com o selo, e é isso que a faz um gate**: o que mudou
    foi o que ela CARREGA — o envelope no lugar do valor —, e `marks` é quem o
    lê. Um arquivo que parasse de ser escrito, ou um valor que aparecesse em
    claro num deles, continua sendo uma linha do catálogo que falha.
    """
    identity = env.state(env.IDENTITY)
    return (
        # §7b's gate: drawn by the deploy at installation, read by the Caddy (the
        # line it attaches to every request) and by AT (the check that makes an
        # identity an identity). Two files, one value.
        (caddy.gate_file(), None, frozenset({GATE})),
        (env.state(env.CADDY) / "Caddyfile", None, frozenset({GATE})),
        # The provider's three, drawn once and kept beside the file that carries
        # them; the YAML is the same three values inline, which is why it names
        # all of them.
        (identity / env.IDENTITY_SESSION, None, frozenset({SESSION})),
        (identity / env.IDENTITY_ENCRYPTION, None, frozenset({ENCRYPTION})),
        (identity / env.IDENTITY_JWT, None, frozenset({SIGNATURE})),
        (identity / env.IDENTITY_YAML, None,
         frozenset({SESSION, ENCRYPTION, SIGNATURE})),
        # The people of the folder: the DERIVATION of each credential and not the
        # credential (§4) — a value that is only ever compared, and nothing that
        # could be turned back into one.
        (identity / env.IDENTITY_USERS, None, frozenset()),
        # No secret at all: the names the DNS answers, the image the folder is
        # pinned at, and the notifier's own configuration (paths and the posture).
        (env.state("dnsmasq") / "dnsmasq.conf", None, frozenset()),
        (env.pin_file(), None, frozenset()),
        (env.state(env.NOTIFIER) / env.NOTIFIER_YAML, None, frozenset()),
        # §7f's two ends of the ACL: AT's credential and the phone's, the one
        # pair the deploy keeps to itself — a `0600` file, never in an argv and
        # never printed.
        (notifier.token_file(), 0o600, frozenset({TOKEN})),
        (notifier.phone_file(), 0o600, frozenset({PHONE})),
    )


class TheClearState(FolderCase):
    """What the deploy writes into the folder, and with what mode (item 50).

    The audit of the vault's first slice, held as a gate — e o que ele tranca
    mudou com cada corte do selo. A folder is copied without encryption, so the
    files below are the ones a copy hands over: **os SEIS valores que o AT
    sorteia chegam à pasta como o envelope do cofre** e o valor claro não está
    em arquivo nenhum dela — nem os das duas pontas do notificador, que este
    corte selou —, e o resto não é segredo nenhum.

    O catálogo é a linha por arquivo, e ele é o mesmo depois do selo: o que
    mudou é o que cada linha carrega, e é por isso que `marks` existe — a
    classificação continua sendo MEDIDA, arquivo a arquivo, e não repetida.
    """

    def up(self) -> None:
        """The environment up — the whole of the deploy's writing happens here.

        One stand-in: §7f draws the phone's credential in `subscribe`, which
        needs the notifier standing for real. Its writer is called directly — com
        a Chave da Frase, porque o que ele grava é o envelope —, so what is
        proved is the mode and the place and not the door.
        """
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        notifier.write_phone_token(DRAWN_PHONE, self.phrase_key())

    def written(self) -> set[Path]:
        """Every file the deploy wrote, by the path it wrote it at."""
        found = {where for where in env.pin_file().parent.rglob("*") if where.is_file()}
        found.add(caddy.gate_file())
        return found

    def umask(self) -> int:
        """The machine's umask, read without changing it."""
        now = os.umask(0o022)
        os.umask(now)
        return now

    def test_the_deploy_writes_exactly_what_the_catalogue_names(self):
        # Nothing new appears unclassified and nothing classified disappears: a
        # writer that lands a file nobody said carries a secret fails HERE.
        self.up()
        self.assertEqual(self.written(), {where for where, _, _ in _catalogue()})

    def test_every_secret_a_file_carries_is_there_and_no_other_one_is(self):
        # The classification is MEASURED and not repeated: what the catalogue
        # says a file carries has to be in it — o ENVELOPE, para os seis que o AT
        # sela —, e um segredo que apareça num arquivo que o catálogo não nomeia
        # é um vazamento que o catálogo perdeu.
        self.up()
        marks = self.marks()
        for where, _, carries in _catalogue():
            text = where.read_text(encoding="utf-8")
            with self.subTest(where=where):
                for name in carries:
                    self.assertIn(marks[name], text)
                for name, mark in marks.items():
                    if name not in carries:
                        self.assertNotIn(mark, text)

    def test_the_clear_value_of_a_sealed_one_is_in_no_file_of_the_folder(self):
        # **A promessa desta fatia, medida**: o que o AT sorteia não se lê numa
        # cópia da pasta. O envelope está lá, e o valor não — em arquivo nenhum
        # dela, nem no que o catálogo não nomeia.
        self.up()
        sealed = _sealed_values()
        for name, value in self.secrets().items():
            if name not in sealed or not value:
                continue
            for where, _, _ in _catalogue():
                with self.subTest(value=name, where=where):
                    self.assertNotIn(value, where.read_text(encoding="utf-8"))

    def test_the_mode_of_every_file_is_the_one_the_catalogue_declares(self):
        # `None` is the umask's, and it is what the deploy leaves for every
        # secret but the two credentials — the finding the audit is for.
        self.up()
        umask = self.umask()
        for where, mode, _ in _catalogue():
            expected = mode if mode is not None else 0o666 & ~umask
            with self.subTest(where=where):
                self.assertEqual(
                    stat.S_IMODE(where.stat().st_mode), expected,
                    f"{where.name} is {stat.S_IMODE(where.stat().st_mode):o}, "
                    f"and the catalogue says {expected:o}",
                )

    def test_the_folders_a_container_fills_are_born_empty(self):
        # The CA's private keys, the provider's database and the notifier's are
        # in the folder and are NOT AT's write: the deploy creates the folder
        # and the container fills it. Asserted empty because that is what says
        # whose act each secret is — and the audit names them so that the slice
        # that seals does not forget the one thing the deploy cannot write.
        self.up()
        for service, folder in FILLED_BY_CONTAINERS:
            where = env.state(service) / folder
            with self.subTest(where=where):
                self.assertTrue(where.is_dir())
                self.assertEqual(list(where.iterdir()), [])


class TheAccessPhrase(FolderCase):
    """A Frase de Acesso na subida: quem sela, quem abre, e o que não sobe (§4).

    A fatia que fecha a promessa do item 50 do lado de FORA: o que o AT sorteia
    não se lê na pasta — o que se lê lá é o envelope —, e o valor claro só existe
    no diretório de execução, que morre com o ambiente. Quem o escreve lá é o
    `up`, e ele só o faz com a Frase que ABRIU cada envelope: sem Frase, ou com
    uma que não abre, o ambiente não sobe e a pasta fica exatamente onde estava.
    """

    def counting(self, phrase: str = PHRASE):
        """Um leitor sem eco que conta o que lhe foi perguntado.

        Ele é o que responde por quantas vezes a Frase foi LIDA — a pergunta que
        separa a primeira subida (duas leituras, porque não há contra o que
        conferir) das seguintes (uma, porque a conferência é a abertura).
        """
        asked: list[str] = []

        def reader(question: str) -> str:
            asked.append(question)
            return phrase

        return asked, reader

    def seeded(self) -> None:
        """Uma pasta que nasceu ANTES do selo: os valores, em claro.

        É o estado que a auditoria mediu na instância, e o corte da migração é o
        seguinte: esta fatia ainda não o decide, e o que ela tem de provar é que
        ele sobe como sempre subiu — a Frase não é pedida onde não há o que abrir
        nem o que selar. **A credencial do AT entra aqui em claro também**, e não
        é detalhe: é assim que a instância a tem, e é ela que faz o `up` não ter
        o que sortear — sem ela, um sorteio viria aí e um sorteio SELA.
        """
        files.atomic_write_text(caddy.gate_file(), "o-portao-que-nasceu-em-claro\n")
        for name in env.IDENTITY_SECRETS:
            files.atomic_write_text(env.state(env.IDENTITY) / name,
                                    f"o-valor-{name}-em-claro\n")
        files.atomic_write_text(notifier.token_file(),
                                "tk_o-token-que-nasceu-em-claro\n")

    def test_the_first_boot_reads_the_phrase_twice(self):
        # **Uma Frase que SELA não tem como ser conferida depois**: a segunda
        # leitura é a única conferência possível na primeira vez, e é a mesma
        # proteção que a credencial do primeiro administrador tem (`at-cli
        # admin`) — e aqui ela vale o que ela acabou de selar.
        asked, reader = self.counting()
        self.runtime()
        outcome, _ = self.quiet(env.up, secret=reader)
        self.assertEqual(outcome, env.UP)
        self.assertEqual(len(asked), 2)

    def test_a_folder_that_already_sealed_is_read_once(self):
        # Depois da primeira vez a conferência é a ABERTURA do que a pasta
        # guarda, e ela é melhor que uma segunda leitura: dois valores selados
        # com a mesma Frase são a prova de que é a mesma.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        asked, reader = self.counting()
        outcome, _ = self.quiet(env.up, secret=reader)
        self.assertEqual(outcome, env.UP)
        self.assertEqual(len(asked), 1)

    def test_two_readings_that_disagree_draw_nothing(self):
        # A recusa ANTES de qualquer sorteio: uma pasta com valores selados sob
        # uma Frase que ninguém sabe qual é seria pior que uma pasta vazia.
        said = iter([PHRASE, "outra frase de acesso, e ela tambem e longa"])
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=lambda question: next(said))
        self.assertEqual(outcome, env.UNREADABLE)
        self.assertIn(i18n.tr("services.phrase.mismatch"), text)
        self.assertNotIn("run", fake.verbs())
        self.assertFalse(caddy.gate_file().exists())
        self.assertFalse(env.pin_file().exists())

    def test_no_terminal_is_no_phrase_and_the_folder_is_untouched(self):
        # §3's fail-closed posture, a mesma da elevação: sem terminal não se
        # pergunta, e não se sobe um ambiente que não abriu o que ele guarda.
        fake = self.runtime()
        outcome, text = self.quiet(env.up)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.phrase.no_tty"), text)
        self.assertNotIn("run", fake.verbs())
        self.assertFalse(caddy.gate_file().exists())
        self.assertFalse(env.pin_file().exists())

    def test_a_phrase_that_does_not_open_what_the_folder_keeps_does_not_come_up(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        fake = self.runtime()
        outcome, text = self.quiet(
            env.up, secret=lambda question: "uma frase que nao e a que selou")
        self.assertEqual(outcome, env.UNREADABLE)
        self.assertIn(i18n.tr("services.phrase.unopened", where=caddy.gate_file()),
                      text)
        self.assertNotIn("run", fake.verbs())

    def test_a_phrase_under_the_vaults_floor_is_refused_by_its_sentence(self):
        # O tamanho é a regra do COFRE e não desta porta (§3: quem pergunta não
        # decide a regra), e a sentença é a mesma que o `core.secrets` diz.
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=lambda question: "curta")
        self.assertEqual(outcome, env.UNREADABLE)
        self.assertIn(i18n.tr("secrets.error.phrase", min=vault.MINIMUM), text)
        self.assertNotIn("run", fake.verbs())
        self.assertFalse(caddy.gate_file().exists())

    def test_a_folder_that_never_sealed_is_not_asked(self):
        # A migração do que já está em claro é o corte seguinte do item 50, e
        # não esta fatia: uma pasta que já tem os quatro valores sobe como
        # sempre subiu — sem Frase, porque não há o que abrir nem o que selar.
        self.seeded()
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=None)
        self.assertEqual(outcome, env.UP)
        self.assertNotIn(i18n.tr("services.phrase.no_tty"), text)
        self.assertIn("run", fake.verbs())
        # E o que ela guardava continua em claro: esta fatia não migra.
        self.assertEqual(vault.envelopes(
            caddy.gate_file().read_text(encoding="utf-8")), ())

    def test_the_sealing_is_the_same_phrase_every_time(self):
        # A Chave do Cofre vem da Frase e de mais nada (§4): a mesma Frase sobre
        # os mesmos valores os abre de novo, e é isso que faz de uma cópia da
        # pasta uma pasta que volta a subir.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        first = self.value(caddy.gate_file(), env.CADDY)
        self.quiet(env.up, secret=self.phrase)
        self.assertEqual(self.value(caddy.gate_file(), env.CADDY), first)


class TheRunDirectory(FolderCase):
    """As fatias 2 e 3 do item 50: o container lê o que a subida ABRIU.

    O `--volume` de cada serviço apontava para `App/services/<serviço>/`, a pasta
    da pessoa — e é isso que impedia o selo: um arquivo selado na pasta seria um
    arquivo que o container não consegue abrir. O que esta classe prova é a
    ESTRADA e o que ela carrega: o `up` materializa o que cada serviço lê num
    diretório de execução FORA da Pasta de Trabalho, aponta o `--volume` para lá,
    e **o que ele monta é o valor, não o envelope** — a pasta de estado segue
    sendo a fonte, e ela é a que guarda o selo.

    A pergunta (2) da auditoria é respondida aqui, do lado de dentro: nenhum
    processo do container abre o cofre. Quem o abre é o `up`, uma vez, com a
    Frase, e o que os três leitores recebem é a cópia clara.
    """

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up, secret=self.phrase)
        return fake

    def test_the_run_directory_lives_outside_the_working_folder(self):
        # A pasta de trabalho é a da pessoa, e a cópia que serve a subida não é
        # dela: é FORA que ela mora, e é isso que a faz morrer com o ambiente.
        self.up()
        where = env.run_dir()
        self.assertTrue(where.is_dir())
        self.assertFalse(where.is_relative_to(env.paths.working_folder()))

    def test_the_run_directory_is_a_door_nobody_else_opens(self):
        # **Ele guarda o valor CLARO**, e o diretório de execução pode cair no
        # temporário do sistema, onde ele é de todo mundo: a porta é a pasta, e
        # ela nasce `0700` (o modo do ARQUIVO continua sendo o da umask, porque
        # quem o lê é o container).
        self.up()
        self.assertEqual(stat.S_IMODE(env.run_dir().stat().st_mode), 0o700)

    def test_the_copy_is_the_folder_with_the_values_open(self):
        # **O que o container lê é o arquivo ABERTO, e a classificação é medida
        # caminhando o catálogo**: cada valor que a pasta guarda chega à cópia
        # como o valor — é o que faz de um arquivo selado um arquivo que o
        # container consegue ler —, nenhum envelope sobra na cópia, e o valor de
        # um não aparece no arquivo de outro.
        self.up()
        values = self.secrets()
        for where, _, carries in _catalogue():
            copy = self.copy_of(where)
            if copy is None or not copy.is_file():
                continue
            text = copy.read_text(encoding="utf-8")
            with self.subTest(where=where):
                self.assertEqual(vault.envelopes(text), ())
                for name, value in values.items():
                    if value:
                        self.assertEqual(value in text, name in carries,
                                         f"{name} em {copy.name}")

    def test_the_volume_of_the_read_side_comes_from_the_run_directory(self):
        # **A classificação é MEDIDA, e não repetida**: o teste caminha o
        # manifesto. Uma pasta que o container só lê vira uma montagem do
        # diretório de execução; uma pasta que ele ENCHE fica na pasta de estado,
        # porque o que ele escreve tem de sobreviver ao container.
        fake = self.up()
        for service in env.SERVICES:
            argv = _call(fake, env.container(service.name))
            with self.subTest(service=service.name):
                for mount in service.mounts:
                    if not isinstance(mount, env.Mount):
                        continue
                    source = (env.state(service.name) / mount.host if mount.host
                              else env.materialized(service.name))
                    self.assertIn(f"{source}:{mount.container}:Z", argv)

    def test_a_service_that_reads_no_file_gets_no_copy(self):
        # O WebApp não lê arquivo nenhum do serviço DELE — o que o alcança é a
        # pasta inteira (`Mirror`, §7c) —, e um diretório vazio no diretório de
        # execução não seria o que ele monta, e sim um resto.
        self.up()
        self.assertFalse(env.materialized(env.WEBAPP).exists())

    def test_the_gate_is_materialized_and_handed_to_the_webapp(self):
        # O WebApp é o TERCEIRO leitor do portão e o único de dentro do
        # container: ele o lê pela pasta inteira que monta (`Mirror`), e o
        # `App/caddy/gate` de lá é o arquivo da PASTA — que guarda o ENVELOPE, e
        # que por isso ninguém de dentro abriria. Então ele recebe a cópia clara
        # como uma montagem própria, e o `at-cli` de dentro é told onde ela está.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        self.assertIn(f"{env.gate_materialized()}:{env.GATE_MOUNT}:Z", argv)
        self.assertIn(f"{caddy.GATE_PATH_ENV}={env.GATE_MOUNT}", argv)
        self.assertEqual(env.gate_materialized().read_text(encoding="utf-8").strip(),
                         self.value(caddy.gate_file(), env.CADDY))
        self.assertTrue(vault.envelopes(
            caddy.gate_file().read_text(encoding="utf-8")))

    def test_the_gate_the_container_reads_is_not_the_file_of_the_folder(self):
        # **O defeito que isto tranca**: quem prova a virada lia o portão do
        # ARQUIVO DA PASTA (`switch.witness`), e o que a pasta guarda agora é o
        # envelope — o WebApp compararia o envelope com o valor aberto e
        # recusaria a identidade que ele aceita. `gate_opened` é a porta certa:
        # o valor que o container lê.
        self.up()
        self.assertEqual(env.gate_opened(), self.value(caddy.gate_file(), env.CADDY))
        self.assertNotEqual(env.gate_opened(), caddy.gate_secret())

    def test_the_credentials_of_the_notifier_are_read_by_no_container(self):
        # §7f's two ends are read by AT, from OUTSIDE, and by no container: they
        # stay in the state folder and get no copy — and the state folder is no
        # longer mounted whole into the notifier, which is what put them inside
        # it. Quem as lê é o `notify`, e é a pasta que as guarda.
        fake = self.up()
        notifier.write_phone_token(DRAWN_PHONE, self.phrase_key())
        argv = _call(fake, env.container(env.NOTIFIER))
        self.assertFalse((env.materialized(env.NOTIFIER) / notifier.TOKEN_FILE).exists())
        self.assertFalse((env.materialized(env.NOTIFIER) / notifier.PHONE_FILE).exists())
        self.assertNotIn(f"{env.state(env.NOTIFIER)}:{env.NOTIFIER_CONFIG}:Z", argv)
        self.assertTrue(notifier.token_file().is_file())

    def test_down_takes_the_run_directory_with_it(self):
        # O diretório de execução é a metade que MORRE: o que o container encheu
        # está na pasta de estado, e é ela que fica.
        self.up()
        self.assertTrue(env.run_dir().is_dir())
        self.runtime()
        self.quiet(env.down)
        self.assertFalse(env.run_dir().exists())
        self.assertTrue(env.state(env.NOTIFIER).is_dir())


class TheWords(unittest.TestCase):
    """Every sentence of the environment, written in both languages.

    A key the catalog does not have answers with the key itself (§3's own
    "visible, never silent"), which is exactly why this gate exists: a test that
    compares a message against `i18n.tr(same_key)` would pass with nothing
    written at all.
    """

    def test_every_sentence_said_is_written_in_both_languages(self):
        keys = (*SAID, *(service.label for service in env.SERVICES))
        for key in keys:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(
                        i18n.text(key, code), key,
                        f"{key} is not written in {code}: the screen would show the key",
                    )

    def test_the_service_names_carry_a_description_too(self):
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                about = f"services.{service.name}.about"
                self.assertNotEqual(i18n.tr(about), about)


class TheDoor(FolderCase):
    """`at-cli services` — the cli's word for the environment."""

    def test_the_tree_offers_the_words_of_the_environment_and_the_doors_of_the_switch(self):
        node = tree.find("services")
        self.assertIsNotNone(node)
        assert node is not None
        self.assertEqual(
            [child.name for child in node.children],
            ["up", "down", "status", "switch", "forms", "notify", "phone",
             "credential"],
            "a word the dispatch takes and the help does not offer (or the "
            "other way round) is the defect §5's one-way rule exists for",
        )

    def test_status_is_what_the_wordless_command_answers(self):
        code, text = self.quiet(main, ["services"])
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.status"), text)

    def test_no_terminal_means_no_choice_and_a_refusal(self):
        # The suite runs with no tty, which is the state the offer refuses in.
        code, text = self.quiet(main, ["services", "up"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.no_podman.no_tty"), text)

    def test_the_offer_reaches_the_environment_with_the_persons_answer(self):
        code, text = self.quiet(services, ["up"], ask=lambda question: "n")
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)

    def test_a_word_it_does_not_take_is_a_usage_error(self):
        for words in (["services", "install"], ["services", "up", "extra"], ["services", "run"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_the_help_offers_the_word_and_its_children(self):
        code, text = self.quiet(main, ["help"])
        self.assertEqual(code, OK)
        self.assertIn("services", text)
        self.assertIn(
            "up, down, status, switch, forms, notify, phone, credential", text)

    def test_the_delivery_is_proved_by_hand_and_says_where_it_would_come_from(self):
        # §7f's proof, walked from the `cli`: one alert, through the credential,
        # to the topic. A folder with no credential yet does not fail silently —
        # it names the file and the command that creates it.
        code, text = self.quiet(main, ["services", "notify"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.notifier.no_token",
                              where=notifier.token_file(), topic=notifier.TOPIC), text)


if __name__ == "__main__":
    unittest.main()
