"""Secrets: the Vault Key and the values it protects (§4).

The PoC carried no cryptographic primitive at all — no libsodium, no KDF — so
nothing here is reused. Its convention is what transfers, and it transfers as a
rule: a table keeps identity and metadata, never a value.

Two modules, and they are two subjects. `password` is the derivation the hashed
field stores — what is PROVED, and only ever compared. `vault` is the Access
Phrase, the Vault Key derived from it, the derived keys — one per service or
purpose, recovered from the Vault Key alone (item 14b) — and the envelope that
carries what AT USES.

Neither module has a caller below it that keeps a key: what OPENS the vault is
`core.secrets`, which is the door into the `secret` table, and the key lives for
the length of one call of its own (§4, the three grades are a surface's choice).
"""
