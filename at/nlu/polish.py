"""The text the person wrote, tidied before it becomes a proposal.

**One function, one name.** `polish_text` is the whole of what the interpreter
does to the words a person typed into a title: today it raises the first letter
and leaves the rest exactly as it was written. Spelling and accents are a
different job, and the day they are done they are done HERE — the matcher calls
this and nothing else, so swapping the correction is replacing one body.
"""

from __future__ import annotations

from at import i18n
from at.core import spelling
from at.data import schema
from at.nlu.normalizer import fold

# The declared types whose content is prose a person reads: the only text the
# polish touches. A machine word (an id, a key, a name another table points at)
# is the person's exactly as typed.
PROSE = ("markdown",)


def polish_text(table: str, field: str, text: str, language: str | None = None) -> str:
    """`text` as it should be proposed for `field` of `table`.

    Prose gets its first letter capitalised and, when the `spelling-checker` is
    up, the corrections that are only case or accent (`nao` -> `não`). Everything
    else — and every letter after the first — is untouched. A text that starts
    with something that is not a letter (a digit, a quote) is left alone.
    A checker that is down, or that fails, changes nothing: this never raises.
    """
    declared = (schema.of(table) or {}).get("fields", {}).get(field)
    if not isinstance(declared, dict) or declared.get("type") not in PROSE:
        return text
    if text[:1].isalpha():
        text = text[:1].upper() + text[1:]
    try:
        return _accented(text, language or i18n.active_code())
    except Exception:  # the chat goes on with the text as written
        return text


def _accented(text: str, language: str) -> str:
    """The clear corrections applied: one suggestion, the same word once case and
    accents are folded away. Words that are already capitalised mid-sentence
    (names, acronyms) are the person's."""
    found = spelling.check(text, language)
    if not found:
        return text
    for finding in sorted(found, key=lambda item: item.offset, reverse=True):
        end = finding.offset + finding.length
        original = text[finding.offset:end]
        if not _clear(original, finding):
            continue
        fixed = finding.suggestions[0]
        if finding.offset == 0 and original[:1].isupper():
            fixed = fixed[:1].upper() + fixed[1:]
        text = text[:finding.offset] + fixed + text[end:]
    return text


def _clear(original: str, finding) -> bool:
    if len(finding.suggestions) != 1 or finding.length <= 0:
        return False
    suggestion = finding.suggestions[0]
    if suggestion == original or fold(suggestion) != fold(original):
        return False
    if len(suggestion.split()) != len(original.split()) or suggestion.count("-") != original.count("-"):
        return False
    start = finding.offset == 0
    if any(char.isupper() for char in (original[1:] if start else original)):
        return False
    return start or not any(char.isupper() for char in suggestion)
