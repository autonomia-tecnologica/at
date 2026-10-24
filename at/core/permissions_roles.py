"""What a role row carries.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations


def carried(role: object) -> list[str]:
    """The permissions a role row carries, as the row declares them.

    The row is READ and never trusted: `permissions` is a list by declaration
    (§4), and a row a hand edited to something else carries nothing — a read is
    not the place to raise about it, and no surface is left with a screen it
    cannot draw. What a NAME means is `is_known`'s question and not this one: a
    role may name a permission the catalogue does not have, and it is the read
    that shows the role which ones those are. Here they carry exactly what they
    say, which is nothing a route demands.
    """
    declared = role.get("permissions") if isinstance(role, dict) else None
    if not isinstance(declared, list):
        return []
    return [entry for entry in declared if isinstance(entry, str)]


def carries(role: object, permission: str) -> bool:
    """Whether this role carries a permission — the ceiling of the actor that
    points at it (§4).

    A plain membership, and the whole of it: the catalogue entry IS the grant,
    the row names them one by one, and a permission the role does not name is
    one it does not carry. A `task:*` shape is not a permission the catalogue
    names, and the day one is wanted it will be a decision taken here and not a
    guess made by whoever reads a role.

    **A role that is not there carries nothing**, and that is the rule failing
    CLOSED: an actor whose row points at no role — or at a number nobody wears —
    reaches nothing at all, instead of everything. The `engine`'s row is the
    one born that way, and it is right for it: it does not enter, and its
    ceiling is the engine's own (§4).
    """
    return permission in carried(role)
