"""Who acts — the actor, the role, and the first administrator (§4, item 9).

Every actor is a row of `actor`, with `type` reading `person`, `engine` or
`agent`. The row carries the identity, the role and the credential in the HASHED
field: what is PROVED is stored hashed, and what Bill USES is stored encrypted
(§4) — the credential is of the first kind, and it never leaves the row as a
value, only as a comparison (`tables.verify`).

**Three of the four ways in end here, and none borrows another's door.** The
person enters by Forms or by Basic, and the engine that proves one proves the
other — the same credential, another transport (`authenticate`). The machine
enters by `Bearer`, with the token ALONE and the agent's own door
(`authenticate_agent`): a person does not enter there, and a machine does not
enter by Forms. And the gate asserts the name of a person it has already proved
(`asserted`): there the credential is Authelia's and the proof travels as the
gate secret, so what is left for Bill is the row the name wears. `people()` and
`agents()` are what tell the two apart.

**The row is also the ceiling, and it is read from the row every time.** What an
actor reaches is the role its row points at and nothing else: `role_of` makes the
hop, `permissions.carries` answers it, and `may` is the one door a surface asks.
The machine is capped by the same one — a token is not a free pass, it is the
role its row wears — and an actor whose row points at no role reaches nothing.

**The rule lives here and the conversation lives in the `ui`.** The `cli` asks
for the name and reads the credential without echo; what this module decides is
what a folder gains: the engine's row at the first start, the administrator's
role carrying the whole catalogue, and the person that wears it. The writer is
the table engine (`tables.create`) — the derivation of the credential is the
engine's, never the caller's.

**No default, by choice.** The first administrator is ASKED for, never seeded: a
default credential is a published password, and the item says it with all the
letters. The minimum length is the same kind of decision, and it lives here for
the same reason — whoever asks does not get to decide the rule.
"""

from __future__ import annotations

import secrets

from bill.core import permissions, tables
from bill.data import store
from bill.encryption import password
from bill.i18n import tr

# The machine's row, and the role the first person wears. Both are DATA and do
# not follow the language: an actor's name is an identity a person's notes and
# an audit row will carry, and one that changed with the screen would stop
# naming the same row — the same rule an id follows (`tables.format_id`).
ENGINE_NAME = "engine"
ADMIN_ROLE = "admin"

# The shortest credential the first administrator may wear. §4's Access Phrase
# is a different thing with a different price (16), and this is not it: this is
# the credential that proves a person at the door.
MIN_CREDENTIAL = 8


class AdminError(Exception):
    """Something the first administrator's creation refuses. The message is
    already in the active language — every surface prints it as it stands."""

    def __init__(self, key: str, **kw: object):
        self.key = key
        self.kw = kw
        super().__init__(tr(f"admin.{key}", **kw))


class MachineError(Exception):
    """Something the machine credential's door refuses — minting one and revoking
    one. Its own words, and not the first administrator's: the two doors have
    nothing to do with each other, and a shared block would say so wrongly."""

    def __init__(self, key: str, **kw: object):
        self.key = key
        self.kw = kw
        super().__init__(tr(f"machine.{key}", **kw))


def engine_row() -> dict | None:
    """The machine's row, or `None` when the folder has not got it yet."""
    return next(
        (row for row in store.load("actor") if row.get("type") == "engine"), None
    )


def seed_engine() -> dict | None:
    """Give the engine its row, once — and only when there is none.

    Every act of the engine needs a row to be named in the `audit` (item 15), so
    the row exists before anything acts. It carries no credential and no role:
    the engine does not enter, and its ceiling is the engine's own (§4). The
    `agent`'s credential is item 10's, and no surface mints one yet — the row
    is born through the table door, with its role declared and the token going
    in hashed like any other credential.
    """
    if engine_row() is not None:
        return None
    return tables.create("actor", {"name": ENGINE_NAME, "type": "engine"})


def admin_role() -> dict | None:
    """The administrator's role row, or `None` — found by its NAME.

    It is the one row of `role` the product names, and the name is how it is
    found: the number is the folder's to hand out, and a listing that looked for
    a number would be reading a fact of one instance as if it were the rule.
    """
    return next(
        (row for row in store.load("role") if row.get("name") == ADMIN_ROLE), None
    )


