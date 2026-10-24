"""The offline route (TASK-162): `POST /api/offline/sync`, where the fila the
Service Worker built offline is reconciled in one round trip.

Moved out of `app.py` (B-6) without a change of behaviour. `OfflineRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_body`, `_json`,
`_actor` and `_may` from the `Handler`. This module does not import `app` at
the top. `app.py` imports `OFFLINE_WRITES` back.
"""

from __future__ import annotations

from at import i18n
from at.core import audit, offline, permissions, tables
from at.prose import payload as shape
from at.ui import ask as door
from at.ui.webapp.routes_base import RouteBase

# The two the OFFLINE QUEUE answers — `offline.QueueEntry`'s own closed list
# (TASK-162), and narrower than `TABLE_WRITES` on purpose: `offline.reconcile`
# has no branch for a `cancel` or a `delete`, and an entry of either shape
# would fall into its `edit` branch and silently reconcile as one — a closing
# or a deletion that reached the server as a no-op write. The row menu's two
# new doors (TASK-122) do not go through the fila: they write ONLINE, through
# `_post_table`, the moment the person confirms.
OFFLINE_WRITES = ("create", "edit")


class OfflineRoutes(RouteBase):
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
            def owing(action: str = action, needed: str = needed) -> None:
                door.denied(
                    offline.TABLE,
                    action,
                    actor=actor,
                    via=audit.WEBAPP,
                    reason=audit.DENIED,
                    saying=i18n.tr(
                        "permission.denied", permission=permissions.label(needed)
                    ),
                )

            if not self._may(needed, owing=owing):
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
                    "record": shape.record(offline.TABLE, res.row) if res.row is not None else None,
                }
                for res in resolutions
            ]
        })
