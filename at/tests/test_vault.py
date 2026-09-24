"""The vault: the Access Phrase, the Vault Key and the sealed value (§4, item 14a).

Item 14 is bigger than a session and was cut in two. This is the half that has no
screen: the primitive — the Vault Key the Access Phrase derives, `libsodium`
sealing and opening a value, and the round-trip through `data/secrets.jsonl`,
which is the store the sealed value actually lives in. The other half is the
`secret` table itself: `secret.json` in `data/schema/`, the wrapper that puts the
sealed value in the row, and the intermediate key scoped to one service.

Three things are measured here, and each is a sentence of §4 held to the code:

- **the floor, before anything else.** The Access Phrase has at least 16
  characters and "it is a phrase"; a phrase under the floor is refused BEFORE any
  derivation, so a short one spends no work and leaves no key behind.
- **the derivation comes back.** Nothing stores the Vault Key, so it has to be the
  same key on every machine — which is what tells the vault from `password`, whose
  salt is drawn fresh and travels inside its own answer.
- **what is sealed does not come back in clear.** The envelope carries the
  algorithm and the nonce and nothing else, `unseal` is the only reader, and it
  answers `None` — never an exception, never a value — for anything its key does
  not open.

The entry is measured here too, and it is the reason the vault exists apart from
it: a credential is PROVED with the Access Phrase untyped, because hashed is what
is compared and `authenticate` reaches no vault (§4, item 8).

The product ships no `secret` declaration yet — that is item 14b — so the
round-trip is proved on a declaration of the instance's own, exactly as the
hashed type was before the `actor` table arrived. Every test aims AT at a
throwaway folder with `AT_ROOT`; none of them touches a network or a model.
"""

from __future__ import annotations

import ast
import base64
import inspect
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

import nacl.encoding
import nacl.hash
import nacl.pwhash

from at import i18n
from at.core import actors, boot, paths
from at.data import schema, store
from at.encryption import vault

ROOT = Path(__file__).resolve().parents[2]

# The phrase §4 writes as its own example of what a phrase is, and the value a
# service credential would be — the thing the vault exists to carry.
PHRASE = "mariazinha comeu todo o pudim"
VALUE = "credencial-do-serviço-de-exemplo"

# The floor as a case and not as a guess: one phrase exactly at it, one under.
AT_THE_FLOOR = "x" * 16
UNDER = "x" * 15

# A key of the right size that is not the Vault Key: an envelope has to refuse it
# without any derivation running.
FOREIGN = b"\x00" * 32

# A declaration of the instance's own, so `store.path("secret")` resolves and the
# sealed value can round-trip through `data/secrets.jsonl` before item 14b ships
# the product's own `secret.json`. Its `store` is the one the item names, and the
# labels are keys the product already carries.
SECRET = {
    "id": "secret",
    "order": 99,
    "name": {"one": "table.task.name.one", "many": "table.task.name.many"},
    "store": "data/secrets.jsonl",
    "primary": "name",
    "columns": ["name", "value"],
    "fields": {
        "id": {"label": "table.field.id"},
        "name": {"label": "table.task.field.text"},
        "value": {"label": "table.task.field.desc"},
    },
}


class ThePhrase(unittest.TestCase):
    """The floor, and the derivation that has to come back the same."""

    def test_the_floor_is_the_one_4_writes(self):
        self.assertEqual(vault.MINIMUM, 16)

    def test_a_phrase_at_the_floor_derives_a_vault_key(self):
        key = vault.vault_key(AT_THE_FLOOR)
        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), vault.KEY_SIZE)

    def test_under_the_floor_is_refused(self):
        for phrase in (UNDER, "", " ", None, 3, b"x" * 40):
            with self.subTest(phrase=phrase):
                with self.assertRaises(vault.PhraseRefused):
                    vault.vault_key(phrase)

    def test_the_refusal_happens_before_any_derivation(self):
        # "The refusal is AT's and it happens BEFORE any derivation": neither
        # the salt is drawn nor the cost is paid, so a phrase under the floor
        # leaves no key behind.
        with mock.patch.object(nacl.hash, "blake2b") as salt, mock.patch.object(
            nacl.pwhash.argon2id, "kdf"
        ) as cost:
            with self.assertRaises(vault.PhraseRefused):
                vault.vault_key(UNDER)
        self.assertFalse(salt.called)
        self.assertFalse(cost.called)

    def test_the_same_phrase_derives_the_same_key(self):
        # Nothing stores the Vault Key, so it has to come back from the phrase
        # alone — the whole difference from `password.derive`, whose two
        # derivations of one text are unequal on purpose.
        self.assertEqual(vault.vault_key(PHRASE), vault.vault_key(PHRASE))

    def test_two_phrases_derive_two_keys(self):
        self.assertNotEqual(vault.vault_key(PHRASE), vault.vault_key(AT_THE_FLOOR))

    def test_the_key_is_not_a_bare_digest_of_the_phrase(self):
        # The key costs what `password` fixes. A plain digest of the same phrase
        # would be a key drawn in microseconds, and brute-forced the same way.
        bare = nacl.hash.blake2b(
            PHRASE.encode("utf-8"),
            digest_size=vault.KEY_SIZE,
            encoder=nacl.encoding.RawEncoder,
        )
        self.assertNotEqual(vault.vault_key(PHRASE), bare)

    def test_no_caller_names_the_price(self):
        # A knob that changed the cost would be "no choice per field" with a hole
        # in it: the price has one home, and none of these three doors names one.
        self.assertEqual(list(inspect.signature(vault.vault_key).parameters), ["phrase"])
        self.assertEqual(list(inspect.signature(vault.seal).parameters), ["value", "key"])
        self.assertEqual(
            list(inspect.signature(vault.unseal).parameters), ["envelope", "key"]
        )


