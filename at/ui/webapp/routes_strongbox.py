"""The Vault's two routes: `POST /api/strongbox/open` (the one-time link to a
sealed file's clear) and `GET /api/strongbox/download` (the link, walked once).

Moved out of `app.py` (B-6) without a change of behaviour. `StrongboxRoutes` is
a mixin (no `__init__`) the `Handler` inherits: it reads `_body`, `_json`,
`_send` and `_not_found` from the `Handler`. This module does not import `app`
at the top.
"""

from __future__ import annotations

from pathlib import Path

from at import i18n
from at.core import strongbox
from at.ui.webapp import keys
from at.ui.webapp.look import _strongbox_content
from at.ui.webapp.routes_base import RouteBase


class StrongboxRoutes(RouteBase):
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
