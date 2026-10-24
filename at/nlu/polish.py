"""The text the person wrote, tidied before it becomes a proposal.

**One function, one name.** `polish_text` is the whole of what the interpreter
does to the words a person typed into a title: today it raises the first letter
and leaves the rest exactly as it was written. Spelling and accents are a
different job, and the day they are done they are done HERE — the matcher calls
this and nothing else, so swapping the correction is replacing one body.
"""

from __future__ import annotations

from at.data import schema

# The declared types whose content is prose a person reads: the only text the
# polish touches. A machine word (an id, a key, a name another table points at)
# is the person's exactly as typed.
PROSE = ("markdown",)


def polish_text(table: str, field: str, text: str) -> str:
    """`text` as it should be proposed for `field` of `table`.

    Prose gets its first letter capitalised; everything else — and every letter
    after the first — is untouched. A text that starts with something that is
    not a letter (a digit, a quote) is left alone.
    """
    declared = (schema.of(table) or {}).get("fields", {}).get(field)
    if not isinstance(declared, dict) or declared.get("type") not in PROSE:
        return text
    if text[:1].isalpha():
        return text[:1].upper() + text[1:]
    return text
