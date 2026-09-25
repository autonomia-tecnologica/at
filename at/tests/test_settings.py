"""The settings through the core's door — `setting:read`, `setting:edit`, the line.

Item 15's third slice: §4 makes the settings reachable through the core API, and
this is the door. It has two halves, and both are measured here: `core.settings`
owns the FILE — which keys exist, what a value is, what a write refuses — and
`at.ui.ask.setting` owns the ACT, because it is the one that knows the actor and
the via, and therefore the one that owes §3 its line.

Four sentences are held to the code:

- **the door is the only one a surface has.** §5 says the `cli` reaches
  everything, and it reaches the settings by `setting list|view|edit` — the three
  words are the object's own actions, read from the catalogue, and `setting:read`
  is the one read while `setting:edit` is the one write.
- **what a VALUE is, the core says.** `0.95` is the float the filter compares
  against, `true` turns a permission on, and `forms` is the word the gate reads:
  one reader, and it is not the surface's.
- **what the door refuses is named, and nothing is written.** A key AT owns and a
  key with no name are refused by name, and the file does not move.
- **an edit is an act like any other**: exactly one line, one version, the via of
  the surface and the actor of the folder — and a READ leaves nothing at all.

Every test aims AT at a throwaway folder with `AT_ROOT`, so the checkout's own
Working Folder is never touched; none of them needs a network or a model.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    actors,
    audit,
    boot,
    files,
    paths,
    permissions,
    risk,
    settings,
    tables,
    versioning,
)
from at.data import schema, store
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import main, tree
from at.ui.webapp import app as webapp


class SettingsCase(unittest.TestCase):
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
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def words(self, *args: str) -> tuple[int, str]:
        """One word through the real `cli`, so the actor and the via are the ones
        that surface resolves and not the ones a test hands in."""
        output = StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, output.getvalue()

    def lines(self) -> list[dict]:
        return store.load("audit")


class TheDoor(SettingsCase):
    """`core.settings` — the file's door: which keys, what a value is, and what a
    write refuses."""

    def test_it_hands_over_the_keys_the_product_reads(self):
        # The known keys come first, in one stable order, and they are the ones
        # the product actually reads — each one named where it is read: `boot`
        # the shape version, `nlu` the interpreter, the WebApp the Basic
        # permission, `gate` the authenticator, `risk` the bar, and `migrations`
        # the folders decision.
        keys = settings.keys()
        self.assertEqual(keys[: len(settings.KNOWN)], list(settings.KNOWN))
        for name in ("interpreter", "basic_auth", "risk_threshold", "authenticator"):
            with self.subTest(key=name):
                self.assertIn(name, keys)

    def test_a_key_the_product_does_not_read_is_still_shown(self):
        # The file is the PERSON's: a door that hid half of it would be the door
        # lying, so what the folder carries comes along, after the known ones.
        settings.save({**settings.load(), "minha_chave": 7})
        self.assertEqual(settings.keys()[-1], "minha_chave")

    def test_a_write_keeps_every_other_key(self):
        before = settings.load()
        settings.put("risk_threshold", 0.9)
        after = settings.load()
        self.assertEqual(after["risk_threshold"], 0.9)
        self.assertEqual(before["schema"], after["schema"])

    def test_the_key_is_the_name_the_write_answers(self):
        self.assertEqual(settings.put("  risk_threshold  ", 0.9), "risk_threshold")
        self.assertIn("risk_threshold", settings.load())

    def test_a_key_at_owns_is_refused_by_name(self):
        # `schema` is what a migration reads to know how far this folder has
        # come; a hand moving it would be the folder lying about its own shape,
        # and the next update would skip the catch-up the stamp exists for.
        with self.assertRaises(settings.Refused) as refused:
            settings.put("schema", 2)
        self.assertEqual(refused.exception.key, "setting.error.reserved")
        self.assertEqual(str(refused.exception), tr("setting.error.reserved", setting="schema"))
        self.assertEqual(settings.get("schema"), settings.SCHEMA)

    def test_a_key_with_no_name_is_refused(self):
        for name in ("", "   "):
            with self.subTest(key=name):
                with self.assertRaises(settings.Refused) as refused:
                    settings.put(name, 1)
                self.assertEqual(refused.exception.key, "setting.error.key")

    def test_a_value_is_what_json_writes_and_a_word_is_a_word(self):
        for typed, expected in (
            ("0.95", 0.95),
            ("1", 1),
            ("true", True),
            ("TRUE", True),
            ("false", False),
            ("forms", "forms"),
            ("risk_threshold", "risk_threshold"),
        ):
            with self.subTest(typed=typed):
                self.assertEqual(settings.literal(typed), expected)
                self.assertIs(type(settings.literal(typed)), type(expected))

    def test_the_number_a_key_raises_is_declared_beside_the_key(self):
        # The settings are not a table and have no schema for a per-argument
        # number to live in, so it lives in their own module — and it is the one
        # §4 names, because whoever can move the wall learns where it is.
        self.assertEqual(settings.raised(risk.KEY), 0.95)
        self.assertIsNone(settings.raised("basic_auth"))

    def test_the_per_action_adjustment_is_a_key_the_product_reads(self):
        # §5's promise needs a home, and it is the file the person edits: the map
        # of `object:action` → number sits beside the bar, and the door hands it
        # over with every other key the product reads.
        self.assertEqual(risk.BY_ACTION, "risk_by_action")
        self.assertIn(risk.BY_ACTION, settings.KNOWN)
        self.assertIn(risk.BY_ACTION, settings.keys())

    def test_the_cadence_of_versioning_is_a_key_the_product_reads(self):
        # §4, item 30: the folder's versioning cadence is an adjustment like the
        # interpreter's switch, and it reaches the person by this same door. It
        # raises nothing, and for the reason the switch raises nothing: what it
        # moves is how often the folder is versioned, and never a wall.
        self.assertEqual(versioning.KEY, settings.VERSIONING)
        self.assertIn(settings.VERSIONING, settings.KNOWN)
        self.assertIn(settings.VERSIONING, settings.keys())
        self.assertIsNone(settings.raised(settings.VERSIONING))

    def test_the_map_that_moves_the_wall_is_priced_with_the_bar(self):
        # An edit of the map writes which number each action carries, so it walks
        # an entry under the bar without touching the bar at all: it is the same
        # act as moving the line, and §4's reason prices it the same.
        self.assertEqual(settings.raised(risk.BY_ACTION), 0.95)
        self.assertEqual(
            risk.demand(permissions.SETTING, "edit", [risk.BY_ACTION]), 0.95
        )


class TheCatalogue(SettingsCase):
    """The object in the catalogue: two permissions, and three words."""

    def test_the_settings_declare_the_one_read_and_the_one_write(self):
        self.assertEqual(permissions.catalogue().get(permissions.SETTING), ("read", "edit"))
        for name, known in (
            ("setting:read", True),
            ("setting:edit", True),
            ("setting:list", False),
            ("setting:view", False),
            ("setting:create", False),
            ("setting:delete", False),
        ):
            with self.subTest(permission=name):
                self.assertIs(permissions.is_known(name), known)

    def test_the_words_are_the_actions_the_object_declares(self):
        # The narrowing of an object that is not a table is declared in the
        # catalogue, and read by the same door a table's is: `list` and `view`
        # are the read, `edit` is the write, and the order is the engine's.
        self.assertEqual(
            permissions.actions(permissions.SETTING), ("list", "view", "edit")
        )
        self.assertEqual(permissions.needed(permissions.SETTING, "list"), "setting:read")
        self.assertEqual(permissions.needed(permissions.SETTING, "view"), "setting:read")
        self.assertEqual(permissions.needed(permissions.SETTING, "edit"), "setting:edit")

    def test_the_tree_offers_the_word_and_its_three_actions(self):
        node = next(node for node in tree.words() if node.name == permissions.SETTING)
        self.assertEqual(
            [child.name for child in node.children], ["list", "view", "edit"]
        )

    def test_the_admin_role_carries_both(self):
        role = actors.role_for_admin()
        self.assertIn("setting:read", permissions.carried(role))
        self.assertIn("setting:edit", permissions.carried(role))


class TheWords(SettingsCase):
    """`at-cli setting list|view|edit` — the surface, and what a wrong word costs."""

    def test_list_answers_every_key_and_the_value_of_each(self):
        self.words("setting", "edit", "risk_threshold", "0.9")
        code, text = self.words("setting", "list")
        self.assertEqual(code, 0)
        self.assertIn("risk_threshold", text)
        self.assertIn("0.9", text)
        # A key the folder never chose says so, and the door invents no default:
        # what the interpreter does when the folder is silent is the
        # interpreter's answer, and a second one here would be the one that
        # drifts.
        self.assertIn(tr("setting.unset"), text)

    def test_view_answers_one_key(self):
        self.words("setting", "edit", "authenticator", "gate")
        code, text = self.words("setting", "view", "authenticator")
        self.assertEqual(code, 0)
        self.assertEqual(text.strip(), tr("setting.line", setting="authenticator", value="gate"))

    def test_view_of_a_key_the_folder_never_chose_is_an_answer(self):
        code, text = self.words("setting", "view", "risk_threshold")
        self.assertEqual(code, 0)
        self.assertIn(
            tr("setting.unset.line", setting="risk_threshold"), text
        )

    def test_edit_writes_the_key_and_answers_with_the_value(self):
        code, text = self.words("setting", "edit", "risk_threshold", "0.9")
        self.assertEqual(code, 0)
        self.assertEqual(settings.get("risk_threshold"), 0.9)
        self.assertEqual(risk.threshold(), 0.9)
        self.assertIn(
            tr("setting.edited", setting="risk_threshold", value="0.9"), text
        )

    def test_the_value_is_read_back_from_the_file(self):
        # What the answer says is what the file now HOLDS and not what was
        # typed: the write is the file's, and the file is the truth.
        code, text = self.words("setting", "edit", "basic_auth", "true")
        self.assertEqual(code, 0)
        self.assertIs(settings.get("basic_auth"), True)
        self.assertTrue(webapp.basic_allowed())
        self.assertIn(tr("setting.edited", setting="basic_auth", value="true"), text)

    def test_edit_writes_the_map_and_answers_with_what_the_file_holds(self):
        # The adjustment is written through the door like any other key, and the
        # value is the CORE's reading of what was typed (`settings.literal`): the
        # JSON object the person types is the object the file holds, and it is the
        # one the demand filter reads.
        code, text = self.words(
            "setting", "edit", risk.BY_ACTION, '{"task:delete": 0.1}'
        )
        self.assertEqual(code, 0)
        self.assertEqual(settings.get(risk.BY_ACTION), {"task:delete": 0.1})
        self.assertEqual(risk.demand("task", "delete"), 0.1)
        self.assertIn(
            tr(
                "setting.edited",
                setting=risk.BY_ACTION,
                value='{"task:delete": 0.1}',
            ),
            text,
        )

    def test_the_cadence_is_written_and_read_through_the_door(self):
        # The person chooses the cadence the way they choose any other
        # adjustment, and the number the core reads afterwards is the number the
        # file holds — `0` being the version on every write (§4, item 30).
        code, text = self.words("setting", "edit", versioning.KEY, "0")
        self.assertEqual(code, 0)
        self.assertEqual(settings.get(versioning.KEY), 0)
        self.assertEqual(versioning.interval(), versioning.EVERY_WRITE)
        self.assertIn(
            tr("setting.edited", setting=versioning.KEY, value="0"), text
        )

    def test_a_map_a_hand_wrote_is_read_the_same_way(self):
        # The door is where the act is recorded, and it is not the only way in:
        # the file is the person's, and the reading is the core's either way.
        settings.save({**settings.load(), risk.BY_ACTION: {"setting:edit": 0.9}})
        code, text = self.words("setting", "view", risk.BY_ACTION)
        self.assertEqual(code, 0)
        self.assertIn('{"setting:edit": 0.9}', text)
        self.assertEqual(risk.demand(permissions.SETTING, "edit"), 0.9)

    def test_a_word_the_object_does_not_answer_is_a_usage_error(self):
        code, text = self.words("setting", "delete", "risk_threshold")
        self.assertEqual(code, 2)
        self.assertIn(tr("table.error.unknown_action", action="delete"), text)

    def test_the_wrong_number_of_arguments_is_a_usage_error(self):
        for words in (
            ["setting", "list", "extra"],
            ["setting", "view"],
            ["setting", "view", "a", "b"],
            ["setting", "edit", "risk_threshold"],
            ["setting", "edit", "risk_threshold", "0.9", "extra"],
        ):
            with self.subTest(words=words):
                code, text = self.words(*words)
                self.assertEqual(code, 2)
                self.assertIn(tr("setting.error.arguments"), text)

    def test_a_word_with_no_action_answers_the_listing(self):
        # The same shape every table word carries: no action is the listing, so
        # `at-cli setting` reads the settings instead of refusing the reader.
        code, text = self.words("setting")
        self.assertEqual(code, 0)
        self.assertIn("risk_threshold", text)


class TheLine(SettingsCase):
    """The act and its line — and the read that leaves nothing at all."""

    def test_an_edit_leaves_exactly_one_line(self):
        self.words("setting", "edit", "risk_threshold", "0.9")
        self.words("setting", "edit", "basic_auth", "true")
        self.assertEqual(len(self.lines()), 2)
        row = self.lines()[0]
        self.assertEqual(row[audit.WHAT], "setting:edit")
        self.assertEqual(row[audit.TABLE], permissions.SETTING)
        self.assertEqual(row[audit.STATUS], audit.OK)
        self.assertEqual(row[audit.VIA], audit.CLI)
        self.assertEqual(row[audit.THRESHOLD], risk.DEFAULT)

    def test_the_adjustment_edit_leaves_one_line_and_one_version(self):
        # §5's adjustment is an act like any other: it goes through `setting:edit`,
        # so the line names the actor and the via, carries the bar the demand
        # faced, and ends in one version named by the sentence the person read.
        with mock.patch.object(versioning, "commit") as committed:
            code, text = self.words(
                "setting", "edit", risk.BY_ACTION, '{"task:delete": 0.1}'
            )
        self.assertEqual(code, 0)
        committed.assert_called_once_with(text.strip())
        rows = self.lines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][audit.WHAT], "setting:edit")
        self.assertEqual(rows[0][audit.TABLE], permissions.SETTING)
        self.assertEqual(rows[0][audit.STATUS], audit.OK)
        self.assertEqual(rows[0][audit.THRESHOLD], risk.DEFAULT)

    def test_the_actor_is_the_first_admin(self):
        admin = actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.words("setting", "edit", "risk_threshold", "0.9")
        self.assertEqual(self.lines()[0][audit.ACTOR], store.number_of(admin))

    def test_a_read_leaves_nothing_at_all(self):
        self.words("setting", "list")
        self.words("setting", "view", "risk_threshold")
        self.assertEqual(self.lines(), [])

    def test_a_read_is_not_a_version_and_an_edit_is(self):
        # Every action that changes the folder ends in a version (§4, item 30),
        # named by the very sentence the surface printed; a read changed nothing,
        # so there is nothing to keep.
        with mock.patch.object(versioning, "commit") as committed:
            self.words("setting", "list")
            committed.assert_not_called()
        with mock.patch.object(versioning, "commit") as committed:
            code, text = self.words("setting", "edit", "risk_threshold", "0.9")
        committed.assert_called_once_with(text.strip())

    def test_a_refusal_is_a_line_with_the_reason_key_and_no_value(self):
        code, _ = self.words("setting", "edit", "schema", "2")
        self.assertEqual(code, 1)
        row = self.lines()[0]
        self.assertEqual(row[audit.STATUS], audit.REFUSED)
        self.assertEqual(row[audit.REASON], "setting.error.reserved")
        self.assertEqual(row[audit.WHAT], "setting:edit")
        self.assertNotIn("2", str(row.get("reason", "")))

    def test_a_read_only_run_writes_nothing_and_leaves_no_line(self):
        before = settings.load()
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            code, text = self.words("setting", "edit", "risk_threshold", "0.9")
        self.assertEqual(code, 1)
        self.assertIn(
            tr("cli.error.read_only", where=str(paths.settings_file())), text
        )
        self.assertEqual(settings.load(), before)
        self.assertEqual(self.lines(), [])

    def test_the_ceiling_of_the_object_is_what_the_catalogue_names(self):
        # The permission a settings act demands is the one the catalogue names,
        # read through `needed` — so the day a route demands it, the route and
        # the role read the same word.
        row = tables.create("role", {"name": "narrow", "permissions": "task:list"})
        self.assertFalse(
            permissions.carries(row, permissions.needed(permissions.SETTING, "edit"))
        )
        self.assertTrue(
            permissions.carries(row, permissions.needed("task", "list"))
        )


class TheInstant(SettingsCase):
    """The line is stamped by the engine, like every other one (§3)."""

    def test_the_edit_is_stamped_with_the_engine_s_clock(self):
        frozen = "2026-09-22T13:04:07.123Z"
        with mock.patch.object(audit, "moment", lambda: frozen):
            self.words("setting", "edit", "risk_threshold", "0.9")
        self.assertEqual(self.lines()[0][audit.WHEN], frozen)

    def test_the_line_reads_the_bar_of_the_demand_that_arrived(self):
        # The threshold is a number of the FOLDER's and read at arrival: this is
        # the one act that moves it, and the line says what the demand faced and
        # not what it chose. The reading is the door's (`_arrival`), so no
        # surface can record a bar of its own.
        settings.save({**settings.load(), risk.KEY: 0.8})
        self.words("setting", "edit", risk.KEY, "0.9")
        self.assertEqual(self.lines()[0][audit.THRESHOLD], 0.8)
        self.assertEqual(risk.threshold(), 0.9)


if __name__ == "__main__":
    unittest.main()
