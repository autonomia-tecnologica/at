"""The `secret` table: the sealed value in the row, and the key of its service.

Item 14's second half, and the half that gives the primitive a caller. §4 splits
the two kinds of value a row holds — what only PROVES is hashed in its own row,
what AT USES is sealed in the `secret` table — and this is the second kind
arriving: `secret.json` beside the other system tables, `data/secrets.jsonl` as
its store, the envelope IN the row, and the derived key scoped to one service or
purpose and recovered from the Main Key alone.

Five things are measured, and each is a sentence held to the code:

- **the declaration is the product's.** The table ships (`data/schema/`), its
  store is the file the item names, and the field that carries the envelope is
  the one `core.secrets` seals into — the two names are held together here, so a
  declaration that renamed one fails instead of sealing a value nobody opens.
- **what is sealed does not come back.** Not in the store file, not in a
  listing, not through the engine's door: a cleartext cannot even be written
  into the column, because the type refuses what is not an envelope.
- **the key is scoped, and the Main Key recovers it.** One key per service or
  purpose, the same on every call, opening what it sealed and nothing of
  another's — and a scope that is not a name is refused rather than becoming a
  second key in silence.
- **the table declares its own permissions.** `secret` answers `read` and
  `edit`, not the engine's six: a closing and a deletion are not permissions it
  has, and the name a route demands is the catalogue's (`permissions.needed`).
  The seventh act under the word — `scan` (item 51) — is the object's OWN and is
  measured in `test_scanner.py`, where the word it belongs to lives.
- **the entry stays out of it.** A credential is proved with the vault LOCKED —
  what is compared is a hash and no key is drawn —, which is §4's sentence about
  why what is proved is hashed and not sealed (item 176 put the same STRING on
  both doors; it did not put the key on the entrance).

Every test aims AT at a throwaway folder with `AT_ROOT`, so the checkout's own
Working Folder is never touched; none of them writes a key or a Main Key to
disk, and none needs a network or a model.
"""

from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import actors, boot, migrations, paths, permissions, secrets, tables
from at.data import schema, store
from at.encryption import vault
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import tree

ROOT = Path(__file__).resolve().parents[2]

# The phrase §4 writes as its own example of what a phrase is, and the value a
# service credential would be — the thing the table exists to carry.
PHRASE = "mariazinha comeu todo o pudim"
VALUE = "credencial-do-serviço-de-exemplo"
SERVICE = "notifier"

# Another service, so the scoping has something to be told apart from.
OTHER = "spelling-checker"


class SecretCase(unittest.TestCase):
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
        # The declarations are cached per process and this folder is gone: a
        # cache left behind would hand the next test a table that is not there.
        schema.reset()
        store.reset()
        self.scratch.cleanup()

    def sealed(self, **values: str) -> dict:
        """A row of the shipped table, through the Vault's door."""
        return secrets.seal(
            values.pop("name", "credencial"),
            values.pop("service", SERVICE),
            values.pop("value", VALUE),
            values.pop("phrase", PHRASE),
        )

    def row_file(self) -> Path:
        return paths.data_dir() / "secrets.jsonl"


class TheDeclaration(SecretCase):
    """What the product ships, and the names the door holds it to."""

    def test_the_table_ships_with_the_product(self):
        self.assertTrue((paths.data_dir() / schema.SCHEMA_DIR / "secret.json").is_file())
        self.assertIsNotNone(schema.of("secret"))

    def test_the_store_is_the_file_the_item_names(self):
        self.assertEqual(store.path("secret"), self.row_file())

    def test_the_field_that_carries_the_envelope_is_the_one_the_door_seals_into(self):
        # The two names live in two files — the declaration and `core.secrets` —
        # and this is what holds them together: renaming one without the other
        # would seal a value the table never opens.
        self.assertTrue(tables.sealed("secret", secrets.SEALED))
        self.assertEqual(
            schema.field("secret", secrets.SCOPE).get("label"),
            "table.secret.field.service",
        )

    def test_the_row_is_born_through_the_engine_like_any_other(self):
        self.assertEqual(self.sealed()["id"], 1)
        self.assertEqual([row["name"] for row in store.load("secret")], ["credencial"])

    def test_the_table_is_a_system_default_and_its_type_is_declared(self):
        # The WebApp resolves a reference through the declared TYPE, and `secret`
        # is one of §4's system tables.
        declared = schema.of("secret") or {}
        self.assertEqual(declared.get("type"), "secret")
        self.assertEqual(declared.get("store"), "data/secrets.jsonl")


