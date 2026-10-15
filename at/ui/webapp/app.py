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
forma de autenticação configurada, o AT escuta apenas 127.0.0.1". This is the
state a raw `make_server` serves in — which is what the route tests build.

**And the folder with no administrator is a PAGE now** (TASK-176, fatia 3/3).
It is the same state and one step further: `at-cli webapp` used to refuse to
take the port there, and the way to the first administrator was a terminal —
`at-cli admin`. What the browser gets instead is the form that creates it,
drawn in the entrance's own place (`/api/session` answers `first`, the page
draws it, `POST /api/first` runs the same `actors.create_admin` the word does),
with the same two keys and the same strings. **§3's sentence is not weakened
by it**: without an actor the AT does not answer OFF THE LOOP — not through
`--host`, not behind the Caddy — and the route that writes without a session
refuses the request that did not come over the loop. The population is the one
the terminal already served: whoever is at the machine.

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

**Exposure is the default, and the WebApp never leaves the loop because of it.**
§3 says exposing demands authentication and TLS, that the TLS is Caddy's, and
that Caddy travels inside this binary — so `at-cli webapp` puts that Caddy in
front by default (`services/caddy.py`), and the WebApp behind it listens where
it always did, `127.0.0.1`, on a port nobody types. What the person reaches is
the Caddy's port, with AT's own certificate. `--no-caddy` is the one way back
to the loop alone, in HTTP — the shape a quick local run wants.

