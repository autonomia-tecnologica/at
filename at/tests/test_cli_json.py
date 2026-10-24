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
from at.core import boot, paths
from at.prose import payload
from at.ui import cli
from at.ui.cli import main
from at.ui.webapp import app as webapp
from at.ui.webapp import launch as webapp_launch
from at.ui.webapp import local


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

    # ------------------------------------------------------- the filtered list ---

    def test_a_filtered_listing_carries_only_the_rows_the_filter_kept(self):
        self.say("project", "create", "--set", "name=Alfa", "--json")
        self.say("project", "create", "--set", "name=Beta", "--json")
        self.say("task", "create", "--set", "text=de-alfa", "--set", "project=1", "--json")
        self.say("task", "create", "--set", "text=de-beta", "--set", "project=2", "--json")
        code, body = self.say("task", "list", "--project", "1", "--json")
        self.assertEqual(code, 0)
        whole = payload.table_payload("task", False)
        self.assertEqual(len(whole["records"]), 2)
        self.assertEqual([r["title"] for r in body["table"]["records"]], ["de-alfa"])
        self.assertEqual({k: v for k, v in body["table"].items() if k != "records"},
                         {k: v for k, v in whole.items() if k != "records"})

    def test_a_project_nobody_has_is_a_refusal_without_a_table(self):
        code, body = self.say("task", "list", "--project", "99", "--json")
        self.assertEqual(code, 1)
        self.assertNotIn("table", body)

    # ------------------------------------------------------------- no word ---

    def test_the_flag_alone_opens_the_panel_and_prints_no_json(self):
        out = io.StringIO()
        with mock.patch.object(local, "run", return_value=0) as opened, redirect_stdout(out):
            code = main(["--json"])
        self.assertEqual(code, 0)
        opened.assert_called_once_with()
        self.assertEqual(out.getvalue(), "")

    # -------------------------------------------------------------- webapp ---

    def test_webapp_says_it_started_at_once_and_nothing_at_the_end(self):
        real = io.StringIO()
        seen: list[str] = []

        class Server:
            server_address = ("127.0.0.1", 12399)

            def serve_forever(self):
                # Still serving: the object must already be out.
                seen.append(real.getvalue())
                raise KeyboardInterrupt

            def server_close(self):
                pass

        with mock.patch.object(webapp_launch, "make_server", return_value=Server()), \
             mock.patch.object(webapp_launch, "start_clock"), redirect_stdout(real):
            code = main(["webapp", "--no-caddy", "--port", "12399", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(seen[0].strip().splitlines()), 1)
        started = json.loads(seen[0])
        self.assertTrue(started["ok"])
        self.assertEqual(started["code"], 0)
        self.assertIn(":12399", started["url"])
        self.assertTrue(started["message"])
        self.assertEqual(real.getvalue(), seen[0])
        self.assertEqual(webapp.on_serving, [])

    def test_webapp_that_fails_says_so_in_one_object(self):
        code, body = self.say("webapp", "--port", "abc", "--json")
        self.assertEqual(code, 2)
        self.assertFalse(body["ok"])
        self.assertNotIn("url", body)

    # ------------------------------------------------------ the other words ---

    def readers(self, ask=None, secret=None):
        return mock.patch.object(cli, "_readers", return_value=(ask, secret))

    def test_backup_make_with_the_phrase_typed(self):
        dest = tempfile.TemporaryDirectory()
        self.addCleanup(dest.cleanup)
        with self.readers(secret=lambda q: "uma frase de passe bem longa para o teste"):
            code, body = self.say("backup", "make", dest.name, "--json")
        self.assertEqual(code, 0)
        self.assertIn(dest.name, body["message"])

    def test_backup_without_a_terminal_is_a_refusal(self):
        with self.readers():
            code, body = self.say("backup", "make", self.scratch.name, "--json")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])

    def test_convert_a_file(self):
        (paths.prose_dir() / "nota.md").write_text("# Título\n\nTexto.", encoding="utf-8")
        code, body = self.say("convert", "nota.md", "--to", "pdf", "--json")
        self.assertEqual(code, 0)
        self.assertIn("nota.pdf", body["message"])

    def test_convert_of_a_missing_file_is_refused_and_a_bad_shape_is_usage(self):
        self.assertEqual(self.say("convert", "nao.md", "--to", "pdf", "--json")[0], 1)
        self.assertEqual(self.say("convert", "nao.md", "--json")[0], 2)

    def test_license_summary(self):
        code, body = self.say("license", "--json")
        self.assertEqual(code, 0)
        self.assertIn("MIT", body["message"])

    def test_lang_shows_and_chooses(self):
        code, body = self.say("lang", "--json")
        self.assertEqual(code, 0)
        self.assertIn("pt_BR", body["message"])
        with self.readers(ask=lambda q: "n"):
            code, body = self.say("lang", "en_US", "--json")
        self.assertEqual(code, 0)
        self.assertIn("en_US", body["message"])
        self.assertEqual(self.say("lang", "es", "--json")[0], 2)

    def test_assist_that_cannot_preview_is_a_refusal(self):
        with self.readers(secret=lambda q: "uma frase de passe bem longa para o teste"):
            code, body = self.say("assist", "oi", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])
        self.assertEqual(self.say("assist", "--json")[0], 2)

    def test_setting_list_and_a_wrong_action(self):
        code, body = self.say("setting", "list", "--json")
        self.assertEqual(code, 0)
        self.assertIn("interpreter", body["message"])
        self.assertEqual(self.say("setting", "view", "--json")[0], 2)
        self.assertEqual(self.say("setting", "nada", "--json")[0], 2)

    def test_ask_a_listing_sentence(self):
        code, body = self.say("ask", "listar notas", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(body["message"])
        self.assertEqual(self.say("ask", "--json")[0], 2)

    def test_job_list_and_a_job_nobody_has(self):
        code, body = self.say("job", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(body["message"])
        code, body = self.say("job", "view", "1", "--json")
        self.assertEqual(code, 1)
        self.assertFalse(body["ok"])
