"""O fechamento de um lembrete: `POST /api/reminders/close`.

Um lembrete tem UMA instância corrente — a ocorrência mais recente que já passou
e não foi fechada; fechada essa, a vez é da próxima futura ainda aberta
(`reminder.current`). Fechar é o ato da PESSOA sobre essa ocorrência, e por isso
ele passa pela porta única (`at.ui.ask.run`), a mesma de toda escrita do `cli`,
do intérprete e do WebApp: a linha de auditoria e a versão são da porta, e o
motor só devolve a lista nova (`reminder.with_closed`, pura).

A rota também é quem monta o ITEM que a tela de Lembretes desenha, e o faz aqui
— e não em `routes_get` — porque as duas metades (o que vem, em `GET
/api/reminders`, e o fechamento) precisam do MESMO formato: `freq` e `status` no
texto que a pessoa lê (`tables.text_of`), a instância corrente em
`"AAAA-MM-DD HH:MM"` e o `kind` que diz se ela já venceu, é de hoje ou está por
vir. Duas montagens seriam duas verdades sobre a mesma linha.

`ReminderRoutes` é um mixin (sem `__init__`) que o `Handler` herda: lê `_body`,
`_json`, `_actor` e `_may` do `Handler`. Este módulo não importa `app` no topo.
"""

from __future__ import annotations

import re
from datetime import date

from at import i18n
from at.core import audit, reminder, tables
from at.data import store
from at.ui import ask as door
from at.ui.webapp.routes_base import RouteBase

# O horizonte que a seção "o que vem" abre por padrão, e o teto que ele não passa
# — a query `days` é o que a pessoa escolhe, e um valor fora da faixa é lido no
# limite e nunca como um horizonte sem fim.
DEFAULT_DAYS = 7
MAX_DAYS = 366

# A forma da instância que o fechamento nomeia: dia e hora, exatamente como
# `reminder.current` os devolve (`"AAAA-MM-DD HH:MM"`). Um carimbo que não casa
# não é uma instância, e a rota não adivinha a que a pessoa quis.
INSTANCE = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})$")

# A faixa de cada `kind`, na ordem em que a lista mostra: o vencido primeiro (o
# mais antigo na frente), depois o de hoje, e o que está por vir no fim.
ORDER = {"overdue": 0, "today": 1, "soon": 2}


def reminder_days(query: dict) -> int:
    """O horizonte que a query pediu — `days`, entre 1 e 366, e 7 por padrão.

    Um valor que não é inteiro volta ao padrão em vez de virar erro: a seção
    continua desenhável, e a página que mandou lixo lê o horizonte que sempre
    teve. Fora da faixa, vale o limite.
    """
    raw = (query.get("days") or [""])[0]
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return max(1, min(days, MAX_DAYS))


def reminder_kind(day: date, today: date, overdue: bool) -> str:
    """A faixa da instância: `overdue`, `today` ou `soon`.

    **Vencido manda sobre tudo**: uma ocorrência que já passou e ninguém fechou
    continua sendo o que a tela precisa mostrar, e o horizonte nunca a esconde.
    O de hoje é o que vence hoje sem ter passado; o resto é o que está por vir —
    e quem decide se ele cabe no horizonte é a rota, não esta função.
    """
    if overdue:
        return "overdue"
    if day == today:
        return "today"
    return "soon"


def reminder_item(row: dict, day: date, hour: str, kind: str) -> dict:
    """A linha como a tela de Lembretes a desenha.

    `freq` e `status` vão no TEXTO que a pessoa lê (`tables.text_of`, o mesmo
    que a tabela usa) e não no enum cru — a página inventa palavra nenhuma. O
    `next` é a instância corrente no formato do motor.
    """
    return {
        "id": row.get("id"),
        "text": row.get("text"),
        "freq": tables.text_of(reminder.REMINDER, "freq", row.get("freq")),
        "at": row.get("at"),
        "status": tables.text_of(reminder.REMINDER, "status", row.get("status")),
        "active": row.get("status") == reminder.ACTIVE,
        "next": f"{day.isoformat()} {hour}",
        "kind": kind,
    }


def instance_of(text: object) -> tuple[date, str] | None:
    """A instância que o corpo nomeia, ou `None` quando não é uma.

    O formato é o do motor (`"AAAA-MM-DD HH:MM"`), e um dia que não existe no
    calendário ou uma hora fora de `HH:MM` não viram uma data aproximada: é
    `None`, e a rota responde 400.
    """
    if not isinstance(text, str):
        return None
    found = INSTANCE.match(text)
    if found is None or not reminder.HOUR.match(found.group(2)):
        return None
    try:
        day = date.fromisoformat(found.group(1))
    except ValueError:
        return None
    return day, found.group(2)


class ReminderRoutes(RouteBase):
    def _post_reminders_close(self) -> None:
        """Fecha UMA ocorrência da linha — o "esta já foi" da pessoa.

        **Idempotente de propósito.** O mesmo push pode chegar duas vezes, e um
        carimbo repetido não é um segundo fechamento: quando a ocorrência já
        está em `closed`, a rota não escreve de novo e responde com a instância
        corrente, que é o que a pessoa veria depois do primeiro.

        **O que não é a instância corrente também não é um fechamento** — um dia
        que a recorrência não alcança, uma hora que a linha não toca, um carimbo
        fora do formato: é 400, e nada é escrito.

        A escrita é a da porta única, com o `via` do WebApp e o ator que a
        requisição provou; o motor devolve a lista nova de `closed` e nunca
        escreve na tabela (`reminder.with_closed`).
        """
        payload = self._body()
        if payload is None:
            return
        pid = payload.get("id")
        row = (
            store.find(reminder.REMINDER, pid)
            if isinstance(pid, int) and not isinstance(pid, bool)
            else None
        )
        if row is None:
            self._json(
                {
                    "error": i18n.tr(
                        "table.error.unknown_row",
                        id=pid,
                        table=tables.table_name(reminder.REMINDER, many=True),
                    )
                },
                404,
            )
            return
        when = instance_of(payload.get("instance"))
        if (
            when is None
            or not reminder.occurs(row, when[0])
            or when[1] not in reminder.hours(row)
        ):
            self._json({"error": "bad request"}, 400)
            return
        day, hour = when
        if reminder.closed(row, day, hour):
            self._answer_current(row)
            return
        values = {reminder.CLOSED: reminder.with_closed(row, day, hour)}
        try:
            _, _, written, _, _ = door.run(
                reminder.REMINDER,
                "edit",
                [str(pid)],
                (values, [str(pid)]),
                actor=self._actor(),
                via=audit.WEBAPP,
            )
        except tables.TableError as error:
            self._json({"error": str(error)}, 400)
            return
        self._answer_current(written if written is not None else row)

    def _answer_current(self, row: dict) -> None:
        """`ok` com a instância corrente da linha — ou `null` quando não sobrou.

        Um `once` fechado não tem próxima ocorrência: a linha some da seção, e a
        resposta diz isso com `None` em vez de inventar um item vazio.
        """
        when = reminder.current(row)
        if when is None:
            self._json({"ok": True, "reminder": None})
            return
        day, hour, overdue = when
        self._json(
            {
                "ok": True,
                "reminder": reminder_item(
                    row, day, hour, reminder_kind(day, reminder.today(), overdue)
                ),
            }
        )
