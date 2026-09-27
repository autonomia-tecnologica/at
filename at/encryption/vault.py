"""The vault: the Access Phrase, the Vault Key and the value it seals (§4).

AT's encryption starts from the **Access Phrase** and from nothing stored: §4
says it is what the person knows and types, at least 16 characters and it is a
phrase, and it recommends keeping it outside the machine. From it the **Vault
Key** is derived. Nothing here keeps a key — no cache, no file, no setting — and
that is the module's whole posture: §4 says AT does not choose for you where
the key lives. Typing it when AT starts is grade `S`; keeping it unlocked in
the system user's folder is `A`; keeping it inside the Working Folder is `B` —
and each of the three is a SURFACE's decision, with its price said out loud.
This module sits below all three and holds the key for the length of one call.

**The derivation is deterministic, and that is what tells it from `password`.**
A hashed field draws its own salt and carries it inside its own answer, because
the value never has to come back — it is only ever compared. The Vault Key has to
come back from the phrase alone: nothing stores it, and §4 says it recovers any
derived key lost. So the salt is derived from the phrase itself, and the same
phrase yields the same key on any machine, with no salt written anywhere. The
cost is the one `password` fixes, imported instead of named again — the price of
a derivation from something a person types has one home.

**The sealed value is a self-describing envelope.** `seal` answers
`xsalsa20poly1305:` and the base64 of what `libsodium` produced — the nonce
first, then the ciphertext — so the algorithm and the nonce travel in the value
itself and a row needs nothing beside it.

**Writing refuses; reading answers.** Sealing with no key is a refusal, because
a value sealed with nothing is a value nothing opens; and a key that is not one
is refused by that same door. `unseal` answers `None` for anything that does not
open, exactly as `password.verify` answers `False`: a stored value a hand edited,
a different key, an envelope of another algorithm — all of them are "no", and
none of them is an exception that takes down the read that found it. And the
sealed value comes back in clear through THIS door and no other: `unseal` is the
only reader, and it hands back text only when the key opens it.

**A derived key is a key like any other here, and there is a door that makes
one.** §4 says the derived keys come from the Vault Key, one per service or
purpose, and that the Vault Key recovers any of them lost — which is
`derived_key`, and it is a derivation and not a stored thing, exactly as
`vault_key` is. It is KEYED by the Vault Key and reads the scope as its message,
so the name of a service tells nobody its key, and two names a character apart
are two keys. What seals an envelope is what opens it, and `seal` is handed its
key — so a derived key opens what it sealed and is refused by what its own scope
does not cover, and nothing in this module needs a second secret for that.

The layer points inward (§4): this module reaches `libsodium`, the standard
library and `password`, and never `core` or `data`. The store the envelope lives
in — `data/secrets.jsonl` — is reached by `core`, which is where the row that
carries the sealed value is written.
"""

from __future__ import annotations

import base64
import re

import nacl.encoding
import nacl.exceptions
import nacl.hash
import nacl.pwhash
import nacl.secret

from at.encryption import password

# The floor of the Access Phrase (§4): at least 16 characters, "and it is a
# phrase". §4's own words: "Mariazinha comeu todo o pudim", in lowercase and
# without spaces, is safer than `Mariazinha@123`. The floor belongs to the
# phrase, and not to the door that asks for it — `MIN_CREDENTIAL` in
# `core.actors` is another thing with another price, and it says so.
MINIMUM = 16

# What the envelope names, and the whole of its header. `libsodium`'s secret box
# is XSalsa20-Poly1305, and the name travels in the value so a value sealed today
# is read the day the algorithm changes.
SEALED = "xsalsa20poly1305"

# The Vault Key's size and the salt's, both read off the library: a value
# `libsodium` changes cannot drift here.
KEY_SIZE = nacl.secret.SecretBox.KEY_SIZE
SALT_SIZE = nacl.pwhash.argon2id.SALTBYTES

