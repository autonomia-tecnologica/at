"""O push do AT para o navegador — o Web Push que substituiu o ntfy.

**A estrada é a do PRÓPRIO navegador, e não a de um serviço de notificação.**
O ntfy tinha app, conta e uma segunda porta; o que o AT quer é a notificação
do sistema operacional, publicada pelo PWA que já é a cara do AT. Quem entrega
é o *push service* do navegador (FCM no Chrome/Android, Mozilla no Firefox),
e o AT só precisa falar os dois protocolos que o navegador exige:

- **VAPID** (RFC 8292): o AT assina um JWT ES256 provando, ao push service,
  que é ele quem envia. O par de chaves P-256 é do AT, é sorteado uma vez e
  vive na pasta — o mesmo desenho do `gate` do Caddy (`caddy.draw_gate`), e
  pela mesma razão: a pasta É o backup.
- **aes128gcm** (RFC 8291): o payload vai cifrado com a chave pública que o
  navegador deu na inscrição, por ECDH P-256 + HKDF + AES-128-GCM. O push
  service não abre o que carrega.

**Por que `cryptography` e não `PyNaCl`.** Os dois protocolos são especificados
em NIST P-256, e o libsodium é Curve25519 e mais nada — ele não tem a curva que
o navegador aceita. `cryptography` é a segunda dependência do produto e é só
por isto (`requirements.txt` diz o mesmo).

**A inscrição é do navegador, e o AT não inventa uma.** O `pushManager
.subscribe` da página devolve um objeto com `endpoint` e duas chaves
(`p256dh`, `auth`); é ele que `subscribe` guarda, e é contra ele que `send`
cifra. Uma inscrição que o push service aposentou (404/410) é DESCARTADA aqui
— insistir nela seria um erro que se repete para sempre, e não uma mensagem
que não foi.

**A entrega é best-effort, como sempre foi** (§7f): um push que não saiu não é
uma exceção que o relógio tenha de sobreviver por nome. O que saiu fica no
`INBOX`, que é o que a página lista — o ntfy guardava o tópico, e isso o AT
fazia por uma rede que agora não existe.
"""

from __future__ import annotations

import base64
import json
import os
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from at.core import files, paths

# `App/services/push/` — a casa dos serviços (§7). O notificador é o serviço
# `notifier` (§4), e o par VAPID e as inscrições são o estado DELE: não há
# container nenhum aqui — é o processo do AT falando com o navegador —, mas um
# serviço é um serviço, e a casa é a mesma dos outros.
FOLDER = "push"
VAPID_FILE = "vapid.json"
SUBSCRIPTIONS = "subscriptions.json"
INBOX = "inbox.jsonl"

# A curva, e os tamanhos que a RFC 8291 fixa. O record size (`RS`) é o teto de
# um registro; um aviso do AT cabe folgado nele, e um payload maior seria
# record-splitting, que o produto não faz.
CURVE = ec.SECP256R1()
AESGCM_KEY = 16
NONCE = 12
SALT = 16
RECORD = 4096

# Quanto o push service guarda uma mensagem que o aparelho não estava para
# receber, e quanto se espera por uma resposta antes da rodada seguir.
TTL = 3600
TIMEOUT = 10.0

# O contato que o VAPID declara ao push service: um `mailto:` ou uma URL. O AT
# é de quem o roda, então o valor nasce genérico e é trocado pelo nome do site
# na primeira inscrição, quando a rota sabe o `Host`.
CONTACT = "mailto:at@localhost"

# Quantas mensagens o `INBOX` devolve, e o teto do arquivo.
INBOX_LIMIT = 50

# O que a página desenha de uma notificação — os mesmos campos de antes.
FIELDS = ("id", "time", "title", "message", "priority", "tags")


def directory() -> Path:
    return paths.service_dir(FOLDER)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


# ------------------------------------------------------------------ VAPID ---


