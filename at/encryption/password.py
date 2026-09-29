"""The password derivation — the file that fixes the price of a derivation.

The hashed field (§4) stores a derivation, and only ever compares it: what is
PROVED goes hashed, what AT USES goes encrypted. The method is not a schema
author's preference, so there is no per-field choice and no parameter a caller
passes — `nacl.pwhash` IS libsodium's password derivation, and the two limits
below are its price.

**The price is fixed here and reachable from nowhere else.** `OPSLIMIT` and
`MEMLIMIT` are module constants: no declaration names them (the closed list
refuses the keys), no `settings.json` holds them (§4: no secret lives there),
and no environment variable reaches them. The vault imports them instead of
naming a second price — a credential and the Main Key are both derived from
something a person types, and it is the SAME thing they type (item 176), so they
cost the same twice over. A knob that changed how a credential is derived would
be "no choice per field" with a hole in it.

**A derivation draws its own salt and carries it in its own answer**, so two
equal credentials already produce two unequal rows — which is what the item
asks — and `create` needs no reordering: the id is handed out after the
coercion, so a credential that is refused spends none.

**The comparison answers, it does not raise.** A stored value a hand edited is
exactly a row this door has to say no to; an exception would take down the read
that found it. It reads its two arguments and nothing else — no Main Key, no
setting — which is what makes a credential verifiable while the vault is
locked: it is the hash of the Main Key that is compared, and the key itself is
never derived on the way in.
"""

from __future__ import annotations

import nacl.exceptions
import nacl.pwhash

# The method's cost, and the same for every hashed field of every table (§4).
# `nacl.pwhash` names them the interactive limits; they are copied here so the
# module answers its own price instead of a caller naming one.
OPSLIMIT = nacl.pwhash.OPSLIMIT_INTERACTIVE
MEMLIMIT = nacl.pwhash.MEMLIMIT_INTERACTIVE


def derive(value: str) -> str:
    """The derivation of a value, salt and price included in the answer.

    The answer names back what it cost — the algorithm and the two limits — so
    nothing has to remember them separately.
    """
    return nacl.pwhash.str(
        value.encode("utf-8"), opslimit=OPSLIMIT, memlimit=MEMLIMIT
    ).decode("ascii")


def verify(candidate: str, stored: str) -> bool:
    """Whether the candidate is what the stored derivation proved.

    A stored value that is not a derivation, a stored value that is not text and
    a candidate that is not text are all "no" rather than an exception: a row a
    hand edited is refused, not fatal. The stored derivation handed as its own
    candidate is "no" too, because this is a comparison and not a string
    equality.
    """
    try:
        return nacl.pwhash.verify(stored.encode("ascii"), candidate.encode("utf-8"))
    except nacl.exceptions.CryptoError:
        return False
    except (UnicodeError, AttributeError, TypeError):
        return False
