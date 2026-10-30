"""A notificação do AT — o Web Push do próprio PWA, que substituiu o ntfy.

Nada aqui toca a rede: a única chamada que tocaria (`urlopen`) é trocada por um
duble, e o que um teste lê é a REQUISIÇÃO. A cripto é provada por IDA E VOLTA —
o que o AT cifra, o teste abre com a chave privada do "navegador" —, que é o que
prende a implementação à RFC 8291 sem precisar de um push service de verdade.

A chave derivada que `publish`/`read` aceitam é um valor falso de 32 bytes: o
Web Push não sela nada com ela, e o parâmetro só existe pelo que a chamada já
era.
"""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from at import i18n
from at.core import boot, notifier, push

KEY = b"n" * 32


class Answer:
    """`urlopen`'s answer: a status, and the context manager it needs."""

    def __init__(self, status: int = 201) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class FolderCase(unittest.TestCase):
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

    # --- o "navegador": um par P-256 e o `auth` que ele daria ----------------

    def browser(self) -> tuple[dict, ec.EllipticCurvePrivateKey, bytes]:
        """A subscription the page would send, and the private side of its key."""
        private = ec.generate_private_key(ec.SECP256R1())
        public = private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        auth = os.urandom(16)
        return {
            "endpoint": "https://push.example/xyz",
            "keys": {
                "p256dh": base64.urlsafe_b64encode(public).rstrip(b"=").decode(),
                "auth": base64.urlsafe_b64encode(auth).rstrip(b"=").decode(),
            },
        }, private, auth

    def decrypt(self, body: bytes, private, auth: bytes) -> bytes:
        """RFC 8291: abrir o que `push._encrypt` produziu, do lado do navegador."""
        salt, name_len = body[:16], body[20]
        as_public = body[21:21 + name_len]
        ciphertext = body[21 + name_len:]
        ua_public = private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        shared = private.exchange(
            ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(push.CURVE, as_public)
        )
        ikm = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=auth,
            info=b"WebPush: info\x00" + ua_public + as_public,
        ).derive(shared)
        cek = HKDF(
            algorithm=hashes.SHA256(), length=16, salt=salt,
            info=b"Content-Encoding: aes128gcm\x00",
        ).derive(ikm)
        nonce = HKDF(
            algorithm=hashes.SHA256(), length=12, salt=salt,
            info=b"Content-Encoding: nonce\x00",
        ).derive(ikm)
        padded = AESGCM(cek).decrypt(nonce, ciphertext, None)
        return padded.rstrip(b"\x00").rstrip(b"\x02")


class TheKey(FolderCase):
    def test_the_key_is_drawn_once_and_kept(self):
        first = push.public_key()
        second = push.public_key()
        self.assertEqual(first, second)
        self.assertTrue((push.directory() / push.VAPID_FILE).is_file())

    def test_the_public_key_is_a_point_on_the_curve(self):
        raw = base64.urlsafe_b64decode(push.public_key() + "==")
        self.assertEqual(len(raw), 65)
        self.assertEqual(raw[0], 4)
        parsed = ec.EllipticCurvePublicKey.from_encoded_point(push.CURVE, raw)
        self.assertEqual(parsed.curve.name, "secp256r1")

    def test_the_contact_follows_the_site_name(self):
        push.contact("at.example")
        push.contact("at.example")  # idempotente
        stored = json.loads((push.directory() / push.VAPID_FILE).read_text())
        self.assertEqual(stored["contact"], "mailto:at@at.example")


class TheEncryption(FolderCase):
    def test_what_is_encrypted_is_what_the_browser_opens(self):
        subscription, private, auth = self.browser()
        message = json.dumps({"title": "AT", "body": "Vence hoje"}).encode()
        body = push._encrypt(subscription, message)
        self.assertEqual(self.decrypt(body, private, auth), message)

    def test_the_header_carries_the_salt_the_size_and_the_ephemeral_key(self):
        subscription, _, _ = self.browser()
        body = push._encrypt(subscription, b"oi")
        self.assertEqual(len(body[:16]), 16)          # salt
        self.assertEqual(int.from_bytes(body[16:20], "big"), push.RECORD)
        self.assertEqual(body[20], 65)                # a chave efêmera é de 65 bytes


