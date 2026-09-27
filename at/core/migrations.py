"""Migrations: a folder that already exists changes under it.

AT is one binary, and updating is replacing it inside the folder. When a
release changes the STRUCTURE of the folder — a folder's name, a field in a
declaration, where a file lives — the folder that is already on disk has to
catch up on the first start after the swap. That catch-up is a migration (§3,
Código e delivery).

Three rules, and they are §3's:

- the folder records **how far it has migrated**, and the stamp lives here, with
  the rest of what AT writes — never inside the published declaration, because
  the declaration is shared and the instance is not;
- every release that changes structure **carries its migration**, and it runs on
  the first start after the binary is replaced;
- a migration **never overwrites what is already there**: it adds what is
  missing and reports what it skipped, so a person's edit wins a collision and
  AT says so instead of choosing.

A published migration is immutable — folders have already run it, and a fix is
the next migration, never an edit to one that shipped.

**A migration handles its own impact and decides what to do with it.** Naming a
folder moves a path, and what a person points at from OUTSIDE the folder — a
vault of another tool, a backup script — is what breaks later, when that other
tool is opened. That is why the rename that touches the person's own folders
asks before it moves, and the two that touch only AT's own folder do not.

**A migration runs once; a language does not.** Changing the language renames
the folders again, so that offer is NOT a migration — it is `offer_language`,
and what the settings remember is the DECISION, so whoever declined is asked
again only when the language changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from at.core import (
    actors,
    files,
    paths,
    permissions,
    settings,
    tables,
    versioning,
)
from at.data import schema, store
from at.i18n import tr

# The stamp, inside the instance folder: the ids this folder has already run.
STAMP = "migrations"

# Both spellings answer the same question — the language of the prompt is the
# active one, and whoever answers is free to type either.
YES = frozenset({"s", "sim", "y", "yes"})

Ask = Callable[[str], str]
Report = tuple[str, dict]


def is_yes(answer: str) -> bool:
    return answer.strip().lower() in YES


@dataclass(frozen=True)
class Migration:
    ident: int
    step: Callable[[Ask | None], list[Report]]


def stamp_file() -> Path:
    return paths.instance_dir() / STAMP


def applied() -> list[int]:
    """The ids this folder has already run, in order. A stamp nobody can read
    reads as none: the migrations that follow would then simply run again, and
    each one is written to leave alone what is already right."""
    try:
        raw = files.read_json(stamp_file(), default=[])
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    return sorted({value for value in raw if isinstance(value, int) and not isinstance(value, bool)})


def _mark(ident: int) -> None:
    done = applied()
    if ident in done:
        return
    done.append(ident)
    body = json.dumps(sorted(done), ensure_ascii=False) + "\n"
    files.atomic_write_text(stamp_file(), body)


def record() -> None:
    """Stamp every migration as run, without running any of them.

    A folder born by this release is already in the shape this release declares,
    so it has nothing to catch up on — and saying so once, at birth, is what
    keeps the first start of an old folder different from the first start of a
    new one.
    """
    done = applied()
    body = json.dumps(sorted(set(done) | {item.ident for item in MIGRATIONS})) + "\n"
    files.atomic_write_text(stamp_file(), body)


# ------------------------------------------------------------ the migration ---


def _legacy_instance(ask: Ask | None) -> list[Report]:
    """`.bill/` → `app/` — the rename that shipped ahead of this machinery.

    It is migration number one because it is the smallest case the framework has
    to survive, and because a folder carrying `.bill/` and no `app/` used to
    read as a folder that is NEW (§3, item 5): AT offered to create a Working
    Folder over the one that was already there.

    The impact is nil outside — `.bill/` is a hidden folder AT made for itself
    and nobody points at — so this one does not ask. It moves, and says so.
    """
    root = paths.working_folder()
    old = root / ".bill"
    new = root / "app"
    if not old.is_dir():
        return [("boot.migration.legacy.kept", {})]
    if new.exists():
        # Two folders, one instance: choosing between them would silently adopt
        # the other's settings. Merging them is the person's call, not a
        # migration's.
        return [("boot.migration.legacy.collision", {})]
    old.rename(new)
    return [("boot.migration.legacy.moved", {})]


def _capitalized_instance(ask: Ask | None) -> list[Report]:
    """`app/` → `App/` — §3 writes `App/` now, and the folders follow the prose.

    The impact is nil outside — the folder is AT's own — so this one does not
    ask either. What it does have to handle is the FILESYSTEM: on macOS and
    Windows the two spellings are one name, so `App/` exists before there is
    anything to move. `samefile` tells "already the same folder" from "a second
    folder with that name", and only the second is a collision.
    """
    root = paths.working_folder()
    old = root / "app"
    new = root / "App"
    if not old.is_dir():
        return [("boot.migration.capital.kept", {})]
    if new.exists():
        try:
            if old.samefile(new):
                return [("boot.migration.capital.same", {})]
        except OSError:
            pass
        return [("boot.migration.capital.collision", {})]
    old.rename(new)
    return [("boot.migration.capital.moved", {})]


def _folders_in_the_language(ask: Ask | None, said_so: bool = False) -> list[Report]:
    """`data/` → `Tabelas/`, `prose/` → `Arquivos/` — and the birth of the two
    that are named here and filled later.

    This one ASKS, and it is the only one that does: the folders it renames are
    the person's. `Arquivos/` is where the files they keep live, and what other
    tools point at them breaks — later, when that tool is opened. AT says it
    before and not after, and whoever declines keeps the name they had; the
    resolution finds it under every spelling, and the cost is that the folder
    speaks a language the screen does not.

    **`said_so` is the person answering BEFORE being asked**, and it is the one
    thing that turns the question off: `at-cli lang <code> --include-app-folders`
    is a person typing the decision, which is what the offer exists to collect.
    It is still not automatic — nothing here moves without either an answer or a
    typed flag — and what it buys is a run with no terminal to answer in.

    **The move set is complete because the OFFER is what runs again.** This is
    migration three's step AND the engine of `offer_language`, which runs on
    every language change — so every folder that follows the language is in
    `_moves`, and not only the two that existed when migration three was
    published. For a folder that has NOT run it the change is nil: a folder that
    old carries neither `Projects/` nor `Compartilhada/` under any spelling, and
    `_birth` is what names them.
    """
    moves, collisions = _moves()
    report: list[Report] = []
    if collisions:
        report.append(("boot.migration.folders.collision", {"names": _spelled(collisions)}))
    elif moves:
        if said_so or _confirm(ask, moves):
            for internal, current, target in moves:
                current.rename(target)
            report.append(("boot.migration.folders.moved", {"names": _spelled(moves)}))
        else:
            report.append(("boot.migration.folders.declined", {"names": _spelled(moves)}))
    born = _birth()
    if born:
        report.append(("boot.migration.folders.born", {"names": _spelled(born)}))
    return report


def _moves() -> tuple[list[tuple[str, Path, Path]], list[str]]:
    """What has to move, and what cannot be moved because two spellings exist.

    EVERY folder whose name follows the language, and not only the two that hold
    the person's material today. `Projetos/` and `Compartilhada/` are named by
    the language as well, and a folder that changed language without them kept
    one spelling while an empty twin was born in the other — and `paths.folder`
    reads the active language's name first, so the twin is the folder AT would
    use and the one the person has is the one it stops reading. `Harness/` is
    NOT here, and it is the only one: its name is the same word in both
    languages, so `paths.candidates` spells it twice and `_moves` would report a
    collision with itself.
    """
    root = paths.working_folder()
    language = paths.active_language()
    moves: list[tuple[str, Path, Path]] = []
    collisions: list[str] = []
    for internal in ("data", "prose", "projects", "shared"):
        target = root / paths.NAMES[internal][language]
        found = [root / name for name in paths.candidates(internal) if (root / name).is_dir()]
        if len(found) > 1:
            # Two folders, one internal name: deciding between them is the
            # person's, and a migration that picked one would hide the other.
            collisions.append(internal)
        elif found and found[0] != target:
            moves.append((internal, found[0], target))
    return moves, collisions


def _birth() -> list[Path]:
    """`Projetos/` and `Compartilhada/`, born empty and named here.

    `Compartilhada/` is where the files shared with other people will live (§3);
    the transport, and what it does to the backup promise, are the session that
    comes after. `Projetos/` is where what belongs to a project goes — also a
    later session's, and both are born so the folder is whole on its own from
    the first run on.

    Born only where the folder carries NEITHER spelling. A folder that kept the
    old name — because it declined the rename, or because it was written before
    this name existed — must not gain an empty twin beside it: `paths.folder`
    answers with the active language's name first, so the twin would be read in
    place of the folder the person still has.
    """
    root = paths.working_folder()
    language = paths.active_language()
    born: list[Path] = []
    for internal in ("projects", "shared"):
        if any((root / name).is_dir() for name in paths.candidates(internal)):
            continue
        target = root / paths.NAMES[internal][language]
        target.mkdir(parents=True, exist_ok=True)
        born.append(target)
    return born


def _confirm(ask: Ask | None, moves: list[tuple[str, Path, Path]]) -> bool:
    """Say what moves and what that breaks, and wait for the answer."""
    names = _spelled(moves)
    print(tr("boot.migration.folders.notice", names=names))
    if ask is None:
        # No terminal to ask in means no rename: the folders are the person's,
        # and moving them where nobody could answer is not a decision.
        print(tr("boot.migration.folders.no_tty"))
        return False
    return is_yes(ask(tr("boot.migration.folders.confirm", names=names)))


def _spelled(entries) -> str:
    """`data → Tabelas, prose → Arquivos` — or a bare list, for a birth."""
    parts = []
    for entry in entries:
        if isinstance(entry, tuple):
            parts.append(f"{entry[1].name} → {entry[2].name}")
        elif isinstance(entry, Path):
            parts.append(entry.name)
        else:
            parts.append(entry)
    return ", ".join(parts)


def _agent_note(ask: Ask | None) -> list[Report]:
    """`AGENT.md` at the folder's root — the folder introducing itself.

    A folder born by this release already carries the note, because `boot` writes
    it where it lays the folder down; a folder that was already on disk when the
    note was decided does not, and this is the catch-up. It is a migration for
    the same reason a rename is: the STRUCTURE of the folder changed, and the
    folder that exists has to end up in the shape the release declares.

    The impact is nil outside — a new file at the root, and nothing points at it
    yet — and it never overwrites: a folder that already carries one keeps it,
    whoever wrote it. So this one does not ask.
    """
    note = paths.agent_note()
    if note.exists():
        return [("boot.migration.note.kept", {})]
    files.atomic_write_text(note, tr("folder.agent.body"))
    return [("boot.migration.note.written", {})]


def _harness_folder(ask: Ask | None) -> list[Report]:
    """`Harness/` — where what the agent loads lives (§2, item 25).

    Born named and empty, like `Projetos/` and `Compartilhada/`: the folder is
    whole on its own from the first run on, and what lands in it is whoever
    works in the folder's to put there. AT guarantees the place, nothing more.

    Migration THREE births the two it read off the retired environment, and a
    published migration is never edited — folders have already run it — so this
    one arrives as its own step rather than as a third name in that list. A
    folder that still owes migration three hears both, and a folder that has
    already run it hears only this.

    The impact is nil outside — a new empty folder at the root, and nothing
    points at it yet — so it does not ask.
    """
    target = paths.harness_dir()
    if target.exists():
        return []
    target.mkdir(parents=True, exist_ok=True)
    return [("boot.migration.folders.born", {"names": target.name})]


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


# The table THIS release introduces — what migration eleven names — and the
# permissions it answers. Both lists are explicit for the reason `INTRODUCED` is
# one: a published migration is never edited, so the next release that brings a
# system table brings its own step and its own names.
#
# The two permissions are the table's OWN and not the engine's six: `secret`
# declares `read` and `edit` in its declaration (`permissions.DECLARED`), so its
# listing is `secret:read` and its write is `secret:edit`. A role born before
# this swap carries neither — it was built from the catalogue of its own day —
# and the administrator's is the one that must, exactly as migrations seven and
# eight handed over theirs.
SECRETS = ("secret",)
SECRET_PERMISSIONS = ("secret:read", "secret:edit")


def _secrets(ask: Ask | None) -> list[Report]:
    """Migration eleven: the `secret` table, and the ceiling over it.

    A folder that already exists is the one this is for: the table that carries
    what AT USES has to arrive in it before anything can be sealed, and the
    declaration is written the way migration six writes one — only where it is
    ABSENT, so a `secret.json` a person edited stays theirs and a deletion stays
    a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`) — and the box the rows live in, `data/secrets.jsonl`, is born
    when the first secret is sealed and not here: an empty file that names
    nothing is a store a person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=SECRETS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(SECRET_PERMISSIONS)


# The table THIS release introduces — what migration twelve names — and the one
# permission it answers. Both lists are explicit for the reason `SECRETS` is: a
# published migration is never edited, so the next release that brings a system
# table brings its own step and its own names.
#
# The permission is the table's OWN and not one of the engine's six: `audit`
# declares `read` alone, so its listing and its record are `audit:read` and a
# creation, an edition and a deletion are not permissions it has. A role born
# before this swap carries none of it — it was built from the catalogue of its
# own day — and the administrator's is the one that must, exactly as migrations
# seven, eight and eleven handed over theirs.
AUDITS = ("audit",)
AUDIT_PERMISSIONS = ("audit:read",)


def _audits(ask: Ask | None) -> list[Report]:
    """Migration twelve: the `audit` table, and the ceiling over it.

    A folder that already exists is the one this is for: §3 makes every act that
    enters the core one line of a table that has to BE there when the first act
    arrives, and the declaration is written the way migration eleven writes one —
    only where it is ABSENT, so an `audit.json` a person edited stays theirs and
    a deletion stays a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`). The box the lines live in, `data/audits.jsonl`, is born with
    the first act and not here — an empty file that names nothing is a store a
    person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=AUDITS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(AUDIT_PERMISSIONS)