class TheSealedValue(SecretCase):
    """What reaches the store, and what a person reads where the value would be."""

    def test_the_store_keeps_the_envelope_and_not_the_value(self):
        row = self.sealed()
        self.assertTrue(row[secrets.SEALED].startswith(f"{vault.SEALED}:"))
        raw = self.row_file().read_bytes()
        self.assertNotIn(VALUE.encode("utf-8"), raw)
        self.assertNotIn(PHRASE.encode("utf-8"), raw)

    def test_the_phrase_never_reaches_the_folder(self):
        # The Main Key is what the person knows and types (§4), and nothing
        # AT writes holds it: not the row, not the settings, not the counters.
        self.sealed()
        for path in self.root.rglob("*"):
            if path.is_file():
                with self.subTest(file=path.relative_to(self.root)):
                    self.assertNotIn(PHRASE.encode("utf-8"), path.read_bytes())

    def test_the_key_is_drawn_again_and_opens_it(self):
        # Nothing stores a derived key either: it comes back from the phrase
        # alone, which is what §4 means by the Main Key recovering it.
        row = self.sealed()
        again = secrets.key_of(SERVICE, PHRASE)
        self.assertEqual(vault.unseal(row[secrets.SEALED], again), VALUE)

    def test_two_seals_of_one_value_are_two_envelopes(self):
        self.assertNotEqual(
            self.sealed(name="um")[secrets.SEALED],
            self.sealed(name="dois")[secrets.SEALED],
        )

    def test_the_view_shows_the_mask(self):
        row = self.sealed()
        _, answer, _, _, _ = door.run("secret", "view", [str(row["id"])])
        self.assertIn(tr("table.word.sealed"), answer)
        self.assertNotIn(row[secrets.SEALED], answer)

    def test_the_listing_reads_the_row_without_the_value(self):
        # What a listing carries is the METADATA — which service, and which
        # name — and the sealed value is not a column of it: a row a person
        # reads is a row without the envelope, and never a row with a mask over
        # it (`test_the_view_shows_the_mask` is the door that says there is one).
        row = self.sealed()
        _, answer, _, _, _ = door.run("secret", "list", [])
        self.assertNotIn(row[secrets.SEALED], answer)
        self.assertNotIn(tr("table.word.sealed"), answer)
        self.assertIn(SERVICE, answer)
        self.assertIn("credencial", answer)

    def test_the_other_language_speaks_its_own_word(self):
        row = self.sealed()
        with mock.patch.dict(os.environ, {"AT_LANG": "en_US"}):
            i18n.reset()
            self.assertEqual(
                tables.text_of("secret", secrets.SEALED, row[secrets.SEALED]), "sealed"
            )


