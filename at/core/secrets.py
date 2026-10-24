"""The Vault's door into the table — what AT uses, sealed in its own row (§4).

§4 splits the two kinds of value a row can hold, and this module is where the
second kind meets the engine. What only PROVES is stored hashed in its own row
(`tables` and `password`), and what AT USES is stored encrypted in the `secret`
table. `encryption.vault` is the primitive — the Main Key, the key it derives,
the derived keys and the envelope — and this module is the caller that puts a
sealed value in a row: the primitive sits below `core`, reaches no table and
imports none of it (§4, layers), and the one other file that names it is the
engine, which asks it the shape of the envelope a `sealed` field accepts. Here
the two names are held together, and the sentence the item asks for is written:
the sealed value goes IN the row.

**The string that arrives is the Main Key** (§4, item 176): the same one the
first administrator proves themselves with, and the one the vault derives from
— this module asks for it as an argument and never where it came from, which is
what leaves the three grades of §4 to the surface that types it.

**The engine writes the row, and the sealed value passes through it.** The value
is sealed HERE and handed to `tables.create`, which hands out the id, keeps the
counter and writes the store — so a secret row is a row like any other, and the
engine is never told how to seal. What the engine holds is the TYPE: a field
declared `sealed` refuses anything that is not one of the vault's envelopes, so
a cleartext cannot land in the column even through the table door, and the
surface that tried reads the refusal in its own language (`table.error.*`).

**The row carries the scope, and never a key.** §4 derives the keys one per
service or purpose and says the Main Key recovers any of them lost — so the
scope is a column of the row (`service`) and the key is drawn again from the
string every time the value is opened. Nothing here caches a key and nothing
here writes one down: the key lives for the length of one call, which is what
§4's three grades — typing it when AT starts, `~/.at/`, the Working Folder —
leave to a SURFACE, with the price said out loud. This module sits below all
three and asks none of them: the Main Key arrives as an argument. No surface
asks for it yet, and that is on purpose — the three grades are the choice of
whoever builds the screen, and a fourth invented here would be the invention
this slice may not make.

**Writing refuses; reading answers.** A phrase under the floor and a scope that
is not a name are refusals with words of their own, because a write that cannot
be made is one nobody should be told succeeded; and `open_value` answers `None`
for the wrong phrase, for a row a hand edited and for a service nobody sealed
for — a read has to survive all of them, exactly as `vault.unseal` does.

**Two names, and they are told apart.** `encryption.vault` is the primitive and
`core.secrets` is the door, and neither is called `vault` twice: two names that
would touch each other do not coexist (the glossary's own rule), so the module
that reaches the table is named for what the table holds.
"""

from __future__ import annotations

from at.core import tables
from at.encryption import vault
from at.i18n import tr

# The field that carries the envelope, and the field that names the derived key
# that opens it. They are written here because this is the module that knows the
# subject, and the declaration is held to them by the suite: `secret.json` has
# to declare a `sealed` field called `value` and a field called `service`, and a
# declaration that renamed one would fail there instead of sealing a value
# nobody opens.
SEALED = "value"
SCOPE = "service"


class SecretsError(Exception):
    """Something the Vault's door refuses. The message is already in the active
    language — every surface prints it as it stands."""

    def __init__(self, key: str, **kw: object):
        self.key = key
        self.kw = kw
        super().__init__(tr(f"secrets.{key}", **kw))


def key_of(service: str, main_key: str) -> bytes:
    """The derived key of ONE service or purpose, out of the Main Key alone (§4).

    It is the sentence the item names last: the Main Key recovers any derived
    key that was lost. Nothing is stored between the two derivations, so a key
    the service lost is this call and no other — and the same string over the
    same name answers the same key on any machine. The string IS the Main Key
    (item 176): the one the first administrator proves themselves with, and
    nothing here asks who typed it.
    """
    try:
        return vault.derived_key(vault.vault_key(main_key), service)
    except vault.MainKeyRefused:
        raise SecretsError("error.phrase", min=vault.MINIMUM) from None
    except vault.ScopeRefused:
        raise SecretsError("error.scope", service=service) from None


def seal(name: str, service: str, value: str, main_key: str) -> dict:
    """A new row of `secret`, with the value sealed by the key of its service.

    The row is the engine's from here on: `tables.create` coerces what the
    declaration says, refuses what the type refuses and writes the store. What
    comes back is the row as it was stored — the envelope in the field, and the
    scope beside it — and never the value in clear, because the value in clear
    does not leave this function.
    """
    envelope = vault.seal(value, key_of(service, main_key))
    return tables.create(
        "secret", {"name": name, "service": service, SEALED: envelope}
    )


def open_value(row: dict, main_key: str) -> str | None:
    """The value the row carries, or `None` when this string does not open it.

    Every way of not opening is the same answer, because a read has to survive
    all of them: the wrong string, one under the floor, a scope that was hand
    edited into something that is not a name, a row of another service, and an
    envelope somebody edited. What this door never does is raise over a read.
    """
    try:
        key = key_of(_scope_of(row) or "", main_key)
    except SecretsError:
        return None
    envelope = _delivered(row)
    if envelope is None:
        return None
    return vault.unseal(envelope, key)


def _scope_of(row: object) -> str | None:
    """The service or purpose the row was sealed for, as the row declares it."""
    value = row.get(SCOPE) if isinstance(row, dict) else None
    return value if isinstance(value, str) and value else None


def _delivered(row: object) -> str | None:
    """The envelope the row carries — the sealed value, and nothing else."""
    value = row.get(SEALED) if isinstance(row, dict) else None
    return value if isinstance(value, str) and value else None
