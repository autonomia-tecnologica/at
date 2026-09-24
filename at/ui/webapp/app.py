"""The WebApp server — AT's UI, on loopback.

It serves three things, and nothing else: the built page, the LOOK (base.css,
the themes, the drawings, the hosted typefaces) and the JSON the page reads. The
page owns no rule — the server decides, the page draws.

**The page is public and the API is not.** The built page, the look and the
entrance are served to whoever asks — the entrance has to be dressed before
anybody is in — and everything else under `/api/` answers 401 until a session is
open. Who enters is the folder's own credential: the Forms local of §3, proved
once at the door and carried after that by a token (`session.py`). The proof is
the engine's (`actors.authenticate`): the name says which row, the derivation
that row carries decides, and the value never travels back out.

**Four transports, and the doors of items 10 and 13 behind them.** The cookie is
Forms', and the `Authorization` header carries two of the rest — and both prove
themselves on EVERY request, so the session they answer with is held by nobody
(`session.from_row`). `Basic` carries a person's name and credential: §3's same
credential by the other transport, and only while the folder's PERMISSION says
so — it lives in `settings.json`, which holds permission and adjustment and never
a secret (`basic_allowed`). `Bearer` carries a machine's token ALONE, and the row
it proves is an `agent` (`actors.authenticate_agent`). The two doors do not
borrow each other: a person does not enter by `Bearer`, and a machine does not
enter by Forms. A refused Basic attempt is owed the `WWW-Authenticate` the
browser understands (`_challenge`) — and the page's own 401 is owed nothing,
because a challenge there would pop the browser's dialog over the entrance AT
drew itself.

**The fourth transport is the gate, and its credential is not here.** §7b: on
the container path the identity provider proved the person, the Caddy copied its
answer onto the request — the name in `Remote-User` — and the whole value of
that header is the gate SECRET the Caddy attached beside it, which the provider
never sees. So the two are read together and neither alone: a name whose secret
is missing or wrong is a header somebody wrote, refused (403) and said out loud
(`webapp.gate_refused`), because the failure it usually means — a Caddy whose
secret file went missing, or a request that reached the port without passing the
edge — is one a person has to be able to see. With the secret proved, the name
is looked up among the folder's own people (`actors.asserted`) and the row
answers for the ceiling like any other session: the credential was Authelia's,
the role is AT's.

**Which doors are open is the PATH's, and the switch is what moves it.** On the
hosted path all four are (§6); on the container path the person's door is the
gate's, so Forms and Basic are off (`gate.on_gate`), and a folder that took the
switch and then lost the gate closes: the API answers §6's sentence
(`services.gate.down`) and nothing else, and AT never reopens Forms on its own
— the way back is the Wizard or the `cli`, both local. Neither state is guessed
here: `at/core/gate.py` holds the record, and this file reads it.

**With nobody to enter, nothing is asked.** A folder whose `actors.can_expose()`
is false has no row carrying a credential, so there is nothing to prove — and
there the API answers as it always did. It is §3's own sentence: "sem nenhuma
forma de autenticação configurada, o AT escuta apenas 127.0.0.1". `at
webapp` does not even arrive here (it refuses before taking the port), and this
is the state a raw `make_server` serves in — which is what the route tests
build.

**The session says who is in; the role says how far they reach.** Every route of
the API demands ONE permission of the catalogue, and the actor a request proved
is refused (403) when its role does not carry it — the same door for the person
and for the machine, which is what makes a token reach exactly what its role
allows and nothing else. The role is resolved from the actor's row on EVERY
request and never kept in the session: the store is the truth, and a role edited
under a live session is read on the next request like any other row. The
demand is written at the route it belongs to (`_may`), the object is the route's
own, and nothing the catalogue does not name is demanded by anybody.

**The ceiling is MOVED from a screen, and a machine's credential is minted
there.** The panel's People entry reads the two system tables of the ceiling, and
two routes serve it and nothing else: `GET /api/catalogue` hands over the closed
list a role is written against — one entry per permission, with the words for its
object and its action and the risk it declares — and `POST /api/agent` is the door
that DRAWS a token for an `agent`, gives it again, and takes it away. A token is
not something a person types, so AT makes it and the row keeps only the
derivation; what comes back travels to the person who asked and is never read
again. Each demand is the action's own (`role:list` for the closed list, the
actor's create or edit for the token), and the two records carry the fact their
screen cannot draw from the fields alone (`_says`): the permissions a role names
that the catalogue does not have, and whether an actor holds a credential at all.

Beside the session stand the pair of guards on every write: `Origin` must carry
the same authority as `Host`, and the body must declare itself JSON. The second
is the one that holds, and the reason is worth keeping: an `Origin` check
compares the origin against `Host`, and a name that resolves to this address
(DNS rebinding) matches both — while a foreign page cannot send
`application/json` without a preflight, and no `do_OPTIONS` answers one.

The theme is a LOOKUP against the registry, never a path: an id that names no
theme falls back to the default, so a query string can never reach a file the
registry does not name.

**Exposure is the flag, and the WebApp never leaves the loop because of it.** §3
says exposing demands authentication and TLS, that the TLS is Caddy's, and that
Caddy travels inside this binary — so `at webapp --include-caddy` puts that
Caddy in front (`services/caddy.py`), and the WebApp behind it listens where it
always did, `127.0.0.1`, on a port nobody types. What the person reaches is the
Caddy's port, with AT's own certificate. Without the flag there is no TLS to
be had, so there is no exposure: asking for an address that is not the local
loop is refused here, before a port is taken (`loops_back`).
"""

from __future__ import annotations

import base64
import errno
import hashlib
import ipaddress
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from at import i18n, nlu
from at.core import (
    actors,
    files,
    gate,
    permissions,
    projects,
    risk,
    settings,
    tables,
    versioning,
)
from at.data import schema, store
from at.prose import listing as prose
from at.services import caddy
from at.ui import ask as door
from at.ui.webapp import session

HOST = "127.0.0.1"
DEFAULT_PORT = 12345
DEFAULT_THEME = "at"

# The face of the loop, by name. It is the host the person reaches by default,
# and the only NAME that counts as the loop: any other name is resolved by the
# resolver and not by AT, and AT does not ask a resolver for permission to
# be exposed (`loops_back`).
LOOPBACK_NAME = "localhost"

# The permission that lets an actor come in through Basic (§3, Configurações
# gerais). It is a KEY of `settings.json` and never a credential: the file holds
# permission and adjustment, and what a person proves lives hashed in their own
# row. Off is the default, because Basic puts the credential on the wire on
# every request.
BASIC_KEY = "basic_auth"

# The realm a refused Basic attempt is challenged with. It is a MACHINE word —
# the browser prints it, and it names the thing being entered, which is AT in
# every language (§3: the brand is not translated).
REALM = "AT"

