"""The WebApp server: its routes, its guards, and the doors of the look.

The server runs for real, on an ephemeral port, in a thread — a route tested by
calling its function is a route whose routing is not tested.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from bill import i18n
from bill.core import boot, projects, tables
from bill.ui.webapp import app as webapp


def interface_fields(name: str) -> set[str]:
    """The fields a `store.ts` interface declares — which is what the page reads
    from an entry of the payload.

    Parsed and not listed, so that adding a field to the interface is what makes
    the server owe it: a list written here by hand would be the same manual
    promise the code already failed to keep twice.
    """
    source = (webapp.HERE / "src" / "lib" / "store.ts").read_text(encoding="utf-8")
    body = re.search(rf"export interface {name} \{{(.*?)\n\}}", source, re.S)
    assert body, f"the interface {name} is not in store.ts"
    return set(re.findall(r"^\s*(\w+)\??:", body.group(1), re.M))


class ServerCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"BILL_ROOT": str(self.scratch.name), "BILL_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        with redirect_stdout(io.StringIO()):
            tables.create("task", {"text": "primeira"})

        self.server = webapp.make_server(0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    # -- the two doors, so a test reads as what it does ---------------------

    def get(self, path: str) -> tuple[int, object, bytes]:
        """A refusal is an answer too: it comes back with its status, never as
        an exception a test has to catch to say what it expected."""
        try:
            with urllib.request.urlopen(self.url(path)) as answer:
                return answer.status, answer.headers, answer.read()
        except urllib.error.HTTPError as error:
            body = error.read()
            error.close()
            return error.code, error.headers, body

    def post(self, path: str, payload: object, headers: dict | None = None):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url(path), data=body, method="POST",
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            with urllib.request.urlopen(request) as answer:
                return answer.status, json.loads(answer.read())
        except urllib.error.HTTPError as error:
            body = json.loads(error.read())
            error.close()
            return error.code, body

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
    def test_it_names_the_declared_tables_with_their_counts(self):
        _, _, body = self.get("/api/state")
        state = json.loads(body)
        keys = [table["key"] for table in state["tables"]]
        self.assertEqual(keys, ["task", "project", "reminder"])
        self.assertEqual(next(t for t in state["tables"] if t["key"] == "task")["count"], 1)

    def test_it_carries_the_theme_registry_and_the_language(self):
        _, _, body = self.get("/api/state")
        state = json.loads(body)
        self.assertEqual(state["lang"], "pt_BR")
        self.assertTrue(any(theme["id"] == "studio" for theme in state["themes"]))
        self.assertTrue(all(theme["side"] in ("light", "dark") for theme in state["themes"]))


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


class TheLook(ServerCase):
    def test_base_css_is_served(self):
        status, headers, body = self.get("/base.css")
        self.assertEqual(status, 200)
        self.assertIn("text/css", headers["Content-Type"])
        self.assertIn(b"THE RULES", body)

    def test_a_theme_is_resolved_by_lookup(self):
        _, _, body = self.get("/theme.css?theme=gothic")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / "gothic.css").read_text(encoding="utf-8"))

    def test_the_dark_side_is_a_second_file(self):
        _, _, body = self.get("/theme.css?theme=gothic&dark")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / "gothic-dark.css").read_text(encoding="utf-8"))

    def test_an_id_that_names_no_theme_falls_back_to_the_default(self):
        _, _, body = self.get("/theme.css?theme=../../etc/passwd")
        self.assertEqual(body.decode("utf-8"),
                         (webapp.THEMES / "studio.css").read_text(encoding="utf-8"))

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
        self.assertIn(b"bill.theme", body)


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
        name = sorted(entry.name for entry in webapp.ICONS.iterdir())[0]
        status, headers, _ = self.get(f"/icons/{name}")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/svg+xml")

    def test_a_hosted_font_is_served_with_its_revision(self):
        status, headers, body = self.get("/vendor/font-inter-400")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "font/woff2")
        self.assertEqual(headers["X-Hosted"], "5.3.0")
        manifest = json.loads((webapp.VENDOR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(body).hexdigest(),
                         manifest["files"]["font-inter-400"]["sha256"])

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
        for interface, entries in (("Kind", state["tables"]), ("ThemeRow", state["themes"])):
            self.assertTrue(entries, interface)
            declared = interface_fields(interface)
            for entry in entries:
                self.assertEqual(sorted(declared - set(entry)), [], f"{interface}: {entry}")


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
        rows = json.loads(body)
        self.assertEqual([row["title"] for row in rows],
                         ["Autonomia", "Site", "Sem projeto"])
        self.assertIsNone(rows[0]["parent"])
        self.assertEqual(rows[1]["parent"], 1)
        self.assertTrue(rows[-1].get("orphans"))

    def test_a_line_counts_the_tasks_that_name_that_project_directly(self):
        # Not the subtree: the number says how much of the day is under that
        # name, and what the subtree holds is what the PAGE is for.
        _, _, body = self.get("/api/projects")
        rows = {row["title"]: row["tasks"] for row in json.loads(body)}
        self.assertEqual(rows["Autonomia"], 1)
        self.assertEqual(rows["Site"], 1)

    def test_a_project_the_listing_does_not_show_does_not_claim_its_tasks(self):
        with redirect_stdout(io.StringIO()):
            done = tables.create("project", {"name": "Encerrado", "status": "done"})
            tables.create("task", {"text": "de um projeto fechado", "project": str(done["id"])})
        _, _, body = self.get("/api/projects")
        titles = [row["title"] for row in json.loads(body)]
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

    def test_an_unknown_project_is_not_a_crash(self):
        self.assertEqual(self.status("/api/project/999"), 404)

    def test_the_orphans_page_lists_exactly_them(self):
        _, _, body = self.get("/api/orphans")
        payload = json.loads(body)
        self.assertEqual([row["shown_id"] for row in payload["records"]], ["TASK-1"])


class TheProseDoors(ServerCase):
    def setUp(self):
        super().setUp()
        (self.root / "prose").mkdir(exist_ok=True)
        (self.root / "prose" / "nota.md").write_text("# oi\n", encoding="utf-8")

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

    def test_a_write_with_a_stale_revision_is_refused_with_the_new_one(self):
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        status, answer = self.post("/api/file", {"path": "nota.md", "text": "x\n", "base": "velha"})
        self.assertEqual(status, 409)
        self.assertEqual(answer["rev"], rev)
        self.assertEqual((self.root / "prose" / "nota.md").read_text(encoding="utf-8"), "# oi\n")

    def test_a_write_with_the_right_revision_lands(self):
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        status, answer = self.post("/api/file", {"path": "nota.md", "text": "novo\n", "base": rev})
        self.assertEqual(status, 200)
        self.assertEqual((self.root / "prose" / "nota.md").read_text(encoding="utf-8"), "novo\n")
        self.assertNotEqual(answer["rev"], rev)

    def test_a_refusal_speaks_the_catalogue(self):
        # The engine answers with a KEY and the wire carries the words — so a
        # refusal a person reads is never `prose.empty_write`.
        _, _, body = self.get("/api/file?path=nota.md")
        rev = json.loads(body)["rev"]
        _, answer = self.post("/api/file", {"path": "nota.md", "text": "", "base": rev})
        self.assertTrue(answer["error"])
        self.assertFalse(answer["error"].startswith(("prose.", "webapp.")))


class TheReadOnlySwitch(ServerCase):
    def test_the_page_cannot_write_when_the_switch_is_on(self):
        with mock.patch.dict(os.environ, {"BILL_READONLY": "1"}):
            status, answer = self.post("/api/table/task",
                                       {"action": "create", "set": {"text": "x"}})
        self.assertEqual(status, 403)
        self.assertIn("error", answer)
        self.assertEqual(len(tables.rows("task", show_all=True)), 1)


if __name__ == "__main__":
    unittest.main()