# A FORMA do envelope, para quem precisa achá-lo DENTRO de um texto: o nome do
# algoritmo, os dois-pontos, e o base64 urlsafe que `seal` escreve — o nonce e o
# ciphertext. Ela é montada a partir de `SEALED` para que um algoritmo novo não
# deixe esta expressão para trás, e quem a usa é `envelopes`, que é a única
# porta por onde um envelope é reconhecido sem ser aberto.
_ENVELOPE = re.compile(rf"{SEALED}:[A-Za-z0-9_\-=]+")


class PhraseRefused(ValueError):
    """The Access Phrase cannot be used — and nothing was derived from it.

    The refusal is the product's and it happens BEFORE any derivation: the door
    reads the length and nothing else, so a phrase under the floor spends no
    work and leaves no key behind. A phrase that is not text is refused here
    too: a phrase is what a person types, and nothing else is one.

    The text is English because this layer reaches no `i18n` (§4, layers), which
    imports `core`; the surface that catches this refuses in the active language
    and translates the TYPE, not this sentence.
    """

    def __init__(self) -> None:
        super().__init__(f"the Access Phrase needs at least {MINIMUM} characters")


class ScopeRefused(ValueError):
    """The scope is not a name, so no key was derived from it.

    A derived key is scoped by the canonical name of a service or a purpose
    (§4), and the names a person and a machine write are the ones with a typo in
    them: an empty one, or one carrying its own whitespace, is refused HERE so
    that `notifier` and `notifier ` cannot become two keys in silence. The
    refusal is not a catalogue — the list of the services is §7's and the
    plugins' and lives where they do — it is the shape of a name, and it says
    nothing about which names exist.

    The text is English because this layer reaches no `i18n` (§4, layers), like
    `PhraseRefused`'s.
    """

    def __init__(self) -> None:
        super().__init__("a scope is a canonical name: text, not empty, with no whitespace around it")


class KeyRefused(ValueError):
    """There is no key to seal with — no phrase was typed, or what arrived is
    not a Vault Key.

    `seal` refuses here instead of writing an envelope nothing could ever open;
    `unseal` does not, because a key that does not open a stored envelope is a
    read that has to answer (§4: what is only compared answers, it does not
    raise).
    """

    def __init__(self) -> None:
        super().__init__(f"a Vault Key is {KEY_SIZE} bytes, and that is not what arrived")


def vault_key(phrase: str) -> bytes:
    """The Vault Key the Access Phrase derives — the same key on every machine.

    The derivation is `libsodium`'s password derivation, at the price `password`
    fixes and with a salt read off the phrase itself: nothing stores this key,
    so it has to come back from the phrase alone. A phrase under the floor is
    refused before the salt is drawn and before the cost is paid.
    """
    if not isinstance(phrase, str) or len(phrase) < MINIMUM:
        raise PhraseRefused()
    text = phrase.encode("utf-8")
    salt = nacl.hash.blake2b(
        text, digest_size=SALT_SIZE, encoder=nacl.encoding.RawEncoder
    )
    return nacl.pwhash.argon2id.kdf(
        KEY_SIZE,
        text,
        salt,
        opslimit=password.OPSLIMIT,
        memlimit=password.MEMLIMIT,
    )


def derived_key(vault_key: bytes, scope: str) -> bytes:
    """The key of ONE service or purpose, out of the Vault Key and nothing else.

    §4: "from it the **derived keys**, one per service or purpose", and "the
    Vault Key recovers any lost derived key". Both sentences are this door. It is
    a derivation and not a stored thing — nothing here remembers a derived key
    either — so calling it again is how a key that was lost comes back, and the
    same scope over the same Vault Key is the same key on any machine.

    The scope is the MESSAGE and the Vault Key is the key of the hash, which is
    what tells the two apart: knowing the name of a service tells nobody its key,
    and `notifier` and `spelling-checker` are two keys that open each other's
    nothing. The scope is a canonical NAME — the one thing this door refuses is a
    scope that is not one, so a stray space cannot become a second key in
    silence. `KeyRefused` here is `seal`'s: a Vault Key that is not one is not
    the offer this door can fail to make.
    """
    if not isinstance(scope, str) or not scope.strip() or scope != scope.strip():
        raise ScopeRefused()
    # The size is checked HERE and not left to the library: `blake2b` takes a key
    # of any length up to its own ceiling, so a value that is not a Vault Key
    # would otherwise derive something that looks like a derived key. `KEY_SIZE`
    # is what a Vault Key IS, and `seal` is refused by the same fact.
    if not isinstance(vault_key, bytes) or len(vault_key) != KEY_SIZE:
        raise KeyRefused()
    return nacl.hash.blake2b(
        scope.encode("utf-8"),
        digest_size=KEY_SIZE,
        key=vault_key,
        encoder=nacl.encoding.RawEncoder,
    )