# The header the gate asserts the identity on. It is the provider's own word for
# it (Authelia's answer to the Caddy's `forward_auth`, copied onto the request
# by the Caddy's `copy_headers`) and it is a MACHINE word, like the realm: it
# names the field of a protocol and not a screen. What makes it an identity is
# the secret travelling beside it (`services/caddy.py`, §7b).
GATE_IDENTITY = "Remote-User"

# The page runs under this, which is why nothing inline and no `data:` is ever
# built into it: Vite is configured for it, and the themes are checked for it.
CSP = "default-src 'self'"

# How much a write may carry. A table row is small; the ceiling is what stops a
# stranger's stream from becoming this process's memory.
MAX_BODY = 64 * 1024

# The two actions the table write answers. The engine has six (`tables.ACTIONS`)
# and the page has the doors for these two: a closing and a deletion come with
# the screens that ask for the confirmation they owe. It is the ROUTE's
# vocabulary, and it is what says which permission a write demands — the action
# is part of the permission, and this is the list of actions that may become one.
TABLE_WRITES = ("create", "edit")

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
THEMES = ASSETS / "themes"
ICONS = ASSETS / "icons"
VENDOR = HERE / "vendor"
UI_DIR = HERE / "dist"
UI_ASSETS = UI_DIR / "assets"

_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
}


# ------------------------------------------------------------------ look ---

def theme_rows() -> list[dict]:
    """The theme registry — which themes exist, and which side each wears."""
    where = ASSETS / "themes.jsonl"
    if not where.is_file():
        return []
    rows: list[dict] = []
    for line in where.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            rows.append(row)
    return rows


def active_theme(requested: str | None) -> dict | None:
    """The theme the page wears: the asked one, the machine's, the default, and
    then the first declared — never an error."""
    rows = theme_rows()
    for candidate in (requested, os.environ.get("AT_THEME"), DEFAULT_THEME):
        if not candidate:
            continue
        for row in rows:
            if row.get("id") == candidate:
                return row
    return rows[0] if rows else None


def theme_css(requested: str | None, dark: bool) -> str | None:
    """The stylesheet of the active theme; the light side answers when the dark
    file does not exist."""
    row = active_theme(requested)
    if row is None:
        return None
    ident = str(row.get("id"))
    sides = [f"{ident}-dark.css", f"{ident}.css"] if dark else [f"{ident}.css"]
    for name in sides:
        where = THEMES / name
        if where.is_file():
            return where.read_text(encoding="utf-8")
    return None


def theme_label(row: dict) -> str:
    from at.i18n import active_code

    labels = row.get("labels")
    if isinstance(labels, dict):
        return str(labels.get(active_code()) or labels.get("en_US") or row.get("id"))
    return str(row.get("id"))


# ------------------------------------------------------------- the doors ---

def served(directory: Path, name: str) -> Path | None:
    """A file of `directory` resolved by BARE NAME, or None.

    Nothing the caller sends is ever joined as a path: a name carrying a
    separator, or naming the directory itself, is refused before the disk is
    touched. That is the whole reason every file route takes one segment.
    """
    if not name or name.startswith(".") or "/" in name or "\\" in name:
        return None
    where = directory / name
    return where if where.is_file() else None


def hosted(key: str) -> tuple[Path, str] | None:
    """A hosted dependency by its key, with the hash the manifest pinned.

    The manifest is the pin: it names the package, the version and the sha256 of
    every file, so what leaves here can be checked against what was installed
    (§3, Dependência externa).
    """
    if not key or key.startswith(".") or "/" in key or "\\" in key:
        return None
    manifest = VENDOR / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        rows = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
    except (OSError, json.JSONDecodeError):
        return None
    entry = rows.get(key)
    if not isinstance(entry, dict):
        return None
    where = VENDOR / f"{key}.woff2"
    if not where.is_file():
        return None
    if _pinned(key, where) != entry.get("sha256"):
        return None
    return where, str(entry.get("version", ""))


_PINNED: dict[str, str] = {}


def _pinned(key: str, where: Path) -> str:
    """The file's digest, read once per process — a file on this disk does not
    change under a running server, and re-hashing 372 KB per request would be
    work nobody asked for."""
    if key not in _PINNED:
        _PINNED[key] = hashlib.sha256(where.read_bytes()).hexdigest()
    return _PINNED[key]


# --------------------------------------------------------- the transport ---

def basic_allowed() -> bool:
    """Whether a person may come in through Basic (§3, Configurações gerais).

    It is a PERMISSION in the settings and never a secret: the file holds
    permission and adjustment, and no credential lives in it. Only a literal
    `true` turns it on — a value that is not one is a setting nobody made, and
    the folder answers with the safe side, which is off. A folder that has
    never chosen says nothing at all, and is off for the same reason.
    """
    return settings.get(BASIC_KEY, False) is True


def basic_pair(value: str) -> tuple[str, str] | None:
    """The name and the credential an `Authorization: Basic` header carries.

    Read by hand and never raising: a stranger may send anything in a header,
    and `base64`'s refusal has to be a refusal and not a request thread taken
    down. The pair is `name:credential`, split on the FIRST colon — a credential
    may carry one, and cutting it here would be this door deciding what the
    person meant (the comparison keeps every byte, `actors.authenticate`). A
    header with no colon at all is not a pair, and answers `None`.
    """
    try:
        raw = base64.b64decode(value.strip(), validate=True).decode("utf-8")
    except ValueError:
        # `binascii.Error` and `UnicodeDecodeError` are both `ValueError`, and
        # both mean the same thing here: what travelled was not a Basic pair.
        return None
    name, found, credential = raw.partition(":")
    return (name, credential) if found else None


# ------------------------------------------------------------------ api ---

# The entrance's own words (§3, Forms local). They are a list of their own
# because they travel in a payload of their own: the page that draws the
# entrance has no session to read `/api/state` with.
SESSION_WORDS = (
    "session_hint", "session_name", "session_credential", "session_enter",
    "session_refused", "session_needed",
)

# And what the entrance is handed: its words, plus the two the shell already
# uses. `brand` is the card's heading — the name of the thing being entered is
# the heading a person expects over a door, and it is written once for the whole
# product. `error` is there because the entrance can fail too: a request that
# never arrived is said in the page's own language, and a word missing on the
# FIRST screen AT ever shows would be the one nobody could miss.
ENTRY_WORDS = ("brand", "error", *SESSION_WORDS)