def role_for_admin() -> dict:
    """The administrator's role, created carrying the whole catalogue.

    The set is `permissions.all_permissions()` — the catalogue IS the closed
    list, and the role holds exactly what administering demands (§4). A row that
    already exists is RESPECTED: whoever edited it edited it, and rewriting it
    here would be the product overwriting a person's file.
    """
    found = admin_role()
    if found is not None:
        return found
    return tables.create(
        "role",
        {
            "name": ADMIN_ROLE,
            "permissions": ",".join(permissions.all_permissions()),
        },
    )


def people() -> list[dict]:
    """The rows that are a person — whoever ENTERS. The engine does not enter."""
    return [row for row in store.load("actor") if row.get("type") == "person"]


def agents() -> list[dict]:
    """The rows that are a machine — the agent's own door (item 10).

    A machine is an actor like any other: it carries the role it was born with
    and the token it proves, stored hashed (`tables._hashed`) as a person's
    credential is. What it does not do is enter by the Forms door — `people()`
    leaves it out, and `authenticate` with it — and that, with the mirror of it
    in `authenticate_agent`, is the whole of the separation.
    """
    return [row for row in store.load("actor") if row.get("type") == "agent"]


def admins() -> list[dict]:
    """The people that carry a credential, which is what makes one an entry."""
    return [row for row in people() if row.get("credential")]


def entries() -> list[dict]:
    """The rows that may enter: the people with a credential, and the machines.

    The `engine` is the actor that does not enter (§4), and it carries no
    credential by construction — so what is left is exactly the two doors of
    item 10. A machine with no credential is not an entry either, for the same
    reason a person with none is not.
    """
    return [*admins(), *(row for row in agents() if row.get("credential"))]


# ------------------------------------------------- the machine credential ---

# How much entropy the minted token carries. It is a credential nobody types and
# nobody remembers — a machine pastes it — so what it costs is measured in bytes
# and not in characters a person can carry, and 32 bytes is what `token_urlsafe`
# already draws for a session (`session.Sessions.open`). It is a TOKEN and not an
# Access Phrase: the phrase is what a person knows (§4), and this is what only the
# machine's row holds, hashed.
TOKEN_BYTES = 32


def agent_row(pid: object) -> dict | None:
    """The `agent` row a number names, or `None` — the row the machine door acts
    on. A person's row is not one, and the door that mints and revokes says so by
    name instead of silently editing the wrong actor."""
    number = tables.number_of("actor", pid)
    row = store.find("actor", number) if number is not None else None
    return row if row is not None and row.get("type") == "agent" else None


def mint_agent(name: str, role: object) -> tuple[dict, str]:
    """A machine actor born with a token Bill MAKES, and the token handed back once.

    It is the surface item 10 left without one: an `agent` row could only be born
    through the table door, with its role declared and the token TYPED — which asks
    a person to invent a credential for a machine. Here Bill draws it, and the
    drawing is the engine's like every other derivation: the token goes into the
    row through `tables.create`, which hashes it on the way in (`tables._hashed`),
    and what comes back is the plain token — shown to whoever minted it and kept
    nowhere, because what the row holds is only ever compared.

    **The role is required, and by name.** An agent whose row points at no role
    reaches nothing (`permissions.carries` fails closed), which is a machine
    nobody can use — so a number nobody wears is refused HERE, with the words that
    name it, instead of minting a credential for a ceiling of nothing.
    """
    number = tables.number_of("role", role)
    if number is None or store.find("role", number) is None:
        raise MachineError("error.role_unknown", role=role)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    row = tables.create(
        "actor",
        {"name": name, "type": "agent", "role": str(number), "credential": token},
    )
    return row, token


def reissue_agent(pid: object) -> tuple[dict, str]:
    """A NEW token for a machine that already exists, handed back once.

    It is the other half of minting, and it exists for the reason a credential
    does: a token is lost, leaked, or about to be pasted somewhere it should not
    be, and the machine must keep its identity — its name, its role and its row —
    while the credential it proves is replaced. The old token stops opening the
    door the moment the field is rewritten, because what the row holds is a
    derivation and the comparison is against the NEW one.
    """
    row = agent_row(pid)
    if row is None:
        raise MachineError("error.not_agent", id=pid)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return tables.edit("actor", store.number_of(row), {"credential": token}), token


