"""Shared constants and argument readers of the door (`at.ui.ask`) — the leaf every other piece of it imports.
"""

from __future__ import annotations

from at.core import (
    projects,
    tables,
)
from at.i18n import tr

# The two tables the tree is read off, named once: the `--project` filter and
# the slices of an item are about the pair, and a string typed twice is the one
# that drifts from the declaration.
PROJECT = projects.PROJECT
TASK = projects.TASK

# The three outcomes of an exit, and the same three the `cli` documents.
OK = 0
REFUSED = 1
USAGE = 2


def _sign(op: str) -> str:
    """A operação como um SINAL, para a proposta: `até` é `≤`, `desde` é `≥`, e
    o valor exato é `=`. É o que a pessoa lê para saber se o filtro é um ponto ou
    um intervalo."""
    return {"<=": "≤", ">=": "≥", "<": "<", ">": ">"}.get(op, "=")


def _sets(args: list[str]) -> tuple[dict[str, str], list[str]]:
    """`--set field=value` pairs, and whatever was left that was not one."""
    values: dict[str, str] = {}
    leftovers: list[str] = []
    position = 0
    while position < len(args):
        if args[position] != "--set":
            leftovers.append(args[position])
            position += 1
            continue
        if position + 1 >= len(args) or "=" not in args[position + 1]:
            raise tables.TableError("error.set_needs_value")
        name, value = args[position + 1].split("=", 1)
        values[name.strip()] = value
        position += 2
    return values, leftovers


def rejected(word: str) -> str:
    """The sentence a surface reads when a word was given the wrong arguments."""
    return tr("cli.error.rejected_arguments", word=word)