# The words the PAGE reads. They come from the catalog like everything else —
# the page writes none of its own (§3) — and they travel in every language, so
# switching the language costs no request.
#
# The entrance's words are among them, and that is not duplication: a session
# that dies under a running page brings the entrance back (the page's own 401
# hook), and a `/api/state` that replaced the labels without them would draw a
# second entrance with no words in it.
PAGE_WORDS = (
    # The BRAND was missing from this list, and the defect was invisible because
    # the one screen that draws it did not exist yet: the entrance's heading is
    # the brand, and the second entrance — the one a dead session brings back —
    # came out with an empty one. The panel's `#brand` was drawing nothing all
    # along.
    "brand",
    "tasks", "files", "tables", "settings", "general", "appearance", "language",
    "dark_mode", "dark_system", "dark_theme", "dark_light", "dark_dark",
    "motion", "themes", "no_project", "new_project", "delete_project",
    "move_to_project", "records", "hidden", "no_records", "error", "filter",
    "columns", "refers", "panel", "collapse_menu", "expand_menu",
    "back", "write", "leave_write", "saving",
    "saved", "save_failed", "language_name", "language_flag",
    "ft_text", "ft_markdown", "ft_python", "ft_json", "ft_yaml", "ft_shell",
    "ft_dockerfile", "ft_binary", "ft_other",
    # The interpreter's box, the switch that hides the balloon, and the ruler of
    # the demand filter (§4).
    "chat", "ask", "ask_hint", "proposal", "interpreter", "balloon",
    "risk", "risk_runs", "risk_waits", "risk_threshold", "risk_none",
    # The screens that move a role and a machine's credential — the two system
    # tables whose records are more than a form (§4, item 11).
    "people", "create", "new_role", "new_machine", "mint", "revoke", "token_once",
    "permission_pick", "unknown_permission", "unknown_hint", "credential_none",
    # The entrance's, because the entrance comes back when a session dies under
    # a running page (the 401 hook) — and it would come back wordless.
    *SESSION_WORDS,
)


def entry_payload(open_session: session.Session | None) -> dict:
    """Who is in, and the words the entrance needs before anybody is.

    It is the ONE public answer of the API, and it carries no table and no
    count: a page that described the folder to whoever can reach the port would
    be the folder read by whoever can reach the port. What it says is whether
    there is an entrance at all (`auth`) and, when there is one, who is past it.

    `auth` is not a detail: a folder with no row carrying a credential has
    nothing to prove, and an entrance drawn there would be a door that never
    opens — nobody could type anything that wins. The page tells "nobody is in"
    from "nobody can enter" by this boolean, and only one of the two draws a
    form.
    """
    return {
        "auth": actors.can_expose(),
        "actor": {"name": open_session.name} if open_session else None,
        "lang": i18n.active_code(),
        # The WHOLE language each word, like `/api/state` hands them: the page
        # picks by the language on screen and the server keeps owning the words.
        "labels": {key: i18n.labels(f"webapp.{key}") for key in ENTRY_WORDS},
    }


def state_payload() -> dict:
    row = active_theme(None)
    # The folder's versioning, when there is something to say about it (§4, item
    # 30). It travels written out in every language, like the themes' own
    # description: the page draws the sentence the server hands it, and a folder
    # AT versions hands NOTHING — the band has no words because there is nothing
    # wrong to name.
    unversioned = versioning.phrase()
    return {
        "lang": i18n.active_code(),
        "origin": i18n.active_origin(),
        "labels": {key: i18n.labels(f"webapp.{key}") for key in PAGE_WORDS},
        # WHETHER THE INTERPRETER IS ON is the CORE's switch (`nlu.enabled`), and
        # the page reads it to know what to draw: off, there is no box, no balloon
        # and no chat — the whole function is gone, and nothing else is.
        "interpreter": nlu.enabled(),
        # THE RULER'S NUMBERS. The threshold is the one the demand filter will
        # honour (§4); the marks are the risks the product DECLARES, and today
        # there are none — the permission catalogue is item 11. The page draws
        # what it is handed and invents no risk.
        "risk": {"threshold": risk.threshold(), "marks": risk.declared()},
        # `None` is the answer for a folder under versioning, and it is not the
        # same as absent: the page tells "nothing to say" from "not here yet"
        # exactly the way it does with a session.
        "versioning": i18n.labels(unversioned) if unversioned else None,
        "theme": row.get("id") if row else None,
        "themes": [
            {"id": theme.get("id"), "label": theme_label(theme),
             "side": "dark" if theme.get("side") == "dark" else "light",
             # The theme describes ITSELF, one description per side: the page
             # shows the one being worn, and follows the swap without asking.
             "desc": theme.get("desc") if isinstance(theme.get("desc"), dict) else None}
            for theme in theme_rows()
        ],
        "tables": [
            {"key": declared.get("id"),
             "label": tables.table_name(str(declared.get("id")), many=True),
             "type": declared.get("type"),
             "count": len(tables.rows(str(declared.get("id"))))}
            for declared in schema.declared()
        ],
        # A DECLARED type → the table that declares it. A reference to something
        # is followed through here, so a page asks for the TYPE and never guesses
        # a table by its name.
        "types": {
            str(declared["type"]): str(declared["id"])
            for declared in schema.declared()
            if isinstance(declared.get("type"), str)
        },
    }


def _declared_fields(table: str) -> dict:
    declared = schema.of(table) or {}
    declared = declared.get("fields")
    return declared if isinstance(declared, dict) else {}


def _label_key(table: str, name: str) -> str | None:
    key = schema.field(table, name).get("label")
    return key if isinstance(key, str) else None


def _field_payload(table: str, name: str, field: dict) -> dict:
    """One field of the schema, as the page reads it.

    `labels` carries EVERY language, not the active one: the page switches
    language without asking again, and the words stay the server's (§3).
    """
    key = _label_key(table, name)
    refs = field.get("ref") or []
    choices = field.get("enum") if isinstance(field.get("enum"), dict) else {}
    return {
        "name": name,
        "labels": i18n.labels(key) if key else None,
        # The closed vocabulary, each value already written out in every
        # language: the picker draws the word, and the write sends the VALUE.
        "enum": {
            value: (i18n.labels(choices[value]) if isinstance(choices.get(value), str) else None)
            for value in choices
        },
        "type": field.get("type"),
        "primary": schema.primary(table) == name,
        "filterable": bool(field.get("filterable")),
        "searchable": bool(field.get("searchable")),
        "narrow": bool(field.get("narrow")),
        "editable": bool(field.get("editable")),
        "required": bool(field.get("required")),
        "max_length": field.get("max_length"),
        "hide": field.get("hide") or [],
        "refs": [
            {"key": target,
             "labels": i18n.labels(schema.name_key(target, many=True)) if schema.name_key(target) else None}
            for target in refs
        ],
    }


