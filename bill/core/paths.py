"""The Working Folder, and the paths that live inside it.

The rule comes from §3 (Código e delivery): the folder the binary was opened in
is the binary's folder, and that folder is the Working Folder.

**The name on disk is the face; the machine reads the internal name.** `app`,
`data`, `prose`, `projects` and `shared` are the product's words — the engine
branches on them and on nothing a person says. What a person reads is the
localized name, and it is a DECLARATION of the table below, never an `if` in the
code that acts: the same rule that makes a table's id `task` while the name on
screen comes from `i18n`.

A folder that refused a rename keeps the name it had, so the resolution accepts
every name the product has ever given it — the active language's first, then the
other language's, then the internal name itself. Without that, declining a
rename would break Bill instead of leaving the cost with whoever declined.

`BILL_ROOT` overrides the resolution so a test — or a developer running
`python3 -m bill` from the checkout — can aim the engine somewhere else without
moving anything. It is the only environment variable that decides where Bill
writes; nothing here creates a directory. Creation belongs to `boot`, which asks
first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_ENV = "BILL_ROOT"

# Every internal name, and the folder it is spelled with in each language. One
# home: a name that is added here gains its resolution, its birth and its
# migration at once, and no surface has to learn it.
NAMES: dict[str, dict[str, str]] = {
    "app": {"pt_BR": "App", "en_US": "App"},
    "data": {"pt_BR": "Tabelas", "en_US": "Tables"},
    "prose": {"pt_BR": "Arquivos", "en_US": "Files"},
    "projects": {"pt_BR": "Projetos", "en_US": "Projects"},
    "shared": {"pt_BR": "Compartilhada", "en_US": "Shared"},
}

# The instance folder, and it is NOT localized — deliberately. The language
# itself is recorded inside it (`i18n/active`), so a name that moved with the
# language would be a folder the resolution could not find before it knew the
# language. `App/` is the same word in both, which is what makes that possible.
INSTANCE = "App"

# What the instance folder was called before, newest first. `boot` and the first
# migration read this list: a folder that carries one of these and no `App/` is
# a folder that has not migrated, never a folder that is new.
LEGACY_INSTANCE = (".bill", "app")


def working_folder() -> Path:
    """Where Bill is running. Resolved fresh on every call, never cached."""
    override = os.environ.get(ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        # Packaged as the single binary: the binary IS the folder's owner, so
        # the folder is wherever the binary sits — not where it was called from.
        return Path(sys.executable).resolve().parent
    # Running from source: the checkout is the Working Folder.
    return Path.cwd().resolve()


def candidates(internal: str) -> tuple[str, ...]:
    """Every name the folder may carry, in the order the resolution tries."""
    names = NAMES[internal]
    active = active_language()
    ordered = [names[active]] if active in names else []
    ordered += [name for code, name in sorted(names.items()) if code != active]
    if internal not in ordered:
        # The internal name itself, last: a folder hand-created under it, or one
        # born before this table existed, is still the folder it names.
        ordered.append(internal)
    return tuple(ordered)


def folder(internal: str) -> Path:
    """The folder the internal name points at, as this folder spells it.

    The first name that EXISTS wins, so a folder that declined a rename answers
    under the name it kept. When none exists the active language's name is
    returned — that is where a folder about to be born is written.
    """
    root = working_folder()
    for name in candidates(internal):
        if (root / name).is_dir():
            return root / name
    return root / NAMES[internal][active_language()]


def instance_dir() -> Path:
    """The folder the instance's own state lives in — `App/`.

    Resolved by what is ON DISK and never by the active language, because the
    language lives inside it. A folder carrying a legacy name is the SAME
    instance, and finding it is what lets the first migration run at all: a
    folder with `.bill/` on disk must read as a folder that has not migrated,
    never as a folder that is new.
    """
    root = working_folder()
    if (root / INSTANCE).is_dir():
        return root / INSTANCE
    for name in LEGACY_INSTANCE:
        if (root / name).is_dir():
            return root / name
    return root / INSTANCE


def app_dir() -> Path:
    """The instance folder — `App/` (§4). The internal name is `app`."""
    return instance_dir()


def settings_file() -> Path:
    """`App/settings.json` — the presence of this file is what makes a folder
    a Working Folder, so `boot` asks whenever it is missing."""
    return app_dir() / "settings.json"


def i18n_dir() -> Path:
    return app_dir() / "i18n"


def active_language_file() -> Path:
    """`App/i18n/active` — the only translation artifact the folder keeps
    (§4): the catalogs themselves are packed into the binary."""
    return i18n_dir() / "active"


def data_dir() -> Path:
    """`Tabelas/` — the tables, as `.jsonl`, and their schemas under `schema/`."""
    return folder("data")


def prose_dir() -> Path:
    """`Arquivos/` — every file that is not structured data (§4)."""
    return folder("prose")


def projects_dir() -> Path:
    """`Projetos/` — what belongs to a project, under that project's name."""
    return folder("projects")


def shared_dir() -> Path:
    """`Compartilhada/` — the files shared with other people. Named here, and
    treated later: the transport, and what this does to the backup promise, are
    the session that comes after (§3)."""
    return folder("shared")


def active_language() -> str:
    """The active code — resolved by `i18n`, imported here to keep `paths` the
    only layer that knows a folder has a name at all."""
    from bill import i18n

    return i18n.active_code()
