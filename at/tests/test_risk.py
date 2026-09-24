"""The demand filter's numbers, as far as they exist today (§4, item 15).

The threshold is read from `app/settings.json`, and the ruler on the page is drawn
from what is read here — so a second reading of the same setting, or a boundary
drawn on the wrong side, is the defect this file exists to catch.

The numbers a DEMAND is made of are the other half, and the third slice closed
them: each entry of the catalogue declares its own (item 11's second slice, read
from `permissions.risk` and never declared twice), each argument may raise it —
a table's field in its own declaration, a settings key in `core.settings` — and
the demand is the HIGHEST among them and nothing else.

What is NOT here is the filter itself: nothing waits yet, and the job that holds
a demand at or above the threshold is the next slice. `demand` is the door the
core measures by, and the filter is what will call it.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from at import i18n
from at.core import boot, paths, permissions, risk, settings
from at.data import schema


class RiskCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": self.scratch.name, "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def set_threshold(self, value: object) -> None:
        settings.save({**settings.load(), risk.KEY: value})

    def declare(self, table: str, field: str, value: object) -> None:
        """Write a `risk` onto a field of the folder's own declaration, the way a
        person editing the file would — nothing here writes the product's copy."""
        where = paths.data_dir() / schema.SCHEMA_DIR / f"{table}.json"
        declared = json.loads(where.read_text(encoding="utf-8"))
        declared["fields"][field]["risk"] = value
        where.write_text(
            json.dumps(declared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        schema.reset()


class TheThreshold(RiskCase):
    def test_a_folder_that_never_chose_answers_the_default(self):
        # §4: `0.5`, and a demand AT it waits.
        self.assertEqual(risk.threshold(), risk.DEFAULT)
        self.assertEqual(risk.DEFAULT, 0.5)

    def test_the_folder_decides(self):
        self.set_threshold(0.95)
        self.assertEqual(risk.threshold(), 0.95)

    def test_a_value_that_is_not_a_number_is_a_setting_never_made(self):
        for strange in ("alto", None, True, [0.5]):
            with self.subTest(value=strange):
                self.set_threshold(strange)
                self.assertEqual(risk.threshold(), risk.DEFAULT)

    def test_a_value_off_the_scale_is_brought_into_it(self):
        # The ruler draws from zero to one, and a mark off the drawing is a mark
        # nobody can read.
        self.set_threshold(1.5)
        self.assertEqual(risk.threshold(), risk.CEILING)
        self.set_threshold(-1)
        self.assertEqual(risk.threshold(), risk.FLOOR)


class TheBoundary(RiskCase):
    """AT the line it waits: the boundary §4 closed, and the side the ruler draws."""

    def test_below_the_line_runs(self):
        self.assertFalse(risk.waits(0.49))

    def test_exactly_on_the_line_waits(self):
        # The one case that matters: "the price FROM WHICH a demand waits" means
        # the line itself is already the waiting side.
        self.assertTrue(risk.waits(risk.threshold()))

    def test_above_the_line_waits(self):
        self.assertTrue(risk.waits(0.51))
        self.assertTrue(risk.waits(risk.CEILING))

    def test_the_line_is_the_one_the_folder_set(self):
        self.set_threshold(0.8)
        self.assertFalse(risk.waits(0.79))
        self.assertTrue(risk.waits(0.8))


class TheDeclared(RiskCase):
    """The marks the ruler draws: one per catalogue entry, and the four numbers
    item 15 closed (§4)."""

    def test_one_mark_per_catalogue_entry(self):
        # One entry per PERMISSION, in the catalogue's own order: the page draws
        # the list it was handed and sorts nothing.
        self.assertEqual(
            [mark["key"] for mark in risk.declared()], permissions.all_permissions()
        )

    def test_every_mark_carries_what_the_catalogue_declares(self):
        for mark in risk.declared():
            with self.subTest(permission=mark["key"]):
                self.assertEqual(mark["risk"], permissions.risk(mark["key"]))

    def test_the_four_numbers_are_the_ones_the_product_declares(self):
        # §4, item 15: `0` a read, `0.2` creating or editing, `0.5` overwriting or
        # removing what existed, `0.8` changing what the system allows.
        self.assertEqual(permissions.risk("task:list"), 0.0)
        self.assertEqual(permissions.risk("task:view"), 0.0)
        self.assertEqual(permissions.risk("prose:read"), 0.0)
        self.assertEqual(permissions.risk("task:create"), 0.2)
        self.assertEqual(permissions.risk("task:edit"), 0.2)
        self.assertEqual(permissions.risk("task:delete"), 0.5)
        self.assertEqual(permissions.risk("task:cancel"), 0.5)
        # "The bar does not lower itself": `setting:edit` is named by the item, and
        # the ceiling's own objects come with it.
        self.assertEqual(permissions.risk("setting:edit"), 0.8)
        self.assertEqual(permissions.risk("role:edit"), 0.8)
        self.assertEqual(permissions.risk("actor:create"), 0.8)
        self.assertEqual(permissions.risk("actor:create"), permissions.risk("actor:delete"))

    def test_reading_the_ceiling_is_not_moving_it(self):
        for name in ("role:list", "actor:view", "setting:read"):
            with self.subTest(permission=name):
                self.assertEqual(permissions.risk(name), 0.0)

    def test_the_product_declares_nothing_at_the_top_of_the_ruler(self):
        # §4: the top of the scale is a demand nobody leaves to an automatic act.
        self.assertTrue(all(mark["risk"] < risk.CEILING for mark in risk.declared()))

    def test_a_permission_the_catalogue_does_not_name_declares_nothing(self):
        # A hand-edited role is READ, never crashed on: the number it gets is the
        # floor, and `is_known` is what says the name does not exist.
        self.assertEqual(permissions.risk("task:fly"), risk.FLOOR)
        self.assertFalse(permissions.is_known("task:fly"))

    def test_a_number_an_argument_raises_is_not_a_mark(self):
        # The ruler is ONE mark per catalogue entry, and an argument's number
        # belongs to a demand: it names no permission, so the page draws no mark
        # for it. The three item 15 names are declared all the same, and none of
        # them is a mark the page could draw.
        for object, name in (
            ("actor", "role"),
            ("role", "permissions"),
            (permissions.SETTING, risk.KEY),
        ):
            with self.subTest(argument=f"{object}.{name}"):
                self.assertEqual(risk.raised(object, name), 0.95)
        self.assertNotIn(0.95, [mark["risk"] for mark in risk.declared()])


class TheArgument(RiskCase):
    """The number an ARGUMENT raises a demand to (§4, item 15).

    "Cada campo de uma tabela pode declarar o número a que ele levanta a
    demanda": the declaration is the table's own file, and the settings — which
    are not a table — declare theirs in `core.settings`, beside the keys.
    """

    def test_the_arguments_that_hand_out_access_are_the_ones_declared(self):
        # "Handing out access is the price of the whole model": the three item 15
        # names are at 0.95 — above the 0.8 of the ceiling itself, and still
        # below the top of the ruler, where the product declares nothing. Above
        # 0.8 is the whole point of the per-argument declaration: a folder whose
        # threshold sits at 0.9 runs a plain edit and waits on a hand-out.
        self.assertEqual(risk.raised("actor", "role"), 0.95)
        self.assertEqual(risk.raised("role", "permissions"), 0.95)
        self.assertEqual(risk.raised(permissions.SETTING, risk.KEY), 0.95)

    def test_a_table_that_declares_nothing_answers_the_floor(self):
        # The rule is the DECLARATION's and not a list of tables: only the two
        # fields that declare a number have one, and every other field of every
        # other table — the ones the product ships — answers nothing.
        self.assertEqual(risk.raised("task", "text"), risk.FLOOR)
        self.assertEqual(risk.raised("task", "status"), risk.FLOOR)
        self.assertEqual(risk.raised("actor", "credential"), risk.FLOOR)
        self.assertEqual(risk.raised("audit", "what"), risk.FLOOR)

    def test_a_field_or_a_key_nobody_declared_answers_the_floor(self):
        self.assertEqual(risk.raised("task", "nowhere"), risk.FLOOR)
        self.assertEqual(risk.raised(permissions.SETTING, "basic_auth"), risk.FLOOR)

    def test_a_declaration_that_is_not_a_number_is_read_as_the_floor(self):
        # A strange declaration is read the way every strange declaration is —
        # as nothing — and a boolean is not a number here: in this language
        # `true` is an integer, and a switch read as the top of the scale would
        # be the defect this guard exists for.
        for strange in ("alto", None, True, [0.95]):
            with self.subTest(value=strange):
                self.declare("task", "text", strange)
                self.assertEqual(risk.raised("task", "text"), risk.FLOOR)

    def test_a_number_off_the_scale_is_brought_into_it(self):
        self.declare("task", "text", 1.5)
        self.assertEqual(risk.raised("task", "text"), risk.CEILING)
        self.declare("task", "text", -1)
        self.assertEqual(risk.raised("task", "text"), risk.FLOOR)


class TheDemand(RiskCase):
    """The demand's risk: the HIGHEST among the action and the arguments."""

    def test_a_read_is_free(self):
        self.assertEqual(risk.demand("task", "list"), risk.FLOOR)
        self.assertEqual(risk.demand("task", "view"), risk.FLOOR)
        # The settings' read is `setting:read` — `list` and `view` are the one
        # read the object declares (`permissions.NARROWED`), so the demand is
        # priced for the permission the catalogue has and not for the word.
        self.assertEqual(risk.demand(permissions.SETTING, "list"), risk.FLOOR)
        self.assertEqual(risk.demand(permissions.SETTING, "view"), risk.FLOOR)

    def test_the_action_is_the_floor_of_its_own_demand(self):
        self.assertEqual(risk.demand("task", "create"), permissions.risk("task:create"))
        self.assertEqual(risk.demand("task", "edit"), 0.2)
        self.assertEqual(risk.demand("task", "delete"), 0.5)
        self.assertEqual(risk.demand(permissions.SETTING, "edit"), 0.8)

    def test_an_argument_that_raises_nothing_leaves_the_action_alone(self):
        self.assertEqual(risk.demand("task", "create", ["text"]), 0.2)
        self.assertEqual(risk.demand("task", "edit", ["text", "status"]), 0.2)

    def test_the_argument_that_hands_out_access_is_the_whole_demand(self):
        self.assertEqual(risk.demand("actor", "edit", ["role"]), 0.95)
        self.assertEqual(risk.demand("role", "edit", ["permissions"]), 0.95)
        self.assertEqual(risk.demand(permissions.SETTING, "edit", [risk.KEY]), 0.95)

    def test_the_highest_wins_and_it_is_never_a_sum(self):
        # Two arguments that raise each raise nothing TOGETHER: with the scale
        # bounded, a sum would escape it and the ruler would stop being
        # predictable (§4). 0.95 twice is still 0.95.
        self.assertEqual(risk.demand("actor", "edit", ["role", "role"]), 0.95)
        self.assertEqual(risk.demand("actor", "edit", ["role", "name"]), 0.95)
        self.assertEqual(risk.demand("task", "delete", ["text"]), 0.5)

    def test_a_narrowed_object_is_priced_for_what_it_answers(self):
        # `secret` answers `read` and `edit`, so its write is `secret:edit` —
        # the same name the route demands and the same number — and `audit`
        # answers a read alone.
        self.assertEqual(
            risk.demand("secret", "edit", ["value"]), permissions.risk("secret:edit")
        )
        self.assertEqual(risk.demand("audit", "list"), risk.FLOOR)

    def test_a_demand_never_leaves_the_scale(self):
        every = [
            risk.demand(object, action)
            for object in ("task", "project", "reminder", "actor", "role", "secret", "audit")
            for action in ("list", "view", "create", "edit", "cancel", "delete")
        ]
        self.assertTrue(all(risk.FLOOR <= value <= risk.CEILING for value in every))


if __name__ == "__main__":
    unittest.main()
