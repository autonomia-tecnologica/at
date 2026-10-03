"""`at.core.jev`: the one call out to TypeSafe's System One (TASK-180,
fatia 1/3) — the criteria it builds, the request it sends, and the answer it
reads back into a `Decision`.

Nothing here touches a socket: every test either injects `transport` (the
seam `at.core.assist` swaps too) or patches `urllib.request.urlopen` the
way `test_notifier.py` already does for the one module that talks to a
service the same way. A test at the bottom says the whole file needs no
network, the same promise `test_nlu.py`'s own ruler makes for itself.
"""

from __future__ import annotations

import io
import json
import os
import socket
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, jev, tables
from at.data import schema, store


class JevCase(unittest.TestCase):
    """A Working Folder of its own — the criteria read `schema.tables()`."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def fake(self, action: str, table: str, action_confidence: float, table_confidence: float):
        """A transport that answers the shape the real API answers, with no
        socket opened — the seam both this file and `test_assist.py` use."""

        def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> bytes:
            self.last_url = url
            self.last_body = json.loads(body.decode("utf-8"))
            self.last_headers = headers
            return json.dumps(
                {
                    "model": "jev-test",
                    "answers": {
                        "action": {
                            "type": "choice",
                            "choice": action,
                            "probabilities": {},
                            "confidence": action_confidence,
                        },
                        "table": {
                            "type": "choice",
                            "choice": table,
                            "probabilities": {},
                            "confidence": table_confidence,
                        },
                    },
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            ).encode("utf-8")

        return post


class TheGrounding(JevCase):
    """The criteria the two Choice questions are asked with."""

    def test_every_engine_action_and_none_are_the_action_criteria(self):
        criteria = jev._action_criteria("pt_BR")
        self.assertEqual(set(criteria), set(tables.ACTIONS) | {jev.NONE})

    def test_every_declared_table_and_none_are_the_table_criteria(self):
        criteria = jev._table_criteria("pt_BR")
        self.assertEqual(set(criteria), set(schema.tables()) | {jev.NONE})

    def test_a_recognized_synonym_is_embedded_as_an_example(self):
        # "cria" already means `create` with no help from Jev — the criterion
        # says so, which is the whole point of asking only about what is left.
        criteria = jev._action_criteria("pt_BR")
        self.assertIn("cria", criteria["create"])
        self.assertIn("criar", criteria["create"])

    def test_the_two_languages_ground_the_same_canonicals_in_their_own_words(self):
        pt = jev._action_criteria("pt_BR")
        en = jev._action_criteria("en_US")
        self.assertIn("cria", pt["create"])
        self.assertIn("create", en["create"])
        self.assertNotIn("cria", en["create"])

    def test_an_action_criterion_carries_a_meaning_and_not_only_its_synonyms(self):
        # A bare label plus its own synonyms measured WORSE than the prototype
        # against the live Jev (the fatia's own "medição real") — a sentence of
        # MEANING is what the prototype had and a label alone does not say.
        pt = jev._action_criteria("pt_BR")
        self.assertIn("Fazer existir um item novo", pt["create"])
        en = jev._action_criteria("en_US")
        self.assertIn("Make a new item exist", en["create"])

    def test_a_table_criterion_reuses_the_schema_s_own_desc(self):
        # `desc` is the architecture's own prose (`schema.py`'s own rule: "no
        # text a person reads") — Jev is not a person, and reusing it costs
        # nothing new to maintain.
        criteria = jev._table_criteria("pt_BR")
        self.assertIn(schema.of("task")["desc"], criteria["task"])

    def test_the_meaning_is_the_same_in_both_languages_since_jev_reads_it(self):
        # `desc` is model-facing, not a person-facing `i18n` text, so the same
        # English prose grounds the criterion whichever language the label and
        # the embedded synonyms are written in.
        desc = schema.of("task")["desc"]
        self.assertIn(desc, jev._table_criteria("pt_BR")["task"])
        self.assertIn(desc, jev._table_criteria("en_US")["task"])

    def test_spoken_answers_a_word_this_language_already_reads(self):
        self.assertEqual(jev.spoken("create", "pt_BR"), "criar")
        self.assertEqual(jev.spoken("task", "pt_BR"), "tarefa")
        self.assertEqual(jev.spoken("create", "en_US"), "create")

    def test_spoken_answers_none_for_a_canonical_no_vocabulary_names(self):
        self.assertIsNone(jev.spoken("not-a-real-canonical", "pt_BR"))

    def test_the_criteria_keys_are_in_the_catalogue_of_both_languages(self):
        for key in (
            "assist.criteria.action.instructions",
            "assist.criteria.table.instructions",
            "assist.criteria.option",
            "assist.criteria.none.action",
            "assist.criteria.none.table",
            *(f"assist.criteria.action.desc.{action}" for action in tables.ACTIONS),
        ):
            for language in i18n.SUPPORTED:
                with self.subTest(key=key, language=language):
                    self.assertNotEqual(i18n.text(key, language), key)


class TheRequest(JevCase):
    """What `decide` sends, through the injected transport."""

    def test_the_request_carries_the_phrase_and_the_model(self):
        jev.decide("bota uma tarefa aí", language="pt_BR", api_key="k",
                    transport=self.fake("create", "task", 0.9, 0.9))
        self.assertEqual(self.last_url, jev.ENDPOINT)
        self.assertEqual(self.last_body["state"], "bota uma tarefa aí")
        self.assertEqual(self.last_body["model"], jev.MODEL)
        self.assertEqual(self.last_body["questions"]["action"]["type"], "choice")
        self.assertEqual(self.last_body["questions"]["table"]["type"], "choice")

    def test_the_key_travels_as_a_bearer_header_and_nowhere_else(self):
        jev.decide("x", language="pt_BR", api_key="segredo-123",
                    transport=self.fake("create", "task", 0.9, 0.9))
        self.assertEqual(self.last_headers["Authorization"], "Bearer segredo-123")
        self.assertNotIn("segredo-123", json.dumps(self.last_body))


class TheAnswer(JevCase):
    """What a well-shaped response becomes: a `Decision`."""

    def test_the_answer_becomes_a_decision(self):
        decision = jev.decide(
            "x", language="pt_BR", api_key="k",
            transport=self.fake("create", "task", 0.91, 0.77),
        )
        self.assertEqual(decision.action, "create")
        self.assertEqual(decision.action_confidence, 0.91)
        self.assertEqual(decision.table, "task")
        self.assertEqual(decision.table_confidence, 0.77)

    def test_confidence_is_the_weaker_of_the_two(self):
        decision = jev.decide(
            "x", language="pt_BR", api_key="k",
            transport=self.fake("create", "task", 0.91, 0.55),
        )
        self.assertEqual(decision.confidence, 0.55)


class TheErrors(JevCase):
    """A service that did not answer usably — never raised as anything else."""

    def test_an_unreadable_body_is_a_jev_error(self):
        def broken(url, body, headers, timeout):
            return b"not json"
        with self.assertRaises(jev.JevError):
            jev.decide("x", language="pt_BR", api_key="k", transport=broken)

    def test_a_body_missing_an_answer_is_a_jev_error(self):
        def missing(url, body, headers, timeout):
            return json.dumps({"answers": {"action": {}}}).encode("utf-8")
        with self.assertRaises(jev.JevError):
            jev.decide("x", language="pt_BR", api_key="k", transport=missing)

    def test_the_transport_s_own_error_is_a_jev_error(self):
        def failing(url, body, headers, timeout):
            raise jev.JevError("503: overloaded")
        with self.assertRaises(jev.JevError):
            jev.decide("x", language="pt_BR", api_key="k", transport=failing)


class Answer:
    """`urlopen`'s answer — the shape `test_notifier.py`'s own fake uses."""

    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class TheDefaultTransport(JevCase):
    """`_post`: the one place `urllib` is named, exercised with no socket."""

    def test_a_successful_call_reads_the_body_back(self):
        body = json.dumps({"ok": True}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=Answer(200, body)):
            self.assertEqual(jev._post(jev.ENDPOINT, b"{}", {}, 1.0), body)

    def test_an_http_error_becomes_a_jev_error(self):
        error = urllib.error.HTTPError(
            jev.ENDPOINT, 401, "unauthorized", {}, io.BytesIO(b"bad key")
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(jev.JevError) as refused:
                jev._post(jev.ENDPOINT, b"{}", {}, 1.0)
            self.assertIn("401", str(refused.exception))

    def test_a_network_error_becomes_a_jev_error(self):
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("no route"),
        ):
            with self.assertRaises(jev.JevError):
                jev._post(jev.ENDPOINT, b"{}", {}, 1.0)


class TheSuiteNeedsNoNetwork(JevCase):
    def test_every_call_above_is_injected(self):
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("jev needs no network here")
        ):
            decision = jev.decide(
                "bota uma tarefa aí", language="pt_BR", api_key="k",
                transport=self.fake("create", "task", 0.9, 0.9),
            )
            self.assertEqual(decision.action, "create")


if __name__ == "__main__":
    unittest.main()
