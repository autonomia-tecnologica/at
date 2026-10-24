"""The global search's route (B-21, fatia 2/3): `GET /api/search?q=`.

No network and no model. The engine is tested in `test_search`; here is the
door: it answers the engine's hits, nothing for an empty term, and it demands
`cli:search` of whoever the server asks to prove themselves.
"""

from __future__ import annotations

import json

from at.core import actors, paths, tables
from at.data import store
from at.tests.test_webapp import ServerCase


class TheSearchRoute(ServerCase):
    def put(self, name: str, text: str) -> None:
        where = paths.prose_dir() / name
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(text, encoding="utf-8")

    def hits(self, query: str, headers: dict | None = None) -> list[dict]:
        status, _, body = self.get("/api/search?q=" + query, headers=headers)
        self.assertEqual(status, 200)
        return json.loads(body)["hits"]

    def test_it_answers_the_hits_the_engine_finds(self):
        self.put("kb/nota.md", "primeira\nO ornitorrinco aparece aqui\n")
        found = self.hits("ornitorrinco")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kind"], "file")
        self.assertEqual(found[0]["where"], "kb/nota.md")
        self.assertEqual(found[0]["line"], 2)
        self.assertIn("ornitorrinco", found[0]["snippet"])

    def test_the_name_of_a_file_is_found_too(self):
        self.put("zebra-listrada.md", "nada\n")
        self.assertEqual(self.hits("listrada")[0]["field"], "name")

    def test_an_empty_term_finds_nothing(self):
        self.put("nota.md", "texto\n")
        self.assertEqual(self.hits(""), [])
        self.assertEqual(self.hits("%20%20"), [])

    def test_a_term_that_matches_nothing_is_an_empty_list_not_an_error(self):
        self.assertEqual(self.hits("inexistente-xyz"), [])

    def test_the_answer_is_capped(self):
        from at.ui.webapp.routes_get import SEARCH_LIMIT
        for n in range(SEARCH_LIMIT + 5):
            self.put(f"muitos/arquivo-{n}.md", "x\n")
        self.assertEqual(len(self.hits("arquivo-")), SEARCH_LIMIT)


class TheSearchDemandsItsPermission(ServerCase):
    ADMIN = "admin"
    ADMIN_CREDENTIAL = "uma frase longa do administrador"
    NAME = "Ana"
    CREDENTIAL = "uma frase longa da ana ok"

    def setUp(self):
        super().setUp()
        actors.create_admin(self.ADMIN, self.ADMIN_CREDENTIAL)

    def cookie_for(self, carried: str) -> dict:
        role = tables.create(
            "role", {"name": "papel-busca", "permissions": carried})
        tables.create("actor", {
            "name": self.NAME, "type": "person",
            "role": str(store.number_of(role)), "credential": self.CREDENTIAL})
        status, headers, _ = self.post_full(
            "/api/session", {"name": self.NAME, "credential": self.CREDENTIAL})
        self.assertEqual(status, 200)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def test_a_stranger_is_refused_with_401(self):
        self.assertEqual(self.status("/api/search?q=x"), 401)

    def test_a_role_without_the_permission_is_refused_with_403(self):
        cookie = self.cookie_for("task:list")
        self.assertEqual(self.status("/api/search?q=x", headers=cookie), 403)

    def test_a_role_with_the_permission_is_answered(self):
        cookie = self.cookie_for("cli:search")
        self.assertEqual(self.status("/api/search?q=x", headers=cookie), 200)
