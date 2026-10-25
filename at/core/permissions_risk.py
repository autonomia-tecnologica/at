"""The risk each catalogue entry declares.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations

from at.core.permissions_catalogue import is_known

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
    "run": RISK_WRITE,
    # The scan READS the folder: it reports what it found and corrects nothing
    # (`secrets scan`), so it is a read like a listing and it moves no ceiling.
    "scan": RISK_READ,
    # `secret install-hooks` WRITES two files into a repository's own
    # `.git/hooks/` — the same reason `make`/`convert` sit at this number, and
    # not above it: it changes nothing of what the system ALLOWS.
    "install-hooks": RISK_WRITE,
    # `due` READS the store: it says which reminders a day is about and writes
    # no row, the same reason `scan` is a read and not a write.
    "due": RISK_READ,
    # `backup make` CIFRA a pasta inteira e manda a cópia ao destino — nada
    # que já existia é sobrescrito, o mesmo porquê de um `create`.
    "make": RISK_WRITE,
    # `backup restore` SUBSTITUI a pasta vigente pelo que o backup guardava —
    # é a frase da própria régua, "overwriting... what existed", e não o
    # `create` de quem apenas junta algo novo.
    "restore": RISK_REMOVE,
    # `cli admin` nasce o primeiro administrador: a pasta não tinha governança
    # até este ato, e é exatamente "o que o sistema permite" que ele muda — a
    # mesma razão de `role:create` e `actor:create` nesta régua (§4, item 15).
    "admin": RISK_ALLOW,
    # `cli lang` escolhe o idioma: muda um arquivo da pasta, e não o teto do
    # que ela permite.
    "lang": RISK_WRITE,
    # `cli convert` escreve um arquivo novo em `Convertidos/`, a partir de um
    # que já existia em `Arquivos/` — o mesmo porquê de um `create`.
    "convert": RISK_WRITE,
    # `cli search` READS the files and the searchable fields and writes nothing
    # — a read like a listing (B-21).
    "search": RISK_READ,
    # `help show` lê o que o binário oferece e não muda nada da pasta — o
    # mesmo porquê de `list`/`view`/`read`.
    "show": RISK_READ,
    "cancel": RISK_REMOVE,
    "delete": RISK_REMOVE,
    # The two halves of the approval are ONE act with two outcomes, and they are
    # priced together on purpose: releasing a demand the bar held is changing
    # what the system allows, and refusing is the same word over the same demand
    # — pricing them apart would make the cheaper one a way to learn about the
    # dearer, which is the reason §3 keeps `audit:read` from a machine.
    "approve": RISK_ALLOW,
    "refuse": RISK_ALLOW,
    # `declare` WRITES a row, the same way `create`/`run` do — it does not
    # itself bypass the filter: a round the clock rounds under it still faces
    # the bar, every time, exactly as any other round does.
    "declare": RISK_WRITE,
    # `disable` REMOVES what existed — not the row (it stays, `refused`, for
    # the reason a refusal never deletes), but the schedule's only reason to
    # be: the rounds it would still have had. The same number `restore`
    # carries for the same reason, and the one above `declare`'s on purpose —
    # undoing a schedule is not priced like making one.
    "disable": RISK_REMOVE,
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
