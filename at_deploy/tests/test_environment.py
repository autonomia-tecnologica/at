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
    "services.down.done", "services.status.line", "services.status.site",
    "services.status.running", "services.status.stopped", "services.status.absent",
    "services.dnsmasq.file.header", "services.gate.drawn",
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
        self.fails = set(fails)
        self.running = running

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
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
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
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

    def test_a_tag_that_moves_is_not_a_pin(self):
        # The rule this reads is the shape of the digest, so a pin written by
        # hand has to pass the same door.
        moving = env.Image("docker.io/library/caddy", "latest", "sha256:abc")
        self.assertFalse(moving.at_the_pin())
        nothing = env.Image("docker.io/library/caddy", "2.11.4", "")
        self.assertFalse(nothing.at_the_pin())

    def test_the_loop_is_where_every_service_publishes(self):
        # Measured in the retired environment and inherited: a host deny-list
        # does not cover a published container port — the port goes through DNAT
        # and the `input` hook never sees it — so what closes the LAN is
        # publishing on loopback, never a firewall rule.
        for service in env.SERVICES:
            for port in service.ports:
                with self.subTest(service=service.name, port=port.port):
                    self.assertEqual(port.address, env.LOOP)

    def test_the_caddy_is_the_edge_and_has_no_port_of_its_own(self):
        # It shares the host's network: what it publishes is AT's own address,
        # and what it proxies to is the loop, which a container on a network of
        # its own cannot see.
        caddy = _service("caddy")
        self.assertEqual(caddy.network, env.HOST_NETWORK)
        self.assertEqual(caddy.ports, ())

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
        published = [port.published() for port in _service("dnsmasq").ports]
        self.assertEqual(published, ["127.0.0.1:53:53/udp", "127.0.0.1:53:53/tcp"])


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
        outcome, text = self.quiet(env.up)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.no_podman.no_tty"), text)

    def test_the_two_ways_are_both_in_the_question(self):
        said = []
        outcome, text = self.quiet(env.up, ask=lambda question: (said.append(question), "n")[1])
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.no_podman.hosted"), text)
        self.assertEqual(len(said), 1)

    def test_installing_is_the_persons_act_and_bill_only_says_how(self):
        outcome, text = self.quiet(env.up, ask=lambda question: "s")
        self.assertEqual(outcome, env.INSTALL)
        self.assertIn(i18n.tr("services.no_podman.install"), text)

    def test_neither_way_out_writes_anything(self):
        for answer in ("s", "n"):
            with self.subTest(answer=answer):
                self.quiet(env.up, ask=lambda question, answer=answer: answer)
        self.assertFalse(env.pin_file().exists())
        self.assertFalse(env.state("dnsmasq").exists())

    def test_nothing_is_asked_of_the_runtime_without_a_podman(self):
        with mock.patch.object(podman, "run", mock.Mock()) as called:
            self.quiet(env.up)
        called.assert_not_called()


