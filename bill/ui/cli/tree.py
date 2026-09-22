"""The word tree — the single declaration every surface reads.

Help and dispatch both read this, so a word can never dispatch without being
offered, nor the other way round. A word is declared here once and named nowhere
else.

`about` is an **i18n key**, never the text: the word is the machine's, the
sentence is the person's. The table words are not written here at all — they come
from `data/schema/`, which is what makes a table a table (§4). Add a
declaration and the word appears, with its actions, in the help and in the
dispatch at once.
"""

from __future__ import annotations

from dataclasses import dataclass

from bill import __version__, nlu
from bill.core import tables
from bill.data import schema
from bill.i18n import tr


@dataclass(frozen=True)
class Node:
    name: str
    """The machine word — English, canonical, never translated (§3)."""

    about: str
    """The i18n key of the one-line description."""

    children: tuple["Node", ...] = ()


WORDS: tuple[Node, ...] = (
    Node("webapp", "cli.webapp.about", (Node("run", "cli.webapp.run.about"),)),
    Node("help", "cli.help.about"),
    Node("version", "cli.version.about"),
)

# The interpreter's word, and the other spelling that answers to it: `ask` is
# the machine's, `pedir` is the one the derived document writes, and they are
# one door — the same way `webapp` answers to `run`.
ASK = Node("ask", "cli.ask.about", (Node("pedir", "cli.ask.pedir.about"),))


def words() -> tuple[Node, ...]:
    """The words that are not a table.

    The interpreter's is here while its switch is on, and gone the moment it is
    off: help and dispatch both read this one list, so the word leaves both at
    once — which is what the item means by turning it off taking the word out of
    the tree, and taking nothing else.
    """
    return ((ASK,) if nlu.enabled() else ()) + WORDS


def ask_words() -> tuple[str, ...]:
    """Every word that reaches the interpreter — and nothing at all when it is
    off, so a spelling can never dispatch without the help offering it."""
    if not nlu.enabled():
        return ()
    return (ASK.name, *(child.name for child in ASK.children))


def table_nodes() -> tuple[Node, ...]:
    """One root per declared table, each carrying the actions it answers.

    The action list is the engine's (`tables.ACTIONS`), not a second copy here:
    a word that dispatches is a word the help offers.
    """
    return tuple(
        Node(
            str(declared["id"]),
            schema.name_key(str(declared["id"]), many=True) or str(declared["id"]),
            tuple(Node(action, f"table.action.{action}") for action in tables.ACTIONS),
        )
        for declared in schema.declared()
    )


def roots() -> tuple[Node, ...]:
    return words() + table_nodes()


def find(name: str) -> Node | None:
    return next((node for node in roots() if node.name == name), None)


def as_text() -> str:
    """The help, in the active language."""
    declared = table_nodes()
    width = max((len(node.name) for node in roots()), default=0)

    lines = [
        tr("cli.help.title", version=__version__),
        "",
        tr("cli.help.usage"),
    ]
    if declared:
        lines += _section(declared, width, "cli.help.tables")
    lines += _section(words(), width, "cli.help.words")
    lines += ["", tr("cli.help.no_args")]
    return "\n".join(lines)


def _section(nodes: tuple[Node, ...], width: int, title_key: str) -> list[str]:
    """One block of the help: the word, what it is, and the words under it."""
    described = [(node, tr(node.about)) for node in nodes]
    about = max((len(text) for _, text in described), default=0)
    lines = ["", tr(title_key)]
    for node, text in described:
        under = ", ".join(child.name for child in node.children)
        tail = f"   · {under}" if under else ""
        lines.append(f"  {node.name.ljust(width)}  {text.ljust(about)}{tail}".rstrip())
    return lines
