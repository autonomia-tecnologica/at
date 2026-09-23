"""The first run: a folder becomes a Working Folder — and keeps up after that.

The folder is the binary's, so Bill describes it and asks before writing a
single file (§3). Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A folder is a decision,
  and a decision made where nobody could answer is not one. That is the
  fail-closed posture: what was not authorized does not happen.
- **Declining is not an error.** Nothing is written, and Bill says what to do
  instead of insisting.

A folder that is ALREADY configured has its own first step, and it comes before
anything else reads a path: the migrations that bring it up to the shape this
release declares (§3). They run here, on the first start after the binary is
replaced, and never anywhere else.

The order matters, and it is the whole of the item this file answers: a folder
that has not migrated yet is still found by its OLD name — `paths.instance_dir`
reads what is on disk — so Bill knows it is configured, catches it up, and only
then works. Resolving the path first would offer to create a Working Folder on
top of the one that is already there.
"""

from __future__ import annotations

import sys
from typing import Callable

from bill.core import migrations, paths, settings
from bill.data import schema
from bill.i18n import active_code, tr, write_active

# What a person answers with, injected so a test can answer without a terminal.
Ask = Callable[[str], str]


def is_configured() -> bool:
    return settings.exists()


def ensure_working_folder(ask: Ask | None = None) -> bool:
    """Make sure Bill has a Working Folder to work in.

    `True` when the folder is ready — already configured, or just confirmed.
    `False` when it is not, and Bill must stop without doing anything else.
    """
    if is_configured():
        catch_up(ask)
        return True

    folder = paths.working_folder()
    print(tr("boot.first_run.notice", folder=folder))

    if ask is None:
        if not sys.stdin.isatty():
            print(tr("boot.first_run.no_tty"))
            return False
        ask = _ask

    if not migrations.is_yes(ask(tr("boot.first_run.confirm"))):
        print(tr("boot.first_run.cancelled"))
        return False

    create_working_folder()
    print(tr("boot.first_run.created", folder=folder))
    return True


def catch_up(ask: Ask | None = None) -> None:
    """Bring a folder that already exists up to this release's shape.

    Both halves are offers, and both say what they did: the migrations this
    folder had not run, and — when the language changed since the folder was
    named — the rename that follows the language. A refusal is a report too:
    whoever declined is told what the folder keeps costing them, and is not
    asked again about the same language.
    """
    for key, fields in migrations.run(ask) + migrations.offer_language(ask):
        print(tr(key, **fields))


def create_working_folder() -> None:
    """Lay down what a Working Folder is born with (§4).

    `exist_ok` everywhere: running Bill from a checkout means the folders may
    already be there, and finding them is not a conflict.

    Every folder is born under the name the ACTIVE LANGUAGE gives it, and the
    two that no session fills yet — `Projetos/` and `Compartilhada/` — are born
    empty here: the folder is whole on its own from the first run on.
    """
    paths.app_dir().mkdir(parents=True, exist_ok=True)
    for directory in (
        paths.data_dir(),
        paths.prose_dir(),
        paths.projects_dir(),
        paths.shared_dir(),
    ):
        directory.mkdir(parents=True, exist_ok=True)

    # The system tables arrive with the product and land in the folder here, so
    # that the folder is whole on its own from the first run on (§4).
    schema.seed(paths.data_dir() / schema.SCHEMA_DIR)

    settings.save({"schema": settings.SCHEMA})

    # The catalogs are packed into the binary; the folder keeps only the choice.
    write_active(active_code())

    _write_welcome()

    # Born in this release's shape, so it has nothing to catch up on: the stamp
    # exists so the FIRST start of an old folder differs from the first start of
    # a new one, and this is that difference.
    migrations.record()


def _write_welcome() -> None:
    """The welcome note is written once: a person who deleted it meant it."""
    welcome = paths.prose_dir() / tr("prose.welcome.filename")
    if welcome.exists():
        return
    welcome.write_text(tr("prose.welcome.body"), encoding="utf-8", newline="\n")


def _ask(question: str) -> str:
    try:
        return input(question)
    except EOFError:
        # A closed stdin is an unanswered question, never a yes.
        return ""
