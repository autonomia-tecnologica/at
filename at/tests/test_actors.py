"""The `actor` and `role` tables, and the first administrator (item 9).

The first administrator is the one row of the product that may never be seeded:
a default credential is a published password, and the item says so with all the
letters. What these tests hold still is the rest of the promise — the two system
tables shipping with the product, the engine's row born with the folder, the
credential going in hashed and never coming back out, and a folder with nobody
to enter it not exposing at all.

The credential is the field item 8 gave the schema, so what is checked here is
the DOOR and not the derivation: the engine derives on the way in, `raw_of`
refuses to hand it over, and `verify` is the only comparison.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, migrations, permissions, tables
from at.data import schema, store
from at.ui import ask as door
from at.ui.cli import OK, REFUSED, main

GOOD = "uma-frase-bem-longa"


class ActorCase(unittest.TestCase):
    """A folder born by this release, so the declarations are the product's."""

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

    def catch_up_from_scratch(self) -> None:
        """Forget the stamp, so the migrations run as on the first start after a
        binary swap — which is the state this whole door exists for."""
        (self.root / "App" / "migrations").unlink()
        schema.reset()


class TheDeclarations(ActorCase):
    def test_both_tables_ship_with_the_product_and_land_in_the_folder(self):
        self.assertIn("actor", schema.bundled())
        self.assertIn("role", schema.bundled())
        for table in ("actor", "role"):
            self.assertTrue((self.root / "Tabelas" / "schema" / f"{table}.json").is_file())

    def test_the_engine_honours_them(self):
        """Asserting the file exists would only agree with the file; a listing is
        what says the engine reads the declaration it was handed."""
        code, answer, _ = door.run("actor", "list", [])
        self.assertEqual(code, OK)
        self.assertIn("ACTOR-1", answer)
        # A table with no rows still answers as a table, not as a failure.
        code, answer, _ = door.run("role", "list", [])
        self.assertEqual(code, OK)
        self.assertEqual(answer, i18n.tr("table.word.empty"))

    def test_the_type_is_a_closed_vocabulary(self):
        for value in ("person", "engine", "agent"):
            self.assertIn(value, tables.enum_values("actor", "type"))
        with self.assertRaises(tables.TableError):
            tables.create("actor", {"name": "x", "type": "robot"})

    def test_the_type_speaks_both_languages(self):
        for code in i18n.SUPPORTED:
            written = i18n.text("table.actor.field.type.person", code)
            self.assertTrue(written)
            self.assertNotEqual(written, "table.actor.field.type.person")

    def test_the_principal_field_is_the_identity_and_not_the_credential(self):
        # A title is READ, and a derivation is not: a table whose principal is
        # hashed is refused before any row can carry one (`tables.title`).
        self.assertEqual(schema.primary("actor"), "name")
        self.assertFalse(tables.hashed("actor", schema.primary("actor")))


class TheEngineRow(ActorCase):
    def test_the_folder_is_born_with_it(self):
        self.assertIsNotNone(actors.engine_row())

    def test_seeding_twice_does_not_duplicate_it(self):
        self.assertIsNone(actors.seed_engine())
        self.assertEqual(len(store.load("actor")), 1)

    def test_the_engine_carries_no_role_and_no_credential(self):
        row = actors.engine_row()
        self.assertIsNone(row.get("role"))
        self.assertFalse(row.get("credential"))

    def test_it_does_not_count_as_somebody_entering(self):
        self.assertEqual(actors.people(), [])
        self.assertFalse(actors.can_expose())


class TheFirstAdmin(ActorCase):
    def test_it_brings_the_role_with_the_whole_catalogue(self):
        actors.create_admin("Rafael", GOOD)
        roles = store.load("role")
        self.assertEqual([row["name"] for row in roles], [actors.ADMIN_ROLE])
        self.assertEqual(roles[0]["permissions"], permissions.all_permissions())

    def test_it_creates_the_person_pointing_at_the_role(self):
        actors.create_admin("Rafael", GOOD)
        person = actors.admins()[0]
        self.assertEqual(person["type"], "person")
        self.assertEqual(person["name"], "Rafael")
        self.assertEqual(person["role"], store.load("role")[0]["id"])
        self.assertEqual(tables.title("actor", person), "Rafael")

    def test_the_credential_never_comes_back(self):
        actors.create_admin("Rafael", GOOD)
        row = actors.admins()[0]
        self.assertNotIn(GOOD, row["credential"])
        with self.assertRaises(tables.TableError):
            tables.raw_of("actor", "credential", row["credential"])

    def test_the_credential_is_verified_by_comparison(self):
        actors.create_admin("Rafael", GOOD)
        stored = actors.admins()[0]["credential"]
        self.assertTrue(tables.verify("actor", "credential", GOOD, stored))
        self.assertFalse(tables.verify("actor", "credential", "outra-coisa", stored))

    def test_two_equal_credentials_are_two_unequal_derivations(self):
        # The derivation draws its own salt and carries it in its own answer,
        # which is the whole reason the item asks for a derivation and not a
        # digest (§4, item 8).
        actors.create_admin("Rafael", GOOD)
        actors.create_admin("Outra pessoa", GOOD)
        first, second = (row["credential"] for row in actors.admins())
        self.assertNotEqual(first, second)

    def test_a_short_credential_is_refused_and_writes_nothing(self):
        with self.assertRaises(actors.AdminError):
            actors.create_admin("Rafael", "curta")
        self.assertEqual(store.load("actor"), [actors.engine_row()])

    def test_it_makes_the_folder_expose(self):
        self.assertFalse(actors.can_expose())
        actors.create_admin("Rafael", GOOD)
        self.assertTrue(actors.can_expose())


