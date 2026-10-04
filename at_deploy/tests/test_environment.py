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

import base64
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
from at.core import actors, boot, cofre, files, tables
from at.encryption import vault
from at.services import caddy
from at.ui.webapp import app as webapp
from at.ui.webapp import keys as webapp_keys

from at_deploy import environment as env
from at_deploy import podman, tree, vpn
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
    # §3's second word (2026-09-28): `up` refusing a folder that already has an
    # environment, and `update` refusing one that has none yet.
    "services.up.provisioned", "services.update.unprovisioned",
    "services.update.done",
    "services.down.done", "services.status.site",
    "services.status.running", "services.status.installed", "services.status.missing",
    "services.status.head.service", "services.status.head.state",
    "services.status.head.image",
    "services.gate.drawn",
    # A migração da pasta que nasceu antes do selo (item 50, corte `f`): o ato
    # que re-sorteia e sela o que estava em claro.
    "services.migrated",
    # A forma da pasta de estado: um caminho que é ARQUIVO onde o serviço monta
    # uma pasta (ou o contrário) vira recusa dita, e não um traceback.
    "services.state.shape", "services.state.folder", "services.state.file",
    # §4's Main Key, pedida pela subida (item 50): a pergunta, a segunda
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
    # Item 27's second operator act (§7b): the credential, the derivation the
    # provider reads, and the restart that makes the new one the one it proves.
    "services.credential.changed", "services.credential.hosted",
    "services.credential.unknown", "services.credential.pending",
    "services.restarted",
)


# A Chave Principal que a suíte digita (item 50, §4). **Ela é quem sela o que a
# pasta guarda e quem o abre**, e é por isso que ela é uma só em toda esta
# suíte: um teste que lesse o valor selado com OUTRA Chave Principal não leria nada — que
# é exatamente o que a conferência da Chave Principal prova, no teste que a prova.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"


class FakeRuntime:
    """The runtime's seam, answered by a list.

    Every call is recorded — that is what most of this file reads — and the
    answers are the test's: which verbs fail, and what a container says about
    itself.
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
        # **E a pessoa digita a Chave Principal**, pelo mesmo desenho: o `up` a lê de um
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
        """A chave derivada da Chave Principal da suíte — derivada uma vez por teste.

        `vault.vault_key` é a derivação de uma frase e custa o que ela custa
        (§4); a mesma Chave Principal dentro do mesmo teste é a mesma Chave.
        """
        if self._vault_key is None:
            self._vault_key = vault.vault_key(PHRASE)
        return self._vault_key

    def value(self, where: Path, scope: str) -> str | None:
        """O valor CLARO que um arquivo da pasta guarda SELADO (item 50).

        Ele é lido ABRINDO o envelope com a Chave Principal da suíte, e nunca de um
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
        # TASK-187: o dnsmasq saiu — não há mais DNS do ambiente. A ordem que
        # sobra é a ORDER THINGS COME UP: a borda pergunta ao provedor sobre
        # todo pedido e faz proxy para o WebApp, então os dois estão antes dela.
        self.assertEqual([service.name for service in env.SERVICES],
                         [env.IDENTITY, env.WEBAPP, "caddy"])

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

    def test_the_caddy_publishes_the_site_and_nothing_else(self):
        # A borda é o que a pessoa alcança: ela publica a porta do SITE, e o
        # resto do ambiente fica no laço ou em nada. O que decide a rede de cada
        # serviço é só com quem ele fala (o módulo diz por quê).
        caddy = _service("caddy")
        self.assertEqual(caddy.network, env.NETWORK)
        self.assertEqual([port.port for port in env.ports_of(caddy)], [env.PORT])

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


def _service(name: str) -> env.Service:
    return next(service for service in env.SERVICES if service.name == name)


class ThePin(FolderCase):
    """§3: the pin only moves forward, and an instance ahead is not downgraded."""

    def test_a_folder_that_never_pinned_is_behind(self):
        self.assertEqual(env.decide(_service(env.IDENTITY), {}), env.OUTDATED)

    def test_a_folder_at_the_pin_is_at_the_pin(self):
        service = _service(env.IDENTITY)
        pins = {env.IDENTITY: {"version": service.image.version,
                            "digest": service.image.digest}}
        self.assertEqual(env.decide(service, pins), env.CURRENT)

    def test_a_folder_behind_the_binary_is_re_pinned(self):
        self.assertEqual(
            env.decide(_service(env.IDENTITY), {env.IDENTITY: {"version": "2.89", "digest": "sha256:" + "a" * 64}}),
            env.OUTDATED,
        )

    def test_a_folder_ahead_of_the_binary_warns_and_proceeds(self):
        service = _service(env.IDENTITY)
        ahead = {"version": "9.99", "digest": "sha256:" + "b" * 64}
        self.assertEqual(env.decide(service, {env.IDENTITY: ahead}), env.AHEAD)
        # And what it runs is what it HAS: the pin does not move backward.
        self.assertEqual(env.running(service, {env.IDENTITY: ahead}).version, "9.99")

    def test_a_digest_that_moved_at_the_same_version_is_out_of_date(self):
        service = _service(env.IDENTITY)
        moved = {"version": service.image.version, "digest": "sha256:" + "c" * 64}
        self.assertEqual(env.decide(service, {env.IDENTITY: moved}), env.OUTDATED)

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
        self.assertFalse(env.state(env.IDENTITY).exists())

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

    def test_the_caddy_joins_the_network_and_publishes_the_site(self):
        # A borda é um container como os outros, e as coisas que a fazem a
        # borda são a rede em que ela está — onde o WebApp e o portão estão — e a
        # porta que ela publica: a do site.
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
        self.assertIn(i18n.tr(_service(env.IDENTITY).label), text)
        self.assertNotIn("run", fake.verbs())
        self.assertFalse(env.pin_file().exists())

    def test_an_instance_ahead_warns_and_runs_what_the_folder_has(self):
        # §3: "Uma instância à frente do pino do binário avisa e prossegue: ela
        # não é rebaixada."
        ahead = {"version": "9.99", "digest": "sha256:" + "d" * 64}
        env.pin_file().parent.mkdir(parents=True, exist_ok=True)
        env.pin_file().write_text(
            json.dumps({env.IDENTITY: ahead}), encoding="utf-8"
        )
        fake = self.runtime()
        # `bring_up` and not `up`: a pin already on the folder makes `up` refuse
        # with `PROVISIONED` (2026-09-28) — the engine under test here is the
        # one `update` shares with it, not the first-time gate.
        outcome, text = self.quiet(env.bring_up, secret=self.phrase)
        self.assertEqual(outcome, env.UP)
        self.assertIn(i18n.tr(
            "services.up.ahead", service=i18n.tr(_service(env.IDENTITY).label),
            held="9.99", pin=_service(env.IDENTITY).image.version,
        ), text)
        self.assertIn(f"docker.io/authelia/authelia:9.99@{ahead['digest']}",
                      [call[-1] for call in fake.calls])
        # And the pin it leaves behind is the one it is at, still ahead.
        self.assertEqual(env.held()[env.IDENTITY]["version"], "9.99")

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


