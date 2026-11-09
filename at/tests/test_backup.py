"""The copy that survives the machine — ciphered, gated, and never versioning
(item 51, TASK-119).

**The scan is the gate, faked and never the real tool.** `core.scanner` has its
own suite; what this one proves is that `core.backup` reads the scanner's
ANSWER and nothing else — `scanner.scan` is replaced here the way
`test_scanner.py` replaces `gitleaks` itself, so these tests run with no
network, no model and no real `gitleaks` process.

**The Main Key is a callable, and it is read lazily.** `make` and
`restore` take a zero-argument reader instead of a plain string, so a test can
prove the phrase is never asked for when a cheaper check already refused —
a destination with no tool to reach it, or a folder `restore` will not touch.

**A round trip needs TWO folders, and switching is the whole of `switch`.**
Nothing in `at.core` caches a Working Folder path (`paths.working_folder` reads
`$AT_ROOT` fresh on every call), but `i18n`, `schema` and `versioning` do keep
state of their own — `switch` forgets all three, the same door every test that
moves between folders already uses.
"""

from __future__ import annotations

import io
import os
import shutil
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import (
    actors,
    audit,
    backup,
    boot,
    clock,
    files,
    jobs,
    notifier,
    paths,
    scanner,
    secrets,
    settings,
    strongbox,
    tables,
    versioning,
)
from at.data import schema, store
from at.encryption import vault
from at.i18n import tr
from at.ui import ask as door
from at.ui.cli import OK, REFUSED, USAGE, _backup, main
from at.ui.webapp import app as webapp
from at.ui.webapp import clock as webapp_clock
from at.ui.webapp import keys as webapp_keys
from at.ui.webapp import launch as webapp_launch

PHRASE = "uma-frase-de-dezesseis"
OTHER_PHRASE = "outra-frase-tambem-longa"
SHORT = "curta"


def _clean() -> scanner.Report:
    return scanner.Report(scanner.CLEAN, "gitleaks 8.30.1 (teste)")


def _found() -> scanner.Report:
    return scanner.Report(
        scanner.FOUND,
        "gitleaks 8.30.1 (teste)",
        (scanner.Finding("generic-api-key", "Arquivos/nota.md", 1),),
    )


