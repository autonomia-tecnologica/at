"""The WebApp server: its routes, its guards, and the doors of the look.

The server runs for real, on an ephemeral port, in a thread — a route tested by
calling its function is a route whose routing is not tested.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import io
import json
import os
import queue
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager, redirect_stdout
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    actions_audit,
    actors,
    assist,
    audit,
    boot,
    strongbox,
    jev,
    notifier,
    paths,
    permissions,
    projects,
    risk,
    secrets,
    settings,
    tables,
)
from at.data import schema, store
from at.encryption import vault
from at.services import caddy
from at.tests import POLL, drawn_gate
from at.ui.webapp import app as webapp
from at.ui.webapp import events, strongbox_links
from at.ui.webapp import keys as webapp_keys


def interface_fields(name: str, source_name: str = "store.ts") -> set[str]:
    """The fields a `lib/*.ts` interface declares — which is what the page reads
    from an entry of the payload.

    Parsed and not listed, so that adding a field to the interface is what makes
    the server owe it: a list written here by hand would be the same manual
    promise the code already failed to keep twice.
    """
    source = (webapp.HERE / "src" / "lib" / source_name).read_text(encoding="utf-8")
    body = re.search(rf"export interface {name} \{{(.*?)\n\}}", source, re.S)
    assert body, f"the interface {name} is not in store.ts"
    return set(re.findall(r"^\s*(\w+)\??:", body.group(1), re.M))


def bundle():
    """This process, made into the FROZEN artifact for the length of a `with`.

    `sys.frozen` is the one attribute the frozen loader sets, so patching it is
    how a test is the bundle without building one — and it is the artifact that
    answers the WebApp's entrance (`paths.source`), not a flag a test could set
    any other way.
    """
    return mock.patch.object(sys, "frozen", True, create=True)


class ServerCase(unittest.TestCase):
    # What `make_server` is handed, and it is here so a class that wants a
    # DIFFERENT server says which one without rebuilding the harness: the server
    # a run from the source tree builds is this one with `asks=False`
    # (`TheDevServer`), and everything else about the folder is untouched.
    server_args: dict = {}

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.scratch.name), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        # A Chave Principal é global do PROCESSO (`keys._main`), e um teste
        # anterior que subiu um webapp de verdade a deixa de pé: `keys.boot` lê
        # a Chave do arquivo da MÁQUINA (`~/.config/at/AT_MAIN_KEY`) quando ele
        # existe, então o teste que rodou antes do `test_webapp` deixa a Chave
        # da instância vazando para cá — e o `/api/ask`, que cai em
        # `keys.main_key()`, passa a achar que o pedido trouxe uma Chave, o que
        # desliga o hint do assist por um motivo que este teste não escolheu.
        # Zera na entrada e devolve na saída, para o teste que QUER uma Chave
        # continuar podendo pôr a sua (a classe que a liga o faz por cima).
        held_main = webapp_keys.main_key()
        webapp_keys.keep_main_key(None)
        self.addCleanup(webapp_keys.keep_main_key, held_main)
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        with redirect_stdout(io.StringIO()):
            tables.create("task", {"text": "primeira"})

        self.server = webapp.make_server(0, **self.server_args)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": POLL}, daemon=True,
        )
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    # -- the two doors, so a test reads as what it does ---------------------

    def get(self, path: str,
            headers: dict | None = None) -> tuple[int, object, bytes]:
        """A refusal is an answer too: it comes back with its status, never as
        an exception a test has to catch to say what it expected."""
        request = urllib.request.Request(self.url(path), headers=headers or {})
        try:
            with urllib.request.urlopen(request) as answer:
                return answer.status, answer.headers, answer.read()
        except urllib.error.HTTPError as error:
            body = error.read()
            error.close()
            return error.code, error.headers, body

    def post(self, path: str, payload: object, headers: dict | None = None):
        status, _, answer = self.post_full(path, payload, headers)
        return status, answer

    def post_full(self, path: str, payload: object, headers: dict | None = None):
        """The write AND its answer headers — which is what a session opens by.

        It is a door of its own because `post` is read as the pair a caller
        wants; whoever needs the `Set-Cookie` asks here, and nobody has to
        unpick a tuple that is only sometimes a triple.
        """
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url(path), data=body, method="POST",
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(request) as answer:
                return answer.status, answer.headers, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            headers_out, raw = error.headers, error.read()
            error.close()
            return error.code, headers_out, json.loads(raw)

    def status(self, path: str, method: str = "GET", headers: dict | None = None) -> int:
        request = urllib.request.Request(self.url(path), method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request) as answer:
                return answer.status
        except urllib.error.HTTPError as error:
            error.close()
            return error.code

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"


class TheState(ServerCase):
    def test_it_says_whether_the_interpreter_is_on(self):
        # The page draws the box, the balloon and the chat off this one answer:
        # turning the interpreter off has to reach the screen, and the screen owns
        # no rule that could guess it.
        _, _, body = self.get("/api/state")
        self.assertIs(json.loads(body)["interpreter"], True)

    def test_the_switch_of_the_core_is_what_the_page_reads(self):
        # With it off there is no box, no balloon and no chat — and the page learns
        # it from here, because the page owns no rule that could guess it.
        settings.save({**settings.load(), "interpreter": False})
        _, _, body = self.get("/api/state")
        self.assertIs(json.loads(body)["interpreter"], False)

    def test_it_carries_the_rulers_numbers(self):
        _, _, body = self.get("/api/state")
        risk = json.loads(body)["risk"]
        self.assertEqual(risk["threshold"], 0.5)  # §4's default, for a folder that never chose
        # The marks are the ones the CATALOGUE declares, one per entry and in its
        # order (item 11): the page draws the list it was handed and sorts nothing.
        self.assertEqual(
            [mark["key"] for mark in risk["marks"]], permissions.all_permissions()
        )
        self.assertEqual(
            next(mark for mark in risk["marks"] if mark["key"] == "role:edit")["risk"], 0.8
        )

    def test_the_marks_carry_the_number_the_folder_adjusted(self):
        # §5's per-action adjustment reaches the ruler through the ONE number the
        # engine measures with: a mark is what its entry is measured at, so a
        # folder that lifts `task:delete` draws the mark over the line and the
        # filter holds the demand at the same spot — with no line changing in the
        # page, because the page draws what it is handed.
        settings.save({**settings.load(), risk.BY_ACTION: {"task:delete": 0.9}})
        _, _, body = self.get("/api/state")
        marks = {mark["key"]: mark["risk"] for mark in json.loads(body)["risk"]["marks"]}
        self.assertEqual(marks["task:delete"], 0.9)
        self.assertTrue(risk.waits(marks["task:delete"]))
        # And an entry the folder did not write keeps the catalogue's number.
        self.assertEqual(marks["setting:edit"], permissions.risk("setting:edit"))
        self.assertEqual(marks["task:create"], permissions.risk("task:create"))

    def test_it_names_the_declared_tables_with_their_counts(self):
        _, _, body = self.get("/api/state")
        state = json.loads(body)
        keys = [table["key"] for table in state["tables"]]
        # The order is the schema's, and the system tables arrive with the
        # product: `actor` and `role` are declared beside the three that carry
        # the daily work (§4), and `secret` — what AT uses and nobody reads —,
        # `audit` — the log of acts — and `job` — the demand that waits — close
        # the list with them.
        self.assertEqual(
            keys,
            ["task", "project", "reminder", "actor", "role", "secret", "audit", "job"],
        )
        self.assertEqual(next(t for t in state["tables"] if t["key"] == "task")["count"], 1)

    def test_it_carries_the_brand(self):
        # The panel's `#brand` and the entrance's heading are the same word, and
        # it was missing from this list for as long as the list has existed: the
        # one screen that drew it was drawing nothing, and nothing said so.
        _, _, body = self.get("/api/state")
        self.assertEqual(json.loads(body)["labels"]["brand"]["pt_BR"], "AT")

    def test_it_carries_the_theme_registry_and_the_language(self):
        _, _, body = self.get("/api/state")
        state = json.loads(body)
        self.assertEqual(state["lang"], "pt_BR")
        self.assertTrue(any(theme["id"] == "at" for theme in state["themes"]))
        self.assertTrue(all(set(theme["sides"]) <= {"light", "dark"} and theme["sides"]
                             for theme in state["themes"]))
        at_row = next(theme for theme in state["themes"] if theme["id"] == "at")
        self.assertEqual(sorted(at_row["sides"]), ["dark", "light"])


class TheTablePayload(ServerCase):
    def test_it_carries_every_declared_field(self):
        _, _, body = self.get("/api/table/task")
        payload = json.loads(body)
        names = [field["name"] for field in payload["fields"]]
        self.assertEqual(names[0], "id")
        self.assertIn("status", names)
        self.assertIn("text", names)

    def test_a_field_carries_its_label_in_every_language(self):
        _, _, body = self.get("/api/table/task")
        status = next(f for f in json.loads(body)["fields"] if f["name"] == "status")
        self.assertEqual(status["labels"], {"pt_BR": "Status", "en_US": "Status"})
        self.assertTrue(status["editable"])
        self.assertTrue(status["filterable"])

    def test_it_renders_a_record_in_the_active_language(self):
        _, _, body = self.get("/api/table/task")
        record = json.loads(body)["records"][0]
        by_name = {field["name"]: field for field in record["fields"]}
        self.assertEqual(record["shown_id"], "TASK-1")
        self.assertEqual(by_name["status"]["value"], "A fazer")
        self.assertEqual(by_name["status"]["raw"], "todo")

    def test_a_reference_resolves_to_the_title_it_names(self):
        with redirect_stdout(io.StringIO()):
            project = tables.create("project", {"name": "Autonomia"})
            tables.create("task", {"text": "ligada", "project": str(project["id"])})
        _, _, body = self.get("/api/table/task")
        record = json.loads(body)["records"][1]
        field = next(f for f in record["fields"] if f["name"] == "project")
        self.assertEqual(field["value"], "Autonomia")
        self.assertEqual(field["refs"], [{"key": "project", "id": 1,
                                          "title": "Autonomia", "shown": "Autonomia"}])

    def test_an_unknown_table_is_answered_not_crashed(self):
        self.assertEqual(self.status("/api/table/no-such-table"), 404)


class TheHashedField(ServerCase):
    """The field whose value never reaches the page (§4, item 8).

    The record builder is where the leak was: it handed `row.get(name)` to the
    page as `raw`, so the stored value of every field travelled to the browser.
    With the field hashed, the engine refuses to hand it over — the cell draws
    the mask, and `raw` carries nothing.
    """

    SECRET = "segredo-do-ator"

    # The product ships no hashed field yet — the `actor` table is item 9 — so
    # the page is asked about a table of the instance's own.
    KEEPER = {
        "id": "keeper",
        "order": 90,
        "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
        "store": "data/keepers.jsonl",
        "primary": "name",
        "columns": ["name", "credential"],
        "fields": {
            "id": {"label": "table.field.id"},
            "name": {"label": "table.task.field.text"},
            "credential": {"label": "table.task.field.desc", "type": "hashed"},
        },
    }

    def setUp(self):
        super().setUp()
        where = paths.data_dir() / schema.SCHEMA_DIR / "keeper.json"
        where.write_text(
            json.dumps(self.KEEPER, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        schema.reset()
        with redirect_stdout(io.StringIO()):
            tables.create("keeper", {"name": "portão", "credential": self.SECRET})

    def tearDown(self):
        # The declarations are cached per process and this folder is gone: a
        # cache left behind would hand the next test a table that is not there.
        schema.reset()
        super().tearDown()

    def cell(self, name: str) -> dict:
        _, _, body = self.get("/api/table/keeper")
        record = json.loads(body)["records"][0]
        return next(field for field in record["fields"] if field["name"] == name)

    def test_the_cell_shows_the_mask(self):
        self.assertEqual(self.cell("credential")["value"], i18n.tr("table.word.hashed"))

    def test_the_payload_carries_no_stored_value_for_the_field(self):
        # Neither the credential nor the derivation it became: the answer is
        # read as bytes, because that is what leaves the process.
        _, _, body = self.get("/api/table/keeper")
        self.assertNotIn(self.SECRET.encode("utf-8"), body)
        self.assertNotIn(b"argon2id", body)
        self.assertIsNone(self.cell("credential")["raw"])

    def test_every_other_field_still_carries_what_is_stored(self):
        self.assertEqual(self.cell("name")["raw"], "portão")

    def test_a_declaration_the_folder_carries_is_answered_not_crashed(self):
        # The refusal is the engine's and it travels in the active language: a
        # route that died instead would leave the page with nothing to draw AND
        # nothing to say — the same blank screen the engine refuses to trade a
        # loud answer for.
        where = paths.data_dir() / schema.SCHEMA_DIR / "keeper.json"
        declared = json.loads(where.read_text(encoding="utf-8"))
        declared["fields"]["credential"]["method"] = "scrypt"
        where.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()
        expected = i18n.tr(
            "table.error.hashed_key",
            field=i18n.tr("table.task.field.desc"),
            named="method",
        )
        for path in ("/api/table/keeper", "/api/state"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(body)["error"], expected)


class TheSealedField(ServerCase):
    """The field whose value never reaches the page either (§4, item 14).

    The product ships this one — `secret` is a system table — so the page is
    asked about the table itself, with no declaration of the instance's own in
    the way: the envelope stays in the folder, the cell draws the mask, and
    `raw` carries nothing.
    """

    PHRASE = "mariazinha comeu todo o pudim"
    VALUE = "credencial-de-exemplo"

    def setUp(self):
        super().setUp()
        self.row = secrets.seal("credencial", "notifier", self.VALUE, self.PHRASE)

    def cell(self, name: str) -> dict:
        _, _, body = self.get("/api/table/secret")
        record = json.loads(body)["records"][0]
        return next(field for field in record["fields"] if field["name"] == name)

    def test_the_cell_shows_the_mask(self):
        self.assertEqual(self.cell("value")["value"], i18n.tr("table.word.sealed"))

    def test_the_payload_carries_neither_the_value_nor_the_envelope(self):
        # The answer is read as bytes, because that is what leaves the process —
        # and the phrase that opens neither travels nor is anywhere in it.
        _, _, body = self.get("/api/table/secret")
        self.assertNotIn(self.VALUE.encode("utf-8"), body)
        self.assertNotIn(self.row["value"].encode("utf-8"), body)
        self.assertNotIn(self.PHRASE.encode("utf-8"), body)
        self.assertIsNone(self.cell("value")["raw"])

    def test_every_other_field_still_carries_what_is_stored(self):
        self.assertEqual(self.cell("service")["raw"], "notifier")


class TheLook(ServerCase):
    def test_base_css_is_served(self):
        status, headers, body = self.get("/base.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", headers["Content-Type"])
        self.assertEqual(body, (webapp.ASSETS / "base.css").read_bytes())

    def test_a_theme_is_resolved_by_lookup(self):
        _, _, body = self.get("/theme.css?theme=at")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / "at.css").read_text(encoding="utf-8"))

    def test_the_dark_side_is_a_second_file(self):
        _, _, body = self.get("/theme.css?theme=at&dark")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / "at-dark.css").read_text(encoding="utf-8"))

    def test_a_theme_with_one_side_answers_it_either_way(self):
        # `gothic` kept only its dark file (2026-10-04) — asking for the
        # light side of a theme that does not have one answers the side
        # that exists, never a 404.
        dark_css = (webapp.THEMES / "gothic-dark.css").read_text(encoding="utf-8")
        _, _, light_request = self.get("/theme.css?theme=gothic")
        _, _, dark_request = self.get("/theme.css?theme=gothic&dark")
        self.assertEqual(light_request.decode("utf-8"), dark_css)
        self.assertEqual(dark_request.decode("utf-8"), dark_css)

    def test_an_id_that_names_no_theme_falls_back_to_the_default(self):
        _, _, body = self.get("/theme.css?theme=../../etc/passwd")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / f"{webapp.DEFAULT_THEME}.css").read_text(encoding="utf-8"))

    def test_the_document_carries_the_policy(self):
        # 500 is what a checkout without a build answers, and 200 what a built
        # one does — the policy travels on both, because it is the only route
        # that runs anything.
        status, headers, _ = self.get("/")
        self.assertIn(status, (200, 500))
        self.assertEqual(headers["Content-Security-Policy"], webapp.CSP)

    @unittest.skipUnless((webapp.UI_DIR / "index.html").is_file(),
                         "the page is not built: npm ci && npm run build")
    def test_the_build_keeps_the_policy_and_the_look(self):
        # The build is where the policy is easiest to break in silence: an inline
        # `<script>` or a `data:` asset would simply never run. And the LOOK has
        # to come out of it — Vite removes a stylesheet it cannot resolve on
        # disk, which is how the first build shipped without `base.css`.
        built = (webapp.UI_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/theme.css"', built)
        self.assertIn('href="/base.css"', built)
        self.assertIn('src="/js/boot.js"', built)
        self.assertNotIn("data:", built)
        index = (webapp.UI_ASSETS / built.split("/assets/")[1].split('"')[0])
        self.assertTrue(index.is_file())
        script = (webapp.UI_ASSETS / built.split('src="/assets/')[1].split('"')[0])
        self.assertNotIn("</script>", script.read_text(encoding="utf-8"))

    def test_boot_js_is_served(self):
        status, headers, body = self.get("/js/boot.js")
        self.assertEqual(status, 200)
        self.assertIn("text/javascript", headers["Content-Type"])
        self.assertIn(b"at.theme", body)


class TheAddress(ServerCase):
    """A view has a path — `/task`, `/task/3` — and the page owns the vocabulary."""

    def test_a_view_is_served_at_its_path(self):
        # The page knows which views exist; the server would keep a second copy of
        # that list to refuse anything here, and the second copy is the one that
        # drifts. So the address answers with the page, and the page decides.
        for path in ("/task", "/task/3", "/project/2", "/file/kb/note.md", "/settings"):
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers["Content-Type"])
                self.assertEqual(body, self.get("/")[2])

    def test_the_path_carries_the_policy_like_the_root_does(self):
        status, headers, _ = self.get("/task")
        self.assertIn(status, (200, 500))
        self.assertEqual(headers["Content-Security-Policy"], webapp.CSP)

    def test_the_server_keeps_its_own_answers(self):
        # What IS the server's own keeps its own answer: the API refuses a table
        # nobody declared, and a font nobody pinned is not served.
        self.assertEqual(self.status("/api/table/no-such-table"), 404)
        self.assertEqual(self.status("/vendor/no-such-font"), 404)

    def test_the_query_form_still_answers(self):
        # The link somebody saved before the path existed is not a link to break.
        status, _, body = self.get("/?view=task")
        self.assertEqual(status, 200)
        self.assertEqual(body, self.get("/")[2])


class TheDoors(ServerCase):
    """A name that is a path is refused before the disk is touched."""

    def test_an_icon_name_that_escapes_is_refused(self):
        for name in ("../app.py", "a/../code.svg", "..", ".hidden.svg", "", "code.svg/"):
            self.assertIsNone(webapp.served(webapp.ICONS, name), name)

    def test_an_icon_that_exists_is_served(self):
        status, headers, _ = self.get("/icons/at.svg")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml")

    def test_a_png_icon_is_served_for_the_manifest_install(self):
        # The manifest's own icons are PNG (`manifest.webmanifest`) — the shape
        # Android reads to offer "Install app", and a shape the server serves
        # through the same `/icons/` door as the SVG look.
        status, headers, _ = self.get("/icons/icon-192.png")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/png")

    def test_a_hosted_font_is_served_with_its_revision(self):
        status, headers, body = self.get("/vendor/font-nunito-sans-400")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "font/woff2")
        self.assertEqual(headers["X-Hosted"], "5.3.0")
        manifest = json.loads((webapp.VENDOR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(body).hexdigest(),
                         manifest["files"]["font-nunito-sans-400"]["sha256"])

    def test_a_hosted_renderer_is_served_as_code_with_its_revision(self):
        # The markdown renderer travels the same door as the typefaces, and its
        # extension is the one `upstream` carries — so the content type is the
        # server's own `_CONTENT_TYPES`, not the key's business.
        status, headers, body = self.get("/vendor/marked")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/javascript; charset=utf-8")
        self.assertEqual(headers["X-Hosted"], "18.0.14")
        manifest = json.loads((webapp.VENDOR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(body).hexdigest(),
                         manifest["files"]["marked"]["sha256"])

    def test_a_hosted_key_nobody_pinned_is_refused(self):
        self.assertEqual(self.status("/vendor/no-such-font"), 404)


class TheWrites(ServerCase):
    def test_a_create_through_the_page_reaches_the_store(self):
        status, answer = self.post("/api/table/task", {
            "action": "create", "set": {"text": "vinda do navegador", "priority": "high"},
        })
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["shown_id"], "TASK-2")
        self.assertEqual(tables.find("task", 2)["text"], "vinda do navegador")

    def test_an_edit_through_the_page_reaches_the_store(self):
        status, answer = self.post("/api/table/task",
                                   {"action": "edit", "id": 1, "set": {"status": "done"}})
        self.assertEqual(status, 200)
        by_name = {field["name"]: field for field in answer["record"]["fields"]}
        self.assertEqual(by_name["status"]["raw"], "done")

    def test_a_refusal_from_the_engine_is_answered_not_crashed(self):
        # A reminder declares `text` and `at` as required; an empty one is the
        # engine refusing, and the page must hear the reason.
        status, answer = self.post("/api/table/reminder", {"action": "create", "set": {}})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)

    def test_a_write_from_another_site_is_refused(self):
        status, _ = self.post("/api/table/task",
                              {"action": "create", "set": {"text": "x"}},
                              headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)

    def test_a_write_from_this_origin_is_accepted(self):
        status, _ = self.post("/api/table/task",
                              {"action": "create", "set": {"text": "x"}},
                              headers={"Origin": self.url("")})
        self.assertEqual(status, 200)

    def test_a_write_that_is_not_json_is_refused(self):
        request = urllib.request.Request(
            self.url("/api/table/task"), data=b"x", method="POST",
            headers={"Content-Type": "text/plain"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 415)

    def test_other_verbs_are_refused_out_loud(self):
        for method in ("PUT", "PATCH", "DELETE"):
            self.assertEqual(self.status("/api/table/task", method=method), 405, method)


class TheRowClosingAndDeletion(ServerCase):
    """TASK-122, fatia 3/7: `cancel` and `delete` through the SAME route the
    create and the edit already walk (`TABLE_WRITES` grown, no new route) —
    the row menu's two new doors."""

    def test_a_cancel_through_the_page_closes_with_a_reason(self):
        status, answer = self.post(
            "/api/table/task", {"action": "cancel", "id": 1, "set": {"reason": "não cabe mais"}},
        )
        self.assertEqual(status, 200)
        by_name = {field["name"]: field for field in answer["record"]["fields"]}
        self.assertEqual(by_name["status"]["raw"], "cancelled")

    def test_a_cancel_with_no_reason_is_refused_when_the_table_requires_one(self):
        status, answer = self.post("/api/table/task", {"action": "cancel", "id": 1, "set": {}})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)

    def test_a_delete_through_the_page_reaches_the_store(self):
        status, _ = self.post("/api/table/task", {"action": "delete", "id": 1})
        self.assertEqual(status, 200)
        self.assertEqual(tables.rows("task"), [])

    def test_a_delete_refused_by_a_referrer_is_answered_not_crashed(self):
        with redirect_stdout(io.StringIO()):
            parent = tables.create("project", {"name": "Autonomia", "status": "active"})
            tables.create(
                "project",
                {"name": "Autonomia — subprojeto", "status": "active",
                 "parent": str(store.number_of(parent))},
            )
        status, answer = self.post(
            "/api/table/project", {"action": "delete", "id": store.number_of(parent)},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", answer)
        self.assertIsNotNone(tables.find("project", store.number_of(parent)))

    def test_the_offline_sync_route_still_refuses_a_delete_entry(self):
        # `offline.reconcile` has no branch for it (TASK-162's own scope is
        # `create`/`edit`) — the row menu's two new doors write ONLINE, never
        # through the fila, and this route must keep refusing the word it
        # cannot reconcile instead of silently folding it into an edit.
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "delete", "id": 1, "values": {}, "edited_at": "2026-01-01T00:00:00.000Z"},
        ]})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)
        self.assertEqual(len(tables.rows("task")), 1)


