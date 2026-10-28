"""The migrations of the folder itself — its names, its language, the note and
the Harness it carries.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

from pathlib import Path

from at.core import (
    files,
    paths,
)
from at.core.migrations_base import Ask, Report, is_yes
from at.i18n import tr

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
    """`data/` → `Tabelas/`, `prose/` → `Biblioteca/` — and the birth of the two
    that are named here and filled later.

    This one ASKS, and it is the only one that does: the folders it renames are
    the person's. `Biblioteca/` is where the files they keep live, and what other
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
            for _internal, current, target in moves:
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
        # Only the CURRENT names: a retired face is migration 31's subject, and
        # offering its rename here too would ask twice for one move — and the
        # answer "no" would then apply to a move that happens regardless.
        found = [
            root / name
            for name in paths.current_candidates(internal)
            if (root / name).is_dir()
        ]
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
    """`data → Tabelas, prose → Biblioteca` — or a bare list, for a birth."""
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


def _prose_in_its_new_name(ask: Ask | None) -> list[Report]:
    """`Arquivos/` → `Biblioteca/` (`Files/` → `Library/`) — the folder's new
    name, and the person already decided it.

    This one does NOT ask. What it moves is the face the product itself gave the
    person's folder, and the name on the other side is the product's decision,
    not a choice forced on them: the previous name was the product's too, and
    this is the same folder under the name the product now writes. There is
    nothing of the person's to weigh.

    **Only the ACTIVE language's face moves.** A folder in `pt_BR` carrying
    `Files/` is a folder that declined a language rename in the past; it is not
    this migration's, and the resolution still finds it (`paths.candidates`).
    Renaming it to `Library/` would be following a language the folder is not
    speaking.

    **It is a migration and not `offer_language`.** That offer is silent once
    the language decision is recorded — which is exactly the state of every
    existing folder — so the rename would never be offered to them. The decision
    of the new name is the product's, and it has to reach a folder that already
    exists without depending on a question about language.

    A collision is reported and NOT resolved: two folders for one internal name
    are the person's to settle, and choosing one would hide the other. A folder
    that already has the new name has nothing to do.
    """
    language = paths.active_language()
    former = paths.FORMER["prose"].get(language)
    if not former:
        return [("boot.migration.prose.kept", {})]
    root = paths.working_folder()
    old = root / former
    target = root / paths.NAMES["prose"][language]
    if not old.is_dir():
        return [("boot.migration.prose.kept", {})]
    if target.exists():
        return [("boot.migration.prose.collision", {})]
    old.rename(target)
    return [("boot.migration.prose.moved", {"names": f"{former} → {target.name}"})]
