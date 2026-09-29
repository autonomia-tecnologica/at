"""Secrets: the Main Key and the values it protects (§4).

The PoC carried no cryptographic primitive at all — no libsodium, no KDF — so
nothing here is reused. Its convention is what transfers, and it transfers as a
rule: a table keeps identity and metadata, never a value.

Two modules, and they are two subjects. `password` is the derivation the hashed
field stores — what is PROVED, and only ever compared. `vault` is the Main Key,
the key derived from it, the derived keys — one per service or purpose,
recovered from that key alone (item 14b) — and the envelope that carries what AT
USES. The Main Key is ONE string (item 176): `password` is the door of what
proves and `vault` the door of what opens, and both read the same thing a person
typed.

Neither module has a caller below it that keeps a key: what OPENS the vault is
`core.secrets`, which is the door into the `secret` table, and the key lives for
the length of one call of its own (§4, the three grades are a surface's choice).
"""
