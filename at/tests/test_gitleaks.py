"""The `gitleaks` the binary carries: the payload and the unpacking (item 32).

The same two promises the Caddy's file checks, for the same reasons. The first is
about the ARTIFACT: the repository carries the vendor's tarball byte for byte, and
`at-cli.spec` is what puts it inside the binary — and only that spec, because the
deploy has no scanning word. The second is about the FOLDER: the unpacking lands
in `App/gitleaks/`, with the stamp that says which platform it serves, and it
happens once — the second start writes nothing.

The last test here RUNS the unpacked binary, and that is the Caddy's precedent:
it is what keeps the payload honest — a placeholder would land a file that fails
it. What it runs is `version`, which reads nothing and touches no folder; nothing
here reaches the network, and nothing here scans anything.
"""

from __future__ import annotations

import io
import os
import subprocess
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot
from at.services import gitleaks

ROOT = Path(__file__).resolve().parents[2]

# The release this repository carries, and it is spelled in the tarball's own
# name: the version is the vendor's, and the platform is the vendor's word for it
# — which is NOT the Caddy's word, so it is written here rather than shared.
VERSION = "8.30.1"


class ThePayload(unittest.TestCase):
    """The bytes that travel inside the binary, in the repository they travel from."""

    def test_the_payload_of_this_platform_is_here(self):
        found = gitleaks.payload()
        self.assertIsNotNone(
            found,
            f"no gitleaks payload for {gitleaks.label()} under {gitleaks.PAYLOAD} — the "
            f"build collects that folder, and an empty one is collected as nothing",
        )

    def test_the_name_carries_the_version_and_the_platform(self):
        found = gitleaks.payload()
        assert found is not None
        self.assertEqual(
            found.name, f"gitleaks_{VERSION}_{gitleaks.platform_name()}.tar.gz"
        )

    def test_the_tarball_is_the_vendors_own(self):
        # The README and the LICENSE inside are the vendor's, and they are the
        # reason the payload is a tarball and not a bare binary: an artifact that
        # carries gitleaks carries what gitleaks is distributed with.
        found = gitleaks.payload()
        assert found is not None
        with tarfile.open(found, "r:gz") as archive:
            names = archive.getnames()
            self.assertIn(gitleaks.BINARY, names)
            self.assertIn("LICENSE", names)
            self.assertTrue(archive.getmember(gitleaks.BINARY).size > 1_000_000)

    def test_the_platform_is_the_vendors_word_for_it(self):
        # `x64`, and not the Caddy's `amd64`: two vendors, two spellings, and the
        # tarball is looked for by the one that names it.
        with mock.patch.object(gitleaks.sys, "platform", "linux"), \
                mock.patch.object(gitleaks, "_machine", lambda: "x86_64"):
            self.assertEqual(gitleaks.platform_name(), "linux_x64")
        with mock.patch.object(gitleaks.sys, "platform", "darwin"), \
                mock.patch.object(gitleaks, "_machine", lambda: "arm64"):
            self.assertEqual(gitleaks.platform_name(), "darwin_arm64")

    def test_a_platform_the_release_does_not_name_has_no_payload(self):
        with mock.patch.object(gitleaks, "platform_name", lambda: "solaris_sparc"):
            self.assertIsNone(gitleaks.payload())

    def test_the_app_is_what_carries_it_and_the_deploy_is_not(self):
        # `dist/at-cli` carrying the scanner is only true if the one place that
        # says what travels says it — an unpacking with nothing to unpack is a
        # word that fails on the machine of whoever downloaded the artifact. And
        # the other half: the deploy carries no scanning word, so it must not pay
        # the megabytes for this one.
        line = '("at/vendor/gitleaks", "at/vendor/gitleaks")'
        self.assertIn(line, (ROOT / "at-cli.spec").read_text(encoding="utf-8"))
        self.assertNotIn(line, (ROOT / "at-deploy.spec").read_text(encoding="utf-8"))


class TheUnpacking(unittest.TestCase):
    """`App/gitleaks/` — the binary, the stamp, and the rule that it happens once."""

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

    def stamp(self) -> Path:
        return gitleaks.stamp_file()

    def test_it_lands_in_the_instance_folder(self):
        where = gitleaks.ensure()
        self.assertEqual(where, self.root / "App" / "gitleaks" / "gitleaks")
        self.assertTrue(where.is_file())
        self.assertTrue(os.access(where, os.X_OK),
                        "the unpacked gitleaks must be runnable")
        self.assertEqual(self.stamp().read_text(encoding="utf-8").strip(),
                         gitleaks.platform_name())

    def test_the_second_start_writes_nothing(self):
        gitleaks.ensure()
        # The tarball itself is taken away: a second unpacking has nothing to
        # read, so a start that touched it would raise instead of answering.
        with mock.patch.object(gitleaks, "tarfile") as never:
            self.assertTrue(gitleaks.ensure().is_file())
        never.open.assert_not_called()

    def test_a_platform_that_does_not_match_unpacks_again(self):
        gitleaks.ensure()
        self.stamp().write_text("windows_x64\n", encoding="utf-8")
        gitleaks.binary().write_bytes(b"o gitleaks de outro sistema")
        gitleaks.ensure()
        self.assertEqual(self.stamp().read_text(encoding="utf-8").strip(),
                         gitleaks.platform_name())
        self.assertGreater(gitleaks.binary().stat().st_size, 1_000_000)

    def test_a_binary_the_person_deleted_came_back(self):
        # §3: what was extracted lives in the folder, and nothing regenerates on
        # its own — but asking for a scan is somebody asking, and a scan that
        # cannot run because its scanner is gone is not an answer.
        gitleaks.ensure()
        gitleaks.binary().unlink()
        self.assertTrue(gitleaks.ensure().is_file())

    def test_no_payload_is_said_and_not_guessed(self):
        with mock.patch.object(gitleaks, "platform_name", lambda: "solaris_sparc"):
            self.assertIsNone(gitleaks.ensure())

    def test_a_tarball_without_its_binary_is_refused_by_name(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        where = Path(scratch.name)
        packed = where / f"gitleaks_0_0_{gitleaks.platform_name()}.tar.gz"
        with tarfile.open(packed, "w:gz") as archive:
            archive.add(ROOT / "at-cli.spec")
        with mock.patch.object(gitleaks, "PAYLOAD", where):
            with self.assertRaises(gitleaks.GitleaksError):
                gitleaks.ensure()

    def test_the_payload_is_the_scanner_and_answers_its_version(self):
        # The run is what keeps the payload honest, and it is the Caddy's own
        # rule: a placeholder that unpacked would land a file that fails here.
        where = gitleaks.ensure()
        assert where is not None
        answered = subprocess.run([str(where), "version"], capture_output=True, text=True)
        self.assertEqual(answered.stdout.strip(), VERSION)


if __name__ == "__main__":
    unittest.main()
