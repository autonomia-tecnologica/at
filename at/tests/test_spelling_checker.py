"""The `spelling-checker` service: the motor's question and the process's life.

No Java and no network here: the server is a stdlib fake on the loopback that
answers in LanguageTool's own JSON shape, and the process is a fake too. The
real thing is measured by hand in a temporary Working Folder.
"""

from __future__ import annotations

import hashlib
import io
import json
import lzma
import os
import tarfile
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, spelling
from at.services import spelling_checker as service


class Fake(BaseHTTPRequestHandler):
    reply: bytes = b"{}"
    status = 200
    seen: list[str] = []

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        Fake.seen.append(self.rfile.read(size).decode("utf-8"))
        self.send_response(Fake.status)
        self.end_headers()
        self.wfile.write(Fake.reply)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"[]")

    def log_message(self, *args):
        pass


class Folder(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()


class TheQuestion(Folder):
    def serve(self, matches, status=200):
        Fake.reply = json.dumps({"matches": matches}).encode("utf-8")
        Fake.status = status
        Fake.seen = []
        server = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        spelling.remember(server.server_address[1])

    def test_without_a_port_it_is_unavailable_and_nothing_raises(self):
        self.assertFalse(spelling.available())
        self.assertIsNone(spelling.check("texto", "pt_BR"))

    def test_a_port_nobody_answers_on_is_unavailable(self):
        spelling.remember(1)
        self.assertFalse(spelling.available())
        self.assertIsNone(spelling.check("texto", "pt_BR"))

    def test_findings_carry_offset_length_rule_and_suggestions(self):
        self.serve([{
            "offset": 3, "length": 3, "message": "erro",
            "replacements": [{"value": "não"}, {"value": "nau"}],
            "rule": {"id": "PT_SIMPLE", "issueType": "misspelling",
                     "category": {"id": "TYPOS"}},
        }])
        self.assertTrue(spelling.available())
        found = spelling.check("Eu nao sei", "pt_BR")
        self.assertEqual(found, [spelling.Finding(
            3, 3, "PT_SIMPLE", ("não", "nau"), "TYPOS", "misspelling", "erro")])
        sent = Fake.seen[0]
        self.assertIn("language=pt-BR", sent)

    def test_nothing_found_is_an_empty_list_and_not_unavailable(self):
        self.serve([])
        self.assertEqual(spelling.check("tudo certo", "en_US"), [])

    def test_offsets_come_back_in_python_characters_not_utf16_units(self):
        text = "\U0001F600 nao"  # the emoji is two UTF-16 units
        self.serve([{"offset": 3, "length": 3, "replacements": [],
                     "rule": {"id": "X"}}])
        found = spelling.check(text, "pt_BR")
        assert found is not None
        self.assertEqual(text[found[0].offset:found[0].offset + found[0].length], "nao")

    def test_a_server_that_errors_is_unavailable(self):
        self.serve([], status=500)
        self.assertIsNone(spelling.check("x", "pt_BR"))

    def test_forget_makes_it_unavailable(self):
        self.serve([])
        spelling.forget()
        self.assertFalse(spelling.available())


class ThePayload(unittest.TestCase):
    def test_the_vendored_payload_matches_its_pin(self):
        if service.platform_name() is None:
            self.skipTest("no payload for this platform")
        found = service.payload()
        assert found is not None
        digest = hashlib.sha256(found.read_bytes()).hexdigest()
        self.assertEqual(digest, service.pinned())

    def test_the_upstream_pins_are_sha256(self):
        said = service.manifest()
        for key in ("jdk", "languagetool"):
            self.assertRegex(said[key]["sha256"], r"^[0-9a-f]{64}$")

    def test_a_platform_without_a_payload_is_none(self):
        with mock.patch.object(service, "platform_name", return_value=None):
            self.assertIsNone(service.payload())


class TheLife(Folder):
    def fake_payload(self, content=b"x"):
        vendor = Path(self.scratch.name) / "vendor"
        vendor.mkdir()
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w") as archive:
            for name, data in (("jre/bin/java", content), ("languagetool/x", b"y")):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(data))
        blob = lzma.compress(raw.getvalue())
        (vendor / "p.tar.xz").write_bytes(blob)
        (vendor / "manifest.json").write_text(json.dumps({
            "platform": service.platform_name() or "linux-x64",
            "payload": {"file": "p.tar.xz",
                        "sha256": hashlib.sha256(blob).hexdigest()},
        }))
        return vendor

    def patched(self, vendor):
        stack = [mock.patch.object(service, "PAYLOAD", vendor),
                 mock.patch.object(service, "platform_name", return_value="linux-x64")]
        for each in stack:
            each.start()
            self.addCleanup(each.stop)

    def test_it_unpacks_once_and_stamps(self):
        self.patched(self.fake_payload())
        self.assertFalse(service.unpacked())
        self.assertEqual(service.ensure(), service.java())
        self.assertTrue(service.unpacked())
        self.assertTrue(os.access(service.java(), os.X_OK))

    def test_a_payload_that_is_not_its_pin_is_not_unpacked(self):
        vendor = self.fake_payload()
        said = json.loads((vendor / "manifest.json").read_text())
        said["payload"]["sha256"] = "0" * 64
        (vendor / "manifest.json").write_text(json.dumps(said))
        self.patched(vendor)
        self.assertIsNone(service.ensure())
        self.assertFalse(service.java().exists())

    def test_the_command_listens_on_the_loopback_only_and_offline(self):
        argv = service.command(12345)
        self.assertIn("--port", argv)
        self.assertEqual(argv[argv.index("--port") + 1], "12345")
        self.assertNotIn("--public", argv)
        self.assertNotIn("--languageModel", argv)

    def test_bring_up_remembers_the_port_and_stop_forgets_it(self):
        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch.object(service, "ensure", return_value=Path("java")), \
                mock.patch.object(service, "start", return_value=process), \
                mock.patch.object(service, "started", return_value=True):
            got = service.bring_up()
        self.assertIs(got, process)
        self.assertIsNotNone(spelling.port())
        service.stop(got)
        process.terminate.assert_called_once()
        self.assertIsNone(spelling.port())

    def test_failures_are_unavailable_and_never_raise(self):
        with mock.patch.object(service, "ensure", return_value=None):
            self.assertIsNone(service.bring_up())
        with mock.patch.object(service, "ensure", side_effect=RuntimeError("boom")):
            self.assertIsNone(service.bring_up())
        with mock.patch.object(service, "ensure", return_value=Path("java")), \
                mock.patch.object(service, "start", return_value=mock.Mock()), \
                mock.patch.object(service, "started", return_value=False):
            self.assertIsNone(service.bring_up())
        self.assertFalse(spelling.available())

    def test_the_suite_never_spawns_a_jvm(self):
        self.assertFalse(service.AUTOSTART)


if __name__ == "__main__":
    unittest.main()
