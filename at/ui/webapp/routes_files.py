"""The routes of `Arquivos/`: reading a file (`GET /api/file`, its bytes) and
writing it (save, create, rename, delete).

Moved out of `app.py` (B-6) without a change of behaviour. `FileRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_body`, `_json`,
`_file` and `_not_found` from the `Handler`. This module does not import `app`
at the top.
"""

from __future__ import annotations

from typing import cast

from at import i18n
from at.prose import listing as prose
from at.ui.webapp.entry import _worded
from at.ui.webapp.routes_base import RouteBase


class FileRoutes(RouteBase):
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
        gate (`inside` plus `is_file`, so a name outside the tree
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
        status, answer = prose.write(cast(str, rel), cast(str, text), cast(str, base))
        self._json(_worded(answer), status)

    def _post_file_create(self) -> None:
        """`{path, dir}` → a new empty file or folder in `Arquivos/` (TASK-120,
        fatia 5/7). `dir` tells the two apart — the one thing `prose.create`
        cannot read off the path alone.
        """
        payload = self._body()
        if payload is None:
            return
        rel, is_dir = payload.get("path"), payload.get("dir")
        if not isinstance(rel, str) or not isinstance(is_dir, bool):
            self._json({"error": "bad request"}, 400)
            return
        status, answer = prose.create(rel, is_dir)
        self._json(_worded(answer), status)

    def _post_file_rename(self) -> None:
        """`{path, to}` → `path` under its new name or place (TASK-120, fatia 5/7)."""
        payload = self._body()
        if payload is None:
            return
        rel, to = payload.get("path"), payload.get("to")
        if not all(isinstance(value, str) for value in (rel, to)):
            self._json({"error": "bad request"}, 400)
            return
        status, answer = prose.rename(cast(str, rel), cast(str, to))
        self._json(_worded(answer), status)

    def _post_file_delete(self) -> None:
        """`{path}` → `path` removed from `Arquivos/`, whole if it is a folder
        (TASK-120, fatia 5/7). The page asks the person first (`lib/confirm`);
        the server asks nothing a second time.
        """
        payload = self._body()
        if payload is None:
            return
        rel = payload.get("path")
        if not isinstance(rel, str):
            self._json({"error": "bad request"}, 400)
            return
        status, answer = prose.delete(rel)
        self._json(_worded(answer), status)
