"""The demand filter's numbers, as far as they exist today (§4, item 15).

The threshold is read from `app/settings.json`, and the ruler on the page is drawn
from what is read here — so a second reading of the same setting, or a boundary
drawn on the wrong side, is the defect this file exists to catch.

What is NOT here is the filter itself: the demand that waits, the job that holds
it and the number a FIELD raises a demand to are item 15's second and third
slices. The entry's own risk landed with the catalogue (item 11's second slice),
and it is read from there — never declared twice.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from bill import i18n
from bill.core import boot, permissions, risk, settings


class RiskCase(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ, {"BILL_ROOT": self.scratch.name, "BILL_LANG": "pt_BR"}
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


if __name__ == "__main__":
    unittest.main()
