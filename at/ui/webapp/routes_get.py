"""The GET routes of the API: `_get_api` (the permission each read demands, and
the dispatch to what it reads), the project page, the notifications, the
reminders and the orphan tasks.

Moved out of `app.py` (B-6) without a change of behaviour. `GetRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_json`, `_in`, `_gate`,
`_may`, `_table_actions`, `_project_actions`, `_declarable_payload` and the
other `_get_*` of the sibling mixins from the `Handler`. This module does not
import `app` at the top.
"""

from __future__ import annotations

from at import i18n
from at.core import jobs, notifier, permissions, projects, push, reminder, strongbox, tables
from at.data import schema, store
from at.prose import listing as prose
from at.prose import payload as shape
from at.ui.webapp.entry import catalogue_payload, entry_payload, state_payload
from at.ui.webapp.routes_base import RouteBase


class GetRoutes(RouteBase):
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
            payload = shape.table_payload(table, show_all="all" in query)
            payload["actions"] = self._table_actions(table)
            if table == jobs.JOB:
                # The `declare` panel's own picker (relógio, fatia 3/3) — only
                # the job table has anything to offer it, and the other
                # tables answer every request without this leg existing.
                payload["declarable"] = self._declarable_payload()
            self._json(payload)
            return

        self._not_found()

    def _get_project(self, asked: str) -> None:
        number = tables.number_of("project", asked)
        payload = projects.page(number) if number is not None else None
        if payload is None:
            self._json({"error": "unknown project", "project": asked}, 404)
            return
        payload["fields"] = shape.schema_payload("task")
        payload["records"] = [shape.record("task", row) for row in payload.pop("rows")]
        payload["actions"] = self._table_actions("task")
        # The project's OWN fields, rendered like any other record's: it is what
        # carries the body of an item to the page — the `desc` the table
        # declares `markdown`, plus the status and the priority the tree orders
        # by. The two are named apart on purpose: `fields`/`records` below are
        # the TASKS the page draws, and this pair is the page itself.
        payload["project"] = {
            "fields": shape.schema_payload("project"),
            "record": shape.record("project", payload.pop("row")),
            # The project's OWN row menu (TASK-137, fatia 7/7): the same door
            # `_table_actions` already asks for any table's row, over the
            # project record itself — never `_project_actions`, which is the
            # TREE's different pair (create/edit, never cancel/delete).
            "actions": self._table_actions(projects.PROJECT),
        }
        self._json(payload)

    def _orphans_payload(self) -> dict:
        rows = projects.orphans()
        return {
            "key": "task",
            "title": i18n.tr("webapp.no_project"),
            "filter": None,
            "fields": shape.schema_payload("task"),
            "records": [shape.record("task", row) for row in rows],
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
