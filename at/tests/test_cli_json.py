"""`--json`: the same run said as one JSON object (TASK-131)."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import __version__, i18n
from at.core import boot
from at.prose import payload
from at.ui.cli import main


class JsonOut(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(Path(self.scratch.name)), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def say(self, *words: str) -> tuple[int, dict]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(list(words))
        text = out.getvalue()
        self.assertEqual(len(text.strip().splitlines()), 1)
        body = json.loads(text)
        self.assertEqual(body["code"], code)
        self.assertEqual(body["ok"], code == 0)
        return code, body

    def test_a_listing_is_the_webapps_table_payload(self):
        self.say("note", "create", "--set", "text=um", "--json")
        code, body = self.say("note", "list", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(body["table"], payload.table_payload("note", False))
        self.assertEqual(len(body["table"]["records"]), 1)

    def test_a_view_carries_the_record(self):
        _, made = self.say("note", "create", "--set", "text=um", "--json")
        row = made["record"]
        code, body = self.say("--json", "note", "view", str(row["id"]))
        self.assertEqual(code, 0)
        self.assertEqual(body["record"], row)

    def test_a_write_says_the_message_and_the_row(self):
        code, body = self.say("note", "create", "--set", "text=um", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(body["message"])
        self.assertEqual(body["record"]["title"], "um")

    def test_a_usage_error_is_ok_false_with_code_2(self):
        code, body = self.say("nada-disso", "--json")
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])
        self.assertTrue(body["message"])

    def test_a_refusal_keeps_code_1(self):
        code, body = self.say("note", "view", "9999", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])

    def test_version_carries_the_version(self):
        code, body = self.say("--json", "version")
        self.assertEqual(code, 0)
        self.assertEqual(body["version"], __version__)

    def test_secret_scan_carries_the_findings_list(self):
        from at.core import scanner

        with mock.patch("at.ui.ask.scanner.scan") as scan:
            scan.return_value = scanner.Report(
                state=scanner.FOUND, tool="gitleaks 1",
                findings=(scanner.Finding("rule", "a.txt", 3, None),),
            )
            code, body = self.say("secret", "scan", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(
            body["findings"], [{"rule": "rule", "where": "a.txt", "line": 3, "commit": None}]
        )

    def test_the_flag_in_any_position_is_the_same_answer(self):
        a = self.say("--json", "help")[1]
        b = self.say("help", "--json")[1]
        self.assertEqual(a, b)
