"""The Caddy the binary carries: the payload, the unpacking and the Caddyfile.

Item 12 makes three promises, and this file checks each of them where it can be
checked. The first is about the ARTIFACT: the repository carries the vendor's
tarball byte for byte, and `at-cli.spec` is what puts it inside the binary. The
second is about the FOLDER: the unpacking lands in `App/`, with the stamp that
says which platform it serves, and it happens once — the second start writes
nothing. The third is about what a BROWSER gets, and that one is not read off a
string: the last class here starts the real Caddy out of the real payload, puts
the real WebApp behind it, and asks for the page over TLS.

Nothing here reaches the network. The Caddy runs on the loop, against the
payload this repository ships — which is also what keeps the payload honest: a
placeholder would fail the run, and the run is the only gate that reads the
tarball the way the product reads it.
"""

from __future__ import annotations

import io
import json
import os
import socket
import ssl
import subprocess
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, paths, settings
from at.services import caddy
from at.tests import POLL, drawn_gate
from at.ui.webapp import app as webapp

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "at-cli.spec"


def free_port() -> int:
    """A port nothing is on, asked of the system and given straight back."""
    holder = socket.socket()
    holder.bind((webapp.HOST, 0))
    port = holder.getsockname()[1]
    holder.close()
    return port


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
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()


class ThePayload(unittest.TestCase):
    """The bytes that travel inside the binary, in the repository they travel from."""

    def test_the_payload_of_this_platform_is_here(self):
        found = caddy.payload()
        self.assertIsNotNone(
            found,
            f"no Caddy payload for {caddy.label()} under {caddy.PAYLOAD} — the build "
            f"collects that folder, and an empty one is collected as nothing",
        )

    def test_the_name_carries_the_platform_it_serves(self):
        found = caddy.payload()
        assert found is not None
        self.assertEqual(found.name, f"caddy_2.11.4_{caddy.platform_name()}.tar.gz")

    def test_the_tarball_is_the_vendors_own(self):
        # The README and the LICENSE inside are the vendor's, and they are the
        # reason the payload is a tarball and not a bare binary: an artifact that
        # carries Caddy carries what Caddy is distributed with.
        found = caddy.payload()
        assert found is not None
        with tarfile.open(found, "r:gz") as archive:
            names = archive.getnames()
            self.assertIn(caddy.BINARY, names)
            self.assertIn("LICENSE", names)
            self.assertTrue(archive.getmember(caddy.BINARY).size > 1_000_000)

    def test_the_platform_is_the_vendors_word_for_it(self):
        with mock.patch.object(caddy.sys, "platform", "darwin"), \
                mock.patch.object(caddy, "_machine", lambda: "arm64"):
            self.assertEqual(caddy.platform_name(), "darwin_arm64")
        with mock.patch.object(caddy.sys, "platform", "linux"), \
                mock.patch.object(caddy, "_machine", lambda: "amd64"):
            self.assertEqual(caddy.platform_name(), "linux_amd64")

    def test_a_platform_the_release_does_not_name_has_no_payload(self):
        with mock.patch.object(caddy, "platform_name", lambda: "solaris_sparc"):
            self.assertIsNone(caddy.payload())

    def test_the_build_is_what_carries_it_inside_the_binary(self):
        # `dist/at` carrying the Caddy is only true if the one place that says
        # what travels says it — an unpacking with nothing to unpack is a flag
        # that fails on the machine of whoever downloaded the artifact.
        spec = SPEC.read_text(encoding="utf-8")
        self.assertIn('("at/vendor/caddy", "at/vendor/caddy")', spec)


