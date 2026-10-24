"""The word tree both `cli`s are made of, and the shape the help is drawn in.

There are two artifacts and two command lines (item 27), and both of them offer
their words the same way: a declaration read by the help and by the dispatch, so
that a word can never dispatch without being offered nor the other way round. The
DECLARATIONS are each surface's own — `at-cli`'s tree is `ui/cli/tree.py` and the
deploy's is `at_deploy/tree.py` — and the SHAPE is this file, written once,
because a product whose two surfaces drew their help differently would be two
products wearing one name.

`about` is an **i18n key**, never the text: the word is the machine's, the
sentence is the person's.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from at.i18n import tr


@dataclass(frozen=True)
class Node:
    name: str
    """The machine word — English, canonical, never translated (§3)."""

    about: str
    """The i18n key of the one-line description."""

    children: tuple["Node", ...] = ()


def completion_words(nodes: tuple[Node, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """The words a shell completion offers, read off the tree the help reads.

    One level down and no further, which is as deep as the vocabulary goes
    (§5): the word, and the words under it. Plain tuples and not `Node`s
    because the consumer is `core/install.py`, which must know nothing of a
    tree's shape — the declaration stays here and only its shape travels.
    """
    return tuple(
        (node.name, tuple(child.name for child in node.children))
        for node in nodes
    )


def width(nodes: tuple[Node, ...]) -> int:
    """The column the descriptions start at: the longest word there is."""
    return max((len(node.name) for node in nodes), default=0)


def table(rows: Sequence[Sequence[str]]) -> str:
    """Rows printed as a TABLE: the first row is the header, and every column is
    as wide as its widest cell.

    It is the shape a listing already had (`ui/ask.py`), and it lives here for
    the reason the help's shape lives here: the two artifacts print the same
    kind of thing, and a second renderer would be a second set of widths — the
    one that drifts the first time a title grows a character.

    The widths are measured from what is ABOUT to be printed, so a column is as
    wide as its widest cell and never as wide as somebody guessed.
    """
    widths = [max(len(cell) for cell in column) for column in zip(*rows, strict=False)]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=False)).rstrip()
        for row in rows
    )


def section(nodes: tuple[Node, ...], column: int, title_key: str) -> list[str]:
    """One block of the help: the word, what it is, and the words under it."""
    described = [(node, tr(node.about)) for node in nodes]
    about = max((len(text) for _, text in described), default=0)
    lines = ["", tr(title_key)]
    for node, text in described:
        under = ", ".join(child.name for child in node.children)
        tail = f"   · {under}" if under else ""
        lines.append(f"  {node.name.ljust(column)}  {text.ljust(about)}{tail}".rstrip())
    return lines
