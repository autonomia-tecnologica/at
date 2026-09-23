"""The WebApp server — the bill's UI, on loopback.

It serves three things, and nothing else: the built page, the LOOK (base.css,
the themes, the drawings, the hosted typefaces) and the JSON the page reads. The
page owns no rule — the server decides, the page draws.

**No authentication of its own.** The only way in is loopback, and the guard
belongs to the ingress (Authelia, at the tailnet edge, one login for every app);
a second password here would be a second prompt for what was already answered.
What stands in its place is the pair of guards on every write: `Origin` must
carry the same authority as `Host`, and the body must declare itself JSON. That
is what tells our own page's write apart from a foreign page's form post.

The theme is a LOOKUP against the registry, never a path: an id that names no
theme falls back to the default, so a query string can never reach a file the
registry does not name.
"""

from __future__ import annotations

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bill import i18n, nlu
from bill.core import files, projects, risk, tables
from bill.data import schema, store
from bill.prose import listing as prose
from bill.ui import ask as door

HOST = "127.0.0.1"
DEFAULT_PORT = 12345
DEFAULT_THEME = "bill"

# The page runs under this, which is why nothing inline and no `data:` is ever
# built into it: Vite is configured for it, and the themes are checked for it.
CSP = "default-src 'self'"

# How much a write may carry. A table row is small; the ceiling is what stops a
# stranger's stream from becoming this process's memory.
MAX_BODY = 64 * 1024

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
    for candidate in (requested, os.environ.get("BILL_THEME"), DEFAULT_THEME):
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
    from bill.i18n import active_code

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


# ------------------------------------------------------------------ api ---

# The words the PAGE reads. They come from the catalog like everything else —
# the page writes none of its own (§3) — and they travel in every language, so
# switching the language costs no request.
PAGE_WORDS = (
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
)


def state_payload() -> dict:
    row = active_theme(None)
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

class Handler(BaseHTTPRequestHandler):
    server_version = "bill-webapp/1"

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

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _page(self, path: Path, status: int = 200) -> None:
        """An HTML document — the only place the policy travels, because it is
        the only place that runs anything."""
        try:
            body = path.read_bytes()
        except OSError:
            # "Not built" and "broken" are different things, and the status is
            # what tells a monitor which of the two it is. The policy comes along
            # even here: it belongs to the route, not to the answer's luck.
            self._text("UI not built — run: cd bill/ui/webapp && npm ci && npm run build\n",
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
        if segments == ["api", "file"]:
            self._post_file()
            return
        if segments == ["api", "ask"]:
            self._post_ask()
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
        if rest == ["state"]:
            self._json(state_payload())
            return

        if rest == ["projects"]:
            self._json(projects.tree() if projects.available() else [])
            return

        if rest == ["orphans"]:
            self._json(self._orphans_payload())
            return

        if len(rest) == 2 and rest[0] == "project":
            self._get_project(rest[1])
            return

        if rest == ["tree"]:
            self._json({
                "root": "",
                "files": [
                    {"path": path, "bucket": prose.bucket(path)}
                    for path in prose.listed()
                ],
            })
            return

        if rest == ["file"]:
            self._get_file(query.get("path", [""])[0])
            return

        if len(rest) == 2 and rest[0] == "table":
            table = rest[1]
            if schema.of(table) is None:
                self._json({"error": f"unknown table: {table}"}, 404)
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

        The door is `bill.ui.ask`, which the `cli` reads too — the page walks the
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
        result = door.ask(sentence)
        self._json({"kind": result.kind, "proposal": result.proposal, "text": result.text})

    def _post_table(self, table: str) -> None:
        if schema.of(table) is None:
            self._json({"error": f"unknown table: {table}"}, 404)
            return
        payload = self._body()
        if payload is None:
            return
        action = payload.get("action")
        values = payload.get("set")
        values = {str(k): str(v) for k, v in values.items()} if isinstance(values, dict) else {}
        try:
            if action == "create":
                row = tables.create(table, values)
            elif action == "edit":
                row = tables.edit(table, payload.get("id"), values)
            else:
                self._json({"error": f"unknown action: {action}"}, 400)
                return
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

def make_server(port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, port), Handler)


def run(port: int = DEFAULT_PORT) -> int:
    server = make_server(port)
    from bill.i18n import tr

    print(tr("webapp.serving", url=f"http://{HOST}:{port}"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl-C is how a person stops a server; it is not a failure.
        pass
    finally:
        server.server_close()
    return 0