class BackupCase(unittest.TestCase):
    """A booted scratch Working Folder, with the scan faked CLEAN by default."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self._enter(self.root)
        self.scan = mock.patch.object(backup.scanner, "scan", return_value=_clean())
        self.scan.start()

    def tearDown(self):
        self.scan.stop()
        self._leave()
        self.scratch.cleanup()

    def _enter(self, root: Path) -> None:
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(root), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        versioning.reset()
        files.reset_writes()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def _leave(self) -> None:
        self.env.stop()
        i18n.reset()
        schema.reset()
        versioning.reset()
        files.reset_writes()

    def switch(self, root: Path) -> None:
        """Move the whole environment to another (freshly booted) folder."""
        self._leave()
        self._enter(root)

    def elsewhere(self) -> Path:
        """A scratch directory this test owns, outside the Working Folder."""
        where = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, where, ignore_errors=True)
        return where

    def made(self, root: Path | None = None) -> Path:
        """A real, sealed backup of the CURRENT folder — the source `restore`
        reads in the tests that need one already made."""
        destination = self.elsewhere()
        report = backup.make(lambda: PHRASE, str(destination))
        self.assertEqual(report.state, backup.MADE)
        [sealed] = list(destination.iterdir())
        return sealed


class TheDestinationShape(unittest.TestCase):
    """The three shapes a destination takes, told apart by syntax alone."""

    def test_a_plain_path_is_local(self):
        self.assertEqual(backup._kind("/tmp/algum/caminho"), backup.LOCAL)

    def test_a_relative_path_is_local(self):
        self.assertEqual(backup._kind("pasta/arquivo.enc"), backup.LOCAL)

    def test_a_named_remote_is_rclone(self):
        self.assertEqual(backup._kind("meuremoto:pasta/arquivo"), backup.RCLONE)

    def test_a_user_at_host_is_ssh(self):
        self.assertEqual(backup._kind("pessoa@maquina:/tmp/destino"), backup.SSH)


class TheMake(BackupCase):
    def test_a_clean_folder_is_ciphered_and_sent_to_a_local_path(self):
        tables.create("task", {"text": "comprar pão"})
        destination = self.elsewhere()

        report = backup.make(lambda: PHRASE, str(destination))

        self.assertEqual(report.state, backup.MADE)
        [sealed] = list(destination.iterdir())
        self.assertTrue(sealed.name.endswith(backup.SUFFIX))

        key = secrets.key_of(backup.SCOPE, PHRASE)
        opened = vault.unseal_bytes(sealed.read_bytes(), key)
        self.assertIsNotNone(opened)
        with tempfile.TemporaryDirectory() as hold:
            archive = Path(hold) / "a.tar.gz"
            archive.write_bytes(opened)
            with tarfile.open(archive, "r:gz") as tar:
                names = tar.getnames()
        rel = paths.data_dir().relative_to(paths.working_folder()).as_posix()
        self.assertIn(f"./{rel}/tasks.jsonl", names)

    def test_a_dirty_scan_blocks_the_copy_and_sends_nothing(self):
        self.scan.stop()
        with mock.patch.object(backup.scanner, "scan", return_value=_found()):
            report = backup.make(lambda: PHRASE, str(self.elsewhere()))
        self.assertEqual(report.state, backup.BLOCKED)

    def test_a_scan_that_cannot_answer_blocks_too(self):
        self.scan.stop()
        unclear = scanner.Report(scanner.NO_TOOL, "gitleaks")
        with mock.patch.object(backup.scanner, "scan", return_value=unclear):
            report = backup.make(lambda: PHRASE, str(self.elsewhere()))
        self.assertEqual(report.state, backup.BLOCKED)

    def test_a_missing_tool_is_refused_before_the_phrase_is_asked(self):
        def boom() -> str:
            raise AssertionError("the phrase should not be read")

        with mock.patch("shutil.which", return_value=None):
            report = backup.make(boom, "algumremoto:pasta")
        self.assertEqual(report.state, backup.NO_TOOL)
        self.assertEqual(report.tool, "rclone")

    def test_the_phrase_is_read_lazily_and_only_once(self):
        calls: list[str] = []

        def give() -> str:
            calls.append(PHRASE)
            return PHRASE

        backup.make(give, str(self.elsewhere()))
        self.assertEqual(len(calls), 1)

    def test_a_phrase_under_the_floor_is_refused_and_sends_nothing(self):
        destination = self.elsewhere()
        with self.assertRaises(secrets.SecretsError):
            backup.make(lambda: SHORT, str(destination))
        self.assertEqual(list(destination.iterdir()), [])

    def test_an_rclone_remote_is_reached_through_the_tool_found(self):
        calls: list[list[str]] = []

        def fake_run(args, **kw):
            calls.append(args)
            return mock.Mock(returncode=0)

        with mock.patch("shutil.which", return_value="/usr/bin/rclone"), \
                mock.patch("subprocess.run", side_effect=fake_run):
            report = backup.make(lambda: PHRASE, "meuremoto:pasta/backup")
        self.assertEqual(report.state, backup.MADE)
        [call] = calls
        self.assertEqual(call[:2], ["/usr/bin/rclone", "copyto"])
        self.assertEqual(call[3], "meuremoto:pasta/backup")

    def test_an_ssh_host_that_refuses_the_copy_is_reported(self):
        with mock.patch("shutil.which", return_value="/usr/bin/scp"), \
                mock.patch("subprocess.run", return_value=mock.Mock(returncode=1)):
            report = backup.make(lambda: PHRASE, "pessoa@maquina:/tmp/destino")
        self.assertEqual(report.state, backup.FAILED)
        self.assertEqual(report.tool, "scp")

    def _archive_names(self, destination: Path) -> list[str]:
        report = backup.make(lambda: PHRASE, str(destination))
        self.assertEqual(report.state, backup.MADE)
        [sealed] = list(destination.iterdir())
        key = secrets.key_of(backup.SCOPE, PHRASE)
        opened = vault.unseal_bytes(sealed.read_bytes(), key)
        with tempfile.TemporaryDirectory() as hold:
            archive = Path(hold) / "a.tar.gz"
            archive.write_bytes(opened)
            with tarfile.open(archive, "r:gz") as tar:
                return tar.getnames()

    def test_a_cofre_file_without_the_fingerprint_does_not_travel(self):
        # TASK-154: o backup só leva o que carrega o fingerprint do `.enc` —
        # um `.enc` de outra origem, ou um claro ainda esperando o selo, ficam
        # de fora.
        (paths.strongbox_dir() / "alheio.enc").write_bytes(b"nao passou pelo cofre")
        (paths.strongbox_dir() / "esperando.txt").write_text("ainda nao selado", encoding="utf-8")
        names = self._archive_names(self.elsewhere())
        self.assertNotIn("./Cofre/alheio.enc", names)
        self.assertNotIn("./Cofre/esperando.txt", names)

    def test_a_genuinely_sealed_cofre_file_does_travel(self):
        where = paths.strongbox_dir() / "nota.txt"
        where.write_text("segredo", encoding="utf-8")
        key = vault.derived_key(vault.vault_key(PHRASE), strongbox.SCOPE)
        sealed = strongbox.seal_file(where, key)
        names = self._archive_names(self.elsewhere())
        self.assertIn(f"./Cofre/{sealed.name}", names)


class TheRestore(BackupCase):
    def test_a_missing_file_is_reported_and_nothing_is_asked(self):
        def boom() -> str:
            raise AssertionError("no phrase for a file that is not there")

        report = backup.restore(boom, str(self.root / "nao-existe.tar.gz.enc"))
        self.assertEqual(report.state, backup.NOT_FOUND)

    def test_a_folder_with_a_persons_work_refuses_and_keeps_the_file(self):
        tables.create("task", {"text": "comprar pão"})
        sealed = self.made()

        report = backup.restore(lambda: PHRASE, str(sealed))

        self.assertEqual(report.state, backup.NOT_FRESH)
        self.assertTrue(sealed.is_file())

    def test_the_wrong_phrase_does_not_open_the_file(self):
        sealed = self.made()
        other = self.elsewhere()
        self.switch(other)

        report = backup.restore(lambda: OTHER_PHRASE, str(sealed))

        self.assertEqual(report.state, backup.WRONG_KEY)
        self.assertTrue(sealed.is_file())

    def test_read_only_refuses_before_the_phrase_is_asked(self):
        sealed = self.made()
        self.switch(self.elsewhere())

        def boom() -> str:
            raise AssertionError("read-only should refuse before the phrase")

        with mock.patch.dict(os.environ, {"AT_READONLY": "1"}):
            with self.assertRaises(files.ReadOnly):
                backup.restore(boom, str(sealed))

    def test_a_fresh_folder_receives_the_backups_content_and_the_file_is_gone(self):
        tables.create("task", {"text": "comprar pão"})
        sealed = self.made()
        self.switch(self.elsewhere())
        self.assertEqual(tables.rows("task", show_all=True), [])

        report = backup.restore(lambda: PHRASE, str(sealed))

        self.assertEqual(report.state, backup.RESTORED)
        self.assertFalse(sealed.exists())
        restored = tables.rows("task", show_all=True)
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0]["text"], "comprar pão")

    @unittest.skipIf(
        versioning.DISABLED,
        "automatic versioning is switched off (versioning.DISABLED)",
    )
    @unittest.skipUnless(shutil.which("git"), "git is not on this machine")
    def test_the_restore_is_its_own_version(self):
        # The cadence's own default is periodic (§4, item 30): a commit seconds
        # after `boot`'s own would be held for the interval, same as any other
        # write's. Every-write is what makes this ACT the one this test reads
        # — chosen on the SOURCE, because `restore` overwrites `App/settings.json`
        # with what the archive carries before `versioning.commit` ever reads it.
        settings.save({**settings.load(), versioning.KEY: versioning.EVERY_WRITE})
        tables.create("task", {"text": "comprar pão"})
        sealed = self.made()
        self.switch(self.elsewhere())
        before = self._log()

        backup.restore(lambda: PHRASE, str(sealed))

        after = self._log()
        self.assertGreater(len(after), len(before))
        self.assertIn(i18n.tr("backup.restore.commit"), after[0])

    def _log(self) -> list[str]:
        import subprocess

        return subprocess.run(
            ["git", "log", "--pretty=%s"],
            cwd=paths.working_folder(), capture_output=True, text=True,
        ).stdout.splitlines()


class TheCLIWord(BackupCase):
    def run_verb(self, args: list[str], phrase: str = PHRASE) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = _backup(args, secret=lambda question: phrase)
        return code, output.getvalue()

    def test_make_with_a_local_destination_succeeds(self):
        destination = self.elsewhere()
        code, _ = self.run_verb(["make", str(destination)])
        self.assertEqual(code, OK)
        self.assertTrue(
            any(entry.name.endswith(backup.SUFFIX) for entry in destination.iterdir())
        )

    def test_wrong_number_of_arguments_is_a_usage_error(self):
        code, _ = self.run_verb(["make"])
        self.assertEqual(code, USAGE)

    def test_an_unknown_action_is_a_usage_error(self):
        code, _ = self.run_verb(["send", "algum-destino"])
        self.assertEqual(code, USAGE)

    def test_without_a_terminal_it_refuses_rather_than_assume(self):
        class _NoTerminal:
            def isatty(self) -> bool:
                return False

        output = io.StringIO()
        with mock.patch("sys.stdin", _NoTerminal()):
            with redirect_stdout(output):
                code = _backup(["make", "/tmp/onde-for"])
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("backup.no_tty"), output.getvalue())

    def test_a_short_phrase_is_refused_in_its_own_words(self):
        code, text = self.run_verb(["make", str(self.elsewhere())], phrase=SHORT)
        self.assertEqual(code, REFUSED)
        self.assertIn(i18n.tr("secrets.error.phrase", min=vault.MINIMUM), text)

    def test_the_word_is_offered_by_the_help(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["help"])
        self.assertEqual(code, OK)
        self.assertIn("backup", output.getvalue())

    def test_main_dispatches_the_word(self):
        self.assertEqual(main(["backup", "make"]), USAGE)


class TheAutomaticCopy(BackupCase):
    """O relógio dispara o backup sozinho — a rodada, a cadência e o aviso
    (TASK-133, §4 item 24).

    **The clock and the key are INJECTED.** `clock.now` is the module's one
    seam, and this suite points it at a fixed instant it advances by hand; the
    Main Key is put in the WebApp's in-memory slot (`webapp_keys.keep_main_key`),
    the same door the notifier's own test uses. No test here reads the machine's
    hour, reaches the network or holds a real Main Key.
    """

    # The instant the suite's clock reads, handed in and never taken from the
    # machine: a test that reads the clock twice disagrees with itself.
    AT = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        super().setUp()
        self.moment = self.AT
        self.ticking = mock.patch.object(clock, "now", side_effect=lambda: self.moment)
        self.ticking.start()
        self.addCleanup(self.ticking.stop)

    # -- the doors a test reads as what it does -----------------------------

    def owner(self) -> dict:
        with redirect_stdout(io.StringIO()):
            return actors.create_admin("Rafael", PHRASE)

    def declare(
        self, owner: dict | None = None, when: datetime | None = None, action: str | None = None
    ) -> dict:
        """The scheduled row, built where a boot will one day build it — the job
        that DECLARES it being the WebApp's (`_declare_backup`)."""
        with redirect_stdout(io.StringIO()):
            return tables.create(
                jobs.JOB,
                {
                    jobs.WHAT: jobs.what(backup.OBJECT, action or backup.MAKE),
                    jobs.TABLE: backup.OBJECT,
                    jobs.ARGUMENTS: [],
                    jobs.ACTOR: store.number_of(owner or self.owner()),
                    jobs.WHEN: tables.utc(when or self.AT - timedelta(minutes=1)),
                    jobs.STATUS: jobs.SCHEDULED,
                },
            )

    def job_row(self, number: int = 1) -> dict:
        return store.find(jobs.JOB, number) or {}

    def choose(self, where: Path) -> None:
        settings.save({**settings.load(), backup.DESTINATION_KEY: str(where)})

    def give_key(self, value: str | None = PHRASE) -> None:
        webapp_keys.keep_main_key(value)
        self.addCleanup(webapp_keys.keep_main_key, None)

    def tick(self, at: datetime | None = None) -> list[dict]:
        self.moment = at or self.moment
        with redirect_stdout(io.StringIO()):
            return door.tick(self.moment)

    def sealed(self, destination: Path) -> list[Path]:
        return [entry for entry in destination.iterdir() if entry.name.endswith(backup.SUFFIX)]

    # -- the reading the round is built on ----------------------------------

    def test_the_destination_is_the_one_the_folder_declared(self):
        self.assertEqual(backup.destination(), "")
        where = self.elsewhere()
        self.choose(where)
        self.assertEqual(backup.destination(), str(where))

    def test_the_cadence_defaults_to_a_day_and_a_strange_value_reads_as_the_default(self):
        self.assertEqual(backup.interval(), backup.DEFAULT_INTERVAL)
        self.assertEqual(backup.DEFAULT_INTERVAL, 1440.0)
        settings.save({**settings.load(), backup.INTERVAL_KEY: "ontem"})
        self.assertEqual(backup.interval(), backup.DEFAULT_INTERVAL)
        settings.save({**settings.load(), backup.INTERVAL_KEY: 30})
        self.assertEqual(backup.interval(), 30.0)

    def test_a_folder_that_never_copied_owes_the_first_copy(self):
        self.assertTrue(backup.due(self.AT))
        backup.attempted(self.AT)
        self.assertFalse(backup.due(self.AT))
        self.assertTrue(backup.due(self.AT + timedelta(days=1)))

    # -- the round ----------------------------------------------------------

    def test_the_declared_job_copies_the_folder_on_its_own(self):
        where = self.elsewhere()
        self.choose(where)
        self.give_key()
        self.declare()
        with mock.patch.object(notifier, "publish") as pushed:
            rounded = self.tick()
        self.assertEqual(len(rounded), 1)
        # A cópia saiu, e um sucesso não é assunto de celular.
        self.assertEqual(len(self.sealed(where)), 1)
        pushed.assert_not_called()
        # E o job VIVE: segue scheduled, com o instante movido.
        row = self.job_row()
        self.assertEqual(row[jobs.STATUS], jobs.SCHEDULED)
        self.assertEqual(row[jobs.WHEN], clock.next_instant(self.AT))

    def test_a_copy_within_the_interval_is_not_made_again(self):
        where = self.elsewhere()
        self.choose(where)
        self.give_key()
        backup.attempted(self.AT)
        self.declare()
        with mock.patch.object(notifier, "publish") as pushed:
            self.tick(self.AT + timedelta(minutes=1))
        pushed.assert_not_called()
        self.assertEqual(list(where.iterdir()), [])

    def test_a_round_without_a_destination_does_nothing_and_says_nothing(self):
        # Sem destino a pasta não tem para onde copiar: a rodada é silêncio, e
        # o backup começa a valer sozinho no minuto em que a pessoa declarar um.
        self.give_key()
        self.declare()
        with mock.patch.object(notifier, "publish") as pushed:
            self.tick()
        pushed.assert_not_called()

    def test_a_boot_without_the_main_key_does_not_copy_and_says_so_once(self):
        where = self.elsewhere()
        self.choose(where)
        self.declare()
        with mock.patch.object(notifier, "publish", return_value=(True, "")) as pushed:
            self.tick()
            # Uma segunda rodada, um minuto depois, está DENTRO do intervalo: o
            # aviso sai uma vez por intervalo e não a cada minuto.
            self.tick(self.AT + timedelta(minutes=1))
        pushed.assert_called_once()
        body = pushed.call_args.args[1]
        self.assertIn(tr("backup.make.no_key"), body)
        self.assertEqual(list(where.iterdir()), [])
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.SCHEDULED)

    def test_a_copy_the_scan_blocked_reaches_the_phone_in_the_words_of_the_cli(self):
        where = self.elsewhere()
        self.choose(where)
        self.give_key()
        self.declare()
        with mock.patch.object(backup.scanner, "scan", return_value=_found()), \
                mock.patch.object(notifier, "publish", return_value=(True, "")) as pushed:
            self.tick()
        pushed.assert_called_once()
        body = pushed.call_args.args[1]
        self.assertIn(tr("backup.make.blocked"), body)
        self.assertEqual(list(where.iterdir()), [])
        self.assertEqual(self.job_row()[jobs.STATUS], jobs.SCHEDULED)

    def test_a_restore_that_someone_scheduled_is_refused(self):
        # `restore` troca a pasta inteira pelo que o arquivo guardava, e um ato
        # desses disparado sem ninguém seria a perda que o backup evita.
        with redirect_stdout(io.StringIO()):
            code, answer, *_ = door.run(
                "backup", "restore", [str(self.elsewhere())],
                actor=self.owner(), via=audit.ENGINE,
            )
        self.assertEqual(code, USAGE)