class TheUnpacking(FolderCase):
    """`App/caddy/` — the binary, the stamp, and the rule that it happens once."""

    def stamp(self) -> Path:
        return caddy.stamp_file()

    def test_it_lands_in_the_instance_folder(self):
        where = caddy.ensure()
        self.assertEqual(where, self.root / "App" / "caddy" / "caddy")
        self.assertTrue(where.is_file())
        self.assertTrue(os.access(where, os.X_OK), "the unpacked Caddy must be runnable")
        self.assertEqual(self.stamp().read_text(encoding="utf-8").strip(),
                         caddy.platform_name())

    def test_the_second_start_writes_nothing(self):
        caddy.ensure()
        # The tarball itself is taken away: a second unpacking has nothing to
        # read, so a start that touched it would raise instead of answering.
        with mock.patch.object(caddy, "tarfile") as never:
            self.assertTrue(caddy.ensure().is_file())
        never.open.assert_not_called()

    def test_a_platform_that_does_not_match_unpacks_again(self):
        caddy.ensure()
        self.stamp().write_text("windows_amd64\n", encoding="utf-8")
        caddy.binary().write_bytes(b"o Caddy de outro sistema")
        caddy.ensure()
        self.assertEqual(self.stamp().read_text(encoding="utf-8").strip(),
                         caddy.platform_name())
        self.assertGreater(caddy.binary().stat().st_size, 1_000_000)

    def test_a_binary_the_person_deleted_came_back(self):
        # §3: what was extracted lives in the folder, and nothing regenerates on
        # its own — but running the flag is somebody asking, and asking for a
        # server that cannot start because its Caddy is gone is not an answer.
        caddy.ensure()
        caddy.binary().unlink()
        self.assertTrue(caddy.ensure().is_file())

    def test_no_payload_is_said_and_not_guessed(self):
        with mock.patch.object(caddy, "platform_name", lambda: "solaris_sparc"):
            self.assertIsNone(caddy.ensure())

    def test_a_tarball_without_its_binary_is_refused_by_name(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        where = Path(scratch.name)
        packed = where / f"caddy_0_0_{caddy.platform_name()}.tar.gz"
        with tarfile.open(packed, "w:gz") as archive:
            archive.add(SPEC)
        with mock.patch.object(caddy, "PAYLOAD", where):
            with self.assertRaises(caddy.CaddyError):
                caddy.ensure()


class TheSecret(FolderCase):
    """§7b's secret, on the READING side: the file the Caddy and the WebApp share.

    The DRAWING moved to the deploy with the rest of §7 (item 27) and is proved
    where it lives (`at_deploy/tests/test_environment.py`): `at-cli` is the one
    that reads this file with the deploy artifact absent, and that is what is
    written here — the state `up` leaves behind, and what `at-cli` makes of it.
    """

    def test_the_secret_is_read_off_the_file_the_caddy_wrote(self):
        drawn = drawn_gate()
        self.assertEqual(caddy.gate_secret(), drawn)
        self.assertEqual(caddy.gate_file().read_text(encoding="utf-8").strip(), drawn)

    def test_an_empty_file_is_no_gate(self):
        # A file nobody wrote is not a secret, and a Caddy that attached an empty
        # header would be sealing nothing.
        drawn_gate("")
        self.assertIsNone(caddy.gate_secret())

    def test_a_folder_that_never_drew_one_has_no_gate(self):
        # The hosted path's state, and the common one: no file, no secret, and
        # the Caddyfile gets no gate line.
        self.assertIsNone(caddy.gate_secret())
        self.assertFalse(caddy.gate_file().exists())


class TheCaddyfile(FolderCase):
    """The text AT generates — what the browser is about to be served."""

    def written(self, host: str = "localhost", port: int = 12399,
                backend: int = 41234, auth: str | None = None) -> str:
        return caddy.write_caddyfile(host, port, backend,
                                     auth=auth).read_text(encoding="utf-8")

    def gate(self, secret: str = "segredo-sorteado") -> None:
        """The secret as the deploy's `up` would have left it: in its own file."""
        drawn_gate(secret)

    def test_the_site_is_the_name_and_the_port_the_person_reaches(self):
        self.assertIn("https://localhost:12399 {", self.written())

    def test_the_tls_is_bills_own_certificate(self):
        # Not a public CA and not a plain HTTP: `tls internal` is what makes the
        # certificate exist at all, and §3 accepts the browser's warning as the
        # price of not depending on a public domain.
        self.assertIn("\ttls internal", self.written())

    def test_the_webapp_stays_on_the_loop_behind_it(self):
        text = self.written()
        self.assertIn("\treverse_proxy 127.0.0.1:41234", text)
        self.assertNotIn("0.0.0.0", text)

    def test_the_admin_endpoint_is_off_and_nothing_autosaves(self):
        # The admin endpoint is a local port that rewrites the running
        # configuration; the autosaved copy is the configuration — the gate
        # secret included — landing outside the folder.
        text = self.written()
        self.assertIn("\tadmin off", text)
        self.assertIn("\tpersist_config off", text)

    def test_it_neither_installs_trust_nor_redirects(self):
        # The trust store is entered with elevation, and §3 spends elevation on
        # an explicit request; the redirect listener is :80, which this product
        # never serves and a normal user cannot bind.
        text = self.written()
        self.assertIn("\tskip_install_trust", text)
        self.assertIn("\tauto_https disable_redirects", text)

    def test_the_storage_lives_inside_the_folder(self):
        self.assertIn(f'storage file_system "{caddy.storage_dir()}"', self.written())

    def test_the_authority_is_the_ones_the_local_ca_writes_inside_the_storage(self):
        # A CA é do PRÓPRIO Caddy — `tls internal` emite contra ela —, e o
        # caminho é dele e não uma decisão de AT: por isso ele é escrito uma vez,
        # e quem tem de confiar no certificado (o navegador, ou o celular de
        # §7f) importa ESTE arquivo.
        self.assertEqual(caddy.authority_file(),
                         caddy.storage_dir()
                         / "pki" / "authorities" / "local" / "root.crt")
        # E o mesmo caminho dentro de OUTRO storage: é assim que o caminho do
        # container o lê, do `/data` que ele monta da pasta de estado do serviço.
        other = Path("/tmp/outro-storage")
        self.assertEqual(caddy.authority_file(other),
                         other / "pki" / "authorities" / "local" / "root.crt")

    def test_no_gate_line_without_a_gate(self):
        self.assertNotIn(caddy.GATE_HEADER, self.written())

    def test_the_gate_secret_is_carried_when_there_is_one(self):
        self.gate()
        self.assertIn(f"header_up {caddy.GATE_HEADER} segredo-sorteado", self.written())

    def test_an_empty_gate_file_is_no_gate(self):
        self.gate("\n")
        self.assertNotIn(caddy.GATE_HEADER, self.written())

    def test_the_gate_asks_the_provider_who_is_calling(self):
        # §7b: forward-auth is the Caddy asking the identity provider BEFORE it
        # hands anything over, and the four headers are the provider's own answer
        # travelling on — `Remote-User` is the identity the WebApp reads. A
        # pergunta está DENTRO do `handle` de sempre (§7b: o portal é o outro),
        # e o que ela precede é o proxy do WebApp.
        self.gate()
        text = self.written(auth="127.0.0.1:9091")
        self.assertIn("forward_auth 127.0.0.1:9091 {", text)
        self.assertIn(f"\t\t\turi {caddy.AUTH_URI}", text)
        self.assertIn("\t\t\tcopy_headers Remote-User Remote-Groups Remote-Name "
                      "Remote-Email", text)
        self.assertLess(text.index("forward_auth"),
                        text.index("reverse_proxy 127.0.0.1:41234"))

    def test_the_portal_is_routed_straight_to_the_provider(self):
        # **O defeito que isto tranca, medido contra o container**: o portão
        # autentica por REDIRECIONAMENTO, então o portal não pode ser perguntado
        # — perguntar é o que manda o navegador para lá. Com o portal no site
        # inteiro, a borda perguntava sobre ele, a resposta era outro 302 com
        # `rd=`, e o laço reescrevia a URL até o `431`. O `handle` do portal é a
        # volta por fora da pergunta.
        self.gate()
        text = self.written(auth="127.0.0.1:9091")
        self.assertIn(f"\t@portal path {caddy.PORTAL} {caddy.PORTAL}/*", text)
        self.assertIn("\thandle @portal {", text)
        self.assertIn(f"\t\treverse_proxy 127.0.0.1:9091", text)
        # O portal vem ANTES da pergunta, e o proxy do WebApp depois dela.
        self.assertLess(text.index("handle @portal"),
                        text.index("forward_auth"))
        self.assertLess(text.index("forward_auth"),
                        text.index("reverse_proxy 127.0.0.1:41234"))

    def test_the_portal_is_never_asked_about(self):
        # O que fecha o laço não é só a ORDEM: é que a pergunta não esteja no
        # caminho do portal. Um `handle` que perguntasse sobre ele responderia
        # 302 de novo, e a pessoa continuaria sem entrar.
        self.gate()
        text = self.written(auth="127.0.0.1:9091")
        inside = text[text.index("handle @portal {"):text.index("\thandle {")]
        self.assertNotIn("forward_auth", inside)
        self.assertIn(f"reverse_proxy 127.0.0.1:9091", inside)

    def test_without_a_provider_there_is_no_portal_to_route(self):
        # O caminho hospedado divide este gerador, e um caminho que conserta o
        # container quebrando o hospedado é pior que o defeito: sem provedor não
        # há pergunta, e sem pergunta não há volta por fora dela.
        self.gate()
        for auth in (None, ""):
            with self.subTest(auth=auth):
                text = self.written(auth=auth)
                self.assertNotIn("@portal", text)
                self.assertNotIn("handle", text)

    def test_without_a_provider_there_is_nobody_to_ask(self):
        # A secret with no provider is a folder that drew one and never took the
        # container path: asking a question nobody answers would fail every
        # request, so the block is not written. The secret goes along all the
        # same — the WebApp only ever compares it.
        self.gate()
        text = self.written()
        self.assertNotIn("forward_auth", text)
        self.assertIn(caddy.GATE_HEADER, text)

    def test_without_a_secret_there_is_no_ask_either(self):
        # The two lines are one decision: it is the secret that says the request
        # came through the Caddy, and asking without sealing would be a login
        # that ends in a refusal.
        self.assertNotIn("forward_auth", self.written(auth="127.0.0.1:9091"))

    def test_the_address_is_the_one_the_person_named(self):
        # A certificate is issued for a name, so exposing to the local network
        # means naming the address the person reaches with — the Caddy's local CA
        # issues for an IP as well as for a hostname.
        self.assertIn("https://192.168.1.10:12399 {",
                      self.written(host="192.168.1.10"))
        self.assertTrue(caddy.wildcard("0.0.0.0"))
        self.assertTrue(caddy.wildcard("::"))
        self.assertFalse(caddy.wildcard("192.168.1.10"))

    def test_the_file_is_rewritten_on_every_start(self):
        # It is AT's file and not an adjustment: the port may have changed, and
        # the gate secret may have appeared.
        self.assertIn("https://localhost:12399 {", self.written())
        self.assertIn("https://localhost:12400 {", self.written(port=12400))


class TheAdaptedGate(FolderCase):
    """O Caddyfile do portão, lido pelo Caddy DE VERDADE.

    A suíte não sobe o Authelia — nem precisa: o que se prova aqui é que o
    arquivo que o AT gera é um arquivo que o Caddy ACEITA e ORDENA como o
    desenho diz. `adapt` lê o Caddyfile com o adaptador de verdade e para antes
    de abrir qualquer porta, então a pergunta é de sintaxe e de ordem, e nenhuma
    conexão sai daqui.

    E a ordem não é decorativa: o portal só deixa de ser perguntado porque o
    `handle` dele casa e vence o `handle` sem matcher, que é o fallback. Um
    arquivo que o Caddy ordenasse ao contrário teria o portal dentro do
    `forward_auth` de novo — o defeito, de volta, sem nada mudar no texto.
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.assertTrue(caddy.ensure(), "the payload of this platform is not here")

    def adapted(self, text: str) -> dict[str, dict]:
        """O que o Caddy de verdade leu do arquivo, servidor por servidor."""
        where = caddy.caddyfile_path()
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text, encoding="utf-8")
        done = subprocess.run(
            [str(caddy.binary()), "adapt", "--config", str(where),
             "--adapter", "caddyfile"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)["apps"]["http"]["servers"]

    def routes(self, text: str) -> list[dict]:
        """Os `handle` que o próprio Caddy lê do arquivo, na ordem dele."""
        servers = self.adapted(text)
        return next(iter(servers.values()))["routes"][0]["handle"][0]["routes"]

    def test_the_gate_configuration_is_one_the_caddy_takes(self):
        text = caddy.caddyfile("localhost", 12399, 41234,
                               gate="segredo-sorteado", auth="127.0.0.1:9091")
        routes = self.routes(text)
        self.assertEqual(len(routes), 2)
        self.assertEqual(routes[0]["match"],
                         [{"path": [caddy.PORTAL, f"{caddy.PORTAL}/*"]}])
        self.assertIsNone(routes[1].get("match"),
                          "o resto do site tem de ser o fallback, e não um caminho")

    def test_the_portal_goes_to_the_provider_and_the_rest_through_the_ask(self):
        text = caddy.caddyfile("localhost", 12399, 41234,
                               gate="segredo-sorteado", auth="127.0.0.1:9091")
        portal, rest = self.routes(text)
        portal_proxy = portal["handle"][0]["routes"][0]["handle"][0]
        self.assertEqual(portal_proxy["upstreams"], [{"dial": "127.0.0.1:9091"}])
        # O resto do site pergunta ao provedor (o `uri` da pergunta, e o mesmo
        # endereço do portal), anexa o segredo e entrega ao WebApp. O Caddy
        # escreve o `forward_auth` como um proxy com `rewrite`, então o que se lê
        # aqui é o que ele ENTENDEU, e não a palavra do Caddyfile.
        asked = json.dumps(rest)
        self.assertIn(caddy.AUTH_URI, asked)
        self.assertIn("127.0.0.1:9091", asked)
        self.assertIn("127.0.0.1:41234", asked)
        self.assertIn(f"X-At-Gate", asked)
        self.assertIn("segredo-sorteado", asked)

    def test_the_hosted_configuration_has_no_portal_to_route(self):
        # O mesmo gerador, sem portão: um `handle` aqui seria uma rota que ninguém
        # pediu, e o caminho hospedado é o que a maioria das pastas usa.
        text = caddy.caddyfile("localhost", 12399, 41234)
        routes = self.routes(text)
        self.assertEqual(len(routes), 1)
        self.assertIsNone(routes[0].get("match"))

    def test_the_second_site_is_one_the_caddy_takes_and_does_not_ask_about(self):
        # **O arquivo com dois nomes é um arquivo que o Caddy ACEITA**, e o que
        # se lê aqui é o que ele ENTENDEU: os dois no mesmo servidor, na mesma
        # porta, separados por casador de HOST — e o do notificador sem
        # pergunta nenhuma, que é a medição que o mantém fora do portão
        # (`subscribers=0` atrás do Authelia, `101` sem ele).
        text = caddy.caddyfile(
            "at.local", 443, 41234, gate="segredo-sorteado", auth="127.0.0.1:9091",
            bind="0.0.0.0", upstream="at-webapp",
            outside=(("ntfy.at.local", "at-notifier:2586"),),
        )
        servers = self.adapted(text)
        # Um servidor só: os dois blocos dividem a porta e o `bind`, e é o
        # casador de host que diz qual nome responde o quê.
        self.assertEqual(len(servers), 1)
        server = next(iter(servers.values()))
        self.assertEqual(server["listen"], ["0.0.0.0:443"])
        hosts = {tuple(route["match"][0]["host"]): route for route in server["routes"]}
        self.assertEqual(sorted(hosts), [("at.local",), ("ntfy.at.local",)])
        askless = json.dumps(hosts[("ntfy.at.local",)])
        self.assertIn("at-notifier:2586", askless)
        self.assertNotIn("forward_auth", askless)
        self.assertNotIn("segredo-sorteado", askless)
        # E o site continua com a pergunta e com o segredo — os dois nomes não
        # se confundem. O Caddy escreve o `forward_auth` como um proxy com
        # `rewrite` para o `uri` da pergunta, então é isso que se lê aqui.
        asked = json.dumps(hosts[("at.local",)])
        self.assertIn(caddy.AUTH_URI, asked)
        self.assertIn("127.0.0.1:9091", asked)
        self.assertIn("segredo-sorteado", asked)
        self.assertIn("at-webapp:41234", asked)


class TheExposedRun(FolderCase):
    """`run` with the flag: the Caddy's port in front, the WebApp behind."""

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", "uma-frase-bem-longa")

    def probe(self, **kw) -> tuple[str, mock.Mock, mock.Mock]:
        output = io.StringIO()
        built = mock.Mock()
        built.return_value.server_address = ("127.0.0.1", 41234)
        with mock.patch.object(webapp, "make_server", built), \
                mock.patch.object(caddy, "start", mock.Mock()) as started, \
                mock.patch.object(caddy, "started", return_value=True):
            with redirect_stdout(output):
                code = webapp.run(12399, **kw)
        self.assertEqual(code, 0)
        return output.getvalue(), built, started

    def test_the_webapp_takes_an_ephemeral_port_on_the_loop(self):
        # Two processes cannot share one port, and what has to stay stable is the
        # address the person reaches — so the WebApp is the one that moves.
        _, built, _ = self.probe(include_caddy=True)
        built.assert_called_once_with(0, webapp.HOST)

    def test_with_the_flag_the_address_is_the_name_and_not_the_folders_choice(self):
        # With the Caddy in front, `--host` is the NAME the certificate is issued
        # for (§3) and the WebApp answers on the loop behind it: the folder's
        # address is an ADDRESS, and here an address is not what is being named.
        settings.save({**settings.load(), webapp.HOST_KEY: "0.0.0.0"})
        self.probe(include_caddy=True)
        self.assertIn("https://localhost:12399 {",
                      caddy.caddyfile_path().read_text(encoding="utf-8"))

    def test_the_caddyfile_names_the_backend_the_webapp_took(self):
        self.probe(include_caddy=True)
        text = caddy.caddyfile_path().read_text(encoding="utf-8")
        self.assertIn("https://localhost:12399 {", text)
        self.assertIn("reverse_proxy 127.0.0.1:41234", text)

    def test_the_answer_is_the_url_the_person_types(self):
        output, _, started = self.probe(include_caddy=True)
        self.assertIn(i18n.tr("caddy.serving", url="https://localhost:12399"), output)
        started.assert_called_once()

    def test_a_caddy_that_dies_takes_the_announcement_with_it(self):
        # A Caddy that cannot bind exits in a blink, and AT announcing a URL
        # for a port nothing is on would be a promise nobody could tell was
        # broken. The port it names is the one the person reaches.
        output = io.StringIO()
        built = mock.Mock()
        built.return_value.server_address = ("127.0.0.1", 41234)
        with mock.patch.object(webapp, "make_server", built), \
                mock.patch.object(caddy, "start", mock.Mock()), \
                mock.patch.object(caddy, "started", return_value=False):
            with redirect_stdout(output):
                code = webapp.run(12399, include_caddy=True)
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("webapp.port_taken", port=12399), output.getvalue())

    def test_a_wildcard_is_refused_because_a_certificate_needs_a_name(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = webapp.run(12399, host="0.0.0.0", include_caddy=True)
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("caddy.address_needs_name", host="0.0.0.0"),
                      output.getvalue())
        self.assertFalse(caddy.caddyfile_path().exists())


