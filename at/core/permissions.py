"""The permission catalogue — the closed list of what may be done (§4).

A permission is `object:action`. A role is a row of `role` carrying a set of
them, and the actor points at the role. A role that names a permission that does
not exist **does not take AT down**: it says so, and the saying is what gets
read (§4) — which is why this module answers `is_known`, and whoever reads a role
asks here instead of trusting the row.

**What the catalogue is FOR is `carries`.** Every route of the API demands a
permission, and the ceiling of that route is the answer this module gives about
the role the acting actor points at: the entry IS the grant, there is no
hierarchy and no wildcard, and a permission the role does not name is one the
route is refused for. Resolving the actor into its role is the ACTOR's question
and lives beside it (`actors.may`); what lives here is what a role carries.

**Where the closed list lives.** A table's actions are the ENGINE's
(`tables.ACTIONS`): an action the engine does not have is not a permission that
exists, and writing the six of them here again would be the second copy that
drifts. The objects that ARE a table come from the DECLARED tables, for the same
reason the help reads them from there (`tree.table_nodes`): declaring a table is
what makes it one. What is not a table — the settings, today, and the services,
the plugins and the interpreter's vocabulary with item 11 — is declared HERE,
because there is no other place where it exists.

**An object may narrow itself, and it does it in its own declaration.** The six
are the engine's, and a table whose rows are not CRUD'd has no business offering
all six as permissions: `secret` declares `read` and `edit`, its listing is
`secret:read` and its write is `secret:edit`, and a closing and a deletion are
not permissions it has. An object that is not a table declares the same thing in
the same shape, one shelf up (`NARROWED`), because it has no schema to write it
in — the settings answer `read` and `edit` there, and their `list` and `view` are
the one read. What the narrowing is FOR is that the ceiling is read from one
place — `needed` is what the route, the interpreter and the role all ask — so an
object cannot declare itself narrow for the help and wide for a route.

The labels are `i18n` keys like everything else (§3): this module writes no
sentence, and a permission without a label of its own is composed out of the
object's and the action's.
"""

from __future__ import annotations

from at.core import tables
from at.data import schema
from at.i18n import tr

# The key a declaration narrows itself with, and the whole of what it may say:
# the permission `object:permission` the table answers, and the engine actions
# that reach it. A table that declares none answers the engine's six
# (`tables.ACTIONS`) under their own names — `task:list`, `task:edit`. A table
# that declares one answers exactly what it names and nothing else: `secret`
# answers `read` and `edit`, so its listing is `secret:read` and its write is
# `secret:edit`, and the two actions the table does not answer — a closing and a
# deletion — are not permissions it has.
#
# The actions are held to `tables.ACTIONS` both ways, and that is the point of
# reading them here: a name the ENGINE does not have is not a permission that
# exists (§4), and an action the declaration forgot is one the table does not
# answer any more.
DECLARED = "permissions"

# The name of the settings OBJECT. It is not a table — the word names what
# `setting:read` and `setting:edit` are about — and it is here, once, because
# the catalogue, the tree and the risk all spell it.
SETTING = "setting"

# The objects that ARE not a table narrow themselves HERE, in the same shape a
# table writes in its own declaration — permission → the engine actions it
# answers — because there is no schema for the narrowing to live in. The
# settings are the only one today: `list` and `view` are the one read, `edit` is
# the one write, and the three are the words the `cli` offers under `setting`.
#
# They are read by the SAME door as a table's (`narrowed`), so the help, the
# route and the role cannot disagree about what the object answers: a second
# mapping beside this one would be the second home this module refuses.
NARROWED: dict[str, dict[str, tuple[str, ...]]] = {
    SETTING: {"read": ("list", "view"), "edit": ("edit",)},
}

# The objects that are not a table, and the actions each one accepts. §4 names
# the settings with all the letters; the other two are what the WebApp's routes
# reach and no table answers for — `prose` is the layer that manages every file
# that is not structured data, and `nlu` is the interpreter's door, which
# proposes and never writes. They are named here because there is no other place
# where they exist.
#
# **The last three are reached by NO route yet, and they are declared all the
# same.** §4 lists them among the objects — "the settings, the services, the
# plugins and the interpreter's vocabulary" — and the screens that move them
# (items 13, 15 and 16) are what will demand them. Declaring them here is not
# anticipation: the catalogue is the CLOSED list a role is written against, and a
# role that names `service:edit` today names a permission that EXISTS that
# nothing has yet been refused for — which is a different thing, and the
# difference is the whole of `is_known`. Leaving them out would have the screens
# arrive into a catalogue that has to grow under a live role.
EXTRA: dict[str, tuple[str, ...]] = {
    SETTING: ("read", "edit"),
    "prose": ("read", "edit"),
    "nlu": ("ask",),
    "service": ("read", "edit"),
    "plugin": ("read", "edit"),
    "vocabulary": ("read", "edit"),
}

