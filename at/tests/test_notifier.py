"""at's own push to the notifier — no `at_deploy` between the WebApp and ntfy
(§4, item 29's second slice, item 50).

Nothing here touches the network: the one call that would (`urlopen`) is
patched, and what a test reads is the REQUEST. The key handed to `token` and
`publish` is a fake 32-byte value, the same shape `test_webapp.py`'s
`TheDerivedKeys` uses — never the real Main Key, and never a real Chave Principal.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, files, notifier, paths
from at.data import schema, store
from at.encryption import vault

# A fake derived key — the shape `webapp.keys.notifier_key()` hands over: 32
# bytes, never the real Main Key and never a real Chave Principal (§4, item 50).
KEY = b"n" * 32
OTHER_KEY = b"x" * 32


class Answer:
    """`urlopen`'s answer: a status, a body, and the context manager it needs.

    The body is what the READ path takes (`notifier.read`); the POST never asks
    for one, and an answer built with none answers empty.
    """

    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class TheAddress(unittest.TestCase):
    """`target()`: the topic, at the address the environment handed over."""

    def test_no_variable_is_no_address(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(notifier.NETWORK_ENV, None)
            self.assertIsNone(notifier.target())

    def test_the_variable_names_the_topic_at_that_address(self):
        with mock.patch.dict(os.environ, {notifier.NETWORK_ENV: "at-notifier:2586"}):
            self.assertEqual(notifier.target(), "http://at-notifier:2586/at")

    def test_an_empty_variable_is_no_address_either(self):
        with mock.patch.dict(os.environ, {notifier.NETWORK_ENV: "   "}):
            self.assertIsNone(notifier.target())


class NotifierCase(unittest.TestCase):
    """A Working Folder of its own, so `token_file()` reads a real path."""

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

    def seal(self, value: str, key: bytes = KEY) -> None:
        files.atomic_write_text(
            notifier.token_file(), f"{vault.seal(value, key)}\n", mode=0o600
        )

    def plain(self, value: str) -> None:
        files.atomic_write_text(notifier.token_file(), f"{value}\n", mode=0o600)


class TheTokenFile(NotifierCase):
    def test_it_is_the_same_path_at_deploy_names(self):
        self.assertEqual(
            notifier.token_file(),
            paths.services_dir() / "notifier" / "token",
        )

    def test_no_file_is_no_token(self):
        self.assertIsNone(notifier.token(KEY))

    def test_a_file_with_no_envelope_is_the_value_itself(self):
        # A folder from before the seal (§4, item 50's migration) — the value
        # is in clear, and reading it needs no key at all.
        self.plain("tk_claro")
        self.assertEqual(notifier.token(None), "tk_claro")

    def test_a_sealed_value_opens_with_the_derived_key(self):
        self.seal("tk_selado")
        self.assertEqual(notifier.token(KEY), "tk_selado")

    def test_a_sealed_value_with_no_key_answers_none(self):
        self.seal("tk_selado")
        self.assertIsNone(notifier.token(None))

    def test_a_sealed_value_the_wrong_key_does_not_open(self):
        self.seal("tk_selado")
        self.assertIsNone(notifier.token(OTHER_KEY))


class ThePush(NotifierCase):
    """`publish`: the POST, and what it carries."""

    def post(self, status: int = 200, boom: Exception | None = None):
        sent: list = []

        def urlopen(request, timeout=None):
            sent.append(request)
            if boom is not None:
                raise boom
            if status >= 400:
                raise urllib.error.HTTPError(request.full_url, status, "recusado", {}, None)
            return Answer(status)

        patch = mock.patch.object(notifier.urllib.request, "urlopen", urlopen)
        patch.start()
        self.addCleanup(patch.stop)
        return sent

    def address(self):
        return mock.patch.dict(os.environ, {notifier.NETWORK_ENV: "at-notifier:2586"})

    def test_with_no_address_it_does_not_reach_for_the_network(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(notifier.NETWORK_ENV, None)
            self.seal("tk_selado")
            ok, detail = notifier.publish("AT", "corpo", KEY)
        self.assertFalse(ok)
        self.assertEqual(detail, "no_address")

    def test_with_no_token_it_does_not_reach_for_the_network_either(self):
        with self.address():
            ok, detail = notifier.publish("AT", "corpo", KEY)
        self.assertFalse(ok)
        self.assertEqual(detail, "no_token")

    def test_the_post_carries_the_topic_the_body_and_the_bearer_token(self):
        sent = self.post()
        self.seal("tk_selado")
        with self.address():
            ok, detail = notifier.publish("AT", "corpo", KEY)
        self.assertTrue(ok)
        self.assertEqual(detail, "200")
        request = sent[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, "http://at-notifier:2586/at")
        self.assertEqual(request.data, b"corpo")
        self.assertEqual(request.get_header("Authorization"), "Bearer tk_selado")

    def test_the_alert_announces_itself(self):
        sent = self.post()
        self.seal("tk_selado")
        with self.address():
            notifier.publish("AT", "corpo", KEY)
        request = sent[0]
        self.assertEqual(request.get_header("Title"), "AT")
        self.assertEqual(request.get_header("Priority"), notifier.PRIORITY)
        self.assertEqual(request.get_header("Tags"), notifier.TAGS)

    def test_a_refusal_is_the_status_and_never_a_crash(self):
        self.post(status=403)
        self.seal("tk_selado")
        with self.address():
            ok, detail = notifier.publish("AT", "corpo", KEY)
        self.assertFalse(ok)
        self.assertEqual(detail, "403")

    def test_a_network_that_does_not_answer_is_the_same_kind_of_answer(self):
        self.post(boom=urllib.error.URLError("recusado"))
        self.seal("tk_selado")
        with self.address():
            ok, detail = notifier.publish("AT", "corpo", KEY)
        self.assertFalse(ok)
        self.assertIn("recusado", detail)


class TheRead(NotifierCase):
    """`read`: the topic read from inside, with the one credential the whole
    product talks to the notifier with.

    The account is `read-write`, so the same token this module publishes with
    is the one it reads with — no second account, no second file, and no
    Chave Principal a WebApp would have to ask for one.
    """

    def get(self, status: int = 200, body: bytes = b"[]",
            boom: Exception | None = None):
        sent: list = []

        def urlopen(request, timeout=None):
            sent.append(request)
            if boom is not None:
                raise boom
            if status >= 400:
                raise urllib.error.HTTPError(request.full_url, status, "recusado", {}, None)
            return Answer(status, body)

        patch = mock.patch.object(notifier.urllib.request, "urlopen", urlopen)
        patch.start()
        self.addCleanup(patch.stop)
        return sent

    def address(self):
        return mock.patch.dict(os.environ, {notifier.NETWORK_ENV: "at-notifier:2586"})

    def test_with_no_address_it_does_not_reach_for_the_network(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(notifier.NETWORK_ENV, None)
            self.seal("tk_do_at")
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertEqual(refusal, "no_address")

    def test_with_no_token_it_does_not_reach_for_the_network_either(self):
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertEqual(refusal, "no_token")

    def test_it_polls_the_topic_with_the_accounts_bearer(self):
        sent = self.get()
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(refusal, "")
        request = sent[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(
            request.full_url, "http://at-notifier:2586/at/json?poll=1"
        )
        self.assertEqual(
            request.get_header("Authorization"), "Bearer tk_do_at"
        )

    def test_the_messages_come_back_as_what_the_page_draws(self):
        body = json.dumps([
            {"id": "a", "time": 1, "title": "AT", "message": "oi",
             "priority": 4, "tags": ["bell"], "event": "message",
             "click": "https://x", "actions": [{"action": "view"}]},
        ]).encode("utf-8")
        self.get(body=body)
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(refusal, "")
        # O que não é desenhado não viaja: a página recebe os campos dela, e
        # não o vocabulário inteiro do ntfy.
        self.assertEqual(
            messages,
            [{"id": "a", "time": 1, "title": "AT", "message": "oi",
              "priority": 4, "tags": ["bell"]}],
        )

    def test_an_entry_that_is_not_an_object_is_dropped(self):
        self.get(body=b'["nada", {"message": "oi"}]')
        self.seal("tk_do_at")
        with self.address():
            messages, _ = notifier.read(KEY)
        self.assertEqual(messages, [{"message": "oi"}])

    def test_a_refusal_is_the_status_and_never_a_crash(self):
        self.get(status=403)
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertEqual(refusal, "403")

    def test_a_network_that_does_not_answer_is_the_same_kind_of_answer(self):
        self.get(boom=urllib.error.URLError("recusado"))
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertIn("recusado", refusal)

    def test_an_answer_that_is_not_a_list_is_an_empty_topic(self):
        self.get(body=b'{"unexpected": true}')
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertEqual(refusal, "")

    def test_a_body_that_is_not_json_is_unreadable(self):
        # "Não deu para saber" e "nada chegou" são a mesma coisa para quem lê a
        # página, mas não são a mesma resposta — e é por isso que o segundo
        # campo existe.
        self.get(body=b"<html>nao e json</html>")
        self.seal("tk_do_at")
        with self.address():
            messages, refusal = notifier.read(KEY)
        self.assertEqual(messages, [])
        self.assertEqual(refusal, "unreadable")


if __name__ == "__main__":
    unittest.main()