def _load() -> dict:
    """O par VAPID da pasta, sorteado na primeira vez. Em CLARO, 0600.

    O par é o segredo de ENVIO: quem o tem pode mandar push aos inscritos. Ele
    mora na pasta como o `gate` do Caddy mora — a pasta é de quem usa, é o
    backup, e no caminho hospedado não há container de onde ele tenha de sair
    selado. No caminho container o processo que lê é o próprio WebApp, que já
    monta a pasta.
    """
    where = directory() / VAPID_FILE
    try:
        stored = json.loads(where.read_text(encoding="utf-8"))
        if stored.get("private") and stored.get("public"):
            return stored
    except (FileNotFoundError, ValueError):
        pass
    private = ec.generate_private_key(CURVE)
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public = _b64url(
        private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )
    stored = {"private": pem, "public": public, "contact": CONTACT}
    files.atomic_write_text(
        where, json.dumps(stored, ensure_ascii=False, indent=2) + "\n", mode=0o600
    )
    return stored


def _private(stored: dict) -> ec.EllipticCurvePrivateKey:
    return cast(ec.EllipticCurvePrivateKey, serialization.load_pem_private_key(stored["private"].encode("ascii"), None))


def public_key() -> str:
    """A chave PÚBLICA do VAPID, base64url — o que a página passa ao
    `pushManager.subscribe`. Pública por construção: ela viaja para o navegador,
    e é o par privado que nunca sai da pasta."""
    return _load()["public"]


def contact(host: str | None = None) -> None:
    """Grava o contato do VAPID a partir do nome do site, uma vez."""
    if not host:
        return
    stored = _load()
    wanted = f"mailto:at@{host}"
    if stored.get("contact") != wanted:
        stored["contact"] = wanted
        files.atomic_write_text(
            directory() / VAPID_FILE,
            json.dumps(stored, ensure_ascii=False, indent=2) + "\n",
            mode=0o600,
        )


def _vapid_header(endpoint: str, stored: dict) -> str:
    """`vapid t=<jwt>, k=<chave>` — o JWT ES256 que prova o envio (RFC 8292)."""
    parsed = urlparse(endpoint)
    audience = f"{parsed.scheme}://{parsed.netloc}"
    header = _b64url(json.dumps({"typ": "JWT", "alg": "ES256"}).encode("ascii"))
    claims = _b64url(
        json.dumps(
            {"aud": audience, "exp": int(time.time()) + 12 * 3600,
             "sub": stored.get("contact", CONTACT)}
        ).encode("ascii")
    )
    signing_input = f"{header}.{claims}".encode("ascii")
    der = _private(stored).sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    token = f"{header}.{claims}.{_b64url(signature)}"
    return f"vapid t={token}, k={stored['public']}"


# ------------------------------------------------------------- cifrar -----


def _hkdf(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def _encrypt(subscription: dict, plaintext: bytes) -> bytes:
    """O corpo `aes128gcm` (RFC 8291) para UMA inscrição.

    ECDH efêmero contra a `p256dh` da inscrição, HKDF duas vezes — a primeira
    sela o segredo com o `auth` e o nomeia, a segunda tira dele a chave e o
    nonce do AES-GCM —, e o cabeçalho que diz ao navegador como abrir: sal,
    tamanho do registro, e a chave pública efêmera.
    """
    ua_public = _unb64url(subscription["keys"]["p256dh"])
    auth = _unb64url(subscription["keys"]["auth"])
    recipient = ec.EllipticCurvePublicKey.from_encoded_point(CURVE, ua_public)

    ephemeral = ec.generate_private_key(CURVE)
    as_public = ephemeral.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    shared = ephemeral.exchange(ec.ECDH(), recipient)

    ikm = _hkdf(shared, auth, b"WebPush: info\x00" + ua_public + as_public, 32)
    salt = os.urandom(SALT)
    cek = _hkdf(ikm, salt, b"Content-Encoding: aes128gcm\x00", AESGCM_KEY)
    nonce = _hkdf(ikm, salt, b"Content-Encoding: nonce\x00", NONCE)

    body = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)
    header = salt + struct.pack(">I", RECORD) + bytes([len(as_public)]) + as_public
    return header + body


# --------------------------------------------------------- inscrições -----


