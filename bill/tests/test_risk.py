"""The demand filter's numbers, as far as they exist today (§4, item 15).

The threshold is read from `app/settings.json`, and the ruler on the page is drawn
from what is read here — so a second reading of the same setting, or a boundary
drawn on the wrong side, is the defect this file exists to catch.

What is NOT here is the filter itself: the demand that waits, the job that holds
it and the catalogue of permissions are item 15's slices 2 and 3 and item 11.
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from bill import i18n
from bill.core import boot, risk, settings


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
    def test_nothing_is_declared_yet_and_it_says_so(self):
        # The permission catalogue is item 11: neither an action nor a field
        # carries a number today. The ruler draws what the product DECLARES, and
        # an empty list is the truth — never a guess dressed as a mark.
        self.assertEqual(risk.declared(), [])


if __name__ == "__main__":
    unittest.main()