def revoke_agent(pid: object) -> dict:
    """The machine's credential taken away, with the row left standing.

    The credential is CLEARED and the row is not deleted: an actor is the name the
    `audit` will carry (item 15), and a revoked machine is a machine that no longer
    enters — `entries()` stops counting it the moment the field is empty — and not
    a row whose history is erased. An empty credential is not derived
    (`tables._hashed`), which is what makes this a removal and not a comparison
    against nothing.

    A machine that carries no credential has nothing to revoke, and it is REFUSED
    by name instead of silently rewritten: the screen that offers the button reads
    the same fact (`has_credential`, app's `_says`), so a person never sees the
    refusal — a hand-written request does.
    """
    row = agent_row(pid)
    if row is None:
        raise MachineError("error.not_agent", id=pid)
    if not row.get("credential"):
        raise MachineError("error.not_credential")
    return tables.edit("actor", store.number_of(row), {"credential": ""})


# ------------------------------------------------------------- the ceiling ---


def role_of(row: dict) -> dict | None:
    """The role row the actor's row points at, or `None` — the first hop.

    The row carries the NUMBER of the role, because a reference is how one table
    names another (`ref`, §4), and what it names is resolved HERE on every read:
    the store is the truth, and a role edited under a live session is read on
    the next request like any other row. Keeping the ceiling in the session
    would be a second copy of a fact that lives in the store, and the two would
    disagree the moment somebody edited a role.

    A row that points at nothing answers `None` — a number nobody wears, a role
    the person deleted under it, an actor born with no role at all, which is how
    the `engine` is born. `None` is a ceiling of nothing and never of
    everything, and `permissions.carries` is where that is said.
    """
    number = tables.number_of("role", row.get("role")) if isinstance(row, dict) else None
    return store.find("role", number) if number is not None else None


def may(row: dict, permission: str) -> bool:
    """Whether this actor may — its role's ceiling, read off its own row (§4).

    Two hops, one per module: the row points at the role (`role_of`) and the
    catalogue says what a role carries (`permissions.carries`). The door lives
    here because the question is asked of an ACTOR — a surface holds the row a
    request proved and asks through this — and item 10's machine credential
    reads its ceiling through the very same one, which is what makes the machine
    reach exactly what its role allows and nothing else.
    """
    return permissions.carries(role_of(row), permission)


# The derivation of nothing, computed on the first refusal and kept. It is what
# a comparison against a row that is not there still spends (§ `_nobody`).
_NOBODY: str | None = None


def _nobody() -> str:
    """A derivation of nothing, so a name nobody wears costs what a name somebody
    wears costs.

    It is computed on the FIRST miss and kept: deriving one costs what deriving
    any costs, and doing it at import would charge every command that never asks
    anybody to enter.
    """
    global _NOBODY
    if _NOBODY is None:
        _NOBODY = password.derive(secrets.token_urlsafe(32))
    return _NOBODY


def named(name: str) -> dict | None:
    """The `person` row that name wears, or `None` — the one name lookup.

    **The name is forgiven its whitespace and nothing else.** It is an identity
    a person types and a pasted line carries spaces around; what it names is a
    row, and the row's own name is compared stripped on both sides.

    It is a PERSON and never a machine: the `engine` does not enter (§4), and an
    `agent` enters by its own token alone (`authenticate_agent`), so neither is
    a row a name could open. One lookup and not two, because the two doors that
    ask it — the credential's (`authenticate`) and the gate's (`asserted`) —
    would otherwise drift in how they read the same name.
    """
    wanted = name.strip()
    return next(
        (
            candidate
            for candidate in people()
            if str(candidate.get("name", "")).strip() == wanted
        ),
        None,
    )


def authenticate(name: str, credential: str) -> dict | None:
    """The row the credential proves, or `None` — the entrance's one question.

    The name says WHICH row (`named`) and the credential is compared against the
    derivation that row carries — never against a string, and the comparison is
    `tables.verify`, which is the only door into a derivation. What it answers
    with is the ROW, in the shape the engine already answers one (`admins`,
    `find`): whoever enters is a person with a role — the ceiling item 11 will
    read — and not merely a "yes".

    **A name nobody wears pays the same as a name somebody wears.** Finding the
    row costs nothing and the comparison costs a derivation (libsodium's price,
    `encryption.password`): refused by a name that is not there, the door would
    answer in a blink and by one that is, in a tenth of a second — the same
    words and a different clock, which is a way of enumerating the actors. So
    the miss compares against `_nobody()` and takes as long as the hit.

    **It answers, it never raises.** A declaration the folder carries with a key
    the closed list lacks is refused by the ENGINE (`tables.verify`), and a
    refusal at the door of entry is a `None` and not a taken-down read — which
    is `_proves`, the one comparison behind both doors.
    """
    row = named(name)
    return row if _proves(row.get("credential") if row else None, credential) else None