class TheDeclaration(BackupCase):
    """O job nasce na SUBIDA, enquanto a `cli` de declarar (TASK-139) não existe."""

    def declared(self) -> list[dict]:
        return store.load(jobs.JOB)

    def test_the_boot_declares_the_backup_job_once_for_the_admin(self):
        with redirect_stdout(io.StringIO()):
            owner = actors.create_admin("Rafael", PHRASE)
        webapp._declare_backup()
        webapp._declare_backup()  # idempotente: uma linha, nunca duas
        rows = self.declared()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row[jobs.WHAT], jobs.what(backup.OBJECT, backup.MAKE))
        self.assertEqual(row[jobs.STATUS], jobs.SCHEDULED)
        self.assertEqual(row[jobs.ACTOR], store.number_of(owner))

    def test_a_folder_with_no_admin_declares_nothing(self):
        # §4: o job roda com a autoridade de quem o possui, e sem pessoa nenhuma
        # não há a quem dar o job.
        webapp._declare_backup()
        self.assertEqual(self.declared(), [])

    def test_a_job_a_person_turned_off_is_not_recreated(self):
        # A subida não briga com a pessoa: uma linha de `backup:make` que já
        # existe não é tocada, seja qual for o estado em que ela a deixou.
        # (Desligar de verdade é o verbo da TASK-139, não desta subida.)
        with redirect_stdout(io.StringIO()):
            actors.create_admin("Rafael", PHRASE)
            webapp._declare_backup()
            tables.edit(jobs.JOB, 1, {jobs.STATUS: jobs.REFUSED})
            webapp._declare_backup()
        self.assertEqual(len(self.declared()), 1)
        self.assertEqual(self.job_row(1)[jobs.STATUS], jobs.REFUSED)

    def job_row(self, number: int) -> dict:
        return store.find(jobs.JOB, number) or {}

    def test_the_webapp_boot_declares_it(self):
        with redirect_stdout(io.StringIO()):
            actors.create_admin("Rafael", PHRASE)
        server = mock.Mock()
        server.server_address = ("127.0.0.1", 0)
        with mock.patch.object(webapp_launch, "make_server", return_value=server), \
                mock.patch.object(webapp_clock, "beat"):
            with redirect_stdout(io.StringIO()):
                webapp.run(0, include_caddy=False)
        self.assertEqual(len(self.declared()), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
