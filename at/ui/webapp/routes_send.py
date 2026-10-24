"""The answers of the Handler: `_send` and the helpers that write a response
(`_head`, `_text`, `_json`, `_page`, `_file`, the `Range` and the file written in
blocks), and `_body`, the guarded request body every write reads.

Moved out of `app.py` (B-6) without a change of behaviour. `SendRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_not_found`,
`_local_cookie` and the request (`headers`, `rfile`, `wfile`, `command`) from the
`Handler`. `CSP` and `MAX_BODY` came along because only these two read them.
This module does not import `app` at the top.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from at.ui.webapp.look import _CONTENT_TYPES
from at.ui.webapp.routes_base import RouteBase

# The page runs under this, which is why nothing inline and no `data:` is ever
# built into it: Vite is configured for it, and the themes are checked for it.
CSP = "default-src 'self'"

# How much a write may carry. A table row is small; the ceiling is what stops a
# stranger's stream from becoming this process's memory.
MAX_BODY = 64 * 1024


class SendRoutes(RouteBase):
    def _send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self._head(status, len(body), ctype, extra)
        if self.command != "HEAD":
            self.wfile.write(body)

    def _head(self, status: int, length: int, ctype: str,
              extra: dict | None = None) -> None:
        """The headers of an answer whose body is NOT in memory.

        The body of a file is written in BLOCKS (`_send_file`), and the
        `Content-Length` is the one the disk says — the number of bytes that
        will really leave.
        """
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        # Nothing here is worth a cache: the page is served fresh on purpose, so
        # that the language and the theme the server resolved are the ones drawn.
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        if self._local_cookie:
            # A SEGUNDA linha de `Set-Cookie` que uma resposta pode levar — a
            # primeira é a `extra` acima, que nenhuma rota do modo local usa
            # (o Forms está desligado nele). Duas linhas do mesmo nome são o
            # jeito certo de um cabeçalho HTTP carregar mais de um cookie.
            self.send_header("Set-Cookie", self._local_cookie)
        self.end_headers()

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
        self._send_file(path,
                        _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"),
                        headers or None)

    # The block a file is written in. The file arrives WHOLE — this is a
    # download, not a truncation — but the server never holds it whole: a
    # 1,47 GB `.txt` read at once gave a peak of 2,2 GB of RSS.
    _BLOCK = 64 * 1024

    def _range_of(self, size: int) -> tuple[int, int] | None:
        """The ONE range the client asks for, as `(start, end)`, or None.

        A single range is what a video player's own seek asks for. A request
        the server does not understand is answered with the WHOLE file (a
        200) rather than with a refusal: the download still lands.
        """
        header = (self.headers.get("Range") or "").strip()
        if not header.startswith("bytes="):
            return None
        spec = header[len("bytes="):].strip()
        if "," in spec:
            return None
        first, _, last = spec.partition("-")
        try:
            if not first:
                # `bytes=-N` — the LAST N bytes.
                length = int(last)
                if length <= 0:
                    return None
                start, end = max(0, size - length), size - 1
            else:
                start = int(first)
                end = int(last) if last else size - 1
        except ValueError:
            return None
        if start < 0 or start >= size or start > end:
            return None
        return start, min(end, size - 1)

    def _send_file(self, path: Path, ctype: str, extra: dict | None = None) -> None:
        """A file, written in BLOCKS — never read whole into the memory.

        The `Content-Length` is the one the disk says, and the bytes leave in
        the order they are on it. A `Range` (206) is served for the one range
        a video player asks for when it seeks, and `Accept-Ranges` tells it
        that it may.
        """
        try:
            size = path.stat().st_size
        except OSError:
            self._not_found()
            return
        headers = dict(extra or {})
        headers["Accept-Ranges"] = "bytes"
        span = self._range_of(size)
        if span is None:
            status, start, length = 200, 0, size
        else:
            start, end = span
            status, length = 206, end - start + 1
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        self._head(status, length, ctype, headers)
        if self.command == "HEAD":
            return
        try:
            with path.open("rb") as handle:
                if start:
                    handle.seek(start)
                remaining = length
                while remaining > 0:
                    block = handle.read(min(self._BLOCK, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            # The client went away in the middle of the download — the tab
            # closed, the browser had what it wanted. There is nobody left to
            # send the rest to, and it is not an error of the server.
            return

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