def _references(table: str, name: str, row: dict) -> list[dict]:
    """The references the VALUE carries, so a cell can draw a link to the thing
    it names instead of to the word — the page never parses an id."""
    field = schema.field(table, name)
    targets = field.get("ref") or []
    value = row.get(name)
    if not targets or value is None:
        return []

    def one(target: str, number: object) -> dict | None:
        found = store.find(target, number) if isinstance(number, int) else None
        if found is None:
            return None
        title = tables.title(target, found)
        return {"key": target, "id": number, "title": title, "shown": title}

    if isinstance(value, list):
        # A field that may point at more than one table stores the PAIR
        # (`["project", 3]`); a list field stores the bare numbers.
        if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
            return [entry for entry in (one(value[0], value[1]),) if entry]
        return [entry for item in value if (entry := one(targets[0], item))]
    return [entry for entry in (one(targets[0], value),) if entry]


def _schema_payload(table: str) -> list[dict]:
    """The table's declared fields, as the page reads them."""
    return [
        _field_payload(table, name, field)
        for name, field in _declared_fields(table).items()
        if isinstance(field, dict)
    ]


def _stored(table: str, name: str, value: object) -> object:
    """The stored value a form starts from — and NOTHING for the field the engine
    does not hand over.

    `tables.raw_of` refuses the hashed field by name, and that refusal is the
    answer: a cell draws the mask and a form asks for a new credential, so what
    the page carries is what it may draw. Every OTHER refusal keeps travelling —
    this is the page obeying the engine's rule, not a second rule of its own.
    """
    try:
        return tables.raw_of(table, name, value)
    except tables.TableError as refused:
        if refused.key != "error.hashed_value":
            raise
        return None


def _record(table: str, row: dict) -> dict:
    number = store.number_of(row)
    fields = _declared_fields(table)
    return {
        "id": number,
        **_says(table, row),
        "shown_id": tables.format_id(table, number) if number is not None else "",
        "title": tables.title(table, row),
        "fields": [
            {
                "name": name,
                "type": field.get("type"),
                # The value as a person reads it; `raw` as it is stored, so a
                # field that is going to be edited starts from the truth — and
                # the hashed field is handed over by nobody, so a credential
                # never reaches the wire (`_stored`).
                "value": tables.format_id(table, number) if name == "id"
                         and number is not None
                         else tables.text_of(table, name, row.get(name)),
                "raw": _stored(table, name, row.get(name)),
                "refs": _references(table, name, row),
            }
            for name, field in fields.items()
            if isinstance(field, dict)
        ],
    }


def _says(table: str, row: dict) -> dict:
    """What the row has to be TOLD, over what the fields already say (§4, item 11).

    Two facts of the two system tables do not fit the generic shape, and both are
    read by the screen that shows them:

    - a `role` that names a permission the catalogue does not have **does not take
      AT down**: it says so, and the saying is what gets read. What the record
      carries is the NAMES the catalogue does not know, so the screen lists them —
      a write that dropped them silently, or kept them silently, would be the
      screen deciding what §4 left to the person;
    - an `actor`'s credential is a derivation that NEVER leaves its row, so the
      payload cannot tell "there is one" from "there is none" by its value (the
      cell draws the mask either way, and `_stored` hands over nothing). What the
      screen that mints and revokes needs is exactly that boolean, and the engine
      is the one that knows it.

    Anything else carries the generic shape and nothing more.
    """
    if table == "role":
        return {
            "unknown": [
                name
                for name in permissions.carried(row)
                if not permissions.is_known(name)
            ]
        }
    if table == "actor":
        return {"has_credential": bool(row.get("credential"))}
    return {}


def catalogue_payload() -> dict:
    """The closed list, as the screen that moves a role reads it.

    One entry per permission — the machine name, the label a person reads and the
    risk it declares — and never a guess: whatever the catalogue does not name is
    not here, which is exactly what makes the screen able to say that a role names
    something that does not exist. The order is the catalogue's, so the picker
    draws the list it was handed and sorts nothing.
    """
    entries = []
    for name in permissions.all_permissions():
        obj, _, action = name.partition(":")
        entries.append(
            {
                "key": name,
                # The PARTS as well as the whole: the screen groups the closed
                # list by object, and splitting the label here would be the page
                # parsing a sentence the catalogue already knows how to cut.
                "object": obj,
                "object_label": permissions.object_label(obj),
                "action": action,
                "action_label": permissions.action_label(action),
                "label": permissions.label(name),
                "risk": permissions.risk(name),
            }
        )
    return {"permissions": entries}


def _worded(answer: dict) -> dict:
    """The engine answers with CATALOG KEYS; the wire carries the words.

    A refusal is read by a person, and the page prints what it is handed — so the
    translation happens here, where the catalog is, and never in the page (§3).
    """
    key = answer.get("error")
    if isinstance(key, str) and key.startswith(("prose.", "webapp.")):
        return {**answer, "error": i18n.tr(key)}
    return answer


def table_payload(table: str, show_all: bool) -> dict:
    return {
        "key": table,
        "name": tables.table_name(table, many=True),
        "filter": None,
        "fields": _schema_payload(table),
        # WHICH COLUMNS A LISTING CARRIES IS THE TABLE'S, not whoever wrote the
        # page (§4, "campos padrão na exibição"): the rest steps aside into the
        # pill, where the person can bring it back.
        "columns": schema.columns(table),
        "records": [_record(table, row) for row in tables.rows(table, show_all=show_all)],
    }


# ------------------------------------------------------------- handler ---

# What the session of the request being served starts as: nobody asked yet. It
# is a sentinel and not `None` because `None` is an ANSWER — the folder that
# asks nobody, and the request that proved nobody — and the cache in `_in`
# would then never keep anything.
_UNASKED = object()


