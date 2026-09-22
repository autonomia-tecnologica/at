"""The first run: a folder becomes a Working Folder.

The folder is the binary's, so Bill describes it and asks before writing a
single file (§3). Two refusals are deliberate:

- **No terminal to ask in means no folder is created.** A folder is a decision,
  and a decision made where nobody could answer is not one. That is the
  fail-closed posture: what was not authorized does not happen.
- **Declining is not an error.** Nothing is written, and Bill says what to do
  instead of insisting.
"""

from __future__ import annotations

import sys
from typing import Callable

from bill.core import paths, settings
from bill.data import schema
from bill.i18n import active_code, tr, write_active

# Both spellings answer the same question: the language of the prompt is the
# active one, but the person answering is free to type either.
_YES = frozenset({"s", "sim", "y", "yes"})

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
        return True

    folder = paths.working_folder()
    print(tr("boot.first_run.notice", folder=folder))

    if ask is None:
        if not sys.stdin.isatty():
            print(tr("boot.first_run.no_tty"))
            return False
        ask = _ask

    if not _is_yes(ask(tr("boot.first_run.confirm"))):
        print(tr("boot.first_run.cancelled"))
        return False

    create_working_folder()
    print(tr("boot.first_run.created", folder=folder))
    return True


def create_working_folder() -> None:
    """Lay down what a Working Folder is born with (§4).

    `exist_ok` everywhere: running Bill from a checkout means `data/` and
    `prose/` may already be there, and finding them is not a conflict.
    """
    paths.bill_dir().mkdir(parents=True, exist_ok=True)
    for directory in (paths.data_dir(), paths.prose_dir()):
        directory.mkdir(parents=True, exist_ok=True)

    # The system tables arrive with the product and land in the folder here, so
    # that the folder is whole on its own from the first run on (§4).
    schema.seed(paths.data_dir() / schema.SCHEMA_DIR)

    settings.save({"schema": settings.SCHEMA})

    # The catalogs are packed into the binary; the folder keeps only the choice.
    write_active(active_code())

    _write_welcome()


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


def _is_yes(answer: str) -> bool:
    return answer.strip().lower() in _YES