class TheEntrance(ActorCase):
    """`actors.authenticate` — the question the Forms door asks (§3, item 10).

    What is held still is the SHAPE of the answer: the row when the derivation
    proves it, and `None` for every other way in — a name nobody wears, a name
    that wears no credential, a machine, and a declaration the folder broke. The
    derivation itself is item 8's, so what is checked here is the door.
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)

    def test_the_credential_that_proves_it_answers_the_row(self):
        row = actors.authenticate("Rafael", GOOD)
        self.assertIsNotNone(row)
        self.assertEqual(tables.title("actor", row), "Rafael")

    def test_the_wrong_credential_answers_nothing(self):
        self.assertIsNone(actors.authenticate("Rafael", "outra-frase-longa"))

    def test_a_name_nobody_wears_answers_nothing(self):
        self.assertIsNone(actors.authenticate("Ninguém", GOOD))

    def test_the_miss_spends_a_derivation_like_the_hit(self):
        # The comparison is what costs, and finding the row is what does not: a
        # miss that skipped the derivation would answer in a blink while a hit
        # took a tenth of a second, and the clock would enumerate the actors.
        # The miss compares against a derivation of nothing, and this is that it
        # is a derivation and not a placeholder string.
        self.assertTrue(actors._nobody().startswith("$argon2id$"))
        self.assertFalse(tables.verify("actor", "credential", GOOD, actors._nobody()))

    def test_the_name_is_forgiven_its_whitespace_and_the_credential_is_not(self):
        # A name is an identity a pasted line carries spaces around; a
        # credential is compared as it was written, because forgiving a space
        # there would be this door deciding what the person meant.
        self.assertIsNotNone(actors.authenticate("  Rafael  ", GOOD))
        self.assertIsNone(actors.authenticate("Rafael", GOOD + " "))
        self.assertIsNone(actors.authenticate("Rafael", GOOD[:-1]))

    def test_a_person_with_no_credential_does_not_enter(self):
        with redirect_stdout(io.StringIO()):
            tables.create("actor", {"name": "Sem credencial", "type": "person"})
        self.assertIsNone(actors.authenticate("Sem credencial", ""))
        self.assertIsNone(actors.authenticate("Sem credencial", GOOD))

    def test_the_engine_does_not_enter_by_this_door(self):
        self.assertIsNone(actors.authenticate(actors.ENGINE_NAME, GOOD))

    def test_a_machine_does_not_enter_by_this_door(self):
        # The `agent` is one of §3's four ways in and it is NOT this one: its
        # credential is the machine's, and the transport that proves it is the
        # second slice of item 10. `people()` is what says so.
        with redirect_stdout(io.StringIO()):
            tables.create(
                "actor", {"name": "robô", "type": "agent", "credential": GOOD}
            )
        self.assertIsNone(actors.authenticate("robô", GOOD))

    def test_a_broken_declaration_refuses_rather_than_takes_the_door_down(self):
        # `tables.verify` raises by DESIGN when the folder's copy names a key the
        # closed list lacks — the case `TheHashedField` already covers on the
        # page. At the door of entry that refusal is a `None`: a folder with a
        # hand-edited declaration is a folder nobody enters, and not a server
        # that dies on the first person who tries.
        opened = self.root / "Tabelas" / "schema" / "actor.json"
        declared = json.loads(opened.read_text(encoding="utf-8"))
        declared["fields"]["credential"]["method"] = "scrypt"
        opened.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()
        self.addCleanup(schema.reset)

        with self.assertRaises(tables.TableError):
            tables.verify("actor", "credential", GOOD, "x")
        self.assertIsNone(actors.authenticate("Rafael", GOOD))


class TheGateDoor(ActorCase):
    """`actors.asserted` — §7b's way in, which asserts a name and no credential.

    On the container path the gate proved the person: Authelia holds the
    credential and the proof, and what reaches AT is an identity. What is held
    still here is that the identity answers a ROW — the folder's own, with the
    role the ceiling is read from — and that this door asks nothing else. The
    gate secret is not read here on purpose: it is a fact about the REQUEST, and
    the surface proves it before asking (`ui/webapp/app.py`).
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)

    def test_the_asserted_name_answers_the_row_and_its_ceiling(self):
        row = actors.asserted("Rafael")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(store.number_of(row), store.number_of(actors.admins()[0]))
        self.assertIsNotNone(actors.role_of(row))
        self.assertTrue(actors.may(row, "setting:read"))

    def test_the_name_is_forgiven_its_whitespace_like_every_other_door(self):
        self.assertIsNotNone(actors.asserted("  Rafael  "))

    def test_a_name_nobody_wears_answers_nothing(self):
        self.assertIsNone(actors.asserted("Ninguém"))

    def test_the_engine_does_not_enter_by_this_door(self):
        self.assertIsNone(actors.asserted(actors.ENGINE_NAME))

    def test_a_machine_does_not_enter_by_this_door(self):
        # A machine enters by its token alone, and it is not a name a header can
        # assert.
        with redirect_stdout(io.StringIO()):
            tables.create(
                "actor", {"name": "robô", "type": "agent", "credential": GOOD}
            )
        self.assertIsNone(actors.asserted("robô"))

    def test_the_derivation_of_the_row_is_not_this_doors_question(self):
        # §7b's split: the credential the gate proves is Authelia's, so a row of
        # AT's own is an identity AT knows whatever its own derivation holds
        # — and what caps it is the role, which is read from the row either way.
        with redirect_stdout(io.StringIO()):
            tables.create("actor", {"name": "Sem credencial", "type": "person"})
        self.assertIsNotNone(actors.asserted("Sem credencial"))