class TheType(SecretCase):
    """The sealed field, held to its rule by the engine that reads it."""

    def test_a_cleartext_is_refused_by_the_engine(self):
        # The one thing the type exists for: a secret typed into the column is a
        # refusal, and never a value written into a file a person commits.
        with self.assertRaises(tables.TableError) as refused:
            tables.create(
                "secret", {"name": "n", "service": SERVICE, secrets.SEALED: VALUE}
            )
        self.assertEqual(
            str(refused.exception),
            tr("table.error.not_sealed", field=tr("table.secret.field.value")),
        )
        self.assertFalse(self.row_file().exists())

    def test_a_hand_edited_envelope_is_refused_too(self):
        for wrong in ("xsalsa20poly1305", "outro-algoritmo:QUJD", "xsalsa20poly1305:"):
            with self.subTest(value=wrong):
                with self.assertRaises(tables.TableError):
                    tables.create(
                        "secret",
                        {"name": "n", "service": SERVICE, secrets.SEALED: wrong},
                    )

    def test_an_empty_value_is_nothing_and_not_a_hidden_something(self):
        # What a clearing leaves: no envelope, and never a hidden something —
        # the mask says there is a value behind it, and there is none.
        row = tables.create(
            "secret", {"name": "n", "service": SERVICE, secrets.SEALED: ""}
        )
        self.assertEqual(row[secrets.SEALED], "")
        self.assertEqual(
            tables.text_of("secret", secrets.SEALED, row[secrets.SEALED]),
            tr("table.word.none"),
        )

    def test_the_engine_does_not_hand_the_envelope_over(self):
        # A form opens on what a row already carries, and the envelope is not
        # one of the things a surface is handed: only the key opens it.
        row = self.sealed()
        with self.assertRaises(tables.TableError) as refused:
            tables.raw_of("secret", secrets.SEALED, row[secrets.SEALED])
        self.assertEqual(
            str(refused.exception),
            tr("table.error.sealed_value", field=tr("table.secret.field.value")),
        )

    def test_a_sealed_value_is_unspeakable_into_the_field(self):
        # One reader per kind and none of them is this one (`nlu.KINDS`), which
        # is what makes the value unspeakable without a line about secrets: the
        # sentence's residue goes where the primary field goes, and an envelope
        # only ever arrives through the door that holds the phrase.
        from at import nlu

        self.assertNotIn("sealed", nlu.KINDS)
        proposal = nlu.propose("cria um secret com value abracadabra")
        self.assertIsInstance(proposal, nlu.Proposal)
        self.assertNotIn(secrets.SEALED, proposal.values)

    def test_a_key_outside_the_closed_list_is_refused_by_its_name(self):
        where = paths.data_dir() / schema.SCHEMA_DIR / "secret.json"
        declared = json.loads(where.read_text(encoding="utf-8"))
        declared["fields"][secrets.SEALED]["algorithm"] = "aes256gcm"
        where.write_text(json.dumps(declared, ensure_ascii=False), encoding="utf-8")
        schema.reset()
        with self.assertRaises(tables.TableError) as refused:
            self.sealed()
        self.assertEqual(
            str(refused.exception),
            tr(
                "table.error.sealed_key",
                field=tr("table.secret.field.value"),
                named="algorithm",
            ),
        )


class TheScope(SecretCase):
    """The key of one service or purpose, and the one thing it refuses."""

    def test_the_same_scope_is_the_same_key(self):
        self.assertEqual(secrets.key_of(SERVICE, PHRASE), secrets.key_of(SERVICE, PHRASE))

    def test_two_scopes_are_two_keys(self):
        self.assertNotEqual(secrets.key_of(SERVICE, PHRASE), secrets.key_of(OTHER, PHRASE))

    def test_the_vault_key_recovers_a_lost_key(self):
        # §4: "the Main Key recovers any lost derived key". The derived key is
        # derived from it and from nothing stored — so a fresh phrase-derived
        # Main Key answers exactly the key that was lost.
        lost = vault.derived_key(vault.vault_key(PHRASE), SERVICE)
        self.assertEqual(secrets.key_of(SERVICE, PHRASE), lost)

    def test_the_key_of_one_service_opens_nothing_of_another(self):
        row = self.sealed()
        self.assertIsNone(vault.unseal(row[secrets.SEALED], secrets.key_of(OTHER, PHRASE)))

    def test_a_scope_that_is_not_a_name_is_refused(self):
        for wrong in ("", "   ", " notifier", "notifier ", None, 7):
            with self.subTest(scope=wrong):
                with self.assertRaises(secrets.SecretsError) as refused:
                    secrets.key_of(wrong, PHRASE)
                self.assertEqual(
                    str(refused.exception),
                    tr("secrets.error.scope", service=wrong),
                )

    def test_a_phrase_under_the_floor_is_refused_with_words_of_its_own(self):
        with self.assertRaises(secrets.SecretsError) as refused:
            secrets.key_of(SERVICE, "curta")
        self.assertEqual(
            str(refused.exception),
            tr("secrets.error.phrase", min=vault.MINIMUM),
        )