def seal(value: str, key: bytes) -> str:
    """The envelope that carries `value`, sealed with `key`, nonce included.

    The nonce is the library's and is drawn fresh, so two seals of one value are
    two unequal envelopes — a nonce that repeated would be the one mistake this
    primitive cannot make. `key` comes from `vault_key`, or from a key derived
    from it; a key that is not one is refused rather than written into an
    envelope that nothing opens.
    """
    try:
        box = nacl.secret.SecretBox(key)
    except (TypeError, ValueError):
        raise KeyRefused() from None
    raw = bytes(box.encrypt(value.encode("utf-8")))
    return f"{SEALED}:{base64.urlsafe_b64encode(raw).decode('ascii')}"


def seal_bytes(data: bytes, key: bytes) -> bytes:
    """`data` sealed with `key`, nonce included — `seal`'s twin for raw bytes.

    A file is not a value that lands in a row: it needs no self-describing
    header and no base64, so this is the primitive underneath `seal` with
    neither — `SecretBox.encrypt` already carries the nonce ahead of the
    ciphertext, which is the whole of the envelope a byte string needs.
    """
    try:
        box = nacl.secret.SecretBox(key)
    except (TypeError, ValueError):
        raise KeyRefused() from None
    return bytes(box.encrypt(data))


def unseal_bytes(data: bytes, key: bytes) -> bytes | None:
    """The bytes `data` carries, or `None` when this key does not open it.

    `seal_bytes`'s twin, and the same posture as `unseal`: a key that does not
    open it, bytes a hand shortened or lengthened — every way of not opening
    is one answer, and none of them is an exception that takes down the read.
    """
    try:
        return bytes(nacl.secret.SecretBox(key).decrypt(data))
    except (nacl.exceptions.CryptoError, ValueError, TypeError):
        return None


def envelopes(text: str) -> tuple[str, ...]:
    """Todo envelope que um texto carrega, na ordem em que aparece.

    **Quem compõe um texto com valores selados dentro precisa saber ONDE eles
    estão para abri-los depois.** O `configuration.yml` e o `Caddyfile` do
    caminho container são dois desses textos: eles levam os valores inline, e o
    que eles levam é o envelope — o que o container monta é este mesmo texto
    com eles abertos (`at_deploy/environment.py`). A forma é a de `seal`, e ela
    é lida daqui para que quem a procura não invente uma segunda.

    Um texto sem envelope nenhum responde vazio, e isso não é erro: é o caso
    comum, e é o que diz a quem pergunta que não há nada a abrir.
    """
    return tuple(match.group(0) for match in _ENVELOPE.finditer(text))


def unseal(envelope: str, key: bytes) -> str | None:
    """The value `envelope` carries — or `None` when this key does not open it.

    Every way of not opening is the same answer, because a read has to survive
    all of them: the wrong key, an envelope of another algorithm, a value a hand
    edited, a `key` that is not a key. What the door does NOT do is hand back
    anything but the text the sealing key wrote.
    """
    try:
        header, _, payload = envelope.partition(":")
        if header != SEALED:
            return None
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        return nacl.secret.SecretBox(key).decrypt(raw).decode("utf-8")
    except (
        nacl.exceptions.CryptoError,
        ValueError,
        TypeError,
        AttributeError,
        UnicodeError,
    ):
        return None