class TheMachineDoor(ActorCase):
    """`actors.authenticate_agent` — the machine's credential (item 10).

    The wire carries the token ALONE, so the row is found by comparison and not
    by a name. What is held still is the shape of the answer, the token going in
    hashed like any other credential, and the separation of the two doors: a
    person does not enter by the machine's, and a machine does not enter by
    Forms.
    """

    TOKEN = "um-token-de-maquina"
    AGENT = "robô"

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)
        role = store.load("role")[0]
        tables.create(
            "actor",
            {
                "name": self.AGENT,
                "type": "agent",
                "role": str(store.number_of(role)),
                "credential": self.TOKEN,
            },
        )

    def test_the_token_answers_the_row(self):
        row = actors.authenticate_agent(self.TOKEN)
        self.assertIsNotNone(row)
        self.assertEqual(tables.title("actor", row), self.AGENT)

    def test_the_wrong_token_answers_nothing(self):
        self.assertIsNone(actors.authenticate_agent("outro-token"))
        self.assertIsNone(actors.authenticate_agent(""))

    def test_the_two_doors_do_not_borrow_each_other(self):
        # The mirror of `TheEntrance.test_a_machine_does_not_enter_by_this_door`:
        # the person's credential is not a token, the machine's token is not a
        # name's credential, and each door reads only its own rows.
        self.assertIsNone(actors.authenticate(self.AGENT, self.TOKEN))
        self.assertIsNone(actors.authenticate_agent(GOOD))
        self.assertIsNotNone(actors.authenticate("Rafael", GOOD))
        self.assertIsNotNone(actors.authenticate_agent(self.TOKEN))

    def test_the_engine_does_not_enter_by_the_machines_door(self):
        self.assertIsNone(actors.authenticate_agent(actors.ENGINE_NAME))

    def test_the_token_never_comes_back(self):
        row = next(one for one in actors.agents() if one["name"] == self.AGENT)
        self.assertNotIn(self.TOKEN, row["credential"])
        with self.assertRaises(tables.TableError):
            tables.raw_of("actor", "credential", row["credential"])

    def test_the_agent_carries_the_role_it_was_born_with(self):
        # A machine is an actor like any other: the ceiling item 11 will read
        # comes off the row, and the row points at the role it declared.
        row = actors.authenticate_agent(self.TOKEN)
        self.assertEqual(row["role"], store.load("role")[0]["id"])

    def test_a_broken_declaration_refuses_rather_than_takes_the_door_down(self):
        # The mirror of the Forms door's own: a folder with a hand-edited
        # declaration is a folder no machine enters, and not a server that dies
        # on the first machine that tries.
        opened = self.root / "Tabelas" / "schema" / "actor.json"
        declared = json.loads(opened.read_text(encoding="utf-8"))
        declared["fields"]["credential"]["method"] = "scrypt"
        opened.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()
        self.addCleanup(schema.reset)

        with self.assertRaises(tables.TableError):
            tables.verify("actor", "credential", self.TOKEN, "x")
        self.assertIsNone(actors.authenticate_agent(self.TOKEN))


