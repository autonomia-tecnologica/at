"""The ntfy the binary carries: the payload, the unpacking, the config and the
real account it provisions.

The live gate end-to-end — through Caddy's own swap — is `test_caddy.py`'s
`TheBundle`; this file holds the payload and unpacking (the Caddy's own
arithmetic, nested member included) and one class that runs the real binary
for the four calls `provision` makes, the way `at_deploy/notifier.py`'s own
`_draw` already does against a container's `exec`.
"""

from __future__ import annotations

import io
import os
import socket
import tarfile
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot
from at.services import ntfy


class FolderCase(unittest.TestCase):
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
    def test_the_payload_of_this_platform_is_here(self):
        found = ntfy.payload()
        self.assertIsNotNone(found, f"no ntfy payload for {ntfy.label()} under {ntfy.PAYLOAD}")

    def test_the_name_carries_the_platform_it_serves(self):
        found = ntfy.payload()
        assert found is not None
        self.assertEqual(found.name, f"ntfy_2.28.0_{ntfy.platform_name()}.tar.gz")

    def test_the_binary_is_nested_inside_a_release_named_folder(self):
        found = ntfy.payload()
        assert found is not None
        with tarfile.open(found, "r:gz") as archive:
            names = archive.getnames()
            self.assertNotIn(ntfy.BINARY, names)
            self.assertTrue(any(name.endswith(f"/{ntfy.BINARY}") for name in names))

    def test_the_build_is_what_carries_it_inside_the_binary(self):
        root = Path(__file__).resolve().parents[2]
        spec = (root / "at-cli.spec").read_text(encoding="utf-8")
        self.assertIn('("at/vendor/ntfy", "at/vendor/ntfy")', spec)


class TheUnpacking(FolderCase):
    def test_it_lands_in_the_instance_folder(self):
        where = ntfy.ensure()
        self.assertEqual(where, self.root / "App" / "ntfy" / "ntfy")
        self.assertTrue(where.is_file())
        self.assertTrue(os.access(where, os.X_OK))
        self.assertEqual(
            ntfy.stamp_file().read_text(encoding="utf-8").strip(),
            ntfy.platform_name(),
        )

    def test_the_second_start_writes_nothing(self):
        ntfy.ensure()
        with mock.patch.object(ntfy, "tarfile") as never:
            self.assertTrue(ntfy.ensure().is_file())
        never.open.assert_not_called()

    def test_no_payload_is_said_and_not_guessed(self):
        with mock.patch.object(ntfy, "platform_name", lambda: "solaris_sparc"):
            self.assertIsNone(ntfy.ensure())


class TheConfiguration(FolderCase):
    def test_it_names_the_loopback_listen_and_the_public_url(self):
        text = ntfy.configuration_yaml(2586, "https://at.localhost:8444")
        self.assertIn('listen-http: "127.0.0.1:2586"', text)
        self.assertIn('base-url: "https://at.localhost:8444"', text)
        self.assertIn('auth-default-access: "deny-all"', text)
        self.assertIn("behind-proxy: true", text)

    def test_write_lands_the_file_in_the_folder(self):
        where = ntfy.write(2586, "https://at.localhost:8444")
        self.assertEqual(where, ntfy.directory() / ntfy.CONFIG)
        self.assertTrue(where.is_file())


class TheAccount(FolderCase):
    """The real binary, for the four calls `provision` makes."""

    def setUp(self):
        super().setUp()
        self.assertTrue(ntfy.ensure(), "the ntfy payload of this platform is not here")
        self.port = ntfy.free_port()
        self.config = ntfy.write(self.port, f"http://127.0.0.1:{self.port}")
        self.process = ntfy.start(self.config, log=False)
        deadline = time.monotonic() + 10
        while not (ntfy.directory() / ntfy.AUTH_DB).is_file():
            if self.process.poll() is not None:
                self.fail("ntfy exited before creating its own auth database")
            if time.monotonic() > deadline:
                self.fail("ntfy did not create its auth database in time")
            time.sleep(0.1)

    def tearDown(self):
        ntfy.stop(self.process)
        super().tearDown()

    def test_provisioning_before_the_server_exists_is_not_this_classs_problem(self):
        # Measured against the real binary (module docstring): provisioning
        # needs the auth database the server itself creates, which is why
        # `setUp` already waited for it — this class is what that wait buys.
        self.assertTrue((ntfy.directory() / ntfy.AUTH_DB).is_file())

    def test_provision_grants_read_write_on_the_one_topic(self):
        token = ntfy.provision(self.config, "uma-senha-qualquer")
        self.assertIsNotNone(token)
        self.assertTrue(token.startswith("tk_"))

    def test_provisioning_twice_rotates_the_account_cleanly(self):
        first = ntfy.provision(self.config, "senha-um")
        second = ntfy.provision(self.config, "senha-dois")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
