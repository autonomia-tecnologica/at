"""The gate, as the APP reads it (§6, §7b, item 27).

Two halves of the same record live in two artifacts, and this file is `at-cli`'s
half: which authenticator this folder is on (`core/gate.py`), and what the
WebApp does with that fact — the Forms off, `Basic` off with it, the entrance
closed, and AT closing when the portal stops answering.

**The deploy artifact is absent here and that is the point of the file.** The
switch that COMMITS the record is `at-deploy`'s and is proved in its own suite
(`at_deploy/tests/test_switch.py`); what is proved here is the "Done when" of
item 27 — a folder on the container path is served by `at-cli` on its own, with
nothing of §7 anywhere in the import graph. Nothing here touches a socket: the
portal is asked through the answer seam (`gate.Answer`).
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
import unittest
from collections.abc import Callable
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import actors, boot, gate, settings
from at.services import caddy
from at.tests import drawn_gate
from at.ui.webapp import app as webapp


class FakeProbes:
    """The portal's answers, without a socket — the `gate.Answer` seam."""

    def __init__(self, portal: int | None = 200) -> None:
        self.portal = portal
        self.asked: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> int | None:
        self.asked.append((url, dict(headers)))
        return self.portal


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

    def person(self, name: str = "Rafael") -> dict:
        """Somebody with a credential — what the gate proves."""
        return actors.create_admin(name, "uma-frase-bem-longa")

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


# --------------------------------------------------------------- the mode ---

class TheMode(FolderCase):
    """Where the folder records which path it is on, and how it reads it."""

    def test_a_folder_that_never_switched_is_on_forms(self):
        # The safe side, and the truthful one: a folder that has never proved a
        # gate is the hosted path (§6).
        self.assertEqual(gate.mode(), gate.FORMS)
        self.assertFalse(gate.on_gate())

    def test_a_value_the_release_does_not_know_reads_as_forms(self):
        # A record nobody can read is a record of nothing, and "nothing" here is
        # the path that asks the folder's own credential — never the other one.
        for value in ("", "authelia", True, 3):
            with self.subTest(value=value):
                settings.save({**settings.load(), gate.KEY: value})
                self.assertEqual(gate.mode(), gate.FORMS)

    def test_the_choice_lives_in_the_settings_beside_the_other_adjustments(self):
        # §4: `settings.json` holds what is neither translation nor table, and it
        # never holds a secret — the mode is an adjustment, not a credential.
        settings.save({**settings.load(), gate.KEY: gate.GATE})
        self.assertEqual(settings.get(gate.KEY), gate.GATE)
        self.assertTrue(gate.on_gate())

    def test_the_record_is_the_apps_to_read_with_the_deploy_absent(self):
        # The commit is the deploy's (`switch.to_gate`), and the READ is the
        # app's: this suite imports nothing of `at_deploy`, and the folder the
        # deploy left behind is read here exactly as the running `at-cli` reads it.
        gate.remember(gate.GATE)
        self.assertTrue(gate.on_gate())
        gate.remember(gate.FORMS)
        self.assertFalse(gate.on_gate())


# ------------------------------------------------------------- the portal ---

class ThePortal(FolderCase):
    """§7c: the WebApp asks the provider by the name the environment gave it."""

    def gate_env(self, value: str = "at-identity-provider:9091"):
        """The environment's own word about where its gate is (§7c)."""
        return mock.patch.dict(os.environ, {gate.GATE_ENV: value})

    def test_the_portal_answering_at_all_is_the_gate_standing(self):
        # Anything but nothing: the portal's own page, its redirect, even a
        # refusal are all the portal being there.
        for status in (200, 302, 401, 403):
            with self.subTest(status=status), self.gate_env():
                self.assertTrue(gate.standing(FakeProbes(portal=status)))

    def test_a_portal_that_stops_answering_is_the_gate_fallen(self):
        # Nothing listening, no route, no name: the one answer that closes AT.
        with self.gate_env():
            self.assertFalse(gate.standing(FakeProbes(portal=None)))

    def test_the_portal_the_container_asks_is_the_name_the_environment_gave(self):
        # The WebApp runs in a container on the environment's network: `127.0.0.1`
        # inside it is the WebApp's own loop, so the environment is what says
        # which name reaches the provider (§7c).
        with self.gate_env():
            self.assertEqual(gate.portal(), "http://at-identity-provider:9091")

    def test_a_webapp_the_environment_did_not_start_has_no_gate_to_ask(self):
        # And that is the CLOSED answer, not a guess: the hosted path never gets
        # here (its mode is `forms`), and the host's loop is a port any other
        # thing of the machine may answer on — measured, on the machine this was
        # written on, where a Transmission lives on 9091.
        self.assertIsNone(gate.portal())
        self.assertFalse(gate.standing(FakeProbes(portal=200)))


# ------------------------------------------------------- the WebApp reads it ---

