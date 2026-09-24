"""The vocabulary: the words a person uses, and the machine word each one names.

It is **data**, and it is packed inside the product beside the `i18n` blocks,
because translating vocabulary and translating text are the same job (§5). One
file per subject under `at/i18n/vocabulary/`, both languages side by side,
exactly as the blocks are written.

Where the line between data and code runs is item 15's own decision, and this
module is one half of it: the slang and jargon map is data (here), the mechanical
tolerance is algorithm (the normalizer), and the date, time and number grammar is
code (the grammar). So nothing in these files is conditional — a word whose
meaning depends on what is around it, `trem` being a thing in Minas and a train
elsewhere, is GRAMMAR and lives in the interpreter's code, never in data wearing
an `if` inside (item 16).

What this module does is read the files and merge them. What a word MEANS is the
canonical it names and nothing more: a table's machine word, a field's, an
action's, or a value of a closed vocabulary — every one of them a name that exists
somewhere else in the product, which is what the suite checks by name.

The one exception is the **particle** block: a connecting word means nothing, so
it names nothing, and it is written under a key of its own (`particles`) rather
than under `expressions` — which is exactly why the suite's gates, which read
`expressions` and nothing else, walk past it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from at import i18n

DIRECTORY = "vocabulary"
SUFFIX = ".json"


def files() -> list:
    """Every vocabulary file the product packs, in name order."""
    directory = resources.files(i18n) / DIRECTORY
    return sorted(
        (entry for entry in directory.iterdir() if entry.name.endswith(SUFFIX)),
        key=lambda entry: entry.name,
    )


@lru_cache(maxsize=None)
def of(language: str) -> dict[str, str]:
    """Every pair of a language: the expression, and the canonical it names.

    A language the product does not speak reads in the source language, which is
    where `i18n` already falls back to for every other text.
    """
    code = language if language in i18n.SUPPORTED else i18n.SOURCE
    pairs: dict[str, str] = {}
    for block in files():
        section = _section(block, code)
        expressions = section.get("expressions")
        if not isinstance(expressions, dict):
            continue
        for expression, canonical in expressions.items():
            pairs[str(expression)] = str(canonical)
    return pairs


def particles(language: str) -> tuple[str, ...]:
    """The expressions that name no canonical: the words that only connect.

    A particle is written under a key of its own — `particles`, and not
    `expressions` — and the shape is the reason: a particle carries no meaning,
    so there is no machine word for it to name. The suite's gates read
    `expressions` and ask every canonical to be a name the product declares, and
    a particle written there with an empty canonical would be a canonical no
    table, field, closed value or action of the product has.

    What a particle is FOR is the matcher's: `uma` and `pra` are spent by the
    segmentation and leave nothing behind, because a title is not made of them.
    """
    code = language if language in i18n.SUPPORTED else i18n.SOURCE
    found: list[str] = []
    for block in files():
        listed = _section(block, code).get("particles")
        if isinstance(listed, list):
            found.extend(str(expression) for expression in listed)
    return tuple(found)


def locality(language: str) -> str:
    """Where a language's words belong — the region part of the pair (§5).

    It travels with the data because a word is not language-wide by nature: a
    regionalism belongs to a locality, and the day a plugin carries one is the
    day this tag earns its keep.
    """
    code = language if language in i18n.SUPPORTED else i18n.SOURCE
    for block in files():
        found = _section(block, code).get("locality")
        if isinstance(found, str) and found:
            return found
    return ""


def languages() -> tuple[str, ...]:
    """Every language the packed data carries a section for."""
    found: set[str] = set()
    for block in files():
        found |= set(_read(block))
    return tuple(sorted(found))


def _section(block, language: str) -> dict:
    section = _read(block).get(language)
    return section if isinstance(section, dict) else {}


def _read(block) -> dict:
    """One file, read. A file that will not parse is skipped: one broken
    vocabulary must not take the whole language down.

    Nothing is cached here on purpose — the files are small and `of` is the one
    door that is read on every sentence, and it caches. A Traversable is not
    promised to be hashable, and the cache is not worth the promise.
    """
    try:
        data = json.loads(block.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}