class TheUpdate(FolderCase):
    """§3's second word (2026-09-28): `up` is the first time, `update` every
    time after — the release that already replaced the binary."""

    def test_up_refuses_a_folder_that_already_has_an_environment(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.PROVISIONED)
        self.assertIn(i18n.tr("services.up.provisioned"), text)
        self.assertEqual(fake.calls, [], "a second `up` touched something")

    def test_update_refuses_a_folder_with_no_environment_yet(self):
        fake = self.runtime()
        outcome, text = self.quiet(env.update, secret=self.phrase)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr("services.update.unprovisioned"), text)
        self.assertEqual(fake.calls, [], "`update` touched a never-provisioned folder")

    def test_update_re_pins_and_recreates_every_container(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        fake = self.runtime()
        outcome, text = self.quiet(env.update, secret=self.phrase)
        self.assertEqual(outcome, env.UPDATED)
        self.assertIn(i18n.tr("services.update.done"), text)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(["rm", "--force", env.container(service.name)],
                              fake.calls)
                _call(fake, env.container(service.name))

    def test_update_leaves_what_was_already_drawn_exactly_as_it_was(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        before = self.secrets()
        self.runtime()
        self.quiet(env.update, secret=self.phrase)
        after = self.secrets()
        self.assertEqual(before, after)

    def test_an_instance_ahead_of_the_pin_is_not_downgraded_by_update_either(self):
        # A mesma regra do §3 medida em `TheUp`, agora do lado do `update`: uma
        # instância à frente avisa e segue, e não é rebaixada.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        pins = env.held()
        pins[env.IDENTITY] = {"version": "9.99", "digest": "sha256:" + "d" * 64}
        env.pin_file().write_text(json.dumps(pins), encoding="utf-8")
        fake = self.runtime()
        outcome, text = self.quiet(env.update, secret=self.phrase)
        self.assertEqual(outcome, env.UPDATED)
        self.assertIn(i18n.tr(
            "services.up.ahead", service=i18n.tr(_service(env.IDENTITY).label),
            held="9.99", pin=_service(env.IDENTITY).image.version,
        ), text)
        self.assertEqual(env.held()[env.IDENTITY]["version"], "9.99")

    def test_the_words_reach_the_cli_and_map_to_an_exit_code(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        # `up` a second time is guidance, not a failure.
        code, _ = self.quiet(services, ["up"], secret=self.phrase)
        self.assertEqual(code, OK)
        code, _ = self.quiet(services, ["update"], secret=self.phrase)
        self.assertEqual(code, OK)

    def test_update_with_no_environment_is_a_refusal_on_the_cli(self):
        self.runtime()
        code, text = self.quiet(services, ["update"], secret=self.phrase)
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.update.unprovisioned"), text)


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
        self.assertIn(f"    - domain: {env.site_host()}", text)
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

    def test_the_access_control_names_the_site(self):
        # UMA regra: o `domain` do Authelia lê o Host header sem a porta, então a
        # única linha que nomeia o site já cobre tudo o que responde no mesmo
        # nome. O portal é roteado fora da pergunta, então uma regra para ele
        # seria uma regra que nada consulta.
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
        # ARQUIVO, e ele mora na pasta de estado, que é a pasta do backup (§3).
        #
        # **O caminho montado é o ARQUIVO, e não a pasta que o contém** — medido
        # contra o container: com o diretório montado ali, o Authelia morre no
        # startup check com `open /config/notifications: is a directory`. A
        # montagem o declara (`file=True`) e a subida o cria VAZIO, porque desde
        # então é o container que o preenche.
        self.up()
        self.assertIn(f"filename: {env.IDENTITY_CONFIG}/{env.IDENTITY_NOTIFICATIONS}",
                      self.conf())
        mounted = [mount for mount in _service(env.IDENTITY).mounts
                   if mount.host == env.IDENTITY_NOTIFICATIONS]
        self.assertEqual([mount.file for mount in mounted], [True])
        notice = env.state(env.IDENTITY) / env.IDENTITY_NOTIFICATIONS
        self.assertTrue(notice.is_file(), "o caminho montado tem de ser arquivo")
        self.assertEqual(notice.read_bytes(), b"")
        # E o diretório de execução não leva cópia: o aviso é do container, e a
        # pasta de estado é quem o guarda.
        self.assertFalse(
            (env.materialized(env.IDENTITY) / env.IDENTITY_NOTIFICATIONS).exists())

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

    def test_the_session_registry_is_the_providers_memory(self):
        # O provedor guarda quem está dentro na PRÓPRIA memória — não há
        # `session.redis` nenhum apontando para um serviço do ambiente: um
        # restart do container zera o registro, e o cookie segue assinado pelo
        # mesmo `secret` sem que o provedor ainda conheça a sessão que ele
        # nomeia (§7b).
        self.up()
        self.assertNotIn("redis:", self.conf())

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

    §7a's Caddy publishes the edge on `443`, and a machine that ships the
    kernel's low-port rule refuses that bind to a user process — which is every
    Linux, and the one measured here (`ip_unprivileged_port_start = 1024`). The
    rule says the elevation happens "through an explicit request, with the
    reason on display", and this is that door.
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
        # tomorrow enters this question by existing. **A porta 443 entra por
        # isso, e é ela a mais baixa — e a única — que o ambiente publica**: o
        # piso se move UMA vez, para a mais baixa.
        with self.machine(1024):
            self.assertEqual(env.blocked(), (443,))
        with self.machine(443):
            self.assertEqual(env.blocked(), ())

    def test_the_request_carries_the_reason_and_the_narrowest_value(self):
        # The reason on display (§3), and the floor moves to the LOWEST port the
        # environment publishes — 443, not 0: the machine grants exactly what AT
        # needs and nothing below it.
        said, spent = [], []
        box = {"floor": 1024}

        def spend(*argv: str) -> None:
            spent.append(argv)
            box["floor"] = 443  # the machine moved

        with mock.patch.object(env, "floor", lambda: box["floor"]):
            outcome = self.quiet(
                env.elevate, lambda question: (said.append(question), "s")[1],
                spend=spend,
            )[0]
        self.assertIsNone(outcome)
        self.assertEqual(spent, [("sysctl", "-w", f"{env.SYSCTL_PORTS}=443")])
        self.assertIn(env.SYSCTL_PORTS, said[0])
        self.assertIn("443", said[0])

    def test_declining_moves_nothing_and_says_which_port_is_out_of_reach(self):
        spent = []
        with self.machine(1024):
            outcome, text = self.quiet(
                env.elevate, lambda question: "n", spend=lambda *argv: spent.append(argv)
            )
        self.assertEqual(outcome, env.HOSTED)
        self.assertEqual(spent, [])
        self.assertIn(i18n.tr("services.elevation.refused", ports="443"), text)

    def test_with_no_terminal_the_permission_is_not_requested(self):
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.elevation.no_tty", ports="443"), text)

    def test_a_machine_that_does_not_move_says_so_instead_of_announcing(self):
        # Asking and getting nothing is the one answer that must not be called a
        # success: the services would come up and fail to bind.
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate, lambda question: "s",
                                       spend=lambda *argv: None)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr("services.elevation.failed", ports="443"), text)

    def test_up_asks_before_it_starts_anything_and_leaves_the_folder_alone(self):
        # A refusal is the folder's previous state untouched: no secret drawn, no
        # network created, no service started.
        fake = self.runtime()
        with self.machine(1024):
            outcome, text = self.quiet(env.up, secret=self.phrase, ask=lambda question: "n")
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.elevation.refused", ports="443"), text)
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

    def test_the_network_changes_the_address_and_the_name_follows_it_now(self):
        # **A decisão desta fatia mudou de lado (TASK-187).** A rede privada
        # decide ONDE a borda publica — nunca mudou — e agora também QUAL nome
        # ela serve: sem um `dnsmasq` do ambiente para resolver um domínio
        # próprio, o nome É o da rede (`vpn.name`), que o MagicDNS do próprio
        # Tailscale já resolve para todo dispositivo do tailnet.
        #
        # O endereço da rede privada não existe nesta máquina — quem responde
        # por ele é o seam —, então quem responde pela PERGUNTA ao endereço
        # também: `TheAddress` prova a pergunta, e aqui o que se lê é o que a
        # subida ESCREVE.
        with mock.patch.object(vpn, "name", lambda call=None: "host.example-tailnet.ts.net"), \
                mock.patch.object(vpn, "address", lambda call=None: "100.64.0.1"), \
                mock.patch.object(env, "address_ready", lambda address: True):
            self.assertEqual(env.site_host(), "host.example-tailnet.ts.net")
            fake = self.runtime()
            self.quiet(env.up, secret=self.phrase)
            caddyfile = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
            self.assertIn(f"https://{env.site_host()} {{", caddyfile)
            identity = (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")
            self.assertIn(f"domain: {env.site_host()}", identity)
            # O portal segue o mesmo nome — e carrega o caminho dele, que é o
            # endereço em que a borda o roteia fora do `forward_auth`.
            self.assertIn(
                f"authelia_url: https://{env.site_host()}{caddy.PORTAL}/", identity)
            # **E as DUAS portas do site são publicadas no endereço DA REDE**,
            # que é como a pessoa e o celular chegam: no caminho container quem
            # publica é o container, e o §7e só vale se o endereço for o da rede.
            argv = _call(fake, "at-caddy")
            self.assertIn(f"100.64.0.1:{env.PORT}:{env.PORT}/tcp", argv)

    def test_without_a_network_the_site_falls_back_to_at_localhost(self):
        # O estado suportado, e não um degradado: a máquina não está em rede
        # privada nenhuma, e o site cai no nome universal — `at.localhost`, que
        # todo navegador resolve para o laço sozinho, sem DNS nenhum por trás —
        # porque o portão recusa um domínio de cookie sem ponto e o TLS precisa
        # de um nome para o SNI. Os dois foram medidos.
        self.assertEqual(env.site_host(), env.FALLBACK_HOST)
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        self.assertIn(f"https://{env.site_host()} {{",
                      (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"))


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
            name="lost",
            label=f"services.{env.IDENTITY}.name",
            image=_service(env.IDENTITY).image,
            ports=(env.Port(53, "udp", address=NOBODY),),
        )
        self.runtime()
        with mock.patch.object(env, "SERVICES", (lost,)), \
                mock.patch.object(env, "GRACE", 0.0):
            outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr(
            "services.up.no_address", service=i18n.tr(lost.label),
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
        env.through_edge("https://at.local/settings", {})
        argv = fake.calls[0]
        self.assertEqual(argv[:2], ["run", "--rm"])
        self.assertIn(env.NETWORK, argv)
        self.assertIn(_service(env.CADDY).image.reference(), argv)
        self.assertIn("https://at.local/settings", argv)
        self.assertIn(f'connect-to = "at.local:{env.PORT}:'
                      f'{env.container(env.CADDY)}:{env.PORT}"',
                      fake.given[0]["input"])

    def test_the_edge_probe_carries_the_token_on_the_input_and_not_the_argv(self):
        # A mesma regra do `inside`: um argv é um `ps` nesta máquina.
        fake = self.runtime()
        env.through_edge("https://at.local/settings",
                         {"Authorization": "Bearer um-segredo-qualquer"})
        self.assertNotIn("um-segredo-qualquer", fake.calls[0])
        self.assertIn('header = "Authorization: Bearer um-segredo-qualquer"',
                      fake.given[0]["input"])

    def test_the_edge_probe_answers_a_number_and_nothing_else(self):
        for stdout, expected in (("200\n", 200), ("403", 403),
                                 ("", None), ("curl: (7) refused", None)):
            with self.subTest(stdout=stdout):
                with self.answered(stdout):
                    self.assertEqual(
                        env.through_edge("https://at.local/settings", {}),
                        expected)
        with self.answered("200", returncode=1):
            self.assertIsNone(
                env.through_edge("https://at.local/settings", {}))


class TheDown(FolderCase):
    """`down` takes the containers, and the folder stays where it is."""

    def test_every_container_bill_started_is_removed(self):
        fake = self.runtime()
        _, text = self.quiet(env.down)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(["rm", "--force", env.container(service.name)], fake.calls)
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)
        self.assertIn(i18n.tr("services.down.done", where=env.state(env.IDENTITY).parent), text)

    def test_the_folder_is_not_touched(self):
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        before = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.quiet(env.down)
        self.assertEqual((env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"), before)

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
        # Seis linhas com a mesma forma são seis linhas que ninguém compara, e
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

    def test_without_a_podman_the_environment_has_nothing_standing(self):
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.no_podman.status"), text)




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
        for name in (env.IDENTITY, "caddy"):
            with self.subTest(service=name):
                self.assertNotIn("--env", _call(fake, env.container(name)))

    def test_the_webapp_is_handed_its_own_derived_key(self):
        # §4, item 50: a Main Key não sai do instante do `bring_up` — só o que
        # ela DERIVA viaja, uma variável por escopo, em base64.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        webapp_key = vault.derived_key(self.phrase_key(), env.WEBAPP)
        self.assertIn(
            f"{webapp_keys.WEBAPP_KEY_ENV}="
            f"{base64.urlsafe_b64encode(webapp_key).decode()}",
            argv,
        )

    def test_the_webapp_is_handed_the_cofres_derived_key_too(self):
        # TASK-154: a terceira porta, pela mesma regra — o escopo `cofre`.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        cofre_key = vault.derived_key(self.phrase_key(), cofre.SCOPE)
        self.assertIn(
            f"{webapp_keys.COFRE_KEY_ENV}="
            f"{base64.urlsafe_b64encode(cofre_key).decode()}",
            argv,
        )


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
        self.assertIn(f"https://{env.site_host()} {{",text)
        self.assertIn(f"\tbind {env.ALL}", text)
        self.assertIn(
            f"reverse_proxy {env.container(env.WEBAPP)}:{env.WEBAPP_PORT}", text)
        self.assertNotIn(f"reverse_proxy {env.LOOP}:", text)


class TheNames(FolderCase):
    """O nome do ambiente (TASK-187).

    O ambiente responde por UM nome só — o da rede privada quando há uma
    (`vpn.name`, que o MagicDNS do próprio Tailscale já resolve), `at.localhost`
    quando não há — e não tem mais DNS próprio: não há um `dnsmasq` para
    resolver um segundo nome, e a CA própria (`cert.at.local`) não existe mais.
    O que se lê aqui é o que a subida ESCREVE, que é a única coisa que esta
    suíte pode ler.
    """

    def test_the_environment_owns_one_name(self):
        self.assertEqual(env.site_host(), env.FALLBACK_HOST)
        self.assertEqual(env.names(), (env.site_host(),))

    def test_the_edge_serves_the_site_with_the_tls_and_the_bind_of_the_container(self):
        # A borda serve o site com o `tls internal` que emite por nome e com o
        # `bind` do container: o nome não é um endereço que o container tenha.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f"https://{env.site_host()} {{", text)
        self.assertEqual(text.count("\ttls internal"), 1)
        self.assertEqual(text.count(f"\tbind {env.ALL}"), 1)

    def test_the_default_port_is_not_written_and_another_one_is(self):
        # `https://at.local` e `https://at.local:443` são o mesmo endereço, e o
        # primeiro é o que a pessoa digita; outro porto aparece, porque aí ele é
        # a informação.
        self.assertEqual(caddy.address(env.site_host(), env.PORT),
                         f"https://{env.site_host()}")
        self.assertEqual(caddy.address("at.local", 8443), "https://at.local:8443")


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

# Os valores que a pasta que nasceu ANTES do selo guardava, e que a migração
# existe para matar (item 50, corte `f`). Eles são reconhecíveis de propósito:
# o que cada teste procura é que eles não estejam em arquivo nenhum DEPOIS.
BORN_GATE = "o-portao-que-nasceu-em-claro\n"

# The two folders a CONTAINER fills and the deploy only creates: the Caddy's
# storage (the local CA, and the private keys of it) and the provider's `data`
# (its database). What lands in them is the container's act and not AT's write —
# which is the whole reason they are asserted EMPTY below, and the reason the
# audit of item 50 names them apart.
#
# O aviso do provedor saiu desta lista, e ele é a exceção que PROVA a regra: o
# caminho montado é um ARQUIVO (`Mount(..., file=True)`), porque é assim que o
# Authelia o abre — e um arquivo vazio na pasta de estado é o que a subida
# deixa. Ele tem teste próprio, com a mesma pergunta (`TheIdentityProvider`).
FILLED_BY_CONTAINERS = (
    (env.CADDY, env.CADDY_STORAGE),
    (env.IDENTITY, "data"),
)


def _sealed_values() -> dict[str, tuple[Path, str]]:
    """Onde cada valor que o AT SELA mora, e o escopo da chave que o abre (item 50).

    São os QUATRO deste corte — o portão do Caddy e os três do provedor —, e o
    par `(arquivo, escopo)` é o que a subida usa para os abrir: o escopo é o
    serviço dono do valor (§4), e é o nome dele que a pasta não precisa carregar
    porque o arquivo já o diz.
    """
    return {
        GATE: (caddy.gate_file(), env.CADDY),
        SESSION: (env.state(env.IDENTITY) / env.IDENTITY_SESSION, env.IDENTITY),
        ENCRYPTION: (env.state(env.IDENTITY) / env.IDENTITY_ENCRYPTION,
                     env.IDENTITY),
        SIGNATURE: (env.state(env.IDENTITY) / env.IDENTITY_JWT, env.IDENTITY),
    }


def _catalogue() -> tuple[tuple[Path, int | None, frozenset[str]], ...]:
    """What the deploy writes into the folder: the file, the mode, the secrets.

    **This is item 50's audit, turned into a gate.** The philosophy of the folder
    is that it is copied WITHOUT encryption and that what a PERSON writes in it is
    theirs — so what the AT creates is the part that has to stop being readable in
    a copy, and this is the measurement of what that part is today: **os QUATRO
    valores que o AT sorteia saem daqui como o envelope do cofre** — o portão do
    Caddy e os três do provedor. The scanner does not delimit it: measured on a
    folder the deploy filled, `gitleaks 8.30.1` flags
    ONE of these files — the provider's YAML, where each value has its keyword on
    the line — and is BLIND to the Caddyfile and to the bare-valued files,
    because its default rules read a keyword beside the value and those are the
    value and nothing else. So the scan confirms a leak and never delimits one;
    the delimitation is this list.

    The mode is `None` where the writer left it to the umask — which is every
    file the deploy writes.

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
        # O aviso do provedor: um ARQUIVO VAZIO que a subida cria e o container
        # enche — o caminho é montado como arquivo, e o runtime criaria um
        # DIRETÓRIO ali se ele não existisse (`Mount.file`). Não carrega segredo
        # nenhum: o que ele leva é o que o Authelia tem a dizer.
        (identity / env.IDENTITY_NOTIFICATIONS, None, frozenset()),
        (env.pin_file(), None, frozenset()),
    )


class TheClearState(FolderCase):
    """What the deploy writes into the folder, and with what mode (item 50).

    The audit of the vault's first slice, held as a gate — e o que ele tranca
    mudou com cada corte do selo. A folder is copied without encryption, so the
    files below are the ones a copy hands over: **os QUATRO valores que o AT
    sorteia chegam à pasta como o envelope do cofre** e o valor claro não está
    em arquivo nenhum dela, e o resto não é segredo nenhum.

    O catálogo é a linha por arquivo, e ele é o mesmo depois do selo: o que
    mudou é o que cada linha carrega, e é por isso que `marks` existe — a
    classificação continua sendo MEDIDA, arquivo a arquivo, e não repetida.
    """

    def up(self) -> None:
        """The environment up — the whole of the deploy's writing happens here."""
        self.runtime()
        self.quiet(env.up, secret=self.phrase)

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
        # The CA's private keys and the provider's database are in the folder
        # and are NOT AT's write: the deploy creates the folder
        # and the container fills it. Asserted empty because that is what says
        # whose act each secret is — and the audit names them so that the slice
        # that seals does not forget the one thing the deploy cannot write.
        self.up()
        for service, folder in FILLED_BY_CONTAINERS:
            where = env.state(service) / folder
            with self.subTest(where=where):
                self.assertTrue(where.is_dir())
                self.assertEqual(list(where.iterdir()), [])


# --------------------------------------------- o que o container enche ---

# A árvore que o CONTAINER escreve no storage do Caddy, na forma em que a
# instância a tem: a chave privada de cada autoridade da CA local, a de cada
# certificado emitido contra ela, e o `root.crt` PÚBLICO que a pessoa importa.
# O conteúdo é o de menos — o que estes testes leem é que o `up` não o toca, não
# o sela e não o tira da pasta —, e por isso ele é uma frase que se reconhece.
CA_PRIVATE = "a-chave-privada-que-o-container-escreveu, e o cofre nao a alcanca\n"
CA_PUBLIC = "o-root-crt-publico-que-a-pessoa-importa-no-app-do-celular\n"


class TheStorageOutOfReach(FolderCase):
    """O storage do Caddy fica FORA do alcance do cofre, e isso é declarado (§7a, item 50, corte `e`).

    **O item 50 selou tudo o que o AT SORTEIA — e este objeto ele não sorteia.**
    O `storage` do Caddy é PREENCHIDO pelo container enquanto ele está de pé, na
    cadência da renovação de certificado dele, e nenhuma subida passa por ali
    para selá-lo; e a Chave Principal não chega lá dentro, porque §7a diz que nenhum
    processo de dentro do container abre o cofre. Sem um selo que o alcance, o
    que resta é DECLARAR o objeto fora do alcance do cofre, com o preço dito (a
    cópia da pasta leva a chave privada da CA), e é esta a declaração que a
    suíte segura: o `up` não escreve e não sela o que o container encheu. O modo
    `0600` é o do container — nenhum arquivo daqui é escrita do AT, e é por isso
    que o catálogo de `TheClearState` não tem linha para eles.

    **A única exceção é a PODA, e ela é declarada aqui também** (§7a, a fatia dos
    nomes): o conjunto de nomes servidos é do AT (`names`), então o `up` tira do
    storage o certificado dos nomes que ele deixou de servir — a chave privada em
    claro de um nome que ninguém digita não serve a nada e o portão do backup a
    barraria sem motivo. O que o container escreveu de um nome AINDA servido não
    é tocado: quem o poda é a subida seguinte à mudança do nome, e a árvore do
    nome servido sai byte a byte como estava.
    """

    def storage(self) -> Path:
        """A pasta que o container enche — a mesma que a instância mediu."""
        return env.state(env.CADDY) / env.CADDY_STORAGE

    def seeded(self) -> dict[Path, str]:
        """A árvore como o CONTAINER a deixa, e não como o AT a escreveria.

        Os nomes são os que a árvore de verdade tem dentro do storage, e o
        `root.crt` é o `caddy.AUTHORITY` — o arquivo que o AT NOMEIA, e a única
        metade da CA que é pública.
        """
        local = self.storage() / "pki" / "authorities" / "local"
        files_written = {
            local / "root.key": CA_PRIVATE,
            local / "intermediate.key": CA_PRIVATE,
            local / "intermediate.crt": CA_PUBLIC,
            local / caddy.AUTHORITY.name: CA_PUBLIC,
            self.storage() / "certificates" / "local" / env.site_host()
            / f"{env.site_host()}.key": CA_PRIVATE,
        }
        for where, body in files_written.items():
            files.atomic_write_text(where, body, mode=0o600)
        return files_written

    def up(self) -> None:
        """A subida inteira, com o runtime respondendo no lugar do Podman."""
        self.runtime()
        self.quiet(env.up, secret=self.phrase)

    def test_the_up_leaves_what_the_container_wrote_exactly_as_it_was(self):
        # **A declaração, do lado do AT**: o que o container encheu continua
        # byte a byte como ele deixou. Um AT que passasse a escrever, re-selar ou
        # podar a árvore de um nome SERVIDO falha aqui — que é o que separa "fora
        # do alcance" de um comentário. (O nome semeado é o do site, e é servido:
        # a poda só toca os nomes que a borda já não serve.)
        before = self.seeded()
        self.up()
        for where, body in before.items():
            with self.subTest(where=where):
                self.assertEqual(where.read_text(encoding="utf-8"), body)
                self.assertEqual(stat.S_IMODE(where.stat().st_mode), 0o600)

    def test_the_up_prunes_the_certificate_of_a_name_the_edge_no_longer_serves(
            self):
        # **O conjunto de nomes é do AT, e a subida o faz valer** (§7a, a fatia
        # dos nomes): o certificado de um nome que a borda já não serve — e a
        # chave privada EM CLARO ao lado dele — não fica no storage para sempre.
        # Um nome que ainda é servido não é tocado; um nome que saiu não sobra.
        served = self.storage() / "certificates" / "local" / env.site_host()
        stale = ("velho.at.local", "host.example-tailnet.ts.net")
        for name in stale:
            files.atomic_write_text(
                self.storage() / "certificates" / "local" / name / f"{name}.key",
                CA_PRIVATE, mode=0o600)
        self.seeded()
        self.up()
        self.assertTrue((served / f"{env.site_host()}.key").is_file())
        for name in stale:
            with self.subTest(name=name):
                self.assertFalse(
                    (self.storage() / "certificates" / "local" / name).exists())

    def test_no_envelope_of_the_vault_reaches_the_storage(self):
        # O cofre sela o que o AT SORTEIA, e o envelope é a marca dele
        # (`vault.SEALED`). Nenhum arquivo desta pasta o carrega: ela não está
        # entre os arquivos que o `up` abre ou sela — nem os que o container
        # escreveu, nem qualquer outro que apareça ali.
        self.seeded()
        self.up()
        for where in self.storage().rglob("*"):
            if where.is_file():
                with self.subTest(where=where):
                    self.assertEqual(
                        vault.envelopes(where.read_text(encoding="utf-8")), (),
                        f"{where} carries a vault envelope: o storage não é do cofre",
                    )

    def test_the_storage_is_not_copied_out_of_the_folder(self):
        # O diretório de execução recebe o que o container LÊ de uma cópia; o
        # storage não: ele é montado DA pasta (`Mount(CADDY_DATA, host=...)`), e
        # é na pasta de estado que o container o enche. O que a cópia clara
        # levaria é o que a pasta sela, e esta pasta não é selada — tirá-la de
        # lá seria ir na direção contrária à promessa do backup.
        self.seeded()
        self.up()
        self.assertFalse((env.materialized(env.CADDY) / env.CADDY_STORAGE).exists())
        self.assertTrue(self.storage().is_dir())


class TheStateShape(FolderCase):
    """A pasta de estado com a forma que o serviço não lê — e a recusa dita.

    O `notifications` do provedor já foi as duas coisas, e é a história inteira
    que esta classe guarda. Era um ARQUIVO escrito pelo container, com `/config`
    montado inteiro; a fatia 2 do item 50 o trocou por uma PASTA, com montagem
    própria — e o Authelia morreu no startup check com `is a directory`, porque
    ele abre aquele caminho como arquivo. **Esta fatia o faz voltar a ser um
    ARQUIVO**, e por isso a forma confere os dois sentidos: uma pasta onde o
    serviço monta um arquivo, um arquivo onde ele monta uma pasta, uma pasta
    onde o AT escreve um arquivo.

    Um caminho que já exista com a forma trocada — o resto de uma versão
    anterior do AT, ou algo que a pessoa pôs ali — estoura no meio da subida
    como uma exceção do `pathlib` (`mkdir`, `os.replace`), que o PyInstaller
    entrega como traceback sem uma frase. **A forma do estado é diagnosticável
    ANTES de tentar**, e o AT recusa com a frase: ele não conserta a pasta da
    pessoa em silêncio.
    """

    def said(self, service: str, where: Path, wanted: str) -> str:
        """A frase da recusa, montada como o `up` a monta."""
        return i18n.tr("services.state.shape", service=i18n.tr(service),
                       where=where, wanted=i18n.tr(wanted))

    def test_a_folder_where_the_service_mounts_a_file_is_refused_with_a_phrase(self):
        # É o defeito que a instância tem hoje: `App/services/identity-provider/
        # notifications` ficou uma PASTA vazia da montagem que o Authelia não
        # lê, e o `up` precisa de um ARQUIVO ali. O AT não conserta sozinho — a
        # frase diz o caminho e o que ele devia ser, e quem o move é a pessoa.
        where = env.state(env.IDENTITY) / env.IDENTITY_NOTIFICATIONS
        where.mkdir(parents=True)
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.MALFORMED)
        self.assertIn(self.said("services.identity-provider.name", where,
                                "services.state.file"), text)
        # Nada subiu, e a pasta continua onde estava: o AT não mexe no que não
        # é dele — quem move ou apaga é a pessoa.
        self.assertNotIn("run", fake.verbs())
        self.assertTrue(where.is_dir())

    def test_a_file_where_the_service_mounts_a_folder_is_refused_too(self):
        # O outro sentido da mesma forma: o `data` do provedor é uma PASTA que o
        # container enche, e um arquivo plantado no lugar dela estoura o `mkdir`
        # do `_prepare`.
        where = env.state(env.IDENTITY) / "data"
        files.atomic_write_text(where, "")
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.MALFORMED)
        self.assertIn(self.said("services.identity-provider.name", where,
                                "services.state.folder"), text)
        self.assertNotIn("run", fake.verbs())
        self.assertTrue(where.is_file())

    def test_a_folder_where_the_at_writes_a_file_is_refused_too(self):
        # A mesma classe, do outro lado: o `configuration.yml` é ESCRITO pelo
        # `_prepare`, e uma pasta no lugar dele estoura no `os.replace`.
        where = env.state(env.IDENTITY) / env.IDENTITY_YAML
        where.mkdir(parents=True)
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.MALFORMED)
        self.assertIn(self.said("services.identity-provider.name", where,
                                "services.state.file"), text)
        self.assertNotIn("run", fake.verbs())

    def test_the_shape_is_checked_before_the_phrase_is_asked(self):
        # Sem terminal a subida responde `NO_ANSWER` — e não é o que acontece
        # aqui: a forma do estado é conferida ANTES, porque não se pede a Chave Principal
        # (nem a elevação) para uma subida que já se sabe que não sobe.
        (env.state(env.IDENTITY) / env.IDENTITY_NOTIFICATIONS).mkdir(parents=True)
        self.runtime()
        outcome, _ = self.quiet(env.up, secret=None)
        self.assertEqual(outcome, env.MALFORMED)

    def test_the_restart_refuses_the_same_shape_for_its_own_service(self):
        # O `restart` monta o estado de UM serviço, e a recusa é a mesma frase.
        where = env.state(env.IDENTITY) / env.IDENTITY_YAML
        where.mkdir(parents=True)
        self.runtime()
        outcome, text = self.quiet(env.restart, env.IDENTITY, self.phrase)
        self.assertFalse(outcome)
        self.assertIn(self.said("services.identity-provider.name", where,
                                "services.state.file"), text)


class TheAccessPhrase(FolderCase):
    """A Chave Principal na subida: quem sela, quem abre, e o que não sobe (§4).

    A fatia que fecha a promessa do item 50 do lado de FORA: o que o AT sorteia
    não se lê na pasta — o que se lê lá é o envelope —, e o valor claro só existe
    no diretório de execução, que morre com o ambiente. Quem o escreve lá é o
    `up`, e ele só o faz com a Chave Principal que ABRIU cada envelope: sem Chave Principal, ou com
    uma que não abre, o ambiente não sobe e a pasta fica exatamente onde estava.
    """

    def counting(self, phrase: str = PHRASE):
        """Um leitor sem eco que conta o que lhe foi perguntado.

        Ele é o que responde por quantas vezes a Chave Principal foi LIDA — a pergunta que
        separa a primeira subida (duas leituras, porque não há contra o que
        conferir) das seguintes (uma, porque a conferência é a abertura).
        """
        asked: list[str] = []

        def reader(question: str) -> str:
            asked.append(question)
            return phrase

        return asked, reader

    def seeded(self) -> None:
        """Uma pasta que nasceu ANTES do selo: os valores, em claro (item 50, corte `f`).

        É o estado que a auditoria mediu na instância, e a migração é o ato que
        esta classe prende: **cada valor em claro é RE-SORTEADO e selado**, e não
        apenas selado, porque a pasta pode ter sido copiada e o valor que já
        viajou não volta.
        """
        files.atomic_write_text(caddy.gate_file(), BORN_GATE)
        for name in env.IDENTITY_SECRETS:
            files.atomic_write_text(env.state(env.IDENTITY) / name,
                                    f"o-valor-{name}-em-claro\n")

    def test_the_first_boot_reads_the_phrase_twice(self):
        # **Uma Chave Principal que SELA não tem como ser conferida depois**: a segunda
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
        # com a mesma Chave Principal são a prova de que é a mesma.
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        asked, reader = self.counting()
        # `bring_up`, the second time: `up` itself would refuse a folder that
        # already has an environment (`PROVISIONED`, 2026-09-28) before ever
        # reading a Chave Principal again — the engine underneath is what this test reads.
        outcome, _ = self.quiet(env.bring_up, secret=reader)
        self.assertEqual(outcome, env.UP)
        self.assertEqual(len(asked), 1)

    def test_two_readings_that_disagree_draw_nothing(self):
        # A recusa ANTES de qualquer sorteio: uma pasta com valores selados sob
        # uma Chave Principal que ninguém sabe qual é seria pior que uma pasta vazia.
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
        # `bring_up`: `up` itself would already refuse this second call with
        # `PROVISIONED`, before the wrong Chave Principal is ever read (2026-09-28).
        outcome, text = self.quiet(
            env.bring_up,
            secret=lambda question: "uma frase que nao e a que selou")
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

    def born(self) -> dict[str, str]:
        """Os valores que a pasta guardava em claro, por nome — como `_sealed_values`.

        É o mapa que a migração tem de matar: cada um deles é um valor que já
        esteve no disco sem envelope, e portanto um valor que uma cópia da pasta
        pode ter levado.
        """
        return {
            GATE: BORN_GATE.strip(),
            SESSION: f"o-valor-{env.IDENTITY_SESSION}-em-claro",
            ENCRYPTION: f"o-valor-{env.IDENTITY_ENCRYPTION}-em-claro",
            SIGNATURE: f"o-valor-{env.IDENTITY_JWT}-em-claro",
        }

    def folder_files(self) -> list[Path]:
        """Todo arquivo sob `App/services/`, mais o portão — o que uma cópia levaria."""
        return [where for where in env.pin_file().parent.rglob("*") if where.is_file()] \
            + [caddy.gate_file()]

    def test_a_folder_that_never_sealed_is_migrated_and_reads_the_phrase_twice(self):
        # **A migração é um ATO, e ele pede a Chave Principal** (item 50, corte `f`): a
        # pasta que nasceu antes do selo tem valores em claro, e cada um deles é
        # re-sorteado nesta subida. A segunda leitura é a única conferência
        # possível na primeira vez — não há envelope contra o que conferir antes
        # de o primeiro nascer (`_ask_phrase`) —, e ela vale o que acabou de selar.
        self.seeded()
        asked, reader = self.counting()
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=reader)
        self.assertEqual(outcome, env.UP)
        self.assertEqual(len(asked), 2)
        self.assertIn(i18n.tr("services.migrated", count=len(self.born())), text)
        self.assertIn("run", fake.verbs())

    def test_the_migration_rotates_every_clear_value_and_seals_the_new_one(self):
        # **A rotação é a metade que faz a migração valer**: um valor que já
        # viajou não volta a ser segredo por ser selado depois. O que a pasta
        # guarda agora é o envelope de um valor NOVO — e o novo não é o antigo.
        self.seeded()
        born = self.born()
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        fresh = self.secrets()
        for name, old in born.items():
            with self.subTest(value=name):
                self.assertTrue(fresh.get(name), f"{name} não ficou selado")
                self.assertNotEqual(fresh[name], old, f"{name} não foi rotacionado")

    def test_the_old_clear_values_are_in_no_file_of_the_folder(self):
        # **A promessa da migração, medida**: o valor que nasceu em claro não se
        # lê numa cópia da pasta — em arquivo nenhum dela, nem no envelope que o
        # substituiu. Quem tinha uma cópia antiga fica com o valor morto.
        self.seeded()
        born = self.born()
        self.runtime()
        self.quiet(env.up, secret=self.phrase)
        for where in self.folder_files():
            text = where.read_text(encoding="utf-8")
            for name, old in born.items():
                with self.subTest(value=name, where=where):
                    self.assertNotIn(old, text)

    def test_no_terminal_does_not_migrate_and_leaves_the_folder_as_it_was(self):
        # §3's fail-closed posture: migrar SELA, e sem Chave Principal não há selo — e o
        # que não se abriu não se usa. A pasta fica exatamente onde estava, e
        # nada foi re-sorteado.
        self.seeded()
        fake = self.runtime()
        outcome, text = self.quiet(env.up, secret=None)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.phrase.no_tty"), text)
        self.assertNotIn("run", fake.verbs())
        self.assertEqual(caddy.gate_file().read_text(encoding="utf-8"), BORN_GATE)
        self.assertFalse(env.pin_file().exists())

    def test_only_the_clear_values_are_rotated(self):
        # A migração é cirúrgica, arquivo a arquivo: o que já tem envelope não é
        # re-sorteado — a regra de sempre —, e só o que está em claro é que vira
        # valor novo.
        self.seeded()
        sealed = vault.seal("o-portao-de-verdade",
                            vault.derived_key(self.phrase_key(), env.CADDY))
        files.atomic_write_text(caddy.gate_file(), f"{sealed}\n")
        self.runtime()
        outcome, _ = self.quiet(env.up, secret=self.phrase)
        self.assertEqual(outcome, env.UP)
        self.assertEqual(self.value(caddy.gate_file(), env.CADDY),
                         "o-portao-de-verdade")

    def test_the_sealing_is_the_same_phrase_every_time(self):
        # A chave derivada vem da Chave Principal e de mais nada (§4): a mesma Chave Principal sobre
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
    Chave Principal, e o que os três leitores recebem é a cópia clara.
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

    def test_down_takes_the_run_directory_with_it(self):
        # O diretório de execução é a metade que MORRE: o que o container encheu
        # está na pasta de estado, e é ela que fica.
        self.up()
        self.assertTrue(env.run_dir().is_dir())
        self.runtime()
        self.quiet(env.down)
        self.assertFalse(env.run_dir().exists())
        self.assertTrue(env.state(env.IDENTITY).is_dir())


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
    """`at-deploy`'s seven root words for the container environment, under
    `container` (TASK-190: `host` needed the same shape for a different one)."""

    def test_the_tree_offers_the_environments_seven_words_under_container(self):
        self.assertEqual(
            tree.environment_words(),
            ("up", "update", "down", "status", "switch", "forms", "credential"),
            "a word the dispatch takes and the help does not offer (or the "
            "other way round) is the defect §5's one-way rule exists for",
        )
        for word in tree.environment_words():
            with self.subTest(word=word):
                self.assertIsNotNone(tree.find(word))

    def test_status_is_what_the_status_word_answers(self):
        # 2026-09-28: the wordless `services` that used to answer with the
        # status is gone — the word for it is `at-deploy container status`,
        # same as every other word of the container environment.
        code, text = self.quiet(main, ["container", "status"])
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.status"), text)

    def test_no_terminal_means_no_choice_and_a_refusal(self):
        # The suite runs with no tty, which is the state the offer refuses in.
        code, text = self.quiet(main, ["container", "up"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.no_podman.no_tty"), text)

    def test_the_offer_reaches_the_environment_with_the_persons_answer(self):
        code, text = self.quiet(services, ["up"], ask=lambda question: "n")
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)

    def test_a_word_it_does_not_take_is_a_usage_error(self):
        for words in (["container", "up", "extra"], ["container", "down", "extra"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_an_unknown_word_is_a_usage_error_and_not_a_dispatch(self):
        code, text = self.quiet(main, ["run"])
        self.assertEqual(code, USAGE)
        self.assertIn(i18n.tr("deploy.error.unknown_word", word="run"), text)

    def test_the_help_offers_every_root_word_of_the_environment(self):
        code, text = self.quiet(main, ["help"])
        self.assertEqual(code, OK)
        for word in tree.environment_words():
            with self.subTest(word=word):
                self.assertIn(word, text)

if __name__ == "__main__":
    unittest.main()