class TheWebappObeysThePath(FolderCase):
    """§7c: with the Forms off, the person's door is the gate's — and no other."""

    def server(self) -> SimpleNamespace:
        """A server with the one thing the transports read: its registry."""
        return SimpleNamespace(sessions=webapp.session.Sessions())

    def test_forms_off_takes_the_cookie_session_with_it(self):
        # The cookie a Forms entrance opened is the LOCAL door; a folder on the
        # container path stops reading it, so a session left over from before the
        # switch proves nothing.
        server = self.server()
        opened = server.sessions.open(self.person())
        headers = {"Cookie": f"{webapp.session.COOKIE}={opened.token}"}
        # The same cookie, the same server: what the test moves is the record.
        self.assertIsNotNone(_handler(server, headers)._in())
        with mock.patch.object(webapp.gate, "on_gate", lambda: True):
            self.assertIsNone(_handler(server, headers)._in())

    def test_basic_goes_off_with_the_forms(self):
        self.person()
        settings.save({**settings.load(), webapp.BASIC_KEY: True})
        headers = {"Authorization": _basic("Rafael", "uma-frase-bem-longa")}
        self.assertIsNotNone(_handler(self.server(), headers)._in())
        with mock.patch.object(webapp.gate, "on_gate", lambda: True):
            self.assertIsNone(_handler(self.server(), headers)._in())

    def test_the_gate_still_enters_after_the_switch(self):
        self.person()
        drawn_gate()
        headers = {
            webapp.GATE_IDENTITY: "Rafael",
            caddy.GATE_HEADER: caddy.gate_secret() or "",
        }
        with mock.patch.object(webapp.gate, "on_gate", lambda: True):
            self.assertIsNotNone(_handler(self.server(), headers)._in())

    def test_the_record_in_the_settings_is_what_a_request_reads(self):
        # No mock over the mode anywhere here: how the folder records the path IS
        # how a request learns it, and that wire is the one worth a test.
        self.person()
        settings.save({**settings.load(), gate.KEY: gate.GATE})
        answered: list[dict] = []
        handler = _handler(self.server(), {}, answered.append)
        with mock.patch.object(webapp.gate, "standing", lambda answer=None: False):
            closed, _ = self.quiet(handler._gate)
        self.assertFalse(closed)
        self.assertEqual(answered[-1]["error"], i18n.tr("services.gate.down"))

    def test_the_forms_entrance_stops_handing_out_sessions(self):
        # The door §6 says leaves the path: a folder that kept opening Forms
        # sessions would be keeping the entrance the switch replaced.
        self.person()
        answered: list[dict] = []
        handler = _handler(self.server(), {}, answered.append)
        with mock.patch.object(webapp.gate, "on_gate", lambda: True):
            handler._post_session()
        self.assertEqual(answered[-1]["error"], i18n.tr("webapp.forms_off"))

    def test_a_fallen_gate_closes_bill(self):
        # §6's sentence, on the screen: AT does not reopen Forms on its own.
        # It is said PER REQUEST, and that is the point — the WebApp is a
        # container that comes up before the edge that fronts it, so a start-up
        # refusal would make a committed folder refuse to come up at all.
        self.person()
        answered: list[dict] = []
        handler = _handler(self.server(), {}, answered.append)
        with mock.patch.object(webapp.gate, "on_gate", lambda: True), \
                mock.patch.object(webapp.gate, "standing", lambda answer=None: False):
            closed, text = self.quiet(handler._gate)
        self.assertFalse(closed)
        self.assertEqual(answered[-1]["error"], i18n.tr("services.gate.down"))
        self.assertIn(i18n.tr("services.gate.down"), text)

    def test_a_folder_on_forms_never_asks_the_gate_anything(self):
        # The question does not exist on the hosted path: the gate is not this
        # folder's authenticator, so it has nothing to say about AT serving.
        self.person()
        asked = mock.Mock()
        handler = _handler(self.server(), {}, lambda payload: None)
        with mock.patch.object(webapp.gate, "standing", asked):
            handler._gate()
        asked.assert_not_called()


# ------------------------------------------------------------------ helpers ---

def _handler(server: SimpleNamespace, headers: dict[str, str],
             reply: Callable[[dict], None] | None = None) -> webapp.Handler:
    """A handler for one request, with no socket: the transports are read off the
    headers, and this is what lets the suite ask who a request proves — and what
    a refusal answers, when one is owed."""
    handler = webapp.Handler.__new__(webapp.Handler)
    handler.server = server  # type: ignore[assignment]
    handler.headers = headers  # type: ignore[assignment]
    handler._held = webapp._UNASKED
    handler._json = (  # type: ignore[method-assign]
        lambda payload, status=200, extra=None: (reply or (lambda p: None))(payload)
    )
    return handler


def _basic(name: str, credential: str) -> str:
    """The `Authorization` header a browser's dialog would send."""
    pair = base64.b64encode(f"{name}:{credential}".encode("utf-8")).decode("ascii")
    return f"Basic {pair}"


if __name__ == "__main__":
    unittest.main()
