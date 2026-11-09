"""The Working Folder under versioning — the repository AT drives (item 30).

What this module proves, and the shape of the proof: the folder is born a git
repository, carrying the ignore AT generates; an action that changes the folder
ends in a version named by the ENGINE's own sentence, so `git log` reads like
the table's own story; a folder that already carries a repository of somebody
else's is not clobbered and not driven; and a machine without git is told so,
offered the two ways out, and goes on working.

**Nothing here needs a network, and nothing writes outside the scratch folder
each test makes.** The git that runs is the one on this machine, inside a
`TemporaryDirectory`, and the class that needs it says so and skips without it —
the OTHER class proves the whole orchestration with the tool absent, which is
the state a machine that does not have it is in.

**And it is versioning, never backup.** The words are the product's, so the
words are checked here: the item's done-condition is that no surface calls any
of it a backup, and a test is the only thing that notices when one starts to.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    audit,
    boot,
    migrations,
    paths,
    settings,
    tables,
    versioning,
)
from at.data import store
from at.prose import listing as prose
from at.ui import ask as door
from at.ui.cli import main
from at.ui.webapp import app as webapp

# The git of this machine, or `None`. Everything that runs it is skipped without
# it, and everything else runs either way.
GIT = shutil.which("git")

SKIP = "git is not on this machine"

# The switch itself: with `versioning.DISABLED` on, the repository is not born,
# nothing is committed and nothing is said. Everything that proves the active
# behaviour skips with this while the switch is off.
REASON = "automatic versioning is switched off (versioning.DISABLED)"

# The road the acts of this module come through: a person at the terminal, which
# is what the history being tested IS — the folder's story as its owner writes it.
# It is passed and not defaulted on purpose: `door.run`'s own default is the via
# `engine`, the road of what acts by itself, and a demand at or above the bar
# that comes through it WAITS as a job instead of running (§4, item 15) — which
# is a rule about the filter, and not the subject this module is about.
AS_A_PERSON = {"via": audit.CLI}


def words(block: str = "versioning") -> list[str]:
    """Every text of `block`, both languages — what a person can be told."""
    return [
        text
        for language in json.loads(
            (
                Path(i18n.__file__).parent / "blocks" / f"{block}.json"
            ).read_text(encoding="utf-8")
        ).values()
        for text in language.values()
    ]


class ScratchCase(unittest.TestCase):
    """A scratch Working Folder, and the module's two counters forgotten."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        versioning.reset()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        versioning.reset()
        self.scratch.cleanup()

    def born(self) -> None:
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def wrote(self) -> None:
        """One action through the door — a row, which is a write."""
        with redirect_stdout(io.StringIO()):
            door.run("task", "create", ["--set", "text=comprar pão"], **AS_A_PERSON)

    def chose(self, minutes: float) -> None:
        """The folder chooses its cadence (§4, item 30).

        Written through the core's door and not through the ACT: what this module
        measures is what the cadence DOES to the history, and the line an edit of
        a setting leaves is `test_settings`'s subject.
        """
        settings.save({**settings.load(), versioning.KEY: minutes})

    def every_write(self) -> None:
        """The cadence of one version per write — the choice, not the default.

        A test about the history being the table's story says which cadence it is
        talking about, because the folder that never chose is periodic and would
        carry those writes in one version instead of one each.
        """
        self.chose(versioning.EVERY_WRITE)

    def long_ago(self) -> None:
        """Make the last version look older than the interval this folder chose.

        The clock moves here and nowhere else: the cadence reads the commit's own
        stamp, and a test that proved the interval by waiting it out would sleep
        for ten minutes to prove a comparison.
        """
        stamp = mock.patch.object(
            versioning,
            "last_version",
            lambda: time.time() - (versioning.interval() + 1) * 60,
        )
        stamp.start()
        self.addCleanup(stamp.stop)

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, capture_output=True, text=True
        ).stdout

    def versions(self) -> list[str]:
        """The commit subjects, newest first — what `git log` reads like."""
        return self.git("log", "--pretty=%s").splitlines()


