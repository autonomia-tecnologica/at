"""release.fetch — the vendored payloads are pinned by manifest and pulled at build.

No test here touches the network: the "network" is a fake opener over bytes, and
the folders are scratch copies.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from release import build, fetch


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


class FakeNet:
    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.calls: list[str] = []

    def __call__(self, url):
        self.calls.append(url)
        return io.BytesIO(self.files[url])


class FetchCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.vendor = Path(self.scratch.name) / "vendor"
        (self.vendor / "tool").mkdir(parents=True)
        self.good = b"the real bytes"
        self.url = "https://example.invalid/tool_1.tar.gz"
        self.write_manifest(self.good)
        self.net = FakeNet({self.url: self.good})

    def write_manifest(self, blob: bytes):
        (self.vendor / "tool" / "manifest.json").write_text(json.dumps({
            "service": "tool",
            "files": [{"file": "tool_1.tar.gz", "platform": "linux-x64",
                       "url": self.url, "sha256": digest(blob)},
                      {"file": "tool_1.zip", "platform": "windows-x64",
                       "url": self.url + ".zip", "sha256": digest(b"win")}],
        }), encoding="utf-8")

    def path(self, name="tool_1.tar.gz"):
        return self.vendor / "tool" / name


class TheFetch(FetchCase):
    def test_a_missing_file_is_downloaded_and_verified(self):
        done = fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertEqual(done, ["tool/tool_1.tar.gz"])
        self.assertEqual(self.path().read_bytes(), self.good)
        self.assertEqual(fetch.missing(self.vendor, {"linux-x64"}), [])
        self.assertEqual([i["file"] for i in fetch.missing(self.vendor)], ["tool_1.zip"])

    def test_a_present_file_with_the_right_hash_is_not_downloaded(self):
        self.path().write_bytes(self.good)
        self.assertEqual(fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net), [])
        self.assertEqual(self.net.calls, [])

    def test_a_second_run_downloads_nothing(self):
        fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertEqual(len(self.net.calls), 1)

    def test_a_wrong_hash_from_the_net_is_an_error_and_leaves_nothing(self):
        self.net.files[self.url] = b"tampered"
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertIn("is not the pinned", str(caught.exception))
        self.assertFalse(self.path().exists())
        self.assertEqual([p.name for p in self.path().parent.iterdir()], ["manifest.json"])

    def test_a_bad_local_file_is_deleted_and_replaced(self):
        self.path().write_bytes(b"corrupt")
        fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertEqual(self.path().read_bytes(), self.good)

    def test_a_bad_local_file_with_a_bad_net_is_never_kept(self):
        self.path().write_bytes(b"corrupt")
        self.net.files[self.url] = b"also bad"
        with self.assertRaises(fetch.FetchError):
            fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertFalse(self.path().exists())

    def test_a_download_that_fails_is_a_clear_error(self):
        def boom(url):
            raise OSError("no route")
        with self.assertRaises(fetch.FetchError) as caught:
            fetch.fetch(self.vendor, {"linux-x64"}, opener=boom)
        self.assertIn("download failed", str(caught.exception))

    def test_the_cache_is_reused_and_the_payload_lands_in_place(self):
        cache = Path(self.scratch.name) / "cache"
        fetch.fetch(self.vendor, {"linux-x64"}, cache=cache, opener=self.net)
        self.path().unlink()
        fetch.fetch(self.vendor, {"linux-x64"}, cache=cache, opener=self.net)
        self.assertEqual(self.path().read_bytes(), self.good)
        self.assertEqual(len(self.net.calls), 1)

    def test_the_real_manifests_name_a_url_and_a_hash_for_every_file(self):
        found = fetch.entries()
        self.assertTrue(found)
        for item in found:
            with self.subTest(item=item["file"]):
                self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
                if item["service"] != fetch.GENERATED:
                    self.assertTrue(item["url"].startswith("https://"))


class TheGeneratedPayload(FetchCase):
    def setUp(self):
        super().setUp()
        folder = self.vendor / fetch.GENERATED
        folder.mkdir()
        self.blob = b"packed"
        self.manifest = {"payload": {"file": "sc.tar.xz", "sha256": digest(self.blob)}}
        (folder / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_the_generator_runs_when_absent_and_must_reproduce_the_pin(self):
        def generate(argv):
            (self.vendor / fetch.GENERATED / "sc.tar.xz").write_bytes(self.blob)
            (self.vendor / fetch.GENERATED / "manifest.json").write_text("{}")
            return 0
        with mock.patch("release.spelling_checker.main", generate):
            fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertEqual(json.loads((self.vendor / fetch.GENERATED / "manifest.json").read_text()),
                         self.manifest)

    def test_a_generated_payload_with_another_hash_is_deleted(self):
        def generate(argv):
            (self.vendor / fetch.GENERATED / "sc.tar.xz").write_bytes(b"different")
            return 0
        with mock.patch("release.spelling_checker.main", generate):
            with self.assertRaises(fetch.FetchError):
                fetch.fetch(self.vendor, {"linux-x64"}, opener=self.net)
        self.assertFalse((self.vendor / fetch.GENERATED / "sc.tar.xz").exists())


class TheBuild(unittest.TestCase):
    def test_the_build_refuses_when_the_fetch_fails(self):
        with mock.patch.object(build.fetch, "fetch",
                               side_effect=build.fetch.FetchError("tool/x: boom")), \
                mock.patch.object(build.shutil, "which", return_value="/usr/bin/podman"), \
                mock.patch.object(build.subprocess, "run") as run, \
                mock.patch.object(build.Path, "is_dir", return_value=True):
            self.assertEqual(build.main([]), 1)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
