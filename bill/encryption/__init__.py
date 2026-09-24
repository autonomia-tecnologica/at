"""Secrets: the Bill Key and the values it protects (§4).

The PoC carried no cryptographic primitive at all — no libsodium, no KDF — so
nothing here is reused. Its convention is what transfers, and it transfers as a
rule: a table keeps identity and metadata, never a value.

Two modules, and they are two subjects. `password` is the derivation the hashed
field stores — what is PROVED, and only ever compared. `vault` is the Access
Phrase, the Bill Key derived from it, and the envelope that carries what Bill
USES (item 14a). The derived keys, one per service or purpose, are item 14's
second half and are not built yet.
"""