class TheOfflineSync(ServerCase):
    """The fila the Service Worker built without a network, reconciled in ONE
    round trip (TASK-162, fatia 2/2) — `at.core.offline.reconcile` (fatia 1),
    walked from a route instead of the `cli`'s one-row-at-a-time door.
    """

    def test_a_queued_create_reaches_the_store(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "create", "values": {"text": "no avião"},
             "edited_at": "2026-01-01T10:00:00.000Z", "local_id": "tmp-1"},
        ]})
        self.assertEqual(status, 200)
        [res] = answer["resolutions"]
        self.assertTrue(res["applied"])
        self.assertEqual(res["local_id"], "tmp-1")
        self.assertEqual(res["record"]["shown_id"], "TASK-2")
        self.assertEqual(tables.find("task", 2)["text"], "no avião")

    def test_a_queued_edit_newer_than_the_server_wins(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "edit", "id": 1, "values": {"status": "done"},
             "edited_at": "2030-01-01T00:00:00.000Z"},
        ]})
        self.assertEqual(status, 200)
        [res] = answer["resolutions"]
        self.assertTrue(res["applied"])
        by_name = {f["name"]: f for f in res["record"]["fields"]}
        self.assertEqual(by_name["status"]["raw"], "done")
        self.assertEqual(tables.find("task", 1)["status"], "done")

    def test_a_queued_edit_older_than_the_server_loses_silently(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "edit", "id": 1, "values": {"status": "done"},
             "edited_at": "2000-01-01T00:00:00.000Z"},
        ]})
        self.assertEqual(status, 200)
        [res] = answer["resolutions"]
        self.assertFalse(res["applied"])
        by_name = {f["name"]: f for f in res["record"]["fields"]}
        self.assertEqual(by_name["status"]["raw"], "todo")
        self.assertEqual(tables.find("task", 1)["status"], "todo")

    def test_an_edit_pointing_at_a_local_id_of_the_same_batch_lands_on_it(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "create", "values": {"text": "nova"},
             "edited_at": "2026-01-01T10:00:00.000Z", "local_id": "tmp-1"},
            {"action": "edit", "id": "tmp-1", "values": {"status": "done"},
             "edited_at": "2026-01-01T10:00:01.000Z"},
        ]})
        self.assertEqual(status, 200)
        second = answer["resolutions"][1]
        self.assertTrue(second["applied"])
        by_name = {f["name"]: f for f in second["record"]["fields"]}
        self.assertEqual(by_name["status"]["raw"], "done")

    def test_an_unknown_action_is_refused_and_writes_nothing(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "delete", "id": 1, "values": {}, "edited_at": "x"},
        ]})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)
        self.assertEqual(len(tables.rows("task")), 1)

    def test_entries_that_are_not_a_list_are_refused(self):
        status, answer = self.post("/api/offline/sync", {"entries": "not-a-list"})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)

    def test_a_bad_instant_is_answered_not_crashed(self):
        status, answer = self.post("/api/offline/sync", {"entries": [
            {"action": "edit", "id": 1, "values": {"status": "done"},
             "edited_at": "not-a-date"},
        ]})
        self.assertEqual(status, 400)
        self.assertIn("error", answer)


class TheStateContract(ServerCase):
    """Every key the page reads from `/api/state` is a key the server sends.

    The two sides are different languages, and a name that drifts between them is
    INVISIBLE: the page reads `undefined`, a part of the panel comes out empty, and
    nothing anywhere says why. It happened — the server sent `tables` and the page
    asked for `kinds`, and the sidebar listed no table at all.
    """

    def test_every_key_the_page_reads_is_a_key_the_server_sends(self):
        source = (webapp.HERE / "src" / "lib" / "store.ts").read_text(encoding="utf-8")
        reads = set(re.findall(r"state\.([a-zA-Z_]+)", source))
        self.assertTrue(reads, "the page reads no key at all — did applyState move?")
        self.assertEqual(sorted(reads - set(webapp.state_payload())), [])

    def test_the_page_starts_with_no_table_and_the_server_hands_it_some(self):
        # The other half: the keys match AND the list is not empty, because a
        # payload that is present and empty leaves the panel just as blank.
        self.assertTrue(webapp.state_payload()["tables"])

    def test_every_entry_carries_what_the_page_interface_declares(self):
        # The same defect, one floor down: it is not enough for the top-level key
        # to match — the ENTRY has to carry the names the page reads. It happened
        # twice, the second time as `name` against `label`: the sidebar listed a
        # count with no word beside it.
        state = webapp.state_payload()
        for interface, entries in (
            ("Kind", state["tables"]),
            ("ThemeRow", state["themes"]),
            ("Risk", [state["risk"]]),
        ):
            self.assertTrue(entries, interface)
            declared = interface_fields(interface)
            for entry in entries:
                self.assertEqual(sorted(declared - set(entry)), [], f"{interface}: {entry}")


class ThePageWords(ServerCase):
    """Every word the page asks for by name is a word the server hands over.

    It is the same defect the state contract catches one floor down, and it is
    INVISIBLE for the same reason: the page writes `word("people")`, the server
    never sends `people`, and the line comes out empty with nothing saying why.
    Ask the page what it asks for; the catalog is what has to answer.
    """

    def asked(self) -> set[str]:
        found: set[str] = set()
        for source in (webapp.HERE / "src").rglob("*"):
            if source.suffix not in (".ts", ".vue"):
                continue
            found |= set(
                re.findall(r'word\(\s*"([a-z0-9_]+)"\s*\)', source.read_text(encoding="utf-8"))
            )
        return found

    def test_the_page_asks_for_at_least_one_word(self):
        # The gate below is only worth having if it has something to check.
        self.assertTrue(self.asked())

    def test_every_word_the_page_reads_is_one_the_server_sends(self):
        self.assertEqual(sorted(self.asked() - set(webapp.PAGE_WORDS)), [])


class TheProjectBranch(ServerCase):
    """The tree of the panel, and the page a project opens."""

    def setUp(self):
        super().setUp()
        with redirect_stdout(io.StringIO()):
            tables.create("project", {"name": "Autonomia", "status": "active"})
            tables.create("project", {"name": "Site", "status": "active", "parent": "1"})
            # The task that already exists from the base case names no project.
            tables.create("task", {"text": "ligada", "project": "1"})
            tables.create("task", {"text": "do site", "project": "2"})

    def test_the_tree_carries_a_line_per_project_and_the_orphans_last(self):
        _, _, body = self.get("/api/projects")
        rows = json.loads(body)["tree"]
        self.assertEqual([row["title"] for row in rows],
                         ["Autonomia", "Site", "Sem projeto"])
        self.assertIsNone(rows[0]["parent"])
        self.assertEqual(rows[1]["parent"], 1)
        self.assertTrue(rows[-1].get("orphans"))

    def test_a_line_counts_the_tasks_that_name_that_project_directly(self):
        # Not the subtree: the number says how much of the day is under that
        # name, and what the subtree holds is what the PAGE is for.
        _, _, body = self.get("/api/projects")
        rows = {row["title"]: row["tasks"] for row in json.loads(body)["tree"]}
        self.assertEqual(rows["Autonomia"], 1)
        self.assertEqual(rows["Site"], 1)

    def test_a_project_the_listing_does_not_show_does_not_claim_its_tasks(self):
        with redirect_stdout(io.StringIO()):
            done = tables.create("project", {"name": "Encerrado", "status": "done"})
            tables.create("task", {"text": "de um projeto fechado", "project": str(done["id"])})
        _, _, body = self.get("/api/projects")
        titles = [row["title"] for row in json.loads(body)["tree"]]
        self.assertNotIn("Encerrado", titles)
        # And the task it would have claimed falls to the "no project" node —
        # its project is not on screen either, so nobody claims it.
        texts = [row.get("text") for row in projects.orphans()]
        self.assertEqual(len(texts), 2)
        self.assertIn("de um projeto fechado", texts)

    def test_a_project_page_carries_the_whole_subtree(self):
        _, _, body = self.get("/api/project/1")
        payload = json.loads(body)
        self.assertEqual(payload["title"], "Autonomia")
        self.assertEqual([child["title"] for child in payload["children"]], ["Site"])
        # The subtree's tasks, each row saying which subproject it came from.
        by_id = {row["shown_id"]: {f["name"]: f["value"] for f in row["fields"]}
                 for row in payload["records"]}
        self.assertEqual(by_id["TASK-2"]["project"], "Autonomia")  # its own project
        self.assertEqual(by_id["TASK-3"]["project"], "Site")       # the subproject

    def test_the_project_page_hides_the_column_every_row_repeats(self):
        _, _, body = self.get("/api/project/1")
        project = next(f for f in json.loads(body)["fields"] if f["name"] == "project")
        self.assertIn("project", project["hide"])

    def test_the_page_carries_the_item_own_record_and_its_schema(self):
        # The project's OWN pair, apart from the `fields`/`records` the page
        # draws: it is what puts the body of an item on the page it belongs to.
        with redirect_stdout(io.StringIO()):
            tables.edit("project", 1, {"desc": "## O porquê\n\no corpo do item"})
        _, _, body = self.get("/api/project/1")
        payload = json.loads(body)
        fields = {field["name"]: field for field in payload["project"]["record"]["fields"]}
        self.assertEqual(fields["desc"]["value"], "## O porquê\n\no corpo do item")
        self.assertEqual(fields["desc"]["type"], "markdown")
        self.assertIn("desc", [field["name"] for field in payload["project"]["fields"]])
        # And the pair the page's TABLE reads is still the task's.
        self.assertIn("text", [field["name"] for field in payload["fields"]])

    def test_the_subprojects_come_in_the_order_the_table_declares(self):
        with redirect_stdout(io.StringIO()):
            tables.create("project", {"name": "Depois", "parent": "1", "priority": "low"})
            tables.create("project", {"name": "Antes", "parent": "1", "priority": "critical"})
        _, _, body = self.get("/api/project/1")
        children = [child["title"] for child in json.loads(body)["children"]]
        self.assertEqual(children, ["Antes", "Site", "Depois"])

    def test_an_unknown_project_is_not_a_crash(self):
        self.assertEqual(self.status("/api/project/999"), 404)

    def test_the_orphans_page_lists_exactly_them(self):
        _, _, body = self.get("/api/orphans")
        payload = json.loads(body)
        self.assertEqual([row["shown_id"] for row in payload["records"]], ["TASK-1"])


