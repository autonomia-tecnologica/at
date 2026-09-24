"""The hashed field: the type that stores the derivation and never the value.

§4 gives the schema a third fixed type beside the two about time, and it is the
one whose rule is about what LEAVES a row: what is proved is stored hashed, the
derivation is only ever compared, and no surface is handed the value. The engine
learns the type here — the closed list of keys a declaration may name and the
refusal by the key it named, the write that derives, the mask in the one display
funnel, the door that refuses to hand the value over, the comparison that answers
against the row and the principal that may not be a hashed one — and the WebApp's
record builder stops carrying the stored value, which is the leak the type exists
to close.

The product ships no hashed field yet: the `actor` table is item 9. So the type
is proved on a declaration of the instance's own, which is also what proves the
engine reads the TYPE and not a list of names.

Every test aims AT at a throwaway folder with `AT_ROOT`, so none of them
touches the checkout's own Working Folder, and none of them needs a network.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n, nlu
from at.core import boot, paths, tables
from at.data import schema, store
from at.encryption import password
from at.i18n import tr
from at.ui import ask as door

# What a person types as a credential, and the field it goes into. The label is a
# key the product already carries, so a refusal prints the text a person reads
# instead of a key nobody translated.
SECRET = "segredo-do-ator"
LABEL = "table.task.field.desc"

# "The row's own derivation" for the comparison helper: `None` is a stored value a
# test may hand in on purpose, so it cannot double as the default.
_ROW = object()

# A table of the instance's own. Its `credential` declares the type, and the four
# other keys it names are the rest of the closed list: every one of them has a
# reader — the label in a refusal, `required` in the engine, `max_length` before
# the derivation and `hide` on the page — and a declaration that named one the
# list does not have would be refused by name.
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
        "credential": {
            "label": LABEL,
            "type": "hashed",
            "max_length": 32,
            "hide": ["project"],
        },
    },
}


class HashedCase(unittest.TestCase):
    """A configured folder of its own, and the declared table that lives in it."""

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
        self.declare(KEEPER)

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

    def keeper(self, **field: object) -> dict:
        """The keeper, with its credential field declared the way a test says."""
        table = copy.deepcopy(KEEPER)
        table["fields"]["credential"] = {"label": LABEL, "type": "hashed", **field}
        return table

    def born(self, **values: str) -> dict:
        """A row of the keeper, through the engine's own write door."""
        return tables.create("keeper", {"name": "portão", "credential": SECRET, **values})


class TheWrite(HashedCase):
    """What reaches the store: a derivation, and never the credential."""

    def test_the_store_keeps_the_derivation_and_not_the_credential(self):
        row = self.born()
        self.assertNotEqual(row["credential"], SECRET)
        self.assertIs(password.verify(SECRET, row["credential"]), True)

    def test_the_row_file_read_as_bytes_does_not_carry_the_credential(self):
        # `data/<table>.jsonl` is a file a person opens, copies and commits: the
        # value that only proves must not be readable in it.
        self.born()
        self.assertNotIn(SECRET.encode("utf-8"), self.row_file())

    def test_the_row_file_does_not_carry_the_value_after_an_edit(self):
        row = self.born()
        tables.edit("keeper", row["id"], {"credential": "outro-segredo"})
        self.assertNotIn(b"outro-segredo", self.row_file())

    def test_two_equal_credentials_produce_two_unequal_rows(self):
        # The salt is the library's and travels inside its own answer, so no two
        # rows carrying the same credential carry the same derivation.
        first = self.born(name="um")
        second = self.born(name="dois")
        self.assertNotEqual(first["credential"], second["credential"])

    def test_an_edit_derives_the_new_credential_too(self):
        row = self.born()
        edited = tables.edit("keeper", row["id"], {"credential": "outro"})
        self.assertIs(password.verify("outro", edited["credential"]), True)
        self.assertIs(password.verify(SECRET, edited["credential"]), False)

    def test_a_credential_past_the_ceiling_is_refused(self):
        with self.assertRaises(tables.TableError) as refused:
            self.born(credential="x" * 33)
        self.assertEqual(
            str(refused.exception),
            tr("table.error.too_long", field=tr(LABEL), max=32),
        )

    def test_a_required_credential_missing_is_refused(self):
        self.declare(self.keeper(required=True))
        with self.assertRaises(tables.TableError) as refused:
            tables.create("keeper", {"name": "portão"})
        self.assertEqual(
            str(refused.exception), tr("table.error.required", field=tr(LABEL))
        )

    def test_an_empty_credential_is_not_derived(self):
        # Nothing typed is nothing stored: the field keeps nothing and reads as
        # nothing. A derivation of the empty value would be a credential nobody
        # holds — not even whoever typed nothing — wearing the mask of one.
        row = self.born(credential="")
        self.assertEqual(row["credential"], "")
        self.assertEqual(
            tables.text_of("keeper", "credential", row["credential"]),
            tr("table.word.none"),
        )

    def row_file(self) -> bytes:
        return (paths.data_dir() / "keepers.jsonl").read_bytes()


