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

import ipaddress
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from at import __version__, convert, i18n  # noqa: F401
from at.core import (
    gate,  # noqa: F401 — `webapp.gate` is patched by the tests
    jobs,
    permissions,
    tables,
    vigia,  # noqa: F401 — `webapp.vigia` is patched by the tests
)
from at.data import schema
from at.prose import payload as shape
from at.ui.webapp import keys, session  # noqa: F401 — `webapp.keys` is read by `local.py`
from at.ui.webapp.clock import (  # noqa: F401
    CLOCK_THREAD,
    _declare_backup,
    _rest,
    beat,
    start_clock,
)
from at.ui.webapp.entry import (  # noqa: F401
    PAGE_WORDS,
    SESSION_WORDS,
    _declare_args,
    _worded,
    catalogue_payload,
    entry_payload,
    state_payload,
)

# `DEFAULT_THEME`, `HERE`, `THEMES` and `VENDOR` are not used here: they stay
# importable from `app` because the tests (and `webapp.X` callers) read them there.
from at.ui.webapp.launch import (  # noqa: F401
    HOST_KEY,
    INSTANCE_PROBE_TIMEOUT,
    WARM_TEXT,
    _instance_version,
    _report_taken,
    _spawn_spelling_checker,
    _terminate_as_interrupt,
    _version_order,
    _warm_spelling_checker,
    chosen_host,
    on_serving,
    run,
)
from at.ui.webapp.look import (  # noqa: F401
    _CONTENT_TYPES,
    ASSETS,
    DEFAULT_THEME,
    HERE,
    ICONS,
    THEMES,
    UI_ASSETS,
    UI_DIR,
    VENDOR,
    _strongbox_content,
    active_theme,
    base_css_path,
    hosted,
    served,
    theme_css,
    theme_label,
    theme_rows,
    theme_sides,
)
from at.ui.webapp.routes_ai import AiRoutes
from at.ui.webapp.routes_files import FileRoutes
from at.ui.webapp.routes_gate import (  # noqa: F401
    _UNASKED,
    BASIC_KEY,
    GATE_IDENTITY,
    LOCAL_COOKIE,
    REALM,
    GateRoutes,
    _cookie_named,
    basic_allowed,
    basic_pair,
)
from at.ui.webapp.routes_get import GetRoutes
from at.ui.webapp.routes_offline import OFFLINE_WRITES, OfflineRoutes  # noqa: F401
from at.ui.webapp.routes_push import PushRoutes
from at.ui.webapp.routes_send import CSP, MAX_BODY, SendRoutes  # noqa: F401
from at.ui.webapp.routes_sse import EVENTS_HEARTBEAT, SseRoutes  # noqa: F401
from at.ui.webapp.routes_strongbox import StrongboxRoutes
from at.ui.webapp.routes_tables import TABLE_WRITES, TableRoutes  # noqa: F401
from at.ui.webapp.serve import DEFAULT_PORT, HOST, Server, make_server  # noqa: F401

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

# ------------------------------------------------------------- handler ---


class Handler(
    AiRoutes, FileRoutes, GateRoutes, GetRoutes, OfflineRoutes, PushRoutes,
    SendRoutes, SseRoutes, StrongboxRoutes, TableRoutes,
    BaseHTTPRequestHandler,
):
    server_version = "at-webapp/1"

    # The server this handler is bound to is OURS (`Server`, in `serve.py`), and the
    # routes read its state: the base class only promises a `BaseServer`.
    server: Server  # type: ignore[assignment]

    # The session of the request being served, until `_in` computes it.
    _held: object = _UNASKED

    # The `Set-Cookie` the LOCAL MODE's token earns this request, if any — see
    # `_local_gate`. `None` for every request outside that mode, which is every
    # request `at-cli webapp` ever serves.
    _local_cookie: str | None = None

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
        self._local_cookie = None
        super().handle_one_request()

    # ------------------------------------------------------------ output --

    def _not_found(self) -> None:
        self._text("not found\n", status=404)

    def _declarable_payload(self) -> list[dict]:
        """What the `declare` panel may offer to schedule — every declared
        table whose CRUD this actor already reaches directly, each with the
        writes legal to it and, for `create`/`edit`, the fields a row of it
        takes (relógio, fatia 3/3).

        **`_crud_actions` and not `_table_actions`, on purpose.** The clock's
        own round (`ask._acted`) only ever runs `create`/`edit`/`cancel`/
        `delete` for a table — an own act has no branch there and falls into
        the `edit` one by accident — so offering one here would let a person
        schedule a `scan` that silently becomes an `edit`. `job` itself is
        left out: declaring a job that declares a job is not a round the
        clock is built to run, and the picker is not the place to find out.

        **This is the picker's own honesty, not the ceiling.** §4's "the
        owner's ceiling, read again on every round" (`ask._ceiling`) is what
        actually guards every round the clock fires, whoever declared it —
        this list only keeps the picker from offering what would refuse on
        the spot, every single time, for THIS actor.
        """
        found = []
        for declared in schema.declared():
            table = declared.get("id")
            if not isinstance(table, str) or table == jobs.JOB:
                continue
            writes = self._crud_actions(table)
            if not writes:
                continue
            found.append({
                "key": table,
                "name": tables.table_name(table, many=True),
                "actions": [
                    {
                        "action": action,
                        "label": permissions.action_label(action),
                        "requires_id": action != "create",
                        "fields": shape.schema_payload(table) if action in ("create", "edit") else [],
                    }
                    for action in writes
                ],
            })
        return found

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

    # -------------------------------------------------------------- verbs --

    def do_GET(self) -> None:  # noqa: N802 — the name http.server dispatches on
        if not self._local_gate():
            return
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
        if not self._local_gate():
            return
        segments = [part for part in urlparse(self.path).path.split("/") if part]
        # A PASTA, antes até da entrada (TASK-169, fatia 2/3): sem ela não há
        # sessão, nem admin, nem nada — é a mesma razão que põe `/api/session`
        # e `/api/first` acima do portão, um passo antes das duas.
        if segments == ["api", "folder"]:
            self._post_folder()
            return
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
        if segments == ["api", "file", "create"]:
            if not self._may("prose:edit"):
                return
            self._post_file_create()
            return
        if segments == ["api", "file", "rename"]:
            if not self._may("prose:edit"):
                return
            self._post_file_rename()
            return
        if segments == ["api", "file", "delete"]:
            if not self._may("prose:edit"):
                return
            self._post_file_delete()
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
        if segments == ["api", "job"]:
            self._post_job()
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

    # The server's own log line is noise on a phone screen and in a journal; the
    # surface that matters is the page.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


# ------------------------------------------------------------------ run ---

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