# What THIS release adds to a declaration that is ALREADY on disk — migration
# thirteen, and the same shape migration nine writes: the additions are written
# the way a declaration writes itself, so the merge never has to be told which
# kind of key it is holding.
#
# The addition is the field the audit line grew (§3, §4, item 15): the threshold
# that was in force when a demand ran. The line is born with it — a folder born
# by this release has it in `data/defaults/audit.json` — and a folder that is
# already here catches up on the first start after the swap, which is what makes
# the first act after an update carry the same line as every act after it.
AUDIT_THRESHOLD: dict[str, dict] = {
    "audit": {
        "fields": {
            "threshold": {
                "label": "table.audit.field.threshold",
                "filterable": True,
                "searchable": True,
            }
        }
    },
}


def _audit_threshold(ask: Ask | None) -> list[Report]:
    """Migration thirteen: the threshold the audit line carries.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration). Rows written before it carry no
    threshold and are read as they are stored — the field is not `required`, and
    a log that pretended an old line had one would be a log inventing history.
    """
    return _extend(AUDIT_THRESHOLD)


# The table THIS release introduces — what migration fourteen names — and the
# permissions it answers. Both lists are explicit for the reason `AUDITS` is: a
# published migration is never edited, so the next release that brings a system
# table brings its own step and its own names.
#
# The permissions are the object's OWN and not the engine's six: `job` answers a
# read, a run and the two halves of the approval, and `permissions.NARROWED`
# says so — a creation, an edition and a deletion are not permissions it has. A
# role born before this swap carries none of them, and the administrator's is
# the one that must, exactly as migrations seven, eight, eleven and twelve
# handed over theirs.
#
# **`job:approve` and `job:refuse` reach the administrator and no machine**, and
# that is the same reason §3 gives for `audit:read`: whoever can release a
# demand learns where the bar is, and an `agent` that could release its own
# waiting demand would have opened the door it was held behind.
JOBS = ("job",)
JOB_PERMISSIONS = ("job:read", "job:run", "job:approve", "job:refuse")


