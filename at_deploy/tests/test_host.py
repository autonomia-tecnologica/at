"""TASK-190: `at-deploy host up|update` — the hosted path's own two processes,
kept standing across a reboot by `systemd --user`.

The runtime is faked the same way the container path's Podman already is
(`test_environment.py`'s `FakeRuntime`): one seam (`systemd.run`/`.ok`), every
call recorded, nothing here ever shells out to a real `systemctl`. What is
NOT faked is Authelia's own vendoring (`authelia.ensure()`) and config
writing (`authelia.write()`) — the same real, local, network-free unpacking
`at/tests/test_authelia.py` already exercises, because it is the one thing
this slice promises not to reinvent.
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
from at.core import boot
from at.services import authelia
from at.tests.payloads import required
from at_deploy import environment, host, systemd
from at_deploy.cli import OK, REFUSED, USAGE, main


class FakeSystemd:
    """`systemctl --user`'s seam, answered by a list — the same shape
    `test_environment.py`'s `FakeRuntime` already gives the container path's
    Podman. `active` names the units this fake already considers running,
    which is what `is-active --quiet` answers to."""

    def __init__(self, fails: tuple[str, ...] = (), active: tuple[str, ...] = ()) -> None:
        self.calls: list[list[str]] = []
        self.fails = set(fails)
        self.active = set(active)

    def run(self, args, **kw) -> SimpleNamespace:
        call = [str(part) for part in args]
        self.calls.append(call)
        if call[:1] == ["is-active"]:
            failed = not call or call[-1] not in self.active
        else:
            failed = bool(call) and call[0] in self.fails
        return SimpleNamespace(returncode=1 if failed else 0, stdout="", stderr="")

    def verbs(self) -> list[str]:
        return [call[0] for call in self.calls if call]


class FolderCase(unittest.TestCase):
    """A scratch Working Folder, and the units written into a scratch
    `unit_dir()` — never the real `~/.config/systemd/user/`."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.units = tempfile.TemporaryDirectory()
        self.unit_dir = Path(self.units.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        where = mock.patch.object(host, "unit_dir", lambda: self.unit_dir)
        where.start()
        self.addCleanup(where.stop)
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.units.cleanup()
        self.scratch.cleanup()

    def manager(self, fails: tuple[str, ...] = (),
                active: tuple[str, ...] = (), present: bool = True) -> FakeSystemd:
        fake = FakeSystemd(fails, active)
        there = mock.patch.object(systemd, "present", lambda: present)
        calls = mock.patch.object(systemd, "run", fake.run)
        asked = mock.patch.object(systemd, "ok", lambda args: fake.run(args).returncode == 0)
        for patch in (there, calls, asked):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def quiet(self, call, *args, **kw):
        output = io.StringIO()
        with redirect_stdout(output):
            result = call(*args, **kw)
        return result, output.getvalue()


class TheSystemdSeam(unittest.TestCase):
    """The one function every call to `systemctl` goes through."""

    def test_absent_binary_answers_none(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertIsNone(systemd.found())
            self.assertFalse(systemd.present())

    def test_every_call_is_for_this_persons_session(self):
        with mock.patch("subprocess.run") as ran:
            ran.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
            systemd.run(["daemon-reload"])
            argv = ran.call_args[0][0]
            self.assertIn("--user", argv)


@required(authelia)
class TheFirstTime(FolderCase):
    def test_no_systemd_is_refused_and_not_guessed_at(self):
        self.manager(present=False)
        outcome, text = self.quiet(host.host_up)
        self.assertEqual(outcome, host.NO_SYSTEMD)
        self.assertIn(i18n.tr("services.host.no_systemd"), text)
        self.assertEqual((self.unit_dir / host.AUTHELIA_UNIT).exists(), False)

    def test_up_writes_enables_and_starts_both_units(self):
        fake = self.manager()
        outcome = host.host_up()
        self.assertEqual(outcome, host.UP)

        authelia_unit = (self.unit_dir / host.AUTHELIA_UNIT).read_text(encoding="utf-8")
        webapp_unit = (self.unit_dir / host.WEBAPP_UNIT).read_text(encoding="utf-8")
        self.assertIn(str(authelia.binary()), authelia_unit)
        self.assertIn(f"Requires={host.AUTHELIA_UNIT}", webapp_unit)
        self.assertIn(str(environment.binary()), webapp_unit)

        self.assertIn(["daemon-reload"], fake.calls)
        self.assertIn(["enable", host.AUTHELIA_UNIT], fake.calls)
        self.assertIn(["restart", host.AUTHELIA_UNIT], fake.calls)
        self.assertIn(["enable", host.WEBAPP_UNIT], fake.calls)
        self.assertIn(["restart", host.WEBAPP_UNIT], fake.calls)

        # Authelia's own config and secrets are the real ones `at-cli webapp`
        # itself would write — this slice vendors nothing of its own.
        self.assertTrue((authelia.directory() / authelia.CONFIG).is_file())
        self.assertTrue(authelia.port_file().is_file())

    def test_a_second_up_is_provisioned_and_touches_nothing(self):
        self.manager()
        host.host_up()
        fake = self.manager()  # a fresh fake: no call of THIS up should land
        outcome, text = self.quiet(host.host_up)
        self.assertEqual(outcome, host.PROVISIONED)
        self.assertIn(i18n.tr("services.host.up.provisioned"), text)
        self.assertEqual(fake.calls, [])

    def test_update_before_any_up_is_refused(self):
        self.manager()
        outcome, text = self.quiet(host.host_update)
        self.assertEqual(outcome, host.FAILED)
        self.assertIn(i18n.tr("services.host.update.unprovisioned"), text)

    def test_no_payload_for_this_platform_fails_and_writes_no_unit(self):
        self.manager()
        with mock.patch.object(authelia, "ensure", lambda: None):
            outcome = host.host_up()
        self.assertEqual(outcome, host.FAILED)
        self.assertFalse((self.unit_dir / host.AUTHELIA_UNIT).exists())


@required(authelia)
class TheUpdate(FolderCase):
    def test_update_restarts_nothing_when_nothing_changed(self):
        self.manager()
        host.host_up()
        fake = self.manager(active=(host.AUTHELIA_UNIT, host.WEBAPP_UNIT))
        outcome, text = self.quiet(host.host_update)
        self.assertEqual(outcome, host.UPDATED)
        self.assertIn(i18n.tr("services.host.update.done"), text)
        self.assertNotIn(["restart", host.AUTHELIA_UNIT], fake.calls)
        self.assertNotIn(["restart", host.WEBAPP_UNIT], fake.calls)
        self.assertNotIn(["daemon-reload"], fake.calls)

    def test_a_changed_host_restarts_authelia_too_though_its_unit_text_did_not_change(self):
        # The regression this guards: the Authelia UNIT only names a config
        # PATH, never its content — a `--host` that changes rewrites
        # `configuration.yml` (the cookie domain) while the unit file stays
        # byte-for-byte the same, and a restart keyed on the unit alone would
        # never pick the new host up.
        self.manager()
        host.host_up(host="a.example.org")
        fake = self.manager(active=(host.AUTHELIA_UNIT, host.WEBAPP_UNIT))
        outcome = host.host_update(host="b.example.org")
        self.assertEqual(outcome, host.UPDATED)
        self.assertIn(["restart", host.AUTHELIA_UNIT], fake.calls)

    def test_a_changed_bind_port_restarts_only_the_webapp_unit(self):
        # `public_port` pinned on both calls: it is what Authelia's own
        # config carries (the portal URL the browser is told), so only the
        # bind port — the WebApp unit's own `--port` — may move here.
        self.manager()
        host.host_up(port=12399, public_port=443)
        fake = self.manager(active=(host.AUTHELIA_UNIT, host.WEBAPP_UNIT))
        outcome = host.host_update(port=12400, public_port=443)
        self.assertEqual(outcome, host.UPDATED)
        self.assertIn(["restart", host.WEBAPP_UNIT], fake.calls)
        self.assertNotIn(["restart", host.AUTHELIA_UNIT], fake.calls)

    def test_a_unit_not_already_active_is_started_even_unchanged(self):
        self.manager()
        host.host_up()
        # Nothing active this time: a crash between two `update`s, say.
        fake = self.manager(active=())
        outcome = host.host_update()
        self.assertEqual(outcome, host.UPDATED)
        self.assertIn(["restart", host.AUTHELIA_UNIT], fake.calls)
        self.assertIn(["restart", host.WEBAPP_UNIT], fake.calls)

    def test_a_failed_enable_is_a_failure_and_stops_there(self):
        self.manager()
        host.host_up()
        self.manager(fails=("enable",))
        outcome = host.host_update()
        self.assertEqual(outcome, host.FAILED)


@required(authelia)
class TheCli(FolderCase):
    """`at-deploy host up|update`, through the real command line."""

    def test_host_up_through_main(self):
        self.manager()
        code = main(["host", "up"])
        self.assertEqual(code, OK)

    def test_host_with_no_child_word_is_a_usage_error(self):
        self.manager()
        code = main(["host"])
        self.assertEqual(code, USAGE)

    def test_host_with_an_unknown_child_is_a_usage_error(self):
        self.manager()
        code = main(["host", "down"])
        self.assertEqual(code, USAGE)

    def test_host_up_with_flags_through_main(self):
        self.manager()
        code = main(["host", "up", "--host", "example.org", "--port", "8443"])
        self.assertEqual(code, OK)
        webapp_unit = (self.unit_dir / host.WEBAPP_UNIT).read_text(encoding="utf-8")
        self.assertIn("example.org", webapp_unit)
        self.assertIn("8443", webapp_unit)

    def test_host_up_rejects_a_bad_flag(self):
        self.manager()
        code = main(["host", "up", "--nope"])
        self.assertEqual(code, USAGE)

    def test_no_systemd_through_main_is_refused(self):
        self.manager(present=False)
        code = main(["host", "up"])
        self.assertEqual(code, REFUSED)


SAID = (
    "deploy.host.about", "deploy.host.up.about", "deploy.host.update.about",
    "services.host.no_systemd", "services.host.up.provisioned",
    "services.host.update.unprovisioned", "services.host.update.done",
)


class TheWords(unittest.TestCase):
    def test_every_sentence_is_written_in_both_languages(self):
        for key in SAID:
            for code in i18n.SUPPORTED:
                with self.subTest(key=key, language=code):
                    self.assertNotEqual(i18n.text(key, code), key)


if __name__ == "__main__":
    unittest.main()