class TheMask(HashedCase):
    """What a person reads where the credential is: a word, and not the value."""

    def setUp(self):
        super().setUp()
        self.row = self.born()

    def test_the_view_shows_the_mask(self):
        _, answer, _ = door.run("keeper", "view", [str(self.row["id"])])
        self.assertIn(tr("table.word.hashed"), answer)
        self.assertNotIn(self.row["credential"], answer)

    def test_the_listing_shows_the_mask(self):
        _, answer, _ = door.run("keeper", "list", [])
        self.assertIn(tr("table.word.hashed"), answer)
        self.assertNotIn(self.row["credential"], answer)

    def test_the_other_language_speaks_its_own_word(self):
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(
                tables.text_of("keeper", "credential", self.row["credential"]),
                "protected",
            )

    def test_a_row_with_no_value_reads_as_nothing(self):
        # Not as a hidden something: a row that carries no credential has nothing
        # to hide, and the empty text a clearing leaves is the same nothing.
        for nothing in (None, ""):
            with self.subTest(value=nothing):
                self.assertEqual(
                    tables.text_of("keeper", "credential", nothing), tr("table.word.none")
                )


class TheDeclaration(HashedCase):
    """The closed list, and the refusal by the key it named."""

    def test_a_key_outside_the_list_is_refused_by_its_name(self):
        self.declare(self.keeper(method="scrypt"))
        with self.assertRaises(tables.TableError) as refused:
            self.born()
        self.assertEqual(
            str(refused.exception),
            tr("table.error.hashed_key", field=tr(LABEL), named="method"),
        )

    def test_a_default_is_not_a_key_the_type_takes(self):
        # A default is a value the DECLARATION writes, and the declaration is
        # published: a credential with a default would be one in the repository.
        self.declare(self.keeper(default=SECRET))
        with self.assertRaises(tables.TableError) as refused:
            self.born()
        self.assertIn("default", str(refused.exception))

    def test_the_five_keys_the_type_takes_are_the_engine_reads(self):
        self.declare(self.keeper(required=True, max_length=64, hide=["project"]))
        row = self.born()
        self.assertIs(password.verify(SECRET, row["credential"]), True)

    def test_the_table_does_not_go_down_with_the_refusal(self):
        # The refusal is loud at the point of use and the registry keeps the
        # table: a declaration that vanishes would be a blank screen instead.
        self.declare(self.keeper(opslimit=1))
        with self.assertRaises(tables.TableError):
            self.born()
        self.assertIsNotNone(schema.of("keeper"))
        self.assertEqual(tables.create("task", {"text": "comprar pão"})["text"], "comprar pão")


class TheDoor(HashedCase):
    """The engine does not hand the value to a surface."""

    def setUp(self):
        super().setUp()
        self.row = self.born()

    def test_the_value_is_not_handed_over(self):
        # As a credential and as the derivation it became: this is a door, and
        # what it holds is only ever compared.
        for value in (SECRET, self.row["credential"]):
            with self.subTest(value=value):
                with self.assertRaises(tables.TableError) as refused:
                    tables.raw_of("keeper", "credential", value)
                self.assertEqual(
                    str(refused.exception),
                    tr("table.error.hashed_value", field=tr(LABEL)),
                )

    def test_every_other_field_is_handed_over_as_it_is_stored(self):
        self.assertEqual(tables.raw_of("keeper", "name", self.row["name"]), "portão")
        self.assertEqual(tables.raw_of("task", "status", "todo"), "todo")


