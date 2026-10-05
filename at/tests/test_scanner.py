"""`at-cli secret scan` — the folder says what it carries that it should not (item 51).

The philosophy is that the folder is copied WITHOUT encryption and that what the
person writes in it is theirs: the AT does not hide it. Not protecting is not the
same as not warning, and this is the second half of that same philosophy — the
folder is walked, and what turned up is SAID, with where and never with the value.

What this module measures, in the order the item decided it:

- **the word is the catalogue's seventh act under `secret`.** It is not one of
  the engine's six, so it is declared where every act of an object's own is
  (`permissions.NARROWED`), the help offers it and the dispatch takes it, and the
  administrator's role carries it — born with it, or handed it by migration.
- **the tool travels inside the artifact and is never installed.** The rules are
  `gitleaks`' own and the answer names them; the AT's own is the one that scans,
  and the machine's PATH is never consulted — a dependency nobody pinned, and a
  version the answer could not honestly name. What is left of the old shape is
  the refusal: where the scanner is not there — the extraction that failed — the
  person is told the ways out, nothing is run, and the exit code says the word
  did not close (§7a).
- **the walk is the folder and its history**, and the report lands outside the
  folder: a scan that wrote into the folder it audits would be writing what it
  was asked to look for.
- **the value never reaches a surface.** The report carries the secret and the
  module reads neither field; what a person reads is the rule and the place.
- **a read leaves nothing** — no `audit` line and no version (§3) — and none of
  it needs a network.

Every test aims AT at a throwaway folder with `AT_ROOT`, and the `gitleaks` is a
fake behind the module's one seam (`scanner.run`): no byte of the program is
executed, and the suite runs on a machine that has never seen it. The one class
that touches the real payload (`TheScannerATCarries`) unpacks it the way the
product does and stops there — it never runs what came out.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import socket
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from at import i18n
from at.core import (
    actors,
    boot,
    files,
    migrations,
    paths,
    permissions,
    scanner,
    tables,
    versioning,
)
from at.data import schema, store
from at.i18n import tr
from at.services import gitleaks
from at.ui.cli import main, tree

# The secret a report carries, and the one thing no surface may ever draw. It is
# a value nobody could mistake for the rule or the path beside it.
VALUE = "chave-supersecreta-que-nao-pode-sair"

# Every sentence this word says, and the label of its tree word. A key a catalog
# does not have answers with the KEY itself, which is why the list exists: a
# message added without its line here is a message nobody checks.
SAID = (
    "permission.action.scan",
    "secrets.scan.rules",
    "secrets.scan.clean",
    "secrets.scan.found",
    "secrets.scan.finding",
    "secrets.scan.committed",
    "secrets.scan.no_tool",
    "secrets.scan.ways",
    "secrets.scan.failed",
)


def leak(rule: str, where: str, line: int, commit: str | None = None) -> dict:
    """One entry of the tool's report, as the tool writes it.

    The `Secret` and the `Match` are here ON PURPOSE and full of the value: the
    fake has to hand over what the real one hands over, or the test would be
    proving that AT does not print a field nobody ever gave it.
    """
    return {
        "RuleID": rule,
        "Description": f"{rule} rule",
        "File": where,
        "StartLine": line,
        "EndLine": line,
        "Secret": VALUE,
        "Match": f"token = {VALUE}",
        "Commit": commit or "",
    }


class FakeGitleaks:
    """The `gitleaks` of the suite — the seam (`scanner.run`), never the program.

    `walks` is what each walk writes as its report, in order: the files first,
    and the history after it, when the folder carries one. `None` in that list is
    a walk that leaves no report at all — the tool's quiet answer, or its
    refusal, whichever the exit `code` says.

    `calls` is every invocation, so a test can read WHICH walk the tool was
    asked for, and whether it was asked anything at all.
    """

    def __init__(
        self,
        *walks: list[dict] | None,
        code: int = 1,
        version: str = "8.18.4",
    ) -> None:
        self.walks = list(walks)
        self.code = code
        self.version = version
        self.calls: list[list[str]] = []

    def __call__(self, args) -> subprocess.CompletedProcess:
        call = [str(part) for part in args]
        self.calls.append(call)
        if call[:1] == ["version"]:
            return subprocess.CompletedProcess(call, 0, self.version + "\n", "")
        written = self.walks.pop(0) if self.walks else None
        if written is not None:
            where = call[call.index("--report-path") + 1]
            Path(where).write_text(json.dumps(written), encoding="utf-8")
        return subprocess.CompletedProcess(call, self.code, "", "")

    def walks_asked(self) -> list[list[str]]:
        """The calls that walked something, in order — the version call is not one."""
        return [call for call in self.calls if call[:1] == ["detect"]]

    def reports(self) -> list[str]:
        """Where the tool was told to write each report."""
        return [
            call[call.index("--report-path") + 1] for call in self.walks_asked()
        ]


class ScannerCase(unittest.TestCase):
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

    def tool(self, *walks: list[dict] | None, **kw) -> FakeGitleaks:
        """A `gitleaks` standing at the seam, and the tool is found at it.

        The path answered is the one the product answers — inside the folder —
        so a test that reads it reads what the unpacking would have left there.
        """
        fake = FakeGitleaks(*walks, **kw)
        self.under(mock.patch.object(scanner, "found", return_value=str(gitleaks.binary())))
        self.under(mock.patch.object(scanner, "run", new=fake))
        return fake

    def absent(self) -> mock.Mock:
        """A scanner that is not there — and a `run` nobody may call."""
        self.under(mock.patch.object(scanner, "found", return_value=None))
        never = mock.Mock(side_effect=AssertionError("no gitleaks, no call"))
        self.under(mock.patch.object(scanner, "run", new=never))
        return never

    def state(self, here: str) -> None:
        """What the folder is, versioning-wise — the question the walk order asks.

        It replaces the module the SCANNER holds and never `versioning` itself:
        the real `state` is read on every run by `boot` and by `versioning.ensure`,
        and a folder the rest of the product was told is `bare` would have a
        repository born over it mid-test.
        """
        self.under(
            mock.patch.object(
                scanner,
                "versioning",
                SimpleNamespace(
                    state=lambda: here,
                    OWNED=versioning.OWNED,
                    FOREIGN=versioning.FOREIGN,
                    BARE=versioning.BARE,
                    MISSING=versioning.MISSING,
                    # `_excluded` reads this off the SAME module — the real one,
                    # untouched: what generates `App/services/`
                    # is a fact of the folder, not of the versioning STATE this
                    # helper exists to fake.
                    generated_dirs=versioning.generated_dirs,
                ),
            )
        )

    def under(self, patcher: mock._patch) -> None:
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["secret", "scan", *words])
        return code, output.getvalue()


class TheWord(ScannerCase):
    """The act in the catalogue, in the tree and in the role."""

    def test_the_catalogue_names_the_seventh_act(self):
        self.assertEqual(
            permissions.catalogue().get("secret"), ("read", "edit", "scan")
        )
        self.assertTrue(permissions.is_known("secret:scan"))
        # It is a read: it reports and corrects nothing, so it moves no ceiling.
        self.assertEqual(permissions.risk("secret:scan"), permissions.RISK_READ)
        self.assertEqual(permissions.needed("secret", "scan"), "secret:scan")

    def test_the_tree_offers_it_beside_the_engine_s_acts(self):
        node = next(node for node in tree.table_nodes() if node.name == "secret")
        self.assertEqual(
            [child.name for child in node.children],
            ["list", "view", "create", "edit", "scan"],
        )
        # The KEY of an act the engine does not have is the catalogue's block,
        # never the engine's: a `Node.about` is an i18n key, and drawing the
        # engine's would answer with the key itself.
        about = {child.name: child.about for child in node.children}
        self.assertEqual(about["scan"], "permission.action.scan")
        self.assertEqual(tr(about["scan"]), "Varrer")

    def test_the_administrator_carries_it(self):
        role = actors.role_for_admin()
        self.assertIn("secret:scan", permissions.carried(role))

    def test_the_two_actions_the_table_has_never_had_stay_out_of_it(self):
        # A scan is the seventh act, and it is not a fourth engine permission: a
        # closing and a deletion are still permissions the table does not have.
        self.assertFalse(permissions.is_known("secret:cancel"))
        self.assertFalse(permissions.is_known("secret:delete"))


class TheWalk(ScannerCase):
    """What the tool is asked for, and where its report is written."""

    def test_the_files_are_walked_and_no_history_is_invented(self):
        self.state(versioning.BARE)
        fake = self.tool([])
        self.scan()
        asked = fake.walks_asked()
        self.assertEqual(len(asked), 1)
        self.assertIn("--no-git", asked[0])
        self.assertEqual(asked[0][asked[0].index("--source") + 1], str(self.root))

    def test_the_history_is_walked_where_the_folder_carries_one(self):
        self.state(versioning.OWNED)
        fake = self.tool([], [])
        self.scan()
        asked = fake.walks_asked()
        self.assertEqual(len(asked), 2)
        self.assertIn("--no-git", asked[0])
        self.assertNotIn("--no-git", asked[1])

    def test_a_foreign_repository_is_walked_too(self):
        # A repository the person arranged is a history like AT's own: what the
        # folder carries is what the folder carries, whoever drove git.
        self.state(versioning.FOREIGN)
        fake = self.tool([], [])
        self.scan()
        self.assertEqual(len(fake.walks_asked()), 2)

    def test_the_report_is_written_outside_the_folder(self):
        # A scan that wrote its report into the folder it audits would be writing
        # exactly what it was asked to look for.
        self.state(versioning.BARE)
        fake = self.tool([])
        self.scan()
        for where in fake.reports():
            with self.subTest(report=where):
                self.assertFalse(Path(where).is_relative_to(self.root))

    def test_a_place_the_files_carry_is_one_finding(self):
        # The same leak is found twice — in the files as they are, and in the
        # commit that carries them — and it is ONE finding: what a person needs
        # is where it is, and the path they can open is the worktree's.
        self.state(versioning.OWNED)
        place = ("generic-api-key", "Tabelas/tasks.jsonl", 12)
        self.tool(
            [leak(*place)],
            [leak(*place, commit="a" * 40)],
        )
        _, text = self.scan()
        self.assertEqual(text.count("Tabelas/tasks.jsonl:12"), 1)
        self.assertNotIn("commit", text)

    def test_a_place_only_the_history_keeps_says_the_commit(self):
        self.state(versioning.OWNED)
        self.tool([], [leak("aws-access-token", "nota.md", 3, commit="abcdef0" + "b" * 33)])
        _, text = self.scan()
        self.assertIn("nota.md:3", text)
        self.assertIn("abcdef0", text)

    def test_nothing_found_is_an_answer_and_not_a_failure(self):
        self.state(versioning.BARE)
        self.tool([], code=0)
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.scan.clean"), text)


class TheExclusion(ScannerCase):
    """What AT itself fills — `App/services/` — scans clean
    (item 51: a path exemption, not the vault's constructive one)."""

    def test_a_finding_under_the_caddys_storage_is_not_accused(self):
        self.state(versioning.BARE)
        self.tool([leak("generic-api-key", "App/services/caddy/storage/root.key", 1)], code=1)
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.scan.clean"), text)

    def test_a_finding_under_a_services_own_state_is_not_accused(self):
        self.state(versioning.BARE)
        self.tool(
            [leak("generic-api-key", "App/services/exemplo/token", 1)], code=1
        )
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.scan.clean"), text)

    def test_a_secret_outside_those_two_paths_is_accused_as_before(self):
        self.state(versioning.BARE)
        self.tool(
            [
                leak("generic-api-key", "App/services/caddy/storage/root.key", 1),
                leak("aws-access-token", "Arquivos/nota.md", 3),
            ],
            code=1,
        )
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.scan.found"), text)
        self.assertIn("Arquivos/nota.md:3", text)
        self.assertNotIn("root.key", text)

    def test_a_history_finding_under_a_generated_path_is_excluded_too(self):
        self.state(versioning.OWNED)
        self.tool(
            [],
            [leak("generic-api-key", "App/services/identity/secrets/session",
                  2, commit="a" * 40)],
            code=1,
        )
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.scan.clean"), text)

    def test_the_exclusion_is_the_same_list_the_gitignore_writes(self):
        excluded = {where.name for where in versioning.generated_dirs()}
        self.assertEqual(excluded, {"services"})


class TheAnswer(ScannerCase):
    """What a person reads — and the one thing they never do."""

    def test_the_value_is_never_drawn(self):
        self.state(versioning.BARE)
        self.tool([leak("generic-api-key", "Arquivos/nota.md", 7)])
        code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertNotIn(VALUE, text)
        self.assertIn("generic-api-key", text)
        self.assertIn("Arquivos/nota.md:7", text)

    def test_it_says_the_rules_it_serves_itself_from(self):
        # The list of rules AGES, and the whole answer to that is to say WHICH
        # scanner and which version stood behind the finding.
        self.state(versioning.BARE)
        self.tool([])
        _, text = self.scan()
        self.assertIn(scanner.BINARY, text)
        self.assertIn("8.18.4", text)

    def test_without_the_tool_it_says_the_two_ways_and_installs_nothing(self):
        never = self.absent()
        code, text = self.scan()
        self.assertEqual(code, 1)
        self.assertIn(tr("secrets.scan.no_tool", platform=gitleaks.label()), text)
        self.assertIn(tr("secrets.scan.ways"), text)
        never.assert_not_called()

    def test_a_report_it_cannot_read_is_a_refusal(self):
        # The tool exited outside its own quiet codes and left nothing to read:
        # that is a refusal, and AT says so instead of pretending a clean folder.
        self.state(versioning.BARE)
        self.tool(None, code=2)
        code, text = self.scan()
        self.assertEqual(code, 1)
        self.assertIn(tr("secrets.scan.failed"), text)

    def test_an_extra_argument_is_a_usage_error(self):
        self.absent()
        code, text = self.scan("--all")
        self.assertEqual(code, 2)
        self.assertIn(tr("cli.error.rejected_arguments", word=permissions.SCAN), text)

    def test_a_scan_leaves_no_line_and_no_version(self):
        # §3: reading is not doing. A scan writes nothing, so there is no audit
        # line to keep and no version to take.
        self.state(versioning.BARE)
        self.tool([leak("generic-api-key", "Arquivos/nota.md", 7)])
        before = files.writes()
        self.scan()
        self.assertEqual(files.writes(), before)
        self.assertEqual(
            [line for line in store.load("audit") if line.get("what") == "secret:scan"],
            [],
        )

    def test_the_scan_needs_no_network(self):
        self.state(versioning.BARE)
        self.tool([leak("generic-api-key", "Arquivos/nota.md", 7)])
        with mock.patch.object(
            socket, "socket", side_effect=AssertionError("the scan needs no network")
        ):
            code, text = self.scan()
        self.assertEqual(code, 0)
        self.assertIn("generic-api-key", text)

    def test_every_sentence_speaks_both_languages(self):
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                with mock.patch.dict(os.environ, {"AT_LANG": language}):
                    i18n.reset()
                    for key in SAID:
                        self.assertNotEqual(tr(key), key)


class TheScannerATCarries(ScannerCase):
    """The tool is the artifact's, and the machine's PATH is never consulted.

    This is the decision of slice 2, and it is a decision: a `gitleaks` the
    person installed may well be newer than the one the release froze, and it is
    still not the one that scans. It would be a dependency nobody pinned — and
    the version this module says stood behind a scan is a fact about the release
    only while there is one candidate to say it about. The Caddy's precedent, and
    the reason the answer reads the same on two machines.
    """

    def test_the_scan_finds_the_one_the_artifact_carries(self):
        # The real payload, unpacked for real: the Caddy's class does the same,
        # and it is what keeps the tarball honest — a placeholder would land a
        # file that fails everything below.
        self.assertEqual(scanner.found(), str(gitleaks.binary()))
        self.assertTrue(gitleaks.binary().is_file())
        self.assertEqual(gitleaks.stamp_file().read_text(encoding="utf-8").strip(),
                         gitleaks.platform_name())

    def test_the_path_is_never_consulted(self):
        # A machine that already answers `which gitleaks` must not change what
        # runs. The guard is the call itself: any lookup on the PATH from here
        # down is a regression, and it fails rather than passing quietly.
        with mock.patch.object(
            shutil, "which", side_effect=AssertionError("the PATH is not the source")
        ):
            self.assertEqual(scanner.found(), str(gitleaks.binary()))

    def test_the_extraction_that_failed_is_the_no_tool_state(self):
        # The artifact carries none for this platform — one of the three ways the
        # extraction fails, and the one a person hits by running the wrong
        # release. It is the state `no_tool` names, with the ways out beside it.
        with mock.patch.object(scanner.embedded, "ensure", return_value=None):
            self.assertIsNone(scanner.found())
            code, text = self.scan()
        self.assertEqual(code, 1)
        self.assertIn(tr("secrets.scan.no_tool", platform=gitleaks.label()), text)
        self.assertIn(tr("secrets.scan.ways"), text)

    def test_a_payload_it_cannot_unpack_is_the_same_state(self):
        # The other way: the tarball is there and is not one AT can read. It is
        # the same thing to the person — the scanner is not there —, so it is the
        # same state, and the door says the same ways out.
        with mock.patch.object(
            scanner.embedded,
            "ensure",
            side_effect=gitleaks.GitleaksError("carries no gitleaks"),
        ):
            self.assertIsNone(scanner.found())


class TheMigration(ScannerCase):
    """A folder that already exists gains the act, and its ceiling."""

    def strip(self) -> None:
        """Leave the folder as one born BEFORE this release is: no stamp of
        sixteen, and an administrator whose role was built from the catalogue of
        that day — which did not name the act."""
        role = actors.role_for_admin()
        tables.edit(
            "role",
            store.number_of(role),
            {
                "permissions": ",".join(
                    name
                    for name in permissions.all_permissions()
                    if name not in migrations.SCANNER_PERMISSIONS
                )
            },
        )
        migrations.stamp_file().write_text(
            json.dumps(
                sorted(item.ident for item in migrations.MIGRATIONS if item.ident != 16)
            ),
            encoding="utf-8",
        )

    def test_the_role_that_never_had_it_hears_it_granted(self):
        self.strip()
        output = StringIO()
        with redirect_stdout(output):
            migrations.run(None)
        role = actors.admin_role() or {}
        self.assertIn("secret:scan", permissions.carried(role))
        self.assertIn(
            tr(
                "boot.migration.catalogue.granted",
                role=actors.ADMIN_ROLE,
                names=", ".join(migrations.SCANNER_PERMISSIONS),
            ),
            output.getvalue(),
        )

    def test_the_catalogue_of_a_folder_born_today_already_carries_it(self):
        # The other side of the same fact: a folder born by this release has the
        # role the catalogue of TODAY names, and the migration has nothing to do.
        role = actors.role_for_admin()
        self.assertEqual(
            sorted(
                name for name in permissions.carried(role) if name.startswith("secret:")
            ),
            ["secret:edit", "secret:read", "secret:scan"],
        )
        self.assertIn(16, migrations.applied())


if __name__ == "__main__":
    unittest.main()
