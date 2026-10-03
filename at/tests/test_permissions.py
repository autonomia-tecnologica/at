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

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, permissions
from at.i18n import tr
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


# TASK-186, fatia 2/4: o motor de Actions centralizado. O que a fatia prova é
# a FORMA — cada entrada coberta tem um `name`, uma `key` que traduz para algo
# diferente da própria chave, e um `kind` dentre os dois que o módulo conhece
# —, não a cobertura total do catálogo (a própria ressalva do módulo).
COVERED_PERMISSIONS = (
    "webapp:run",
    "backup:make",
    "backup:restore",
    "secret:scan",
    "job:run",
    "job:approve",
    "job:refuse",
)


class TheModifiersOfAnAct(unittest.TestCase):
    # `job` e `secret` são tabelas: `is_known` lê `catalogue()`, que por sua
    # vez lê `schema.declared()` — e isso só responde dentro de uma Pasta de
    # Trabalho. `webapp`/`backup` não precisam dela (vivem em `EXTRA`), mas a
    # classe toda sobe uma, do mesmo jeito que `test_cli.py` já faz.
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(Path(self.scratch.name)), "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def test_every_covered_permission_is_itself_known(self):
        for permission in COVERED_PERMISSIONS:
            with self.subTest(permission=permission):
                self.assertTrue(permissions.is_known(permission))

    def test_secret_scan_is_covered_with_nothing(self):
        # `scan` não aceita flag nem argumento — a tupla vazia é o que a
        # cobertura diz sobre ele, e não a ausência da entrada.
        self.assertIn("secret:scan", permissions.MODIFIERS)
        self.assertEqual(permissions.modifiers("secret:scan"), ())

    def test_every_covered_modifier_has_the_right_shape(self):
        for permission in COVERED_PERMISSIONS:
            for modifier in permissions.modifiers(permission):
                with self.subTest(permission=permission, name=modifier.name):
                    self.assertIsInstance(modifier, permissions.Modifier)
                    self.assertTrue(modifier.name)
                    self.assertIn(modifier.kind, (permissions.FLAG, permissions.ARGUMENT))
                    self.assertNotEqual(tr(modifier.key), modifier.key)

    def test_webapp_run_carries_its_four_flags(self):
        names = {m.name for m in permissions.modifiers("webapp:run")}
        self.assertEqual(names, {"--port", "--public-port", "--host", "--no-caddy"})
        for modifier in permissions.modifiers("webapp:run"):
            with self.subTest(name=modifier.name):
                self.assertEqual(modifier.kind, permissions.FLAG)

    def test_backup_and_job_carry_an_argument_each(self):
        for permission in ("backup:make", "backup:restore", "job:run",
                           "job:approve", "job:refuse"):
            with self.subTest(permission=permission):
                found = permissions.modifiers(permission)
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].kind, permissions.ARGUMENT)

    def test_an_unmapped_permission_answers_with_nothing(self):
        self.assertEqual(permissions.modifiers("task:list"), ())