class TheMachineCounts(ActorCase):
    """A machine is somebody to enter, so a folder that has one exposes.

    "Sem ator nenhum o AT não expõe" (§3): the engine does not enter and does
    not count; the machine enters by its own door (item 10) and counts like a
    person — as long as it carries the credential that door proves.
    """

    def test_a_folder_whose_only_credential_is_a_machine_exposes(self):
        self.assertFalse(actors.can_expose())
        with redirect_stdout(io.StringIO()):
            tables.create("actor", {"name": "robô", "type": "agent", "credential": GOOD})
        self.assertTrue(actors.can_expose())

    def test_a_machine_with_no_credential_does_not_count(self):
        with redirect_stdout(io.StringIO()):
            tables.create("actor", {"name": "robô", "type": "agent"})
        self.assertFalse(actors.can_expose())
        self.assertEqual(len(actors.agents()), 1)
        self.assertEqual(actors.entries(), [])


class TheMachineCredential(ActorCase):
    """`actors.mint_agent`, `reissue_agent` and `revoke_agent` — the surface item
    10 left without one (item 11).

    A machine's token is DRAWN and not typed: what a person would have to invent
    is what AT makes, and it is shown once and kept hashed like every other
    credential (`tables._hashed`).
    """

    AGENT = "robô"

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)
        self.role = actors.admin_role()

    def minted(self, name: str = AGENT) -> tuple[dict, str]:
        return actors.mint_agent(name, store.number_of(self.role))

    def test_the_token_is_drawn_and_the_row_keeps_only_the_derivation(self):
        row, token = self.minted()
        self.assertTrue(token)
        self.assertEqual(row["type"], "agent")
        self.assertNotIn(token, row["credential"])
        with self.assertRaises(tables.TableError):
            tables.raw_of("actor", "credential", row["credential"])

    def test_a_drawn_token_opens_the_machines_door(self):
        _, token = self.minted()
        found = actors.authenticate_agent(token)
        self.assertIsNotNone(found)
        self.assertEqual(tables.title("actor", found), self.AGENT)

    def test_two_mints_are_two_different_tokens(self):
        _, first = self.minted("um")
        _, second = self.minted("dois")
        self.assertNotEqual(first, second)
        # Each token opens ITS row: the door compares against every machine's
        # derivation and answers with the one that proved (`authenticate_agent`).
        self.assertEqual(tables.title("actor", actors.authenticate_agent(first)), "um")
        self.assertEqual(tables.title("actor", actors.authenticate_agent(second)), "dois")

    def test_it_carries_the_role_it_was_minted_with(self):
        row, _ = self.minted()
        self.assertEqual(store.number_of(self.role), row["role"])
        self.assertTrue(actors.may(row, "role:edit"))

    def test_a_role_nobody_wears_is_refused_by_name_and_mints_nothing(self):
        with self.assertRaises(actors.MachineError) as refused:
            actors.mint_agent(self.AGENT, 99)
        self.assertEqual(refused.exception.key, "error.role_unknown")
        self.assertEqual(actors.agents(), [])

    def test_a_machine_with_no_credential_does_not_count_as_an_entry(self):
        # The administrator is one entry already (`create_admin`), and it is the
        # only one: a machine with nothing to prove is not a way in.
        self.assertEqual([row["type"] for row in actors.entries()], ["person"])
        tables.create("actor", {"name": "sem token", "type": "agent"})
        self.assertEqual([row["type"] for row in actors.entries()], ["person"])

    def test_the_minted_machine_is_somebody_to_enter(self):
        self.assertNotIn(self.AGENT, [row["name"] for row in actors.entries()])
        self.minted()
        self.assertIn(self.AGENT, [row["name"] for row in actors.entries()])

    def test_revoking_takes_the_credential_and_leaves_the_row(self):
        row, token = self.minted()
        actors.revoke_agent(row["id"])
        self.assertIsNone(actors.authenticate_agent(token))
        self.assertNotIn(self.AGENT, [row["name"] for row in actors.entries()])
        self.assertEqual(len(actors.agents()), 1)  # the row stands
        self.assertFalse(actors.agent_row(row["id"])["credential"])

    def test_revoking_what_carries_nothing_is_refused_by_name(self):
        row, _ = self.minted()
        actors.revoke_agent(row["id"])
        with self.assertRaises(actors.MachineError) as refused:
            actors.revoke_agent(row["id"])
        self.assertEqual(refused.exception.key, "error.not_credential")

    def test_a_person_is_not_a_machine_and_both_doors_say_so(self):
        person = actors.admins()[0]
        for door_call in (
            lambda: actors.revoke_agent(person["id"]),
            lambda: actors.reissue_agent(person["id"]),
        ):
            with self.subTest(door=str(door_call)):
                with self.assertRaises(actors.MachineError) as refused:
                    door_call()
                self.assertEqual(refused.exception.key, "error.not_agent")
        self.assertIsNotNone(actors.authenticate("Rafael", GOOD))

    def test_a_reissued_token_replaces_the_one_that_was(self):
        row, first = self.minted()
        _, second = actors.reissue_agent(row["id"])
        self.assertNotEqual(first, second)
        self.assertIsNone(actors.authenticate_agent(first))
        self.assertIsNotNone(actors.authenticate_agent(second))
        self.assertEqual(len(actors.agents()), 1)  # and no second row was born


