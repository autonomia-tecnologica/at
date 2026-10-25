"""What every word of the command line shares: the reader type and the usage refusal."""

from __future__ import annotations

from collections.abc import Callable

from at.i18n import tr
from at.ui import ask as door
from at.ui.ask import USAGE

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot.ensure_working_folder` takes.
Ask = Callable[[str], str]


def readers() -> tuple[Ask | None, Ask | None]:
    """`cli._readers`, resolved at call time: the facade owns the name, and a test
    that patches it there is heard by every word that reads a person."""
    from at.ui import cli

    return cli._readers()


def reject_extra(word: str, argument: str) -> int:
    """The refusal that names WHAT failed: the argument the word did not take."""
    print(door.surplus(word, argument))
    return USAGE


def reject_unknown(word: str) -> int:
    """The refusal of a sub-word nobody declared: it names that sub-word."""
    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def reject(word: str) -> int:
    print(door.rejected(word))
    return USAGE