def _jobs(ask: Ask | None) -> list[Report]:
    """Migration fourteen: the `job` table, and the ceiling over it.

    A folder that already exists is the one this is for: the table that holds
    the demand that could not run has to BE there when the first demand waits,
    and the declaration is written the way migration twelve writes one — only
    where it is ABSENT, so a `job.json` a person edited stays theirs and a
    deletion stays a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`). The box the jobs live in, `data/jobs.jsonl`, is born with
    the first demand that waits and not here — an empty file that names nothing
    is a store a person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=JOBS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(JOB_PERMISSIONS)


# What THIS release adds to declarations that are ALREADY on disk — migration
# fifteen. It is the backlog moving into the tables, read off the declaration:
# the `project` gains the `priority` the queue is ordered by, the `planned`
# status that says "decided and not started", and the default order §4 names
# beside the default fields; the `task` gains the `project` column, which is
# what lets the listing say which item a slice belongs to.
#
# It is written the way migration nine writes one, and for the same reason: the
# additions are spelled as a declaration spells them, so the merge never has to
# be told which kind of key it is holding. `planned` lands at the END of the
# folder's `enum` and not where the bundled declaration puts it — the merge
# only ever ADDS, and a key inserted in the middle would be an edit to the
# person's file. The order the picker lists them in is cosmetic; the closed set
# is the same one either way.
BACKLOG: dict[str, dict] = {
    "project": {
        "columns": ["priority"],
        "sort": {"by": "priority", "direction": "desc", "then": "id"},
        "fields": {
            "priority": {
                "label": "table.project.field.priority",
                "filterable": True,
                "searchable": True,
                "enum": {
                    "low": "table.project.field.priority.low",
                    "medium": "table.project.field.priority.medium",
                    "high": "table.project.field.priority.high",
                    "critical": "table.project.field.priority.critical",
                },
                "default": "medium",
            },
            "status": {
                "enum": {"planned": "table.project.field.status.planned"},
                "show": ["planned"],
            },
        },
    },
    "task": {"columns": ["project"]},
}


def _fill_missing(table: str, field: str) -> list[str]:
    """As linhas que já existiam ganham o valor que a declaração dá ao campo novo.

    O motor JÁ lê um campo ausente como o padrão declarado quando ordena — é o
    que `tables._sort_key` faz —, e esta escrita põe na linha o mesmo valor que
    a leitura vinha supondo. O que se ganha é não haver duas verdades: a
    listagem mostra o que a ordem usa, em vez de uma coluna vazia ao lado de uma
    ordem que já decidiu.

    Nada é sobrescrito. Só a linha que NÃO tem o campo o recebe, e a que a pessoa
    já escreveu fica com o que ela escreveu — uma linha sem `priority` não é uma
    decisão, é uma linha mais velha que o campo. É o outro lado da regra de
    sempre: a migração acrescenta o que falta, e diz o que acrescentou.
    """
    default = schema.field(table, field).get("default")
    if default is None or schema.of(table) is None:
        return []
    filled: list[str] = []
    for row in store.load(table):
        if row.get(field) is not None:
            continue
        number = store.number_of(row)
        if number is None:
            continue
        tables.edit(table, number, {field: default})
        filled.append(tables.format_id(table, number))
    return filled


def _backlog_order(ask: Ask | None) -> list[Report]:
    """Migration fifteen: the fields the backlog needs to be a queue.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration). The rows it writes are the `priority`
    those projects never had the chance to carry — the very value the order was
    already reading off the declaration for them.
    """
    report = _extend(BACKLOG)
    filled = _fill_missing("project", "priority")
    if filled:
        report.append(("boot.migration.backlog.filled", {"names": ", ".join(filled)}))
    return report


# The permission THIS release grows the catalogue by — what migration sixteen
# grants. It is the act the `secret` declares of its OWN (item 51,
# `permissions.NARROWED`): the word reads the folder and says what it found, and
# a role born before this swap carries none of it — it was built from the
# catalogue of its own day —, exactly as migrations seven, eight, eleven, twelve
# and fourteen handed over theirs.
#
# It is the administrator's and nobody else's for now, and that is the same
# answer §3 gives for `audit:read`: the ceiling is written once, and the screens
# that move it (item 11) are the ones that hand it to another role.
SCANNER_PERMISSIONS = ("secret:scan",)


def _scanner(ask: Ask | None) -> list[Report]:
    """Migration sixteen: `secret scan`, and the ceiling over it.

    A folder that already exists is the one this is for: the word that says what
    the folder carries is the administrator's, and the row it wears was written
    from the catalogue of the day it was born — which did not name the act.

    It does not ask: the row is AT's own, and the change only ever ADDS
    (`_hand_over`). Nothing else about the folder changes — the act writes no row
    and needs no declaration of its own, and the `gitleaks` it calls is the
    person's machine's business and not the folder's.
    """
    return _hand_over(SCANNER_PERMISSIONS)


# What THIS release adds to a declaration that is ALREADY on disk — migration
# seventeen, and the same shape migrations nine and fifteen write: the additions
# are spelled as a declaration spells them, so the merge never has to be told
# which kind of key it is holding.
#
# The backlog stops being a project or a subproject and becomes a QUEUE OF TAGS:
# the tag is the FATIA, and the fatia is the set of tasks that carry the same
# one. The `task` gains the `tags` list and the column the listing shows it in.
# It is not `editable`: who writes a tag is the backlog session, and not the
# screen a person types into.
TAGS: dict[str, dict] = {
    "task": {
        "columns": ["tags"],
        "fields": {
            "tags": {
                "label": "table.task.field.tags",
                "type": "list",
                "filterable": True,
                "searchable": True,
                "default": [],
            }
        },
    },
}


def _tags(ask: Ask | None) -> list[Report]:
    """Migration seventeen: a task carries the tag the backlog is sliced by.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration).

    **No row is filled, and that is the decision — `_fill_missing` is NOT called
    here.** The default is an empty list, and a row without the field already
    READS as empty: the listing joins the list it finds, an absent field joins
    nothing, and both read as `—`. Writing `[]` into every task would be a
    migration rewriting the whole file to say what the read already says, and
    there is no second truth to settle — unlike `priority`, which the order was
    already reading off the declaration.
    """
    return _extend(TAGS)


# What THIS release adds to a declaration that is ALREADY on disk — migration
# eighteen, and the same shape migrations nine, fifteen and seventeen write.
#
# **The `job` gains the state the CLOCK drives** (§4, item 24): a folder born
# before the clock declares four states, and a job that comes round on its own
# has a fifth. The value is the last one in the enum and not the first, and that
# is not cosmetic — the merge only ever ADDS, so a value inserted before `done`
# would be an edit to the person's file, while appended it is the same list the
# bundled declaration now carries.
CLOCK: dict[str, dict] = {
    "job": {
        "fields": {
            "status": {
                "enum": {"scheduled": "table.job.field.status.scheduled"},
            }
        },
    },
}


def _clock(ask: Ask | None) -> list[Report]:
    """Migration eighteen: the `job` gains the state that says it rounds on its own.

    A folder that already exists is the one this is for: its declaration was
    written when a job could only WAIT, and the new state is what the engine
    reads to know which jobs the clock drives. Nothing about the rows changes —
    a job is `waiting` until a person answers it, and only a job DECLARED with a
    `when` is ever `scheduled` —, and nothing outside the folder points at the
    declaration (§3, migration).

    It does not ask, for the reason `_tags` gives: a declaration of the
    product's own.
    """
    return _extend(CLOCK)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, _legacy_instance),
    Migration(2, _capitalized_instance),
    Migration(3, _folders_in_the_language),
    Migration(4, _agent_note),
    Migration(5, _harness_folder),
    Migration(6, _declarations),
    Migration(7, _catalogue),
    Migration(8, _objects),
    Migration(9, _declarations_extended),
    Migration(10, _versioning),
    Migration(11, _secrets),
    Migration(12, _audits),
    Migration(13, _audit_threshold),
    Migration(14, _jobs),
    Migration(15, _backlog_order),
    Migration(16, _scanner),
    Migration(17, _tags),
    Migration(18, _clock),
)


def _say(report: Report) -> None:
    print(tr(report[0], **report[1]))


def run(ask: Ask | None = None) -> list[Report]:
    """Apply what this folder has not run yet, oldest first, saying each.

    Each migration is named AS IT HAPPENS, and not collected into a list to be
    printed at the end: one of them asks a question in the middle, and a report
    that arrives after the question it belongs to is a report out of order.

    A read-only run applies nothing: a verification pass must not move a folder
    any more than it may write a file, and the switch binds the engine, not the
    word that was typed.
    """
    if files.readonly():
        return []
    done = applied()
    said: list[Report] = []
    ran: list[int] = []
    for migration in MIGRATIONS:
        if migration.ident in done:
            continue
        for report in migration.step(ask):
            _say(report)
            said.append(report)
        _mark(migration.ident)
        ran.append(migration.ident)
    if ran:
        # The catch-up is a thing that changed the folder, and an action that
        # changes the folder ends in a version (§4, item 30). It is named by the
        # steps that ran, because that IS what changed. The step that gives the
        # folder its repository commits on its own — the stamp it leaves after
        # is what this one carries.
        versioning.commit(
            tr("versioning.commit.migrated", ids=", ".join(str(ident) for ident in ran))
        )
    return said


# -------------------------------------------------------- the language ---

DECISION = "folders"


def offer_language(ask: Ask | None, include_folders: bool = False) -> list[Report]:
    """The folders take the active language's names — offered, never automatic.

    Not a migration: a migration runs once, and the language can change again
    tomorrow. What is remembered is the DECISION, so whoever declined the rename
    is asked again only when the language changes — not on every start.

    It is offered only for the language the FOLDER chose. An override in the
    environment is not the folder's, and renaming the person's folders to follow
    something as temporary as `$AT_LANG` would be the opposite of the promise —
    the flag does not remove that guard, because the names have to match the
    language the screen is actually speaking.

    **`include_folders` is `at-cli lang <code> --include-app-folders`**, and what it
    turns off is the QUESTION and not the rule: the person typed the decision, so
    there is nothing left to ask, no terminal needed, and the memory of a past
    decline does not hold a second one back. The renames the engine already knew
    are what runs; a collision between two spellings of one folder is still the
    person's to resolve, and it is still reported instead of chosen.
    """
    from at import i18n

    language = paths.active_language()
    if settings.get(DECISION) == language and not include_folders:
        return []
    if i18n.active_origin() != "folder":
        return []

    said = _folders_in_the_language(ask, said_so=include_folders)
    for report in said:
        _say(report)
    settings.save({**settings.load(), DECISION: language})
    return said
