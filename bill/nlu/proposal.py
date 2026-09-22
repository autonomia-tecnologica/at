"""What a sentence becomes: one action, one table, and what it sets.

A proposal is what the interpreter answers with, and it is deliberately not a
row: nothing here has been validated, nothing here has been written, and none of
the values here are the store's yet. **The interpreter proposes; the core
validates and writes** (§4) — so a proposal is the shape of an intention, and
`bill.core.tables` is what says whether it may become one.

It is one action because the item fixed it that way: a batch would be an action
of its own the day a batch API exists, with its own permission. A sentence that
names two is refused, never disambiguated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Proposal:
    """One act as a sentence proposed it, before the core has a word on it.

    `action` is one of `tables.ACTIONS` and `table` a declared table — the
    interpreter names them, it does not invent them. `row` is the number a
    person named when the action acts on one, and `None` when the action needs
    none: `create` and `list` are the two that never do.

    `values` is **not** the engine's to trust: it is handed to `_coerce`, and the
    answer a person reads comes back from the engine's own mouth.
    """

    action: str
    table: str
    values: dict[str, Any] = field(default_factory=dict)
    row: Any = None