class TheComparison(HashedCase):
    """The door that answers whether a candidate is what the row proved (§4).

    The engine hands the row over whole — `find` answers it, derivation included —
    and the comparison is built on that: whoever compares passes the stored value
    in, and the door reaches for nothing else. No Access Phrase, no setting, no
    folder: that is what makes a credential verifiable while AT is locked, and
    it is the clause item 14 depends on.
    """

    def setUp(self):
        super().setUp()
        self.row = self.born()

    def compare(self, candidate: object, stored: object = _ROW, field: str = "credential"):
        return tables.verify(
            "keeper",
            field,
            candidate,
            self.row["credential"] if stored is _ROW else stored,
        )

    def test_the_right_candidate_comes_back_true(self):
        self.assertIs(self.compare(SECRET), True)

    def test_the_wrong_candidate_comes_back_false(self):
        self.assertIs(self.compare("outro segredo"), False)

    def test_the_derivation_itself_fails_as_a_candidate(self):
        # The door compares, it does not match strings: the stored derivation
        # handed back as its own candidate derives to something else.
        self.assertIs(self.compare(self.row["credential"]), False)

    def test_a_hand_edited_stored_value_is_no_and_not_an_exception(self):
        # A row a hand edited is exactly a row this door has to answer "no" to:
        # an exception would take down the read that found it.
        for stored in ("", "nao-e-uma-derivacao", "$argon2id$v=19$m=1$xxx$yyy", None, 3):
            with self.subTest(stored=stored):
                self.assertIs(self.compare(SECRET, stored=stored), False)

    def test_a_field_that_is_not_hashed_is_refused_by_name(self):
        with self.assertRaises(tables.TableError) as refused:
            self.compare(SECRET, field="name")
        self.assertEqual(
            str(refused.exception),
            tr("table.error.not_hashed", field=tr("table.task.field.text")),
        )

    def test_a_field_the_table_does_not_declare_is_refused_by_name(self):
        with self.assertRaises(tables.TableError) as refused:
            self.compare(SECRET, field="nope")
        self.assertEqual(
            str(refused.exception),
            tr(
                "table.error.unknown_hashed_field",
                table=tables.table_name("keeper"),
                field="nope",
            ),
        )

    def test_it_hands_the_two_arguments_to_the_comparison_and_nothing_else(self):
        # What reaches the primitive is the candidate and the stored derivation, in
        # that order — no Access Phrase and no setting read on the way.
        with mock.patch.object(password, "verify", return_value=True) as asked:
            self.assertIs(self.compare(SECRET), True)
        asked.assert_called_once_with(SECRET, self.row["credential"])

    def test_the_door_reads_nothing_but_its_two_arguments(self):
        # No Access Phrase, no setting, no folder: the door opens no file to
        # answer, which is what makes a credential verifiable with AT locked —
        # the clause item 14 depends on. The row is already in hand, as the engine
        # hands it over, and the value comes in with it.
        blocked = mock.patch.object(
            store, "load", side_effect=AssertionError("the store was read")
        )
        with blocked, mock.patch.object(
            store, "find", side_effect=AssertionError("the store was read")
        ):
            self.assertIs(self.compare(SECRET), True)


class ThePrincipal(HashedCase):
    """A title is read, and a hashed field is not."""

    def test_a_table_whose_principal_is_hashed_is_refused(self):
        table = self.keeper()
        table["primary"] = "credential"
        self.declare(table)
        with self.assertRaises(tables.TableError) as refused:
            tables.title("keeper", {"name": "portão"})
        self.assertEqual(
            str(refused.exception),
            tr(
                "table.error.hashed_primary",
                table=tables.table_name("keeper"),
                field=tr(LABEL),
            ),
        )


class TheInterpreter(HashedCase):
    """A type the grammar has no reader for is residue, and residue is not a value."""

    def test_the_grammar_has_no_reader_for_the_type(self):
        # One reader per kind, and none of them is this one — which is what makes
        # the credential unspeakable without a single line about credentials.
        self.assertNotIn("hashed", nlu.KINDS)

    def test_a_credential_is_unspeakable_into_the_field(self):
        # The declaration's own words name the table and the field, and the
        # phrase that names the field is residue: what was typed goes where the
        # primary field goes, and never into the credential.
        #
        # The word a person types here is a PLACEHOLDER and not the credential
        # the sentence is about, and it is spelled so on purpose: item 14b's
        # `secret` table took `segredo` into the vocabulary, and a fixture that
        # kept it would be a sentence naming two tables.
        proposal = nlu.propose("cria um keeper com credential abracadabra")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertNotIn("credential", proposal.values)
        self.assertEqual(proposal.values.get("name"), "abracadabra")


class TheTypesThatAlreadyShip(HashedCase):
    """The type that arrives changes nothing about the ones that were here."""

    def test_a_day_still_writes_and_reads_the_way_it_did(self):
        row = tables.create("task", {"text": "comprar pão", "deadline": "2026-10-03"})
        self.assertEqual(row["deadline"], "2026-10-03")
        self.assertEqual(tables.text_of("task", "deadline", row["deadline"]), "03/10/2026")

    def test_an_instant_is_still_written_utc_with_milliseconds(self):
        # The type that was already here writes what it wrote: UTC, with
        # milliseconds, and no locale anywhere near the stored value.
        written = tables.utc(datetime(2026, 9, 22, 20, 40, tzinfo=timezone.utc))
        self.assertEqual(written, "2026-09-22T20:40:00.000Z")


if __name__ == "__main__":
    unittest.main()