class TheOpen(SecretCase):
    """A read answers, and it never raises over a row it cannot open."""

    def setUp(self):
        super().setUp()
        self.row = self.sealed()

    def test_the_right_phrase_opens_it(self):
        self.assertEqual(secrets.open_value(self.row, PHRASE), VALUE)

    def test_the_wrong_phrase_answers_none(self):
        self.assertIsNone(
            secrets.open_value(self.row, "outra frase igualmente longa")
        )

    def test_a_phrase_under_the_floor_answers_none(self):
        self.assertIsNone(secrets.open_value(self.row, "curta"))

    def test_a_hand_edited_envelope_answers_none(self):
        edited = dict(self.row, **{secrets.SEALED: "xsalsa20poly1305:QUJD"})
        self.assertIsNone(secrets.open_value(edited, PHRASE))

    def test_a_hand_edited_scope_answers_none(self):
        # A scope a person rewrote into something that is not a name is a read
        # that has to answer, and the answer is that nothing opened.
        edited = dict(self.row, **{secrets.SCOPE: " notifier "})
        self.assertIsNone(secrets.open_value(edited, PHRASE))

    def test_a_row_that_is_not_one_answers_none(self):
        for wrong in ({}, {"id": 9}, None, "não é uma linha"):
            with self.subTest(row=wrong):
                self.assertIsNone(secrets.open_value(wrong, PHRASE))


class ThePermissions(SecretCase):
    """What the table declares to the engine, and the name a route demands."""

    def test_the_table_answers_read_and_edit(self):
        # And the two acts of its own — `secret scan` and `secret
        # install_hooks` — which are not of the engine's six and are declared
        # where every act of an object's own is (`permissions.NARROWED`). Both
        # are measured in `test_scanner.py`/`test_hooks.py`.
        self.assertEqual(
            permissions.catalogue().get("secret"),
            ("read", "edit", "scan", "install_hooks"),
        )
        self.assertTrue(permissions.is_known("secret:read"))
        self.assertTrue(permissions.is_known("secret:edit"))

    def test_the_two_actions_it_does_not_answer_are_not_permissions_it_has(self):
        # A secret is not closed and its deletion is not offered by a surface:
        # the engine has the six, and this table answers four of them.
        self.assertFalse(permissions.is_known("secret:cancel"))
        self.assertFalse(permissions.is_known("secret:delete"))

    def test_the_permission_is_the_declaration_s_and_not_the_action_s_name(self):
        self.assertEqual(permissions.needed("secret", "list"), "secret:read")
        self.assertEqual(permissions.needed("secret", "view"), "secret:read")
        self.assertEqual(permissions.needed("secret", "create"), "secret:edit")
        self.assertEqual(permissions.needed("secret", "edit"), "secret:edit")
        # A table that declares nothing demands the action's own name, exactly
        # as every table did before a declaration could narrow it.
        self.assertEqual(permissions.needed("task", "list"), "task:list")

    def test_the_help_offers_the_actions_the_table_answers(self):
        node = next(node for node in tree.table_nodes() if node.name == "secret")
        self.assertEqual(
            [child.name for child in node.children],
            ["list", "view", "create", "edit", "scan", "install_hooks"],
        )

    def test_the_closing_and_the_deletion_are_not_words_of_this_table(self):
        # A word that dispatches is a word the help offers, and vice versa.
        node = next(node for node in tree.table_nodes() if node.name == "secret")
        self.assertNotIn("cancel", [child.name for child in node.children])
        self.assertNotIn("delete", [child.name for child in node.children])

    def test_the_administrator_carries_both(self):
        # The role is built from the catalogue, and the catalogue is what says
        # the table answers these two — and the scan of item 51 and the
        # install_hooks beside it, the third and fourth `secret:` entries the
        # catalogue names today.
        role = actors.role_for_admin()
        self.assertEqual(
            sorted(
                name
                for name in permissions.carried(role)
                if name.startswith("secret:")
            ),
            ["secret:edit", "secret:install_hooks", "secret:read", "secret:scan"],
        )

    def test_a_read_is_a_read_and_a_write_is_a_write(self):
        # The four numbers item 15 closed, over the table's own entries: reading
        # a name is a read, and sealing one is a write — neither of them is
        # "changing what the system allows", which is what `0.8` is for.
        self.assertEqual(permissions.risk("secret:read"), permissions.RISK_READ)
        self.assertEqual(permissions.risk("secret:edit"), permissions.RISK_WRITE)


