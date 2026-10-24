"""The closed list: narrowing, actions, needed, catalogue and is_known.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations

from at.core import tables
from at.core.permissions_base import DECLARED, EXTRA, NARROWED
from at.data import schema


def narrowed(table: str) -> dict[str, tuple[str, ...]]:
    """The permissions this object's declaration narrows it to, or `{}`.

    TWO SOURCES, and they are composed. The declaration is the TABLE's own
    (`data/schema/<table>.json`), and what it names is held to the engine's six
    — an action the engine does not have is not a permission that exists (§4).
    `NARROWED` carries the rest: the objects that are not a table at all (the
    settings), and the acts an object declares of its OWN — the ones the engine
    does not have, like the `job`'s run and its two answers and the `secret`'s
    scan. A table that has both writes both, and this is where they meet, so a
    word, a route and a role never read two answers.

    It is read the way every other declaration is, and answered the way every
    other read of a declaration answers: what is not there, or is not shaped the
    way the declaration is, is nothing — a hand-edited file is a table the
    catalogue answers for with the engine's six, never a read that raises. What
    `NARROWED` names is taken as it stands, and it wins a name both sources
    spell: it is the object's own word for an act, and the one place the act
    exists.
    """
    found: dict[str, tuple[str, ...]] = {}
    declared = schema.of(table) or {}
    stated = declared.get(DECLARED)
    if isinstance(stated, dict):
        for permission, actions in stated.items():
            if not isinstance(permission, str) or not isinstance(actions, list):
                continue
            kept = tuple(action for action in tables.ACTIONS if action in actions)
            if kept:
                found[permission] = kept
    held = NARROWED.get(table)
    if held is not None:
        for permission, actions in held.items():
            found[permission] = tuple(actions)
    return found


def actions(table: str) -> tuple[str, ...]:
    """The words this object answers, in the order a surface offers them.

    It is what the help offers and what the dispatch accepts (`tree`), so a word
    the object does not answer is a word no surface spells. The engine's six come
    FIRST, in the engine's order, because the six are the engine's and a
    declaration does not reorder them; what the object declares of its own — the
    acts the engine does not have, like the `job`'s run and its two answers, and
    the `secret`'s scan — comes after, in the order its narrowing names them. It
    answers for a table and for an object that is not one alike, which is how the
    `setting` word is declared: the tree reads its children from here and does
    not write them down.
    """
    found = narrowed(table)
    if not found:
        return tables.ACTIONS
    declared = [action for actions in found.values() for action in actions]
    own = [action for action in declared if action not in tables.ACTIONS]
    return tuple(
        [action for action in tables.ACTIONS if action in declared] + own
    )


def needed(table: str, action: str) -> str:
    """The permission an engine action demands of `table`.

    A table that declares nothing demands the action's own name, which is what
    every table did before a declaration could narrow it; one that declares a
    permission over the action demands THAT, so the route, the interpreter's
    ceiling and the role are all reading the same name.
    """
    for permission, actions in narrowed(table).items():
        if action in actions:
            return f"{table}:{permission}"
    return f"{table}:{action}"


def catalogue() -> dict[str, tuple[str, ...]]:
    """Every object and the permissions it accepts, in the catalogue's order."""
    found: dict[str, tuple[str, ...]] = {}
    for declared in schema.declared():
        table = declared.get("id")
        if not isinstance(table, str):
            continue
        found[table] = tuple(narrowed(table)) or tables.ACTIONS
    found.update(EXTRA)
    return found


def all_permissions() -> list[str]:
    """The whole closed list, `object:action`, in the catalogue's order."""
    return [
        f"{obj}:{action}" for obj, actions in catalogue().items() for action in actions
    ]


def is_known(permission: str) -> bool:
    """Whether the catalogue names this permission. Never raises: a role a hand
    edited is a row this door has to answer about, and an exception would take
    down the read that found it."""
    obj, _, action = permission.partition(":")
    return action in catalogue().get(obj, ())
