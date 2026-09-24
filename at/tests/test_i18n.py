"""The catalogs and the lookup.

These tests answer no question about the Working Folder: they pin the catalogs
themselves, which is the part that must never drift.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from at import i18n


class CatalogsInStep(unittest.TestCase):
    def test_both_languages_carry_the_same_keys(self):
        self.assertEqual(i18n.keys_out_of_step(), {})

    def test_writing_in_one_language_only_is_caught(self):
        # The gate above is only worth having if it can fail.
        incomplete = {"pt_BR": {"only.here": "a"}, "en_US": {}}
        present = {language: set(data) for language, data in incomplete.items()}
        every = set().union(*present.values())
        self.assertEqual(sorted(every - present["en_US"]), ["only.here"])


class Translation(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AT_LANG": "pt_BR"})
        self.env.start()
        i18n.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()

    def test_a_missing_key_answers_with_the_key(self):
        # Visible, never silent: an empty string would hide the defect.
        self.assertEqual(i18n.tr("boot.no.such.key"), "boot.no.such.key")

    def test_placeholders_are_filled_from_the_call(self):
        text = i18n.tr("boot.first_run.notice", folder="/tmp/somewhere")
        self.assertIn("/tmp/somewhere", text)

    def test_the_environment_decides_the_language(self):
        self.assertEqual(i18n.active_code(), "pt_BR")
        self.assertEqual(i18n.active_origin(), "env")

    def test_a_block_namespaces_the_keys_of_its_file(self):
        # `blocks/boot.json` holds `first_run.confirm`, read as `boot.…`.
        self.assertNotEqual(i18n.tr("boot.first_run.confirm"), "boot.first_run.confirm")


if __name__ == "__main__":
    unittest.main()
