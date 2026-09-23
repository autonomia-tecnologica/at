"""Secrets: the master key and the values it protects (§4).

The PoC carried no cryptographic primitive at all — no libsodium, no KDF — so
nothing here is reused. Its convention is what transfers, and it transfers as a
rule: a table keeps identity and metadata, never a value.

The Access Phrase, the Bill Key and the derived keys land here with item 14.
What already has a room is `password`: the password derivation the hashed field
stores, and the only file in the product that speaks to `libsodium`.
"""