def subscriptions() -> list[dict]:
    stored = files.read_json(directory() / SUBSCRIPTIONS, default=[])
    return [entry for entry in cast(list, stored) if isinstance(entry, dict) and entry.get("endpoint")]


def _write_subscriptions(entries: list[dict]) -> None:
    files.atomic_write_text(
        directory() / SUBSCRIPTIONS,
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
        mode=0o600,
    )


def subscribe(subscription: object) -> bool:
    """Guarda a inscrição que o navegador mandou. Uma por `endpoint`.

    Um objeto que não é o que o `PushSubscription.toJSON()` promete é RECUSADO
    — guardar o que não se sabe cifrar seria uma inscrição que nunca recebe, e
    um erro só apareceria no dia do aviso.
    """
    if not isinstance(subscription, dict):
        return False
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys")
    if not endpoint or not isinstance(keys, dict):
        return False
    if not keys.get("p256dh") or not keys.get("auth"):
        return False
    entries = [entry for entry in subscriptions() if entry.get("endpoint") != endpoint]
    entries.append({"endpoint": endpoint, "keys": {"p256dh": keys["p256dh"],
                                                   "auth": keys["auth"]}})
    _write_subscriptions(entries)
    return True


def forget(endpoint: str) -> None:
    """Tira uma inscrição — o push service disse que ela morreu."""
    entries = [entry for entry in subscriptions() if entry.get("endpoint") != endpoint]
    _write_subscriptions(entries)


# ------------------------------------------------------------- envio ------


def _post(subscription: dict, payload: dict, stored: dict) -> tuple[bool, str]:
    endpoint = subscription["endpoint"]
    body = _encrypt(subscription, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    request = urllib.request.Request(endpoint, data=body, method="POST")
    request.add_header("Content-Encoding", "aes128gcm")
    request.add_header("Content-Type", "application/octet-stream")
    request.add_header("TTL", str(TTL))
    request.add_header("Urgency", payload.get("urgency", "high"))
    request.add_header("Authorization", _vapid_header(endpoint, stored))
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 300, str(response.status)
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        if code in (404, 410):
            forget(endpoint)  # inscrição morta: descartar, não insistir
        return False, str(code)
    except (urllib.error.URLError, OSError) as error:
        return False, str(getattr(error, "reason", error))


def send(title: str, body: str, urgency: str = "high") -> tuple[bool, str]:
    """Manda UM aviso a toda inscrição, e registra no `INBOX`. `(ok, detalhe)`.

    `ok` é verdadeiro quando PELO MENOS uma inscrição recebeu, que é o que faz
    o lembrete ser marcado como avisado — uma inscrição morta não pode fazer o
    aviso se repetir todo dia. Sem inscrição nenhuma, é `no_subscribers`, e o
    lembrete tenta de novo na próxima passada, como sempre.
    """
    entries = subscriptions()
    if not entries:
        return False, "no_subscribers"
    stored = _load()
    payload = {"title": title, "body": body, "urgency": urgency}
    delivered = ""
    for subscription in list(entries):
        ok, detail = _post(subscription, payload, stored)
        if ok:
            delivered = detail
    if not delivered:
        return False, "undelivered"
    record(title, body)
    return True, delivered


# --------------------------------------------------------------- inbox ----


def record(title: str, body: str) -> None:
    """A linha do `INBOX` — o que a página lista depois."""
    where = directory() / INBOX
    try:
        lines = where.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    entry = {
        "id": int(time.time() * 1000),
        "time": int(time.time()),
        "title": title,
        "message": body,
        "priority": "high",
    }
    lines.append(json.dumps(entry, ensure_ascii=False))
    files.atomic_write_text(where, "\n".join(lines[-INBOX_LIMIT:]) + "\n", mode=0o600)


def inbox(limit: int = INBOX_LIMIT) -> list[dict]:
    """As últimas notificações, da mais nova para a mais velha."""
    where = directory() / INBOX
    try:
        lines = where.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    rows: list[dict] = []
    for line in reversed(lines[-limit:]):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            rows.append({name: entry[name] for name in FIELDS if name in entry})
    return rows
