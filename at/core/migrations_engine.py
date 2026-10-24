"""The two moves most steps are made of: handing a permission over, and
extending a declaration without overwriting what a person edited.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

from at.core import (
    actors,
    permissions,
    tables,
)
from at.core.migrations_base import Report
from at.data import schema, store


def _hand_over(names: tuple[str, ...]) -> list[Report]:
    """The administrator's role catches up with the catalogue this swap grew.

    Item 9 promised that role "exactly the permissions needed to administer,
    which item 11 defines" — and a folder born before a swap carries a role born
    from the catalogue of THAT day. The catalogue is bigger now: the prose layer
    and the interpreter's door are objects the routes demand, and the services,
    the plugins and the vocabulary are objects §4 names. A folder that upgraded
    without this would be refused its own files by the very ceiling item 11 put
    in, and would carry a role narrower than the one a folder born today wears.

    **Only what `names` names, and never the whole catalogue.** The difference is
    the whole of the care taken here: a permission the person took OUT of a role
    before the swap was taken out on purpose, and a migration that re-granted
    everything would be AT overwriting a decision it never made. What this
    hands over is what the folder never had the CHANCE to carry, because it did
    not exist on the day the role was born.

    It does not ask: the row is AT's own — the first administrator's role —
    the change only ever ADDS, and every entry is one the catalogue names. A
    folder with no `admin` role has nothing to catch up, and says nothing: a
    folder that never had an administrator has no role to fix.
    """
    role = actors.admin_role()
    number = store.number_of(role) if role is not None else None
    if number is None:
        return []
    held = permissions.carried(role)
    granted = [permission for permission in names if permission not in held]
    if not granted:
        return [("boot.migration.catalogue.kept", {"role": actors.ADMIN_ROLE})]
    tables.edit(
        "role", number, {"permissions": ",".join([*held, *granted])}
    )
    return [
        (
            "boot.migration.catalogue.granted",
            {"role": actors.ADMIN_ROLE, "names": ", ".join(granted)},
        )
    ]


def _extend(additions: dict[str, dict]) -> list[Report]:
    """Grow every declaration `additions` names, and report what happened.

    It is the body the additive migrations share — nine, and thirteen — and the
    rule it exists to serve is §3's: a migration never overwrites what is already
    there — it adds what is missing and reports what it skipped. What is hard
    about it is that the declaration is a file a PERSON edits, so every addition
    meets whatever they wrote there: the `type` a field was missing, the `enum`
    of a closed vocabulary, an entry of a list, a whole block a table never had.

    A collision — the path already carrying something else — is the person's
    edit winning, and it is SAID, by the name of the path it happened at, so
    whoever reads can open the file and find it. AT does not choose between its
    declaration and the person's: it says what it found, which is the same choice
    it makes about the image pin (§3).

    Two other things about the folder have a report of their own, and neither is
    touched: a declaration that is not there — a deletion that was meant, and
    `seed` does not bring back either — and one that does not parse, which is the
    person's file and not AT's to rewrite.

    **Sharing it does not edit a published migration.** What nine MEANT on the
    day it shipped is `EXTENDED` and this promise; the loop is machinery, and a
    folder that ran nine saw exactly what it would have seen with the loop
    written out there. A release that adds something to a declaration still
    brings its own step and its own dict, which is what the rule protects.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration).
    """
    added: list[str] = []
    collisions: list[str] = []
    missing: list[str] = []
    unreadable: list[str] = []
    for table, entries in additions.items():
        grown = schema.extend(table, entries)
        if grown.state == "missing":
            missing.append(table)
            continue
        if grown.state == "unreadable":
            unreadable.append(table)
            continue
        added.extend(f"{table}.{path}" for path in grown.added)
        collisions.extend(f"{table}.{path}" for path in grown.collisions)

    report: list[Report] = []
    if added:
        report.append(("boot.migration.declarations.extended", {"names": ", ".join(added)}))
    if collisions:
        report.append(("boot.migration.declarations.collision", {"names": ", ".join(collisions)}))
    if missing:
        report.append(("boot.migration.declarations.missing", {"names": ", ".join(missing)}))
    if unreadable:
        report.append(("boot.migration.declarations.unreadable", {"names": ", ".join(unreadable)}))
    if not report:
        report.append(("boot.migration.declarations.unchanged", {}))
    return report
