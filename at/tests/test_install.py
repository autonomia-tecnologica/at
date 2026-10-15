"""`install` — the artifact put where commands are found (§3, item 28).

The install writes OUTSIDE the Working Folder, and that is exactly why this
suite proves what it WOULD do and never installs on the machine running the
suite: the directory it writes into is a scratch one, the home it writes the
completion into is a scratch one, and the PATH it reads is a scratch one. The
real `~/.local/bin` is never named — the same seam the Podman and the git get,
one file over.

What is under test here is the install and not the first run, so the folder is
born by hand — `App/settings.json` and a stand-in `at-cli` — instead of by
`boot`: that keeps the case where the folder is NOT AT's yet a case a test can
set up deliberately, which is one of the ones this item had to decide.

No test here needs a network, and none writes outside `self.scratch`.
"""

from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import files, install, paths
from at.i18n import text
from at.ui.cli import USAGE, main, tree
from at_deploy import cli as deploy_cli
from at_deploy import tree as deploy_tree


class Scratch(unittest.TestCase):
    """A folder, a bin directory and a home — all of them temporary."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        base = Path(self.scratch.name)
        self.root = base / "folder"
        self.bin = base / "bin"
        self.home = base / "home"
        for directory in (self.root, self.bin, self.home):
            directory.mkdir()
        (self.root / "at-cli").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / "at-deploy").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.root / "App").mkdir()
        (self.root / "App" / "settings.json").write_text("{}\n", encoding="utf-8")

        # The PATH is the scratch directory and nothing else: whether another
        # command of the same name answers is a thing a test sets up ON PURPOSE,
        # and inheriting the machine's own PATH would make that a property of
        # whoever is running the suite.
        self.environ = mock.patch.dict(os.environ, {
            "AT_ROOT": str(self.root),
            "HOME": str(self.home),
            "AT_LANG": "pt_BR",
            "PATH": str(self.bin),
        })
        self.environ.start()
        i18n.reset()
        files.reset_writes()

    def tearDown(self):
        self.environ.stop()
        i18n.reset()
        self.scratch.cleanup()

    # --- the doors the tests walk through ---------------------------------

    def act(self, rest: tuple[str, ...] = (), shell: str = "bash") -> tuple[str, str]:
        """`at-cli install` as the `cli` runs it, in a terminal that is not one."""
        return self.walk(main, ("install", *rest), shell)

    def undo(self, rest: tuple[str, ...] = (), shell: str = "bash") -> tuple[int, str]:
        return self.walk(main, ("uninstall", *rest), shell)

    def deploy(self, word: str, rest: tuple[str, ...] = (),
               shell: str = "bash") -> tuple[int, str]:
        return self.walk(deploy_cli.main, (word, *rest), shell)

    def walk(self, door, words: tuple[str, ...], shell: str) -> tuple[int, str]:
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"SHELL": f"/usr/bin/{shell}" if shell else ""}):
            with redirect_stdout(output):
                code = door(list(words))
        return code, output.getvalue()

    def act_directly(self, rest: tuple[str, ...] = (),
                     shell: str = "bash", platform: str | None = None,
                     artifact: str | None = None) -> tuple[str, str]:
        """The core door, for the cases the `cli` cannot express — and the one
        a test reaches for whenever the platform is not the real one: `cli`
        never passes `platform`, so a Windows case has to call `act` itself."""
        flag = rest[1] if rest[:1] == ("--bin",) else None
        output = io.StringIO()
        with redirect_stdout(output):
            outcome = install.act(paths.ARTIFACT, artifact or paths.artifact_file(),
                                  tree.completion(), bin_flag=flag, shell=shell,
                                  platform=platform)
        return outcome, output.getvalue()

    def undo_directly(self, rest: tuple[str, ...] = (),
                      shell: str = "bash", platform: str | None = None,
                      artifact: str | None = None) -> tuple[str, str]:
        """`undo`'s own version of `act_directly`, for the same reason."""
        flag = rest[1] if rest[:1] == ("--bin",) else None
        output = io.StringIO()
        with redirect_stdout(output):
            outcome = install.undo(paths.ARTIFACT, artifact or paths.artifact_file(),
                                   bin_flag=flag, shell=shell, platform=platform)
        return outcome, output.getvalue()

    def link(self, word: str = "at-cli") -> Path:
        return self.bin / word

    def record(self) -> dict:
        return json.loads((self.root / "App" / "install.json").read_text(encoding="utf-8"))

    def completion(self, word: str = "at-cli", shell: str = "bash") -> Path:
        where = install.completion_path(word, shell)
        assert where is not None
        return where


