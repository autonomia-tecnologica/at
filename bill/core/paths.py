"""The Working Folder, and the paths that live inside it.

The rule is the README's (§3, Código e delivery): the folder the binary was
opened in is the binary's folder, and that folder is the Working Folder.

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


def app_dir() -> Path:
    """`app/` — the instance's configuration and per-service state (§4)."""
    return working_folder() / "app"


def settings_file() -> Path:
    """`app/settings.json` — the presence of this file is what makes a folder
    a Working Folder, so `boot` asks whenever it is missing."""
    return app_dir() / "settings.json"


def i18n_dir() -> Path:
    return app_dir() / "i18n"


def active_language_file() -> Path:
    """`app/i18n/active` — the only translation artifact the folder keeps
    (§4): the catalogs themselves are packed into the binary."""
    return i18n_dir() / "active"


def data_dir() -> Path:
    """`data/` — the tables, as `.jsonl`, and their schemas under `schema/`."""
    return working_folder() / "data"


def prose_dir() -> Path:
    """`prose/` — every file that is not structured data (§4)."""
    return working_folder() / "prose"