def asserted(name: str) -> dict | None:
    """The person the GATE asserted, by name — §7b's other half, and no credential.

    On the container path the gate is what proved the person: Authelia holds the
    credential and the proof, and what reaches Bill is an identity — a name in
    the header the Caddy copied from the provider's own answer. What Bill
    decides here is WHO that identity is, and the answer is a row of the
    folder's own `actor` table, with the role the ceiling is read from: "who is
    an actor belongs to Bill, and how it is proved that it is them belongs to
    Authelia" (§7b).

    **There is no credential to compare, and that is the point.** The value this
    door reads is a header any client can write, so it is worth exactly what
    says it came through the gate — and that is the gate secret, which is not
    read here: the caller proves it before asking (`ui/webapp/app.py`), because
    it is a fact about the REQUEST and not about the row. A name nobody wears is
    `None`, and no row is invented for an identity the folder does not know.
    """
    return named(name)


def authenticate_agent(token: str) -> dict | None:
    """The machine a `Bearer` token proves, or `None` — the agent's own door.

    **The wire carries the token ALONE.** A machine says what it is in a header
    of its own mind and not in the credential, so there is no name to pick the
    row by and the row is found by COMPARISON: every `agent` row is tried
    against the token, and `_proves` is the only comparison — the derivation is
    the row's and the engine is the one that reads it. The price is one
    derivation per agent, and it is what the token-alone transport costs.

    **The two doors do not borrow each other.** A person does not enter here —
    `agents()` leaves them out — and a machine does not enter by Forms, which
    is the mirror of it in `authenticate`. It answers, it never raises, like
    the other door: a folder with a hand-edited declaration is a folder nobody
    enters, not a server that dies on the first machine that tries.
    """
    found = agents()
    for row in found:
        if _proves(row.get("credential"), token):
            return row
    if not found:
        # A folder with no machine still pays ONE comparison, so that the
        # answer costs what the first candidate would have cost and the clock
        # does not say what the answer does not (`_nobody`).
        _proves(None, token)
    return None


def _proves(stored: object, credential: str) -> bool:
    """Whether this derivation is the one `credential` carries.

    It is the ONE comparison of the module, and both doors read it — a second
    one would be a second place where `tables.verify` is called, and the two
    would drift. A row with nothing stored spends a derivation of nothing
    (`_nobody`), and a declaration the engine refuses is `False` here: at the
    door of entry a broken folder is a folder nobody enters.
    """
    try:
        return tables.verify(
            "actor",
            "credential",
            credential,
            stored if isinstance(stored, str) and stored else _nobody(),
        )
    except tables.TableError:
        return False


def can_expose() -> bool:
    """Whether the folder has somebody to enter it.

    "Sem ator nenhum o Bill não expõe" (§3) — and the `engine` is an actor that
    does not count: it does not enter, the person does. A machine enters by its
    own door (item 10), so an `agent` with a credential counts as well: a
    folder that opens only for a machine still asks somebody to prove
    themselves, and it is not the folder that asks nothing.
    """
    return bool(entries())


def check_credential(credential: str) -> None:
    """The price of a credential, refused in the active language."""
    if len(credential) < MIN_CREDENTIAL:
        raise AdminError("error.short", min=MIN_CREDENTIAL)


def create_admin(name: str, credential: str) -> dict:
    """The row of the person who administers, with the role created before it.

    The order matters: the role is the row the actor REFERENCES, and pointing at
    a number that is not there yet would leave a listing resolving a reference
    to nothing. The credential never lands here as typed — the engine derives it
    on the way in (`tables._hashed`), and this module never sees the derivation.
    """
    check_credential(credential)
    role = role_for_admin()
    return tables.create(
        "actor",
        {
            "name": name,
            "type": "person",
            "role": str(store.number_of(role)),
            "credential": credential,
        },
    )