class TheEntry(SecretCase):
    """A credential is proved with the vault locked (§4, item 8; item 176)."""

    def test_the_vault_is_reached_by_eight_files_and_by_them_alone(self):
        # Item 14a landed the vault with no caller anywhere and said so in a
        # test; the slice that landed the table gave it the first two. They are
        # the door that SEALS (`core/secrets`) and the engine that knows the
        # shape of the envelope it validates (`core/tables`) — and a third file
        # is a decision and not an accident, the same way the pin in
        # `test_encryption.py` names the files that speak to `libsodium`.
        #
        # **O outro é o `at-deploy`** (item 50), e ele entrou com um motivo
        # próprio: o que a pasta guarda dos valores que o AT SORTEIA é o
        # envelope, e quem sela e abre não é uma linha de tabela e sim o arquivo
        # — o `at_deploy/environment.py` para o portão e os três do provedor.
        #
        # **O quinto é `core/backup.py`** (item 51): o arquivo que o backup manda
        # para fora não é uma linha de tabela nem um valor que o container encheu
        # — é a Pasta de Trabalho inteira, num arquivo só —, e por isso a chave
        # derivada e o par `seal_bytes`/`unseal_bytes` entram por ele, e não pela
        # porta que sela linhas.
        #
        # **O sexto é `core/strongbox.py`** (TASK-154): a pasta que sela sozinha
        # não guarda uma linha de tabela nem um arquivo do container — é um
        # arquivo qualquer que a pessoa largou —, e por isso o par
        # `seal_bytes`/`unseal_bytes` entra por ele também, com a chave do
        # escopo `cofre` chegando pela porta de `at.ui.webapp.keys`.
        #
        # **O sétimo é `core/actors.py`** (item 176): a credencial do primeiro
        # administrador É a Chave Principal, então o piso dela é o piso do cofre
        # e a entrada o lê DAQUI em vez de nomear um segundo número. É o único
        # motivo pelo qual a entrada alcança o cofre — e ele não é uma chave:
        # quem PROVA alguém continua comparando um hash, com o cofre fechado
        # (`test_vault.py::TheEntry`, e o teste abaixo).
        #
        # **O oitavo é `services/caddy.py`** (TASK-177, 02/10/2026): o caminho
        # hospedado e o caminho container escrevem no MESMO `App/services/caddy/gate`, e o
        # container sela o que escreve ali. Este arquivo não sela nem abre nada —
        # ele só RECONHECE o envelope do outro caminho (`vault.envelopes`), para
        # não ler o texto cifrado como se fosse a sua própria senha em claro.
        # Reconhecer a forma não é a mesma porta que lê o conteúdo, e é por isso
        # que ele entra aqui sem ganhar uma chave.
        #
        # **O ntfy saiu, e com ele uma nona porta** (a fatia do Web Push,
        # 03/10/2026): `core/notifier.py` não abre mais o envelope do token do
        # notificador — não há token, não há envelope, não há chave derivada a
        # usar. A notificação é o Web Push do PWA (`core/push.py`), que cifra
        # contra a chave do NAVEGADOR e não toca o Cofre.
        #
        # **E `core/assist.py` entrou** (o Jev primário, 03/10/2026): configurar
        # a credencial do Jev (o `secret` de escopo `jev`) SELA o valor com a
        # chave derivada, pela mesma porta do Cofre — é a oitava entrada.
        # contra a chave do NAVEGADOR e não toca o Cofre.
        #
        # Sorted, because the filesystem hands the files over in an order of its
        # own and the list below is the declaration, not a directory listing.
        callers = sorted(
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "at", ROOT / "at_deploy")
            for path in root.rglob("*.py")
            if "tests" not in path.parts and reaches_vault(path)
        )
        self.assertEqual(callers, [
            "at/core/actors.py", "at/core/assist.py", "at/core/backup.py",
            "at/core/secrets.py", "at/core/strongbox.py", "at/core/tables_types.py",
            "at/services/caddy_gate.py", "at_deploy/environment.py", "at_deploy/environment_secrets.py",
        ])

    def test_the_surface_that_reaches_the_vault_is_the_deploy_and_no_screen(self):
        # §4's three grades — typing the phrase when AT starts, `~/.at/`, the
        # Working Folder — are a SURFACE's choice, with its price said out loud.
        # **A escolha foi feita, e ela é a nota `S`**: quem sobe o ambiente
        # digita a Chave Principal (`at-deploy up`), e é ela que sela o que a
        # subida sorteia e abre o que a pasta guarda (item 50).
        #
        # O que esta linha tranca é a ESCOLHA e não a ausência dela: a
        # superfície que DIGITA a Chave Principal é UMA — o `at-deploy` —, e a outra, a
        # tela, continua de fora: nenhum arquivo de `at/ui` pergunta a Chave Principal, e
        # o WebApp não digita nenhuma. **O que mudou (item 50, corte g) é que a
        # tela continua de fora: nenhum arquivo de `at/ui` pergunta a Chave
        # Principal, e o WebApp não digita nenhuma — o núcleo que toca o Cofre
        # está sob `at/core`, não sob `at/ui`.
        # **E é um arquivo só do artefato**: o `environment`, que sela o que a
        # subida sorteia e abre o que ela monta.
        reached = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "at_deploy").rglob("*.py")
            if "tests" not in path.parts and reaches_vault(path)
        )
        self.assertEqual(reached, ["at_deploy/environment.py", "at_deploy/environment_secrets.py"])
        for path in (ROOT / "at" / "ui").rglob("*.py"):
            if "tests" in path.parts:
                continue
            with self.subTest(file=path.relative_to(ROOT)):
                self.assertFalse(reaches_vault(path))

    def test_a_credential_is_proved_with_the_vault_locked(self):
        # Nothing was opened in this folder and no key was drawn, and the door
        # works: what is compared is a hash. It is the SAME string the vault
        # opens with (item 176) — the point of the item — and the entrance still
        # does not need the vault to prove anybody.
        actors.create_admin("Rafael", "uma-frase-bem-longa")
        self.assertIsNotNone(actors.authenticate("Rafael", "uma-frase-bem-longa"))
        self.assertIsNone(actors.authenticate("Rafael", "outra-frase-bem-longa"))


