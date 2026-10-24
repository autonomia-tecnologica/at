"""Migrations six to ten: the declarations the folder carries, the catalogue,
the objects and the versioning.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

from at.core import (
    actors,
    paths,
    versioning,
)
from at.core.migrations_base import Ask, Report
from at.core.migrations_engine import _extend, _hand_over
from at.data import schema

# The tables THIS release introduces — what migration six names. A published
# migration is never edited, so the next release that brings a system table
# brings its own step and its own list, and this one goes on meaning what it
# meant on the day it shipped.
INTRODUCED = ("actor", "role")


def _declarations(ask: Ask | None) -> list[Report]:
    """The declarations of this release — the tables THIS swap introduced.

    It is the EASY half of item 5: the declaration that is ABSENT. `schema.seed`
    writes only what is missing, so a folder that already carried them gains
    nothing — and that is deliberate, because a system table a person deleted
    is a deletion that was meant, which is why the migration runs ONCE and the
    seed does not come back on every start.

    The list is EXPLICIT, and that is the same promise from the other side: the
    migration is a dated fact — what changed in that one binary swap — and one
    that seeded the whole directory would bring back, on the first start after
    the swap, a declaration somebody had deleted. The hard half stays item 5's:
    a NEW field inside a file that is already there, which has to meet a
    person's edit without overwriting it.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration). The engine's row comes along, because
    the folder that gains the `actor` table is the folder that starts having who
    acts in it — and `seed_engine` leaves a folder that already had it alone.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=INTRODUCED)
    actors.seed_engine()
    if written:
        return [
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        ]
    return [("boot.migration.declarations.kept", {})]


# The catalogue entries item 11's FIRST slice introduced — what migration seven
# grants. It is a list for the same reason `INTRODUCED` is one: a published
# migration is never edited, so the next release that grows the catalogue brings
# its own step and its own names, and this one goes on meaning what it meant on
# the day it shipped.
ADDED = ("prose:read", "prose:edit", "nlu:ask")


# And the entries the SECOND slice grew it by. They are a migration of their own
# and not three more names in the list above, and that is the rule earning its
# keep in the smallest possible case: seven had ALREADY RUN on folders when this
# slice landed — this checkout's own instance among them — and a permission added
# to a published migration is a permission those folders would never be handed.
#
# What the objects are is §4's: "the settings, the services, the plugins and the
# interpreter's vocabulary are also objects" — and the services, the plugins and
# the vocabulary are what no route reaches YET (items 13, 15 and 16 own the
# screens that will). They are handed over all the same, for the reason seven
# handed over the prose layer: they are entries the folder never had the CHANCE
# to carry, and the administrator's role is the one that must.
GROWN = (
    "service:read",
    "service:edit",
    "plugin:read",
    "plugin:edit",
    "vocabulary:read",
    "vocabulary:edit",
)


def _catalogue(ask: Ask | None) -> list[Report]:
    """Migration seven: the entries item 11's first slice introduced."""
    return _hand_over(ADDED)


def _objects(ask: Ask | None) -> list[Report]:
    """Migration eight: the objects §4 names that no route reaches yet."""
    return _hand_over(GROWN)


# What THIS release adds to declarations that are ALREADY on disk — migration
# nine. It is written the way a declaration writes itself, so what a release
# adds to a table is readable as the slice of that table it is, and the merge
# never has to be told which kind of key it is holding.
#
# The additions are DATED: they are what earlier swaps changed in silence,
# before the machinery existed to carry them. A folder that ran those releases
# heard nothing — the seed writes only the declarations that are ABSENT, and
# these tables were already there — so the folder that exists catches up here,
# on the first start after THIS swap. `type` a field was born without is what
# item 15's first slice added to five fields of three tables; the `lifecycle`
# is what item 6 added to `task` and `project`, and a folder that never heard
# it cannot close a row.
#
# A published migration is never edited, so the next release that grows a
# declaration brings its own step and its own additions, and this one goes on
# meaning what it meant on the day it shipped.
EXTENDED: dict[str, dict] = {
    "task": {
        "fields": {
            "since": {"type": "day"},
            "deadline": {"type": "day"},
            "modifications": {"append": {"type": "instant"}},
        },
        "lifecycle": {
            "cancel": {
                "status": "cancelled",
                "reason": {"into": "desc", "text": "table.closed.reason"},
                "reason_required": True,
            }
        },
    },
    "project": {
        "fields": {"since": {"type": "day"}},
        "lifecycle": {
            "cancel": {
                "status": "cancelled",
                "reason": {"into": "desc", "text": "table.closed.reason"},
                "reason_required": True,
            }
        },
    },
    "reminder": {
        "fields": {
            "on_date": {"type": "day"},
            "since": {"type": "day"},
        }
    },
}


def _declarations_extended(ask: Ask | None) -> list[Report]:
    """Migration nine: the declaration keys earlier swaps added in silence."""
    return _extend(EXTENDED)


def _versioning(ask: Ask | None) -> list[Report]:
    """Migration ten: the folder gains the repository AT drives (§3, item 30).

    A folder that already exists when versioning arrives is exactly the folder
    this machinery is for: the person's whole life is in it and none of it has a
    yesterday, so the repository is born here, on the first start after the
    swap.

    It answers with NO report, and that is not an omission: `versioning` is what
    says what happened — the born sentence, or the two ways out when git is not
    on the machine — and a report composed here would be the second wording of
    the same fact. What belongs to the migration is the moment, and it is this
    one.
    """
    versioning.start(ask)
    return []
