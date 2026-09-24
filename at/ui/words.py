"""The word tree both `cli`s are made of, and the shape the help is drawn in.

There are two artifacts and two command lines (item 27), and both of them offer
their words the same way: a declaration read by the help and by the dispatch, so
that a word can never dispatch without being offered nor the other way round. The
DECLARATIONS are each surface's own — `at`'s tree is `ui/cli/tree.py` and the
deploy's is `at_deploy/tree.py` — and the SHAPE is this file, written once,
because a product whose two surfaces drew their help differently would be two
products wearing one name.

`about` is an **i18n key**, never the text: the word is the machine's, the
sentence is the person's.
"""

from __future__ import annotations

from dataclasses import dataclass

from at.i18n import tr


@dataclass(frozen=True)
class Node:
    name: str
    """The machine word — English, canonical, never translated (§3)."""

    about: str
    """The i18n key of the one-line description."""

    children: tuple["Node", ...] = ()


def width(nodes: tuple[Node, ...]) -> int:
    """The column the descriptions start at: the longest word there is."""
    return max((len(node.name) for node in nodes), default=0)


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