class TheEnvelope(unittest.TestCase):
    """What `seal` writes, and what `unseal` answers."""

    @classmethod
    def setUpClass(cls):
        cls.key = vault.vault_key(PHRASE)

    def test_the_value_round_trips(self):
        self.assertEqual(vault.unseal(vault.seal(VALUE, self.key), self.key), VALUE)

    def test_the_value_comes_back_with_its_accents(self):
        accent = "açúcar e ção"
        self.assertEqual(vault.unseal(vault.seal(accent, self.key), self.key), accent)

    def test_the_envelope_names_the_algorithm(self):
        self.assertTrue(vault.seal(VALUE, self.key).startswith(f"{vault.SEALED}:"))

    def test_the_envelope_carries_no_cleartext(self):
        self.assertNotIn(VALUE, vault.seal(VALUE, self.key))

    def test_it_is_one_json_scalar(self):
        # The envelope is what a row carries in a `.jsonl` line: a single text,
        # with no newline and no structure the writer would have to know about.
        sealed = vault.seal(VALUE, self.key)
        self.assertEqual(json.loads(json.dumps({"value": sealed}))["value"], sealed)
        self.assertNotIn("\n", sealed)

    def test_two_seals_of_one_value_are_two_envelopes(self):
        # The nonce is the library's and is drawn fresh. A nonce that repeated
        # would be the one mistake this primitive cannot make.
        self.assertNotEqual(vault.seal(VALUE, self.key), vault.seal(VALUE, self.key))

    def test_opening_is_deterministic(self):
        sealed = vault.seal(VALUE, self.key)
        self.assertEqual(vault.unseal(sealed, self.key), vault.unseal(sealed, self.key))

    def test_another_key_does_not_open_it(self):
        self.assertIsNone(vault.unseal(vault.seal(VALUE, self.key), FOREIGN))

    def test_a_key_of_its_own_opens_what_it_sealed(self):
        # §4's derived key, reduced to what it is here: a key recovered from the
        # Vault Key alone, and nothing else. What it seals, it opens; the Vault Key
        # itself does not, which is the scope working.
        derived = nacl.hash.blake2b(
            self.key, digest_size=vault.KEY_SIZE, encoder=nacl.encoding.RawEncoder
        )
        sealed = vault.seal(VALUE, derived)
        self.assertEqual(vault.unseal(sealed, derived), VALUE)
        self.assertIsNone(vault.unseal(sealed, self.key))

    def test_no_key_at_all_does_not_open_it(self):
        # The answer when the Access Phrase was not typed: the value does not
        # come back, and nothing raises over a read.
        sealed = vault.seal(VALUE, self.key)
        for key in (None, b"", b"curta"):
            with self.subTest(key=key):
                self.assertIsNone(vault.unseal(sealed, key))

    def test_a_hand_edited_envelope_is_no_and_not_an_exception(self):
        garbage = base64.urlsafe_b64encode(b"nao-e-um-envelope").decode("ascii")
        for sealed in (
            "",
            "nao-e-um-envelope",
            f"{vault.SEALED}:",
            f"{vault.SEALED}:{garbage}",
            f"outro-algoritmo:{garbage}",
            None,
            3,
            b"bytes",
        ):
            with self.subTest(sealed=sealed):
                self.assertIsNone(vault.unseal(sealed, self.key))

    def test_sealing_with_no_key_is_refused(self):
        # The other side of the same rule: sealing with nothing would write an
        # envelope nothing can open, so the WRITE refuses where the read answers.
        for key in (None, b"", b"curta"):
            with self.subTest(key=key):
                with self.assertRaises(vault.KeyRefused):
                    vault.seal(VALUE, key)


