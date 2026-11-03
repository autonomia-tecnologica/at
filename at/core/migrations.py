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
tool is opened. That is why the rename that follows a language CHANGE asks
before it moves: the language is the folder's, and declining is a cost the
person chooses. The rename that adopts the product's own new name does not ask —
there is no choice on the other side —, and neither do the moves that touch only
AT's own folder.

**A migration runs once; a language does not.** Changing the language renames
the folders again, so that offer is NOT a migration — it is `offer_language`,
and what the settings remember is the DECISION, so whoever declined is asked
again only when the language changes.
"""

from __future__ import annotations

import json

from at.core import (
    files,
    paths,
    settings,
    versioning,
)
from at.core.migrations_base import (  # noqa: F401
    STAMP,
    YES,
    Ask,
    Migration,
    Report,
    _mark,
    applied,
    is_yes,
    stamp_file,
)
from at.core.migrations_declarations import (  # noqa: F401
    ADDED,
    GROWN,
    INTRODUCED,
    _catalogue,
    _declarations,
    _declarations_extended,
    _objects,
    _versioning,
)
from at.core.migrations_engine import _extend, _hand_over  # noqa: F401
from at.core.migrations_folders import (  # noqa: F401
    _agent_note,
    _birth,
    _capitalized_instance,
    _confirm,
    _folders_in_the_language,
    _harness_folder,
    _legacy_instance,
    _moves,
    _prose_in_its_new_name,
    _remove_agent_note,
    _spelled,
)
from at.core.migrations_later import (  # noqa: F401
    HOOKS_PERMISSIONS,
    JEV_CACHE,
    LATE_PERMISSIONS,
    NOTE_PERMISSIONS,
    NOTES,
    PROJECT_DESC_LIMIT,
    REMINDER_CLOSED,
    STRONGBOX_GRANTED,
    _clock,
    _convert_folder,
    _edited_at,
    _hooks,
    _late_permissions,
    _merge_into,
    _notes,
    _once_needs_a_day,
    _project_desc_limit,
    _remark_renamed,
    _reminder_closed,
    _reminder_hour,
    _services_under_their_house,
    _silent_additions,
    _strongbox_folder,
    _strongbox_permission,
    _strongbox_permission_renamed,
)
from at.core.migrations_tables import (  # noqa: F401
    AUDIT_PERMISSIONS,
    AUDITS,
    JOB_PERMISSIONS,
    JOBS,
    SCANNER_PERMISSIONS,
    SECRET_PERMISSIONS,
    SECRETS,
    _audit_threshold,
    _audits,
    _backlog_order,
    _fill_missing,
    _jobs,
    _scanner,
    _secrets,
    _tags,
)
from at.i18n import tr


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
    Migration(19, _strongbox_folder),
    Migration(20, _strongbox_permission),
    Migration(21, _edited_at),
    Migration(22, _convert_folder),
    Migration(23, _silent_additions),
    Migration(24, _project_desc_limit),
    Migration(25, _strongbox_permission_renamed),
    Migration(26, _services_under_their_house),
    Migration(27, _reminder_hour),
    Migration(28, _once_needs_a_day),
    Migration(29, _hooks),
    Migration(30, _notes),
    Migration(31, _prose_in_its_new_name),
    Migration(32, _reminder_closed),
    Migration(33, _remove_agent_note),
    Migration(34, _late_permissions),
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