@unittest.skipIf(versioning.DISABLED, REASON)
@unittest.skipUnless(GIT, SKIP)
class TheRepository(ScratchCase):
    """The folder's own repository: born by AT, driven by AT."""

    def test_the_folder_is_born_under_versioning_and_says_so(self):
        out = io.StringIO()
        with redirect_stdout(out):
            boot.create_working_folder()
        self.assertEqual(versioning.state(), versioning.OWNED)
        self.assertTrue((self.root / ".git").is_dir())
        self.assertEqual(
            versioning.owner_mark(self.root).read_text(encoding="utf-8"), "AT\n"
        )
        self.assertIn(i18n.tr("versioning.born"), out.getvalue())

    def test_the_ignore_is_generated_and_leaves_out_only_what_is_derived(self):
        self.born()
        written = (self.root / ".gitignore").read_text(encoding="utf-8")
        self.assertEqual(written, versioning.ignore_text())
        for derived in ("App/services/", "*.tmp", "at-cli", "at-deploy"):
            self.assertIn(derived, written)
        # And NEVER what the person wrote: the folders and the settings they own
        # are the history's whole point (§4).
        for kept in ("Tabelas/", "Biblioteca/", "Projetos/", "settings.json", "App/i18n/"):
            self.assertNotIn(kept, written)

    def test_generated_dirs_is_the_one_list_the_ignore_and_the_scanner_share(self):
        found = versioning.generated_dirs()
        names = {where.name for where in found}
        self.assertEqual(names, {"services"})
        for where in found:
            self.assertTrue(where.is_relative_to(paths.working_folder()))

    def test_a_person_s_ignore_file_is_never_overwritten(self):
        # The folder is made WITHOUT a repository first, so the `.gitignore` that
        # is there when the repository arrives is somebody's edit (§3: a
        # migration never overwrites one).
        ancient = "# meu\n*.meu\n"
        (self.root / ".gitignore").write_text(ancient, encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            boot.create_working_folder()
        self.assertEqual(
            (self.root / ".gitignore").read_text(encoding="utf-8"), ancient
        )
        self.assertIn(i18n.tr("versioning.ignore.kept"), out.getvalue())

    def test_the_first_version_carries_the_whole_working_folder(self):
        self.born()
        self.assertEqual(len(self.versions()), 1)
        carried = self.git("ls-tree", "-r", "--name-only", "HEAD")
        for born_with in ("Tabelas/schema/task.json", "App/settings.json", "App/migrations"):
            self.assertIn(born_with, carried)

    def test_an_action_ends_in_a_version_named_by_the_engine_s_own_sentence(self):
        self.born()
        self.every_write()
        with redirect_stdout(io.StringIO()):
            _, answer, _, _, _ = door.run(
                "task", "create", ["--set", "text=comprar pão"], **AS_A_PERSON
            )
        # The very sentence the surface printed, and not a second wording of it:
        # `git log` reads like the table's own story (§4).
        self.assertEqual(self.versions()[0], answer)
        self.assertEqual(self.versions()[0], "TASK-1 criado.")

    def test_a_folder_that_asks_for_every_write_is_never_left_dirty(self):
        # The cadence of zero minutes is the version that is never late, and it
        # keeps the invariant the periodic default trades away: nothing waits.
        self.born()
        self.assertFalse(versioning.pending())
        self.every_write()
        self.wrote()
        self.assertFalse(versioning.pending())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_the_whole_history_is_the_table_s_story_in_order(self):
        self.born()
        self.every_write()
        for value in ("primeira", "segunda"):
            with redirect_stdout(io.StringIO()):
                door.run("task", "create", ["--set", f"text={value}"], **AS_A_PERSON)
        with redirect_stdout(io.StringIO()):
            door.run("task", "cancel", ["1", "--set", "reason=desisti"], **AS_A_PERSON)
        self.assertEqual(
            self.versions(),
            ["TASK-1 encerrado.", "TASK-2 criado.", "TASK-1 criado.",
             i18n.tr("versioning.commit.started")],
        )

    def test_a_listing_takes_no_version(self):
        self.born()
        self.wrote()
        before = self.versions()
        with redirect_stdout(io.StringIO()):
            door.run("task", "list", [])
            door.run("task", "view", ["1"])
        self.assertEqual(self.versions(), before)

    def test_a_refused_action_leaves_the_line_and_no_row(self):
        self.born()
        self.every_write()
        before = len(self.versions())
        # The engine coerces and requires BEFORE it writes, so the ROW is never
        # written and the table is untouched. What the refusal leaves is the
        # AUDIT line (§3, item 15) — a refusal is a line like an act — and the
        # version that carries it is named by the refusal itself, so the folder
        # is not left dirty by an act that was turned down.
        with self.assertRaises(tables.TableError):
            door.run("task", "create", ["--set", "nowhere=x"], **AS_A_PERSON)
        self.assertEqual(len(self.versions()), before + 1)
        self.assertEqual(
            self.versions()[0],
            i18n.tr("table.error.unknown_field", table="task", field="nowhere"),
        )
        self.assertEqual(
            [row["status"] for row in store.load("audit")], ["refused"]
        )
        self.assertFalse(versioning.pending())

    def test_a_file_of_the_person_s_ends_in_a_version_named_by_its_path(self):
        self.born()
        self.every_write()
        (prose.root() / "nota.md").write_text("olá\n", encoding="utf-8")
        status, _ = prose.write("nota.md", "olá, mundo\n", "")
        self.assertEqual(status, 200)
        self.assertEqual(self.versions()[0], "Biblioteca/nota.md escrito.")

    def test_a_write_whose_git_fails_does_not_bring_the_action_down(self):
        self.born()
        with mock.patch.object(versioning, "run", side_effect=OSError("boom")):
            self.wrote()
        self.assertEqual(len(store.load("task")), 1)


@unittest.skipIf(versioning.DISABLED, REASON)
@unittest.skipUnless(GIT, SKIP)
class TheCadence(ScratchCase):
    """The folder versioned from time to time, and never on every write.

    The default is PERIODIC (§4, item 30): a working session writes hundreds of
    times, and one version per keystroke is a metronome, not a history. The write
    itself looks at how long ago the last version was and only commits when the
    interval has passed — no job and no timer — and what waits between versions
    is carried by the next one, because a version is the whole folder.
    """

    def test_a_folder_that_never_chose_is_versioned_periodically(self):
        self.born()
        before = self.versions()
        self.wrote()
        # The birth is the only version there is: the interval has not gone by.
        # The row is on disk all the same — what waits is the HISTORY, and the
        # folder is more useful carrying a wait than wearing a version per edit.
        self.assertEqual(self.versions(), before)
        self.assertEqual(len(store.load("task")), 1)
        self.assertTrue(versioning.pending())
        self.assertFalse(versioning.stale())

    def test_the_next_write_after_the_interval_carries_everything_that_waited(self):
        self.born()
        self.wrote()
        self.long_ago()
        # The folder is behind, and this is what the `cli` and the page read
        # before the write that resolves it: AT's repository, writes the last
        # version does not carry, and the interval gone by.
        self.assertTrue(versioning.stale())
        self.assertEqual(versioning.phrase(), versioning.STALE)
        self.wrote()
        # ONE version for both rows, named by the write that took it, and the
        # folder is clean again: what waited was carried, and not lost.
        self.assertEqual(self.versions()[0], "TASK-2 criado.")
        self.assertEqual(len(store.load("task")), 2)
        self.assertFalse(versioning.pending())
        self.assertFalse(versioning.stale())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_a_clean_folder_is_never_behind(self):
        # The sentence is about writes the last version does not carry, and never
        # about age: a folder nothing was written to owes nothing, and warning
        # about the time it sat still would be a sentence with no subject.
        self.born()
        self.long_ago()
        self.assertIsNone(versioning.phrase())
        self.assertFalse(versioning.stale())

    def test_the_cli_says_the_folder_fell_behind(self):
        self.born()
        self.wrote()
        self.long_ago()
        out = io.StringIO()
        with redirect_stdout(out):
            main(["version"])
        self.assertIn(i18n.tr("versioning.stale"), out.getvalue())

    def test_the_page_is_handed_the_sentence_in_every_language(self):
        self.born()
        self.wrote()
        self.long_ago()
        handed = webapp.state_payload()["versioning"]
        self.assertEqual(sorted(handed), sorted(i18n.SUPPORTED))
        for language in i18n.SUPPORTED:
            self.assertEqual(
                handed[language], i18n.text("versioning.stale", language)
            )

    def test_the_page_of_a_folder_that_is_not_behind_is_handed_nothing(self):
        self.born()
        self.assertIsNone(webapp.state_payload()["versioning"])


@unittest.skipUnless(GIT, SKIP)
class TheFolderWithARepositoryOfItsOwn(ScratchCase):
    """A folder that already carries a repository is not clobbered — and not
    driven either: the history there is its owner's (§4)."""

    def setUp(self):
        super().setUp()
        subprocess.run(["git", "init", "--quiet"], cwd=self.root, check=True)

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_repository_of_somebody_else_is_left_alone(self):
        out = io.StringIO()
        with redirect_stdout(out):
            boot.create_working_folder()
        self.assertEqual(versioning.state(), versioning.FOREIGN)
        self.assertFalse(versioning.owner_mark(self.root).exists())
        self.assertEqual(self.versions(), [])
        self.assertIn(i18n.tr("versioning.foreign"), out.getvalue())

    def test_the_folder_goes_on_working_without_a_version_of_at_s(self):
        self.born()
        self.wrote()
        self.assertEqual(len(store.load("task")), 1)
        self.assertEqual(self.versions(), [])

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_page_is_handed_the_sentence_and_the_owner_is_handed_nothing(self):
        self.born()
        handed = webapp.state_payload()["versioning"]
        self.assertEqual(sorted(handed), sorted(i18n.SUPPORTED))
        self.assertEqual(handed["pt_BR"], i18n.tr("versioning.foreign"))

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_folder_of_somebody_else_is_never_told_it_fell_behind(self):
        # AT does not version in here at all, so the wait this item is about does
        # not exist: what the person hears is whose the repository is.
        self.born()
        self.wrote()
        self.long_ago()
        self.assertFalse(versioning.stale())
        self.assertEqual(versioning.phrase(), versioning.PHRASES[versioning.FOREIGN])

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_cli_says_it_on_every_run(self):
        self.born()
        out = io.StringIO()
        with redirect_stdout(out):
            main(["version"])
        self.assertIn(i18n.tr("versioning.foreign"), out.getvalue())


@unittest.skipIf(versioning.DISABLED, REASON)
class TheFolderThatPredatesVersioning(ScratchCase):
    """A folder that exists when versioning arrives catches up, as every
    structure change does: on the first start after the swap (§3)."""

    @unittest.skipUnless(GIT, SKIP)
    def test_the_repository_is_born_on_the_first_start_after_the_swap(self):
        # The folder is built, and the stamp is forged back to the state of a
        # folder that ran every migration EXCEPT this release's.
        self.born()
        self.assertEqual(versioning.state(), versioning.OWNED)

    @unittest.skipUnless(GIT, SKIP)
    def test_a_folder_that_never_heard_of_versioning_gains_it(self):
        self.born()
        shutil.rmtree(self.root / ".git")
        (migrations.stamp_file()).write_text(
            json.dumps([item.ident for item in migrations.MIGRATIONS if item.ident != 10])
        )
        self.assertEqual(versioning.state(), versioning.BARE)
        with redirect_stdout(io.StringIO()):
            boot.catch_up()
        self.assertEqual(versioning.state(), versioning.OWNED)
        self.assertIn(
            i18n.tr("versioning.commit.started"), self.versions()
        )


class WithoutTheTool(ScratchCase):
    """A machine without git: AT says so, offers the two ways out, and goes on.

    The tool is absent, and this is not a hole in the test — it is the state the
    product promises not to fall over (§7a's precedent, on the other tool). The
    whole orchestration is provable here, on a machine that has no git.
    """

    def setUp(self):
        super().setUp()
        self.absent = mock.patch.object(versioning, "present", lambda: False)
        self.absent.start()
        self.addCleanup(self.absent.stop)

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_folder_is_born_without_a_repository_and_works(self):
        out = io.StringIO()
        with redirect_stdout(out):
            boot.create_working_folder()
        self.assertEqual(versioning.state(), versioning.MISSING)
        self.assertFalse((self.root / ".git").exists())
        self.assertIn(i18n.tr("versioning.no_git.no_tty"), out.getvalue())

    def test_a_write_goes_through_without_the_tool(self):
        self.born()
        self.wrote()
        self.assertEqual(len(store.load("task")), 1)

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_cli_says_the_folder_is_not_under_versioning(self):
        self.born()
        out = io.StringIO()
        with redirect_stdout(out):
            main(["version"])
        self.assertIn(i18n.tr("versioning.missing"), out.getvalue())

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_folder_without_the_tool_is_never_told_it_fell_behind(self):
        # There is no repository to fall behind in, and the sentence this module
        # owes is the one about the tool that is not here.
        self.born()
        self.wrote()
        self.long_ago()
        self.assertFalse(versioning.stale())
        self.assertEqual(versioning.phrase(), versioning.PHRASES[versioning.MISSING])

    @unittest.skipIf(versioning.DISABLED, REASON)
    def test_the_page_is_handed_the_sentence(self):
        self.born()
        handed = webapp.state_payload()["versioning"]
        self.assertEqual(sorted(handed), sorted(i18n.SUPPORTED))
        # In EVERY language, like every word the page is handed: switching the
        # language on screen costs no request (§3).
        for language in i18n.SUPPORTED:
            self.assertEqual(
                handed[language], i18n.text("versioning.missing", language)
            )

    def test_installing_is_one_of_the_two_ways_out(self):
        out = io.StringIO()
        with redirect_stdout(out):
            answer = versioning.ways_out(lambda question: "s")
        self.assertEqual(answer, versioning.INSTALL)
        self.assertIn(i18n.tr("versioning.no_git.install"), out.getvalue())
        # AT does not install anything: it says how, and stops there.
        self.assertFalse((self.root / ".git").exists())

    def test_declining_keeps_the_folder_where_it_already_works(self):
        out = io.StringIO()
        with redirect_stdout(out):
            answer = versioning.ways_out(lambda question: "")
        self.assertEqual(answer, versioning.WITHOUT)
        self.assertIn(i18n.tr("versioning.no_git.without"), out.getvalue())

    def test_no_terminal_takes_neither_way_out(self):
        out = io.StringIO()
        with redirect_stdout(out):
            answer = versioning.ways_out(None)
        self.assertEqual(answer, versioning.NO_ANSWER)
        self.assertIn(i18n.tr("versioning.no_git.no_tty"), out.getvalue())

    @unittest.skipIf(versioning.DISABLED, REASON)
    @unittest.skipUnless(GIT, SKIP)
    def test_a_tool_that_arrives_later_gives_the_folder_its_history(self):
        self.born()
        with mock.patch.object(versioning, "present", lambda: True):
            with redirect_stdout(io.StringIO()):
                versioning.notice()
        self.assertEqual(versioning.state(), versioning.OWNED)
        self.assertTrue((self.root / ".git").is_dir())


class TheCadenceSetting(ScratchCase):
    """The key the cadence lives in, read ONCE and governing both halves (§4)."""

    def test_a_folder_that_never_chose_is_periodic(self):
        self.assertEqual(versioning.interval(), versioning.DEFAULT)
        self.assertGreater(versioning.DEFAULT, versioning.EVERY_WRITE)

    def test_zero_is_the_person_asking_for_every_write(self):
        self.chose(versioning.EVERY_WRITE)
        self.assertEqual(versioning.interval(), versioning.EVERY_WRITE)

    def test_a_value_that_is_not_a_cadence_is_read_as_the_default(self):
        # `risk.threshold`'s rule, on this key: a number AT cannot read is a
        # setting that was never made — never a refusal, and never a cadence that
        # either floods the history or quietly stops it.
        for strange in ("1h", None, True, -3, [10]):
            with self.subTest(value=strange):
                self.chose(strange)
                self.assertEqual(versioning.interval(), versioning.DEFAULT)


@unittest.skipUnless(versioning.DISABLED, "the switch is back on (DISABLED is False)")
class TheSwitch(ScratchCase):
    """With `DISABLED`, every public door is silent and no git runs.

    The mirror of the classes above: while automatic versioning is off, the
    folder is not born under versioning, nothing is committed, and nothing is
    said. The class skips itself the day the switch goes back to `False`, so it
    never has to be deleted.
    """

    def test_no_door_reaches_git_or_writes_anything(self):
        with mock.patch.object(
            versioning, "run", side_effect=AssertionError("git was called")
        ):
            self.assertFalse(versioning.commit("qualquer coisa"))
            self.assertEqual(versioning.ensure(), versioning.state())
            self.assertEqual(versioning.start(), versioning.state())
            self.assertIsNone(versioning.phrase())
            self.assertFalse(versioning.stale())
            self.assertFalse(versioning.dirty())
        self.assertFalse((self.root / ".git").exists())
        self.assertFalse((self.root / ".gitignore").exists())

    def test_the_folder_is_not_born_under_versioning_and_says_nothing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            boot.create_working_folder()
        self.assertFalse((self.root / ".git").exists())
        self.assertFalse((self.root / ".gitignore").exists())
        self.assertEqual(out.getvalue(), "")

    def test_the_run_says_nothing_about_versioning(self):
        out = io.StringIO()
        with redirect_stdout(out):
            versioning.notice()
        self.assertEqual(out.getvalue(), "")


class TheWords(ScratchCase):
    """The item's other half is a promise about WORDS, and words are checked."""

    def test_no_surface_calls_any_of_it_a_backup(self):
        # Item 30, done-condition: "no surface and no document calls any of it a
        # backup". Versioning and backup are different things, and the word is
        # the whole of the difference until the other thing exists.
        for text in words():
            for forbidden in ("backup", "cópia de segurança"):
                self.assertNotIn(forbidden, text.lower())

    def test_the_two_languages_are_in_step(self):
        self.assertEqual(i18n.keys_out_of_step(), {})

    def test_a_folder_under_versioning_has_nothing_to_say(self):
        # `bare` is the one state with no sentence: a folder with no repository
        # on a machine that has git is a folder about to have one, and warning
        # about it would be warning about the next half-second.
        self.assertIsNone(versioning.PHRASES.get(versioning.BARE))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