class TheAddress(FolderCase):
    """The address AT answers on: the folder's choice, and the loop as default.

    **Leaving the loop is not refused**, and the reason is that the same address
    means two different things: a container's `0.0.0.0` is inside a network,
    behind the edge and the gate (§7b, §7c), and a machine's is on a LAN. An app
    that cannot tell them apart would refuse the container or wave the machine
    through — so what it does is SAY where it answers, and what leaving the loop
    costs is the environment's security note's to say.
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", "uma-frase-bem-longa")

    def chose(self, value: object) -> None:
        """The folder's choice, written where only the folder writes."""
        settings.save({**settings.load(), webapp.HOST_KEY: value})

    def served(self, **kw) -> mock.Mock:
        """The server AT would build, taken away — the address is what is read."""
        built = mock.Mock()
        with mock.patch.object(webapp, "make_server", built):
            with redirect_stdout(io.StringIO()):
                code = webapp.run(12399, **kw)
        self.assertEqual(code, 0)
        return built

    def test_the_loop_is_the_default_and_what_the_product_recommends(self):
        self.assertEqual(webapp.chosen_host(), webapp.HOST)
        self.served().assert_called_once_with(12399, webapp.HOST)

    def test_the_folder_may_name_another_address(self):
        # The door is `settings.json`, on the same shelf `basic_auth` sits on:
        # an adjustment of the installation, and never a credential.
        self.chose("0.0.0.0")
        self.assertEqual(webapp.chosen_host(), "0.0.0.0")
        self.served().assert_called_once_with(12399, "0.0.0.0")

    def test_the_command_line_says_it_for_one_run(self):
        self.chose("0.0.0.0")
        self.served(host="192.168.1.10").assert_called_once_with(12399, "192.168.1.10")

    def test_a_value_that_is_not_a_name_answers_the_default(self):
        for value in (7, "", "   ", True, ["0.0.0.0"]):
            with self.subTest(value=value):
                self.chose(value)
                self.assertEqual(webapp.chosen_host(), webapp.HOST)

    def test_a_settings_file_nobody_can_read_answers_the_default(self):
        # The same side `gate.mode` falls on, for the same reason: a folder whose
        # settings are broken is not a folder that moved its address.
        where = paths.settings_file()
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text("{ this is not JSON", encoding="utf-8")
        self.assertEqual(webapp.chosen_host(), webapp.HOST)