class TheLink(Scratch):
    """What the word creates: a link to the artifact, and nothing else."""

    def test_the_link_points_at_the_artifact_in_the_folder(self):
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertEqual(self.link().resolve(), (self.root / "at-cli").resolve())
        self.assertIn(str(self.root / "at-cli"), text_)

    def test_nothing_is_copied_out_of_the_folder(self):
        # The whole of item 28's "what the install is NOT": what leaves the
        # folder is a link, and a link is not state.
        self.act(("--bin", str(self.bin)), shell="")
        wrote = sorted(path.name for path in self.bin.iterdir())
        self.assertEqual(wrote, ["at-cli"])

    def test_the_default_is_the_xdg_directory_under_the_home(self):
        self.assertEqual(install.where("at-cli"), self.home / ".local" / "bin")

    def test_a_directory_chosen_once_stays_chosen(self):
        # The one thing the install REMEMBERS, and the reason it remembers it:
        # without the record the second install would go to the default and the
        # person would end up with two links and no way to tell which answers.
        chosen = Path(self.scratch.name) / "somewhere"
        chosen.mkdir()
        self.act(("--bin", str(chosen)))
        code, _ = self.act()
        self.assertEqual(code, 0)
        self.assertTrue((chosen / "at-cli").is_symlink())
        self.assertFalse((self.home / ".local" / "bin" / "at-cli").exists())

    def test_installing_twice_leaves_one_link(self):
        self.act(("--bin", str(self.bin)))
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertEqual(sorted(path.name for path in self.bin.iterdir()), ["at-cli"])
        self.assertIn(i18n.tr("install.already", word="at-cli",
                              link=self.link(), target=self.root / "at-cli"), text_)

    def test_an_update_is_the_file_replaced_and_the_link_following_it(self):
        # §3's own sentence about updating, read through the install: the new
        # release replaces the binary IN THE FOLDER, the link follows it, and
        # there is no second file left standing — which is the whole reason the
        # install is a link and not a copy.
        self.act(("--bin", str(self.bin)))
        was = self.link().resolve()
        (self.root / "at-cli").write_text("#!/bin/sh\n# the new build\n", encoding="utf-8")

        self.assertEqual(self.link().resolve(), was)
        self.assertEqual(self.link().resolve().read_text(encoding="utf-8"),
                         "#!/bin/sh\n# the new build\n")
        self.assertEqual(sorted(path.name for path in self.bin.iterdir()), ["at-cli"])

    def test_a_folder_with_no_artifact_is_refused_and_writes_nothing(self):
        (self.root / "at-cli").unlink()
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 1)
        self.assertIn("at-cli", text_)
        self.assertFalse(self.link().exists())
        self.assertFalse((self.root / "App" / "install.json").exists())

    def test_read_only_refuses_the_link_and_the_record(self):
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                self.act_directly(("--bin", str(self.bin)))
        self.assertFalse(self.link().exists())
        self.assertFalse((self.root / "App" / "install.json").exists())


class TheObstacle(Scratch):
    """In a collision, the person's edit rules (§3) — and the install says so."""

    def test_a_file_that_is_not_ats_is_not_overwritten(self):
        self.link().write_text("the person's own script\n", encoding="utf-8")
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 1)
        self.assertEqual(self.link().read_text(encoding="utf-8"),
                         "the person's own script\n")
        self.assertIn(str(self.link()), text_)
        self.assertFalse((self.root / "App" / "install.json").exists())

    def test_a_link_aimed_somewhere_else_is_not_overwritten(self):
        elsewhere = Path(self.scratch.name) / "elsewhere"
        elsewhere.write_text("", encoding="utf-8")
        self.link().symlink_to(elsewhere)
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 1)
        self.assertEqual(self.link().readlink(), elsewhere)
        self.assertIn(str(elsewhere), text_)

    def test_a_link_of_ats_whose_target_was_deleted_is_repointed(self):
        # The folder moved and the binary went with it. Nobody can RUN through
        # the link — the system refuses to start a process through a link that
        # points at nothing — so the door that speaks about it is this one, run
        # from the artifact that exists, and what it reads is the NAME the link
        # points at: only AT writes a link named after its own artifact.
        self.link().symlink_to(self.root / "at-cli")
        (self.root / "at-cli").unlink()
        (self.root / "at-cli").write_text("#!/bin/sh\n", encoding="utf-8")

        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertEqual(self.link().resolve(), (self.root / "at-cli").resolve())
        self.assertNotIn(i18n.tr("install.held.file", link=self.link()), text_)