class TheInterpreterCeiling(ActorCase):
    """The door of the interpreter carries the ceiling (§5, item 11).

    "O que ela pode propor é o que ela já pode fazer": the proposal is an action
    on a table, and the actor's role is asked about the permission that action IS
    — through `actors.may`, the same door the routes read. An actor that is not
    there is the folder that asks nobody, and the door answers as it always did.
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)
        with redirect_stdout(io.StringIO()):
            tables.create("task", {"text": "primeira"})

    def wearing(self, carried: str) -> dict:
        role = tables.create("role", {"name": f"papel-{len(store.load('role'))}",
                                      "permissions": carried})
        return tables.create(
            "actor",
            {"name": "Leitor", "type": "person", "role": str(store.number_of(role)),
             "credential": GOOD},
        )

    def test_the_act_the_role_does_not_carry_is_refused_before_the_proposal(self):
        row = self.wearing("nlu:ask,task:list")
        result = door.ask("cria uma tarefa pra hoje", actor=row)
        self.assertEqual(result.kind, "refused")
        self.assertIsNone(result.proposal)  # nothing was proposed and nothing ran
        self.assertEqual(result.code, REFUSED)
        self.assertEqual(
            result.text,
            i18n.tr("permission.denied", permission=permissions.label("task:create")),
        )
        self.assertEqual(len(tables.rows("task")), 1)

    def test_the_act_the_role_carries_runs(self):
        row = self.wearing("nlu:ask,task:create")
        result = door.ask("cria uma tarefa pra hoje", actor=row)
        self.assertEqual(result.kind, "answer")
        self.assertTrue(result.proposal)
        self.assertEqual(len(tables.rows("task")), 2)

    def test_reading_is_capped_like_writing(self):
        # A `list` is a table action like any other, and the permission is the
        # route's own form: `task:list`.
        row = self.wearing("nlu:ask")
        result = door.ask("lista as tarefas", actor=row)
        self.assertEqual(result.kind, "refused")
        self.assertEqual(
            result.text,
            i18n.tr("permission.denied", permission=permissions.label("task:list")),
        )

    def test_the_administrator_reaches_both(self):
        row = actors.admins()[0]
        self.assertEqual(door.ask("cria uma tarefa pra hoje", actor=row).kind, "answer")
        self.assertEqual(door.ask("lista as tarefas", actor=row).kind, "answer")

    def test_no_actor_is_no_ceiling(self):
        # The `cli` asks with nobody proved, and the folder that asks nobody has
        # no actor either: both are where the route answers as it always did.
        result = door.ask("cria uma tarefa pra hoje")
        self.assertEqual(result.kind, "answer")
        self.assertEqual(len(tables.rows("task")), 2)

    def test_a_sentence_the_interpreter_did_not_read_is_refused_by_name(self):
        # The ceiling never gets asked about a sentence that became no proposal:
        # the interpreter's own refusal is what a person reads.
        row = self.wearing("nlu:ask")
        result = door.ask("banana", actor=row)
        self.assertEqual(result.kind, "refused")
        self.assertIn("banana", result.text)


class TheCatalogue(ActorCase):
    def test_the_tables_are_in_it_and_so_are_the_settings(self):
        found = permissions.catalogue()
        for table in ("actor", "role", "task"):
            self.assertIn(table, found)
            self.assertEqual(found[table], tables.ACTIONS)
        self.assertEqual(found["setting"], ("read", "edit"))

    def test_the_prose_and_the_interpreter_are_in_it_too(self):
        # The two objects that are not a table and that the WebApp reaches: the
        # prose layer and the interpreter's door. `/api/tree`, `/api/file` and
        # `/api/ask` demand them (item 11), and without them a role carrying
        # nothing would go on reading and writing every file through the API.
        found = permissions.catalogue()
        self.assertEqual(found["prose"], ("read", "edit"))
        self.assertEqual(found["nlu"], ("ask",))
        for permission in ("prose:read", "prose:edit", "nlu:ask"):
            with self.subTest(permission=permission):
                self.assertTrue(permissions.is_known(permission))

    def test_the_objects_no_route_reaches_yet_are_declared_all_the_same(self):
        # §4 lists them among the objects — "the settings, the services, the
        # plugins and the interpreter's vocabulary" — and the screens that move
        # them are items 13, 15 and 16's. Declaring them now is what keeps a role
        # written against a name that EXISTS from meeting a catalogue that grows
        # under it, and `is_known` is the difference this holds still.
        found = permissions.catalogue()
        for obj in ("service", "plugin", "vocabulary"):
            with self.subTest(object=obj):
                self.assertEqual(found[obj], ("read", "edit"))
        for permission in ("service:edit", "plugin:edit", "vocabulary:edit"):
            with self.subTest(permission=permission):
                self.assertTrue(permissions.is_known(permission))

    def test_every_object_answers_with_a_word_and_not_with_its_key(self):
        # The labels of the objects that are not a table are declared beside the
        # ones that are: a screen that groups the closed list by object reads
        # them, and a key leaking through would be the raw word on the page.
        for obj in ("setting", "prose", "nlu", "service", "plugin", "vocabulary"):
            with self.subTest(object=obj):
                written = permissions.object_label(obj)
                self.assertNotEqual(written, f"permission.object.{obj}")
                self.assertTrue(written)

    def test_the_risk_of_an_entry_is_the_number_the_catalogue_declares(self):
        # The scale is item 15's, and the entry that MOVES the ceiling is the
        # dearest of them (§4: "the bar does not lower itself").
        self.assertEqual(permissions.risk("role:list"), 0.0)
        self.assertEqual(permissions.risk("role:create"), 0.8)
        self.assertEqual(permissions.risk("role:delete"), 0.8)
        self.assertEqual(permissions.risk("service:edit"), 0.8)
        self.assertLess(permissions.risk("task:delete"), permissions.risk("setting:edit"))

    def test_it_is_a_closed_list(self):
        self.assertTrue(permissions.is_known("actor:create"))
        self.assertFalse(permissions.is_known("actor:fly"))
        self.assertFalse(permissions.is_known("nowhere:list"))
        self.assertFalse(permissions.is_known(""))

    def test_every_permission_is_written_object_colon_action(self):
        for permission in permissions.all_permissions():
            with self.subTest(permission=permission):
                self.assertRegex(permission, r"^[a-z_]+:[a-z_]+$")

    def test_a_label_is_a_word_and_not_a_key(self):
        written = permissions.label("task:create")
        self.assertNotIn("permission.", written)
        self.assertIn(tables.table_name("task", many=True), written)
        settings = permissions.label("setting:read")
        self.assertNotIn("permission.", settings)
        self.assertIn(i18n.tr("permission.action.read"), settings)
        # The two objects that are not a table are composed the same way: the
        # object's own word and the action's, in the active language.
        self.assertIn(i18n.tr("permission.object.prose"), permissions.label("prose:edit"))
        self.assertIn(i18n.tr("permission.action.ask"), permissions.label("nlu:ask"))

    # -- what a role carries, which is what the routes ask (item 11) ---------

    def test_a_role_carries_what_its_row_declares(self):
        self.assertEqual(
            permissions.carried({"permissions": ["task:list", "task:view"]}),
            ["task:list", "task:view"],
        )

    def test_a_row_a_hand_edited_carries_nothing_and_does_not_raise(self):
        # A read is not the place to raise about a declaration somebody broke:
        # the answer is "nothing", and the surface goes on drawing.
        for broken in ({}, {"permissions": None}, {"permissions": "task:list"},
                       {"permissions": [1, 2]}, None, "task:list"):
            with self.subTest(row=broken):
                self.assertEqual(permissions.carried(broken), [])

    def test_carries_is_a_membership_and_not_a_hierarchy(self):
        role = {"permissions": ["task:list", "task:view"]}
        self.assertTrue(permissions.carries(role, "task:list"))
        self.assertFalse(permissions.carries(role, "task:create"))
        self.assertFalse(permissions.carries(role, "task:*"))
        self.assertFalse(permissions.carries(role, ""))

    def test_a_role_that_is_not_there_carries_nothing(self):
        # Fail closed: no role is a ceiling of nothing, never of everything.
        self.assertFalse(permissions.carries(None, "task:list"))
        self.assertFalse(permissions.carries({}, "task:list"))


class TheCeiling(ActorCase):
    """`actors.role_of` and `actors.may` — the row resolved into its role (§4).

    The actor's row points at the role and the role carries the set: two hops,
    and what they answer is the ceiling item 11 reads on every request. What is
    held still here is that the hop is made off the ROW and never kept, that a
    row pointing at nothing reaches nothing, and that the machine is read by the
    same door a person is.
    """

    def setUp(self):
        super().setUp()
        actors.create_admin("Rafael", GOOD)

    def subject(self, carried: str, kind: str = "person") -> dict:
        role = tables.create("role", {"name": "papel", "permissions": carried})
        return tables.create(
            "actor",
            {
                "name": "quem",
                "type": kind,
                "role": str(store.number_of(role)),
                "credential": GOOD,
            },
        )

    def test_the_role_is_the_row_the_actor_points_at(self):
        person = actors.admins()[0]
        found = actors.role_of(person)
        self.assertEqual(found["name"], actors.ADMIN_ROLE)
        self.assertEqual(found["permissions"], permissions.all_permissions())

    def test_the_ceiling_is_what_the_role_carries(self):
        person = self.subject("task:list")
        self.assertTrue(actors.may(person, "task:list"))
        self.assertFalse(actors.may(person, "task:create"))

    def test_a_row_pointing_at_nothing_reaches_nothing(self):
        # Fail closed — and the `engine`'s row is the one born this way, which
        # is right for it: it does not enter, and its ceiling is the engine's.
        self.assertIsNone(actors.role_of(actors.engine_row()))
        self.assertIsNone(actors.role_of({"name": "quem"}))
        self.assertIsNone(actors.role_of({"role": 99}))  # a number nobody wears
        self.assertFalse(actors.may(actors.engine_row(), "task:list"))
        self.assertFalse(actors.may({"role": 99}, "task:list"))

    def test_the_machine_reads_the_same_door(self):
        # An agent's row is a row: the same hop and the same ceiling, and no
        # door of its own — which is what makes the token reach the role.
        robot = self.subject("task:list", kind="agent")
        self.assertTrue(actors.may(robot, "task:list"))
        self.assertFalse(actors.may(robot, "task:create"))

    def test_the_role_is_read_again_on_every_ask(self):
        person = self.subject("task:list")
        self.assertFalse(actors.may(person, "task:create"))
        tables.edit("role", person["role"], {"permissions": "task:list,task:create"})
        self.assertTrue(actors.may(person, "task:create"))

    def test_the_administrator_role_is_found_by_its_name(self):
        # The number is the folder's to hand out, and the name is the rule; the
        # row that exists is the one both doors answer.
        found = actors.admin_role()
        self.assertEqual(found["name"], actors.ADMIN_ROLE)
        self.assertEqual(actors.role_for_admin()["id"], found["id"])


class TheVerb(ActorCase):
    """`at-cli admin` — the conversation the `cli` has, with the readers injected
    the way the first run's `ask` is. A test that typed at a real terminal would
    be a test that hangs on a build machine."""

    def run_verb(self, name: str, secrets: tuple[str, ...]) -> tuple[int, str]:
        from at.ui.cli import _admin

        given = iter(secrets)
        output = io.StringIO()
        with redirect_stdout(output):
            code = _admin(
                [], ask=lambda question: name, secret=lambda question: next(given)
            )
        return code, output.getvalue()

    def test_it_creates_the_person_it_asked_for(self):
        code, text = self.run_verb("Rafael", (GOOD, GOOD))
        self.assertEqual(code, OK)
        self.assertIn("Rafael", text)
        self.assertEqual(len(actors.admins()), 1)

    def test_a_credential_that_does_not_match_creates_nothing(self):
        code, text = self.run_verb("Rafael", (GOOD, "outra-coisa"))
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("admin.error.mismatch"), text)
        self.assertEqual(actors.admins(), [])

    def test_a_short_credential_creates_nothing(self):
        code, _ = self.run_verb("Rafael", ("curta", "curta"))
        self.assertEqual(code, REFUSED)
        self.assertEqual(actors.admins(), [])

    def test_a_second_administrator_is_refused_by_name(self):
        self.run_verb("Rafael", (GOOD, GOOD))
        code, text = self.run_verb("Outra", (GOOD, GOOD))
        self.assertEqual(code, REFUSED)
        self.assertIn("Rafael", text)
        self.assertEqual(len(actors.admins()), 1)

    def test_an_argument_is_a_usage_error(self):
        code, _ = self.run_verb("Rafael", (GOOD, GOOD))
        self.assertEqual(code, OK)
        output = io.StringIO()
        with redirect_stdout(output):
            refused = main(["admin", "extra"])
        self.assertEqual(refused, 2)

    def test_without_a_terminal_it_refuses_rather_than_assume(self):
        class _NoTerminal:
            def isatty(self) -> bool:
                return False

        output = io.StringIO()
        with mock.patch("sys.stdin", _NoTerminal()):
            with redirect_stdout(output):
                code = main(["admin"])
        self.assertEqual(code, REFUSED)
        self.assertEqual(actors.admins(), [])
        self.assertIn(i18n.tr("admin.no_tty"), output.getvalue())

    def test_the_word_is_offered_by_the_help(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["help"])
        self.assertEqual(code, OK)
        self.assertIn("admin", output.getvalue())


class TheMigration(ActorCase):
    """A folder that existed BEFORE this release catches up on the next start."""

    def test_a_folder_without_the_declarations_gains_them(self):
        where = self.root / "Tabelas" / "schema"
        for table in ("actor", "role"):
            (where / f"{table}.json").unlink()
        self.catch_up_from_scratch()

        with redirect_stdout(io.StringIO()):
            boot.catch_up(ask=None)

        for table in ("actor", "role"):
            self.assertTrue((where / f"{table}.json").is_file())
        self.assertIn("actor", schema.tables())

    def test_it_never_overwrites_a_declaration_that_is_already_there(self):
        opened = self.root / "Tabelas" / "schema" / "actor.json"
        edited = opened.read_text(encoding="utf-8").replace("Ator", "Ator meu")
        opened.write_text(edited, encoding="utf-8", newline="\n")
        self.catch_up_from_scratch()

        with redirect_stdout(io.StringIO()):
            boot.catch_up(ask=None)

        self.assertEqual(opened.read_text(encoding="utf-8"), edited)

    # -- the role that administers catches up with the catalogue (item 11) ---

    def worn(self, carried: list[str]) -> None:
        """The administrator's role as an EARLIER release left it."""
        tables.edit(
            "role", store.number_of(actors.admin_role()),
            {"permissions": ",".join(carried)},
        )

    def worn_through(self, through: int) -> None:
        """The stamp a folder that had already migrated up to `through` carries —
        the state a migration of its own exists for."""
        (self.root / "App" / "migrations").write_text(
            json.dumps(list(range(1, through + 1))) + "\n", encoding="utf-8"
        )

    def test_a_folder_that_already_ran_seven_catches_up_with_the_objects(self):
        # The catalogue grew a SECOND time, and migration seven had already run on
        # folders when it did — a published migration is never edited, so the
        # objects §4 names arrive by a step of their own. They are permissions no
        # route reaches yet, and they are handed over all the same: the role of a
        # folder that upgraded would otherwise be narrower than the one a folder
        # born today wears.
        actors.create_admin("Rafael", GOOD)
        self.worn(
            [p for p in permissions.all_permissions() if p not in migrations.GROWN]
        )
        self.worn_through(7)

        output = io.StringIO()
        with redirect_stdout(output):
            boot.catch_up(ask=None)

        carried = actors.admin_role()["permissions"]
        for permission in migrations.GROWN:
            with self.subTest(permission=permission):
                self.assertIn(permission, carried)
        self.assertIn(
            i18n.tr(
                "boot.migration.catalogue.granted",
                role=actors.ADMIN_ROLE,
                names=", ".join(migrations.GROWN),
            ),
            output.getvalue(),
        )

    def test_the_role_gains_the_catalogue_this_release_grew(self):
        # The folder was born by item 9, so its role carries the catalogue of
        # THAT day — and the prose layer and the interpreter's door did not
        # exist in it. The swap hands the role what it never had the chance to
        # carry, or the person who upgraded would be refused their own files by
        # the very ceiling item 11 put in.
        actors.create_admin("Rafael", GOOD)
        self.worn(
            [p for p in permissions.all_permissions() if p not in migrations.ADDED]
        )
        self.catch_up_from_scratch()

        output = io.StringIO()
        with redirect_stdout(output):
            boot.catch_up(ask=None)

        # The SET and not the order: a migration only ever ADDS, so what it hands
        # over lands at the end of the row — and what a role carries is a
        # MEMBERSHIP (`permissions.carries`), never a sequence.
        self.assertEqual(
            sorted(actors.admin_role()["permissions"]),
            sorted(permissions.all_permissions()),
        )
        self.assertIn(
            i18n.tr(
                "boot.migration.catalogue.granted",
                role=actors.ADMIN_ROLE,
                names=", ".join(migrations.ADDED),
            ),
            output.getvalue(),
        )

    def test_it_never_hands_back_a_permission_somebody_took_out(self):
        # A permission removed from the role before the swap was removed on
        # purpose: the migration knows what the RELEASE added, and nothing else.
        actors.create_admin("Rafael", GOOD)
        self.worn(
            [
                p
                for p in permissions.all_permissions()
                if p not in migrations.ADDED and p != "task:delete"
            ]
        )
        self.catch_up_from_scratch()

        with redirect_stdout(io.StringIO()):
            boot.catch_up(ask=None)

        carried = actors.admin_role()["permissions"]
        self.assertNotIn("task:delete", carried)
        for permission in (*migrations.ADDED, *migrations.GROWN):
            with self.subTest(permission=permission):
                self.assertIn(permission, carried)

    def test_a_role_that_already_carries_it_hears_kept(self):
        actors.create_admin("Rafael", GOOD)
        self.catch_up_from_scratch()

        output = io.StringIO()
        with redirect_stdout(output):
            boot.catch_up(ask=None)

        self.assertIn(
            i18n.tr("boot.migration.catalogue.kept", role=actors.ADMIN_ROLE),
            output.getvalue(),
        )

    def test_a_folder_with_no_administrator_says_nothing(self):
        # Nothing to catch up: a folder that never had an administrator has no
        # role to fix, and the migration is silent about a row that is not there.
        self.catch_up_from_scratch()

        output = io.StringIO()
        with redirect_stdout(output):
            boot.catch_up(ask=None)

        self.assertNotIn(actors.ADMIN_ROLE, output.getvalue())

    def test_it_does_not_bring_back_a_declaration_the_person_deleted(self):
        # The deletion was meant, and `schema.seed` promises not to repair it
        # behind the person's back — which is why the migration names the tables
        # it introduces instead of seeding the whole directory.
        where = self.root / "Tabelas" / "schema"
        (where / "task.json").unlink()
        self.catch_up_from_scratch()

        with redirect_stdout(io.StringIO()):
            boot.catch_up(ask=None)

        self.assertFalse((where / "task.json").exists())
        self.assertNotIn("task", schema.tables())


if __name__ == "__main__":
    unittest.main()
