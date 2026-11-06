"""Extensions (§8): the manifest, the canonical hash and the review.

The product SEES what is on disk (`App/extensions/<id>/`) and keeps the state of
each one in `App/extensions.json`; copying a folder in makes AT see it, and
`install` is the act that counts. This slice is the core only: no surface, no
execution.

- **The manifest** (`manifest.json`) declares `id` (the folder's name), `name`,
  `version`, `author_note` and `class`: `data` carries `alters` (ids of the
  product's permissions, never asked as a read permission), `frontend` carries
  `contract` and `permissions` as `table:action`.
- **The hash is of the CONTENT**: every file, in canonical (sorted) order of its
  relative path, with no mtime, no mode and no empty folder. One byte changed,
  another hash.
- **The review** is `read` | `ai` | `trust`, bound to the hash it was made on:
  when the folder no longer hashes to it, the review is gone.
- **Blockers** are listed, never raised: a missing or invalid manifest, a `.js`
  file anywhere in the folder, an unknown class, a table that does not exist or
  an action that is not one of `ACTIONS`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timezone
from pathlib import Path
from typing import Any

from at.core import clock, paths
from at.data import schema

MANIFEST = "manifest.json"
STATE_FILE = "extensions.json"
FOLDER = "extensions"

REVIEWS = ("read", "ai", "trust")
CLASSES = ("data", "frontend")
# The actions a frontend plugin may ask of a table (§8).
ACTIONS = ("list", "create", "update", "delete")

# Blocker codes. The surfaces translate them (i18n); the core only names them.
MISSING_MANIFEST = "manifest_missing"
INVALID_MANIFEST = "manifest_invalid"
SCRIPT = "script_present"
UNKNOWN_CLASS = "class_unknown"
UNKNOWN_TABLE = "table_unknown"
INVALID_ACTION = "action_invalid"


class ExtensionError(Exception):
    """A refusal of `install`: unknown extension, unknown review or blockers."""


def extensions_dir() -> Path:
    """`App/extensions/` — where the folders are copied to."""
    return paths.app_dir() / FOLDER


def state_file() -> Path:
    """`App/extensions.json` — the review state of each installed extension."""
    return paths.app_dir() / STATE_FILE


def digest(folder: Path) -> str:
    """The canonical hash of a folder: content only, in canonical order."""
    sha = hashlib.sha256()
    files = sorted(
        (p.relative_to(folder).as_posix(), p)
        for p in folder.rglob("*")
        if p.is_file()
    )
    for name, path in files:
        data = path.read_bytes()
        encoded = name.encode("utf-8")
        # Length-framed, so no file can be spelled to look like another split.
        sha.update(len(encoded).to_bytes(8, "big") + encoded)
        sha.update(len(data).to_bytes(8, "big") + data)
    return sha.hexdigest()


def _state() -> dict[str, dict]:
    try:
        loaded = json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _blockers(folder: Path) -> tuple[dict | None, list[str]]:
    """The manifest (or None) and every blocker the folder carries."""
    found: list[str] = []
    if any(p.is_file() and p.suffix.lower() == ".js" for p in folder.rglob("*")):
        found.append(SCRIPT)
    path = folder / MANIFEST
    if not path.is_file():
        return None, [MISSING_MANIFEST, *found]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, [INVALID_MANIFEST, *found]
    base = ("id", "name", "version", "author_note")
    if (
        not isinstance(manifest, dict)
        or manifest.get("id") != folder.name
        or not all(_text(manifest.get(key)) for key in base)
    ):
        return None, [INVALID_MANIFEST, *found]
    kind = manifest.get("class")
    if kind not in CLASSES:
        return manifest, [*found, UNKNOWN_CLASS]
    if kind == "data":
        alters = manifest.get("alters")
        if not isinstance(alters, list) or not all(_text(a) for a in alters):
            return manifest, [*found, INVALID_MANIFEST]
        return manifest, found
    permissions = manifest.get("permissions")
    if not _text(manifest.get("contract")) or not isinstance(permissions, list):
        return manifest, [*found, INVALID_MANIFEST]
    for entry in permissions:
        table, sep, action = entry.partition(":") if isinstance(entry, str) else ("", "", "")
        if not sep:
            found.append(INVALID_MANIFEST)
        elif schema.of(table) is None:
            found.append(UNKNOWN_TABLE)
        elif action not in ACTIONS:
            found.append(INVALID_ACTION)
    return manifest, list(dict.fromkeys(found))


def inspect(extension: str) -> dict:
    """What the core sees of one folder: manifest, hash, review and blockers.

    `review` is the installed one when it is still bound to the folder's hash,
    and None otherwise (never installed, or a byte changed since).
    """
    folder = extensions_dir() / extension
    manifest, blockers = _blockers(folder)
    current = digest(folder)
    entry = _state().get(extension)
    review = None
    if isinstance(entry, dict) and entry.get("hash") == current:
        review = entry.get("review") if entry.get("review") in REVIEWS else None
    return {
        "id": extension,
        "manifest": manifest,
        "hash": current,
        "review": review,
        "blockers": blockers,
    }


def scan() -> list[dict]:
    """Every folder in `App/extensions/`, in canonical order."""
    root = extensions_dir()
    if not root.is_dir():
        return []
    return [inspect(p.name) for p in sorted(root.iterdir()) if p.is_dir()]


def install(extension: str, review: str) -> dict:
    """Bind a review to the folder's current hash and record it."""
    if review not in REVIEWS:
        raise ExtensionError(f"unknown review: {review}")
    if not (extensions_dir() / extension).is_dir():
        raise ExtensionError(f"unknown extension: {extension}")
    seen = inspect(extension)
    if seen["blockers"]:
        raise ExtensionError(f"blocked: {', '.join(seen['blockers'])}")
    entry = {
        "hash": seen["hash"],
        "review": review,
        "at": clock.now().astimezone(timezone.utc).isoformat(),
    }
    state = _state()
    state[extension] = entry
    path = state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry
