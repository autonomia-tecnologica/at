""".bill/settings.json — the instance's key-value configuration (§4).

Deliberately not the home of the active language: that lives in
`.bill/i18n/active`, because the catalogs are packed into the binary and only
the choice is the folder's. This file carries what is neither translation nor
table.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from bill.core import files, paths

# The shape version. It exists so a later release can migrate a folder instead
# of guessing at it — the first run after an update is when structure changes
# are applied (MANIFESTO.md §3).
SCHEMA = 1


def exists() -> bool:
    return paths.settings_file().is_file()


def load() -> dict[str, Any]:
    """The settings as they are on disk; `{}` for a folder not yet configured.

    A corrupt file is reported, never silently replaced: rewriting it would
    destroy whatever a person had put there.
    """
    try:
        text = paths.settings_file().read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        settings = json.loads(text)
    except JSONDecodeError as error:
        raise SettingsError(f"{paths.settings_file()}: {error}") from error
    if not isinstance(settings, dict):
        raise SettingsError(f"{paths.settings_file()}: not a JSON object")
    return settings


def save(settings: dict[str, Any]) -> None:
    text = json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    files.atomic_write_text(paths.settings_file(), text)


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


class SettingsError(Exception):
    """The settings file exists but cannot be read as one."""