class Handler(BaseHTTPRequestHandler):
    server_version = "at-webapp/1"

    # The session of the request being served, until `_in` computes it.
    _held: object = _UNASKED

    def handle_one_request(self) -> None:
        """One request — and the session of THAT one starts empty.

        The look `_in` keeps is the request's and cannot outlive it: `_gate`
        asks it for the entrance and `_may` for the ceiling, and two requests
        that shared one would be two requests one admission answered for. The
        handler closes after each request today (`protocol_version` is HTTP/1.0,
        so there is no keep-alive), and this is not a statement about that: it
        is where the emptying belongs, whatever the protocol does later.
        """
        self._held = _UNASKED
        super().handle_one_request()

    # ------------------------------------------------------------ output --

    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # Nothing here is worth a cache: the page is served fresh on purpose, so
        # that the language and the theme the server resolved are the ones drawn.
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _text(self, text: str, ctype: str = "text/plain; charset=utf-8",
              status: int = 200, extra: dict | None = None) -> None:
        self._send(status, text.encode("utf-8"), ctype, extra)

    def _json(self, payload: object, status: int = 200,
              extra: dict | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _page(self, path: Path, status: int = 200) -> None:
        """An HTML document — the only place the policy travels, because it is
        the only place that runs anything."""
        try:
            body = path.read_bytes()
        except OSError:
            # "Not built" and "broken" are different things, and the status is
            # what tells a monitor which of the two it is. The policy comes along
            # even here: it belongs to the route, not to the answer's luck.
            self._text("UI not built — run: cd at/ui/webapp && npm ci && npm run build\n",
                       status=500, extra={"Content-Security-Policy": CSP})
            return
        self._send(status, body, "text/html; charset=utf-8",
                   {"Content-Security-Policy": CSP})

    def _file(self, path: Path, hosted_version: str | None = None) -> None:
        extra = {"X-Hosted": hosted_version} if hosted_version else None
        self._send(200, path.read_bytes(),
                   _CONTENT_TYPES.get(path.suffix, "application/octet-stream"), extra)

    def _not_found(self) -> None:
        self._text("not found\n", status=404)

    # ---------------------------------------------------------- the entrance --

    def _asks(self) -> bool:
        """Whether this folder asks anybody to enter.

        It is `actors.can_expose()` — the folder with somebody to enter it —
        read HERE and not only in `run`: the command refusing to take the port
        says nothing about a server somebody built by hand, and a gate that
        closed over a folder with nothing to prove would be a door with no key
        in it. §3: with no authentication configured, AT listens on loopback
        and asks nothing.
        """
        return actors.can_expose()

    def _in(self) -> session.Session | None:
        """The session this request carries, or `None`.

        Three transports, in the order they cost: the cookie a Forms entrance
        opened, and then the two headers, which prove themselves on every
        request (`_proved`). With no authenticator at all, `None` — and it is
        then that `_gate` lets the request through: this is the folder that asks
        nothing, and it is exactly where the API answers as it always did.

        **One look per request.** `_gate` asks this before the route runs and
        `_may` asks it again for the ceiling, and for the two header transports
        each ask is a derivation — the price the token-alone door pays, and one
        this request pays once. The answer is kept until `handle_one_request`
        empties it, and that is where the keeping belongs: to the REQUEST.
        """
        if self._held is _UNASKED:
            self._held = self._opened()
        return self._held

    def _opened(self) -> session.Session | None:
        """Who this request proved, asked of the transports once.

        **The registry is not consulted when the Forms is off.** The cookie a
        Forms entrance opened is the LOCAL door (§3), and on the container path
        the person's door is the gate's — so with the switch committed
        (`gate.on_gate`) a cookie left over from before proves nothing, and the
        session it names is not read. It is the same sentence the switch is made
        of, one request at a time: Forms off, the gate on.
        """
        if not self._asks():
            return None
        if not gate.on_gate():
            held = self.server.sessions.get(session.token_of(self.headers.get("Cookie")))
            if held is not None:
                return held
        return self._proved()

    def _proved(self) -> session.Session | None:
        """The session a header proves for this request alone.

        The gate first, because it is the transport whose value is a claim and
        not a proof: the name is read only when the secret beside it says the
        request came through the Caddy (`_sealed`), and what it proves is the
        row that name wears (`actors.asserted`) — Authelia proved the person, and
        AT resolves who they are.

        Then `Basic`, a PERSON's name and credential — the Forms credential by
        the other transport, so the door is the engine's
        (`actors.authenticate`) — read only while the folder's permission says
        so. And `Bearer`, a MACHINE's token alone, whose door is the agent's
        (`actors.authenticate_agent`). None of them is looked up in the
        registry: all prove on every request, and what comes back is a session
        held by nobody (`session.from_row`).

        **With the Forms off, Basic goes with it.** It is the same credential by
        another transport (§3), which is exactly why the switch takes it out with
        the Forms: on the container path the person's credential is Authelia's,
        and a folder that kept taking it here would be keeping the door the gate
        replaced. `Bearer` stays, because it is not a person's door at all — it
        is the machine's, and no machine enters by Forms.
        """
        asserted = self.headers.get(GATE_IDENTITY)
        if asserted is not None:
            row = actors.asserted(asserted) if self._sealed() else None
            return session.from_row(row) if row else None
        header = self.headers.get("Authorization")
        if not header:
            return None
        scheme, _, value = header.partition(" ")
        scheme = scheme.lower()
        if scheme == "basic" and basic_allowed() and not gate.on_gate():
            pair = basic_pair(value)
            row = actors.authenticate(*pair) if pair else None
        elif scheme == "bearer":
            row = actors.authenticate_agent(value.strip())
        else:
            return None
        return session.from_row(row) if row else None

    def _sealed(self) -> bool:
        """Whether the gate secret this request carries is the folder's one.

        It is the comparison §7b is made of, and it answers `False` when the
        folder has no gate at all: without a secret drawn there is nothing the
        Caddy could have attached, and a header claiming an identity is a header
        nobody sealed. The comparison is constant-time, because the value is a
        secret and the clock is a way of reading one.
        """
        secret = caddy.gate_secret()
        carried = self.headers.get(caddy.GATE_HEADER) or ""
        return secret is not None and secrets.compare_digest(carried, secret)

    def _forged(self) -> bool:
        """Whether this request asserts an identity the gate did not seal."""
        return self.headers.get(GATE_IDENTITY) is not None and not self._sealed()

    def _challenge(self) -> dict:
        """The `WWW-Authenticate` a refused Basic attempt is owed, if any.

        It answers an ATTEMPT and nothing else. The header is what makes a
        browser open its own dialog, and one travelling with the page's own 401
        would pop that dialog over the entrance AT drew — so the page, which
        sends no `Authorization`, is never challenged. A folder that does not
        take Basic has nothing to offer and challenges nobody either.
        """
        header = self.headers.get("Authorization") or ""
        if not basic_allowed() or header.partition(" ")[0].lower() != "basic":
            return {}
        return {"WWW-Authenticate": f'Basic realm="{REALM}"'}

    def _gate(self) -> bool:
        """Whether this request reaches the API — answering, when it does not.

        Called by BOTH dispatching halves, and that is the whole reason it is a
        method: `do_GET` walks `_route` and `do_POST` dispatches by itself, so a
        gate written into one of them would leave the other's doors open. What
        sits ABOVE it is the page, the look and the entrance — the three things
        that have to answer before anybody is in.

        **The forged identity is refused before the question of session is
        asked**, and it is answered differently on purpose: "you are not in" is
        401 and is what a stranger gets, and "that identity is not one AT
        takes" is 403 and names the gate (§7b). The two are not the same failure
        — the second is what a person sees when the Caddy's secret and the
        folder's stopped agreeing, and it has to say so instead of looking like
        a login that did not happen.

        **And a fallen gate closes AT before either question is asked.** The
        folder is on the container path — the switch committed, and that is a
        fact of the folder and not of this process — so the API answers the
        sentence §6 names and nothing else. It is asked HERE, per request, and
        that is deliberate: the WebApp is a container that comes up BEFORE the
        edge that fronts it (§7a's order), so asking at start-up would make a
        committed folder refuse to come up at all; and a gate that falls while
        the environment is standing is noticed by the request that finds nothing
        answering, never by a container that does not restart itself.
        """
        if gate.on_gate() and not gate.standing():
            print(i18n.tr("services.gate.down"))
            self._json({"error": i18n.tr("services.gate.down")}, 503)
            return False
        if self._forged():
            self._json({"error": i18n.tr("webapp.gate_refused")}, 403)
            return False
        if not self._asks() or self._in() is not None:
            return True
        self._json({"error": i18n.tr("webapp.session_needed")}, 401, self._challenge())
        return False

    def _may(self, permission: str) -> bool:
        """Whether the actor this request proved carries `permission` — and the
        refusal, when it does not.

        It is the STRICT ceiling (§4, item 11): what the role carries is what the
        actor reaches, and a permission the role does not name is one the route
        is refused for. The same door caps the person and the machine — the
        machine's token is the credential of a row that wears a role like any
        other — and an actor pointing at no role reaches nothing, because
        `permissions.carries` fails CLOSED.

        **It sits BESIDE `_gate` and answers a different question.** The gate
        refuses the request that proved nobody (401) and this one refuses the
        request that proved itself and carries too little (403). Both are asked
        with the ROUTE, which is why the demand is written where the route is:
        the one route that cannot say it up front — the table write, whose action
        travels in the body — asks it as soon as the action is read.

        The role is resolved from the ACTOR's row here (`actors.role_of`), on
        every request and never from the session: what a role carries is a fact
        of the store, and a session that kept it would hand a request the ceiling
        of a moment ago.

        The folder that asks nobody has no session to read and keeps answering as
        it always did (§3) — which is what `_asks` says, and the reason this is
        not a gate over the whole server.
        """
        held = self._in()
        if not self._asks() or held is None:
            return True
        row = self._actor()
        if row is not None and actors.may(row, permission):
            return True
        self._json(
            {
                "error": i18n.tr(
                    "permission.denied", permission=permissions.label(permission)
                )
            },
            403,
        )
        return False

    def _actor(self) -> dict | None:
        """The row this request proved, or `None` — the session's own hop back to
        the store.

        `_in` answers WHO, with the row's NUMBER; the ceiling is read off the ROW,
        and this is the one place that makes the hop. It is what `_may` resolves
        the role from, and what the interpreter's door is handed — one hop, so a
        route imposing a ceiling and the door imposing it cannot disagree.
        """
        held = self._in()
        if not self._asks() or held is None or held.actor is None:
            return None
        return store.find("actor", held.actor)

    def _post_session(self) -> None:
        """The entrance: the credential is proved, and a session opens.

        It is the one write that does not need a session, because it is the one
        that makes one — and it obeys the same body guards as every other write,
        through the same door (`_body`), because it is the same page that sends
        it.

        A refusal is 401 in the catalog's words: the same sentence whether the
        name is unknown or the credential is wrong, so the answer says neither.

        **And on the container path this door does not open at all.** It is the
        Forms entrance, and the Forms is what the switch takes off the path — a
        folder that kept handing out session cookies would be keeping the door
        one switch served to close. It is refused here rather than hidden from
        the page, because the page is not the thing that decides who enters.
        """
        if gate.on_gate():
            self._json({"error": i18n.tr("webapp.forms_off")}, 403)
            return
        payload = self._body()
        if payload is None:
            return
        name, credential = payload.get("name"), payload.get("credential")
        if not isinstance(name, str) or not isinstance(credential, str):
            self._json({"error": "bad request"}, 400)
            return
        row = actors.authenticate(name, credential)
        if row is None:
            self._json({"error": i18n.tr("webapp.session_refused")}, 401)
            return
        opened = self.server.sessions.open(row)
        self._json(
            {"actor": {"name": opened.name}},
            extra={"Set-Cookie": session.cookie_header(opened)},
        )

    # -------------------------------------------------------------- verbs --

    def do_GET(self) -> None:  # noqa: N802 — the name http.server dispatches on
        try:
            self._route()
        except tables.TableError as refused:
            # A declaration the folder carries is refused in the ENGINE's words,
            # in the active language, as the write path already answers one — a
            # route that died instead would leave the page with nothing to draw
            # AND nothing to say, which is the blank screen the engine refuses.
            self._json({"error": str(refused)}, 400)

    def _route(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        segments = [part for part in parsed.path.split("/") if part]

        if not segments:
            self._page(UI_DIR / "index.html")
            return

        head, rest = segments[0], segments[1:]

        if head == "base.css" and not rest:
            self._file(ASSETS / "base.css")
            return

        if head == "theme.css" and not rest:
            css = theme_css(query.get("theme", [None])[0], "dark" in query)
            if css is None:
                self._not_found()
                return
            self._text(css, "text/css; charset=utf-8")
            return

        if head == "js" and len(rest) == 1:
            self._static(ASSETS / "js", rest[0])
            return

        if head == "icons" and len(rest) == 1 and rest[0].endswith(".svg"):
            self._static(ICONS, rest[0])
            return

        if head == "assets" and len(rest) == 1:
            self._static(UI_ASSETS, rest[0])
            return

        if head == "vendor" and len(rest) == 1:
            found = hosted(rest[0])
            if found is None:
                self._not_found()
                return
            self._file(*found)
            return

        if head == "api":
            self._get_api(rest, query)
            return

        # WHAT THE SERVER DOES NOT SERVE IS THE PAGE. The address names a view —
        # `/task`, `/task/3`, `/project/2`, `/file/kb/note.md`, `/settings` — and
        # the page is who knows its own vocabulary: to answer 404 here, the server
        # would have to keep a second copy of that list, which is the copy that
        # drifts. A name the page does not know is ignored there, like a saved one,
        # and the address is corrected to what was opened: no address lies about
        # what it shows. The routes ABOVE are the server's own, and those keep
        # their own answers, 404 included.
        self._page(UI_DIR / "index.html")

    def do_POST(self) -> None:  # noqa: N802
        segments = [part for part in urlparse(self.path).path.split("/") if part]
        # The entrance first, and above the gate: it is the write that OPENS a
        # session, so it is the one write that cannot already have one.
        if segments == ["api", "session"]:
            self._post_session()
            return
        if not self._gate():
            return
        # The writes demand their permissions the way the reads do — through the
        # same door (`_may`), asked with the route. The table write is the one
        # that cannot say it here: which of the two it is travels in the body.
        if segments == ["api", "file"]:
            if not self._may("prose:edit"):
                return
            self._post_file()
            return
        if segments == ["api", "ask"]:
            if not self._may("nlu:ask"):
                return
            self._post_ask()
            return
        if segments == ["api", "agent"]:
            self._post_agent()
            return
        if len(segments) == 3 and segments[0] == "api" and segments[1] == "table":
            self._post_table(segments[2])
            return
        self._not_found()

    # HEAD is GET without the body, which `_send` already handles. The other
    # verbs are refused OUT LOUD: a server that answers a PUT with a page teaches
    # a stray tool that it wrote something.
    do_HEAD = do_GET  # noqa: N815

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802
        self._method_not_allowed()

    def _method_not_allowed(self) -> None:
        self._send(405, b"not allowed\n", "text/plain; charset=utf-8",
                   {"Allow": "GET, HEAD, POST"})

    def _static(self, directory: Path, name: str) -> None:
        where = served(directory, name)
        if where is None:
            self._not_found()
            return
        self._file(where)

    def _get_api(self, rest: list[str], query: dict) -> None:
        # Who is in, and above the gate: the page asks this before it has a
        # session, and the entrance cannot be drawn without it.
        if rest == ["session"]:
            self._json(entry_payload(self._in()))
            return

        if not self._gate():
            return

        # Every route below DEMANDS a permission, and the object is the route's
        # own: the shell reads the settings it draws, a project route reads
        # projects, `Arquivos/` reads prose, and a table route reads the table it
        # names — the action being the one the route performs (`list` for a
        # listing). The demand is written HERE, at the route, because the route
        # is what knows it.
        if rest == ["state"]:
            if not self._may("setting:read"):
                return
            self._json(state_payload())
            return

        if rest == ["projects"]:
            if not self._may("project:list"):
                return
            self._json(projects.tree() if projects.available() else [])
            return

        if rest == ["orphans"]:
            if not self._may("task:list"):
                return
            self._json(self._orphans_payload())
            return

        if len(rest) == 2 and rest[0] == "project":
            if not self._may("project:view"):
                return
            self._get_project(rest[1])
            return

        if rest == ["catalogue"]:
            # The closed list is the ROLE table's vocabulary: a screen that moves
            # a role reads it to draw the picker, so reading it is `role:list` —
            # the same permission that lets the person read the roles it names.
            if not self._may("role:list"):
                return
            self._json(catalogue_payload())
            return

        if rest == ["tree"]:
            if not self._may("prose:read"):
                return
            self._json({
                "root": "",
                "files": [
                    {"path": path, "bucket": prose.bucket(path)}
                    for path in prose.listed()
                ],
            })
            return

        if rest == ["file"]:
            if not self._may("prose:read"):
                return
            self._get_file(query.get("path", [""])[0])
            return

        if len(rest) == 2 and rest[0] == "table":
            table = rest[1]
            if schema.of(table) is None:
                # A table the folder does not declare is a 404 and never a 403:
                # the objects that ARE a table are the DECLARED ones, so the
                # catalogue names no permission for this name and nobody could
                # carry it — refusing it as a permission would be pretending a
                # row exists to be denied.
                self._json({"error": f"unknown table: {table}"}, 404)
                return
            if not self._may(f"{table}:list"):
                return
            self._json(table_payload(table, show_all="all" in query))
            return

        self._not_found()

    def _get_project(self, asked: str) -> None:
        number = tables.number_of("project", asked)
        payload = projects.page(number) if number is not None else None
        if payload is None:
            self._json({"error": "unknown project", "project": asked}, 404)
            return
        payload["fields"] = _schema_payload("task")
        payload["records"] = [_record("task", row) for row in payload.pop("rows")]
        self._json(payload)

    def _orphans_payload(self) -> dict:
        rows = projects.orphans()
        return {
            "key": "task",
            "title": i18n.tr("webapp.no_project"),
            "filter": None,
            "fields": _schema_payload("task"),
            "records": [_record("task", row) for row in rows],
        }

    def _get_file(self, path: str) -> None:
        answer = prose.read(path)
        if answer is None:
            self._json({"error": i18n.tr("prose.not_served")}, 404)
            return
        if answer.get("reason"):
            answer["reason"] = i18n.tr(str(answer["reason"]))
        self._json(answer)

    def _post_file(self) -> None:
        payload = self._body()
        if payload is None:
            return
        rel, text, base = payload.get("path"), payload.get("text"), payload.get("base")
        if not all(isinstance(value, str) for value in (rel, text, base)):
            self._json({"error": "bad request"}, 400)
            return
        status, answer = prose.write(rel, text, base)
        self._json(_worded(answer), status)

    def _post_ask(self) -> None:
        """One sentence through the interpreter's door: the proposal, and then.

        The door is `at.ui.ask`, which the `cli` reads too — the page walks the
        same road (`nlu.propose` for the reading, the table engine for the
        writing) and gains no rule of its own. What travels back is what a person
        reads: the proposal in the engine's words, the answer after it, the
        question when the sentence was ambiguous, or the reason when it was not
        read at all. A refusal is an ANSWER here and not a failure of the request:
        it is a sentence the conversation keeps, and the page prints it as it
        stands.
        """
        payload = self._body()
        if payload is None:
            return
        sentence = payload.get("text")
        if not isinstance(sentence, str) or not sentence.strip():
            self._json({"error": "bad request"}, 400)
            return
        # The ACTOR comes along: the door owns the ceiling (§5, "o que ela pode
        # propor é o que ela já pode fazer"), and it is the same door the balloon,
        # the chat and `at ask` read — so the refusal lands on every surface at
        # once and none of them keeps a ceiling of its own. `None` is a folder
        # asking nobody, and there the door answers as it always did.
        result = door.ask(sentence, actor=self._actor())
        self._json({"kind": result.kind, "proposal": result.proposal, "text": result.text})

    def _post_agent(self) -> None:
        """The machine credential's door: mint it, give it again, take it away.

        It is the surface item 10 left without one, and it is a route of its own
        for the reason the credential is a thing of its own: an `agent` could only
        be born through the table door with the token TYPED, and a token is not
        something a person types — it is something AT draws and hands over once.

        The permission is the ACTION's, asked here because the action travels in
        the body: minting a new machine is the `actor` CREATE and re-issuing or
        revoking one is the `actor` EDIT. The three are one door because they are
        one subject — the machine's credential — and the vocabulary a person reads
        is the screen's, not the wire's.
        """
        payload = self._body()
        if payload is None:
            return
        action = payload.get("action")
        number = payload.get("id")
        if action == "mint":
            # A machine being BORN is a create; one being given a new token is an
            # edit. Two acts under one word, and the row is what tells them apart.
            if number is None:
                if not self._may("actor:create"):
                    return
                try:
                    row, token = actors.mint_agent(payload.get("name"), payload.get("role"))
                except (actors.MachineError, tables.TableError) as refused:
                    self._json({"error": str(refused)}, 400)
                    return
            else:
                if not self._may("actor:edit"):
                    return
                try:
                    row, token = actors.reissue_agent(number)
                except (actors.MachineError, tables.TableError) as refused:
                    self._json({"error": str(refused)}, 400)
                    return
            self._json({"record": _record("actor", row), "token": token})
            return
        if action == "revoke":
            if not self._may("actor:edit"):
                return
            try:
                row = actors.revoke_agent(number)
            except (actors.MachineError, tables.TableError) as refused:
                self._json({"error": str(refused)}, 400)
                return
            self._json({"record": _record("actor", row)})
            return
        self._json({"error": f"unknown action: {action}"}, 400)

    def _post_table(self, table: str) -> None:
        if schema.of(table) is None:
            self._json({"error": f"unknown table: {table}"}, 404)
            return
        payload = self._body()
        if payload is None:
            return
        action = payload.get("action")
        if action not in TABLE_WRITES:
            # The route answers these two and no other, and it says so before it
            # demands anything: the demand is one of `tables.ACTIONS`, and an
            # action the engine does not have is a 400 and not a permission the
            # role could carry (`create`, `edit` — a closing and a deletion are
            # not offered by this route yet).
            self._json({"error": f"unknown action: {action}"}, 400)
            return
        # The permission is the ACTION's, and it is asked here because this is
        # where the action exists: the route is one, and what it does is two.
        if not self._may(f"{table}:{action}"):
            return
        values = payload.get("set")
        values = {str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {}
        try:
            if action == "create":
                row = tables.create(table, values)
            else:
                row = tables.edit(table, payload.get("id"), values)
        except tables.TableError as error:
            self._json({"error": str(error)}, 400)
            return
        except files.ReadOnly as error:
            self._json({"error": f"read-only: {error.where}"}, 403)
            return
        self._json({"record": _record(table, row)})

    def _body(self) -> dict | None:
        """The request body, or None when the request was already answered.

        Three guards, and each closes a different door: the size stops a stream
        from becoming memory, the content type tells our page's write apart from
        a form post, and the origin authority tells it apart from another site's.
        """
        length = 0
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            self._json({"error": "body too large"}, 413)
            return None

        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._json({"error": "content type must be application/json"}, 415)
            return None

        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self._json({"error": "cross-origin write refused"}, 403)
            return None

        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json({"error": "body is not JSON"}, 400)
            return None
        if not isinstance(payload, dict):
            self._json({"error": "body must be an object"}, 400)
            return None
        return payload

    # The server's own log line is noise on a phone screen and in a journal; the
    # surface that matters is the page.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


# ------------------------------------------------------------------ run ---

class Server(ThreadingHTTPServer):
    """The server, with the sessions it holds.

    The registry lives HERE and not in a module-level name: a server is one AT
    on one port, and two of them — which is what the suite builds, one per test
    — are two of them, each with its own entrances open. A shared registry would
    hand one test's session to another test's folder.
    """

    def __init__(self, address: tuple[str, int],
                 handler: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(address, handler)
        self.sessions = session.Sessions()


def loops_back(host: str) -> bool:
    """Whether that address is the local loop and nothing else (§3).

    `localhost` counts by name; everything else has to BE a loopback address,
    because a `127.0.0.1` spelled as a name is a name a resolver could answer
    with anything tomorrow — and AT refusing exposure is not a question it
    delegates to whatever `/etc/hosts` or a DNS server says today.
    """
    if host == LOOPBACK_NAME:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def make_server(port: int = DEFAULT_PORT, host: str = HOST) -> Server:
    return Server((host, port), Handler)


def run(port: int = DEFAULT_PORT, host: str | None = None,
        include_caddy: bool = False) -> int:
    """Put AT on a port — in HTTP on the loop, or behind the Caddy's TLS.

    Two refusals live here rather than in `make_server`, and both are the same
    promise from §3: exposing demands TLS, the TLS is the Caddy's, and without
    the flag there is no TLS at all — so an address outside the loop is refused,
    and so is the one address a certificate cannot be issued for. The raw server
    is what the route tests build, and it is not a hole: it is the folder that
    asks nothing, and `_asks` is where that is decided.
    """
    from at.i18n import tr

    # "Sem ator nenhum o AT não expõe" (§3, Acesso e exposição): a folder with
    # nobody to enter it does not open its page. The engine's row does not count
    # — it does not enter, the person does (`actors.can_expose`).
    if not actors.can_expose():
        print(tr("webapp.no_admin"))
        return 1

    where = host or (LOOPBACK_NAME if include_caddy else HOST)

    if include_caddy and caddy.wildcard(where):
        print(tr("caddy.address_needs_name", host=where))
        return 1

    if not include_caddy and not loops_back(where):
        # Without the flag, reaching beyond the loop would be HTTP with no TLS,
        # which §3 forbids in the same sentence that demands authentication.
        print(tr("caddy.outside_loopback"))
        return 1

    # Exposed, the WebApp takes an EPHEMERAL port on the loop and the Caddy holds
    # the port the person reaches: two processes cannot share one, and moving the
    # WebApp is the move that keeps the exposed address the stable one.
    try:
        server = make_server(0 if include_caddy else port,
                             HOST if include_caddy else where)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        # A port somebody else is already serving on is the way this fails in
        # practice — the PoC on 12345, or a second AT — and the bare `OSError:
        # Address already in use` names neither the port nor a way out. AT
        # says both, and the two ways out are the person's: another port, or
        # freeing this one.
        print(tr("webapp.port_taken", port=port))
        return 1

    process = None
    if include_caddy:
        if not caddy.unpacked():
            print(tr("caddy.unpacking", where=caddy.directory()))
        if caddy.ensure() is None:
            server.server_close()
            print(tr("caddy.no_payload", platform=caddy.label()))
            return 1
        config = caddy.write_caddyfile(where, port, server.server_address[1])
        process = caddy.start(config)
        if not caddy.started(process):
            # The Caddy holds the port the person reaches, so its failure is the
            # command's: an AT that answered with a URL here would be announcing
            # an address nothing is on.
            server.server_close()
            print(tr("webapp.port_taken", port=port))
            return 1

    url = f"https://{where}:{port}" if include_caddy else f"http://{where}:{port}"
    print(tr("caddy.serving", url=url) if include_caddy
          else tr("webapp.serving", url=url))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl-C is how a person stops a server; it is not a failure.
        pass
    finally:
        caddy.stop(process)
        server.server_close()
    return 0