class TheProseDoors(ServerCase):
    def setUp(self):
        super().setUp()
        (paths.prose_dir()).mkdir(exist_ok=True)
        (paths.prose_dir() / "nota.md").write_text("# oi\n", encoding="utf-8")

    def test_the_tree_lists_what_the_folder_holds(self):
        _, _, body = self.get("/api/tree")
        listing = json.loads(body)
        self.assertEqual(listing["root"], "")
        # The folder is born with a welcome note, so it is never empty.
        self.assertIn("nota.md", [f["path"] for f in listing["files"]])

    def test_a_file_is_read_with_its_revision(self):
        _, _, body = self.get("/api/file?path=nota.md")
        payload = json.loads(body)
        self.assertEqual(payload["text"], "# oi\n")
        self.assertEqual(payload["bucket"], "text")
        self.assertTrue(payload["writable"])

    def test_a_path_that_escapes_is_refused(self):
        self.assertEqual(self.status("/api/file?path=../pyproject.toml"), 404)
        self.assertEqual(self.status("/api/file?path=app/settings.json"), 404)

    def test_an_image_answers_with_its_kind_and_no_refusal_reason(self):
        # PNG bytes are binary (a NUL early on) — the extension is what tells
        # `prose.read` it opens anyway (TASK-167).
        (paths.prose_dir() / "foto.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 20)
        _, _, body = self.get("/api/file?path=foto.png")
        payload = json.loads(body)
        self.assertEqual(payload["kind"], "image")
        self.assertEqual(payload["bucket"], "image")
        self.assertFalse(payload["writable"])
        self.assertIsNone(payload["reason"])

    def test_a_binary_neither_text_nor_image_carries_the_renamed_reason(self):
        (paths.prose_dir() / "bin.dat").write_bytes(b"a\0b")
        _, _, body = self.get("/api/file?path=bin.dat")
        payload = json.loads(body)
        self.assertEqual(payload["reason"], i18n.tr("prose.not_supported"))

    def test_the_bytes_route_serves_the_raw_file_with_its_content_type(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\0" * 20
        (paths.prose_dir() / "foto.png").write_bytes(data)
        status, headers, body = self.get("/api/file/bytes?path=foto.png")
        self.assertEqual(status, 200)
        self.assertEqual(body, data)
        self.assertEqual(headers["Content-Type"], "image/png")

    def test_the_bytes_route_refuses_a_path_that_escapes(self):
        self.assertEqual(self.status("/api/file/bytes?path=../pyproject.toml"), 404)

    def test_the_bytes_route_refuses_a_file_that_does_not_exist(self):
        self.assertEqual(self.status("/api/file/bytes?path=nao-existe.png"), 404)

    def test_an_svg_is_served_sandboxed_and_the_other_images_are_not(self):
        # An SVG can carry a `<script>`. Drawn as an `<img>` it never runs,
        # but opened straight from this URL the SVG is a DOCUMENT and it
        # would run in AT's own origin — the header takes that away and
        # leaves the `<img>` alone (TASK-167).
        (paths.prose_dir() / "marca.svg").write_bytes(
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>'
        )
        status, headers, _ = self.get("/api/file/bytes?path=marca.svg")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml")
        self.assertEqual(headers["Content-Security-Policy"], "sandbox")
        (paths.prose_dir() / "foto.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        _, headers, _ = self.get("/api/file/bytes?path=foto.png")
        self.assertNotIn("Content-Security-Policy", headers)

    def test_the_content_type_folds_the_suffix_the_way_the_list_does(self):
        # `prose.bucket` reads `FOTO.PNG` as an image (`suffix.lower()`); a
        # route that served it as `application/octet-stream` would disagree
        # with the list the page drew the row from (TASK-167).
        (paths.prose_dir() / "FOTO.PNG").write_bytes(b"\x89PNG\r\n\x1a\n")
        _, headers, _ = self.get("/api/file/bytes?path=FOTO.PNG")
        self.assertEqual(headers["Content-Type"], "image/png")

    def test_a_write_with_a_stale_revision_is_refused_with_the_new_one(self):
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        status, answer = self.post("/api/file", {"path": "nota.md", "text": "x\n", "base": "velha"})
        self.assertEqual(status, 409)
        self.assertEqual(answer["rev"], rev)
        self.assertEqual((paths.prose_dir() / "nota.md").read_text(encoding="utf-8"), "# oi\n")

    def test_a_write_with_the_right_revision_lands(self):
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        status, answer = self.post("/api/file", {"path": "nota.md", "text": "novo\n", "base": rev})
        self.assertEqual(status, 200)
        self.assertEqual((paths.prose_dir() / "nota.md").read_text(encoding="utf-8"), "novo\n")
        self.assertNotEqual(answer["rev"], rev)

    def test_a_refusal_speaks_the_catalogue(self):
        # The engine answers with a KEY and the wire carries the words — so a
        # refusal a person reads is never `prose.empty_write`.
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        _, answer = self.post("/api/file", {"path": "nota.md", "text": "", "base": rev})
        self.assertTrue(answer["error"])
        self.assertFalse(answer["error"].startswith(("prose.", "webapp.")))


class TheProseCrudRoutes(ServerCase):
    """`POST /api/file/{create,rename,delete}` — the tree's own CRUD (TASK-120,
    fatia 5/7), over the same door `prose.inside` already enforces."""

    def setUp(self):
        super().setUp()
        (paths.prose_dir()).mkdir(exist_ok=True)
        (paths.prose_dir() / "nota.md").write_text("# oi\n", encoding="utf-8")

    def test_a_file_is_created(self):
        status, answer = self.post("/api/file/create", {"path": "nova.md", "dir": False})
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nova.md")
        self.assertTrue((paths.prose_dir() / "nova.md").is_file())

    def test_a_folder_is_created(self):
        status, _ = self.post("/api/file/create", {"path": "sub", "dir": True})
        self.assertEqual(status, 200)
        self.assertTrue((paths.prose_dir() / "sub").is_dir())

    def test_creating_over_a_taken_name_speaks_the_catalogue(self):
        status, answer = self.post("/api/file/create", {"path": "nota.md", "dir": False})
        self.assertEqual(status, 409)
        self.assertEqual(answer["error"], i18n.tr("prose.exists"))

    def test_a_path_that_escapes_is_refused(self):
        status, _ = self.post("/api/file/create", {"path": "../fora.md", "dir": False})
        self.assertEqual(status, 400)

    def test_a_file_is_renamed(self):
        status, answer = self.post("/api/file/rename", {"path": "nota.md", "to": "nova.md"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nova.md")
        self.assertFalse((paths.prose_dir() / "nota.md").exists())
        self.assertTrue((paths.prose_dir() / "nova.md").is_file())

    def test_renaming_what_does_not_exist_speaks_the_catalogue(self):
        status, answer = self.post("/api/file/rename", {"path": "nao-existe.md", "to": "nova.md"})
        self.assertEqual(status, 404)
        self.assertEqual(answer["error"], i18n.tr("prose.not_served"))

    def test_a_file_is_deleted(self):
        status, answer = self.post("/api/file/delete", {"path": "nota.md"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nota.md")
        self.assertFalse((paths.prose_dir() / "nota.md").exists())

    def test_a_folder_is_deleted_whole(self):
        (paths.prose_dir() / "sub").mkdir()
        (paths.prose_dir() / "sub" / "dentro.md").write_text("x", encoding="utf-8")
        status, _ = self.post("/api/file/delete", {"path": "sub"})
        self.assertEqual(status, 200)
        self.assertFalse((paths.prose_dir() / "sub").exists())

    def test_deleting_what_does_not_exist_speaks_the_catalogue(self):
        status, answer = self.post("/api/file/delete", {"path": "nao-existe.md"})
        self.assertEqual(status, 404)
        self.assertEqual(answer["error"], i18n.tr("prose.not_served"))


class TheBroadcaster(unittest.TestCase):
    """`events.Broadcaster`, isolado — sem servidor, sem rede."""

    def test_a_fresh_broadcaster_has_no_subscriber(self):
        self.assertEqual(len(events.Broadcaster()), 0)

    def test_a_publish_puts_a_signal_in_every_subscribed_queue(self):
        made = events.Broadcaster()
        first, second = made.subscribe(), made.subscribe()
        made.publish()
        self.assertIsNone(first.get_nowait())
        self.assertIsNone(second.get_nowait())

    def test_an_unsubscribed_queue_does_not_hear_the_next_publish(self):
        made = events.Broadcaster()
        gone = made.subscribe()
        made.unsubscribe(gone)
        self.assertEqual(len(made), 0)
        made.publish()
        self.assertTrue(gone.empty())

    def test_unsubscribing_an_unknown_queue_does_nothing(self):
        made = events.Broadcaster()
        made.unsubscribe(queue.Queue())  # não estoura


class TheEvents(ServerCase):
    """`/api/events` — a escrita em `Arquivos/` chega à aba aberta, sem
    recarregar (TASK-128, fatia 2/3).

    O vigia que varre de verdade vive em `beat()` (provado em `test_clock.py`);
    aqui o que se prova é o FIO — o que uma conexão recebe quando ALGUÉM
    publica no `Broadcaster` do servidor, sem precisar do relógio de pé.
    """

    def open(self) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(conn.close)
        conn.request("GET", "/api/events")
        return conn, conn.getresponse()

    def test_the_connection_opens_as_an_event_stream(self):
        _, answer = self.open()
        self.assertEqual(answer.status, 200)
        self.assertEqual(answer.getheader("Content-Type"), "text/event-stream; charset=utf-8")
        self.assertEqual(answer.fp.readline(), b": connected\n")
        self.assertEqual(answer.fp.readline(), b"\n")

    def test_a_publish_reaches_every_open_connection(self):
        _, first = self.open()
        _, second = self.open()
        for answer in (first, second):
            answer.fp.readline()
            answer.fp.readline()
        self.server.events.publish()
        for answer in (first, second):
            self.assertEqual(answer.fp.readline(), b"data: changed\n")
            self.assertEqual(answer.fp.readline(), b"\n")

    def test_closing_the_connection_unsubscribes_it(self):
        conn, answer = self.open()
        answer.fp.readline()
        answer.fp.readline()
        self.assertEqual(len(self.server.events), 1)
        answer.close()
        conn.close()
        # A thread só nota a aba fechada ao TENTAR escrever — o que o próximo
        # `keep-alive` faria sozinho, só que até `EVENTS_HEARTBEAT` segundos
        # depois. Publicar repete a tentativa sem esperar: a PRIMEIRA escrita
        # depois do `close()` ainda pode sair sem erro (o SO só devolve o
        # `RST` numa tentativa seguinte), então o teste insiste algumas vezes.
        for _ in range(100):
            self.server.events.publish()
            time.sleep(0.01)
            if len(self.server.events) == 0:
                break
        self.assertEqual(len(self.server.events), 0)


class TheConvertRoute(ServerCase):
    """`POST /api/convert` — o botão direito do arquivo (TASK-165, fatia 4/4)."""

    def setUp(self):
        super().setUp()
        (paths.prose_dir()).mkdir(exist_ok=True)
        (paths.prose_dir() / "nota.md").write_text("# Título\n\nUm parágrafo.", encoding="utf-8")

    def test_it_writes_into_convertidos_and_answers_the_name(self):
        status, answer = self.post("/api/convert", {"path": "nota.md", "to": "pdf"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nota.pdf")
        self.assertTrue((paths.convert_dir() / "nota.pdf").is_file())

    def test_docx_too(self):
        status, answer = self.post("/api/convert", {"path": "nota.md", "to": "docx"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["path"], "nota.docx")

    def test_an_unknown_format_is_a_bad_request(self):
        status, _ = self.post("/api/convert", {"path": "nota.md", "to": "epub"})
        self.assertEqual(status, 400)

    def test_a_path_that_escapes_is_refused_like_any_other_prose_route(self):
        status, _ = self.post("/api/convert", {"path": "../pyproject.toml", "to": "pdf"})
        self.assertEqual(status, 404)

    def test_a_missing_file_is_refused(self):
        status, _ = self.post("/api/convert", {"path": "nao-existe.md", "to": "pdf"})
        self.assertEqual(status, 404)


class TheRemindersDoor(ServerCase):
    """`/api/reminders` — os lembretes com o PRÓXIMO disparo (TASK-164), que é o
    que a metade "o que vem" da tela de Lembretes desenha. O cálculo é do motor
    (`reminder.upcoming`); a rota só o entrega, com `freq` e `status` no texto
    que a pessoa lê (o mesmo `tables.text_of` da tabela)."""

    def test_it_hands_the_reminders_with_their_next_fire(self):
        tables.create("reminder", {"text": "água", "freq": "daily", "at": "09:00,19:00"})
        _, _, body = self.get("/api/reminders")
        payload = json.loads(body)
        self.assertEqual(len(payload["reminders"]), 1)
        item = payload["reminders"][0]
        self.assertEqual(item["text"], "água")
        self.assertEqual(item["at"], ["09:00", "19:00"])
        self.assertEqual(item["freq"], i18n.tr("table.reminder.field.freq.daily"))
        self.assertEqual(item["status"], i18n.tr("table.reminder.field.status.active"))
        self.assertTrue(item["active"])
        self.assertIsNotNone(item["next"])

    def test_a_paused_reminder_is_left_out(self):
        # Um `paused` não volta a tocar: não é "o que vem".
        tables.create(
            "reminder",
            {"text": "quieto", "freq": "daily", "at": "09:00", "status": "paused"},
        )
        _, _, body = self.get("/api/reminders")
        self.assertEqual(json.loads(body), {"reminders": []})

    def test_a_reminder_beyond_tomorrow_is_left_out(self):
        # "Só hoje e amanhã" (2026-10-05): o que toca depois disso é calendário.
        far = date.today() + timedelta(days=30)
        tables.create(
            "reminder",
            {"text": "longe", "freq": "once", "on_date": far.isoformat(), "at": "09:00"},
        )
        _, _, body = self.get("/api/reminders")
        self.assertEqual(json.loads(body), {"reminders": []})

    def test_a_folder_with_no_reminder_answers_with_an_empty_list(self):
        _, _, body = self.get("/api/reminders")
        self.assertEqual(json.loads(body), {"reminders": []})


class TheStrongboxDoor(ServerCase):
    """`GET /api/strongbox` — a lista dos `.enc`, e só (TASK-156, fatia 3/3).

    A recusa por permissão é a de `TheCeiling` (o mesmo teste que cobre TODA
    rota de leitura, `/api/strongbox` incluída) — aqui só o que a rota é dona de
    provar: o que ela lista.
    """

    def test_the_listing_carries_every_enc_and_nothing_else(self):
        (paths.strongbox_dir() / "claro.txt").write_text("ainda nao selado", encoding="utf-8")
        strongbox.seal_file(paths.strongbox_dir() / "claro.txt", b"k" * 32)
        _, _, body = self.get("/api/strongbox")
        listing = json.loads(body)
        self.assertEqual([f["path"] for f in listing["files"]], ["claro.txt.enc"])

    def test_an_empty_cofre_answers_an_empty_list(self):
        _, _, body = self.get("/api/strongbox")
        self.assertEqual(json.loads(body)["files"], [])

    def test_a_file_still_clear_does_not_show_up(self):
        (paths.strongbox_dir() / "claro.txt").write_text("ainda nao selado", encoding="utf-8")
        _, _, body = self.get("/api/strongbox")
        self.assertEqual(json.loads(body)["files"], [])


class TheStrongboxOpenDoor(ServerCase):
    """`POST /api/strongbox/open` + `GET /api/strongbox/download` — the one-time
    link that hands back the clear without ever writing it to disk.

    `_held`/`addCleanup` follow the same care `setUp` already takes with
    `keys._main`: the Vault's key is global to the PROCESS, and a test that
    changes it has to hand back what was there before it ends.
    """

    KEY = b"k" * 32

    def setUp(self):
        super().setUp()
        held = webapp_keys._keys.get(webapp_keys.STRONGBOX_KEY_ENV)
        webapp_keys._keys[webapp_keys.STRONGBOX_KEY_ENV] = self.KEY
        self.addCleanup(webapp_keys._keys.pop, webapp_keys.STRONGBOX_KEY_ENV, None)
        if held is not None:
            self.addCleanup(webapp_keys._keys.__setitem__,
                            webapp_keys.STRONGBOX_KEY_ENV, held)

    def seal(self, name: str, content: bytes, key: bytes | None = None) -> str:
        where = paths.strongbox_dir() / name
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_bytes(content)
        strongbox.seal_file(where, key if key is not None else self.KEY)
        return f"{name}{strongbox.SUFFIX}"

    def test_a_path_outside_the_listing_is_refused_before_any_link_exists(self):
        status, answer = self.post("/api/strongbox/open", {"path": "../outside.enc"})
        self.assertEqual(status, 400)
        self.assertEqual(answer["error"], "bad request")

    def test_with_no_key_this_boot_opening_is_refused(self):
        path = self.seal("photo.png", b"image bytes")
        webapp_keys._keys.pop(webapp_keys.STRONGBOX_KEY_ENV, None)
        status, answer = self.post("/api/strongbox/open", {"path": path})
        self.assertEqual(status, 503)
        self.assertEqual(answer["error"], i18n.tr("strongbox.no_key"))

    def test_a_minted_link_opens_the_clear_exactly_once(self):
        clear = b"image bytes, nothing ciphered here"
        path = self.seal("photo.png", clear)
        status, opened = self.post("/api/strongbox/open", {"path": path})
        self.assertEqual(status, 200)
        self.assertEqual(opened["kind"], "image")
        url = opened["url"]
        self.assertTrue(url.startswith("/api/strongbox/download?token="))

        status, headers, body = self.get(url)
        self.assertEqual(status, 200)
        self.assertEqual(body, clear)  # the clear, never the `.enc`
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertIn('inline; filename="photo.png"', headers["Content-Disposition"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

        # Walking the SAME link a second time finds nothing — the token was
        # already spent by the first `take`, and the Vault keeps no copy of it.
        status, _, _ = self.get(url)
        self.assertEqual(status, 404)

    def test_the_open_answers_the_kind_the_page_draws(self):
        # The kind travels WITH the address, so the page knows how to draw the
        # file before it walks the one-time link (`strongbox.look`).
        text = self.seal("nota.txt", "uma nota com acento".encode("utf-8"))
        status, opened = self.post("/api/strongbox/open", {"path": text})
        self.assertEqual(status, 200)
        self.assertEqual(opened["kind"], "text")

        pdf = self.seal("doc.pdf", b"%PDF-1.7\n")
        _, opened = self.post("/api/strongbox/open", {"path": pdf})
        self.assertEqual(opened["kind"], "pdf")

        # A `.txt` that is not valid UTF-8 has no text viewer — it downloads.
        broken = self.seal("quebrado.txt", b"caf\xe9")
        _, opened = self.post("/api/strongbox/open", {"path": broken})
        self.assertEqual(opened["kind"], "other")

    def test_an_unlisted_extension_downloads_as_an_attachment(self):
        # `.html` is the case the person raised: opening this as a document
        # would run whatever is inside it in AT's own origin. It leaves as
        # `octet-stream` and `attachment`, never as `text/html`.
        path = self.seal("page.html", b"<script>alert(1)</script>")
        _, opened = self.post("/api/strongbox/open", {"path": path})
        _, headers, body = self.get(opened["url"])
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertIn('attachment; filename="page.html"', headers["Content-Disposition"])
        self.assertEqual(body, b"<script>alert(1)</script>")

    def test_an_svg_is_an_attachment_too_despite_being_an_image(self):
        # SVG is XML and may carry `<script>`: "is it an image" is not the rule.
        path = self.seal("drawing.svg", b"<svg onload='alert(1)'></svg>")
        _, opened = self.post("/api/strongbox/open", {"path": path})
        _, headers, _ = self.get(opened["url"])
        self.assertEqual(headers["Content-Type"], "application/octet-stream")
        self.assertIn("attachment", headers["Content-Disposition"])

    def test_a_file_the_key_does_not_open_is_refused_at_the_door(self):
        # The folder was sealed with a DIFFERENT key than this boot's — the
        # same answer a wrong key gets at any door of the Vault. The door is
        # the OPEN now: it reads the clear once to answer the KIND, so a file
        # the key does not open is refused BEFORE any link exists — no overlay
        # ever opens on an error.
        path = self.seal("photo.png", b"bytes", key=b"o" * 32)
        status, answer = self.post("/api/strongbox/open", {"path": path})
        self.assertEqual(status, 500)
        self.assertEqual(answer["error"], i18n.tr("strongbox.unreadable"))

    def test_an_unknown_token_answers_not_found(self):
        status, _, _ = self.get("/api/strongbox/download?token=never-existed")
        self.assertEqual(status, 404)

    def test_a_token_outside_its_ttl_answers_not_found(self):
        path = self.seal("photo.png", b"bytes")
        _, opened = self.post("/api/strongbox/open", {"path": path})
        later = strongbox_links.time.monotonic() + strongbox_links.TTL + 1
        with mock.patch.object(strongbox_links.time, "monotonic", return_value=later):
            status, _, _ = self.get(opened["url"])
        self.assertEqual(status, 404)


class TheAskDoor(ServerCase):
    """`POST /api/ask` — the box's door, and the words it reads back.

    The box has TWO SHAPES (the chat and the balloon), and they ask the same thing
    and read the same thing: this route is that one thing, and both walk it.
    """

    def test_the_proposal_comes_before_the_answer(self):
        status, answer = self.post("/api/ask", {"text": "cria uma tarefa pra hoje"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        # The proposal in the ENGINE's words — the action's, the table's — and the
        # answer after it in the engine's own sentence. The page writes neither.
        self.assertIn(i18n.tr("table.action.create"), answer["proposal"])
        self.assertIn(tables.table_name("task"), answer["proposal"])
        self.assertEqual(answer["text"], i18n.tr("table.created", id="TASK-2"))

    def test_the_sentence_of_the_item_reaches_the_row_it_names(self):
        # "editar a tarefa 1 status concluída": the row named the way a person names
        # one becomes a WRITE, and the LISTING UNDERNEATH is what changes — which is
        # the effect the balloon exists for.
        status, answer = self.post("/api/ask", {"text": "editar a tarefa 1 status concluída"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertEqual(answer["text"], i18n.tr("table.edited", id="TASK-1"))
        self.assertEqual(tables.find("task", 1)["status"], "done")

    def test_a_sentence_outside_the_catalogue_is_refused_by_name(self):
        status, answer = self.post("/api/ask", {"text": "banana"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "refused")
        self.assertIsNone(answer["proposal"])  # nothing was proposed, nothing written
        self.assertIn("banana", answer["text"])

    def test_an_ambiguous_sentence_comes_back_as_a_question(self):
        status, answer = self.post("/api/ask", {"text": "cria um projeto pra sexta"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "question")
        self.assertEqual(answer["text"], i18n.tr("nlu.ask.which_field", text="sexta"))
        self.assertEqual(tables.rows("project"), [])  # a question writes nothing
        # The grammar's OWN ambiguity carries no rewritten sentence to confirm —
        # confirming it would only ask the very same question again (TASK-183).
        self.assertIsNone(answer["confirm"])

    def test_the_engine_is_the_one_that_validates_and_it_says_so(self):
        # The proposal is made and the DECLARATION refuses it: what a person reads
        # after the proposal is the engine's refusal, not a second sentence.
        status, answer = self.post("/api/ask", {"text": "cria um lembrete pra hoje"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertTrue(answer["proposal"])
        self.assertEqual(
            answer["text"],
            i18n.tr("table.error.required", field=tables.label("reminder", "text")),
        )

    def test_it_refuses_an_empty_sentence(self):
        self.assertEqual(self.post("/api/ask", {})[0], 400)
        self.assertEqual(self.post("/api/ask", {"text": "   "})[0], 400)

    def test_it_is_a_write_like_the_others_and_obeys_the_same_guards(self):
        self.assertEqual(
            self.post("/api/ask", {"text": "lista as tarefas"},
                      headers={"Origin": "http://evil.example"})[0],
            403,
        )

    def test_the_interpreter_off_answers_in_its_own_words(self):
        settings.save({**settings.load(), "interpreter": False})
        status, answer = self.post("/api/ask", {"text": "cria uma tarefa pra hoje"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "refused")
        self.assertEqual(answer["text"], i18n.tr("nlu.error.interpreter_off"))
        self.assertEqual(len(tables.rows("task")), 1)  # and nothing was written

    def test_a_refusal_hints_the_assist_with_no_key(self):
        # "banana" refuses, e com nada para abrir a credencial o hint é a única
        # coisa que muda: o Jev lê TODA frase, então uma chave pode mudar a
        # resposta deste pedido.
        status, answer = self.post("/api/ask", {"text": "banana"})
        self.assertEqual(status, 200)
        self.assertTrue(answer["assist"])

    def test_any_refusal_hints_the_assist_with_no_key(self):
        # Não há mais gatilho: uma recusa que NÃO é de ação/tabela ausente
        # também passa pelo Jev agora, então ela também dá o hint.
        status, answer = self.post("/api/ask", {"text": "cria e lista uma tarefa"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "refused")
        self.assertTrue(answer["assist"])

    def test_an_answer_never_hints_the_assist(self):
        status, answer = self.post("/api/ask", {"text": "cria uma tarefa pra hoje"})
        self.assertEqual(status, 200)
        self.assertFalse(answer["assist"])

    def test_the_switch_off_never_hints_the_assist(self):
        settings.save({**settings.load(), assist.SWITCH: False})
        status, answer = self.post("/api/ask", {"text": "banana"})
        self.assertEqual(status, 200)
        self.assertFalse(answer["assist"])


class TheAssistThroughAsk(ServerCase):
    """`POST /api/ask` with a `main_key` — the REAL path reaching Jev for real
    (TASK-180, fatia 3/3), proven with a FAKE Jev client and never a real one.
    """

    MAIN_KEY = "uma-frase-bem-longa-de-exemplo-mesmo"

    def sealed(self, value: str = "a-chave-de-exemplo-do-jev") -> dict:
        return secrets.seal("jev", jev.SERVICE, value, self.MAIN_KEY)

    def fake(self, action: str, table: str, confidence: float):
        def post(url, body, headers, timeout):
            return json.dumps({
                "answers": {
                    "action": {"type": "choice", "choice": action,
                               "probabilities": {}, "confidence": confidence},
                    "table": {"type": "choice", "choice": table,
                              "probabilities": {}, "confidence": confidence},
                },
            }).encode("utf-8")
        return post

    def test_automatic_mode_applies_the_rewrite_for_real(self):
        self.sealed()
        settings.save({**settings.load(), assist.MODE: assist.AUTOMATIC})
        with mock.patch.object(jev, "_post", self.fake("create", "task", 0.95)):
            status, answer = self.post(
                "/api/ask", {"text": "bota uma penca aqui", "main_key": self.MAIN_KEY},
            )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertEqual(len(tables.rows("task")), 2)

    def test_cautious_mode_asks_instead_of_applying(self):
        self.sealed()
        # `MODE` is left at its default — `CAUTIOUS` — on purpose.
        with mock.patch.object(jev, "_post", self.fake("create", "task", 0.95)):
            status, answer = self.post(
                "/api/ask", {"text": "bota uma penca aqui", "main_key": self.MAIN_KEY},
            )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "question")
        self.assertEqual(len(tables.rows("task")), 1)  # nothing written
        # The REWRITTEN sentence travels too — it is what "Confirmar" resubmits
        # (TASK-183), and it is not the phrase that was typed.
        self.assertIsNotNone(answer["confirm"])
        self.assertNotEqual(answer["confirm"], "bota uma penca aqui")

    def test_confirming_resubmits_the_rewrite_with_no_key_at_all(self):
        # "Confirmar" is the SAME road a Main Key retry already walks — ask()
        # again — except the rewritten sentence resolves on the ordinary
        # matcher alone, with no Main Key and no second trip to Jev.
        self.sealed()
        with mock.patch.object(jev, "_post", self.fake("create", "task", 0.95)):
            status, first = self.post(
                "/api/ask", {"text": "bota uma penca aqui", "main_key": self.MAIN_KEY},
            )
        self.assertEqual(first["kind"], "question")
        status, answer = self.post("/api/ask", {"text": first["confirm"]})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertEqual(len(tables.rows("task")), 2)

    def test_a_wrong_main_key_opens_nothing_and_stands_by_the_refusal(self):
        self.sealed()
        with mock.patch.object(jev, "_post", self.fake("create", "task", 0.95)):
            status, answer = self.post(
                "/api/ask",
                {"text": "bota uma penca aqui", "main_key": "outra-frase-tambem-longa"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "refused")

    def test_the_key_is_dropped_without_the_assist_permission(self):
        # A role carrying `nlu:ask` but not `assist:ask` gets the sentence's
        # ORDINARY refusal — never a 403 over a field the request did not have
        # to send (the same "a key handed in without the permission is dropped"
        # the route's own docstring promises).
        self.sealed()
        actors.create_admin("Rafael", "uma-frase-bem-longa-de-admin")
        role = tables.create("role", {"name": "sem-assist", "permissions": "nlu:ask"})
        tables.create(
            "actor",
            {"name": "Leitor", "type": "person",
             "role": str(store.number_of(role)), "credential": "outra-frase-bem-longa"},
        )
        status, headers, _ = self.post_full(
            "/api/session", {"name": "Leitor", "credential": "outra-frase-bem-longa"},
        )
        self.assertEqual(status, 200)
        cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
        with mock.patch.object(jev, "_post", self.fake("create", "task", 0.95)):
            status, answer = self.post(
                "/api/ask", {"text": "bota uma penca aqui", "main_key": self.MAIN_KEY},
                headers=cookie,
            )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "refused")
        self.assertFalse(answer["assist"])
        self.assertEqual(len(tables.rows("task")), 1)  # nothing written


class TheAssistKnobs(ServerCase):
    """`POST /api/assist` — the Control Panel's write into the two settings
    (TASK-180, fatia 3/3), and `/api/state`'s read of the same pair."""

    def test_the_state_carries_the_switch_and_the_mode(self):
        status, _, body = self.get("/api/state")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(payload["assist"])
        self.assertEqual(payload["assist_mode"], assist.CAUTIOUS)

    def test_it_turns_the_switch_off_and_back_on(self):
        status, answer = self.post("/api/assist", {"enabled": False})
        self.assertEqual(status, 200)
        self.assertFalse(answer["enabled"])
        self.assertFalse(assist.enabled())
        status, answer = self.post("/api/assist", {"enabled": True})
        self.assertEqual(status, 200)
        self.assertTrue(answer["enabled"])
        self.assertTrue(assist.enabled())

    def test_it_writes_the_mode(self):
        status, answer = self.post("/api/assist", {"mode": assist.AUTOMATIC})
        self.assertEqual(status, 200)
        self.assertEqual(answer["mode"], assist.AUTOMATIC)
        self.assertEqual(assist.mode(), assist.AUTOMATIC)

    def test_an_unknown_mode_is_rejected(self):
        status, _ = self.post("/api/assist", {"mode": "qualquer-coisa"})
        self.assertEqual(status, 400)
        self.assertEqual(assist.mode(), assist.CAUTIOUS)

    def test_it_leaves_a_line_and_a_version_like_any_other_setting(self):
        self.post("/api/assist", {"enabled": False})
        lines = store.load("audit")
        self.assertTrue(lines)
        self.assertEqual(lines[-1]["table"], permissions.SETTING)
        self.assertEqual(lines[-1]["via"], audit.WEBAPP)


class TheEntrance(ServerCase):
    """The Forms door: the credential, the session, and the refusal (item 10).

    The base case builds a folder carrying the engine's row and nobody else —
    the folder that asks nothing — and this class is the folder that DOES ask.
    Between the two there is one row with a credential, and it is the whole
    difference between an API that answers and an API that refuses.
    """

    CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Rafael"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)

    def open_session(self) -> str:
        """The `Cookie` header a proved credential earns — the token alone, the
        way a browser sends it back."""
        status, headers, answer = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL}
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["actor"]["name"], self.NAME)
        return headers["Set-Cookie"].split(";")[0]

    def cookie(self, value: str) -> dict:
        return {"Cookie": value}

    # -- the door itself, and it is public ---------------------------------

    def test_the_door_says_that_it_asks_and_that_nobody_is_in(self):
        _, _, body = self.get("/api/session")
        answer = json.loads(body)
        self.assertIs(answer["auth"], True)
        self.assertIsNone(answer["actor"])
        self.assertEqual(answer["lang"], "pt_BR")

    def test_the_door_carries_no_table_and_no_count(self):
        # It is the ONE public answer of the API, and a page that described the
        # folder to whoever can reach the port would be the folder read by
        # whoever can reach the port. `version` is not a description of the
        # folder — it is the same word `at-cli --version` prints — and it is
        # what lets a second `at-cli webapp` landing on this port ask this
        # very route which release is already up.
        _, _, body = self.get("/api/session")
        answer = json.loads(body)
        self.assertEqual(
            sorted(set(answer)
                   - {"auth", "first", "actor", "lang", "labels", "version"}), [])

    def test_the_words_of_the_entrance_arrive_in_both_languages(self):
        # The first screen AT ever shows speaks the active language, and it
        # learns the words HERE — there is no session to read `/api/state` with.
        # Both languages travel, the way they do in the state: switching the
        # language on screen costs no request, and the server keeps owning them.
        _, _, body = self.get("/api/session")
        labels = json.loads(body)["labels"]
        self.assertEqual(
            labels["session_name"],
            {code: i18n.text("webapp.session_name", code) for code in i18n.SUPPORTED},
        )
        self.assertEqual(labels["session_name"]["pt_BR"], "Nome")

    def test_the_entrance_payload_carries_what_the_page_reads(self):
        # The state's contract, one floor up: the page reads the door's answer by
        # NAME, so a name that drifts is invisible — the entrance comes out with
        # no word in it — and this is what makes the server owe every one.
        entry = webapp.entry_payload(self.server.sessions.open(actors.admins()[0]))
        self.assertEqual(sorted(interface_fields("Entry", "session.ts") - set(entry)), [])
        self.assertEqual(
            sorted(interface_fields("Actor", "session.ts") - set(entry["actor"])), []
        )

    # -- the credential, and the session it opens --------------------------

    def test_the_right_credential_opens_a_session(self):
        cookie = self.open_session()
        self.assertTrue(cookie.startswith("at_session="))

    def test_the_cookie_is_host_only_http_only_and_out_of_another_site(self):
        _, headers, _ = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL}
        )
        written = headers["Set-Cookie"]
        self.assertIn("HttpOnly", written)
        self.assertIn("SameSite=Strict", written)
        # No `Domain=`: that absence is the guard, and it is what stops a name
        # that resolves to this address (DNS rebinding) from carrying the cookie.
        self.assertNotIn("Domain", written)
        # And no `Secure`: the hosted path is plain HTTP on loopback, and a
        # `Secure` cookie would never come back — the flag belongs to the TLS of
        # item 12, where the TLS exists.
        self.assertNotIn("Secure", written)

    def test_the_wrong_credential_does_not(self):
        status, headers, answer = self.post_full(
            "/api/session", {"name": self.NAME, "credential": "outra-frase-longa"}
        )
        self.assertEqual(status, 401)
        self.assertEqual(answer["error"], i18n.tr("webapp.session_refused"))
        self.assertIsNone(headers.get("Set-Cookie"))

    def test_a_name_nobody_wears_is_refused_in_the_same_words(self):
        # The answer says neither which of the two was wrong nor that the name
        # exists at all — and the miss spends the same derivation, so the clock
        # does not say it either.
        status, answer = self.post(
            "/api/session", {"name": "Ninguém", "credential": self.CREDENTIAL}
        )
        self.assertEqual(status, 401)
        self.assertEqual(answer["error"], i18n.tr("webapp.session_refused"))

    def test_a_body_that_is_not_a_pair_is_a_bad_request(self):
        self.assertEqual(self.post("/api/session", {"name": self.NAME})[0], 400)
        self.assertEqual(self.post("/api/session", {"credential": self.CREDENTIAL})[0], 400)

    def test_the_entrance_obeys_the_guards_of_every_other_write(self):
        status, _ = self.post(
            "/api/session",
            {"name": self.NAME, "credential": self.CREDENTIAL},
            headers={"Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)

    # -- the gate, which is what the session is FOR ------------------------

    def test_a_token_nobody_issued_is_no_session(self):
        status, _, body = self.get("/api/state", headers=self.cookie("at_session=forjado"))
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.session_needed"))

    def test_the_state_is_refused_without_a_session(self):
        self.assertEqual(self.status("/api/state"), 401)

    def test_the_reads_are_refused_without_a_session(self):
        for path in ("/api/tree", "/api/projects", "/api/table/task"):
            with self.subTest(path=path):
                self.assertEqual(self.status(path), 401)

    def test_the_writes_are_refused_without_a_session(self):
        # `do_POST` dispatches by itself and never walks `_route`, so a gate
        # written into the GET side alone would leave every write open.
        for path in ("/api/file", "/api/ask", "/api/table/task"):
            with self.subTest(path=path):
                self.assertEqual(self.post(path, {"action": "create", "set": {}})[0], 401)
        self.assertEqual(len(tables.rows("task")), 1)  # and nothing was written

    def test_with_the_session_the_page_reads(self):
        status, _, body = self.get("/api/state", headers=self.cookie(self.open_session()))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["lang"], "pt_BR")

    def test_with_the_session_the_page_writes(self):
        status, answer = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "vinda de dentro"}},
            headers=self.cookie(self.open_session()),
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["shown_id"], "TASK-2")

    def test_the_state_still_carries_the_words_of_the_entrance(self):
        # The entrance comes back when a session dies under a running page, and
        # it comes back over the labels `/api/state` left behind: a state that
        # dropped them would draw a SECOND entrance with no words in it.
        _, _, body = self.get("/api/state", headers=self.cookie(self.open_session()))
        labels = json.loads(body)["labels"]
        for key in webapp.SESSION_WORDS:
            with self.subTest(key=key):
                self.assertIn(key, labels)

    def test_the_page_and_the_look_are_served_to_whoever_has_not_entered(self):
        # The entrance has to be DRESSED before anybody is in, and it is dressed
        # by the same page and the same themes as everything else (§5).
        status, headers, _ = self.get("/")
        self.assertIn(status, (200, 500))
        self.assertEqual(headers["Content-Security-Policy"], webapp.CSP)
        self.assertEqual(self.status("/base.css"), 200)
        self.assertEqual(self.status("/theme.css?theme=at"), 200)

    def test_the_sessions_belong_to_the_server_and_not_to_the_process(self):
        # A session is a session of THIS server: another AT, in the same
        # process, does not answer for the token this one issued.
        cookie = self.open_session()
        other = webapp.make_server(0)
        port = other.server_address[1]
        thread = threading.Thread(
            target=other.serve_forever,
            kwargs={"poll_interval": POLL}, daemon=True,
        )
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/state", headers=self.cookie(cookie)
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code, 401)
            caught.exception.close()
        finally:
            other.shutdown()
            other.server_close()
            thread.join(timeout=5)


class TheBasicTransport(ServerCase):
    """Basic: the same credential of Forms, by the other transport (item 10).

    The permission lives in `settings.json` and never a secret does (§3,
    Configurações gerais): while it is off the header is refused, and turned on,
    the credential that opens the entrance opens this door.
    """

    NAME = "Rafael"
    CREDENTIAL = "uma-frase-bem-longa"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)

    def allow(self) -> None:
        """The folder's permission, written the way a person would write it."""
        settings.save({**settings.load(), webapp.BASIC_KEY: True})

    def header(self, name: str | None = None,
               credential: str | None = None) -> dict:
        pair = f"{name or self.NAME}:{credential or self.CREDENTIAL}"
        return {"Authorization": "Basic " + base64.b64encode(pair.encode()).decode()}

    def test_while_the_permission_is_off_the_header_is_refused(self):
        self.assertFalse(webapp.basic_allowed())
        self.assertEqual(self.status("/api/state", headers=self.header()), 401)

    def test_turned_on_the_same_credential_opens_the_api(self):
        self.allow()
        status, _, body = self.get("/api/state", headers=self.header())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["lang"], "pt_BR")

    def test_the_wrong_credential_is_refused_in_the_same_words(self):
        self.allow()
        status, _, body = self.get(
            "/api/state", headers=self.header(credential="outra-coisa")
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.session_needed"))

    def test_a_header_that_is_not_a_pair_is_a_refusal_and_not_a_crash(self):
        # A stranger may send anything in a header: what travels is base64 of
        # nothing, or a payload with no colon, and neither is a request thread
        # taken down.
        self.allow()
        for value in ("Basic !!!", "Basic", "Basic " +
                      base64.b64encode(b"sem dois pontos").decode()):
            with self.subTest(value=value):
                self.assertEqual(
                    self.status("/api/state", headers={"Authorization": value}), 401
                )

    def test_the_refusal_challenges_who_tried_and_only_who_tried(self):
        self.allow()
        # An attempt is owed the challenge the browser understands — it is what
        # makes a `curl -u` and a browser arrive at the same place.
        _, headers, _ = self.get("/api/state", headers=self.header(credential="errada"))
        self.assertEqual(headers["WWW-Authenticate"], f'Basic realm="{webapp.REALM}"')
        # The page sends none, and is owed none: a challenge travelling with its
        # own 401 would pop the browser's dialog over the entrance AT drew.
        _, headers, _ = self.get("/api/state")
        self.assertIsNone(headers.get("WWW-Authenticate"))

    def test_a_folder_that_does_not_take_basic_challenges_nobody(self):
        # Nothing is offered while the permission is off, so nothing is
        # challenged: the header would be announcing a door that is shut.
        status, headers, _ = self.get("/api/state", headers=self.header())
        self.assertEqual(status, 401)
        self.assertIsNone(headers.get("WWW-Authenticate"))

    def test_the_entrance_names_the_actor_the_header_proved(self):
        self.allow()
        _, _, body = self.get("/api/session", headers=self.header())
        self.assertEqual(json.loads(body)["actor"]["name"], self.NAME)

    def test_the_write_path_reads_the_header_too(self):
        # `do_POST` dispatches by itself and never walks `_route`: a header read
        # into the GET side alone would leave every write closed.
        self.allow()
        status, answer = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "vinda do cabeçalho"}},
            headers=self.header(),
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["shown_id"], "TASK-2")


class TheMachineTransport(ServerCase):
    """Bearer: the machine's token alone, and the agent's own door (item 10).

    The token is the credential the `agent` row carries hashed — a machine
    communicates with a token, and it says what it is in a header of its own
    mind, not in the credential.
    """

    TOKEN = "um-token-de-maquina"
    AGENT = "robô"

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        role = store.load("role")[0]
        self.agent = tables.create(
            "actor",
            {
                "name": self.AGENT,
                "type": "agent",
                "role": str(store.number_of(role)),
                "credential": self.TOKEN,
            },
        )

    def bearer(self, token: str | None = None) -> dict:
        return {"Authorization": "Bearer " + (token or self.TOKEN)}

    def test_the_token_opens_the_api(self):
        status, _, body = self.get("/api/state", headers=self.bearer())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["lang"], "pt_BR")

    def test_the_wrong_token_does_not(self):
        status, _, body = self.get("/api/state", headers=self.bearer("outro-token"))
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.session_needed"))

    def test_it_does_not_need_the_basic_permission(self):
        # Basic and the machine credential are two ways in, not one: the switch
        # governs the person's header, and the machine's door is its own.
        self.assertFalse(webapp.basic_allowed())
        self.assertEqual(self.status("/api/state", headers=self.bearer()), 200)

    def test_a_person_does_not_enter_by_the_machines_door(self):
        status, _, _ = self.get(
            "/api/state", headers=self.bearer("uma-frase-bem-longa")
        )
        self.assertEqual(status, 401)

    def test_the_machine_does_not_enter_by_forms(self):
        status, answer = self.post(
            "/api/session", {"name": self.AGENT, "credential": self.TOKEN}
        )
        self.assertEqual(status, 401)
        self.assertEqual(answer["error"], i18n.tr("webapp.session_refused"))

    def test_the_machine_does_not_enter_by_basic_either(self):
        # The Basic door is the person's — it proves by `actors.authenticate`,
        # which reads `people()` — and the machine's token is not a name's
        # credential, permission or no permission.
        settings.save({**settings.load(), webapp.BASIC_KEY: True})
        pair = f"{self.AGENT}:{self.TOKEN}".encode()
        status, _, _ = self.get(
            "/api/state",
            headers={"Authorization": "Basic " + base64.b64encode(pair).decode()},
        )
        self.assertEqual(status, 401)

    def test_the_entrance_names_the_machine(self):
        _, _, body = self.get("/api/session", headers=self.bearer())
        self.assertEqual(json.loads(body)["actor"]["name"], self.AGENT)

    def test_it_writes_while_its_role_carries_the_write(self):
        # The machine reaches the same API by its own door, and what it reaches
        # is what its role CARRIES (item 11). Its role here is the
        # administrator's, so the write goes through — the write is the role's
        # to allow and not the transport's.
        status, answer = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "vinda da máquina"}},
            headers=self.bearer(),
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["shown_id"], "TASK-2")

    def test_the_role_is_what_caps_the_machine(self):
        # The sentence item 10 left standing — a proved actor reaches everything
        # — is the one this reads: the token is the credential of a row that
        # wears a role like any other, and the ceiling is read off it.
        role = tables.create("role", {"name": "leitor", "permissions": "task:list"})
        tables.edit("actor", self.agent["id"], {"role": str(role["id"])})

        self.assertEqual(self.status("/api/table/task", headers=self.bearer()), 200)
        status, _ = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "não devia"}},
            headers=self.bearer(),
        )
        self.assertEqual(status, 403)
        self.assertEqual(len(tables.rows("task")), 1)  # and nothing was written


class TheGateTransport(ServerCase):
    """The gate: the identity the Caddy copies, valid only with the secret (§7b).

    It is the fourth way in and the only one whose proof is not here — Authelia
    proved the person, and what AT reads is a header, which is a thing any
    client can write. What makes it an identity is the gate secret travelling
    beside it, and that is what this class is: the same header, twice, with and
    without the secret.
    """

    NAME = "Rafael"
    CREDENTIAL = "uma-frase-bem-longa"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)
        self.secret = drawn_gate()

    def identity(self, name: str | None = None, secret: str | None = None) -> dict:
        """What the Caddy hands the WebApp: the name, and the secret with it."""
        headers = {webapp.GATE_IDENTITY: name or self.NAME}
        if secret is not None:
            headers[caddy.GATE_HEADER] = secret
        return headers

    def test_the_identity_with_the_secret_is_who_it_says_it_is(self):
        status, _, body = self.get("/api/state", headers=self.identity(secret=self.secret))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["lang"], "pt_BR")

    def test_the_identity_without_the_secret_is_refused(self):
        status, _, body = self.get("/api/state", headers=self.identity())
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.gate_refused"))

    def test_a_secret_that_is_not_the_folders_is_refused_the_same_way(self):
        status, _, body = self.get(
            "/api/state", headers=self.identity(secret="outro-segredo-qualquer")
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.gate_refused"))

    def test_a_name_nobody_wears_is_no_session(self):
        # The gate proved somebody the folder has no row for, and AT does not
        # invent one: the identity is an identity OF the folder.
        status, _, body = self.get(
            "/api/state", headers=self.identity("Ninguém", self.secret)
        )
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.session_needed"))

    def test_the_writes_are_refused_too(self):
        # `do_POST` dispatches by itself and never walks `_route`, so a refusal
        # written into the GET side alone would leave every write open.
        status, answer = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "de fora"}},
            headers=self.identity(),
        )
        self.assertEqual(status, 403)
        self.assertEqual(answer["error"], i18n.tr("webapp.gate_refused"))
        self.assertEqual(len(tables.rows("task")), 1)  # and nothing was written

    def test_with_the_secret_the_write_lands(self):
        status, answer = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "pelo portão"}},
            headers=self.identity(secret=self.secret),
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["record"]["shown_id"], "TASK-2")

    def test_the_ceiling_is_the_role_of_the_row_the_name_wears(self):
        # The gate says WHO; what that reaches is AT's, and it is the same
        # door every other transport goes through (`_may`).
        with redirect_stdout(io.StringIO()):
            tables.create("actor", {"name": "Sem papel", "type": "person"})
        status, _, body = self.get(
            "/api/state", headers=self.identity("Sem papel", self.secret)
        )
        self.assertEqual(status, 403)
        self.assertNotEqual(json.loads(body)["error"], i18n.tr("webapp.gate_refused"))

    def test_a_folder_that_never_drew_a_gate_takes_no_identity(self):
        # On the hosted path there is no secret for the Caddy to attach, so a
        # name arriving there is a header somebody wrote — and the refusal is
        # the gate's, because the request is asserting an identity.
        caddy.gate_file().unlink()
        status, _, body = self.get(
            "/api/state", headers=self.identity(secret=self.secret)
        )
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], i18n.tr("webapp.gate_refused"))

    def test_the_entrance_answer_carries_the_actor_the_gate_asserted(self):
        # `/api/session` is the one public answer of the API and it sits ABOVE
        # the gate — the page asks it before it has a session, and what it says
        # is who is past the door, which the gate already is.
        status, _, body = self.get(
            "/api/session", headers=self.identity(secret=self.secret)
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["actor"], {"name": self.NAME})

    def test_the_public_answer_says_nobody_is_in_for_a_forged_identity(self):
        # A refusal here would be a status the entrance cannot draw; what a
        # forged header earns is the same answer as anybody else's — nobody.
        _, _, body = self.get("/api/session", headers=self.identity())
        self.assertIsNone(json.loads(body)["actor"])


