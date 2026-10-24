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
the one read. **And `NARROWED` is also where an ACT of the object's own is
declared** — one the engine does not have, which a declaration could never name
because it is held to the engine's six: the `job`'s run and its two answers live
there, and so does the `secret`'s scan, which reads the folder and writes no row.
What the narrowing is FOR is that the ceiling is read from one place — `needed`
is what the route, the interpreter and the role all ask — so an object cannot
declare itself narrow for the help and wide for a route.

The labels are `i18n` keys like everything else (§3): this module writes no
sentence, and a permission without a label of its own is composed out of the
object's and the action's.
"""

from at.core.permissions_base import (  # noqa: F401
    DECLARED,
    DUE,
    EXTRA,
    INSTALL_HOOKS,
    JOB,
    NARROWED,
    REMINDER,
    SCAN,
    SECRET,
    SETTING,
    WORD_PERMISSIONS,
)
from at.core.permissions_catalogue import (  # noqa: F401
    actions,
    all_permissions,
    catalogue,
    is_known,
    narrowed,
    needed,
)
from at.core.permissions_labels import (  # noqa: F401
    action_key,
    action_label,
    label,
    object_label,
)
from at.core.permissions_modifiers import (  # noqa: F401
    ARGUMENT,
    FLAG,
    MODIFIERS,
    Modifier,
    modifiers,
)
from at.core.permissions_risk import (  # noqa: F401
    ALLOWING,
    RISK_ALLOW,
    RISK_BY_ACTION,
    RISK_READ,
    RISK_REMOVE,
    RISK_WRITE,
    risk,
)
from at.core.permissions_roles import carried, carries  # noqa: F401
