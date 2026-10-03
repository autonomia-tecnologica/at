"""The non-table words of the CLI, against the catalogue (TASK-186, fatia 1/4).

`tree.WORDS` is the closed list of words the CLI offers that are not a table —
and until this slice, `permissions.py` was silent about every one of them: a
role could not be written against `webapp:run` or `backup:restore` because
neither existed. This file is the proof the catalogue caught up: every word of
`tree.WORDS`, besides `ASK` (the interpreter's, read off `tree.words()` and not
this list) and the table words (which come from `data/schema/`, not from
here), now answers to a permission the catalogue knows — or is one of the five
named here, with the reason it is not about the Working Folder at all.
"""

from __future__ import annotations

import unittest

from at.core import permissions
from at.ui.cli import tree

# The five words that are the artifact's OWN INTERFACE, and not an act on the
# Working Folder — so none of them has a permission to carry. Each reason is
# the code's own, not one invented for this test:
#
# - `install`/`uninstall` run BEFORE the folder is even confirmed
#   (`cli/__init__.py`'s `main`: "the only words that do"), so there is no
#   actor and no role yet to hold a ceiling for them to answer to.
# - `license`'s own docstring says it plainly: "Nothing here is about the
#   Working Folder, so there is no permission and no folder to read: the same
#   place `version` and `help` answer from."
# - `help` and `version` print what the binary is and what it carries,
#   reading nothing the folder owns.
NAMED_EXCEPTIONS = ("help", "version", "license", "install", "uninstall")

# Every other word, mapped to the permission(s) it now carries. Most words ARE
# their own object (`webapp:run`, `backup:make`/`backup:restore`) — the clear
# object+verb cases. `admin`, `lang` and `convert` are the verbs left SOLTOS,
# with no object of their own: the catalogue has no shape yet for "a verb
# alone", so the three share one, `cli`, the way the recommended reading of
# this slice's own prompt offered. `assist` and `setting` were catalogued
# already (`EXTRA`, before this slice) and are listed here all the same, so
# this file is the one place that proves EVERY word of `tree.WORDS` — not only
# the five this slice added.
WORD_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "webapp": ("webapp:run",),
    "backup": ("backup:make", "backup:restore"),
    "convert": ("cli:convert",),
    "admin": ("cli:admin",),
    "lang": ("cli:lang",),
    "assist": ("assist:ask",),
    permissions.SETTING: ("setting:read", "setting:edit"),
}


class TheWordsOfTheTree(unittest.TestCase):
    def test_every_word_is_mapped_or_a_named_exception(self):
        # The whole point: a word `tree.WORDS` grows tomorrow and this test
        # does not mention is a FAILURE here, never a silent gap the catalogue
        # stays quiet about.
        names = {node.name for node in tree.WORDS}
        self.assertEqual(names, set(WORD_PERMISSIONS) | set(NAMED_EXCEPTIONS))

    def test_every_mapped_permission_is_known(self):
        for word, names in WORD_PERMISSIONS.items():
            for permission in names:
                with self.subTest(word=word, permission=permission):
                    self.assertTrue(permissions.is_known(permission))

    def test_every_mapped_permission_is_in_all_permissions(self):
        catalogued = permissions.all_permissions()
        for names in WORD_PERMISSIONS.values():
            for permission in names:
                with self.subTest(permission=permission):
                    self.assertIn(permission, catalogued)

    def test_every_mapped_permission_declares_a_risk_on_the_scale(self):
        for names in WORD_PERMISSIONS.values():
            for permission in names:
                with self.subTest(permission=permission):
                    self.assertTrue(0.0 <= permissions.risk(permission) <= 1.0)

    def test_every_new_object_and_action_has_a_translated_label(self):
        # The raw word is what `object_label`/`action_label` fall back to when
        # a key is missing (§3) — so a label equal to the raw name is a
        # missing translation, not a coincidence. Only THIS slice's own words:
        # `assist` and `setting` were catalogued before it and are somebody
        # else's gap to close, not this test's to fail on.
        for word in ("webapp", "backup", "admin", "lang", "convert"):
            for permission in WORD_PERMISSIONS[word]:
                obj, _, action = permission.partition(":")
                with self.subTest(permission=permission):
                    self.assertNotEqual(permissions.object_label(obj), obj)
                    self.assertNotEqual(permissions.action_label(action), action)

    def test_the_named_exceptions_are_not_catalogued(self):
        catalogue = permissions.catalogue()
        for word in NAMED_EXCEPTIONS:
            with self.subTest(word=word):
                self.assertNotIn(word, catalogue)