class TheSubscriptions(FolderCase):
    def test_a_subscription_the_browser_would_send_is_stored(self):
        subscription, _, _ = self.browser()
        self.assertTrue(push.subscribe(subscription))
        self.assertEqual([entry["endpoint"] for entry in push.subscriptions()],
                         ["https://push.example/xyz"])

    def test_the_same_endpoint_is_one_subscription_not_two(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        push.subscribe(subscription)
        self.assertEqual(len(push.subscriptions()), 1)

    def test_a_body_that_is_not_a_subscription_is_refused(self):
        for bad in (None, {}, {"endpoint": "x"}, {"endpoint": "x", "keys": {}},
                    {"keys": {"p256dh": "a", "auth": "b"}}, "nao-e-um-objeto"):
            with self.subTest(bad=bad):
                self.assertFalse(push.subscribe(bad))

    def test_forget_drops_the_endpoint(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        push.forget(subscription["endpoint"])
        self.assertEqual(push.subscriptions(), [])


class TheSend(FolderCase):
    def test_with_no_subscribers_there_is_nothing_to_send(self):
        self.assertEqual(push.send("AT", "oi"), (False, "no_subscribers"))

    def test_every_subscriber_gets_the_ciphered_alert(self):
        subscription, private, auth = self.browser()
        push.subscribe(subscription)
        seen: list = []

        def fake(request, timeout=None):
            seen.append(request)
            return Answer(201)

        with mock.patch("urllib.request.urlopen", side_effect=fake):
            ok, detail = push.send("AT", "Vence hoje")
        self.assertTrue(ok)
        self.assertEqual(detail, "201")
        self.assertEqual(len(seen), 1)
        sent = seen[0]
        self.assertEqual(sent.get_full_url(), "https://push.example/xyz")
        self.assertEqual(sent.get_header("Content-encoding"), "aes128gcm")
        self.assertTrue(sent.get_header("Authorization").startswith("vapid t="))
        payload = self.decrypt(sent.data, private, auth)
        self.assertEqual(json.loads(payload)["body"], "Vence hoje")

    def test_the_inbox_keeps_what_went_out(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        with mock.patch("urllib.request.urlopen", return_value=Answer(201)):
            push.send("AT", "Vence hoje")
        rows = push.inbox()
        self.assertEqual(rows[0]["title"], "AT")
        self.assertEqual(rows[0]["message"], "Vence hoje")

    def test_a_dead_subscription_is_dropped_not_retried(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        dead = urllib.error.HTTPError("https://push.example/xyz", 410, "gone", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=dead):
            ok, _ = push.send("AT", "oi")
        self.assertFalse(ok)
        self.assertEqual(push.subscriptions(), [])

    def test_a_network_that_does_not_answer_is_not_a_crash(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        with mock.patch("urllib.request.urlopen", side_effect=OSError("sem rede")):
            ok, detail = push.send("AT", "oi")
        self.assertFalse(ok)
        self.assertEqual(detail, "undelivered")

    def test_the_payload_carries_data_and_actions_when_they_come(self):
        subscription, private, auth = self.browser()
        push.subscribe(subscription)
        seen: list = []

        def fake(request, timeout=None):
            seen.append(request)
            return Answer(201)

        data = {"reminder": 7, "instance": "2026-10-05 09:00"}
        actions = [{"action": "close", "title": "Concluir"}]
        with mock.patch("urllib.request.urlopen", side_effect=fake):
            push.send("AT", "Vence hoje", data=data, actions=actions)
        payload = json.loads(self.decrypt(seen[0].data, private, auth))
        self.assertEqual(payload["data"], data)
        self.assertEqual(payload["actions"], actions)

    def test_the_payload_carries_neither_when_they_are_empty(self):
        subscription, private, auth = self.browser()
        push.subscribe(subscription)
        seen: list = []

        def fake(request, timeout=None):
            seen.append(request)
            return Answer(201)

        with mock.patch("urllib.request.urlopen", side_effect=fake):
            push.send("AT", "oi")
        payload = json.loads(self.decrypt(seen[0].data, private, auth))
        self.assertNotIn("data", payload)
        self.assertNotIn("actions", payload)


class TheDoor(FolderCase):
    def test_publish_delegates_to_the_push_and_ignores_the_key(self):
        subscription, _, _ = self.browser()
        push.subscribe(subscription)
        with mock.patch.object(push, "send", return_value=(True, "201")) as send:
            self.assertEqual(notifier.publish("AT", "oi", KEY), (True, "201"))
        send.assert_called_once_with("AT", "oi", urgency="high", data=None, actions=None)

    def test_publish_hands_data_and_actions_to_the_push(self):
        data = {"reminder": 3, "instance": "2026-10-05 09:00"}
        actions = [{"action": "close", "title": "Concluir"}]
        with mock.patch.object(push, "send", return_value=(True, "201")) as send:
            notifier.publish("AT", "oi", KEY, data=data, actions=actions)
        send.assert_called_once_with("AT", "oi", urgency="high", data=data, actions=actions)

    def test_read_is_the_inbox_and_can_never_refuse(self):
        push.record("AT", "um aviso")
        messages, refusal = notifier.read(KEY)
        self.assertEqual(refusal, "")
        self.assertEqual(messages[0]["message"], "um aviso")


if __name__ == "__main__":
    unittest.main()