class TheCeiling(ServerCase):
    """The role the actor's row points at — the strict ceiling (item 11).

    The session says WHO is in; the role says HOW FAR they reach. Every route of
    the API demands one permission of the catalogue, and the actor a request
    proved is refused (403) when its role does not carry it. What the base case
    builds is the folder that asks nobody; this one builds a folder with an
    administrator and a second person wearing a role of the test's own — and the
    machine, which is capped by the same door.
    """

    ADMIN = "Rafael"
    ADMIN_CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Leitor"
    CREDENTIAL = "outra-frase-bem-longa"

    # Every route of the API, which is what "every route" means: the reads of
    # `_get_api` and the writes of `do_POST`, minus the entrance, which is the
    # one that has to answer before anybody is in.
    READS = ("/api/state", "/api/projects", "/api/orphans", "/api/project/1",
             "/api/tree", "/api/events", "/api/file?path=nota.md",
             "/api/file/bytes?path=nota.md",
             "/api/table/task", "/api/strongbox", "/api/strongbox/download?token=x")
    WRITES = (
        ("/api/file", {"path": "nota.md", "text": "x", "base": ""}),
        ("/api/file/create", {"path": "nova.md", "dir": False}),
        ("/api/file/rename", {"path": "nota.md", "to": "nova.md"}),
        ("/api/file/delete", {"path": "nota.md"}),
        ("/api/ask", {"text": "cria uma tarefa pra hoje"}),
        ("/api/table/task", {"action": "create", "set": {"text": "x"}}),
        ("/api/table/task", {"action": "edit", "id": 1, "set": {"text": "x"}}),
        ("/api/offline/sync", {"entries": [
            {"action": "edit", "id": 1, "values": {"text": "x"},
             "edited_at": "2030-01-01T00:00:00.000Z"},
        ]}),
        ("/api/convert", {"path": "nota.md", "to": "pdf"}),
        ("/api/strongbox/open", {"path": "nao-existe.enc"}),
    )

    def setUp(self):
        super().setUp()
        actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def person(self, carried: str, name: str | None = None) -> dict:
        """A person wearing a role that carries exactly `carried`."""
        role = tables.create(
            "role",
            {"name": f"papel-{len(store.load('role'))}", "permissions": carried},
        )
        return tables.create(
            "actor",
            {
                "name": name or self.NAME,
                "type": "person",
                "role": str(store.number_of(role)),
                "credential": self.CREDENTIAL,
            },
        )

    def cookie(self, name: str | None = None, credential: str | None = None) -> dict:
        status, headers, _ = self.post_full(
            "/api/session",
            {"name": name or self.NAME, "credential": credential or self.CREDENTIAL},
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    # -- exactly what the role carries -------------------------------------

    def test_a_role_grants_exactly_what_it_carries(self):
        self.person("task:list,prose:read")
        cookie = self.cookie()
        # What it carries answers...
        self.assertEqual(self.status("/api/table/task", headers=cookie), 200)
        self.assertEqual(self.status("/api/tree", headers=cookie), 200)
        # ...and what it does not carry is refused, route by route.
        self.assertEqual(self.status("/api/state", headers=cookie), 403)
        self.assertEqual(self.status("/api/projects", headers=cookie), 403)
        self.assertEqual(
            self.post(
                "/api/table/task", {"action": "create", "set": {"text": "x"}},
                headers=cookie,
            )[0],
            403,
        )
        self.assertEqual(len(tables.rows("task")), 1)  # and nothing was written

    def test_the_refusal_names_the_permission_it_missed(self):
        # A person reads the refusal, so it carries the permission's own label —
        # the object's word and the action's, composed where the catalogue is.
        self.person("task:list")
        status, answer = self.post(
            "/api/table/task", {"action": "create", "set": {"text": "x"}},
            headers=self.cookie(),
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            answer["error"],
            i18n.tr(
                "permission.denied", permission=permissions.label("task:create")
            ),
        )

    def test_every_route_is_refused_to_a_role_that_carries_nothing(self):
        self.person("")
        cookie = self.cookie()
        for path in self.READS:
            with self.subTest(path=path):
                self.assertEqual(self.status(path, headers=cookie), 403)
        for path, payload in self.WRITES:
            with self.subTest(path=path, action=payload.get("action")):
                self.assertEqual(self.post(path, payload, headers=cookie)[0], 403)
        self.assertEqual(len(tables.rows("task")), 1)
        self.assertEqual(len(tables.rows("project")), 0)

    def test_the_entrance_answers_before_anybody_is_in_and_to_anybody(self):
        # `/api/session` is above the gate on purpose: it is the answer that
        # DRAWS the entrance, and the role has nothing to say about a door
        # somebody has not gone through yet.
        self.person("")
        _, _, body = self.get("/api/session", headers=self.cookie())
        self.assertEqual(json.loads(body)["actor"]["name"], self.NAME)
        self.assertEqual(self.status("/api/session"), 200)

    def test_an_actor_pointing_at_no_role_reaches_nothing(self):
        # The rule fails CLOSED: no role is a ceiling of nothing and never of
        # everything — which is also the `engine`'s row, born pointing at none.
        tables.create(
            "actor",
            {"name": "sem papel", "type": "person", "credential": self.CREDENTIAL},
        )
        status, _, _ = self.get("/api/state", headers=self.cookie("sem papel"))
        self.assertEqual(status, 403)

    def test_a_permission_the_catalogue_does_not_name_grants_nothing(self):
        # §4: a role that names a permission that does not exist does not bring
        # AT down — and it grants exactly what it names that DOES exist. The
        # unknown name is not a token that opens the rest.
        self.assertFalse(permissions.is_known("task:fly"))
        self.person("task:list,task:fly")
        cookie = self.cookie()
        self.assertEqual(self.status("/api/table/task", headers=cookie), 200)
        self.assertEqual(
            self.post(
                "/api/table/task", {"action": "create", "set": {"text": "x"}},
                headers=cookie,
            )[0],
            403,
        )

    def test_the_role_is_read_on_every_request(self):
        # The ceiling lives in the store and not in the session: a role edited
        # under a LIVE session is read on the next request, granted and taken
        # away both.
        person = self.person("task:list")
        cookie = self.cookie()
        self.assertEqual(self.status("/api/state", headers=cookie), 403)
        tables.edit(
            "role", person["role"], {"permissions": "task:list,setting:read"}
        )
        self.assertEqual(self.status("/api/state", headers=cookie), 200)
        tables.edit("role", person["role"], {"permissions": "task:list"})
        self.assertEqual(self.status("/api/state", headers=cookie), 403)

    def test_the_administrator_role_reaches_the_whole_api(self):
        # The positive control: the role born carrying the catalogue is the role
        # that reaches what the routes demand, and the ceiling does not close on
        # the person who administers.
        cookie = self.cookie(self.ADMIN, self.ADMIN_CREDENTIAL)
        for path in ("/api/state", "/api/projects", "/api/orphans", "/api/tree",
                     "/api/table/task"):
            with self.subTest(path=path):
                self.assertEqual(self.status(path, headers=cookie), 200)
        self.assertEqual(
            self.post(
                "/api/table/task", {"action": "create", "set": {"text": "x"}},
                headers=cookie,
            )[0],
            200,
        )
        self.assertEqual(self.post("/api/ask", {"text": "banana"}, headers=cookie)[0], 200)


class TheContextMenuActions(ServerCase):
    """TASK-120, fatia 1: what a context menu may show, and never invents (§4, item 11).

    `_table_actions` asks the SAME ceiling `_may` would refuse a write with —
    `actors.may`, over the permission `permissions.needed` composes — but reads
    it instead of gating a route: a menu that shows nothing is not a request
    that failed. Row-independent, and it is the system's own shape and not a
    shortcut: the role's ceiling is over the TABLE, so every record of one
    table answers alike, and this asks it once per payload and not once per
    row.
    """

    ADMIN = "Rafael"
    ADMIN_CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Leitor"
    CREDENTIAL = "outra-frase-bem-longa"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def person(self, carried: str, name: str | None = None) -> dict:
        role = tables.create(
            "role",
            {"name": f"papel-{len(store.load('role'))}", "permissions": carried},
        )
        return tables.create(
            "actor",
            {
                "name": name or self.NAME, "type": "person",
                "role": str(store.number_of(role)),
                "credential": self.CREDENTIAL,
            },
        )

    def cookie(self, name: str | None = None) -> dict:
        status, headers, _ = self.post_full(
            "/api/session", {"name": name or self.NAME, "credential": self.CREDENTIAL},
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def test_the_administrator_sees_the_full_set_the_table_structurally_allows(self):
        # TASK-122, fatia 3/7: `task` declares BOTH a `lifecycle` (a closing)
        # and no `deletable: false` (a deletion), so the administrator — who
        # carries the whole catalogue — sees the full four.
        status, headers, _ = self.post_full(
            "/api/session",
            {"name": self.ADMIN, "credential": self.ADMIN_CREDENTIAL},
        )
        self.assertEqual(status, 200)
        cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
        _, _, body = self.get("/api/table/task", headers=cookie)
        self.assertEqual(json.loads(body)["actions"], ["create", "edit", "cancel", "delete"])

    def test_a_role_that_carries_edit_sees_it(self):
        self.person("task:list,task:edit")
        _, _, body = self.get("/api/table/task", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["edit"])

    def test_a_role_that_carries_create_sees_it(self):
        # TASK-121: `create` joins `edit` in the SAME generic row menu, read
        # off the SAME ceiling — a role that carries one and not the other
        # sees only the one it carries.
        self.person("task:list,task:create")
        _, _, body = self.get("/api/table/task", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["create"])

    def test_a_role_that_does_not_carry_edit_sees_nothing(self):
        self.person("task:list")
        _, _, body = self.get("/api/table/task", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], [])

    def test_a_role_carrying_nothing_is_refused_by_the_route_before_the_menu(self):
        # `task:list` is the ROUTE's own demand (`_may`), asked before this
        # door's question ever runs — a role naming nothing does not reach
        # `_table_actions` at all, it is refused earlier and by the same rule.
        self.person("")
        code = self.status("/api/table/task", headers=self.cookie())
        self.assertEqual(code, 403)

    def test_a_role_that_carries_cancel_and_delete_sees_them(self):
        self.person("task:list,task:cancel,task:delete")
        _, _, body = self.get("/api/table/task", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["cancel", "delete"])

    def test_cancel_never_shows_on_a_table_with_no_lifecycle_even_when_carried(self):
        # `actor` declares no `lifecycle` at all — the permission is legal in
        # the catalogue (the engine's six are a permission each by default),
        # but the engine has no closing to perform. The structural question
        # comes BEFORE the ceiling, so a role carrying `actor:cancel` still
        # does not see it — the door the server would refuse never opens.
        self.person("actor:list,actor:cancel,actor:edit")
        _, _, body = self.get("/api/table/actor", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["edit"])

    def test_delete_never_shows_on_a_table_the_declaration_marks_not_deletable(self):
        # `audit` declares `deletable: false` — the same structural refusal,
        # read off `tables.deletable` the way `cancel`'s reads `lifecycle`.
        self.person("audit:read")
        _, _, body = self.get("/api/table/audit", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], [])

    def test_the_project_page_answers_the_same_way(self):
        with redirect_stdout(io.StringIO()):
            tables.create("project", {"name": "Autonomia", "status": "active"})
        self.person("task:list,project:view")
        _, _, body = self.get("/api/project/1", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], [])
        self.person("task:list,task:edit,project:view", "Editor")
        _, _, body = self.get("/api/project/1", headers=self.cookie("Editor"))
        self.assertEqual(json.loads(body)["actions"], ["edit"])

    def test_the_orphans_page_answers_the_same_way(self):
        self.person("task:list,task:edit")
        _, _, body = self.get("/api/orphans", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["edit"])

    def test_the_projects_tree_offers_create_and_edit_when_carried(self):
        # TASK-135: a DIFFERENT pair from the row menu's — `create` (a project
        # or a subproject) alongside `edit` (a rename or a move).
        self.person("project:list,project:create,project:edit")
        _, _, body = self.get("/api/projects", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], ["create", "edit"])

    def test_the_projects_tree_offers_nothing_the_role_does_not_carry(self):
        self.person("project:list")
        _, _, body = self.get("/api/projects", headers=self.cookie())
        self.assertEqual(json.loads(body)["actions"], [])