# ------------------------------------------------------------------- risk ---
#
# The risk each entry DECLARES (§4, item 15), and the whole of the scale: the
# four numbers below are the ones the item closed, and the product declares
# nothing at `1` — the top of the ruler is a demand nobody may leave to an
# automatic act.
#
# **The number belongs to the ACTION**, with the objects that change what the
# SYSTEM allows lifted above them: a read is `0`, creating or editing a row is
# `0.2`, and overwriting or removing what existed is `0.5`. Changing the ceiling
# itself — the settings, the roles, the actors, and the services, plugins and
# vocabulary that decide what AT understands and does — is `0.8`, and it is
# where item 15 puts `setting:edit` by name: "the bar does not lower itself".
#
# **This is not the filter, and it is not the whole of the rule.** The demand's
# risk is the highest among the action and the arguments it carries, and a FIELD
# may raise it (item 15's second slice): what is declared here is the floor every
# demand of this entry starts from, which is what the ruler on the page draws.
RISK_READ = 0.0
RISK_WRITE = 0.2
RISK_REMOVE = 0.5
RISK_ALLOW = 0.8

RISK_BY_ACTION: dict[str, float] = {
    "list": RISK_READ,
    "view": RISK_READ,
    "read": RISK_READ,
    "create": RISK_WRITE,
    "edit": RISK_WRITE,
    "ask": RISK_WRITE,
    "cancel": RISK_REMOVE,
    "delete": RISK_REMOVE,
}

# The objects whose change is "what the system allows". A read of one of them is
# a read like any other — knowing what the ceiling is, is not moving it.
ALLOWING = ("setting", "role", "actor", "service", "plugin", "vocabulary")


def risk(permission: str) -> float:
    """The number this catalogue entry declares (§4, item 15).

    An entry the catalogue does not name answers with nothing — a role a hand
    edited is read by the screen that shows it, and this is asked about the same
    names `is_known` is. The value is never a refusal: it is what the demand
    filter compares against the threshold, and the screen draws it.
    """
    obj, _, action = permission.partition(":")
    if not is_known(permission):
        return RISK_READ
    if obj in ALLOWING and RISK_BY_ACTION.get(action, RISK_READ) > RISK_READ:
        return RISK_ALLOW
    return RISK_BY_ACTION.get(action, RISK_READ)


def narrowed(table: str) -> dict[str, tuple[str, ...]]:
    """The permissions this object's declaration narrows it to, or `{}`.

    The declaration is the TABLE's own (`data/schema/<table>.json`) when the
    object is a table, and `NARROWED` when it is not — the settings are the one
    object of the second kind, and both are read here, by the same door, so a
    word, a route and a role never read two answers.

    It is read the way every other declaration is, and answered the way every
    other read of a declaration answers: what is not there, or is not shaped the
    way the declaration is, is nothing — a hand-edited file is a table the
    catalogue answers for with the engine's six, never a read that raises.
    """
    held = NARROWED.get(table)
    if held is not None:
        return {permission: actions for permission, actions in held.items()}
    declared = schema.of(table) or {}
    stated = declared.get(DECLARED)
    if not isinstance(stated, dict):
        return {}
    found: dict[str, tuple[str, ...]] = {}
    for permission, actions in stated.items():
        if not isinstance(permission, str) or not isinstance(actions, list):
            continue
        kept = tuple(action for action in tables.ACTIONS if action in actions)
        if kept:
            found[permission] = kept
    return found


