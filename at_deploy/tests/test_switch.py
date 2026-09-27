"""The switch between the paths (§6, §7c): transactional, or nothing at all.

§6 declares the whole contract in a paragraph, and this file is that paragraph
read as tests: the Forms stays on until the gate is PROVED in front of AT, a
step that does not close takes everything back to the state before, and a folder
that committed is a folder the APP closes the moment the portal stops answering.

The last of those is `at-cli`'s half and it is proved where it lives
(`at/tests/test_gate.py`): what the deploy owns is the switch, and what `at-cli`
owns is reading the record it commits — with the deploy artifact absent.

Nothing here touches a socket, and none of it needs one: the environment runs
against the runtime's SEAM (`at_deploy/podman.py`), and the proof asks through
a seam of its own (`core/gate.py`'s `Answer`) — which is what lets a switch whose
whole point is a live portal be proved on a machine with no portal, no Podman and
no network.
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
from at.core import actors, boot, files, gate
from at.encryption import vault
from at.services import caddy
from at.ui.webapp import app as webapp

from at_deploy import environment as env
from at_deploy import podman, switch, vpn
from at_deploy.cli import OK, REFUSED, USAGE, services, main

# A Frase de Acesso que a suíte digita (item 50, §4). A virada é uma das portas
# por onde alguém sobe o ambiente, e é ela que sela o que a subida sorteia.
PHRASE = "a frase de acesso da suite, e ela nao abre nada de ninguem"


class FakeRuntime:
    """The runtime's seam, answered by a list — the same shape the environment's
    suite uses, and here for the same reason: what the switch decides about a
    container is an argv, and the argv is readable without a container."""

    def __init__(self, fails: tuple[str, ...] = ()) -> None:
        self.calls: list[list[str]] = []
        self.fails = set(fails)

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        failed = bool(call) and call[0] in self.fails
        said = "true" if call[:2] == ["container", "inspect"] else ""
        return SimpleNamespace(returncode=1 if failed else 0, stdout=said, stderr="")

    def removed(self, name: str) -> bool:
        return ["rm", "--force", env.container(name)] in self.calls


class FakeProbes:
    """The portal's answers, without a socket — the `gate.Answer` seam.

    Each claim of the proof has its own status, so a test can make ONE of them
    wrong and watch the switch refuse: the site answered by the gate, AT taking
    the sealed identity, the same identity refused without the secret, and the
    portal — the address the gate SENDS people to — answering.
    """

    def __init__(self, front: int | None = 401, sealed: int | None = 200,
                 unsealed: int | None = 403, portal: int | None = 200) -> None:
        self.front, self.sealed = front, sealed
        self.unsealed, self.portal = unsealed, portal
        self.asked: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> int | None:
        self.asked.append((url, dict(headers)))
        if url == f"{switch.site()}/api/session":
            return self.front
        if url == env.portal_url():
            return self.portal
        return self.sealed if caddy.GATE_HEADER in headers else self.unsealed


class FolderCase(unittest.TestCase):
    """A scratch Working Folder, which is what every path below resolves to."""

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
        # The machine has NO Podman as far as this suite is concerned, and that
        # is a rule and not a convenience: a test that read the machine's real
        # runtime would pull images from the network the day one is installed
        # (the environment's suite says the same, and `runtime()` is the switch).
        self.absent = mock.patch.object(podman, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)
        # And the machine's low-port rule allows every port, for the same
        # reason: this suite is about the switch, and the environment's
        # permission has a suite of its own.
        self.floor = mock.patch.object(env, "floor", lambda: 0)
        self.floor.start()
        self.addCleanup(self.floor.stop)
        # And this machine is on no private network, so the site the proof asks
        # about is the loop's (§7e has a suite of its own).
        self.no_vpn = mock.patch.object(vpn, "run", side_effect=FileNotFoundError)
        self.no_vpn.start()
        self.addCleanup(self.no_vpn.stop)
        # **E a pessoa digita a Frase**: o `up` a lê de um leitor sem eco, e a
        # suíte entrega o dela — é o `getpass` do terminal que ela substitui.
        self.phrase = lambda question: PHRASE
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.execution.cleanup()
        self.scratch.cleanup()

    def runtime(self, fails: tuple[str, ...] = ()) -> FakeRuntime:
        fake = FakeRuntime(fails)
        started = mock.patch.object(podman, "present", lambda: True)
        calls = mock.patch.object(podman, "run", fake.run)
        asked = mock.patch.object(podman, "ok", lambda args: fake.run(args).returncode == 0)
        for patch in (started, calls, asked):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def person(self, name: str = "Rafael") -> dict:
        """Somebody with a credential — what the gate proves, and what the proof
        speaks as."""
        return actors.create_admin(name, "uma-frase-bem-longa")

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


# -------------------------------------------------------------- the proof ---

class TheProof(FolderCase):
    """§6: it is not "the container came up", it is AT receiving the identity."""

    def setUp(self):
        super().setUp()
        self.person()
        # **O ambiente de pé, que é o que a prova pergunta**: ele sorteia o
        # portão, o SELA na pasta e monta a cópia aberta no diretório de
        # execução — e é a cópia que a prova carrega no cabeçalho, porque é ela
        # que o WebApp de dentro do container compara (item 50).
        self.runtime()
        self.quiet(env.up, secret=self.phrase)

    def test_the_four_claims_together_are_what_proves_the_gate(self):
        self.assertTrue(switch.proved(FakeProbes()))

    def test_an_edge_that_lets_bill_answer_is_not_a_gate(self):
        # The site answered 200: AT's own page came back through the edge, so
        # nothing stands in front of it — whatever the container says.
        self.assertFalse(switch.proved(FakeProbes(front=200)))

    def test_an_identity_bill_does_not_take_is_not_a_gate(self):
        # The real path is there, but the sealed request never arrived: the M2M
        # between the Caddy and the WebApp is what the switch is buying.
        self.assertFalse(switch.proved(FakeProbes(sealed=403)))

    def test_an_identity_without_the_secret_must_be_refused(self):
        # If a name alone opens the door, the secret is decoration — and the
        # switch would be committing a folder to a gate that is not one.
        self.assertFalse(switch.proved(FakeProbes(unsealed=200)))

    def test_the_portal_must_answer_on_the_address_the_gate_sends_people_to(self):
        # A quarta pergunta, e a que faltava: `in_front` se contenta com o 302,
        # e um redirecionamento para uma página que não atende também responde
        # 302 — era assim que a virada fechava com o portal em laço. A pergunta
        # vai ao ENDEREÇO do portal, pela borda, que é onde o navegador pousa.
        probes = FakeProbes()
        self.assertTrue(switch.portal(probes))
        self.assertIn(env.portal_url(), [url for url, _ in probes.asked])
        # E é o endereço do SITE, com o caminho do portal — não o nome interno
        # da rede, que só o WebApp alcança.
        self.assertTrue(env.portal_url().startswith(switch.site()))

    def test_a_portal_that_does_not_answer_does_not_prove_the_gate(self):
        # 302 de novo é o laço; 431 é o laço depois de algumas voltas. Nenhum
        # dos dois é a página — e um portal inalcançável não é o mesmo que um
        # portal que responde.
        for answer in (302, 431, 404, None):
            with self.subTest(portal=answer):
                self.assertFalse(switch.proved(FakeProbes(portal=answer)))

    def test_the_redirect_in_front_is_not_the_portal_answering(self):
        # **O estado real do ambiente medido**: a borda responde 302 — o portão
        # na frente — e o portal não atende, porque o redirecionamento volta
        # para a borda e é perguntado de novo. As duas coisas juntas, e só a
        # segunda separa "algo está na frente" de "dá para entrar".
        probes = FakeProbes(front=302, portal=431)
        self.assertFalse(switch.proved(probes))
        self.assertEqual(switch.unproved(probes), "services.switch.noportal")

    def test_the_sealed_request_carries_the_folders_own_secret(self):
        # The proof does not invent a secret: it carries the one the Caddyfile
        # was written with, which is what makes it the M2M and not a rehearsal.
        probes = FakeProbes()
        switch.proved(probes)
        sealed = [headers for _, headers in probes.asked
                  if caddy.GATE_HEADER in headers]
        self.assertEqual(len(sealed), 1)
        self.assertEqual(sealed[0][caddy.GATE_HEADER], env.gate_opened())
        self.assertEqual(sealed[0][switch.IDENTITY_HEADER], "Rafael")

    def test_the_sealed_identity_is_asked_inside_the_network_by_name(self):
        # O WebApp responde na rede e em lugar nenhum mais (§7c), então a
        # pergunta vai ao NOME dele na rede — e não ao laço do host, que é
        # exatamente o defeito que este pedaço conserta.
        probes = FakeProbes()
        switch.proved(probes)
        sealed = [url for url, headers in probes.asked if caddy.GATE_HEADER in headers]
        self.assertEqual(sealed, [
            f"http://{env.container(env.WEBAPP)}:{env.WEBAPP_PORT}/api/state"])

    def test_the_real_transport_is_the_environments_own_probe(self):
        # Sem costura, quem pergunta é `environment.inside` — o container
        # descartável na rede. O teste troca o transporte por um seam da MESMA
        # forma (`gate.Answer`) para provar que é ele que fica no lugar.
        seen: list[tuple[str, dict[str, str]]] = []

        def transport(url: str, headers: dict[str, str]) -> int:
            seen.append((url, dict(headers)))
            return 200

        with mock.patch.object(env, "inside", transport):
            self.assertTrue(switch.sealed())
        self.assertEqual(seen, [(
            f"http://{env.container(env.WEBAPP)}:{env.WEBAPP_PORT}/api/state",
            {switch.IDENTITY_HEADER: "Rafael",
             caddy.GATE_HEADER: env.gate_opened()},
        )])

    def test_a_probe_that_reaches_nothing_is_not_a_refusal(self):
        # "Não deu para saber" não é "foi recusado": nada respondeu, e uma prova
        # que lesse isso como recusa estaria culpando um portão que funciona.
        self.assertFalse(switch.proved(FakeProbes(sealed=None, unsealed=None)))

    def test_the_edge_answering_nothing_is_said_by_the_road_and_not_by_the_gate(self):
        # **O caso que se repete**: a primeira pergunta não recebe NADA. Ela tem
        # duas causas, e elas se consertam em lugares diferentes — o nome que não
        # resolve nesta máquina (o DNS do ambiente é §7a, e a máquina precisa
        # usá-lo) e o ambiente que não está de pé —, então a frase diz qual das
        # duas. Antes desta linha as duas viravam "o portão não foi provado", que
        # manda a pessoa procurar num lugar que não tem nada de errado.
        with mock.patch.object(switch, "reaches", lambda host: False):
            self.assertEqual(switch.unproved(FakeProbes(front=None)),
                             "services.switch.unresolved")
        with mock.patch.object(switch, "reaches", lambda host: True):
            self.assertEqual(switch.unproved(FakeProbes(front=None)),
                             "services.switch.unreachable")

    def test_the_first_claim_is_asked_once_and_the_machine_is_asked_its_name(self):
        # Duas coisas da mesma frase: a primeira pergunta é feita UMA vez (a
        # estrada sai do mesmo número que a recusa do portão, e uma pergunta a
        # mais é uma espera a mais), e a pergunta à máquina é sobre o NOME do
        # site — é ele que o DNS do ambiente responde (§7a).
        probes = FakeProbes(front=None)
        asked: list[str] = []
        with mock.patch.object(switch, "reaches",
                               lambda host: asked.append(host) or True):
            switch.unproved(probes)
        self.assertEqual(len(probes.asked), 1)
        self.assertEqual(asked, [env.site_host()])

    def test_with_nobody_to_prove_there_is_nothing_to_prove(self):
        # The proof speaks AS somebody: an identity is a row of `actor`, and a
        # folder with no row has no name to receive.
        with mock.patch.object(actors, "admins", lambda: []):
            self.assertFalse(switch.proved(FakeProbes()))

    def test_the_witness_is_a_row_the_probe_route_would_actually_answer(self):
        # `admins()` is "whoever has a credential", and a credential is not a
        # reach: a role that cannot read the probe's route answers 403, and 403
        # is the status the proof reads as "the identity was not taken". So the
        # witness is chosen by the permission the ROUTE is about to demand.
        self.assertEqual(switch.witness(), ("Rafael", env.gate_opened()))
        with mock.patch.object(actors, "may", lambda row, permission: False):
            self.assertIsNone(switch.witness())

    def test_a_folder_whose_gate_the_container_cannot_read_proves_nothing(self):
        # **O portão que a prova manda é a cópia ABERTA do diretório de
        # execução** (item 50), e sem ela não há prova: é ela que o WebApp
        # compara, e o arquivo da pasta é o envelope — uma prova que mandasse o
        # envelope acusaria o portão de recusar a identidade que ele aceita.
        env.gate_materialized().unlink()
        self.assertFalse(switch.proved(FakeProbes()))
        self.assertIsNone(switch.witness())


# ------------------------------------------------------------- the switch ---

class TheSwitch(FolderCase):
    """§6: the set of actions either closes, or everything goes back."""

    def test_the_switch_commits_only_after_the_gate_is_proved(self):
        self.person()
        fake = self.runtime()
        probes = FakeProbes()
        outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=probes)
        self.assertEqual(outcome, switch.SWITCHED)
        self.assertTrue(gate.on_gate())
        # And it was proved BEFORE the commit: the mode is written after the
        # probes, and the folder was on Forms while they ran.
        self.assertTrue(probes.asked)
        self.assertIn(i18n.tr("services.switch.done", url=switch.site()), text)
        # The environment is what stands behind the committed folder.
        self.assertTrue(fake.removed("caddy"))

    def test_the_forms_is_still_on_while_the_proof_runs(self):
        # The rule the order exists for: whatever the probes see, the folder is
        # the hosted path until the last line.
        self.person()
        self.runtime()
        seen = []

        def watch(url, headers):
            seen.append(gate.mode())
            return FakeProbes()(url, headers)

        self.quiet(switch.to_gate, secret=self.phrase, answer=watch)
        self.assertEqual(set(seen), {gate.FORMS})

    def test_a_proof_that_does_not_close_takes_everything_back(self):
        self.person()
        fake = self.runtime()
        outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes(sealed=403))
        self.assertEqual(outcome, switch.FAILED)
        # The folder is exactly what it was: Forms on, and the environment the
        # switch brought up is gone with its containers and its network.
        self.assertFalse(gate.on_gate())
        self.assertTrue(fake.removed("caddy"))
        self.assertTrue(fake.removed(env.WEBAPP))
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)
        self.assertIn(i18n.tr("services.switch.unproved"), text)

    def test_a_portal_that_does_not_answer_takes_everything_back(self):
        # A frase é a do PORTAL, e não a do portão: dizer "o portão não foi
        # provado" aqui culparia o provedor por uma borda que não roteia o
        # portal — e a pessoa iria procurar o defeito no lugar errado.
        self.person()
        fake = self.runtime()
        outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes(portal=431))
        self.assertEqual(outcome, switch.FAILED)
        self.assertFalse(gate.on_gate())
        self.assertIn(i18n.tr("services.switch.noportal"), text)
        self.assertNotIn(i18n.tr("services.switch.unproved"), text)
        # E o ambiente que a virada subiu vai embora com ela.
        self.assertTrue(fake.removed("caddy"))
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)

    def test_a_name_this_machine_does_not_resolve_is_said_with_its_name(self):
        # O que a pessoa lê quando o nome não resolve daqui: a frase da estrada,
        # com o nome, e não "o portão não foi provado". É a rodada de `up` e
        # `switch` que esta frase existe para não repetir.
        self.person()
        self.runtime()
        with mock.patch.object(switch, "reaches", lambda host: False):
            outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes(front=None))
        self.assertEqual(outcome, switch.FAILED)
        self.assertFalse(gate.on_gate())
        self.assertIn(
            i18n.tr("services.switch.unresolved", host=env.site_host()), text)
        self.assertNotIn(i18n.tr("services.switch.unproved"), text)

    def test_a_service_that_does_not_come_up_takes_everything_back(self):
        # The environment is not the switch, but the switch OWNS what it started:
        # a half-done environment is undone before the person is told.
        self.person()
        fake = self.runtime(fails=("pull",))
        outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        self.assertEqual(outcome, env.FAILED)
        self.assertFalse(gate.on_gate())
        self.assertTrue(fake.removed("caddy"))
        self.assertIn(i18n.tr("services.switch.failed"), text)

    def test_a_folder_with_nobody_to_prove_as_does_not_commit(self):
        # No witness is its own failure and not the gate's: nothing was tried
        # against the portal, and the folder is told which of the two it is.
        self.person()
        fake = self.runtime()
        with mock.patch.object(switch, "witness", lambda: None):
            outcome, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        self.assertEqual(outcome, switch.FAILED)
        self.assertFalse(gate.on_gate())
        self.assertIn(i18n.tr("services.switch.nowitness"), text)
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)

    def test_a_commit_the_folder_refuses_takes_the_environment_back(self):
        # The commit IS the switch: a folder that refuses the write refuses the
        # switch, and what the swap brought up goes with it — there is no state
        # where the environment stands and the record does not.
        self.person()
        fake = self.runtime()
        refused = files.ReadOnly(env.pin_file())
        with mock.patch.object(gate.settings, "save", side_effect=refused):
            with self.assertRaises(files.ReadOnly):
                self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        self.assertFalse(gate.on_gate())
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)

    def test_a_service_that_raises_on_its_files_takes_everything_back(self):
        # `up` reports a failure by returning and a broken disk by RAISING, and
        # both are steps that did not close: the exception keeps travelling, and
        # the environment does not.
        self.person()
        fake = self.runtime()
        broken = OSError("no space left on device")
        with mock.patch.object(env.files, "atomic_write_text", side_effect=broken):
            with self.assertRaises(OSError):
                self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        self.assertFalse(gate.on_gate())
        self.assertIn(["network", "rm", env.NETWORK], fake.calls)

    def test_a_folder_already_on_the_container_path_has_nothing_to_switch(self):
        self.person()
        self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        _, text = self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        self.assertIn(i18n.tr("services.switch.already"), text)
        self.assertTrue(gate.on_gate())

    def test_without_a_podman_the_two_ways_out_come_back_unchanged(self):
        # §7a's sentence, and neither way wrote anything: there is nothing to
        # roll back and nothing to commit.
        outcome, text = self.quiet(switch.to_gate, secret=self.phrase)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertFalse(gate.on_gate())
        self.assertFalse(env.pin_file().exists())

        outcome, text = self.quiet(switch.to_gate, secret=self.phrase, ask=lambda question: "n")
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)
        self.assertFalse(gate.on_gate())

    def test_the_failed_switch_leaves_the_hosted_webapp_working(self):
        # "o que existia antes continua funcionando": with the environment gone
        # and the Forms on, `at-cli webapp` takes the loop exactly as it did before
        # — no gate stands in its way, and nothing of the container path remains
        # to refuse it.
        self.person()
        self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes(sealed=403))
        self.assertFalse(gate.on_gate())
        # E o endereço do caminho hospedado é o de sempre: o laço.
        self.assertEqual(webapp.chosen_host(), webapp.HOST)
        # And the folder kept its people: the rollback moves nothing of the
        # person's (§3, the backup promise).
        self.assertTrue(actors.admins())


# ---------------------------------------------------------- the way back ---

class TheForms(FolderCase):
    """§6: the way back is the Wizard or the `cli`, both local — never automatic."""

    def on_gate(self) -> FakeRuntime:
        self.person()
        fake = self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        assert gate.on_gate()
        return fake

    def test_the_return_brings_the_environment_down_and_the_forms_back(self):
        fake = self.on_gate()
        _, text = self.quiet(switch.to_forms)
        self.assertEqual(gate.mode(), gate.FORMS)
        self.assertTrue(fake.removed("caddy"))
        self.assertIn(i18n.tr("services.forms.done"), text)

    def test_a_folder_on_forms_has_nothing_to_return_from(self):
        _, text = self.quiet(switch.to_forms)
        self.assertIn(i18n.tr("services.forms.already"), text)

    def test_the_return_works_without_a_podman(self):
        # A folder whose environment vanished is exactly the folder that needs
        # this door: the record goes back to Forms whether or not a runtime is
        # there to take anything down.
        self.person()
        self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        with mock.patch.object(podman, "present", lambda: False):
            _, text = self.quiet(switch.to_forms)
        self.assertEqual(gate.mode(), gate.FORMS)
        self.assertIn(i18n.tr("services.no_podman.down"), text)

    def test_the_read_only_folder_refuses_the_return_and_moves_nothing(self):
        self.person()
        fake = self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        calls = len(fake.calls)
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                self.quiet(switch.to_forms)
        self.assertTrue(gate.on_gate())
        self.assertEqual(len(fake.calls), calls)


class TheMissingEnvironment(FolderCase):
    """§6: the folder came back, and what was missing was the ground under it."""

    def on_gate(self) -> None:
        self.person()
        self.runtime()
        self.quiet(switch.to_gate, secret=self.phrase, answer=FakeProbes())
        assert gate.on_gate()

    def test_the_question_is_asked_where_the_absent_podman_is_noticed(self):
        # The two ways out of a folder already on the container path are NOT the
        # first offer's two: "continue on the hosted path" is not nothing here,
        # because the Forms is off and AT is closed.
        self.on_gate()
        asked: list[str] = []
        with mock.patch.object(podman, "present", lambda: False):
            _, text = self.quiet(
                env.ways_out, lambda question: (asked.append(question), "n")[1]
            )
        self.assertEqual(asked, [i18n.tr("services.missing.ask")])
        self.assertIn(i18n.tr("services.forms.done"), text)
        self.assertFalse(gate.on_gate())

    def test_choosing_to_install_says_how_and_moves_nothing(self):
        self.on_gate()
        with mock.patch.object(podman, "present", lambda: False):
            outcome, text = self.quiet(env.ways_out, lambda question: "s")
        self.assertEqual(outcome, env.INSTALL)
        self.assertIn(i18n.tr("services.no_podman.install"), text)
        self.assertTrue(gate.on_gate())

    def test_with_no_terminal_neither_way_is_taken_and_nothing_moves(self):
        self.on_gate()
        with mock.patch.object(podman, "present", lambda: False):
            outcome, text = self.quiet(env.ways_out)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.missing.no_tty"), text)
        self.assertTrue(gate.on_gate())

    def test_a_folder_on_forms_gets_the_first_offer_and_not_this_one(self):
        _, text = self.quiet(env.ways_out, lambda question: "n")
        self.assertNotIn(i18n.tr("services.missing.ask"), text)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)


# ----------------------------------------------------------------- the door ---

class TheCli(FolderCase):
    """`at-deploy services switch` and `services forms` — the two local doors."""

    def test_the_switch_reaches_the_environment_with_the_persons_answer(self):
        code, text = self.quiet(services, ["switch"], ask=lambda question: "n")
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)

    def test_a_switch_that_did_not_close_is_a_refusal(self):
        self.person()
        self.runtime()
        # A costura é `unproved`: a virada pergunta as quatro uma vez só e a
        # frase nomeia a que falhou, então é essa resposta que o teste troca —
        # e nenhuma sonda sai deste processo.
        with mock.patch.object(
            switch, "unproved", lambda answer=None: "services.switch.unproved"
        ):
            code, text = self.quiet(services, ["switch"], secret=self.phrase)
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("services.switch.unproved"), text)

    def test_the_return_is_an_ok_and_leaves_the_folder_on_forms(self):
        self.person()
        self.runtime()
        with mock.patch.object(switch, "unproved", lambda answer=None: None):
            self.quiet(services, ["switch"], secret=self.phrase)
        self.assertTrue(gate.on_gate())
        code, text = self.quiet(services, ["forms"])
        self.assertEqual(code, OK)
        self.assertIn(i18n.tr("services.forms.done"), text)
        self.assertFalse(gate.on_gate())

    def test_a_word_it_does_not_take_is_a_usage_error(self):
        for words in (["services", "virada"], ["services", "switch", "extra"], ["services", "path"]):
            with self.subTest(words=words):
                code, _ = self.quiet(main, words)
                self.assertEqual(code, USAGE)

    def test_every_word_of_the_switch_is_written_in_both_languages(self):
        for key in ("services.switch.already", "services.switch.rolling_back",
                    "services.switch.failed", "services.switch.unproved",
                    "services.switch.noportal",
                    "services.switch.nowitness", "services.switch.done",
                    "services.forms.already", "services.forms.done",
                    "services.gate.down",
                    "services.missing.ask", "services.missing.no_tty",
                    "deploy.services.about", "deploy.services.switch.about",
                    "deploy.services.forms.about", "deploy.error.read_only"):
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(i18n.text(key, code), key)


if __name__ == "__main__":
    unittest.main()
