"""The non-table words of the CLI, against the catalogue (TASK-186, fatia 1/4).

`tree.WORDS` is the closed list of words the CLI offers that are not a table —
and until this slice, `permissions.py` was silent about every one of them: a
role could not be written against `webapp:run` or `backup:restore` because
neither existed. This file is the proof the catalogue caught up: every word of
`tree.WORDS`, besides `ASK` (the interpreter's, read off `tree.words()` and not
this list) and the table words (which come from `data/schema/`, not from
here), now answers to a permission the catalogue knows — or is one of the four
named in `tree.NAMED_EXCEPTIONS`, with the reason it is not about the Working
Folder at all.

`NAMED_EXCEPTIONS` and `WORD_PERMISSIONS` live in `tree.py` now and not here
(TASK-186, fatia 3/4): the audit (`at.core.actions_audit`) reads the same two
for the CLI side of these words, and a second copy here would be the second
home the catalogue already refuses (`permissions.py`'s own docstring).
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
from at.core import actions_audit, boot, permissions
from at.i18n import tr
from at.ui.cli import tree
from at.ui.cli.tree import NAMED_EXCEPTIONS, WORD_PERMISSIONS


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
        # else's gap to close, not this test's to fail on. `help` joined in
        # fatia 3/4, and its label is this test's to prove the same way.
        for word in ("webapp", "backup", "admin", "lang", "convert", "help"):
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


# TASK-186, fatia 3/4: a auditoria das três portas. O que ela prova é que
# NENHUMA permissão do catálogo fica sem porta nenhuma — a não ser uma das
# nomeadas em `NO_INTERFACE_YET` —, e que a leitura da gramática é ESTÁTICA
# (sem Jev, sem rede): as duas coisas que a fatia exige para "conta como
# pronto".
class TheInterfacesThatReach(unittest.TestCase):
    # `catalogue()` lê `schema.declared()`, que só responde dentro de uma
    # Pasta de Trabalho — a mesma que `TheModifiersOfAnAct` sobe.
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

    def test_no_catalogue_permission_is_an_orphan(self):
        # O coração da fatia: uma permissão que o catálogo conhece e que
        # nenhuma porta alcança é um buraco — um papel que a carrega não
        # consegue fazer nada com ela. A única saída é estar em
        # `NO_INTERFACE_YET`, com o porquê escrito ao lado.
        self.assertEqual(actions_audit.orphans(), [])

    def test_reach_answers_for_every_permission_of_the_catalogue(self):
        # "Para CADA permissão do catálogo": a chave existe sempre, vazia
        # quando ninguém chega — o que deixa `orphans` perguntar "quantas
        # portas?" sem um `in` que confunda "não achei" com "não existe".
        self.assertEqual(
            set(actions_audit.reach()),
            set(permissions.all_permissions()),
        )

    def test_the_hand_written_web_list_matches_the_catalogue(self):
        # `WEB_PERMISSIONS` é a parte escrita à mão (a rota é código, não
        # dado); este cruzamento é o que impede a lista de apodrecer — um nome
        # que a rota exige mas o catálogo não tem falharia FECHADO.
        self.assertEqual(actions_audit.unknown_web_permissions(), [])

    def test_the_named_exceptions_are_really_unreached(self):
        # Uma permissão que ganha porta sai da lista nomeada; enquanto estiver
        # lá, ela NÃO pode ser alcançada — senão a lista vira desculpa que
        # esconde um alcance que já existe.
        found = actions_audit.reach()
        for permission in actions_audit.NO_INTERFACE_YET:
            with self.subTest(permission=permission):
                self.assertIn(permission, found)
                self.assertEqual(found[permission], frozenset())

    def test_the_grammar_read_is_static_and_never_asks_jev(self):
        # A ressalva da fatia: a leitura da gramática é ESTÁTICA, sem chamada
        # ao Jev. Se `reach()` passasse pelo matcher ou pelo Jev, estes dois
        # patches — que estouram se tocados — derrubariam o teste; que ele
        # passe prova que a leitura só consulta o vocabulário embalado.
        with mock.patch("at.nlu.matcher.match", side_effect=AssertionError("matcher tocado")):
            with mock.patch("at.core.jev.decide", side_effect=AssertionError("jev tocado")):
                reached = actions_audit.reach()
        self.assertTrue(reached)

    def test_the_grammar_actions_are_the_ones_the_vocabulary_names(self):
        # Só os verbos que o vocabulário embalado nomeia como canônico entram
        # no `llm`; hoje são os quatro que o `action.json` carrega. O teste
        # trava o FATO, para um vocabulário que ganhe (`cancel`) ou perca uma
        # gíria apareça aqui e não passe em silêncio.
        self.assertEqual(
            actions_audit._grammar_actions(),
            frozenset({"list", "view", "create", "edit"}),
        )

    def test_the_three_interfaces_are_all_exercised(self):
        # As três marcas existem e são usadas — a auditoria não é um conjunto
        # vazio que "passa" por não achar nada. Cada uma aparece ao menos uma
        # vez no catálogo de hoje (toda ação de tabela chega pela CLI; a
        # leitura tem rota web; a frase nomeia os quatro verbos).
        seen = set()
        for marks in actions_audit.reach().values():
            seen |= marks
        self.assertEqual(seen, {actions_audit.CLI, actions_audit.WEB, actions_audit.LLM})