def actions(table: str) -> tuple[str, ...]:
    """The engine actions this object answers, in the engine's own order.

    It is what the help offers and what the dispatch accepts (`tree`), so a word
    the object does not answer is a word no surface spells — and the order is the
    engine's and not the declaration's, because the six are the engine's and a
    declaration does not reorder them. It answers for a table and for an object
    that is not one alike, which is how the `setting` word is declared: the tree
    reads its children from here and does not write them down.
    """
    found = narrowed(table)
    if not found:
        return tables.ACTIONS
    return tuple(
        action
        for action in tables.ACTIONS
        if any(action in actions for actions in found.values())
    )


def needed(table: str, action: str) -> str:
    """The permission an engine action demands of `table`.

    A table that declares nothing demands the action's own name, which is what
    every table did before a declaration could narrow it; one that declares a
    permission over the action demands THAT, so the route, the interpreter's
    ceiling and the role are all reading the same name.
    """
    for permission, actions in narrowed(table).items():
        if action in actions:
            return f"{table}:{permission}"
    return f"{table}:{action}"


def catalogue() -> dict[str, tuple[str, ...]]:
    """Every object and the permissions it accepts, in the catalogue's order."""
    found: dict[str, tuple[str, ...]] = {}
    for declared in schema.declared():
        table = declared.get("id")
        if not isinstance(table, str):
            continue
        found[table] = tuple(narrowed(table)) or tables.ACTIONS
    found.update(EXTRA)
    return found


def all_permissions() -> list[str]:
    """The whole closed list, `object:action`, in the catalogue's order."""
    return [
        f"{obj}:{action}" for obj, actions in catalogue().items() for action in actions
    ]


def is_known(permission: str) -> bool:
    """Whether the catalogue names this permission. Never raises: a role a hand
    edited is a row this door has to answer about, and an exception would take
    down the read that found it."""
    obj, _, action = permission.partition(":")
    return action in catalogue().get(obj, ())


def carried(role: object) -> list[str]:
    """The permissions a role row carries, as the row declares them.

    The row is READ and never trusted: `permissions` is a list by declaration
    (§4), and a row a hand edited to something else carries nothing — a read is
    not the place to raise about it, and no surface is left with a screen it
    cannot draw. What a NAME means is `is_known`'s question and not this one: a
    role may name a permission the catalogue does not have, and it is the read
    that shows the role which ones those are. Here they carry exactly what they
    say, which is nothing a route demands.
    """
    declared = role.get("permissions") if isinstance(role, dict) else None
    if not isinstance(declared, list):
        return []
    return [entry for entry in declared if isinstance(entry, str)]


def carries(role: object, permission: str) -> bool:
    """Whether this role carries a permission — the ceiling of the actor that
    points at it (§4).

    A plain membership, and the whole of it: the catalogue entry IS the grant,
    the row names them one by one, and a permission the role does not name is
    one it does not carry. A `task:*` shape is not a permission the catalogue
    names, and the day one is wanted it will be a decision taken here and not a
    guess made by whoever reads a role.

    **A role that is not there carries nothing**, and that is the rule failing
    CLOSED: an actor whose row points at no role — or at a number nobody wears —
    reaches nothing at all, instead of everything. The `engine`'s row is the
    one born that way, and it is right for it: it does not enter, and its
    ceiling is the engine's own (§4).
    """
    return permission in carried(role)


def label(permission: str) -> str:
    """The display name: a key of its own when one exists, and the object and the
    action composed when it does not.

    `tr` answers the key itself when the catalog lacks it, so an absent label is
    the signal to compose — the same way the engine falls back to the field's
    name.
    """
    key = f"permission.{permission.replace(':', '.')}"
    written = tr(key)
    if written != key:
        return written
    obj, _, action = permission.partition(":")
    return tr("permission.line", object=object_label(obj), action=action_label(action))


def object_label(name: str) -> str:
    """The word for the OBJECT of a permission — `Tarefas`, `Configurações`.

    A table is named the way every surface names it; anything else answers with
    its own key, and with the raw word when there is not even that. It is public
    because the screen that moves a role GROUPS the closed list by object, and a
    second reading of the same key would be the second home this module refuses.
    """
    if schema.of(name) is not None:
        return tables.table_name(name, many=True)
    key = f"permission.object.{name}"
    written = tr(key)
    return written if written != key else name


def action_label(name: str) -> str:
    """The word for the ACTION of a permission — `Ler`, `Criar`."""
    if name in tables.ACTIONS:
        return tr(f"table.action.{name}")
    key = f"permission.action.{name}"
    written = tr(key)
    return written if written != key else name
