"""`at-cli secret install_hooks` — the varredura becomes `git`'s own portão.

`.claude/CLAUDE.md` already names the practice by hand: scan before a commit,
scan before a push, refuse the one and the other when the folder is not clean.
This module is that practice become product — `core.hooks` writes the two git
hooks, and what this suite proves is that they actually gate a REAL `git
commit` and a REAL `git push`, with the embedded `gitleaks` genuinely run
(never faked, unlike `test_scanner.py`'s own seam): a commit or a push that
only ever talked to a mock would not be proof that anything is refused.

**The repository the hooks protect is never this session's `AT_ROOT`.** It is
a throwaway git repository of the test's own, built the way `versioning`'s own
suite builds one — `TheGate` is the class that proves the product's whole
point: a folder that is nobody's Working Folder (§3) still gets the gate, by
`--repo`.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, hooks
from at.i18n import tr
from at.ui.cli import main

GIT = shutil.which("git")
SKIP = "git is not on this machine"


class HooksCase(unittest.TestCase):
    """A Working Folder of its own — for the CLI's permission to read, not for
    the repository `install` protects, which each test builds beside it."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def cli(self, *words: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["secret", "install_hooks", *words])
        return code, output.getvalue()


class TheInstall(HooksCase):
    """`core.hooks.install` on its own — no `git` subprocess runs here."""

    def test_a_folder_with_no_git_is_refused(self):
        foreign = self.root / "plain"
        foreign.mkdir()
        report = hooks.install(foreign)
        self.assertEqual(report.state, hooks.NOT_A_REPO)

    def test_a_repository_gains_both_hooks_executable(self):
        repo = self.root / "repo"
        (repo / ".git").mkdir(parents=True)
        report = hooks.install(repo)
        self.assertEqual(report.state, hooks.INSTALLED)
        for name in hooks.HOOK_NAMES:
            hook = repo / ".git" / "hooks" / name
            self.assertTrue(hook.is_file())
            self.assertTrue(os.access(hook, os.X_OK))
            self.assertIn(str(repo), hook.read_text(encoding="utf-8"))

    def test_the_default_target_is_the_working_folder(self):
        # No `repo` named: the Working Folder this session already carries —
        # `boot` versions it, so it already has a `.git` to write into.
        report = hooks.install()
        self.assertEqual(report.state, hooks.INSTALLED)
        self.assertEqual(report.target, self.root)
        self.assertTrue((self.root / ".git" / "hooks" / hooks.PRE_COMMIT).is_file())

    def test_a_prior_hook_is_replaced_and_not_merged(self):
        repo = self.root / "repo"
        (repo / ".git" / "hooks").mkdir(parents=True)
        prior = repo / ".git" / "hooks" / hooks.PRE_COMMIT
        prior.write_text("#!/bin/sh\necho somebody else's hook\n", encoding="utf-8")
        hooks.install(repo)
        self.assertIn(str(repo), prior.read_text(encoding="utf-8"))


class TheCLI(HooksCase):
    """`secret install_hooks`, through `main` — usage, refusal and the word."""

    def test_extra_arguments_without_repo_are_a_usage_error(self):
        code, _ = self.cli("--unknown")
        self.assertEqual(code, 2)

    def test_repo_without_a_value_is_a_usage_error(self):
        code, _ = self.cli("--repo")
        self.assertEqual(code, 2)

    def test_a_foreign_path_with_no_git_is_refused(self):
        foreign = self.root / "plain"
        foreign.mkdir()
        code, text = self.cli("--repo", str(foreign))
        self.assertEqual(code, 1)
        self.assertIn(tr("secrets.hooks.not_a_repo", where=str(foreign)), text)

    def test_the_default_target_installs_and_says_so(self):
        code, text = self.cli()
        self.assertEqual(code, 0)
        self.assertIn(tr("secrets.hooks.installed", where=str(self.root)), text)


