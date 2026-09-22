"""The UI language — the source of truth for every text a person reads (§3).

Texts live in **blocks** under `blocks/`: one file per subject, both languages
side by side. A single `pt_BR.json` grows into a file that has to be read whole
to find one string, and reading it whole is the cost the README forbids. The
block's filename is the namespace of its keys — `blocks/boot.json` holds
`first_run.confirm`, read as `boot.first_run.confirm` — so a key names its
subject twice only if the subject deserves it.

Keys are **stable ids**, never the English sentence: renaming a text must not
rename a key. (The PoC derived keys from the sentence, so editing a message
silently broke every reference to it.)

Resolution order: `$BILL_LANG` → `app/i18n/active` → the OS locale → `en_US`.
Only the choice is the folder's; the catalogs travel inside the binary.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources

from bill.core import paths

# The language every text is written in first; `en_US` is its translation (§3).
# It is the fallback when the active language is missing a key: a person reading
# a translation deserves the original over a raw key.
SOURCE = "pt_BR"
SUPPORTED = ("pt_BR", "en_US")
DEFAULT = "en_US"

LANG_ENV = "BILL_LANG"
_BLOCKS = "blocks"
SUFFIX = ".json"


def tr(key: str, **kw: object) -> str:
    """The text for `key` in the active language.

    Falls back to the source language, then to the key itself — a missing
    translation is visible, never silent.
    """
    for language in (active_code(), SOURCE):
        text = _catalog(language).get(key)
        if text is not None:
            return text.format(**kw) if kw else text
    return key


def text(key: str, language: str) -> str:
    """The text for `key` in a NAMED language.

    The page is handed a label in EVERY supported language at once, so switching
    the language on screen costs no request — and the server keeps owning the
    words, which is the rule (§3).
    """
    for candidate in (language, SOURCE):
        found = _catalog(candidate).get(key)
        if found is not None:
            return found
    return key


def labels(key: str) -> dict[str, str]:
    """One key, written out in every supported language."""
    return {code: text(key, code) for code in SUPPORTED}


def active_code() -> str:
    return _resolve()[0]


def active_origin() -> str:
    """Where the active language came from: `env`, `folder`, `locale`, `default`."""
    return _resolve()[1]


def write_active(code: str) -> None:
    """Record the chosen language in the Working Folder."""
    if code not in SUPPORTED:
        raise ValueError(f"unsupported language: {code}")
    paths.i18n_dir().mkdir(parents=True, exist_ok=True)
    paths.active_language_file().write_text(code + "\n", encoding="utf-8", newline="\n")
    reset()


def reset() -> None:
    """Drop the cached resolution and catalogs — for tests, and for `write_active`."""
    _resolve.cache_clear()
    _catalog.cache_clear()


def keys_out_of_step() -> dict[str, dict[str, list[str]]]:
    """Per block, the keys one language has and another does not.

    A translation that lags is a defect, not a state: this is what the test
    suite reads to say so.
    """
    out_of_step: dict[str, dict[str, list[str]]] = {}
    for block in _block_files():
        data = json.loads(block.read_text(encoding="utf-8"))
        present = {language: set(data.get(language, {})) for language in SUPPORTED}
        every = set().union(*present.values())
        missing = {
            language: sorted(every - present[language])
            for language in SUPPORTED
        }
        missing = {language: keys for language, keys in missing.items() if keys}
        if missing:
            out_of_step[block.name[: -len(SUFFIX)]] = missing
    return out_of_step


@lru_cache(maxsize=None)
def _resolve() -> tuple[str, str]:
    override = os.environ.get(LANG_ENV, "").strip()
    if override in SUPPORTED:
        return override, "env"
    stored = _stored()
    if stored in SUPPORTED:
        return stored, "folder"
    from_locale = _from_locale()
    if from_locale:
        return from_locale, "locale"
    return DEFAULT, "default"


@lru_cache(maxsize=None)
def _catalog(language: str) -> dict[str, str]:
    catalog: dict[str, str] = {}
    for block in _block_files():
        data = json.loads(block.read_text(encoding="utf-8"))
        namespace = block.name[: -len(SUFFIX)]
        for key, text in data.get(language, {}).items():
            catalog[f"{namespace}.{key}"] = text
    return catalog


def _block_files() -> list:
    directory = resources.files(__name__) / _BLOCKS
    return sorted(
        (entry for entry in directory.iterdir() if entry.name.endswith(SUFFIX)),
        key=lambda entry: entry.name,
    )


def _stored() -> str | None:
    try:
        return paths.active_language_file().read_text(encoding="utf-8").strip() or None
    except OSError:
        # A folder not yet configured has no choice recorded, which is not an
        # error — it is the state `boot` is about to resolve.
        return None


def _from_locale() -> str | None:
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(variable, "")
        if not raw:
            continue
        language = raw.split(".")[0].split("_")[0].lower()
        if language == "pt":
            return SOURCE
        if language == "en":
            return "en_US"
    return None