class TheRbacScreens(ServerCase):
    """The two routes the screens item 11 lands are made of: the closed list the
    role screen draws, and the door that MINTS and revokes a machine credential.

    The screens themselves are the page's; what the server owes them is here —
    the catalogue, the two facts a record has to carry (`unknown` and
    `has_credential`), and the demand each route is refused without.
    """

    ADMIN = "Rafael"
    ADMIN_CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Leitor"
    CREDENTIAL = "outra-frase-bem-longa"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def person(self, carried: str, name: str | None = None) -> dict:
        role = tables.create(
            "role",
            {"name": f"papel-{len(store.load('role'))}", "permissions": carried},
        )
        return tables.create(
            "actor",
            {"name": name or self.NAME, "type": "person",
             "role": str(store.number_of(role)), "credential": self.CREDENTIAL},
        )

    def cookie(self, name: str | None = None, credential: str | None = None) -> dict:
        """The `Cookie` of whoever is named — the ADMIN's by default, and the
        second person's by `self.cookie(self.NAME, self.CREDENTIAL)`."""
        status, headers, _ = self.post_full(
            "/api/session",
            {"name": name or self.ADMIN, "credential": credential or self.ADMIN_CREDENTIAL},
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def role_number(self) -> int:
        return store.number_of(actors.admin_role())

    # -- the closed list ----------------------------------------------------

    def test_it_hands_over_the_whole_closed_list(self):
        _, _, body = self.get("/api/catalogue", headers=self.cookie())
        entries = json.loads(body)["permissions"]
        self.assertEqual([entry["key"] for entry in entries], permissions.all_permissions())

    def test_every_entry_carries_the_words_and_the_risk(self):
        # The screen groups by OBJECT and writes the ACTION beside each check, so
        # the parts travel with the whole — the page cuts no label in two.
        _, _, body = self.get("/api/catalogue", headers=self.cookie())
        entry = next(
            one for one in json.loads(body)["permissions"] if one["key"] == "task:create"
        )
        self.assertEqual(entry["object"], "task")
        self.assertEqual(entry["object_label"], tables.table_name("task", many=True))
        self.assertEqual(entry["action_label"], i18n.tr("table.action.create"))
        self.assertEqual(entry["risk"], permissions.risk("task:create"))
        self.assertNotIn(entry["object_label"], ("permission.object.task", "task"))

    def test_an_entry_carries_the_modifiers_its_act_accepts(self):
        # TASK-189, fatia 4/4: `webapp:run` é a entrada com mais flags do
        # catálogo (`permissions.MODIFIERS`), e a árvore de Actions é o que
        # lê este campo para desenhá-los sob a entidade.
        _, _, body = self.get("/api/catalogue", headers=self.cookie())
        entry = next(
            one for one in json.loads(body)["permissions"] if one["key"] == "webapp:run"
        )
        self.assertEqual(
            [modifier["name"] for modifier in entry["modifiers"]],
            ["--port", "--public-port", "--host", "--no-caddy"],
        )
        self.assertEqual(entry["modifiers"][0]["kind"], "flag")
        self.assertEqual(entry["modifiers"][0]["label"], i18n.tr(permissions.MODIFIERS["webapp:run"][0].key))
        # `task:create` não aceita flag nem argumento: a lista vem vazia, não
        # ausente — a mesma forma que `permissions.modifiers` já devolve.
        plain = next(
            one for one in json.loads(body)["permissions"] if one["key"] == "task:create"
        )
        self.assertEqual(plain["modifiers"], [])

    def test_an_entry_carries_the_reach_and_the_orphan_mark(self):
        # TASK-189, fatia 4/4: a mesma marca que a auditoria (`actions_audit`,
        # fatia 3/4) já calcula, lida pela rota e não recalculada por ela.
        _, _, body = self.get("/api/catalogue", headers=self.cookie())
        entries = {one["key"]: one for one in json.loads(body)["permissions"]}
        reached = actions_audit.reach()
        orphaned = set(actions_audit.orphans())
        for key, entry in entries.items():
            self.assertEqual(entry["reach"], sorted(reached[key]))
            self.assertEqual(entry["orphan"], key in orphaned)
        # Nenhum ponto de verdade por desenho (`NO_INTERFACE_YET`) é dito órfão.
        for key in actions_audit.NO_INTERFACE_YET:
            self.assertFalse(entries[key]["orphan"])
            self.assertEqual(entries[key]["reach"], [])

    def test_reading_the_catalogue_is_reading_the_roles(self):
        self.person("task:list")
        status, _, body = self.get(
            "/api/catalogue", headers=self.cookie(self.NAME, self.CREDENTIAL)
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            json.loads(body)["error"],
            i18n.tr("permission.denied", permission=permissions.label("role:list")),
        )

    # -- what a record has to be TOLD ---------------------------------------

    def test_a_role_record_says_the_permission_the_catalogue_does_not_have(self):
        # §4: the role does not bring AT down, and the saying is what gets read.
        row = tables.create(
            "role", {"name": "meio", "permissions": "task:list,task:read"}
        )
        _, _, body = self.get("/api/table/role", headers=self.cookie())
        record = next(
            one for one in json.loads(body)["records"] if one["id"] == row["id"]
        )
        self.assertEqual(record["unknown"], ["task:read"])

    def test_a_role_that_names_only_what_exists_says_nothing(self):
        _, _, body = self.get("/api/table/role", headers=self.cookie())
        record = next(one for one in json.loads(body)["records"]
                      if one["id"] == store.number_of(actors.admin_role()))
        self.assertEqual(record["unknown"], [])

    def test_an_actor_record_says_whether_it_holds_a_credential(self):
        # The credential never travels as a value (`_stored`), so the boolean is
        # the whole of what the screen that mints and revokes can read.
        engine = tables.create("actor", {"name": self.NAME, "type": "agent"})
        _, _, body = self.get("/api/table/actor", headers=self.cookie())
        records = {one["id"]: one for one in json.loads(body)["records"]}
        self.assertTrue(records[store.number_of(actors.admins()[0])]["has_credential"])
        self.assertFalse(records[engine["id"]]["has_credential"])

    # -- the machine credential ---------------------------------------------

    def mint(self, cookie: dict, **body: object) -> tuple[int, dict]:
        return self.post("/api/agent", {"action": "mint", **body}, headers=cookie)

    def test_the_mint_draws_the_token_and_hands_it_over_once(self):
        status, answer = self.mint(self.cookie(), name="robô", role=self.role_number())
        self.assertEqual(status, 200)
        token = answer["token"]
        self.assertTrue(token)
        # The row keeps the derivation and never the token — the answer carries it
        # and no later read does.
        self.assertNotIn(token, json.dumps(answer["record"]))
        row = tables.rows("actor")[-1]
        self.assertNotIn(token, row["credential"])
        self.assertEqual(row["type"], "agent")

    def test_the_minted_token_opens_the_api_by_bearer(self):
        _, answer = self.mint(self.cookie(), name="robô", role=self.role_number())
        token = answer["token"]
        self.assertEqual(
            self.status("/api/state", headers={"Authorization": "Bearer " + token}), 200
        )
        self.assertEqual(
            self.status("/api/state", headers={"Authorization": "Bearer outra-coisa"}), 401
        )

    def test_the_mint_demands_the_create_of_the_actor(self):
        self.person("actor:list,actor:edit")
        status, answer = self.mint(
            self.cookie(self.NAME, self.CREDENTIAL), name="robô", role=self.role_number()
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            answer["error"],
            i18n.tr("permission.denied", permission=permissions.label("actor:create")),
        )
        self.assertEqual(actors.agents(), [])

    def test_a_role_nobody_wears_is_refused_by_name(self):
        status, answer = self.mint(self.cookie(), name="robô", role=99)
        self.assertEqual(status, 400)
        self.assertEqual(answer["error"], i18n.tr("machine.error.role_unknown", role=99))
        self.assertEqual(actors.agents(), [])

    def test_a_new_token_replaces_the_one_that_was(self):
        _, first = self.mint(self.cookie(), name="robô", role=self.role_number())
        row = actors.agents()[0]
        status, second = self.mint(self.cookie(), id=row["id"])
        self.assertEqual(status, 200)
        self.assertNotEqual(first["token"], second["token"])
        self.assertEqual(
            self.status("/api/state", headers={"Authorization": "Bearer " + first["token"]}),
            401,
        )
        self.assertEqual(
            self.status("/api/state", headers={"Authorization": "Bearer " + second["token"]}),
            200,
        )
        self.assertEqual(len(actors.agents()), 1)

    def test_revoking_closes_the_door_and_leaves_the_row(self):
        _, answer = self.mint(self.cookie(), name="robô", role=self.role_number())
        row = actors.agents()[0]
        status, _ = self.post("/api/agent", {"action": "revoke", "id": row["id"]},
                              headers=self.cookie())
        self.assertEqual(status, 200)
        self.assertEqual(
            self.status("/api/state", headers={"Authorization": "Bearer " + answer["token"]}),
            401,
        )
        self.assertEqual(len(actors.agents()), 1)
        self.assertEqual(actors.agent_row(row["id"])["credential"], "")

    def test_the_revoke_demands_the_edit_of_the_actor(self):
        self.mint(self.cookie(), name="robô", role=self.role_number())
        row = actors.agents()[0]
        self.person("actor:list")
        status, answer = self.post(
            "/api/agent", {"action": "revoke", "id": row["id"]},
            headers=self.cookie(self.NAME, self.CREDENTIAL),
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            answer["error"],
            i18n.tr("permission.denied", permission=permissions.label("actor:edit")),
        )
        self.assertTrue(actors.agent_row(row["id"])["credential"])

    def test_a_person_is_not_a_machine(self):
        person = actors.admins()[0]
        status, answer = self.post("/api/agent", {"action": "revoke", "id": person["id"]},
                                   headers=self.cookie())
        self.assertEqual(status, 400)
        self.assertEqual(
            answer["error"],
            i18n.tr("machine.error.not_agent", id=person["id"]),
        )
        self.assertIsNotNone(actors.authenticate(self.ADMIN, self.ADMIN_CREDENTIAL))

    def test_an_unknown_action_is_a_bad_request(self):
        self.assertEqual(
            self.post("/api/agent", {"action": "fly"}, headers=self.cookie())[0], 400
        )

    def test_the_machine_door_obeys_the_guards_of_every_other_write(self):
        status, _ = self.post(
            "/api/agent",
            {"action": "mint", "name": "robô", "role": self.role_number()},
            headers={**self.cookie(), "Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(actors.agents(), [])


class TheAskCeiling(ServerCase):
    """`POST /api/ask` under a role — the interpreter's door carries the ceiling.

    §5: "o que ela pode propor é o que ela já pode fazer". The route demands
    `nlu:ask`, and the PROPOSAL demands the permission the action on the table
    is; the door is the same one the balloon, the chat and `at-cli ask` read, so
    the refusal lands on every surface at once (`at.ui.ask`).
    """

    ADMIN = "Rafael"
    ADMIN_CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Leitor"
    CREDENTIAL = "outra-frase-bem-longa"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def person(self, carried: str) -> dict:
        role = tables.create(
            "role",
            {"name": f"papel-{len(store.load('role'))}", "permissions": carried},
        )
        return tables.create(
            "actor",
            {"name": self.NAME, "type": "person",
             "role": str(store.number_of(role)), "credential": self.CREDENTIAL},
        )

    def cookie(self, name: str | None = None, credential: str | None = None) -> dict:
        status, headers, _ = self.post_full(
            "/api/session",
            {"name": name or self.NAME, "credential": credential or self.CREDENTIAL},
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def test_the_ask_without_the_write_is_refused_and_writes_nothing(self):
        self.person("nlu:ask,task:list")
        status, answer = self.post(
            "/api/ask", {"text": "cria uma tarefa pra hoje"}, headers=self.cookie()
        )
        self.assertEqual(status, 200)  # a refusal is an ANSWER, not a failed request
        self.assertEqual(answer["kind"], "refused")
        self.assertIsNone(answer["proposal"])
        self.assertEqual(
            answer["text"],
            i18n.tr("permission.denied", permission=permissions.label("task:create")),
        )
        self.assertEqual(len(tables.rows("task")), 1)  # nothing was written

    def test_the_act_the_role_carries_runs(self):
        self.person("nlu:ask,task:create")
        status, answer = self.post(
            "/api/ask", {"text": "cria uma tarefa pra hoje"}, headers=self.cookie()
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertEqual(len(tables.rows("task")), 2)

    def test_reading_is_capped_like_writing(self):
        self.person("nlu:ask")
        _, answer = self.post("/api/ask", {"text": "lista as tarefas"}, headers=self.cookie())
        self.assertEqual(answer["kind"], "refused")
        self.assertEqual(
            answer["text"],
            i18n.tr("permission.denied", permission=permissions.label("task:list")),
        )

    def test_the_administrator_is_not_capped(self):
        cookie = self.cookie(self.ADMIN, self.ADMIN_CREDENTIAL)
        status, answer = self.post(
            "/api/ask", {"text": "cria uma tarefa pra hoje"}, headers=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")

    def test_the_missing_ask_is_the_route_that_refuses_it(self):
        self.person("task:create")
        status, answer = self.post(
            "/api/ask", {"text": "cria uma tarefa pra hoje"}, headers=self.cookie()
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            answer["error"],
            i18n.tr("permission.denied", permission=permissions.label("nlu:ask")),
        )
        self.assertEqual(len(tables.rows("task")), 1)


class TheAskWithoutAnActor(ServerCase):
    """A folder that asks nobody has no actor — and no ceiling either.

    It is §3's own sentence: with no authentication configured AT listens on
    loopback and asks nothing, so the interpreter's door answers as it always
    did. The `cli` asks by the same door and with the same nobody.
    """

    def test_the_interpreter_proposes_and_runs(self):
        status, answer = self.post("/api/ask", {"text": "cria uma tarefa pra hoje"})
        self.assertEqual(status, 200)
        self.assertEqual(answer["kind"], "answer")
        self.assertEqual(len(tables.rows("task")), 2)


class TheFolderWithNobodyToAsk(ServerCase):
    """The folder with no credential to prove asks nothing — and answers.

    It is §3's own sentence — "sem nenhuma forma de autenticação configurada, o
    AT escuta apenas 127.0.0.1" — and it is the state every other test in this
    file runs in. What it is NOT is an entrance: a door drawn there would be one
    nobody could open, and the page tells the two apart by `auth`.
    """

    def test_it_says_it_asks_nobody(self):
        _, _, body = self.get("/api/session")
        answer = json.loads(body)
        self.assertIs(answer["auth"], False)
        self.assertIsNone(answer["actor"])

    def test_the_api_answers_with_nobody_to_ask(self):
        self.assertEqual(self.status("/api/state"), 200)
        self.assertEqual(self.status("/api/table/task"), 200)


class TheDevServer(ServerCase):
    """The server a run from the source tree builds: it asks nobody in.

    It is the SAME harness every other class here uses, with the one difference
    that matters — `asks=False`, which is what `run` hands it when the artifact
    IS the checkout (`paths.source`). Everything else about the folder is
    untouched, and that is the point: the admin is still there, the tables are
    still the tables, and nobody has to prove who they are to read them.

    What it is NOT is an open door: the folder has no entrance to open. That is
    what the API answers, and what the page reads to draw the shell instead of
    the form.
    """

    server_args = {"asks": False}

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", "uma-frase-bem-longa")

    def test_the_entrance_says_it_draws_none(self):
        _, _, body = self.get("/api/session")
        answer = json.loads(body)
        self.assertIs(answer["auth"], False)
        self.assertIsNone(answer["actor"])

    def test_the_api_answers_with_no_session(self):
        # The folder HAS a person to prove themselves — and asking them is
        # exactly what this server does not do.
        self.assertTrue(actors.can_expose())
        self.assertEqual(self.status("/api/state"), 200)
        self.assertEqual(self.status("/api/table/task"), 200)

    def test_the_ceiling_is_nobody(self):
        # No actor was proved, so no role was read: what a person carries is
        # what the gate is FOR, and a gate that asked nobody has nothing to
        # measure. The write is allowed because it was never gated.
        status, _ = self.post("/api/table/task", {"action": "create", "values": {"text": "outra"}})
        self.assertEqual(status, 200)
        self.assertEqual(len(tables.rows("task")), 2)


class TheArtifact(unittest.TestCase):
    """The switch between the checkout and the bundle — `paths.source`.

    It is a property of the ARTIFACT and not of a flag (`paths.source` says
    why), so the test moves the artifact and not a switch.
    """

    def test_the_checkout_is_the_source_and_the_bundle_is_not(self):
        self.assertTrue(paths.source())
        with bundle():
            self.assertFalse(paths.source())


class TheExposure(unittest.TestCase):
    """`at-cli webapp` in a folder with nobody to enter it.

    "Sem ator nenhum o AT não expõe" (§3): the engine's row does not count — it
    does not enter, the person does (`actors.can_expose`) — and the refusal is
    about an ENTRANCE, so it is asked of a run that has one: the bundle, which is
    what `bundle()` makes this process for the length of a test.

    **E a regra é sobre o ENDEREÇO, e não sobre subir** (TASK-176, fatia 3/3):
    a primeira subida é uma página, então o processo sobe — mas só no laço. Um
    `--host` que não o laço é a recusa, e o Caddy é a mesma exposição por outra
    porta (`include_caddy` publica na rede, ainda que o WebApp escute no laço).
    """

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def test_a_folder_with_no_person_does_not_expose_off_the_loop(self):
        output = io.StringIO()
        with bundle(), redirect_stdout(output):
            code = webapp.run(0, host="0.0.0.0")
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("webapp.no_admin"), output.getvalue())

    def test_the_caddy_is_the_same_exposure_and_is_refused_too(self):
        # `include_caddy` põe a borda na frente de um WebApp que escuta no
        # laço: o que a pessoa alcança é a REDE, e é a mesma exposição que o
        # `--host` compraria. Sem ator nenhum, ela não acontece.
        output = io.StringIO()
        with bundle(), redirect_stdout(output):
            code = webapp.run(0, include_caddy=True)
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("webapp.no_admin"), output.getvalue())

    def test_on_the_loop_it_comes_up_to_serve_the_first_run(self):
        # A primeira subida é uma PÁGINA (TASK-176, fatia 3/3): o formulário que
        # cria o primeiro administrador é uma tela desta casa, e para ele
        # existir o processo tem de estar de pé. `serve_forever` é o que uma
        # subida nunca deixa, e o Ctrl-C é o fim dela — o mesmo fim sem uma
        # porta presa para o teste.
        output = io.StringIO()
        with bundle(), mock.patch.object(
            webapp.Server, "serve_forever", side_effect=KeyboardInterrupt
        ), redirect_stdout(output):
            code = webapp.run(0, include_caddy=False)
        self.assertEqual(code, 0)
        self.assertIn("http://127.0.0.1:0", output.getvalue())

    def test_the_loop_is_read_as_an_address_and_not_as_a_string(self):
        # `localhost` é o laço por declaração; `127.0.0.7` e `::1` são o laço
        # pela régua dos endereços. E um NOME que não é nenhum dos dois não é o
        # laço: esta é a porta que não tem como saber quem mora atrás dele.
        for name in ("localhost", "127.0.0.1", "127.0.0.7", "::1"):
            with self.subTest(name=name):
                self.assertTrue(webapp.loopback(name))
        for name in ("0.0.0.0", "192.168.1.10", "at.local", "", "example.com"):
            with self.subTest(name=name):
                self.assertFalse(webapp.loopback(name))

    def test_a_run_from_the_source_does_not_refuse_and_says_why(self):
        # Running from the checkout there is no entrance to close, so the coin
        # of "no actor yet" — the one thing an install does not have on its
        # first minute — does not stand between the person and the page. What
        # the command owes them is the sentence saying so.
        output = io.StringIO()
        # `serve_forever` is what a run never leaves; Ctrl-C is how it ends, and
        # raising it here is the same ending without a port held for the test.
        with mock.patch.object(webapp.Server, "serve_forever", side_effect=KeyboardInterrupt):
            with redirect_stdout(output):
                code = webapp.run(0, include_caddy=False)
        self.assertEqual(code, 0)
        self.assertIn(i18n.tr("webapp.source_open"), output.getvalue())

    def test_the_person_makes_the_folder_expose_it(self):
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.assertTrue(actors.can_expose())


class ThePort(unittest.TestCase):
    """`at-cli webapp` when somebody else already answers on that port.

    It is the way the command fails in practice — the PoC on 12345, or a second
    AT — and what the person used to get was a bare `OSError: Address already
    in use`, which names neither the port nor a way out.
    """

    def setUp(self):
        # The port is answered only in a folder that has somebody to enter it:
        # the exposure refusal comes BEFORE the server is built, so a folder
        # without an administrator would answer with that and never reach the
        # port this test is about.
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        actors.create_admin("Rafael", "uma-frase-bem-longa")

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def test_a_taken_port_is_named_instead_of_dying_raw(self):
        holder = socket.socket()
        holder.bind((webapp.HOST, 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                code = webapp.run(port, include_caddy=False)
        finally:
            holder.close()
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("webapp.port_taken", port=port), output.getvalue())

    def test_a_port_answering_at_the_same_version_names_nothing_to_do(self):
        with _answering(webapp.__version__) as port:
            output = io.StringIO()
            with redirect_stdout(output):
                code = webapp.run(port, include_caddy=False)
        self.assertEqual(code, 1)
        self.assertIn(
            i18n.tr("webapp.instance_up", url=f"http://{webapp.HOST}:{port}",
                     version=webapp.__version__),
            output.getvalue(),
        )

    def test_a_port_answering_ahead_says_to_update_this_at_cli(self):
        with _answering("9.9.9") as port:
            output = io.StringIO()
            with redirect_stdout(output):
                code = webapp.run(port, include_caddy=False)
        self.assertEqual(code, 1)
        self.assertIn(
            i18n.tr("webapp.instance_ahead", url=f"http://{webapp.HOST}:{port}",
                     theirs="9.9.9", mine=webapp.__version__),
            output.getvalue(),
        )

    def test_a_port_answering_behind_names_at_deploy_update(self):
        with _answering("0.0.1") as port:
            output = io.StringIO()
            with redirect_stdout(output):
                code = webapp.run(port, include_caddy=False)
        self.assertEqual(code, 1)
        self.assertIn(
            i18n.tr("webapp.instance_behind", url=f"http://{webapp.HOST}:{port}",
                     theirs="0.0.1", mine=webapp.__version__),
            output.getvalue(),
        )
        # No `at-deploy` in this folder, so the second exit is offered too —
        # never fetched, only named.
        self.assertIn(
            i18n.tr("webapp.instance_behind_no_deploy", deploy=paths.deploy_file()),
            output.getvalue(),
        )

    def test_a_port_answering_behind_says_nothing_more_with_at_deploy_present(self):
        (paths.working_folder() / paths.deploy_file()).touch()
        with _answering("0.0.1") as port:
            output = io.StringIO()
            with redirect_stdout(output):
                webapp.run(port, include_caddy=False)
        self.assertNotIn(
            i18n.tr("webapp.instance_behind_no_deploy", deploy=paths.deploy_file()),
            output.getvalue(),
        )

    def test_a_port_answering_something_that_is_not_at_falls_back(self):
        # A body that does not carry `version` is not this AT — the door
        # `/api/session` never answers without it — so the plain refusal is
        # what a stray server on the port gets.
        class NotAT(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                body = json.dumps({"ok": True}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer((webapp.HOST, 0), NotAT)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                code = webapp.run(port, include_caddy=False)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        self.assertEqual(code, 1)
        self.assertIn(i18n.tr("webapp.port_taken", port=port), output.getvalue())


@contextmanager
def _answering(version: str):
    """A bare HTTP server standing in for another AT, answering `/api/session`
    with a version of the caller's choosing — never this process's own, so
    the three orders `_report_taken` decides between can each be driven."""

    class Answering(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps({"version": version}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer((webapp.HOST, 0), Answering)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class TheAuditRoute(ServerCase):
    """The page's half of the log (§3, item 15).

    The page walks the SAME door the `cli` and the interpreter walk, so a write
    made here leaves the same kind of line — with `webapp` as its VIA and the
    session's actor as its WHO — and the route reads it through the ceiling the
    catalogue declares, `audit:read`.
    """

    ADMIN = "Rafael"
    ADMIN_CREDENTIAL = "uma-frase-bem-longa"

    def setUp(self):
        super().setUp()
        self.admin = actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def cookie(self, name: str | None = None, credential: str | None = None) -> dict:
        status, headers, _ = self.post_full(
            "/api/session",
            {"name": name or self.ADMIN,
             "credential": credential or self.ADMIN_CREDENTIAL},
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def lines(self) -> list[dict]:
        return store.load("audit")

    def test_a_write_through_the_page_leaves_one_line_with_the_page_s_via(self):
        status, _ = self.post(
            "/api/table/task",
            {"action": "create", "set": {"text": "do painel"}},
            headers=self.cookie(),
        )
        self.assertEqual(status, 200)
        line = self.lines()[0]
        self.assertEqual(line[audit.WHAT], "task:create")
        self.assertEqual(line[audit.VIA], audit.WEBAPP)
        self.assertEqual(line[audit.STATUS], audit.OK)
        self.assertEqual(line[audit.ACTOR], store.number_of(self.admin))

    def test_the_administrator_reads_the_log(self):
        # The route reads the permission from the CATALOGUE and does not compose
        # `audit:list`, which the catalogue does not name: the table narrows
        # itself to `read`, and a composed name would fail CLOSED on the very
        # person the catalogue says reads it.
        self.assertEqual(self.status("/api/table/audit", headers=self.cookie()), 200)

    def test_the_page_cannot_write_a_line_of_its_own(self):
        # `audit` answers `read` and nothing else, so there is no `audit:create`
        # for anybody to carry — and the attempt is itself a line: the refusal of
        # the ceiling.
        status, _ = self.post(
            "/api/table/audit",
            {"action": "create", "set": {"what": "task:create"}},
            headers=self.cookie(),
        )
        self.assertEqual(status, 403)
        self.assertEqual([line[audit.STATUS] for line in self.lines()], [audit.REFUSED])
        self.assertEqual(self.lines()[0][audit.REASON], audit.DENIED)

    def test_a_write_the_ceiling_refused_is_a_line(self):
        role = tables.create("role", {"name": "leitor", "permissions": "task:list"})
        tables.create(
            "actor",
            {"name": "Leitor", "type": "person",
             "role": str(store.number_of(role)), "credential": "outra-frase-bem-longa"},
        )
        cookie = self.cookie("Leitor", "outra-frase-bem-longa")
        status, _ = self.post(
            "/api/table/task", {"action": "create", "set": {"text": "x"}}, headers=cookie
        )
        self.assertEqual(status, 403)
        line = self.lines()[0]
        self.assertEqual(line[audit.STATUS], audit.REFUSED)
        self.assertEqual(line[audit.REASON], audit.DENIED)
        self.assertEqual(line[audit.WHAT], "task:create")
        self.assertEqual(line[audit.VIA], audit.WEBAPP)

    def test_a_person_without_the_permission_is_refused_by_name(self):
        role = tables.create("role", {"name": "leitor", "permissions": "task:list"})
        tables.create(
            "actor",
            {"name": "Leitor", "type": "person",
             "role": str(store.number_of(role)), "credential": "outra-frase-bem-longa"},
        )
        status, _, body = self.get(
            "/api/table/audit",
            headers=self.cookie("Leitor", "outra-frase-bem-longa"),
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            json.loads(body)["error"],
            i18n.tr("permission.denied", permission=permissions.label("audit:read")),
        )

    def test_a_machine_is_refused_the_log_by_name(self):
        # §3: a machine that could read its own refusals would learn where the
        # wall is. The token proves the row and the row wears a role — and that
        # role names no `audit:read`.
        role = tables.create("role", {"name": "runner", "permissions": "task:create"})
        _, token = actors.mint_agent("runner", str(store.number_of(role)))
        status, _, body = self.get(
            "/api/table/audit", headers={"Authorization": "Bearer " + token}
        )
        self.assertEqual(status, 403)
        self.assertEqual(
            json.loads(body)["error"],
            i18n.tr("permission.denied", permission=permissions.label("audit:read")),
        )

    def test_a_machine_s_demand_at_the_bar_is_answered_as_a_job(self):
        # §4, item 15: the demand that cannot run becomes a row of `jobs`, and
        # the answer names it. The route answers what HAPPENED instead of a
        # record — nothing was written — and it is not an error either, because
        # the act was neither written nor refused. A person's demand never
        # reaches this answer: the act they type IS the approval.
        #
        # The demand is an `actor:edit` handing out a role, which the catalogue
        # prices at `0.95` — the argument that raises it is the whole point of
        # the per-argument declaration, and it is above any default bar.
        role = tables.create("role", {"name": "runner", "permissions": "actor:edit"})
        _, token = actors.mint_agent("runner", str(store.number_of(role)))
        status, _, body = self.post_full(
            "/api/table/actor",
            {"action": "edit", "id": 1, "set": {"role": 1}},
            headers={"Authorization": "Bearer " + token},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["held"])
        self.assertEqual(body["answer"], i18n.tr("job.waits", id="JOB-1"))
        self.assertEqual(store.load("job")[0]["status"], "waiting")
        self.assertEqual(self.lines(), [])

    def test_a_read_through_the_page_leaves_nothing(self):
        cookie = self.cookie()
        self.get("/api/table/task", headers=cookie)
        self.get("/api/state", headers=cookie)
        self.assertEqual(self.lines(), [])


class TheReadOnlySwitch(ServerCase):
    def test_the_page_cannot_write_when_the_switch_is_on(self):
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            status, answer = self.post("/api/table/task",
                                       {"action": "create", "set": {"text": "x"}})
        self.assertEqual(status, 403)
        self.assertIn("error", answer)
        self.assertEqual(len(tables.rows("task", show_all=True)), 1)


class TheNotificationRoute(ServerCase):
    """A rota que lê o que o AT já avisou (TASK-176, 3/3; Web Push desde que o
    ntfy saiu).

    **Não há mais tópico remoto nem credencial.** Quem guarda o que saiu é o
    próprio AT, no `INBOX` do Web Push (`core.notifier.read`), e a rota só o
    entrega à página. O seam é o próprio `notifier.read`: o que o teste mede é
    o que a rota devolve — e que nada de credencial volta, porque não existe
    credencial nenhuma aqui.
    """

    CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Rafael"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)
        self.answer()

    def answer(self, messages: list | None = None) -> None:
        """O que o motor responde à rota."""
        held = messages if messages is not None else []

        def read(key=None):
            return held, ""

        patch = mock.patch.object(notifier, "read", read)
        patch.start()
        self.addCleanup(patch.stop)

    def session(self) -> dict:
        status, headers, _ = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL}
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def test_the_read_is_called_with_no_key(self):
        # A leitura não tem chave: o Web Push não sela nada com a chave
        # derivada, então a rota chama `read()` sem argumento nenhum.
        calls: list = []

        def read(*args, **kwargs):
            calls.append((args, kwargs))
            return [], ""

        with mock.patch.object(notifier, "read", read):
            status, _, raw = self.get("/api/notifications", headers=self.session())
        self.assertEqual(status, 200)
        self.assertEqual(calls, [((), {})])
        self.assertEqual(json.loads(raw), {"messages": []})

    def test_the_messages_are_what_the_route_answers(self):
        self.answer(messages=[{"id": "a", "time": 7, "title": "AT",
                               "message": "oi"}])
        status, _, raw = self.get("/api/notifications", headers=self.session())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {"messages": [
            {"id": "a", "time": 7, "title": "AT", "message": "oi"},
        ]})

    def test_the_credential_never_reaches_the_page(self):
        # O que a rota devolve são as MENSAGENS, e nada de segredo junto.
        status, _, raw = self.get("/api/notifications", headers=self.session())
        self.assertEqual(status, 200)
        self.assertNotIn(b"tk_", raw)
        self.assertNotIn(b"Bearer", raw)

    def test_without_a_session_it_is_refused_like_every_other_read(self):
        self.assertEqual(self.status("/api/notifications"), 401)

    def test_the_role_that_does_not_carry_it_is_refused(self):
        # A demanda é a da ROTA (`notifier:read`), como em toda rota daqui: um
        # papel sem ela não lê os avisos, e a recusa é a da casa (403).
        role = tables.create("role", {"name": "leitor", "permissions": ["task:list"]})
        tables.create("actor", {"name": "outro", "type": "person",
                                "role": str(store.number_of(role)),
                                "credential": "outra frase bem longa"})
        status, headers, _ = self.post_full(
            "/api/session", {"name": "outro", "credential": "outra frase bem longa"}
        )
        self.assertEqual(status, 200)
        cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
        self.assertEqual(self.status("/api/notifications", headers=cookie), 403)

    def test_the_catalogue_names_the_object_and_the_read(self):
        self.assertTrue(permissions.is_known("notifier:read"))
        self.assertNotIn("notifier:write", permissions.all_permissions())


class ThePushRoutes(ServerCase):
    """As duas rotas do Web Push: a chave pública do VAPID e a inscrição.

    O que o navegador precisa para se inscrever é a chave PÚBLICA — o par
    privado nunca sai da pasta —, e o que ele devolve depois é a inscrição, que
    o AT guarda para cifrar cada aviso contra ela.
    """

    CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Rafael"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)

    def session(self) -> dict:
        status, headers, _ = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL}
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def subscription(self) -> dict:
        # A rota só GUARDA a inscrição — quem valida a curva é o envio —, então
        # as duas chaves só precisam estar lá.
        return {"endpoint": "https://push.example/xyz",
                "keys": {"p256dh": "AAAA", "auth": "BBBB"}}

    def test_the_public_key_is_served(self):
        from at.core import push
        status, _, raw = self.get("/api/push/key", headers=self.session())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {"key": push.public_key()})

    def test_a_subscription_is_stored(self):
        from at.core import push
        status, _, raw = self.post_full(
            "/api/push/subscribe", self.subscription(), headers=self.session()
        )
        self.assertEqual(status, 200)
        self.assertTrue(raw["ok"])
        self.assertEqual([entry["endpoint"] for entry in push.subscriptions()],
                         ["https://push.example/xyz"])

    def test_a_body_that_is_not_a_subscription_is_refused(self):
        status, _, raw = self.post_full(
            "/api/push/subscribe", {"endpoint": "x"}, headers=self.session()
        )
        self.assertEqual(status, 400)

    def test_without_a_session_the_key_is_refused(self):
        self.assertEqual(self.status("/api/push/key"), 401)


class TheFirstRun(ServerCase):
    """A primeira subida: a pasta sem administrador serve a PÁGINA que o cria.

    TASK-176, fatia 3/3. O estado é o da pasta que nasceu agora — o `ServerCase`
    não cria admin nenhum de propósito —, e o que a página lê para desenhar o
    formulário é `first`, que é a mesma pergunta (`actors.admins()`) que
    `at-cli admin` recusa por (`admin.exists`). As palavras são as do bloco
    `admin` do catálogo: a tela e o terminal dizem as MESMAS strings.
    """

    NAME = "rafael"
    CREDENTIAL = "uma frase bem longa"

    def test_the_entry_says_the_folder_has_no_administrator(self):
        _, _, body = self.get("/api/session")
        answer = json.loads(body)
        self.assertIs(answer["first"], True)
        # Sem ator nenhum `auth` é falso — é o que `_asks` já dizia —, e `first`
        # é o que a página lê para saber que a tela é a que CRIA o primeiro.
        self.assertIs(answer["auth"], False)
        self.assertIsNone(answer["actor"])

    def test_the_entry_carries_the_words_the_word_of_the_cli_uses(self):
        _, _, body = self.get("/api/session")
        labels = json.loads(body)["labels"]
        self.assertEqual(
            labels["admin.name"]["pt_BR"], "Nome do administrador"
        )
        self.assertEqual(labels["admin.credential"]["pt_BR"], "Chave Principal")
        # O piso viaja JÁ ESCRITO, e o número é o do motor — a página não decide
        # a regra nem a repete; a frase é a mesma que a recusa do `at-cli admin`.
        self.assertIn(
            str(actors.MIN_CREDENTIAL), labels["admin.error.short"]["pt_BR"]
        )

    def test_it_creates_the_first_administrator_and_opens_the_session(self):
        status, headers, answer = self.post_full(
            "/api/first",
            {"name": self.NAME, "credential": self.CREDENTIAL,
             "again": self.CREDENTIAL},
        )
        self.assertEqual(status, 200)
        self.assertEqual(answer["actor"]["name"], self.NAME)
        self.assertEqual(len(actors.admins()), 1)
        # A sessão vem na MESMA resposta: quem acabou de digitar a Chave
        # Principal já provou quem é, e pedi-la de novo seria cobrar duas vezes.
        cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
        self.assertEqual(self.status("/api/state", headers=cookie), 200)

    def test_the_same_string_proves_the_admin_and_unlocks_the_vault(self):
        # A promessa inteira do item, medida de ponta a ponta por esta porta: a
        # linha guarda o HASH da string, e é ela que abre o Cofre.
        self.post("/api/first",
                  {"name": self.NAME, "credential": self.CREDENTIAL,
                   "again": self.CREDENTIAL})
        row = actors.admins()[0]
        self.assertNotEqual(row.get("credential"), self.CREDENTIAL)
        self.assertTrue(actors.authenticate(self.NAME, self.CREDENTIAL))
        self.assertIsNotNone(vault.vault_key(self.CREDENTIAL))

    def test_the_key_below_the_floor_is_refused_in_the_engines_words(self):
        status, answer = self.post(
            "/api/first",
            {"name": self.NAME, "credential": "curta", "again": "curta"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(answer["error"],
                         i18n.tr("admin.error.short", min=actors.MIN_CREDENTIAL))
        self.assertEqual(actors.admins(), [])

    def test_the_two_reads_that_are_not_the_same_are_refused(self):
        status, answer = self.post(
            "/api/first",
            {"name": self.NAME, "credential": self.CREDENTIAL,
             "again": self.CREDENTIAL + "x"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(answer["error"], i18n.tr("admin.error.mismatch"))
        self.assertEqual(actors.admins(), [])

    def test_the_folder_that_already_has_one_is_refused_by_name(self):
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        status, answer = self.post(
            "/api/first",
            {"name": self.NAME, "credential": self.CREDENTIAL,
             "again": self.CREDENTIAL},
        )
        self.assertEqual(status, 403)
        self.assertEqual(answer["error"],
                         i18n.tr("admin.exists", name="Rafael"))
        self.assertEqual(len(actors.admins()), 1)

    def test_once_it_exists_the_entry_stops_offering_the_first_run(self):
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        _, _, body = self.get("/api/session")
        self.assertIs(json.loads(body)["first"], False)

    def test_a_request_that_did_not_come_over_the_loop_is_refused(self):
        # §3: sem ator nenhum o AT não expõe. Esta é a única rota que escreve
        # sem sessão e sem portão, então é a que mais precisa responder a quem
        # está do outro lado do fio — e a resposta é a MESMA frase que o comando
        # diz quando se recusa a sair do laço.
        with mock.patch.object(webapp, "loopback", return_value=False):
            status, answer = self.post(
                "/api/first",
                {"name": self.NAME, "credential": self.CREDENTIAL,
                 "again": self.CREDENTIAL},
            )
        self.assertEqual(status, 403)
        self.assertEqual(answer["error"], i18n.tr("webapp.no_admin"))
        self.assertEqual(actors.admins(), [])

    def test_the_run_from_the_source_tree_offers_no_first_run(self):
        # Uma subida que não pergunta NADA não tem primeira subida a desenhar
        # pela mesma razão que não tem entrada: não há porta, então não há o que
        # abrir. Nessa pasta a palavra continua sendo a da `cli`, que não depende
        # de porta nenhuma — e é o que `TheDevServer` é, com `asks=False`.
        dev = webapp.entry_payload(None, asks=False)
        self.assertIs(dev["first"], False)
        self.assertIs(dev["auth"], False)


class TheDerivedKeys(unittest.TestCase):
    """§4, item 50: the derived keys `at_deploy` hands the container, read once."""

    def setUp(self):
        self._held = dict(webapp_keys._keys)
        webapp_keys._keys.clear()
        self.addCleanup(webapp_keys._keys.clear)
        self.addCleanup(webapp_keys._keys.update, self._held)

    def test_boot_reads_every_variable_and_pops_them_from_the_environment(self):
        webapp_key = b"w" * 32
        notifier_key = b"n" * 32
        strongbox_key = b"c" * 32
        env = {
            webapp_keys.WEBAPP_KEY_ENV: base64.urlsafe_b64encode(webapp_key).decode(),
            webapp_keys.NOTIFIER_KEY_ENV: base64.urlsafe_b64encode(notifier_key).decode(),
            webapp_keys.STRONGBOX_KEY_ENV: base64.urlsafe_b64encode(strongbox_key).decode(),
        }
        with mock.patch.dict(os.environ, env):
            webapp_keys.boot()
            self.assertNotIn(webapp_keys.WEBAPP_KEY_ENV, os.environ)
            self.assertNotIn(webapp_keys.NOTIFIER_KEY_ENV, os.environ)
            self.assertNotIn(webapp_keys.STRONGBOX_KEY_ENV, os.environ)
        self.assertEqual(webapp_keys.webapp_key(), webapp_key)
        self.assertEqual(webapp_keys.notifier_key(), notifier_key)
        self.assertEqual(webapp_keys.strongbox_key(), strongbox_key)

    def test_a_process_that_never_got_a_variable_has_no_key(self):
        # Nem variável, nem Chave Principal (nem no ambiente, nem no arquivo da
        # máquina) — isolado do que `~/.config/at/AT_MAIN_KEY` guarda de
        # verdade em quem roda a suíte, senão o Cofre derivaria dali.
        with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(webapp_keys, "_main_key_from_file", return_value=None):
            os.environ.pop(webapp_keys.MAIN_KEY_ENV, None)
            os.environ.pop(webapp_keys.WEBAPP_KEY_ENV, None)
            os.environ.pop(webapp_keys.NOTIFIER_KEY_ENV, None)
            os.environ.pop(webapp_keys.STRONGBOX_KEY_ENV, None)
            webapp_keys.boot()
        self.assertIsNone(webapp_keys.webapp_key())
        self.assertIsNone(webapp_keys.notifier_key())
        self.assertIsNone(webapp_keys.strongbox_key())

    def test_a_process_with_the_main_key_derives_the_strongbox_on_its_own(self):
        # O caminho hospedado não tem `AT_STRONGBOX_KEY` pronta (só o container
        # deriva por fora, em `_webapp_env`) — então, com a Chave Principal e
        # sem a variável, `boot` deriva a chave do Cofre ela mesma.
        main_key = "uma-frase-bem-longa-o-bastante"
        with mock.patch.dict(os.environ, {webapp_keys.MAIN_KEY_ENV: main_key}):
            os.environ.pop(webapp_keys.STRONGBOX_KEY_ENV, None)
            webapp_keys.boot()
        expected = vault.derived_key(vault.vault_key(main_key), strongbox.SCOPE)
        self.assertEqual(webapp_keys.strongbox_key(), expected)

    def test_a_container_scoped_variable_is_never_overridden_by_derivation(self):
        # Um `AT_STRONGBOX_KEY` pronto é o do caminho container — a derivação só
        # preenche o que `_ENV_VARS` deixou vazio, nunca o que já chegou.
        main_key = "uma-frase-bem-longa-o-bastante"
        given = b"c" * 32
        env = {
            webapp_keys.MAIN_KEY_ENV: main_key,
            webapp_keys.STRONGBOX_KEY_ENV: base64.urlsafe_b64encode(given).decode(),
        }
        with mock.patch.dict(os.environ, env):
            webapp_keys.boot()
        self.assertEqual(webapp_keys.strongbox_key(), given)

    def test_a_main_key_too_short_to_derive_leaves_the_cofre_without_one(self):
        with mock.patch.dict(os.environ, {webapp_keys.MAIN_KEY_ENV: "curta"}):
            os.environ.pop(webapp_keys.STRONGBOX_KEY_ENV, None)
            webapp_keys.boot()
        self.assertIsNone(webapp_keys.strongbox_key())

    def test_a_value_that_does_not_decode_is_skipped_and_not_raised(self):
        with mock.patch.dict(os.environ, {webapp_keys.WEBAPP_KEY_ENV: "not base64 at all!!"}):
            webapp_keys.boot()
        self.assertIsNone(webapp_keys.webapp_key())


class TheJevRoute(ServerCase):
    """`POST /api/jev` — a chave do Jev, selada na pasta.

    A rota não chama o Jev nem guarda a Chave Principal: ela sela a credencial
    (o `secret` de escopo `jev`, `assist.configure`) e o estado passa a dizer
    `jev_ready` — que é o que o chat lê para parar de dizer "Jev não
    configurado".
    """

    CREDENTIAL = "uma-frase-bem-longa"
    NAME = "Rafael"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.NAME, self.CREDENTIAL)
        # A Chave Principal da SUBIDA, em memória — o mesmo que o `boot` deixaria
        # quando o host sobe com ela (`keys.MAIN_KEY_ENV`).
        webapp_keys.keep_main_key(self.CREDENTIAL)
        self.addCleanup(webapp_keys.keep_main_key, None)

    def session(self) -> dict:
        status, headers, _ = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL}
        )
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def test_setting_the_key_stores_it_and_the_state_says_ready(self):
        status, _, raw = self.post_full(
            "/api/jev", {"key": "chave-do-jev"}, headers=self.session(),
        )
        self.assertEqual(status, 200)
        self.assertTrue(raw["ok"])
        _, _, state = self.get("/api/state", headers=self.session())
        self.assertTrue(json.loads(state)["jev_ready"])

    def test_without_a_key_it_is_a_400(self):
        status, _, _ = self.post_full("/api/jev", {}, headers=self.session())
        self.assertEqual(status, 400)

    def test_without_the_main_key_in_memory_it_is_refused(self):
        # Sem a Chave Principal da subida não há com que SELAR — e a rota diz
        # isso, em vez de gravar em claro.
        webapp_keys.keep_main_key(None)
        status, _, _ = self.post_full(
            "/api/jev", {"key": "chave-do-jev"}, headers=self.session()
        )
        self.assertEqual(status, 409)

    def test_without_a_session_it_is_refused(self):
        self.assertEqual(self.status("/api/jev", method="POST"), 401)


if __name__ == "__main__":
    unittest.main()
