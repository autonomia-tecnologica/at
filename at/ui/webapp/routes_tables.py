"""The REST of the tables: `POST /api/tables/<table>` (create, edit, cancel,
delete) and the answers to "which actions may this actor reach" the pages draw
their menus from.

Moved out of `app.py` (B-6) without a change of behaviour. `TableRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_body`, `_json`,
`_actor`, `_may` and `_legal` from the `Handler`. This module does not import
`app` at the top. `app.py` imports `TABLE_WRITES` back.
"""

from __future__ import annotations

from at import i18n
from at.core import audit, files, permissions, projects, tables
from at.data import schema
from at.prose import payload as shape
from at.ui import ask as door
from at.ui.webapp.routes_base import RouteBase

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


class TableRoutes(RouteBase):
    def _crud_actions(self, table: str) -> list[str]:
        """Which of the engine's own FOUR writes this actor may reach on
        `table` — the half of `_table_actions` that is a CRUD question, kept
        apart because the DECLARE picker (relógio, fatia 3/3) only ever offers
        THESE: an own act scheduled through the clock's road (`ask._acted`)
        falls into its last branch and is run as an `edit`, so a table's own
        act has no business being something a person can schedule this way.

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

    def _table_actions(self, table: str) -> list[str]:
        """Which actions this actor may reach on `table` — the truth a context
        menu shows instead of inventing one (TASK-120), the engine's own four
        (`_crud_actions`) AND the object's OWN acts, when it declares any
        (relógio, fatia 3/3): `job` narrows itself to `run`/`approve`/
        `refuse`/`declare`/`disable` (`permissions.NARROWED`), none of which is
        one of `tables.ACTIONS`, and this is the one place that reads them
        back into the same list a menu already trusted — a table with no own
        act (every table but `job` today) answers exactly what it always did,
        because `permissions.actions` falls back to `tables.ACTIONS` itself
        and the filter below then keeps nothing.
        """
        return self._crud_actions(table) + [
            action for action in permissions.actions(table)
            if action not in tables.ACTIONS
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
        self._json({"record": shape.record(table, row)})
