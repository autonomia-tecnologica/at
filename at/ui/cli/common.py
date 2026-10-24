"""What every word of the command line shares: the reader type and the usage refusal."""

from __future__ import annotations

from collections.abc import Callable

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


def reject(word: str) -> int:
    print(door.rejected(word))
    return USAGE