class TheName(Scratch):
    """The name is `at-cli` so that `at` stays the machine's (§3, item 28).

    What the rename settles is the NAME and not the DIRECTORY: a link can still
    land where another command of its own name already answers — a file of the
    person's, or a tool that arrives later — and what the install does there is
    write the link and say which of the two the `PATH` makes win.
    """

    def test_the_link_is_still_written_when_the_directory_is_off_the_path(self):
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin"}):
            code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertIn(i18n.tr("install.off_path", bin=self.bin, word="at-cli"), text_)

    def test_a_command_of_the_same_name_earlier_on_the_path_wins(self):
        earlier = Path(self.scratch.name) / "earlier"
        earlier.mkdir()
        other = earlier / "at-cli"
        other.write_text("#!/bin/sh\n", encoding="utf-8")
        other.chmod(other.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"PATH": f"{earlier}{os.pathsep}{self.bin}"}):
            code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertIn(i18n.tr("install.collision.shadowed", word="at-cli",
                              other=other, bin=self.bin), text_)

    def test_a_command_of_the_same_name_later_on_the_path_is_shadowed(self):
        later = Path(self.scratch.name) / "later"
        later.mkdir()
        other = later / "at-cli"
        other.write_text("#!/bin/sh\n", encoding="utf-8")
        other.chmod(other.stat().st_mode | stat.S_IXUSR)
        with mock.patch.dict(os.environ, {"PATH": f"{self.bin}{os.pathsep}{later}"}):
            code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertIn(i18n.tr("install.collision.shadowing", word="at-cli",
                              other=other, bin=self.bin), text_)

    def test_ats_own_link_is_not_a_collision(self):
        # What is on the PATH under that name is the link the last install put
        # there, and re-installing over it is not a name clash — it is the
        # common case, and a product that cried collision here would cry it
        # every time anybody updated.
        self.act(("--bin", str(self.bin)))
        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertNotIn(i18n.tr("install.off_path", bin=self.bin, word="at-cli"), text_)
        self.assertNotIn("collision", text_)