@unittest.skipUnless(GIT, SKIP)
class TheGate(unittest.TestCase):
    """The hook blocks a REAL `git commit` and a REAL `git push` while the
    repository carries a secret in clear, with the embedded `gitleaks` genuinely
    run — and lets both through once it does not."""

    SECRET = 'aws_secret_access_key = "AKIAABCDEFGHIJKLMNOP"\n'

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._git("init", "--quiet", "-b", "main")
        self.remote = self.root / "remote.git"
        subprocess.run(
            ["git", "init", "--quiet", "--bare", str(self.remote)], check=True
        )
        self._git("remote", "add", "origin", str(self.remote))
        # The repository this gate protects is nobody's Working Folder — the
        # product's own rule (§3) — so `AT_ROOT` here is never the repo. It is
        # left UNSET for the committer's own shell, the way a real one mostly
        # is; `test_an_ambient_working_folder_is_scanned_too` is the one case
        # that sets it.
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("AT_ROOT", None)

    def tearDown(self):
        self.env.stop()
        self.scratch.cleanup()

    def _git(self, *args: str, check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "git",
                "-c", "user.name=Test",
                "-c", "user.email=test@example.com",
                *args,
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=check,
        )

    def _write(self, text: str) -> None:
        (self.repo / "config.py").write_text(text, encoding="utf-8")
        self._git("add", "config.py", check=True)

    def test_a_secret_in_clear_blocks_commit_and_a_clean_one_passes(self):
        self.assertEqual(hooks.install(self.repo).state, hooks.INSTALLED)

        self._write(self.SECRET)
        blocked = self._git("commit", "-m", "secret")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("secret-gate", blocked.stderr)

        self._write("ok = True\n")
        clean = self._git("commit", "-m", "clean")
        self.assertEqual(clean.returncode, 0, clean.stderr)

    def test_a_secret_already_committed_blocks_the_push(self):
        self.assertEqual(hooks.install(self.repo).state, hooks.INSTALLED)

        self._write(self.SECRET)
        # `--no-verify` is the test's own way IN — standing in for a commit
        # made before the hook existed, or made elsewhere: what `push` is
        # proving is that the SECOND gate catches what the first one did not,
        # not that the first one can be talked around.
        self._git("commit", "--no-verify", "-m", "secret", check=True)
        blocked = self._git("push", "origin", "HEAD:main")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("secret-gate", blocked.stderr)

        self._write("ok = True\n")
        self._git("commit", "-m", "clean", check=True)
        pushed = self._git("push", "origin", "HEAD:main")
        self.assertEqual(pushed.returncode, 0, pushed.stderr)

    def test_the_tools_own_cache_never_lands_in_the_worktree(self):
        hooks.install(self.repo)
        self._write("ok = True\n")
        self._git("commit", "-m", "clean", check=True)
        self.assertFalse((self.repo / "App").exists())
        self.assertTrue((self.repo / ".git" / hooks.CACHE_NAME).is_dir())

    def test_an_ambient_working_folder_is_scanned_too(self):
        # "o produto e a instância, sempre" (`.claude/CLAUDE.md`): a Working
        # Folder the committer's OWN shell names is checked beside the
        # repository, without this module ever naming it by a fixed path.
        extra = self.root / "working_folder"
        self.env2 = mock.patch.dict(os.environ, {"AT_ROOT": str(extra), "AT_LANG": "pt_BR"})
        self.env2.start()
        self.addCleanup(self.env2.stop)
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()
        i18n.reset()

        self.assertEqual(hooks.install(self.repo).state, hooks.INSTALLED)
        (extra / "Arquivos" / "nota.md").write_text(self.SECRET, encoding="utf-8")

        self._write("ok = True\n")
        blocked = self._git("commit", "-m", "clean repo, dirty working folder")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("secret-gate", blocked.stderr)
        self.assertIn(str(extra), blocked.stderr)


if __name__ == "__main__":
    unittest.main()
