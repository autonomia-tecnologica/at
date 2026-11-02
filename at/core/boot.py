"""The first run: a folder becomes a Working Folder — and keeps up after that.

The folder is the binary's, so AT describes it and asks before writing a
single file (§3). Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A folder is a decision,
  and a decision made where nobody could answer is not one. That is the
  fail-closed posture: what was not authorized does not happen.
- **Declining is not an error.** Nothing is written, and AT says what to do
  instead of insisting.

A folder that is ALREADY configured has its own first step, and it comes before
anything else reads a path: the migrations that bring it up to the shape this
release declares (§3). They run here, on the first start after the binary is
replaced, and never anywhere else.

The order matters, and it is the whole of the item this file answers: a folder
that has not migrated yet is still found by its OLD name — `paths.instance_dir`
reads what is on disk — so AT knows it is configured, catches it up, and only
then works. Resolving the path first would offer to create a Working Folder on
top of the one that is already there.
"""

from __future__ import annotations

import sys
from typing import Callable

from at.core import actors, files, migrations, paths, settings, versioning
from at.data import schema
from at.i18n import active_code, tr, write_active

# What a person answers with, injected so a test can answer without a terminal.
Ask = Callable[[str], str]


def is_configured() -> bool:
    return settings.exists()


def ensure_working_folder(ask: Ask | None = None) -> bool:
    """Make sure AT has a Working Folder to work in.

    `True` when the folder is ready — already configured, or just confirmed.
    `False` when it is not, and AT must stop without doing anything else.
    """
    # The terminal is resolved ONCE, here, and both halves use the same door:
    # the first run and the catch-up ask the person the same question, and a
    # migration that got a `None` while a terminal sat in front of it would
    # refuse to move a folder nobody was ever asked about.
    if ask is None and sys.stdin.isatty():
        ask = _ask

    if is_configured():
        catch_up(ask)
        return True

    folder = paths.working_folder()
    print(tr("boot.first_run.notice", folder=folder))

    if ask is None:
        print(tr("boot.first_run.no_tty"))
        return False

    if not migrations.is_yes(ask(tr("boot.first_run.confirm"))):
        print(tr("boot.first_run.cancelled"))
        return False

    create_working_folder(ask)
    print(tr("boot.first_run.created", folder=folder))
    # The folder is born without an administrator ON PURPOSE, and the person is
    # told where the first one comes from: seeding one would be a published
    # credential, and the door that creates it lives in the `cli` (§3, item 9).
    print(tr("boot.first_run.admin_needed"))
    return True


def catch_up(ask: Ask | None = None) -> None:
    """Bring a folder that already exists up to this release's shape.

    Both halves are offers, and both say what they did: the migrations this
    folder had not run, and — when the language changed since the folder was
    named — the rename that follows the language. A refusal is a report too:
    whoever declined is told what the folder keeps costing them, and is not
    asked again about the same language.
    """
    migrations.run(ask)
    migrations.offer_language(ask)
    # The folder's versioning, on every start: the repository is born here when
    # it could not be born before, and a folder that is not under versioning
    # says so — rather than waiting quietly for a state nobody named.
    versioning.notice()


def create_working_folder(ask: Ask | None = None) -> None:
    """Lay down what a Working Folder is born with (§4).

    `exist_ok` everywhere: running AT from a checkout means the folders may
    already be there, and finding them is not a conflict.

    Every folder is born under the name the ACTIVE LANGUAGE gives it, and the
    three that no session fills yet — `Projetos/`, `Compartilhada/` and
    `Harness/` — are born empty here: the folder is whole on its own from the
    first run on.
    """
    paths.app_dir().mkdir(parents=True, exist_ok=True)
    for directory in (
        paths.data_dir(),
        paths.prose_dir(),
        paths.projects_dir(),
        paths.shared_dir(),
        paths.harness_dir(),
        paths.strongbox_dir(),
        paths.convert_dir(),
    ):
        directory.mkdir(parents=True, exist_ok=True)

    # The system tables arrive with the product and land in the folder here, so
    # that the folder is whole on its own from the first run on (§4).
    schema.seed(paths.data_dir() / schema.SCHEMA_DIR)

    # The engine's row is born with the folder, because every act of the engine
    # needs a row to be named in the `audit` (item 15). The first ADMIN is not:
    # it is asked for, and `at-cli admin` is the door (§3, item 9).
    actors.seed_engine()

    settings.save({"schema": settings.SCHEMA})

    # The catalogs are packed into the binary; the folder keeps only the choice.
    write_active(active_code())

    _write_welcome()
    _write_root_note()

    # Born in this release's shape, so it has nothing to catch up on: the stamp
    # exists so the FIRST start of an old folder differs from the first start of
    # a new one, and this is that difference.
    migrations.record()

    # LAST, and deliberately: versioning is the folder's own repository, and it
    # is born over a folder that is already whole — so the first commit carries
    # a Working Folder and not the pieces it was being assembled from.
    versioning.start(ask)


def _write_welcome() -> None:
    """The welcome note is written once: a person who deleted it meant it."""
    welcome = paths.prose_dir() / tr("prose.welcome.filename")
    if welcome.exists():
        return
    welcome.write_text(tr("prose.welcome.body"), encoding="utf-8", newline="\n")


def _write_root_note() -> None:
    """`README.md` — the folder introducing itself (§0, item 25).

    Whoever opens the folder — a person, or a model working in it — reads what
    its root carries, so the root carries a note that says what this folder is,
    what it holds and how to reach the rest. It POINTS: the rules are the
    product's, they live in the founding document, and a note that restated them
    here would be the second copy of a rule (§0).

    Written ONCE, like the welcome note and for the same reason: it is the
    folder's, and a note that comes back is a note arguing with whoever deleted
    it. It is deliberately NOT inside `Biblioteca/` — that folder is the person's
    material, and this one is the folder's own.
    """
    note = paths.root_note()
    if note.exists():
        return
    files.atomic_write_text(note, tr("folder.agent.body"))


def _ask(question: str) -> str:
    try:
        return input(question)
    except EOFError:
        # A closed stdin is an unanswered question, never a yes.
        return ""
