"""The push route: `POST /api/push/subscribe`, where the browser's
`PushSubscription` is kept.

Moved out of `app.py` (B-6) without a change of behaviour. `PushRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_body` and `_json`
from the `Handler`. This module does not import `app` at the top.
"""

from __future__ import annotations

from at import i18n
from at.core import push
from at.ui.webapp.routes_base import RouteBase


class PushRoutes(RouteBase):
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