class TheRecord(Scratch):
    """Where the installation is remembered, and what happens with no folder."""

    def test_the_record_lands_in_app(self):
        self.act(("--bin", str(self.bin)))
        remembered = self.record()
        self.assertEqual(remembered["at-cli"]["bin"], str(self.bin))
        self.assertIn(str(self.link()), remembered["at-cli"]["wrote"])
        self.assertIn(str(self.completion()), remembered["at-cli"]["wrote"])

    def test_a_folder_that_is_not_ats_yet_is_told_and_records_nothing(self):
        # The install reads the folder from where the ARTIFACT is, and a folder
        # that is not AT's has nowhere of AT's to keep the record. Creating
        # `App/` here would be creating a Working Folder through the back door,
        # which is the one thing `boot` asks before (§3).
        (self.root / "App" / "settings.json").unlink()
        (self.root / "App").rmdir()

        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertIn(i18n.tr("install.no_folder",
                              settings=paths.settings_file(), bin=self.bin), text_)
        self.assertFalse((self.root / "App").exists())

    def test_a_corrupt_record_falls_back_to_the_default(self):
        (self.root / "App" / "install.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(install.where("at-cli"), self.home / ".local" / "bin")


class TheCompletion(Scratch):
    """The words reachable without a path, generated from the one declaration."""

    def test_the_bash_completion_carries_the_words_of_the_tree(self):
        self.act(("--bin", str(self.bin)))
        script = self.completion().read_text(encoding="utf-8")
        for name, _ in tree.completion():
            with self.subTest(word=name):
                self.assertIn(name, script)
        self.assertIn("complete -F", script)
        self.assertIn(" at", script)

    def test_the_zsh_completion_is_a_compdef_file(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        script = self.completion(shell="zsh").read_text(encoding="utf-8")
        # The word comes from the declaration and not from a literal here: the
        # completion has to name whatever command the install writes, and
        # `test_names` is where that name is held.
        self.assertTrue(script.startswith(f"#compdef {paths.ARTIFACT}\n"))
        self.assertIn("_describe", script)

    def test_the_zsh_file_says_the_fpath_line_nobody_can_guess(self):
        # AT writes the file where zsh CAN read it and does not edit the shell
        # configuration that would make it read it: that file is the person's,
        # and a product that edited it would owe finding and undoing its own
        # edit later. So the line is printed, once, where a person will see it.
        code, text_ = self.act(("--bin", str(self.bin)), shell="zsh")
        self.assertEqual(code, 0)
        self.assertIn("fpath=(", text_)
        self.assertIn(str(self.completion(shell="zsh").parent), text_)

    def test_a_shell_the_product_does_not_know_writes_no_completion(self):
        code, text_ = self.act(("--bin", str(self.bin)), shell="fish")
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertIn(i18n.tr("install.completion.unknown", shell="fish"), text_)

    def test_with_no_shell_at_all_it_says_so_and_installs_the_link_anyway(self):
        code, text_ = self.act(("--bin", str(self.bin)), shell="")
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertIn(i18n.tr("install.completion.no_shell"), text_)

    def test_the_completion_is_the_trees_and_not_a_second_list(self):
        # The one declaration, read twice: a word arriving in the tree arrives
        # in the completion with it, and a word leaving leaves both.
        script = install.completion_text("at-cli", (("nowhere", ("in", "it")),), "bash")
        self.assertIn("nowhere", script)
        self.assertIn("in it", script)
        self.assertNotIn("webapp", script)


class TheFpathReminder(Scratch):
    """`version` repeats the zsh line while `$FPATH` does not carry it yet."""

    def version(self, fpath: str | None = None) -> tuple[int, str]:
        env = {"FPATH": fpath} if fpath is not None else {}
        output = io.StringIO()
        with mock.patch.dict(os.environ, env):
            if fpath is None:
                os.environ.pop("FPATH", None)
            with redirect_stdout(output):
                code = main(["version"])
        return code, output.getvalue()

    def test_no_completion_at_all_is_nothing_to_remind(self):
        self.assertIsNone(install.fpath_needed(paths.ARTIFACT))

    def test_a_bash_completion_is_nothing_to_remind_either(self):
        # bash-completion needs no line in a configuration file: the reminder
        # is zsh's own problem, because zsh is the shell that reads `fpath`.
        self.act(("--bin", str(self.bin)), shell="bash")
        self.assertIsNone(install.fpath_needed(paths.ARTIFACT))

    def test_a_freshly_written_zsh_completion_needs_the_reminder(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        self.assertEqual(
            install.fpath_needed(paths.ARTIFACT), self.completion(shell="zsh").parent
        )

    def test_a_directory_already_on_the_inherited_fpath_is_not_reminded(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        directory = self.completion(shell="zsh").parent
        with mock.patch.dict(os.environ, {"FPATH": str(directory)}):
            self.assertIsNone(install.fpath_needed(paths.ARTIFACT))

    def test_a_different_directory_on_fpath_still_needs_the_reminder(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        with mock.patch.dict(os.environ, {"FPATH": str(self.bin)}):
            self.assertIsNotNone(install.fpath_needed(paths.ARTIFACT))

    def test_version_says_nothing_with_no_completion_installed(self):
        code, text_ = self.version()
        self.assertEqual(code, 0)
        self.assertNotIn("fpath=(", text_)

    def test_version_repeats_the_line_while_fpath_does_not_carry_it(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        code, text_ = self.version()
        self.assertEqual(code, 0)
        self.assertIn("fpath=(", text_)
        self.assertIn(str(self.completion(shell="zsh").parent), text_)

    def test_version_stops_once_the_inherited_fpath_carries_it(self):
        self.act(("--bin", str(self.bin)), shell="zsh")
        directory = self.completion(shell="zsh").parent
        code, text_ = self.version(fpath=str(directory))
        self.assertEqual(code, 0)
        self.assertNotIn("fpath=(", text_)


class TheUndo(Scratch):
    """`uninstall` takes back what AT put there, and only that."""

    def test_it_takes_back_the_link_and_the_completion(self):
        self.act(("--bin", str(self.bin)))
        code, text_ = self.undo(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertFalse(self.link().is_symlink())
        self.assertFalse(self.completion().exists())
        self.assertIn(str(self.link()), text_)
        self.assertFalse((self.root / "App" / "install.json").exists())

    def test_a_file_that_is_not_ats_is_kept_and_said(self):
        self.link().write_text("the person's own script\n", encoding="utf-8")
        code, text_ = self.undo(("--bin", str(self.bin)))
        self.assertEqual(code, 1)
        self.assertEqual(self.link().read_text(encoding="utf-8"),
                         "the person's own script\n")
        self.assertIn(str(self.link()), text_)

    def test_nothing_installed_is_not_a_failure(self):
        code, text_ = self.undo(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertIn(i18n.tr("install.uninstall.nothing", word="at-cli", bin=self.bin), text_)

    def test_read_only_refuses_the_undo_too(self):
        self.act(("--bin", str(self.bin)))
        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                install.undo(paths.ARTIFACT, paths.artifact_file(), bin_flag=str(self.bin))
        self.assertTrue(self.link().is_symlink())


class TheWindowsShim(Scratch):
    """The word on Windows: a `.cmd` shim instead of a symlink.

    The platform is INJECTED — never read off the real `sys.platform` — so
    this class proves what `install` would do on Windows without needing a
    Windows machine, and without the answer depending on the one running the
    suite. Linux and macOS do not change a line (Ressalvas): every other test
    in this file still runs the symlink the way it always has.
    """

    WIN = "win32"

    def setUp(self):
        super().setUp()
        self.exe = self.root / "at-cli.exe"
        self.exe.write_text("", encoding="utf-8")

    def shim(self) -> Path:
        return self.bin / "at-cli.cmd"

    def install(self, bin_flag: Path | None = None) -> tuple[str, str]:
        return self.act_directly(("--bin", str(bin_flag or self.bin)),
                                 platform=self.WIN, artifact="at-cli.exe")

    def uninstall(self, bin_flag: Path | None = None) -> tuple[str, str]:
        return self.undo_directly(("--bin", str(bin_flag or self.bin)),
                                  platform=self.WIN, artifact="at-cli.exe")

    def test_install_writes_a_cmd_shim_forwarding_to_the_artifact(self):
        outcome, text_ = self.install()
        self.assertEqual(outcome, install.DONE)
        self.assertTrue(self.shim().is_file())
        self.assertFalse(self.shim().is_symlink())
        self.assertFalse((self.bin / "at-cli").exists())
        content = self.shim().read_text(encoding="utf-8")
        self.assertIn(f'"{self.exe}"', content)
        self.assertIn("%*", content)
        self.assertIn(str(self.exe), text_)

    def test_the_shim_quotes_a_path_with_a_space(self):
        spaced = Path(self.scratch.name) / "com espaço"
        spaced.mkdir()
        (spaced / "at-cli.exe").write_text("", encoding="utf-8")
        with mock.patch.dict(os.environ, {"AT_ROOT": str(spaced)}):
            outcome, _ = self.act_directly(("--bin", str(self.bin)),
                                           platform=self.WIN, artifact="at-cli.exe")
        self.assertEqual(outcome, install.DONE)
        content = self.shim().read_text(encoding="utf-8")
        self.assertIn(f'"{spaced / "at-cli.exe"}"', content)

    def test_running_it_again_recognizes_its_own_shim_and_updates(self):
        self.install()
        outcome, text_ = self.install()
        self.assertEqual(outcome, install.DONE)
        self.assertEqual(sorted(path.name for path in self.bin.iterdir()), ["at-cli.cmd"])
        self.assertIn(i18n.tr("install.already", word="at-cli",
                              link=self.shim(), target=self.exe), text_)

    def test_a_file_that_is_not_ats_is_not_overwritten(self):
        self.shim().write_text("the person's own script\n", encoding="utf-8")
        outcome, text_ = self.install()
        self.assertEqual(outcome, install.HELD)
        self.assertEqual(self.shim().read_text(encoding="utf-8"),
                         "the person's own script\n")
        self.assertIn(str(self.shim()), text_)

    def test_uninstall_removes_the_shim_it_wrote(self):
        self.install()
        outcome, text_ = self.uninstall()
        self.assertEqual(outcome, install.REMOVED)
        self.assertFalse(self.shim().exists())
        self.assertIn(str(self.shim()), text_)

    def test_uninstall_keeps_a_file_that_is_not_ats(self):
        self.shim().write_text("the person's own script\n", encoding="utf-8")
        outcome, text_ = self.uninstall()
        self.assertEqual(outcome, install.HELD)
        self.assertTrue(self.shim().exists())


class TheRule(unittest.TestCase):
    """§3 carries the decision, and it carries it in both languages.

    The item's own "done when": the record's home is decided in §3. A decision
    nothing points at is one the next release is free to undo without noticing,
    so the gate reads the pair of documents instead of trusting that somebody
    remembers. What it reads for is the three things that would not survive
    being re-decided in silence: the two words, the directory the record lives
    in, and the way back.
    """

    HEADING = {"pt_BR": "### Código e delivery", "en_US": "### Code and delivery"}

    def test_the_delivery_section_of_both_languages_carries_the_install(self):
        root = Path(__file__).resolve().parents[2]
        for language in i18n.SUPPORTED:
            with self.subTest(language=language):
                document = (root / "docs" / language / "rules.md").read_text(encoding="utf-8")
                start = document.index(self.HEADING[language])
                section = document[start:]
                end = section.find("\n### ", 1)
                section = section if end < 0 else section[:end]

                for marker in ("`at-cli install`", "`at-deploy install`",
                               "`App/install.json`", "`uninstall`"):
                    with self.subTest(marker=marker):
                        self.assertIn(
                            marker, section,
                            f"{language}/rules.md: §3 no longer carries {marker}; the "
                            f"install is a rule of delivery and it is decided there",
                        )


class TheDoor(Scratch):
    """The word in the `cli`: offered, dispatched, and where it runs."""

    def test_the_help_offers_both_words(self):
        code, text_ = self.walk(main, ("help",), "bash")
        self.assertEqual(code, 0)
        self.assertIn("install", text_)
        self.assertIn("uninstall", text_)

    def test_install_runs_before_a_working_folder_is_confirmed(self):
        # The pair is the exception §5 keeps: every other word is about the
        # folder, and these two are about the file. So they run with no
        # `settings.json` and create none — the folder is not theirs to make.
        (self.root / "App" / "settings.json").unlink()
        (self.root / "App").rmdir()

        code, text_ = self.act(("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        self.assertTrue(self.link().is_symlink())
        self.assertFalse((self.root / "App").exists())
        # And not one word of the first run was printed, which is what makes it
        # the exception instead of a second road to the same place.
        self.assertNotIn(i18n.tr("boot.first_run.notice", folder=self.root), text_)

    def test_a_flag_the_word_does_not_take_is_a_usage_error(self):
        for rest in (("--bin",), ("--bin", str(self.bin), "extra"), ("--casa",)):
            with self.subTest(rest=rest):
                code, _ = self.act(rest)
                self.assertEqual(code, USAGE)
                self.assertFalse(self.link().exists())

    def test_the_deploy_installs_its_own_file(self):
        code, text_ = self.deploy("install", ("--bin", str(self.bin)))
        self.assertEqual(code, 0)
        deploy = self.bin / "at-deploy"
        self.assertTrue(deploy.is_symlink())
        self.assertEqual(deploy.resolve(), (self.root / "at-deploy").resolve())
        self.assertIn("at-deploy", text_)

    def test_neither_artifact_installs_the_other(self):
        # §3's cut read from the install: whoever stays on the hosted path never
        # needs the deploy, so `at-cli install` does not reach for it.
        self.deploy("install", ("--bin", str(self.bin)))
        self.assertFalse((self.bin / "at-cli").exists())
        self.assertEqual(list(self.record()), ["at-deploy"])

        self.act(("--bin", str(self.bin)))
        self.assertEqual(sorted(self.record()), ["at-cli", "at-deploy"])
        self.assertTrue((self.bin / "at-cli").is_symlink())
        self.assertTrue((self.bin / "at-deploy").is_symlink())

    def test_the_deploys_help_offers_both_words_in_both_languages(self):
        for code in i18n.SUPPORTED:
            for node in deploy_tree.roots():
                with self.subTest(key=node.about, language=code):
                    self.assertNotEqual(text(node.about, code), node.about)


if __name__ == "__main__":
    unittest.main()
