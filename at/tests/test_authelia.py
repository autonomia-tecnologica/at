"""The Authelia the binary carries: the payload, the unpacking, the config.

The live gate — Caddy, Authelia and ntfy together, answering real requests —
is `test_caddy.py`'s `TheBundle`; this file holds what does not need a live
process: the payload this repository ships, the unpacking into `App/
authelia/`, and the two files this module writes (`configuration.yml`,
`users.yml`), checked the same way `test_caddy.py`'s own `ThePayload` and
`TheUnpacking` check the Caddy's.
"""

from __future__ import annotations

import io
import os
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot
from at.services import authelia
from at.tests.payloads import needs, required


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
        needs(self, authelia)
        found = authelia.payload()
        self.assertIsNotNone(
            found,
            f"no Authelia payload for {authelia.label()} under {authelia.PAYLOAD}",
        )

    def test_the_name_carries_the_platform_it_serves(self):
        needs(self, authelia)
        found = authelia.payload()
        assert found is not None
        self.assertEqual(found.name, f"authelia-v4.39.28-{authelia.platform_name()}.tar.gz")

    def test_the_tarball_is_the_vendors_own(self):
        needs(self, authelia)
        found = authelia.payload()
        assert found is not None
        with tarfile.open(found, "r:gz") as archive:
            names = archive.getnames()
            self.assertIn(authelia.BINARY, names)
            self.assertTrue(archive.getmember(authelia.BINARY).size > 1_000_000)

    def test_the_platform_is_dashed_and_not_underscored(self):
        with mock.patch.object(authelia.sys, "platform", "linux"), \
                mock.patch.object(authelia, "_machine", lambda: "x86_64"):
            self.assertEqual(authelia.platform_name(), "linux-amd64")

    def test_darwin_and_windows_have_no_release_to_find(self):
        # Authelia ships no darwin or windows asset — measured against the
        # vendor's own `releases/latest`, and said instead of guessed.
        for system in ("darwin", "win32"):
            with mock.patch.object(authelia.sys, "platform", system):
                self.assertIsNone(authelia.platform_name())

    def test_the_build_is_what_carries_it_inside_the_binary(self):
        root = Path(__file__).resolve().parents[2]
        spec = (root / "at-cli.spec").read_text(encoding="utf-8")
        self.assertIn('("at/vendor/authelia", "at/vendor/authelia")', spec)


@required(authelia)
class TheUnpacking(FolderCase):
    def test_it_lands_in_the_instance_folder(self):
        where = authelia.ensure()
        self.assertEqual(where, self.root / "App" / "services" / "authelia" / "authelia")
        self.assertTrue(where.is_file())
        self.assertTrue(os.access(where, os.X_OK))
        self.assertEqual(
            authelia.stamp_file().read_text(encoding="utf-8").strip(),
            authelia.platform_name(),
        )

    def test_the_second_start_writes_nothing(self):
        authelia.ensure()
        with mock.patch.object(authelia, "tarfile") as never:
            self.assertTrue(authelia.ensure().is_file())
        never.open.assert_not_called()

    def test_no_payload_is_said_and_not_guessed(self):
        with mock.patch.object(authelia, "platform_name", lambda: "solaris-sparc"):
            self.assertIsNone(authelia.ensure())


class TheCookieDomain(unittest.TestCase):
    def test_a_name_with_a_dot_is_accepted(self):
        self.assertTrue(authelia.valid_cookie_domain("at.localhost"))

    def test_a_bare_loopback_word_is_refused(self):
        self.assertFalse(authelia.valid_cookie_domain("localhost"))

    def test_an_ip_is_accepted_with_no_dot_needed(self):
        self.assertTrue(authelia.valid_cookie_domain("127.0.0.1"))

    def test_an_arbitrary_word_with_no_dot_is_refused(self):
        self.assertFalse(authelia.valid_cookie_domain("meumaquina"))


class TheConfiguration(FolderCase):
    def test_the_users_file_carries_only_people_with_a_credential(self):
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        text = authelia.users_yaml()
        self.assertIn('"Rafael"', text)
        self.assertIn("displayname:", text)
        self.assertNotIn('"password": ""', text)

    def test_an_empty_folder_writes_an_empty_map(self):
        self.assertEqual(authelia.users_yaml(), authelia.users_yaml())
        self.assertIn("users: {}", authelia.users_yaml())

    def test_the_configuration_names_the_loopback_listen_address(self):
        text = authelia.configuration_yaml("at.localhost", 9091, 443)
        self.assertIn('address: "tcp://127.0.0.1:9091/authelia"', text)
        self.assertIn('authelia_url: "https://at.localhost/authelia"', text)
        self.assertIn("domain: at.localhost", text)
        self.assertNotIn("redis:", text)

    def test_a_public_port_other_than_443_is_spelled_out(self):
        text = authelia.configuration_yaml("192.168.1.10", 9091, 8443)
        self.assertIn("https://192.168.1.10:8443/authelia", text)

    def test_extra_rules_are_each_their_own_domain(self):
        text = authelia.configuration_yaml("at.localhost", 9091, 443,
                                           rules=("ntfy.example",))
        self.assertIn("domain: ntfy.example", text)

    def test_write_lands_both_files_in_the_folder(self):
        config = authelia.write("at.localhost", 9091, 443)
        self.assertEqual(config, authelia.directory() / authelia.CONFIG)
        self.assertTrue(config.is_file())
        self.assertTrue((authelia.directory() / authelia.USERS).is_file())

    def test_the_theme_with_both_sides_wears_the_auto_palette(self):
        with mock.patch.dict(os.environ, {"AT_THEME": "at"}):
            self.assertEqual(authelia.palette(), "auto")
            text = authelia.configuration_yaml("at.localhost", 9091, 443)
        self.assertIn("theme: auto", text)

    def test_a_one_sided_theme_pins_its_side(self):
        from at.ui.webapp import app
        for sides, expected in ((["light"], "light"), (["dark"], "dark")):
            with mock.patch.object(app, "theme_sides", return_value=sides):
                self.assertEqual(authelia.palette(), expected)

    def test_the_configuration_points_at_the_brand_assets(self):
        text = authelia.configuration_yaml("at.localhost", 9091, 443)
        self.assertIn(f'asset_path: "{authelia.assets_directory()}"', text)

    def test_write_lands_the_logo_and_a_valid_favicon(self):
        authelia.write("at.localhost", 9091, 443)
        where = authelia.assets_directory()
        logo = (where / "logo.png").read_bytes()
        self.assertTrue(logo.startswith(b"\x89PNG"))
        ico = (where / "favicon.ico").read_bytes()
        self.assertEqual(ico[:6], b"\x00\x00\x01\x00\x01\x00")
        self.assertEqual(ico[22:], logo)

    def test_secrets_are_drawn_once_and_kept(self):
        first = authelia.session_secret()
        second = authelia.session_secret()
        self.assertEqual(first, second)
        self.assertTrue((authelia.directory() / authelia.SESSION_SECRET).is_file())


@required(authelia)
class TheValidation(FolderCase):
    """The real binary's own `validate-config` — not a guess about the YAML."""

    def test_the_written_configuration_validates(self):
        self.assertTrue(authelia.ensure())
        config = authelia.write("at.localhost", authelia.free_port(), 443)
        self.assertTrue(authelia.validate(config))


if __name__ == "__main__":
    unittest.main()