class VaultCase(unittest.TestCase):
    """A Working Folder of its own, born by this release."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        # The declarations are cached per process and this folder is gone: a
        # cache left behind would hand the next test a table that is not there.
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def declare(self, table: dict) -> None:
        where = paths.data_dir() / schema.SCHEMA_DIR / f"{table['id']}.json"
        where.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()


class TheRoundTrip(VaultCase):
    """The sealed value, through `data/secrets.jsonl` and back."""

    def setUp(self):
        super().setUp()
        self.declare(SECRET)
        self.key = vault.vault_key(PHRASE)

    def store_row(self) -> dict:
        """One row of the secret table, written the way the store writes one."""
        row = {"id": 1, "name": "serviço-de-exemplo", "value": vault.seal(VALUE, self.key)}
        store.save("secret", [row])
        return row

    def row_file(self) -> Path:
        return paths.data_dir() / "secrets.jsonl"

    def test_the_store_is_the_file_the_item_names(self):
        self.assertEqual(store.path("secret"), self.row_file())

    def test_the_sealed_value_round_trips_through_the_store(self):
        row = self.store_row()
        back = store.load("secret")
        self.assertEqual([row], back)
        self.assertEqual(vault.unseal(back[0]["value"], self.key), VALUE)

    def test_the_phrase_opens_the_row_again_on_a_fresh_derivation(self):
        # The key is not in the file and not in memory: it is drawn again from
        # the phrase, and it is the one that opens what the earlier one sealed.
        self.store_row()
        again = vault.vault_key(PHRASE)
        self.assertEqual(vault.unseal(store.load("secret")[0]["value"], again), VALUE)

    def test_the_row_file_carries_neither_the_value_nor_the_phrase(self):
        # `data/secrets.jsonl` is a file a person opens, copies and commits: what
        # AT USES is sealed in it, and the phrase that opens it is nowhere.
        self.store_row()
        raw = self.row_file().read_bytes()
        self.assertNotIn(VALUE.encode("utf-8"), raw)
        self.assertNotIn(PHRASE.encode("utf-8"), raw)

    def test_the_envelope_survives_the_row_as_a_text(self):
        row = self.store_row()
        self.assertIsInstance(row["value"], str)
        self.assertTrue(row["value"].startswith(f"{vault.SEALED}:"))


class TheCut(VaultCase):
    """Where this slice stops, said out loud.

    The product ships no `secret` declaration and nothing calls the vault: both
    are item 14b's — `secret.json` in `data/schema/`, the wrapper that puts the
    sealed value in the row. A session that lands them deletes these two tests,
    which is the point: crossing the cut is a decision, not a drift.
    """

    def test_the_product_ships_no_secret_declaration(self):
        self.assertIsNone(store.path("secret"))
        self.assertFalse((paths.data_dir() / schema.SCHEMA_DIR / "secret.json").exists())

    def test_nothing_calls_the_vault_yet(self):
        callers = []
        for root in (ROOT / "at", ROOT / "at_deploy"):
            for path in root.rglob("*.py"):
                if "tests" not in path.parts and reaches_vault(path):
                    callers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(callers, [])


def reaches_vault(path: Path) -> bool:
    """Whether the module imports `at.encryption.vault` — the caller's mark."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "at.encryption":
            if any(alias.name == "vault" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name in ("at.encryption.vault", "vault") for alias in node.names):
                return True
    return False


class TheEntry(VaultCase):
    """The credential is proved with the Access Phrase untyped (§4, item 8)."""

    def test_the_module_that_authenticates_reaches_no_vault(self):
        # §4: "a verificação de uma credencial que chega não depende da Frase de
        # Acesso" — otherwise AT only starts when somebody types it. The door
        # reads its two arguments and nothing else, and this is that sentence
        # read off the source.
        tree = ast.parse((ROOT / "at/core/actors.py").read_text(encoding="utf-8"))
        reached: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                reached.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                reached.add(node.module)
        self.assertNotIn("at.encryption.vault", reached)

    def test_a_credential_is_proved_with_no_phrase_typed(self):
        # No phrase was typed anywhere in this folder, and the door works: what
        # is compared is hashed, and the vault is not on the way in.
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.assertIsNotNone(actors.authenticate("Rafael", "uma-frase-bem-longa"))
        self.assertIsNone(actors.authenticate("Rafael", "outra-frase-bem-longa"))


class TheLayer(unittest.TestCase):
    """The dependency points inward (§4): `encryption` reaches no `core`, no `data`."""

    def test_the_vault_reaches_libsodium_and_the_price_and_nothing_else(self):
        tree = ast.parse((ROOT / "at/encryption/vault.py").read_text(encoding="utf-8"))
        reached: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                reached.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                reached.add(node.module)
        self.assertEqual(
            {name.split(".")[0] for name in reached} - {"__future__"},
            {"base64", "nacl", "at"},
        )
        self.assertEqual({name for name in reached if name.startswith("at.")}, {"at.encryption"})


if __name__ == "__main__":
    unittest.main()