class TheMigration(SecretCase):
    """A folder that already exists gains the table, and its ceiling."""

    def declaration(self) -> Path:
        return paths.data_dir() / schema.SCHEMA_DIR / "secret.json"

    def strip(self) -> None:
        """Leave the folder as one born BEFORE this release is: no declaration,
        no stamp of eleven, and an administrator whose role was built from the
        catalogue of that day."""
        actors.role_for_admin()
        self.declaration().unlink()
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 11)
            ),
            encoding="utf-8",
        )
        schema.reset()

    def test_a_folder_without_the_table_gains_it(self):
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertTrue(self.declaration().is_file())
        self.assertIsNotNone(schema.of("secret"))
        role = actors.admin_role() or {}
        self.assertIn("secret:read", permissions.carried(role))
        self.assertIn("secret:edit", permissions.carried(role))

    def test_a_declaration_a_person_deleted_is_not_brought_back(self):
        # A deletion that was meant stays one, and the promise is the migration
        # running ONCE: the seed writes what is ABSENT — which is what the swap
        # needs — and, stamped, it does not come back on the next start to argue
        # with whoever took the file out on purpose.
        self.strip()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertTrue(self.declaration().is_file())
        self.assertIn(11, migrations.applied())

        self.declaration().unlink()
        schema.reset()
        with redirect_stdout(StringIO()):
            migrations.run(None)
        self.assertFalse(self.declaration().is_file())


def reaches_vault(path: Path) -> bool:
    """Whether the module imports `at.encryption.vault` — the caller's mark."""
    try:
        parsed = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(parsed):
        if isinstance(node, ast.ImportFrom) and node.module == "at.encryption":
            if any(alias.name == "vault" for alias in node.names):
                return True
        elif isinstance(node, ast.Import):
            if any(alias.name in ("at.encryption.vault", "vault") for alias in node.names):
                return True
    return False


if __name__ == "__main__":
    unittest.main()
