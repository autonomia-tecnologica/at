"""The mechanical tolerance: the same word, however it was written.

The normalizer of item 15 is three pieces, and this is the one that is
**algorithm**. The slang and jargon map is data and lives in the vocabulary; the
date, time and number grammar is code and lives in the grammar. What is left is
here, and it is the half a person notices first: a word typed off a phone
keyboard, in a hurry, without the accent.

Forgiven, in this order: case, accents, hyphens and runs of space; then a plural;
then one letter out of place. Not forgiven: a word the product does not know —
and the nearer expression wins **only when it is alone at that distance**, so two
candidates in a tie name nothing rather than a coin toss. That is the rule the
whole layer answers under: what does not resolve is residue, never a guess.

`fold` is the one fold of the product, and the grammar uses it too. There is no
second one: the grammar's own words and a person's words are compared the same
way, and a second implementation would be a second answer.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from bill import i18n
from bill.nlu import vocabulary

# One letter, and only one: this forgiving is for a typo, not for a different
# word.
TYPO_DISTANCE = 1

# A word shorter than this is not forgiven a letter. At four letters a typo IS
# another word, and the tie rule below would have almost nothing to stand on.
TYPO_FLOOR = 5


def fold(text: str) -> str:
    """A phrase written the way the product's own words are compared.

    Case and accents are the writer's to skip: `amanha` off a phone keyboard and
    `SÁBADO` typed in a hurry are the same two words as `amanhã` and `sábado`.
    Hyphens and runs of space are one space, because `meia-noite` and `meia noite`
    are one word to the person who wrote them.
    """
    plain = unicodedata.normalize("NFD", text.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"[\s\-_]+", " ", plain).strip()


def folded(words: dict) -> dict:
    """A table of words, keyed the way `fold` writes them."""
    return {fold(word): value for word, value in words.items()}


def canonical(text: str, language: str | None = None) -> str | None:
    """The machine word a person's word names, or nothing at all.

    The expression as it was written, then its singulars, then its misspellings —
    and never a coin toss: a word that names two things names none, and comes
    back as nothing for whoever asked to treat as a residue.
    """
    pairs = _pairs(language or i18n.active_code())
    spoken = fold(text)
    if not spoken:
        return None
    for form in _forms(spoken):
        found = pairs.get(form)
        if found is not None:
            return found
    return nearest(spoken, pairs)


def nearest(word: str, pairs: dict[str, str]) -> str | None:
    """What a word is one letter away from, when it is alone at that distance.

    `pairs` is expression → canonical, as the vocabulary hands them over. Two
    expressions at the same distance from the word are a tie, and a tie names
    nothing — unless they happen to name the same canonical, in which case there
    was never a question to answer.
    """
    if len(word) < TYPO_FLOOR:
        return None
    closest = TYPO_DISTANCE + 1
    found: set[str] = set()
    for expression, canonical in pairs.items():
        if abs(len(expression) - len(word)) > TYPO_DISTANCE:
            continue
        distance = _distance(word, expression, TYPO_DISTANCE)
        if distance > TYPO_DISTANCE:
            continue
        if distance < closest:
            closest, found = distance, {canonical}
        elif distance == closest:
            found.add(canonical)
    return found.pop() if len(found) == 1 else None


@lru_cache(maxsize=None)
def _pairs(language: str) -> dict[str, str]:
    """A language's pairs, keyed the way `fold` writes them.

    Two expressions that fold to the same word are one entry here; that they
    agree on the canonical is the suite's to prove, because a file read into a
    dict keeps the last one in silence.
    """
    return {
        fold(expression): canonical
        for expression, canonical in vocabulary.of(language).items()
    }


def _forms(spoken: str):
    """The word, and the singulars a plural may have been written from."""
    yield spoken
    if len(spoken) > 3 and spoken.endswith("s"):
        yield spoken[:-1]
    if len(spoken) > 4 and spoken.endswith("es"):
        yield spoken[:-2]
    if len(spoken) > 4 and spoken.endswith("ies"):
        yield spoken[:-3] + "y"


def _distance(left: str, right: str, ceiling: int) -> int:
    """How many letters apart two words are, up to `ceiling` — past it, it is moot.

    The length difference alone settles most pairs, and it settles them without
    walking the grid of the rest.
    """
    if abs(len(left) - len(right)) > ceiling:
        return ceiling + 1
    previous = list(range(len(right) + 1))
    for row, char in enumerate(left, start=1):
        current = [row]
        for column, other in enumerate(right, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (char != other),
                )
            )
        previous = current
    return previous[-1]