class TheUp(FolderCase):
    """`up` with a Podman: the argv is the whole of what AT decides."""

    def test_every_service_runs_the_image_at_the_pin(self):
        fake = self.runtime()
        outcome, text = self.quiet(env.up)
        self.assertEqual(outcome, env.UP)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(service.image.reference(), [call[-1] for call in fake.calls])
                self.assertIn(i18n.tr(
                    "services.up.service", service=i18n.tr(service.label),
                    reference=service.image.reference(), where=env.state(service.name),
                ), text)

    def test_the_dnsmasq_publishes_on_the_loop_and_mounts_its_own_folder(self):
        fake = self.runtime()
        self.quiet(env.up)
        argv = _call(fake, "at-dnsmasq")
        self.assertIn("--network", argv)
        self.assertIn(env.NETWORK, argv)
        self.assertIn("127.0.0.1:53:53/udp", argv)
        self.assertIn(f"{env.state('dnsmasq')}:{env.DNSMASQ_CONFIG}:Z", argv)

    def test_the_caddy_shares_the_host_network_and_mounts_its_state(self):
        fake = self.runtime()
        self.quiet(env.up)
        argv = _call(fake, "at-caddy")
        self.assertIn(env.HOST_NETWORK, argv)
        self.assertNotIn("--publish", argv)
        self.assertIn(f"{env.state('caddy')}:{env.CADDY_CONFIG}:Z", argv)
        self.assertIn(f"{env.state('caddy') / 'storage'}:{env.CADDY_DATA}:Z", argv)

    def test_the_containers_are_named_and_labeled_as_bills(self):
        fake = self.runtime()
        self.quiet(env.up)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                argv = _call(fake, env.container(service.name))
                self.assertIn(env.container(service.name), argv)
                self.assertIn(f"{env.LABEL}={service.name}", argv)

    def test_the_configuration_lands_in_the_state_folder(self):
        self.runtime()
        self.quiet(env.up)
        self.assertIn("address=/", (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"))
        self.assertIn("reverse_proxy", (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"))

    def test_the_caddyfile_of_the_container_keeps_its_storage_in_the_container(self):
        # §7a: the same Caddy, the same generator — and the one line that is a
        # path and not a decision is where the folder is inside the container.
        self.runtime()
        self.quiet(env.up)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f'storage file_system "{env.CADDY_DATA}"', text)
        self.assertNotIn(str(self.root / "App" / "caddy" / "storage"), text)

    def test_the_pin_is_recorded_once_the_service_is_up(self):
        self.runtime()
        self.quiet(env.up)
        recorded = env.held()
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertEqual(recorded[service.name]["version"], service.image.version)
                self.assertEqual(recorded[service.name]["digest"], service.image.digest)

    def test_a_service_already_there_is_replaced_and_not_refused(self):
        # Two containers cannot share a name, and the name is the service.
        fake = self.runtime()
        self.quiet(env.up)
        self.assertIn(["rm", "--force", "at-caddy"], fake.calls)

    def test_an_image_that_does_not_arrive_stops_the_service(self):
        fake = self.runtime(fails=("pull",))
        outcome, text = self.quiet(env.up)
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
        outcome, text = self.quiet(env.up)
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
        self.quiet(env.up)
        self.assertIn(["network", "exists", env.NETWORK], fake.calls)
        self.assertIn(["network", "create", env.NETWORK], fake.calls)

    def test_the_read_only_folder_refuses_the_write(self):
        self.runtime()
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                self.quiet(env.up)


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
        self.quiet(env.up)
        return fake

    def conf(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")

    def users(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_USERS).read_text(encoding="utf-8")

    def secret(self) -> str:
        return (env.state(env.IDENTITY) / env.IDENTITY_SESSION).read_text(encoding="utf-8")

    def test_the_provider_is_published_on_the_loop_and_mounts_its_state(self):
        # The Caddy shares the host's network, so how it reaches the provider is
        # the loop — and publishing there is what keeps the LAN closed (§7a).
        service = _service(env.IDENTITY)
        self.assertEqual([port.published() for port in service.ports],
                         ["127.0.0.1:9091:9091/tcp"])
        hosts = [mount.host for mount in service.mounts]
        self.assertIn("", hosts)       # `/config`: what AT wrote for it
        self.assertIn("data", hosts)   # `/data`: what the provider keeps itself

    def test_the_configuration_puts_bill_behind_the_gate_as_one_more_app(self):
        # §7b: "o AT entra por forward-auth como um app a mais, nunca como
        # exceção". Deny by default, and AT's own site named as one_factor.
        self.up()
        text = self.conf()
        self.assertIn("default_policy: deny", text)
        self.assertIn(f"    - domain: {env.HOST}", text)
        self.assertIn("      policy: one_factor", text)
        self.assertIn(f"authelia_url: https://{env.HOST}:{env.PORT}", text)

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
        self.quiet(env.up)
        return fake

    def caddyfile(self) -> str:
        return (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")

    def test_up_draws_the_secret_and_says_where_it_is(self):
        # §7b: "um valor sorteado pelo AT na instalação". The installation is
        # the environment coming up, and this is the one message it owes.
        self.runtime()
        _, text = self.quiet(env.up)
        self.assertTrue(caddy.gate_secret())
        self.assertIn(i18n.tr("services.gate.drawn", where=caddy.gate_file()), text)

    def test_a_secret_already_drawn_is_not_drawn_again(self):
        # Two different secrets are a Caddy attaching one value and a WebApp
        # taking another: every identity would be refused until both restarted
        # from the same file.
        self.up()
        held = caddy.gate_secret()
        _, text = self.quiet(env.up)
        self.assertEqual(caddy.gate_secret(), held)
        self.assertNotIn(i18n.tr("services.gate.drawn", where=caddy.gate_file()), text)

    def test_the_caddyfile_carries_the_secret_and_asks_the_gate(self):
        self.up()
        text = self.caddyfile()
        self.assertIn(f"header_up {caddy.GATE_HEADER} {caddy.gate_secret()}", text)
        # And the ask comes first: the Caddy finds out who is calling before it
        # hands anything to the WebApp.
        self.assertLess(text.index("forward_auth"), text.index("reverse_proxy"))
        self.assertIn(f"forward_auth {env.LOOP}:{env.IDENTITY_PORT}", text)
        self.assertIn(f"uri {caddy.AUTH_URI}", text)
        self.assertIn("copy_headers Remote-User", text)

    def test_without_a_podman_no_gate_is_drawn(self):
        # The folder that never took the container path has no gate, and a
        # secret drawn for a path nobody took would be a file nobody reads.
        self.quiet(env.up)
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
        # tomorrow enters this question by existing.
        with self.machine(1024):
            self.assertEqual(env.blocked(), (53,))
        with self.machine(54):
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
        self.assertIn(i18n.tr("services.elevation.refused", ports="53"), text)

    def test_with_no_terminal_the_permission_is_not_requested(self):
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate)
        self.assertEqual(outcome, env.NO_ANSWER)
        self.assertIn(i18n.tr("services.elevation.no_tty", ports="53"), text)

    def test_a_machine_that_does_not_move_says_so_instead_of_announcing(self):
        # Asking and getting nothing is the one answer that must not be called a
        # success: the services would come up and fail to bind.
        with self.machine(1024):
            outcome, text = self.quiet(env.elevate, lambda question: "s",
                                       spend=lambda *argv: None)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr("services.elevation.failed", ports="53"), text)

    def test_up_asks_before_it_starts_anything_and_leaves_the_folder_alone(self):
        # A refusal is the folder's previous state untouched: no secret drawn, no
        # network created, no service started.
        fake = self.runtime()
        with self.machine(1024):
            outcome, text = self.quiet(env.up, lambda question: "n")
        self.assertEqual(outcome, env.HOSTED)
        self.assertIn(i18n.tr("services.elevation.refused", ports="53"), text)
        self.assertFalse(caddy.gate_file().exists())
        self.assertEqual(fake.calls, [])

    def test_a_machine_that_already_allows_it_goes_straight_to_the_services(self):
        fake = self.runtime()
        with self.machine(0):
            outcome, _ = self.quiet(env.up)
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

    def test_the_site_follows_the_network_when_there_is_one(self):
        with mock.patch.object(vpn, "name", lambda call=None: "host.example-tailnet.ts.net"), \
                mock.patch.object(vpn, "address", lambda call=None: "100.64.0.1"):
            self.assertEqual(env.site_host(), "host.example-tailnet.ts.net")
            self.runtime()
            self.quiet(env.up)
            self.assertIn("https://host.example-tailnet.ts.net:8443",
                          (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8"))
            identity = (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")
            self.assertIn("domain: host.example-tailnet.ts.net", identity)
            self.assertIn("authelia_url: https://host.example-tailnet.ts.net:8443", identity)
            # The name AT answers for points at where the edge actually is.
            self.assertIn("address=/at.local/100.64.0.1",
                          (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"))

    def test_without_a_network_nothing_moves(self):
        # The supported state, and not a degraded one: the loop, exactly as
        # before §7e existed.
        self.assertEqual(env.site_host(), env.HOST)
        self.runtime()
        self.quiet(env.up)
        self.assertIn(f"https://{env.HOST}:{env.PORT}",
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
            outcome, text = self.quiet(env.up)
        self.assertEqual(outcome, env.FAILED)
        self.assertIn(i18n.tr(
            "services.up.no_address", service=i18n.tr("services.dnsmasq.name"),
            address=NOBODY,
        ), text)


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
        self.quiet(env.up)
        before = (env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8")
        self.quiet(env.down)
        self.assertEqual((env.state("dnsmasq") / "dnsmasq.conf").read_text(encoding="utf-8"), before)

    def test_without_a_podman_there_is_nothing_to_bring_down(self):
        _, text = self.quiet(env.down)
        self.assertIn(i18n.tr("services.no_podman.down"), text)


class TheStatus(FolderCase):
    """What is standing, read off the runtime and said in AT's words."""

    def test_a_running_service_is_said_to_be_up(self):
        self.runtime(running="true")
        _, text = self.quiet(env.status)
        for service in env.SERVICES:
            with self.subTest(service=service.name):
                self.assertIn(i18n.tr(
                    "services.status.line", service=i18n.tr(service.label),
                    state=i18n.tr("services.status.running"),
                    reference=service.image.reference(),
                ), text)

    def test_a_container_that_is_there_and_stopped_says_so(self):
        self.runtime(running="false")
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.status.stopped"), text)

    def test_a_container_that_never_came_up_says_so(self):
        self.runtime(fails=("container",))
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.status.absent"), text)

    def test_without_a_podman_the_environment_has_nothing_standing(self):
        _, text = self.quiet(env.status)
        self.assertIn(i18n.tr("services.no_podman.status"), text)

    def test_the_deliverys_credential_is_reported_by_its_file_and_never_its_value(self):
        # §7f: what a person needs to know is that the credential exists and
        # WHERE it lives — the value is a secret and is never printed.
        self.runtime()
        self.quiet(env.up)
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
        self.quiet(env.up)
        return fake

    def test_the_webapp_publishes_on_the_loop_at_bills_own_port(self):
        # The pair cannot drift from the WebApp's OWN constants: the port the
        # container publishes is the one the WebApp listens on, and the loop is
        # where the Caddy's `reverse_proxy` reaches it (§7a's measured rule).
        service = _service(env.WEBAPP)
        self.assertEqual([port.published() for port in service.ports],
                         ["127.0.0.1:12345:12345/tcp"])
        self.assertEqual((env.WEBAPP_HOST, env.WEBAPP_PORT),
                         (webapp.HOST, webapp.DEFAULT_PORT))

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
        # binary this folder holds, told to serve the WebApp on the loop.
        fake = self.up()
        argv = _call(fake, env.container(env.WEBAPP))
        self.assertEqual(argv[-4:],
                         [env.binary(), "webapp", "--port", str(env.WEBAPP_PORT)])
        self.assertTrue(argv[-4].startswith(str(env.paths.working_folder())))

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

    def test_a_service_that_needs_nothing_is_told_nothing(self):
        fake = self.up()
        for name in ("dnsmasq", env.IDENTITY, "caddy", env.NOTIFIER):
            with self.subTest(service=name):
                self.assertNotIn("--env", _call(fake, env.container(name)))


class TheWebappBehindIt(FolderCase):
    """The Caddy publishes the WebApp, and this is where that pair cannot drift."""

    def test_the_site_the_container_caddy_serves_is_bills_and_on_the_loop(self):
        self.runtime()
        self.quiet(env.up)
        text = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn(f"https://{env.HOST}:{env.PORT}", text)
        self.assertIn(f"reverse_proxy 127.0.0.1:{env.WEBAPP_PORT}", text)


class TheNotifier(FolderCase):
    """§7f's notifier: the service, the memory it keeps, and the rule it inherits.

    The notifier is the one service of §7 that no edge fronts, and the rule that
    keeps it out of the gate is a MEASUREMENT and not a preference — which is why
    it is read here as the absence of the gate in everything the environment
    writes around it.
    """

    def up(self) -> FakeRuntime:
        fake = self.runtime()
        self.quiet(env.up)
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
        self.quiet(env.up)
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
        # the line ntfy reads — and the URL the config hands back is the same
        # address, because a `base-url` naming another one would put a dead link
        # in every notification.
        self.up()
        text = self.conf()
        self.assertIn(f'listen-http: ":{env.NOTIFIER_PORT}"', text)
        self.assertIn(f'base-url: "http://{env.LOOP}:{env.NOTIFIER_PORT}"', text)

    def test_the_door_is_shut_to_whoever_brings_no_token(self):
        # §6: "No `ntfy`, isso é a ACL por tópico: o AT publica, o celular lê,
        # e nenhum dos dois tokens serve para o resto". A default of read-write
        # would make the token decorative.
        self.up()
        self.assertIn('auth-default-access: "deny-all"', self.conf())

    def test_the_gate_does_not_front_the_notifier(self):
        # Measured in the retired environment and inherited: behind Authelia the
        # notifier answered `subscribers=0` — the gate authenticates by redirect
        # and session cookie, and the phone app takes the 302 and never connects
        # —, and `101` without it. So the edge does not name it, the gate's rule
        # does not name it, and nothing of the gate is handed to its container.
        fake = self.up()
        caddyfile = (env.state("caddy") / "Caddyfile").read_text(encoding="utf-8")
        identity = (env.state(env.IDENTITY) / env.IDENTITY_YAML).read_text(encoding="utf-8")
        for text, where in ((caddyfile, "Caddyfile"), (identity, env.IDENTITY_YAML)):
            with self.subTest(file=where):
                self.assertNotIn(env.NOTIFIER, text)
                self.assertNotIn(str(env.NOTIFIER_PORT), text)
        argv = _call(fake, env.container(env.NOTIFIER))
        self.assertNotIn(env.GATE_ENV, argv)
        self.assertNotIn(caddy.GATE_HEADER, argv)

    # ------------------------------------------------------ §7f's delivery ---

    def test_up_creates_the_deliverys_credential_in_the_notifier(self):
        # §7f's other half, and the reason the environment comes up COMPLETE: the
        # service, and AT's own credential inside it — the account, the scope,
        # and the token (`services/notifier.py`).
        self.runtime()
        _, text = self.quiet(env.up)
        self.assertEqual(notifier.token(), DRAWN_TOKEN)
        self.assertIn(i18n.tr(
            "services.notifier.drawn", where=notifier.token_file(),
            topic=notifier.TOPIC, scope=notifier.SCOPE,
        ), text)
        # The value is a secret: it is kept, and it is never said.
        self.assertNotIn(DRAWN_TOKEN, text)

    def test_the_credential_is_kept_at_0600_and_never_in_an_argv(self):
        # The interim while the vault does not exist (item 14): a 0600 file
        # beside the folder's other secrets, never printed, never in the argv —
        # which on this machine means never in a `ps`.
        fake = self.up()
        mode = stat.S_IMODE(notifier.token_file().stat().st_mode)
        self.assertEqual(mode, 0o600, f"the credential is readable by others: {mode:o}")
        self.assertNotIn(DRAWN_TOKEN, [part for call in fake.calls for part in call])

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
        held = notifier.token()
        _, text = self.quiet(env.up)
        self.assertEqual(notifier.token(), held)
        self.assertNotIn(i18n.tr(
            "services.notifier.drawn", where=notifier.token_file(),
            topic=notifier.TOPIC, scope=notifier.SCOPE,
        ), text)


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
