"""The door's listing and prose: rows narrowed by the sentence, cards, grids and views.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from at.core import (
    projects,
    reminder,
    tables,
)
from at.data import schema
from at.i18n import tr
from at.nlu import matcher
from at.ui import words
from at.ui.ask_base import OK, PROJECT, TASK, USAGE, _sign, rejected

# The rows the last `_listing` kept, after every narrowing — what `--json` hands
# over as the listing's `table`, so the filter is the listing's and not a second.
last_rows: list[dict] | None = None


def _listing(
    table: str, args: list[str], values: dict | None = None,
    ranges: dict[str, str] | None = None, full_table: bool = True,
) -> tuple[int, str, tuple[list[str], list[list[str]]] | None, list[str] | None]:
    """A table's listing, and the one narrowing the `cli` adds to it: `--all`
    puts back what the declaration hides, and `--project` keeps what one item
    claims.

    The filter is the PAGE's SCOPE and not a second one: a project's tasks are
    the whole of its SUBTREE, the set item 3's page draws. What stays the
    listing's own is the status filter the table declares — `task list` hides
    what is finished, `--all` puts it back — so the scope is shared with the
    page and the narrowing is the listing's, each in its own place.

    **`full_table` is the person's own convention (03/10/2026):** the GRID,
    every declared column, only when the sentence said "tabela"/"table"
    (`nlu.matcher`'s own reading) — the `cli`, which never carries that word at
    all, keeps asking for it by never passing `False` here. Everything else —
    a bare "listar tarefas" — is a bullet, one line per row, the row's own
    TITLE and nothing beside it.
    """
    global last_rows
    last_rows = None
    show_all = "--all" in args
    rest = [arg for arg in args if arg != "--all"]
    wanted: str | None = None
    if rest[:1] == ["--project"] and len(rest) == 2:
        wanted, rest = rest[1], []
    if rest:
        return USAGE, rejected("list"), None, None
    if wanted is not None and not _claims(table):
        return USAGE, rejected("list"), None, None
    rows = tables.rows(table, show_all=show_all)
    if wanted is not None:
        rows = _in_project(rows, wanted)
    values = dict(values or {})
    ranges = dict(ranges or {})
    on_day = _bare_day(table, values, ranges)
    rows = _kept(table, rows, values, ranges)
    if on_day is not None:
        rows = [row for row in rows if reminder.occurs(row, on_day)]
    last_rows = rows
    if not rows:
        return OK, _nothing(table, values, ranges, on_day), None, None
    if full_table:
        header, cells = _table_rows(table, rows)
        return OK, words.table([header, *cells]), (header, cells), None
    # O IDENTIFICADOR VAI JUNTO DO TÍTULO (23/10/2026): é o que a pessoa diz para
    # nomear a linha (`apagar nota 5`), então a lista o mostra.
    bullets = [
        f"{tables.format_id(table, row['id'])} · {tables.title(table, row)}"
        for row in rows
    ]
    return OK, "\n".join(f"- {line}" for line in bullets), None, bullets


def _in_project(rows: list[dict], wanted: str) -> list[dict]:
    """The rows one project's SUBTREE claims — a project nobody has is refused the
    way a row nobody has is, and by the same sentence: the filter is a reference
    like any other."""
    owner = tables.find(PROJECT, wanted)
    scope = set(projects.subtree(owner["id"]))
    return [row for row in rows if projects.project_of(row) in scope]


def _nothing(table: str, values: dict, ranges: dict[str, str], on_day: date | None) -> str:
    """The sentence of a listing that found no row, said the way the person asked."""
    if on_day is not None:
        # Named the way the person asked it: the DAY, not a field nobody
        # said — "nenhum lembrete em 03/10/2026", not "nada aqui ainda".
        when = tables.text_of(reminder.REMINDER, matcher.open_day_field(table) or "", on_day.isoformat())
        return tr("table.reminder.list.empty_on_day", date=when)
    described = _described(table, values, ranges)
    if described:
        return tr(
            "table.list.empty_filtered",
            table=tables.table_name(table, many=True).lower(), filter=described,
        )
    return tr("table.word.empty")


def _bare_day(table: str, values: dict, ranges: dict[str, str]) -> date | None:
    """A day said ALONE, for the `reminder` table — popped out of `values` so
    `_kept` never compares it, and handed back for `occurs` to read instead.

    "Lembretes de hoje" names no field: the day lands on `on_date`, the one
    `nlu.matcher.open_day_field` leaves open for this table (the comment beside
    `reminder.NOTIFIED` is where that wiring is declared). Read as a literal
    field match, `on_date` only holds for a `once` reminder — every `daily`,
    `weekly`, `monthly` and `yearly` row carries no `on_date` at all, so "hoje"
    found NOTHING for the reminder a person has every day. A day is a set of
    INSTANCES, not a stored value (the person's own words for the defect): what
    "hoje" means for this table is `reminder.occurs`, which already reads the
    very recurrence `on_date`'s literal match could only ever cover a slice of.

    Only the EXACT day is read this way — `ranges` empty for the field, which is
    what a bare "hoje"/"amanhã" produces. "lembretes até sexta" keeps the literal
    field comparison: folding a RANGE through the recurrence is a future day's
    work, and falling back to what already existed is not a regression.
    """
    if table != reminder.REMINDER:
        return None
    field = matcher.open_day_field(table)
    if field is None or field not in values or ranges.get(field, "=") != "=":
        return None
    raw = values.pop(field)
    ranges.pop(field, None)
    try:
        return date.fromisoformat(raw) if isinstance(raw, str) else None
    except ValueError:
        return None


def _described(table: str, values: dict, ranges: dict[str, str]) -> str:
    """The filter, in words — "prazo até 03/10/2026", "status ativo" — joined
    the way a person would say more than one at once. The primary field never
    describes (the same reason `_kept` never filters by it): residue is
    content, never a clause an empty listing explains itself with. `""` is a
    bare "listar tarefas", with nothing to describe at all.
    """
    primary = schema.primary(table)
    parts = []
    for name, value in values.items():
        if name == primary or not schema.field(table, name):
            continue
        label = tables.label(table, name).lower()
        text = tables.text_of(table, name, value)
        op = ranges.get(name, "=")
        if op == "<=":
            parts.append(f"{label} {tr('table.list.until')} {text}")
        elif op == ">=":
            parts.append(f"{label} {tr('table.list.since')} {text}")
        elif op in ("<", ">"):
            parts.append(f"{label} {_sign(op)} {text}")
        elif schema.field(table, name).get("type") == "day":
            # A bare day reads as "due by" in how the person already says it
            # ("tarefas para hoje") even though the engine's own match on it
            # is exact — the same leniency `_bare_day` gives `reminder`.
            parts.append(f"{label} {tr('table.list.until')} {text}")
        else:
            parts.append(f"{label} {text}")
    return " e ".join(parts)


def _kept(table: str, rows: list[dict], values: dict, ranges: dict[str, str]) -> list[dict]:
    """O que a FRASE filtrou: cada campo que ela citou mantém só as linhas cujo
    valor casa.

    **O campo de texto livre não filtra** (`schema.primary`): "listar tarefas
    comprar pão" não é "as tarefas cujo texto é exatamente 'comprar pão'" — o
    resíduo de um `list` não é um filtro, e tratá-lo como um esvaziaria a
    listagem que a pessoa esperava ver. O que filtra são os campos que um leitor
    TIPADO preencheu (data, número, valor de enum) — e cada um com a sua
    operação: `=` quando não há palavra de intervalo, `<=`/`>=` quando há.
    """
    primary = schema.primary(table)
    declared = (schema.of(table) or {}).get("fields", {})
    for name, value in values.items():
        if name == primary or name not in declared:
            continue
        op = ranges.get(name, "=")
        rows = [row for row in rows if _matches(row.get(name), value, op)]
    return rows


def _matches(cell: Any, value: Any, op: str) -> bool:
    """Se o valor de uma linha casa com o que a frase pediu, sob `op`.

    Sem operação é igualdade. Com `até`/`desde` é a comparação — e uma célula
    VAZIA (`None`) nunca casa um intervalo: uma tarefa sem prazo não é "até
    sexta". Uma comparação que os tipos não deixam fazer (um texto contra uma
    data) não estoura: não casa.
    """
    if op == "=" or cell is None:
        return cell == value
    try:
        if op == "<=":
            return cell <= value
        if op == ">=":
            return cell >= value
        if op == "<":
            return cell < value
        if op == ">":
            return cell > value
    except TypeError:
        return False
    return cell == value


def _claims(table: str) -> bool:
    """Whether `table` is one a `--project` filter can narrow — a table that
    declares a field of its own pointing at `project`."""
    ref = schema.field(table, "project").get("ref")
    return isinstance(ref, list) and PROJECT in ref


def _viewing(table: str, args: list[str]) -> tuple[int, str, dict | None]:
    """One row's fields — and, for a project, what is inside it.

    A project is a SCOPE and not a table of its own (§4): the page a person
    opens shows the project's own fields and then the tasks of the whole
    subtree, and §5 does not let the `cli` be the surface that cannot. So the
    slices of an item are answered here, by the very rows the page draws.
    """
    if len(args) != 1:
        return USAGE, rejected("view"), None
    row = tables.find(table, args[0])
    lines = [f"{tr('table.field.id')}: {tables.format_id(table, row['id'])}"]
    for name in (schema.of(table) or {}).get("fields", {}):
        if name == "id":
            continue
        lines.append(f"{tables.label(table, name)}: {tables.text_of(table, name, row.get(name))}")
    if table == PROJECT:
        page = projects.page(row["id"]) or {}
        slices = [entry for entry in page.get("rows", []) if isinstance(entry, dict)]
        lines.append("")
        lines.append(f"{tables.table_name(TASK, many=True)}:")
        lines.append(rendered(TASK, slices) if slices else tr("table.word.empty"))
    return OK, "\n".join(lines), row


def card(table: str, row: dict) -> dict:
    """ONE row as a card a surface draws — the fields the table declares as its
    `columns`, and nothing else.

    It is the person's own rule (20/10/2026): the card is the table's MAIN
    fields, and which ones those are is the DECLARATION's to say, never the
    surface's — `schema.columns` is the very list a listing shows, so the card
    and the grid agree about what a table's main fields are.

    The ID travels beside the fields because a card is a door: the surface
    links to the record's page with it (`views.ts`'s `openRef`), the same way
    the row's own title does. Every value is written the way the engine writes
    one (`text_of`) — the closed vocabulary's word, the reference's title — so
    the card shows what the listing shows and never a raw number.

    It is the CARD's shape, not the record's (`at.prose.payload.record`): a
    full record carries every declared field, `raw` values, references and the
    editor's own facts. A chat answer has no editor — what it needs is the row
    as a person reads it.
    """
    return {
        "table": table,
        "entity": tables.table_name(table),
        "id": row.get("id"),
        "shown_id": tables.format_id(table, row["id"]) if "id" in row else "",
        "title": tables.title(table, row),
        "fields": [
            {
                "name": name,
                "label": tables.label(table, name),
                "value": tables.text_of(table, name, row.get(name)),
            }
            for name in tables.columns(table)
            if schema.field(table, name)
        ],
    }


def _table_rows(table: str, rows: list[dict]) -> tuple[list[str], list[list[str]]]:
    """The header and the cells, the id then the columns the table declares —
    the shape both `rendered` (the `cli`'s ASCII) and a surface that draws an
    actual table (the WebApp's chat, TASK-?) read, each in its own words."""
    header = [tr("table.field.id")] + [tables.label(table, name) for name in tables.columns(table)]
    cells = [
        [tables.format_id(table, row["id"])]
        + [tables.text_of(table, name, row.get(name)) for name in tables.columns(table)]
        for row in rows
    ]
    return header, cells


def rendered(table: str, rows: list[dict]) -> str:
    """The listing: the id, then the columns the table declares.

    The drawing is `ui/words.table`'s and not this file's: the deploy's status
    is the same kind of thing — a header and cells — and two renderers would be
    two sets of widths that part company the first time a title grows.
    """
    header, cells = _table_rows(table, rows)
    return words.table([header, *cells])