**The address is a choice of the folder's, and the loop is what it gets by
default.** `--host` says it for one run and `settings.json` says it for the
folder (`HOST_KEY`, `chosen_host`); with neither, AT answers on `127.0.0.1`,
which is the address this product recommends and the one it uses for itself.
**Leaving the loop is not refused here**, and the reason is that the same
address means two different things and this module cannot tell them apart: a
container's `0.0.0.0` is inside a network, behind the edge and the gate (§7b,
§7c), and a machine's `0.0.0.0` is on a LAN — and an app that guessed would
refuse the first or wave the second through. What answers for an address is the
network around it, and the environment's security note is where that is
evaluated.
"""

from __future__ import annotations

import base64
import errno
import hashlib
import ipaddress
import json
import os
import queue
import secrets
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote, urlparse

from at import __version__, convert, i18n, nlu
from at.core import (
    actions_audit,
    actors,
    assist,
    audit,
    backup,
    clock,
    files,
    gate,
    jobs,
    notifier,
    offline,
    paths,
    permissions,
    projects,
    push,
    reminder,
    risk,
    settings,
    strongbox,
    tables,
    versioning,
    vigia,
)
from at.data import schema, store
from at.prose import listing as prose
from at.services import authelia, caddy
from at.ui import ask as door
from at.ui.webapp import events, keys, session, strongbox_links

HOST = "127.0.0.1"
DEFAULT_PORT = 12345
DEFAULT_THEME = "at"

# The face of the loop, by name. It is the host the person reaches by default,
# and it is the only NAME this module answers for itself: with the Caddy in
# front, the name is what the certificate is issued for (§3), and `localhost` is
# the name that needs no resolver to mean this machine.
LOOPBACK_NAME = "localhost"

# **The bundle's own default** (TASK-177, 02/10/2026): the bundle now always
# brings Authelia up beside the Caddy, and Authelia refuses a session
# cookie domain with no dot that is not an IP — the exact shape `localhost`
# has (measured against the real binary, `authelia.valid_cookie_domain`). Every
# browser resolves a `.localhost` name to the loop on its own (RFC 6761), with
# no resolver this product controls, so the dot is bought for free.
GATE_LOOPBACK_NAME = "at.localhost"

# The key of `settings.json` that carries the address the folder answers on. It
# is the same shelf `basic_auth` sits on — an adjustment of the installation and
# never a credential — and it is the door for the person who wants AT to listen
# somewhere else: `127.0.0.1` is the default and what this product recommends,
# and what leaving it costs is the environment's security note's to say.
HOST_KEY = "webapp_host"

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

# The clock's thread, by name (§4, item 24). It is named because a thread with
# no name is a thread nobody can find: a person reading a dump of the process,
# and the test that proves the RAW server does not start one.
CLOCK_THREAD = "at-clock"

# Quanto tempo uma conexão `/api/events` fica sem escrever nada antes de
# mandar um comentário de keep-alive (TASK-128, fatia 2/3). `EventSource`
# ignora toda linha que começa com `:` — não dispara `onmessage` —, então o
# keep-alive não é um evento, é só o que mantém a conexão viva através de um
# proxy (o Caddy) que fecharia um socket ocioso por tempo demais, e o que
# deixa este processo notar uma aba que fechou sem esperar a próxima escrita
# na pasta vigiada.
EVENTS_HEARTBEAT = 20.0

# How much a write may carry. A table row is small; the ceiling is what stops a
# stranger's stream from becoming this process's memory.
MAX_BODY = 64 * 1024

# The four actions the table write answers (TASK-122, fatia 3/7 grew it from
# two to four). The engine has six (`tables.ACTIONS`); `list` and `view` are
# reads and have their own route. `cancel` and `delete` come with the
# confirmation the row menu asks before either reaches here — the row's own
# screen, never a second route: the permission ceiling below is already the
# ACTION's, read from the catalogue, so a closing and a deletion are refused
# the same way an edit is. It is the ROUTE's vocabulary, and it is what says
# which permission a write demands — the action is part of the permission, and
# this is the list of actions that may become one.
#
# **`_post_offline_sync` does NOT read this one** — it has its own
# (`OFFLINE_WRITES`), below, and growing this tuple must never widen that
# route's own.
TABLE_WRITES = ("create", "edit", "cancel", "delete")

# The two the OFFLINE QUEUE answers — `offline.QueueEntry`'s own closed list
# (TASK-162), and narrower than `TABLE_WRITES` on purpose: `offline.reconcile`
# has no branch for a `cancel` or a `delete`, and an entry of either shape
# would fall into its `edit` branch and silently reconcile as one — a closing
# or a deletion that reached the server as a no-op write. The row menu's two
# new doors (TASK-122) do not go through the fila: they write ONLINE, through
# `_post_table`, the moment the person confirms.
OFFLINE_WRITES = ("create", "edit")

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
    ".webmanifest": "application/manifest+json; charset=utf-8",
    # The nine `prose.IMAGE_EXT` names (TASK-167) — the bytes route
    # (`_get_file_bytes`) reads this the same way `_file` already does for
    # every static asset.
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".ico": "image/vnd.microsoft.icon",
    ".avif": "image/avif",
}


# What the Vault's clear may go out as a DOCUMENT — opened straight in a tab,
# and not only inside an `<img>` this very page already trusts. **It is a
# deliberate SUBSET of `_CONTENT_TYPES`, and the exclusion is the defence**:
# the Vault holds whatever the PERSON dropped in there, never what this
# product wrote, and a file's name proves nothing about what its bytes
# carry. `.svg` is XML and may carry `<script>` — it is OUT here despite
# being an image, because "is it an image" is not the right question; the
# question is "does the browser run something when this opens as a
# document", and the answer for SVG is yes. `.html`, `.js`, `.css` never
# entered. Whatever `_STRONGBOX_INLINE_TYPES` does not name leaves as
# `application/octet-stream` (`_strongbox_content`) — the browser downloads
# instead of opening, and no extension's name can talk it out of that.
_STRONGBOX_INLINE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".ico": "image/vnd.microsoft.icon",
    ".avif": "image/avif",
    ".pdf": "application/pdf",
}


def _strongbox_content(name: str) -> tuple[str, str]:
    """The Content-Type and the Content-Disposition for `name`, the original
    name (with the `.enc` gone) — never read off the extension the `.enc`
    itself carried, because the person wrote it, not this product.

    What `_STRONGBOX_INLINE_TYPES` recognises opens `inline`: the browser
    draws the image or the PDF exactly as it would one opened from anywhere
    else. Everything else is `attachment` over `application/octet-stream` —
    which is the decision and not a forgotten default: an `.html` or `.svg`
    name that opened as what its name says would be a document running in
    THIS origin, with the person's own session inside it. `quote` carries
    the accented name whole in `filename*` (RFC 6266), and the plain
    `filename` copy carries only what ASCII has, for the browser that does
    not read the first.
    """
    ctype = _STRONGBOX_INLINE_TYPES.get(Path(name).suffix.lower())
    kind = "inline" if ctype else "attachment"
    ascii_name = name.encode("ascii", "replace").decode("ascii")
    disposition = (f'{kind}; filename="{ascii_name}"; '
                    f"filename*=UTF-8''{quote(name)}")
    return ctype or "application/octet-stream", disposition


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
    """The stylesheet of the active theme; the OTHER side answers when the
    asked one does not exist. Only `at` ships both — every other theme in the
    registry kept the one side it wore by default and dropped its mirror
    (2026-10-04) — so a theme with one file answers the same CSS whichever
    way `dark` reads: it carries no choice for the page to get wrong."""
    row = active_theme(requested)
    if row is None:
        return None
    ident = str(row.get("id"))
    sides = [f"{ident}-dark.css", f"{ident}.css"] if dark else [f"{ident}.css", f"{ident}-dark.css"]
    for name in sides:
        where = THEMES / name
        if where.is_file():
            return where.read_text(encoding="utf-8")
    return None


def theme_sides(ident: str) -> list[str]:
    """Which files a theme actually has — never hand-declared (the old
    `"side"` field drifted from the files it described), always read off
    disk. Only `at` answers both: every other theme in the registry kept
    the one side it wore by default (2026-10-04) and the picker in Settings
    reads this to know whether there is a choice to offer at all."""
    sides = []
    if (THEMES / f"{ident}.css").is_file():
        sides.append("light")
    if (THEMES / f"{ident}-dark.css").is_file():
        sides.append("dark")
    return sides


def base_css_path(requested: str | None) -> Path:
    """Which base the active theme wears. A theme MAY declare one by name
    (`"base"` in the registry row) — a door every row in the registry leaves
    unused today, since `base-shared.css` was retired on 2026-10-03 and every
    theme now walks `base.css`, `at`'s own from-scratch design system and the
    server's default. The name is a bare filename or the door is refused: no
    separator survives to become a path."""
    row = active_theme(requested)
    name = row.get("base") if row and isinstance(row.get("base"), str) else None
    if name and "/" not in name and "\\" not in name and name.endswith(".css"):
        candidate = ASSETS / name
        if candidate.is_file():
            return candidate
    return ASSETS / "base.css"


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

    The key is the file's NAME and never a path — the same rule the font door
    keeps —, and the file's extension is the one the vendor's own `upstream`
    carries (`.woff2` for the typefaces, `.js` for the renderer `lib/markdown`
    waits for): it is what tells the content type apart without the key spelling
    a second extension the URL would then have to carry.
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
    upstream = entry.get("upstream")
    suffix = Path(upstream).suffix if isinstance(upstream, str) else ""
    if not suffix:
        return None
    where = VENDOR / f"{key}{suffix}"
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
    # A PRIMEIRA SUBIDA é a outra tela que a entrada desenha (TASK-176, fatia
    # 3/3), e ela é irmã da entrada e não da casca: quem chega numa pasta sem
    # administrador vê o formulário que o cria, e o vê ANTES de ter sessão —
    # então as palavras que ele desenha têm de viajar com a entrada, e o
    # `create` do botão é uma delas (o mesmo que a tela de criar papel usa).
    "first_hint", "create",
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
    "brand", "brand_name",
    "tasks", "files", "strongbox", "tables", "settings", "general", "appearance", "language",
    "dark_mode", "dark_system", "dark_light", "dark_dark",
    "motion", "themes", "no_project", "all_tasks", "board", "new_task", "new_project", "delete_project",
    # A ÁRVORE DE PROJETOS, O CRUD (TASK-135): o subprojeto que `new_project`
    # não nomeia, o verbo genérico de renomear, o rótulo do campo de nome do
    # formulário inline, e a opção "sem pai" do seletor de mover.
    "new_subproject", "rename", "name", "no_parent",
    # A TELA DE LEMBRETES (TASK-164): a seção, as duas metades, e o que uma
    # pasta sem lembrete e um dia sem aviso dizem.
    "reminders", "reminders_coming", "reminders_rang", "reminders_none", "reminders_quiet",
    "move_to_project", "records", "hidden", "no_records", "error", "filter",
    # THE FILA'S BADGE (TASK-162, fatia 2/2): whether this browser is online,
    # and how many edits are still waiting to leave it.
    "offline", "queued",
    # THE FILE TREE'S FIRST CONTEXT MENU (TASK-165, fatia 4/4): the two
    # actions and the toast that follows one.
    "convert_pdf", "convert_docx", "convert_toast",
    "columns", "refers", "panel", "collapse_menu", "expand_menu",
    # The context menu's own items (TASK-120, fatia 1): what the row's menu
    # offers when the engine says `edit` is legal.
    "edit",
    # TASK-122, fatia 3/7: the row menu's other two — a closing and a deletion,
    # each with the confirmation it owes before either reaches the server.
    "close", "close_confirm", "close_reason", "delete", "delete_confirm",
    "back", "confirm_cancel", "confirm_ok", "write", "saving",
    "saved", "save_failed", "chars", "words", "language_name", "language_flag",
    "ft_text", "ft_markdown", "ft_python", "ft_json", "ft_yaml", "ft_shell",
    "ft_dockerfile", "ft_binary", "ft_other",
    "bucket_code", "bucket_text", "bucket_data", "bucket_image", "bucket_other",
    # The interpreter's box, the switch that hides the balloon, and the ruler of
    # the demand filter (§4).
    "chat", "ask", "ask_hint", "proposal", "interpreter", "balloon", "balloon_close",
    "chat_cleared",
    "risk", "risk_runs", "risk_waits", "risk_threshold", "risk_none",
    # The assist's own Control Panel section, and its one retry (TASK-180,
    # fatia 3/3): the switch, the mode's two names, and the inline form a
    # refusal offers when a Main Key could still turn it into an answer.
    "assist", "assist_hint", "assist_mode", "assist_cautious", "assist_automatic",
    "assist_key", "assist_retry",
    # The CONFIRM tier's own two buttons (TASK-183): what a cautious assist's
    # question offers instead of the sentence it used to ask to be retyped.
    "assist_confirm", "assist_deny", "assist_denied",
    # NOTIFICAÇÕES (Web Push): o bloco das Configurações que pede a permissão
    # do navegador e inscreve o PWA — sem ntfy.
    "notifications", "notifications_hint", "notifications_on", "notifications_off",
    # A CREDENCIAL DO JEV, em Configurações, e o aviso do chat quando falta.
    "jev", "jev_hint", "jev_key", "jev_save", "jev_saved", "jev_not_configured",
    # The screens that move a role and a machine's credential — the two system
    # tables whose records are more than a form (§4, item 11).
    "people", "create", "new_role", "new_machine", "mint", "revoke", "token_once",
    "permission_pick", "unknown_permission", "unknown_hint", "credential_none",
    # A árvore de Actions (TASK-189, fatia 4/4): verbo → entidades → modificadores,
    # com a marca de quais portas alcançam cada ação do catálogo.
    "actions", "actions_hint", "modifier_flag", "modifier_argument",
    "reach_cli", "reach_web", "reach_llm", "reach_orphan", "reach_none_known",
    # O LEITOR DO COFRE (TASK-155): a confirmação antes de abrir, o botão de
    # salvar uma cópia, e o que se diz de um arquivo que não tem visualizador.
    "open_confirm", "save_local", "cannot_show",
    # The entrance's, because the entrance comes back when a session dies under
    # a running page (the 401 hook) — and it would come back wordless.
    *SESSION_WORDS,
)


# As palavras do `at-cli admin` que a PRIMEIRA SUBIDA em página desenha
# (TASK-176, fatia 3/3). Elas vêm do MESMO bloco do catálogo (`admin.json`) e
# nunca de uma segunda cópia: o que a pessoa lê no formulário e o que ela leria
# no terminal são uma string só, e uma das duas não pode envelhecer sozinha —
# "as mesmas strings que a fatia 2/3 já pôs no `at-cli admin`". Elas viajam com
# o próprio nome (`admin.name`) porque o bloco é outro: o formulário pede
# `admin.name`, e não um `webapp.*` que repetisse a frase.
FIRST_WORDS = ("name", "credential", "credential.again", "credential.twice",
               "error.short")


def _first_words() -> dict:
    """As palavras da primeira subida, na forma que uma ETIQUETA tem.

    **A pontuação é do PROMPT e não da palavra.** `admin.name` é "Nome do
    administrador: " — dois-pontos e espaço, que é como um prompt de terminal
    termina e como um formulário não escreve: a etiqueta já pede a resposta por
    estar onde está, e o sinal solto vira ruído. O que sai aqui é só isso, e a
    frase é a MESMA de `at-cli admin`; trocar a pontuação é o preço de a mesma
    string servir aos dois suportes, e é menor do que o de manter duas frases
    que possam divergir.
    """
    found = {}
    for key in FIRST_WORDS:
        name = f"admin.{key}"
        rendered = {}
        for lang, text in i18n.labels(name).items():
            # O PISO É DO MOTOR, e viaja já escrito: `admin.error.short` diz o
            # número, e quem o decide é `actors.MIN_CREDENTIAL` — que é o do
            # Cofre. Uma página que o soubesse teria a segunda cópia da regra.
            if key == "error.short":
                text = text.format(min=actors.MIN_CREDENTIAL)
            rendered[lang] = text.rstrip(": ")
        found[name] = rendered
    return found


def entry_payload(open_session: session.Session | None, asks: bool = True) -> dict:
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

    **`asks` is the OTHER reason a server has no entrance**, and it comes from
    the caller and not from here: a run from the source tree does not draw one
    (`server.asks`, `run`). The page reads the same `false` for both, which is
    the point — what it must not do is draw a form, and why the form is not
    there is not a thing the form could say.

    `version` rides along for a reader that is not the page: `at-cli webapp`,
    landing on a port another AT already holds, asks THIS route to find out
    which one — it stays the ONE public answer instead of a second route, and
    the page itself has no use for the field and reads past it.

    **`first` is the OTHER screen this answer draws** (TASK-176, fatia 3/3): a
    folder with no administrator at all has no entrance either — nobody could
    prove anything against it — and what the page draws in the entrance's place
    is the form that CREATES the first one (`/api/first`). The question is
    `admins()` and not `can_expose()`: a folder whose only actor is a machine's
    `agent` still has no administrator, and that is exactly the condition
    `at-cli admin` refuses by (`admin.exists`) — one rule, one answer, whether
    the word is typed at a terminal or in this form.

    A run that asks NOBODY has no first run to draw (`asks`), for the same
    reason it has no entrance: there is no door, so there is nothing to open.
    """
    return {
        "auth": asks and actors.can_expose(),
        "first": asks and not actors.admins(),
        "actor": {"name": open_session.name} if open_session else None,
        "lang": i18n.active_code(),
        "version": __version__,
        # The WHOLE language each word, like `/api/state` hands them: the page
        # picks by the language on screen and the server keeps owning the words.
        # The `admin.*` block rides beside them, and it is the same store the
        # entrance reads (`_first_words`).
        "labels": {
            **{key: i18n.labels(f"webapp.{key}") for key in ENTRY_WORDS},
            **_first_words(),
        },
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
        # THE ASSIST'S OWN TWO KNOBS (TASK-180, fatia 3/3): the switch (whether
        # Jev is asked at all, once the matcher gives up) and the mode (what a
        # non-`refuse` tier does once Jev has answered). The Control Panel draws
        # both from here and writes them back through `/api/assist`.
        "assist": assist.enabled(),
        "assist_mode": assist.mode(),
        # SE A CREDENCIAL DO JEV ESTÁ CONFIGURADA: sem ela o Jev não é
        # consultado, e a página diz "Jev não configurado" no chat em vez de
        # fingir que leu.
        "jev_ready": assist.configured(),
        # THE RULER'S NUMBERS. The threshold is the one the demand filter honours
        # (§4); the marks are one per catalogue entry, each carrying the number
        # the demand is measured at — the catalogue's, adjusted by what this
        # folder wrote (`risk.marks`). The page draws what it is handed and
        # invents no number, so the mark and the engine say the same thing.
        "risk": {"threshold": risk.threshold(), "marks": risk.marks()},
        # `None` is the answer for a folder under versioning, and it is not the
        # same as absent: the page tells "nothing to say" from "not here yet"
        # exactly the way it does with a session.
        "versioning": i18n.labels(unversioned) if unversioned else None,
        "theme": row.get("id") if row else None,
        "themes": [
            {"id": theme.get("id"), "label": theme_label(theme),
             "sides": theme_sides(str(theme.get("id"))),
             # The theme describes ITSELF, one description per side: the page
             # shows the one being worn, and follows the swap without asking.
             "desc": theme.get("desc") if isinstance(theme.get("desc"), dict) else None,
             # Almost always absent: the shared `base.css` needs no name of its
             # own. A theme that walks its OWN door (`base_css_path`) says so
             # here, and `theme.ts` reads it to swap the second link.
             "base": theme.get("base") if isinstance(theme.get("base"), str) else None}
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

    It asks the ENGINE which fields those are (`tables.opaque`) and not a list of
    types of its own: a credential is only ever compared and a sealed value is
    only ever opened with the key, and the page carries neither — a cell draws
    the mask and a form asks for a new credential. Any other field is handed over
    as it is stored, and the engine's own door is what says so (`raw_of`).
    """
    if tables.opaque(table, name) is not None:
        return None
    return tables.raw_of(table, name, value)


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
    """The closed list, as the screen that moves a role reads it — and, for the
    Actions tree (TASK-189, fatia 4/4), the same list carrying what the role
    picker never needed: the modifiers each act accepts and the interfaces that
    reach it.

    One entry per permission — the machine name, the label a person reads and the
    risk it declares — and never a guess: whatever the catalogue does not name is
    not here, which is exactly what makes the screen able to say that a role names
    something that does not exist. The order is the catalogue's, so the picker
    draws the list it was handed and sorts nothing.

    **`modifiers` and `reach` are read off the SAME declarations the fatias
    before this one wrote** (`permissions.modifiers`, `actions_audit.reach`), and
    not a second count: a page that drew its own would be the catalogue's
    second home. `orphan` is `actions_audit.orphans()`'s verdict, by key — the
    named exceptions (`NO_INTERFACE_YET`) answer `False` with an empty `reach`,
    which is a gap already decided, and never the one `orphan` flags.
    """
    reached = actions_audit.reach()
    orphaned = frozenset(actions_audit.orphans())
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
                "modifiers": [
                    {"name": modifier.name, "label": i18n.tr(modifier.key), "kind": modifier.kind}
                    for modifier in permissions.modifiers(name)
                ],
                "reach": sorted(reached.get(name, frozenset())),
                "orphan": name in orphaned,
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

    def _file(self, path: Path, hosted_version: str | None = None,
              extra: dict | None = None) -> None:
        headers = dict(extra or {})
        if hosted_version:
            headers["X-Hosted"] = hosted_version
        # The suffix is folded first: `prose.kind`/`prose.bucket` already fold
        # it (`Path(name).suffix.lower()`), and a `FOTO.PNG` the list calls an
        # image must not be served as `application/octet-stream` here.
        self._send(200, path.read_bytes(),
                   _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"),
                   headers or None)

    def _not_found(self) -> None:
        self._text("not found\n", status=404)

    # ---------------------------------------------------------- the entrance --

    def _asks(self) -> bool:
        """Whether this server asks anybody to enter.

        Two facts, and both have to hold. It is `actors.can_expose()` — the
        folder with somebody to enter it — read HERE and not only in `run`: the
        command refusing to take the port says nothing about a server somebody
        built by hand, and a gate that closed over a folder with nothing to
        prove would be a door with no key in it. §3: with no authentication
        configured, AT listens on loopback and asks nothing.

        **And it is whether THIS server draws an entrance at all**
        (`server.asks`). A run from the source tree does not (`run`), and the
        difference is the whole of what "sem forms" means: the folder is still
        the folder, the tables are still the tables, and nobody has to prove who
        they are to read them.
        """
        return self.server.asks and actors.can_expose()

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

    def _may(
        self, permission: str, *, owing: Callable[[], None] | None = None
    ) -> bool:
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

        **`owing` is what the refusal owes before it is answered**: the table
        write's line (§3, item 15), which its route hands in because `_may` is
        the moment the wall is found. It runs BEFORE the response goes out — a
        line written after the answer is a line a crash can lose, and a refusal
        that was answered and not recorded is exactly the one worth having.
        """
        held = self._in()
        if not self._asks() or held is None:
            return True
        row = self._actor()
        if row is not None and actors.may(row, permission):
            return True
        if owing is not None:
            owing()
        self._json(
            {
                "error": i18n.tr(
                    "permission.denied", permission=permissions.label(permission)
                )
            },
            403,
        )
        return False

    def _legal(self, permission: str) -> bool:
        """Whether the actor this request proved carries `permission` — a QUESTION
        and never a refusal (TASK-120, fatia 1).

        `_may` is a GATE: it answers the same way and writes the 403 a route is
        refused with. A context menu asking what it may show is not a route being
        refused — there is nothing to write, and no owing either, because showing
        nothing is not a demand that failed. Same two hops as `_may`'s ceiling
        (`_asks`, `_actor`, `actors.may`), and none of its response.
        """
        if not self._asks():
            return True
        row = self._actor()
        return row is not None and actors.may(row, permission)

    def _table_actions(self, table: str) -> list[str]:
        """Which of the engine's own actions this actor may reach on `table` —
        the truth a context menu shows instead of inventing one (TASK-120).

        **Row-independent, and that is the system's own shape and not a
        shortcut**: the ceiling `actors.may` reads is the ROLE's, over the
        TABLE — no table here narrows a permission by which row it is — so
        "what this row allows" and "what this table allows this actor" are the
        same question. `view` is implicit in the row already being listed,
        and `create` (TASK-121) joins `edit` here.

        **`cancel` and `delete` (TASK-122, fatia 3/7) carry a SECOND question,
        beside the permission.** A role may carry `actor:cancel` — the engine's
        six are a permission each, whether or not the table ever answers the
        act — while `actor` declares no `lifecycle` at all; offering the door
        there would be one `tables.cancel` refuses the moment it is pushed
        (`error.no_lifecycle`). So the two ask the STRUCTURAL question first —
        `tables.lifecycle` for a closing, `tables.deletable` for a deletion —
        and only then the same ceiling `create`/`edit` already ask.
        """
        return [
            action for action in ("create", "edit", "cancel", "delete")
            if (action != "cancel" or tables.lifecycle(table))
            and (action != "delete" or tables.deletable(table))
            and self._legal(permissions.needed(table, action))
        ]

    def _project_actions(self) -> list[str]:
        """Which of `create`/`edit` this actor may reach on `project` — the
        projects tree's own context menu (TASK-135), asked the same way
        `_table_actions` asks for a table's row menu.

        Named apart from `_table_actions` because the tree's occasion offers a
        DIFFERENT pair: `create` (a project or a subproject), never offered by
        the generic row menu yet (TASK-121), and `edit` (a rename or a move,
        the SAME permission — `narrowed` does not split a table's six by what
        field changes).
        """
        return [action for action in ("create", "edit")
                if self._legal(permissions.needed(projects.PROJECT, action))]

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

    def _local(self) -> bool:
        """Whether this request came over the LOOP — §3's line, read per request.

        A folder with no administrator has exactly one door open without a
        session (`_post_first`), and it is the PERSON's: the one sitting at the
        machine. Any other address is somebody else, and the answer is the same
        sentence `run` gives when it refuses to leave the loop (`no_admin`) —
        one rule about where a folder without an actor is served, said at the
        command and at the door.
        """
        return loopback(self.client_address[0])

    def _post_first(self) -> None:
        """A primeira subida: o formulário da página cria o primeiro admin.

        **É a MESMA porta de `at-cli admin`** — `actors.create_admin`, com o
        papel criado antes da linha —, e é por isso que ela está ACIMA do
        portão, como `_post_session`: não há sessão a exigir de quem ainda não
        tem com quem entrar, e uma rota que exigisse uma seria uma porta que só
        abre para quem já passou por ela. Pela mesma razão ela é a ÚNICA rota
        de escrita que responde a um pedido sem sessão, e é por isso que ela
        responde ANTES a quem está do outro lado do fio (`_local`): §3 —
        sem ator nenhum o AT não expõe.

        **As regras são as do terminal, e não uma segunda cópia delas.** As
        duas chaves são lidas duas vezes porque não se recuperam, e o
        `admin.error.mismatch` é a recusa quando não são a mesma; o piso é
        `actors.MIN_CREDENTIAL`, que é o do Cofre, e quem recusa por ele é o
        próprio motor (`admin.error.short`, dentro de `create_admin`); e a
        pasta que já tem administrador é recusada pelo nome dele
        (`admin.exists`), que é a mesma pergunta que `at-cli admin` faz. As
        palavras são as do bloco `admin` do catálogo, as mesmas que o
        formulário desenhou (`_first_words`).

        **A sessão abre no fim, e ela é a única coisa que sobra para o
        formulário fazer.** Quem acabou de digitar a Chave Principal já provou
        quem é — a mesma string é o que a linha vai guardar hasheada —, e
        pedir a mesma coisa duas vezes seria a página cobrando de novo o que o
        servidor acabou de aceitar.
        """
        if gate.on_gate():
            self._json({"error": i18n.tr("webapp.forms_off")}, 403)
            return
        if self._forged():
            self._json({"error": i18n.tr("webapp.gate_refused")}, 403)
            return
        if not self._local():
            self._json({"error": i18n.tr("webapp.no_admin")}, 403)
            return
        existing = actors.admins()
        if existing:
            self._json(
                {"error": str(actors.AdminError(
                    "exists", name=tables.title("actor", existing[0])
                ))},
                403,
            )
            return
        payload = self._body()
        if payload is None:
            return
        name = payload.get("name")
        credential, again = payload.get("credential"), payload.get("again")
        if not all(isinstance(value, str) for value in (name, credential, again)):
            self._json({"error": "bad request"}, 400)
            return
        if credential != again:
            self._json({"error": str(actors.AdminError("error.mismatch"))}, 400)
            return
        try:
            row = actors.create_admin(name.strip(), credential)
        except (actors.AdminError, tables.TableError) as refused:
            self._json({"error": str(refused)}, 400)
            return
        opened = self.server.sessions.open(row)
        self._json(
            {"actor": {"name": opened.name},
             "created": i18n.tr("admin.created",
                                name=tables.title("actor", row))},
            extra={"Set-Cookie": session.cookie_header(opened)},
        )

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
            self._file(base_css_path(query.get("theme", [None])[0]))
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

        # ROOT SCOPE, ON PURPOSE (TASK-162, fatia 2/2): a Service Worker's
        # reach is its own folder unless the response comes from the root, and
        # `/js/sw.js` would leave the document and the API outside it.
        if head == "sw.js" and not rest:
            self._static(ASSETS / "js", "sw.js")
            return

        if head == "manifest.webmanifest" and not rest:
            self._static(ASSETS, "manifest.webmanifest")
            return

        # `.svg` for the look, `.png` for the launcher: the manifest's own
        # install icons have to be PNG (`_CONTENT_TYPES` serves them as
        # `image/png`), and Android offers no "Install app" without a 192 and a
        # 512 — an SVG icon is a picture, not a WebAPK icon.
        if head == "icons" and len(rest) == 1 and rest[0].endswith((".svg", ".png")):
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
        # A PRIMEIRA SUBIDA, ao lado da entrada e pelo mesmo motivo: as duas
        # são escritas que não podem já ter sessão — uma porque a abre, a outra
        # porque cria com quem ela se abre. O que as separa é o que já existe
        # na pasta, e quem responde por isso é a própria rota (`_post_first`).
        if segments == ["api", "first"]:
            self._post_first()
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
        if segments == ["api", "convert"]:
            if not self._may("prose:read"):
                return
            self._post_convert()
            return
        if segments == ["api", "strongbox", "open"]:
            if not self._may("strongbox:read"):
                return
            self._post_strongbox_open()
            return
        if segments == ["api", "ask"]:
            if not self._may("nlu:ask"):
                return
            self._post_ask()
            return
        if segments == ["api", "assist"]:
            if not self._may("setting:edit"):
                return
            self._post_assist()
            return
        if segments == ["api", "jev"]:
            if not self._may("setting:edit"):
                return
            self._post_jev()
            return
        if segments == ["api", "agent"]:
            self._post_agent()
            return
        if len(segments) == 3 and segments[0] == "api" and segments[1] == "table":
            self._post_table(segments[2])
            return
        if segments == ["api", "offline", "sync"]:
            self._post_offline_sync()
            return
        if segments == ["api", "push", "subscribe"]:
            if not self._may("notifier:read"):
                return
            self._post_push_subscribe()
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
            self._json(entry_payload(self._in(), asks=self.server.asks))
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
            self._json({
                "tree": projects.tree() if projects.available() else [],
                # The projects TREE's own context menu (TASK-135) — the same
                # engine question `_table_actions` asks, over the pair this
                # occasion offers.
                "actions": self._project_actions() if projects.available() else [],
            })
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

        if rest == ["events"]:
            # A MESMA PERMISSÃO DE `tree` (TASK-128, fatia 2/3): o que este
            # canal avisa é "algo mudou em `Arquivos/`", e quem já pode ler a
            # árvore é quem já pode saber que ela mudou.
            if not self._may("prose:read"):
                return
            self._get_events()
            return

        if rest == ["file"]:
            if not self._may("prose:read"):
                return
            self._get_file(query.get("path", [""])[0])
            return

        if rest == ["file", "bytes"]:
            if not self._may("prose:read"):
                return
            self._get_file_bytes(query.get("path", [""])[0])
            return

        if rest == ["strongbox"]:
            # TASK-156: a lista, e só — o que sela é o vigia (TASK-154), não
            # um gesto desta rota.
            if not self._may("strongbox:read"):
                return
            self._json({"files": [{"path": path} for path in strongbox.listed()]})
            return

        if rest == ["strongbox", "download"]:
            # The link `_post_strongbox_open` minted, walked once. The same
            # `strongbox:read` as above: a plain navigation carries the
            # session cookie like any other, and the token by itself is not
            # proof of WHO the person is — it is proof of WHICH file, once.
            if not self._may("strongbox:read"):
                return
            self._get_strongbox_download(query.get("token", [""])[0])
            return

        if rest == ["notifications"]:
            # TASK-176, fatia 3/3: o WebApp entrega à página o que o AT já
            # avisou (o `INBOX` do Web Push, desde que o ntfy saiu). A demanda
            # está AQUI, na rota, como em todas as outras — e é o `read` do
            # objeto `notifier`, que é o teto de quem lê os avisos.
            if not self._may("notifier:read"):
                return
            self._get_notifications()
            return

        if rest == ["reminders"]:
            # TASK-164: a metade "o que vem" da tela de Lembretes — os lembretes
            # com o PRÓXIMO disparo CALCULADO. A recorrência é do motor
            # (`reminder.upcoming`), e a página não a repete: a regra mora num
            # lugar só. A demanda é a de listar a tabela, a mesma de toda
            # leitura dela.
            if not self._may(permissions.needed(reminder.REMINDER, "list")):
                return
            self._get_reminders()
            return

        if rest == ["push", "key"]:
            # A chave PÚBLICA do VAPID, que a página passa ao
            # `pushManager.subscribe`. Pública por construção: o par privado
            # nunca sai da pasta (`core.push`).
            if not self._may("notifier:read"):
                return
            self._json({"key": push.public_key()})
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
            # The permission is the ACTION's, read from the catalogue like the
            # write route's: a table may narrow itself (`secret` answers `read`
            # for a listing, `audit` answers nothing else), and a route composing
            # `table:list` would demand a permission the catalogue does not have
            # — which fails CLOSED, and would refuse the administrator the very
            # table the catalogue says is theirs.
            if not self._may(permissions.needed(table, "list")):
                return
            payload = table_payload(table, show_all="all" in query)
            payload["actions"] = self._table_actions(table)
            self._json(payload)
            return

        self._not_found()

    def _get_events(self) -> None:
        """A conexão fica de pé: a cada escrita em `Arquivos/`, uma linha sai
        (TASK-128, fatia 2/3).

        **O corpo nunca diz QUAL arquivo mudou.** A aba que recebe o aviso
        relê a página inteira (`poke()`, do lado do navegador) — dizer o
        caminho aqui seria um campo que ninguém lê, a mesma razão de
        `vigia.Event` carregar só o caminho e nada além dele.

        **Uma fila por conexão, e não um vigia por aba** (`events.Broadcaster`):
        o vigia que varre `Arquivos/` vive uma vez só, no relógio (`beat()`),
        e publica uma vez por rodada — é o `Broadcaster` que copia esse aviso
        para a fila de toda aba aberta.

        Sem `Content-Length`: o corpo não tem fim conhecido, e é isso que
        `text/event-stream` pede — a conexão fecha quando a aba fecha, não
        quando um tamanho se esgota.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        made = self.server.events.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    made.get(timeout=EVENTS_HEARTBEAT)
                    payload = b"data: changed\n\n"
                except queue.Empty:
                    payload = b": keep-alive\n\n"
                self.wfile.write(payload)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            # A aba fechou — não é uma falha deste processo, é o fim de uma
            # conexão que nunca prometeu durar.
            pass
        finally:
            self.server.events.unsubscribe(made)

    def _get_project(self, asked: str) -> None:
        number = tables.number_of("project", asked)
        payload = projects.page(number) if number is not None else None
        if payload is None:
            self._json({"error": "unknown project", "project": asked}, 404)
            return
        payload["fields"] = _schema_payload("task")
        payload["records"] = [_record("task", row) for row in payload.pop("rows")]
        payload["actions"] = self._table_actions("task")
        # The project's OWN fields, rendered like any other record's: it is what
        # carries the body of an item to the page — the `desc` the table
        # declares `markdown`, plus the status and the priority the tree orders
        # by. The two are named apart on purpose: `fields`/`records` below are
        # the TASKS the page draws, and this pair is the page itself.
        payload["project"] = {
            "fields": _schema_payload("project"),
            "record": _record("project", payload.pop("row")),
        }
        self._json(payload)

    def _orphans_payload(self) -> dict:
        rows = projects.orphans()
        return {
            "key": "task",
            "title": i18n.tr("webapp.no_project"),
            "filter": None,
            "fields": _schema_payload("task"),
            "records": [_record("task", row) for row in rows],
            "actions": self._table_actions("task"),
        }

    def _get_notifications(self) -> None:
        """O que o AT já avisou, lido da pasta (TASK-176, fatia 3/3).

        **Não há mais um tópico remoto.** O ntfy guardava a mensagem do outro
        lado; agora quem guarda é o próprio AT, no `INBOX` do Web Push
        (`core.notifier.read`), e o que a página recebe são as últimas
        notificações que SAÍRAM — reduzidas aos campos que ela desenha, e
        nunca nada de credencial, que não existe mais aqui.

        **Uma leitura não pode falhar por rede.** O ntfy respondia por uma
        porta, e um notificador fora do ar era um 502; o que há agora é um
        arquivo da pasta, e uma pasta sem avisos é uma lista vazia, não um
        erro.
        """
        messages, _ = notifier.read()
        self._json({"messages": messages})

    def _get_reminders(self) -> None:
        """Os lembretes com o PRÓXIMO disparo — a metade "o que vem" (TASK-164).

        **SÓ HOJE E AMANHÃ** (2026-10-05, pedido da pessoa): a seção é o que
        precisa da atenção de AGORA, e o que toca depois disso não é "próximo",
        é calendário — a tabela é quem o mostra por inteiro. Um lembrete que não
        volta a tocar (um `paused`, um `once` vencido, um dia que o mês não tem)
        não entra: não há disparo para apontar, e uma linha sem próximo na lista
        do que VEM seria uma promessa que `occurs` já recusa.

        A ordem é a do relógio: o que toca primeiro vem primeiro.

        As quatro colunas do schema (`freq`, `at`, `status`, `text`) e o
        cálculo, e nada além: o `note` é do lembrete e não desta tela. `freq` e
        `status` vão no TEXTO que a pessoa lê (`tables.text_of`, o mesmo que a
        tabela usa) e não no enum cru — a página inventa palavra nenhuma.
        """
        today = reminder.today()
        upcoming = []
        for row in store.load(reminder.REMINDER):
            when = reminder.upcoming(row)
            if when is None or (when[0] - today).days > 1:
                continue
            upcoming.append(
                {
                    "id": row.get("id"),
                    "text": row.get("text"),
                    "freq": tables.text_of(reminder.REMINDER, "freq", row.get("freq")),
                    "at": row.get("at"),
                    "status": tables.text_of(reminder.REMINDER, "status", row.get("status")),
                    "active": row.get("status") == reminder.ACTIVE,
                    "next": f"{when[0].isoformat()} {when[1]}",
                }
            )
        upcoming.sort(key=lambda item: (item["next"], item["id"] or 0))
        self._json({"reminders": upcoming})

    def _post_push_subscribe(self) -> None:
        """Guarda a inscrição do navegador — o `PushSubscription.toJSON()`.

        O corpo traz `endpoint` e as duas chaves (`p256dh`, `auth`); é contra
        elas que o AT cifra cada aviso (`core.push`). O `Host` da requisição
        entra no contato do VAPID — é o único momento em que o AT sabe o nome
        que o push service vê.
        """
        payload = self._body()
        if not push.subscribe(payload):
            self._json({"error": i18n.tr("webapp.push_subscribe")}, 400)
            return
        host = (self.headers.get("Host") or "").split(":")[0]
        push.contact(host or None)
        self._json({"ok": True})

    def _get_file(self, path: str) -> None:
        answer = prose.read(path)
        if answer is None:
            self._json({"error": i18n.tr("prose.not_served")}, 404)
            return
        if answer.get("reason"):
            answer["reason"] = i18n.tr(str(answer["reason"]))
        self._json(answer)

    def _get_file_bytes(self, path: str) -> None:
        """The raw bytes of one file of `Arquivos/`, for whatever `<img>` in
        the page names it as `src` (TASK-167). The SAME door every other read
        of the folder walks (`prose.inside`, never a raw join) and the SAME
        gate (`servable`: `inside` plus `is_file`, so a name outside the tree
        or a name nothing answers to is a 404 and not a peek at the
        filesystem).

        **The SVG is served sandboxed, and the other eight carry no header.**
        In the page it is only ever an `<img src>` (`FileView.vue`), and a
        browser runs no `<script>` an SVG loaded that way carries — but this
        is a URL like any other, and whoever opens it straight in a tab gets
        the SVG as a DOCUMENT, where that script WOULD run in AT's own origin.
        `sandbox` takes that away (no script, no origin) and changes nothing
        about the `<img>`: the header of a subresource is not read when the
        browser draws it as an image. PNG, JPEG, GIF, WebP, BMP, ICO and AVIF
        are inert bytes with no script to run, so the header would be noise.
        """
        where = prose.inside(path)
        if where is None or not where.is_file():
            self._not_found()
            return
        sandbox = ({"Content-Security-Policy": "sandbox"}
                   if where.suffix.lower() == ".svg" else None)
        self._file(where, extra=sandbox)

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

    def _post_convert(self) -> None:
        """`{path, to}` → a DOCX or PDF landed in `Convertidos/` (TASK-165,
        fatia 4/4). The same door and the same refusals `_get_file` already
        answers with — a path outside `Arquivos/` or a file that is not text
        is refused by `prose` itself, never a second rule invented here.
        """
        payload = self._body()
        if payload is None:
            return
        rel, to = payload.get("path"), payload.get("to")
        if not isinstance(rel, str) or to not in convert.FORMATS:
            self._json({"error": "bad request"}, 400)
            return
        info = prose.read(rel)
        if info is None:
            self._json({"error": i18n.tr("prose.not_served")}, 404)
            return
        if info.get("reason"):
            self._json({"error": i18n.tr(str(info["reason"]))}, 400)
            return
        where = prose.inside(rel)
        try:
            target = convert.convert(where, to)
        except files.ReadOnly as error:
            self._json({"error": f"read-only: {error.where}"}, 403)
            return
        self._json({"path": target.name})

    def _post_strongbox_open(self) -> None:
        """`{path}` → `{url, kind}`: a one-time link to the clear of `path`,
        and HOW the page should draw it.

        **What this route hands back is an ADDRESS, never the content.** Whoever
        confirmed they want the file open gets somewhere to navigate to — the
        page sends the browser there (`window.location`, a link, whatever the
        gesture is), and it is that navigation that spends the link
        (`_get_strongbox_download`). What this route DOES read is the clear,
        once, to answer `kind` (`strongbox.look`) — the page has to know whether
        it is drawing an image, a PDF, text or none of them BEFORE it walks the
        link, and the kind is not a fact of the `.enc`'s name. Reading it here
        also means a file the key does not open is refused at the DOOR, before
        any overlay opens on an error.

        `path` has to be exactly one of the names `strongbox.listed()` hands
        back — the SAME listing the page already reads to draw the tree: a
        name not in it is refused here, before any link exists, because that
        listing is the only catalogue of what belongs to the Vault.
        """
        payload = self._body()
        if payload is None:
            return
        path = payload.get("path")
        if not isinstance(path, str) or path not in strongbox.listed():
            self._json({"error": "bad request"}, 400)
            return
        key = keys.strongbox_key()
        if key is None:
            self._json({"error": i18n.tr("strongbox.no_key")}, 503)
            return
        clear = strongbox.open_file(strongbox.folder() / path, key)
        if clear is None:
            self._json({"error": i18n.tr("strongbox.unreadable")}, 500)
            return
        name = Path(path).name.removesuffix(strongbox.SUFFIX)
        token = self.server.strongbox_links.open(path)
        self._json({
            "url": f"/api/strongbox/download?token={token}",
            "kind": strongbox.look(clear, name),
        })

    def _get_strongbox_download(self, token: str) -> None:
        """The clear `token` opens — once, straight into the response, never
        into a file. `strongbox.open_file` reads the `.enc` and hands back
        bytes in memory; what leaves here is that very return, and nothing
        along the way writes them to disk.

        The check against `strongbox.listed()` runs again here
        (`_post_strongbox_open` already ran the same one, at minting)
        because the world may have changed between the two calls — a file
        removed, resealed — and a token still alive is no proof that the
        path it names is still one of the Vault's `.enc` files.
        """
        path = self.server.strongbox_links.take(token)
        if path is None or path not in strongbox.listed():
            self._not_found()
            return
        key = keys.strongbox_key()
        if key is None:
            self._json({"error": i18n.tr("strongbox.no_key")}, 503)
            return
        clear = strongbox.open_file(strongbox.folder() / path, key)
        if clear is None:
            self._json({"error": i18n.tr("strongbox.unreadable")}, 500)
            return
        name = Path(path).name.removesuffix(strongbox.SUFFIX)
        ctype, disposition = _strongbox_content(name)
        self._send(200, clear, ctype, {
            "Content-Disposition": disposition,
            "X-Content-Type-Options": "nosniff",
        })

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

        **`main_key` is the one thing this route adds past fatia 1/2** (TASK-180,
        fatia 3/3): the real path through the assist, from the ONE place that can
        type a Main Key without it ever landing in a file or a log — the person's
        own browser, for the one request that carries it. It is never cached here
        and never on the page: a retry sends it again, exactly the way `at-cli
        assist` reads it fresh every time.

        **Asking Jev is its own ceiling, separate from `nlu:ask`'s** (already
        asked at the dispatch above): a role may read the deterministic box
        without being free to spend a call to an external service, so a key that
        arrived without `assist:ask` is dropped here — the sentence gets the
        same answer it would have gotten with no key at all, and never a 403 over
        a field the request did not have to send.
        """
        payload = self._body()
        if payload is None:
            return
        sentence = payload.get("text")
        if not isinstance(sentence, str) or not sentence.strip():
            self._json({"error": "bad request"}, 400)
            return
        raw_key = payload.get("main_key")
        main_key = raw_key if isinstance(raw_key, str) and raw_key else None
        if main_key is not None and not self._legal("assist:ask"):
            main_key = None
        # A Chave Principal da SUBIDA, guardada em memória no `boot` (§4): o
        # pedido não precisa trazê-la de novo a cada mensagem.
        if main_key is None:
            main_key = keys.main_key()
        # The ACTOR comes along: the door owns the ceiling (§5, "o que ela pode
        # propor é o que ela já pode fazer"), and it is the same door the balloon,
        # the chat and `at-cli ask` read — so the refusal lands on every surface at
        # once and none of them keeps a ceiling of its own. `None` is a folder
        # asking nobody, and there the door answers as it always did.
        result = door.ask(sentence, actor=self._actor(), main_key=main_key,
                          confirmed=bool(payload.get("confirmed")))
        self._json({
            "kind": result.kind,
            "proposal": result.proposal,
            "text": result.text,
            # Whether the assist could still answer THIS refusal for a Main Key
            # typed now — `False` once one already travelled (nothing left to
            # retry) and for an actor the role does not let spend the call at
            # all, so the browser never offers a retry that can only be denied.
            "assist": result.assist and self._legal("assist:ask"),
            # The rewritten sentence a "Confirmar" resubmits (TASK-183) — `None`
            # for every answer and every ordinary ambiguity question. It needs
            # no ceiling of its own: `door.ask` only fills it once the assist
            # has already run, which only happened because the Main Key that
            # reached it already cleared `assist:ask` above.
            "confirm": result.confirm,
            # A `list`'s own header and cells, so the chat draws an actual
            # table instead of parsing `text`'s ASCII back apart — `None` for
            # every other answer, and for a `list` that found nothing.
            "table": {"header": result.table[0], "rows": result.table[1]}
            if result.table is not None else None,
            # A `list`'s own bullets — the default shape, one line per row —
            # mutually exclusive with `table` (above): a sentence that said
            # "tabela" fills one, every other `list` fills the other.
            "bullets": result.bullets,
            # The action a bare verb named ("listar", alone) — `null` for
            # every answer that is not that one refusal — so the chat can
            # complete it from whatever is typed next instead of asking the
            # person to repeat themselves with the object already in hand.
            "awaiting": result.awaiting,
        })

    def _post_jev(self) -> None:
        """Configura a credencial do Jev — o `secret` de escopo `jev` (§4).

        O corpo traz a chave do Jev e a Chave Principal: a segunda é o que SELA
        a primeira (`assist.configure`), e não é guardada em lugar nenhum. A
        rota não abre nada e não chama o Jev — só escreve a linha; a página
        passa a ver `jev_ready` no estado.
        """
        payload = self._body()
        if payload is None:
            return
        value = payload.get("key")
        if not (isinstance(value, str) and value.strip()):
            self._json({"error": i18n.tr("webapp.jev_missing")}, 400)
            return
        # A Chave Principal é a da SUBIDA, em memória (`keys.main_key`) — a
        # pessoa NÃO a digita de novo aqui: ela já foi digitada quando o AT
        # subiu, e é a mesma que sela o valor (§4).
        main_key = keys.main_key()
        if not main_key:
            self._json({"error": i18n.tr("webapp.jev_no_main_key")}, 409)
            return
        if not assist.configure(value.strip(), main_key):
            self._json({"error": i18n.tr("webapp.jev_bad_key")}, 400)
            return
        self._json({"ok": True, "jev_ready": True})

    def _post_assist(self) -> None:
        """The assist's own two knobs, from the Control Panel (TASK-180, fatia
        3/3): the switch and the mode, each an adjustment of the folder (§4)
        and not a datum of the page, so each is written through `door.setting`
        — the same line and the same version a `setting edit` at a terminal
        already leaves, and not a second road into `settings.json`.

        Either field alone is a legal request — the switch flips without
        touching the mode, and the mode changes without touching the switch —
        so the two are read and written independently, and the answer is the
        pair as the folder now holds it, read back rather than echoed, the
        same reason `door.setting` itself answers from the file and not from
        what was typed.
        """
        payload = self._body()
        if payload is None:
            return
        on = payload.get("enabled")
        wanted_mode = payload.get("mode")
        actor = self._actor()
        if isinstance(on, bool):
            code, answer = door.setting(
                "edit", [assist.SWITCH, "true" if on else "false"],
                actor=actor, via=audit.WEBAPP,
            )
            if code != door.OK:
                self._json({"error": answer}, 400)
                return
        if isinstance(wanted_mode, str):
            if wanted_mode not in (assist.CAUTIOUS, assist.AUTOMATIC):
                self._json({"error": f"unknown mode: {wanted_mode}"}, 400)
                return
            code, answer = door.setting(
                "edit", [assist.MODE, wanted_mode], actor=actor, via=audit.WEBAPP,
            )
            if code != door.OK:
                self._json({"error": answer}, 400)
                return
        self._json({"enabled": assist.enabled(), "mode": assist.mode()})

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
        # The permission is the action's, read from the CATALOGUE and not
        # composed here: a table may narrow itself to `read` and `edit`
        # (`secret`), and a route that wrote `table:action` would refuse a write
        # the role carries — or worse, demand a permission the catalogue does
        # not have.
        needed = permissions.needed(table, action)
        actor = self._actor()
        if not self._may(
            needed,
            # The CEILING refused an act, and a wall an actor found is a line
            # (§3): the machine that could read its own refusals would learn
            # where the wall is, which is why only the admin carries `audit:read`.
            # It is handed in as what the refusal OWES, so the line is in the
            # store before the 403 leaves the server.
            owing=lambda: door.denied(
                table,
                action,
                actor=actor,
                via=audit.WEBAPP,
                reason=audit.DENIED,
                saying=i18n.tr(
                    "permission.denied", permission=permissions.label(needed)
                ),
            ),
        ):
            return
        values = payload.get("set")
        values = {str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {}
        # The row the action names, written the way the door reads one: the
        # leftover for `edit`, and none for `create` — which is why the two
        # agree on `rest` and the pair travels beside it.
        rest = [] if action == "create" else [str(payload.get("id"))]
        try:
            # The page walks the SAME door the `cli` and the interpreter walk
            # (`at.ui.ask.run`): one engine, one version and one line per act,
            # and the record it answers with is the page's own wording of it.
            _, answer, row, _, _ = door.run(
                table,
                action,
                rest,
                (values, rest),
                actor=actor,
                via=audit.WEBAPP,
            )
        except tables.TableError as error:
            self._json({"error": str(error)}, 400)
            return
        except files.ReadOnly as error:
            self._json({"error": f"read-only: {error.where}"}, 403)
            return
        if row is None:
            # The demand did not run: it WAITS, and the answer names the job
            # (§4, item 15). It is not a record and it is not an error either —
            # the act was neither written nor refused — so what travels back is
            # the engine's own sentence, which is what the `cli` prints and what
            # the machine that asked it reads. A person's demand never reaches
            # here: the act IS the approval, and this is the road of whoever
            # cannot ask.
            self._json({"held": True, "answer": answer})
            return
        self._json({"record": _record(table, row)})

    def _post_offline_sync(self) -> None:
        """The fila the Service Worker built offline, reconciled in ONE round
        trip (TASK-162, fatia 2/2) — the motor of fatia 1 (`at.core.offline`),
        walked from here instead of the `cli`'s single-row door.

        A conflict is resolved by `offline.reconcile` itself (last-write-wins,
        by `edited_at`); this route's own job is the permission ceiling every
        other write already answers to (`_may`) — a queue built offline
        carries no session of its own to have already proved it.
        """
        payload = self._body()
        if payload is None:
            return
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            self._json({"error": "bad entries"}, 400)
            return
        entries: list[offline.QueueEntry] = []
        actions: set[str] = set()
        for raw in raw_entries:
            action = raw.get("action") if isinstance(raw, dict) else None
            if action not in OFFLINE_WRITES:
                self._json({"error": f"unknown action: {action}"}, 400)
                return
            actions.add(action)
            values = raw.get("values")
            values = {str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {}
            entries.append(offline.QueueEntry(
                action=action,
                values=values,
                edited_at=str(raw.get("edited_at")),
                id=raw.get("id"),
                local_id=raw.get("local_id"),
            ))
        actor = self._actor()
        for action in actions:
            needed = permissions.needed(offline.TABLE, action)
            if not self._may(
                needed,
                owing=lambda action=action: door.denied(
                    offline.TABLE,
                    action,
                    actor=actor,
                    via=audit.WEBAPP,
                    reason=audit.DENIED,
                    saying=i18n.tr(
                        "permission.denied", permission=permissions.label(needed)
                    ),
                ),
            ):
                return
        try:
            resolutions = offline.reconcile(entries)
        except tables.TableError as error:
            self._json({"error": str(error)}, 400)
            return
        self._json({
            "resolutions": [
                {
                    "local_id": res.entry.local_id,
                    "id": res.entry.id,
                    "applied": res.applied,
                    "record": _record(offline.TABLE, res.row) if res.row is not None else None,
                }
                for res in resolutions
            ]
        })

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

    **And the ASKING lives here for the same reason** (`asks`): whether this
    server draws an entrance is a fact of THIS server, and `run` is the one that
    decides it from the artifact (`paths.source`). The suite builds bare servers,
    which ask as the bundle does — a test that wants the dev answer asks for it
    out loud (`make_server(asks=False)`), which is what keeps every other test's
    refusals exactly what they were.

    **`daemon_threads = True`** (TASK-128, fatia 2/3): uma conexão `/api/events`
    fica de pé por uma aba inteira, às vezes mais do que o processo — e uma
    thread não-daemon é uma thread que o interpretador espera no fim, mesmo
    depois do servidor ter fechado. É a mesma razão do relógio ser DAEMON
    (`beat`'s own docstring): o que fica de pé morre com o processo, e nada
    tem de derrubá-lo à mão.
    """

    daemon_threads = True

    def __init__(self, address: tuple[str, int],
                 handler: type[BaseHTTPRequestHandler], asks: bool = True) -> None:
        super().__init__(address, handler)
        self.sessions = session.Sessions()
        self.strongbox_links = strongbox_links.Links()
        self.events = events.Broadcaster()
        self.asks = asks


def loopback(name: str) -> bool:
    """Whether an address is the LOOP — the one a folder without an
    administrator is served on (§3, TASK-176 fatia 3/3).

    A name is read as a NAME first, and `localhost` is the loop by declaration
    (it is the word the command itself uses); anything else is read as an
    ADDRESS, by `ipaddress`'s rule and never by a string comparison — `127.0.0.7`
    and `::1` are the loop too, and a folder served on one of them is exactly as
    local as one on `127.0.0.1`. A name that is neither — a hostname, which this
    machine may or may not resolve to itself — is NOT the loop, and that is the
    safe side: it is a name somebody else may hold, and a door with no way to
    tell has to answer no.
    """
    if name == LOOPBACK_NAME:
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def chosen_host() -> str:
    """The address the folder answers on — `HOST` when it chose none.

    `HOST_KEY` holds it, and it is an ADJUSTMENT of the installation: no
    credential, nothing proved. A folder that never wrote it answers on
    `127.0.0.1`, which is the default and what this product recommends; a person
    who wants AT somewhere else says it there, or says it for one run with
    `--host`.

    **A record nobody can read answers the default**, the same way `gate.mode`
    reads a broken one as the safe side: a settings file that will not parse is
    not a folder that moved its address, and a value that is not a name is not a
    name. What is NOT asked here is whether the address is the loop — that
    question has no answer this module could act on (the docstring says why),
    and asking it would be inventing a rule to enforce.
    """
    try:
        held = settings.get(HOST_KEY)
    except settings.SettingsError:
        return HOST
    return held.strip() if isinstance(held, str) and held.strip() else HOST


def make_server(port: int = DEFAULT_PORT, host: str = HOST, asks: bool = True) -> Server:
    return Server((host, port), Handler, asks=asks)


def _declare_backup() -> None:
    """O job do backup, pré-declarado UMA vez, na subida do processo que mantém
    o relógio (§4, item 24; TASK-133).

    **É pré-declarado aqui porque a `cli` que declara um job agendado ainda não
    existe** (TASK-139): enquanto ela não chega, quem põe a linha é a subida, e
    ela é idempotente — uma linha de `backup:make` que já exista NÃO é tocada
    nem recriada, seja qual for o estado em que uma pessoa a tenha deixado
    (desligar de verdade é o verbo da TASK-139, não desta subida).

    **O dono é o primeiro administrador.** §4 diz que o job roda com a autoridade
    de quem o possui, e uma pasta sem pessoa nenhuma não tem a quem dar o job —
    então ela não declara nada, e nada se perde: sem administrador não há a quem
    avisar de um backup que não saiu.

    O `when` inicial é AGORA, e o relógio o reescreve a cada rodada; quem decide
    se a cópia sai é a cadência própria do backup (`backup.due`), nunca o `when`.
    """
    if files.readonly():
        return
    owner = actors.first_admin()
    if owner is None:
        return
    declared = jobs.what(backup.OBJECT, backup.MAKE)
    if any(
        isinstance(row, dict) and row.get(jobs.WHAT) == declared
        for row in store.load(jobs.JOB)
    ):
        return
    tables.create(
        jobs.JOB,
        {
            jobs.WHAT: declared,
            jobs.TABLE: backup.OBJECT,
            jobs.ARGUMENTS: [],
            jobs.ACTOR: store.number_of(owner),
            jobs.WHEN: tables.utc(clock.now()),
            jobs.STATUS: jobs.SCHEDULED,
        },
    )


def beat(server: "Server | None" = None, times: int | None = None,
         pause: Callable[[float], None] = time.sleep) -> None:
    """The clock's rhythm: one pass, then the cadence, over and over (§4, item 24).

    **The WebApp is where the clock lives, and it is the process AT already
    raises.** A job has no clock of its own, and the process that manages it IS
    this one — which is exactly why item 24 puts the clock here, and why the
    clock leaves the day the engine does. It is a THREAD and not a loop inside
    `serve_forever`: the two do not know each other, so a pass neither waits for
    a request nor blocks one.

    **A pass that raises does not take the clock down.** A clock that stopped is
    a folder whose jobs stopped with it, and nobody to say so — so the failure is
    said (in AT's words, with the machine's message inside, because a bug's text
    is the only thing that can be diagnosed from) and the rhythm goes on. The
    reminder's round (§4, item 29's second slice) shares the pass and the same
    guard: the two rounds do not know about each other, so one that raises does
    not take the other down either.

    **The reminder's round is handed the notifier's derived key, read at
    `keys.boot` and kept nowhere but this process's memory** (§4, item 50): a
    boot with no key still rounds — `notifier.publish` answers `no_token`
    rather than sending an envelope nobody here could open.

    **The Vault's round shares the same guard, and its own `Watcher` is born
    once, here** (TASK-154): a `strongbox.Watcher` holds the pasta's retrato
    and the writes still settling between two rounds, so it has to be the
    SAME object across the whole rhythm and not one built fresh inside the
    loop — a fresh one every round would never see a write settle, because
    settling is read against the round before. It rounds on the job clock's
    own cadence and not a faster one of its own: a Vault is not a chat, and
    one more thread with one more rhythm is a cost this fatia does not ask
    for.

    **A quarta rodada é o vigia da página, e só existe com um `server`**
    (TASK-128, fatia 2/3): o que ele vigia é `Arquivos/`
    (`paths.prose_dir()`) — a mesma pasta que `FileTree.vue` relê hoje ao
    cutucar —, e o que ele faz ao ver uma escrita é publicar no
    `Broadcaster` do servidor (`server.events`), que repassa para toda aba
    com uma conexão `/api/events` aberta. `server` é `None` nos testes que
    só provam as outras rodadas (`TheProcess`, abaixo) — sem servidor não há
    `Broadcaster` para publicar em, e a rodada simplesmente não nasce, como
    sempre foi antes desta fatia.

    `times` and `pause` are the seams a test drives: the pass is proven with the
    instant handed to `at.ui.ask.tick`, and these are how the same pass is
    proven without the machine's hour and without sleeping through a cadence.
    """
    watcher = strongbox.Watcher()
    page_vigia = None
    if server is not None:
        page_vigia = vigia.Vigia(paths.prose_dir())
        page_vigia.watch(lambda event: server.events.publish())
    done = 0
    while times is None or done < times:
        try:
            door.tick()
        except Exception as error:  # noqa: BLE001 — the clock does not die of a pass
            print(i18n.tr("webapp.clock_failed", error=error))
        try:
            door.remind(key=keys.notifier_key())
        except Exception as error:  # noqa: BLE001 — same guard, the other round
            print(i18n.tr("webapp.clock_failed", error=error))
        try:
            watcher.tick(keys.strongbox_key())
        except Exception as error:  # noqa: BLE001 — same guard, the third round
            print(i18n.tr("webapp.clock_failed", error=error))
        if page_vigia is not None:
            try:
                page_vigia.scan()
            except Exception as error:  # noqa: BLE001 — same guard, the fourth round
                print(i18n.tr("webapp.clock_failed", error=error))
        done += 1
        if times is None or done < times:
            pause(_rest(clock.CADENCE.total_seconds()))


def _rest(period: float) -> float:
    """The seconds until the next boundary of `period` — the beat lands ON the
    grid instead of drifting a little later with every pass.

    Com a cadência no minuto, um passo que derrapa (a cadência MAIS o trabalho
    da passada, a cada passada) acaba pulando um minuto inteiro — e um lembrete
    marcado para esse minuto não toca. Dormir até a PRÓXIMA borda reseta a
    deriva a cada passada, e é o que faz "toca às 18h00" valer mesmo depois de
    horas de batida.
    """
    return period - (time.time() % period)


# How long `run` waits for whoever already holds the port to answer
# `/api/session` before giving up on knowing who it is. Local and fast: the
# instance on the other end is on THIS machine's loopback (or reached the same
# way the person reaches it), never a wait worth making a person sit through.
INSTANCE_PROBE_TIMEOUT = 0.5


def _instance_version(where: str, port: int) -> str | None:
    """The version of whoever already answers on that port, or `None`.

    Asked over HTTP and never guessed from HOW the thing was started: a loose
    `at-cli webapp`, a machine service and the container of §7c all answer the
    same `/api/session` the same way, so ONE probe covers every case this
    product can meet on a port — nothing here has to tell them apart. `None`
    covers everything that is not that answer: a closed port that only took
    the handshake, a page that is not AT's, a body the session payload never
    takes this shape in.
    """
    request = urllib.request.Request(f"http://{where}:{port}/api/session")
    try:
        with urllib.request.urlopen(request, timeout=INSTANCE_PROBE_TIMEOUT) as answer:
            payload = json.loads(answer.read())
    except (OSError, ValueError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    return version if isinstance(version, str) else None


def _version_order(version: str) -> tuple[int, ...]:
    """A version as the numbers in it, for the one comparison this needs:
    which of two is ahead.

    The same rule `at_deploy/environment.py:order` reads image pins by — but
    not imported from there: `at` does not depend on `at_deploy` (that half
    needs the machine and elevation, this one does not), so the few lines are
    repeated instead of reached for across the line that separates them.
    """
    numbers: list[int] = []
    for part in version.replace("-", ".").replace("_", ".").split("."):
        digits = "".join(character for character in part if character.isdigit())
        if digits:
            numbers.append(int(digits))
    return tuple(numbers)


def _report_taken(where: str, port: int) -> None:
    """The port is somebody else's — and, when that somebody is an AT, which
    version it is and the way out that fits (§3: the pin only moves forward).

    A version this cannot read at all falls back to the plain refusal: named
    port, named way out, nothing guessed about who is holding it. Otherwise
    it is one of three: the SAME version (nothing to do — it is already the
    WebApp this command would have started, loose or as a service, and this
    probe cannot tell which); AHEAD (this at-cli is the one behind, and the
    way out is updating IT); or BEHIND, where the way out is updating the
    instance itself. That word — `at-deploy update` — does not exist yet, so
    this only NAMES the exit and never runs it; once it exists, the missing
    piece is `at-deploy` itself, offered and never fetched, the same way the
    Podman and the `certutil` gaps are (`docs/pt_BR/container.md`).
    """
    url = f"http://{where}:{port}"
    theirs = _instance_version(where, port)
    if theirs is None:
        print(i18n.tr("webapp.port_taken", port=port))
        return
    mine = _version_order(__version__)
    order = _version_order(theirs)
    if order == mine:
        print(i18n.tr("webapp.instance_up", url=url, version=theirs))
    elif order > mine:
        print(i18n.tr("webapp.instance_ahead", url=url, theirs=theirs, mine=__version__))
    else:
        print(i18n.tr("webapp.instance_behind", url=url, theirs=theirs, mine=__version__))
        deploy = paths.deploy_file()
        if not (paths.working_folder() / deploy).is_file():
            print(i18n.tr("webapp.instance_behind_no_deploy", deploy=deploy))


def run(port: int = DEFAULT_PORT, public_port: int | None = None,
        host: str | None = None, include_caddy: bool = True) -> int:
    """Put AT on a port — in HTTP, or behind the Caddy's TLS.

    **One refusal lives here, and it is not a rule about exposure: it is the
    certificate.** `tls internal` is issued FOR A NAME (§3), and "every address"
    is the absence of one — a Caddy that took `0.0.0.0` would start and never
    finish a handshake. The address itself is the folder's choice
    (`chosen_host`), and the default is the loop; where the address is asked
    about and where it is not is the module docstring's. The raw server is what
    the route tests build, and it is not a hole: it is the folder that asks
    nothing, and `_asks` is where that is decided.

    **`public_port` is the bind port, unless something out there bends that**
    (TASK-187's follow-up): the Caddy right here is not always the one the
    browser's TLS lands on — `tailscale serve` terminates its own and proxies
    to this one, on a LOCAL port picked only to stay out of that front door's
    way. Left as `None`, the two are the same port, which is every run without
    one of those in front, this very repository's own `at-cli webapp --port
    12399` included. Said explicitly, it is what Authelia's portal tells the
    browser — the port it actually reaches, and never the bind the front door
    already swallowed.

    **And the clock starts with it** (§4, item 24): a daemon thread that rounds
    the jobs which have come round, born here and gone with the process. It is
    NOT in `make_server`, and that is the same line the refusal above draws —
    the route tests build a bare server, and nothing of theirs may move with an
    hour the machine chose.

    **And the derived keys are read here, once, before anything else** (§4,
    item 50): whatever `at_deploy.environment._webapp_env` handed this process
    is popped off `os.environ` and kept in `keys` for the life of the process —
    `keys.boot` is idempotent, but a second boot in the same run would just find
    nothing left to read, which is why this is the one call site.
    """
    from at.i18n import tr

    keys.boot()

    # The port that reaches the browser, and `port` itself whenever nobody
    # says otherwise — see the docstring on `public_port`.
    public = public_port if public_port is not None else port

    # WHETHER THIS RUN ASKS. A run from the source tree does not: it serves
    # whoever is testing it, on the loop, and the install-time coin of "no actor
    # yet" must not stand between that person and the page. The BUNDLE always
    # asks, and that is the whole rule — `paths.source` is the artifact
    # answering, and there is no flag beside it (`paths.source` says why).
    asks = not paths.source()

    where = host or (GATE_LOOPBACK_NAME if include_caddy else chosen_host())

    # "Sem ator nenhum o AT não expõe" (§3, Acesso e exposição): a folder with
    # nobody to enter it does not open its page. The engine's row does not count
    # — it does not enter, the person does (`actors.can_expose`). It is asked
    # only of a run that ASKS: the refusal is about an entrance, and a run with
    # none is not a run with a door to close.
    #
    # **E ela não RECUSA mais: ela fica no LAÇO** (TASK-176, fatia 3/3). A
    # primeira subida é uma PÁGINA agora, e o formulário que cria o primeiro
    # administrador é uma tela desta casa — para ele existir, este processo tem
    # de estar de pé. O que a regra de §3 compra é o ENDEREÇO, e ele continua
    # comprado: sem ator nenhum o AT não responde fora do laço, nem por
    # `--host`, nem atrás do Caddy (`include_caddy` publica na rede, e é a
    # mesma exposição). O que fica de fora é a população que o terminal já
    # servia: quem está na máquina.
    if asks and not actors.can_expose() and (include_caddy or not loopback(where)):
        print(tr("webapp.no_admin"))
        return 1

    if include_caddy and caddy.wildcard(where):
        print(tr("caddy.address_needs_name", host=where))
        return 1

    # TASK-177: the bundle now always brings the gate beside the TLS, and
    # Authelia refuses a cookie domain this blunt before anything else
    # even unpacks (`authelia.valid_cookie_domain`, measured against the real
    # binary) — said here, before a port is taken or a secret drawn.
    if include_caddy and not authelia.valid_cookie_domain(where):
        print(tr("authelia.cookie_domain", host=where))
        return 1

    # Exposed, the WebApp takes an EPHEMERAL port on the loop and the Caddy holds
    # the port the person reaches: two processes cannot share one, and moving the
    # WebApp is the move that keeps the exposed address the stable one.
    try:
        server = make_server(0 if include_caddy else port,
                             HOST if include_caddy else where, asks=asks)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        # A port somebody else is already serving on is the way this fails in
        # practice — the PoC on 12345, or a second AT — and the bare `OSError:
        # Address already in use` names neither the port nor a way out. When
        # the somebody is an AT, `_report_taken` asks it which version and
        # names the way out that fits; otherwise it falls back to naming just
        # the port and the two generic ways out: another port, or freeing
        # this one.
        _report_taken(where, port)
        return 1

    process = None
    authelia_process = None
    if include_caddy:
        if not caddy.unpacked():
            print(tr("caddy.unpacking", where=caddy.directory()))
        if caddy.ensure() is None:
            server.server_close()
            print(tr("caddy.no_payload", platform=caddy.label()))
            return 1

        # TASK-177: the bundle's other vendored binary, unpacked the
        # same way and with the same refusal — said, not guessed, before
        # either of the two is asked to run.
        if not authelia.unpacked():
            print(tr("authelia.unpacking", where=authelia.directory()))
        if authelia.ensure() is None:
            server.server_close()
            print(tr("authelia.no_payload", platform=authelia.label()))
            return 1

        # O segredo do portão que o Caddyfile abaixo carrega — sorteado uma
        # vez, mantido em claro ao lado da pasta do Caddy (`caddy.draw_gate`'s
        # own docstring diz por quê), e lido de novo em toda subida seguinte
        # em vez de sorteado outra vez.
        caddy.draw_gate()

        # Authelia first: the Caddyfile below names its loopback address, so
        # it has to exist before that file is written.
        # O Authelia FICA DE PÉ entre subidas: se já há um respondendo na porta
        # lembrada, esta subida o REUSA. A sessão da pessoa vive nele, e
        # reiniciar o `at-cli` não pode reiniciá-lo — só a primeira subida (ou
        # uma em que ele caiu) sobe um novo. Quem o reinicia é a pessoa.
        standing = authelia.standing()
        if standing is not None:
            authelia_port, authelia_config = standing
            authelia_process = None
            print(tr("authelia.reused", port=authelia_port))
        else:
            authelia_port = authelia.free_port()
            authelia_config = authelia.write(where, authelia_port, public)
            authelia_process = authelia.start(authelia_config)
            if not authelia.started(authelia_process):
                server.server_close()
                print(tr("authelia.start_failed"))
                return 1
            authelia.remember(authelia_port)

        # `gate.standing`'s own self-check (`_gate`, §6) reads this exactly as
        # the container path's environment hands it over — a bare
        # `host:port`, no scheme — and a folder once committed to the gate on
        # THAT path carries the commitment into this one too, since the two
        # share the same `settings.json`. Left unset, `gate.portal` reads
        # nothing, `standing` is never true, and every request this bundle's
        # own Authelia just proved closes anyway on a 503 that blames a
        # portal which is, in fact, up.
        os.environ[gate.GATE_ENV] = f"{caddy.LOOPBACK}:{authelia_port}"

        # O ntfy saiu: a notificação é o Web Push do próprio PWA
        # (`core.push`), e o Caddy não publica um segundo site. O Caddyfile
        # que sobe tem UM site — o AT —, e a porta que a pessoa alcança é a
        # dele só.
        config = caddy.write_caddyfile(
            where, port, server.server_address[1],
            auth=f"{caddy.LOOPBACK}:{authelia_port}",
        )
        process = caddy.start(config)
        if not caddy.started(process):
            # The Caddy holds the port the person reaches, so its failure is the
            # command's: an AT that answered with a URL here would be announcing
            # an address nothing is on. O Authelia NÃO é parado: ele fica de pé
            # para a próxima subida o reusar (a sessão vive nele).
            server.server_close()
            print(tr("webapp.port_taken", port=port))
            return 1

    url = f"https://{where}:{port}" if include_caddy else f"http://{where}:{port}"
    print(tr("caddy.serving", url=url) if include_caddy
          else tr("webapp.serving", url=url))
    # AND WHETHER THIS RUN ASKS, said out loud: a person who expected an
    # entrance and does not find one should not have to guess why — and the
    # sentence is the same fact (`asks`), said once in the language on screen.
    if not asks:
        print(tr("webapp.source_open"))
    # The clock, kept by the process that is already up (§4, item 24). It is a
    # DAEMON: it dies with the server, and nothing has to stop it — the folder
    # that is idle is exactly the one it is here for. `server` travels with it
    # now (TASK-128, fatia 2/3): it is what lets the clock's own page-vigia
    # round reach the `Broadcaster` every open tab's `/api/events` subscribed to.
    # And the backup's own job is declared before it beats once (TASK-133): the
    # round that copies the folder on its own has no other door to be born by.
    _declare_backup()
    threading.Thread(target=beat, args=(server,), daemon=True, name=CLOCK_THREAD).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl-C is how a person stops a server; it is not a failure.
        pass
    finally:
        caddy.stop(process)
        # E o Authelia FICA DE PÉ: a sessão da pessoa vive nele, e derrubá-lo
        # aqui seria perdê-la a cada reinício do `at-cli`. Quem o reinicia é a
        # pessoa — a subida seguinte o reusa (`authelia.standing`).
        server.server_close()
    return 0
