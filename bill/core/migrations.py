"""Migrations: a folder that already exists changes under it.

Bill is one binary, and updating is replacing it inside the folder. When a
release changes the STRUCTURE of the folder — a folder's name, a field in a
declaration, where a file lives — the folder that is already on disk has to
catch up on the first start after the swap. That catch-up is a migration (§3,
Código e delivery).

Three rules, and they are §3's:

- the folder records **how far it has migrated**, and the stamp lives here, with
  the rest of what Bill writes — never inside the published declaration, because
  the declaration is shared and the instance is not;
- every release that changes structure **carries its migration**, and it runs on
  the first start after the binary is replaced;
- a migration **never overwrites what is already there**: it adds what is
  missing and reports what it skipped, so a person's edit wins a collision and
  Bill says so instead of choosing.

A published migration is immutable — folders have already run it, and a fix is
the next migration, never an edit to one that shipped.

**A migration handles its own impact and decides what to do with it.** Naming a
folder moves a path, and what a person points at from OUTSIDE the folder — a
vault of another tool, a backup script — is what breaks later, when that other
tool is opened. That is why the rename that touches the person's own folders
asks before it moves, and the two that touch only Bill's own folder do not.

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

from bill.core import files, paths, settings
from bill.i18n import tr

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
    read as a folder that is NEW (§3, item 5): Bill offered to create a Working
    Folder over the one that was already there.

    The impact is nil outside — `.bill/` is a hidden folder Bill made for itself
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

    The impact is nil outside — the folder is Bill's own — so this one does not
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


def _folders_in_the_language(ask: Ask | None) -> list[Report]:
    """`data/` → `Tabelas/`, `prose/` → `Arquivos/` — and the birth of the two
    that are named here and filled later.

    This one ASKS, and it is the only one that does: the folders it renames are
    the person's. `Arquivos/` is where the files they keep live, and what other
    tools point at them breaks — later, when that tool is opened. Bill says it
    before and not after, and whoever declines keeps the name they had; the
    resolution finds it under every spelling, and the cost is that the folder
    speaks a language the screen does not.
    """
    moves, collisions = _moves()
    report: list[Report] = []
    if collisions:
        report.append(("boot.migration.folders.collision", {"names": _spelled(collisions)}))
    elif moves:
        if _confirm(ask, moves):
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
    """What has to move, and what cannot be moved because two spellings exist."""
    root = paths.working_folder()
    language = paths.active_language()
    moves: list[tuple[str, Path, Path]] = []
    collisions: list[str] = []
    for internal in ("data", "prose"):
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
    """
    root = paths.working_folder()
    language = paths.active_language()
    born: list[Path] = []
    for internal in ("projects", "shared"):
        target = root / paths.NAMES[internal][language]
        if not target.exists():
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


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, _legacy_instance),
    Migration(2, _capitalized_instance),
    Migration(3, _folders_in_the_language),
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
    for migration in MIGRATIONS:
        if migration.ident in done:
            continue
        for report in migration.step(ask):
            _say(report)
            said.append(report)
        _mark(migration.ident)
    return said


# -------------------------------------------------------- the language ---

DECISION = "folders"


def offer_language(ask: Ask | None) -> list[Report]:
    """The folders take the active language's names — offered, never automatic.

    Not a migration: a migration runs once, and the language can change again
    tomorrow. What is remembered is the DECISION, so whoever declined the rename
    is asked again only when the language changes — not on every start.

    It is offered only for the language the FOLDER chose. An override in the
    environment is not the folder's, and renaming the person's folders to follow
    something as temporary as `$BILL_LANG` would be the opposite of the promise.
    """
    from bill import i18n

    language = paths.active_language()
    if settings.get(DECISION) == language:
        return []
    if i18n.active_origin() != "folder":
        return []

    said = _folders_in_the_language(ask)
    for report in said:
        _say(report)
    settings.save({**settings.load(), DECISION: language})
    return said