class TheBlink(unittest.TestCase):
    """The moment that decides whether AT gets to announce a URL."""

    def test_a_caddy_that_exited_is_not_started(self):
        dead = mock.Mock()
        dead.wait.return_value = 1
        self.assertFalse(caddy.started(dead))

    def test_a_caddy_that_is_still_there_is_started(self):
        alive = mock.Mock()
        alive.wait.side_effect = subprocess.TimeoutExpired("caddy", 0.3)
        self.assertTrue(caddy.started(alive))


class TheRealTls(FolderCase):
    """The claim a browser can check: TLS, on the loop, from the real Caddy.

    The Caddy is the one this repository ships, unpacked the way the flag
    unpacks it, in front of the real WebApp. What is asserted is what the person
    would see: the certificate is not from a public authority, and the page still
    arrives when the browser is told to accept it.
    """

    def setUp(self):
        super().setUp()
        self.port = free_port()
        self.server = webapp.make_server(0)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": POLL}, daemon=True,
        )
        self.thread.start()
        self.process = None
        self.assertTrue(caddy.ensure(), "the payload of this platform is not here")

    def tearDown(self):
        caddy.stop(self.process)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def url(self, path: str = "/") -> str:
        return f"https://localhost:{self.port}{path}"

    def test_the_certificate_is_bills_own_and_not_a_public_one(self):
        config = caddy.write_caddyfile("localhost", self.port,
                                       self.server.server_address[1])
        self.process = caddy.start(config, log=False)
        self.wait_for_tls()

        with self.assertRaises(urllib.error.URLError) as caught:
            urllib.request.urlopen(self.url())
        self.assertIsInstance(caught.exception.reason, ssl.SSLCertVerificationError)

    def test_the_page_arrives_over_that_tls(self):
        config = caddy.write_caddyfile("localhost", self.port,
                                       self.server.server_address[1])
        self.process = caddy.start(config, log=False)
        self.wait_for_tls()

        # The unverified context is the person clicking through the warning §3
        # accepts; what is under test is that there IS a TLS to click through.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(self.url(), context=context) as answer:
            self.assertEqual(answer.status, 200)
            self.assertEqual(answer.headers["Content-Security-Policy"], webapp.CSP)
            self.assertIn(b"<div id=", answer.read())

    def wait_for_tls(self, timeout: float = 20.0) -> None:
        """Wait until the Caddy answers a handshake, or fail on the reason why.

        Caddy binds before it obtains the certificate, so a refused connection
        and a completed handshake are both "not ready yet"; the process dying is
        the only thing that ends the wait early, and it is worth a failure that
        carries Caddy's own words.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.fail(f"the Caddy exited with {self.process.returncode}")
            try:
                with socket.create_connection(("localhost", self.port), timeout=1):
                    return
            except OSError:
                time.sleep(0.1)
        self.fail(f"the Caddy did not answer on {self.url()} in {timeout}s")


if __name__ == "__main__":
    unittest.main()
