"""Migrations eleven to seventeen: secrets, audits, jobs, the backlog order,
the scanner and the tags.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

from at.core import (
    paths,
    tables,
)
from at.core.migrations_base import Ask, Report
from at.core.migrations_engine import _extend, _hand_over
from at.data import schema, store

# The table THIS release introduces — what migration eleven names — and the
# permissions it answers. Both lists are explicit for the reason `INTRODUCED` is
# one: a published migration is never edited, so the next release that brings a
# system table brings its own step and its own names.
#
# The two permissions are the table's OWN and not the engine's six: `secret`
# declares `read` and `edit` in its declaration (`permissions.DECLARED`), so its
# listing is `secret:read` and its write is `secret:edit`. A role born before
# this swap carries neither — it was built from the catalogue of its own day —
# and the administrator's is the one that must, exactly as migrations seven and
# eight handed over theirs.
SECRETS = ("secret",)


SECRET_PERMISSIONS = ("secret:read", "secret:edit")


def _secrets(ask: Ask | None) -> list[Report]:
    """Migration eleven: the `secret` table, and the ceiling over it.

    A folder that already exists is the one this is for: the table that carries
    what AT USES has to arrive in it before anything can be sealed, and the
    declaration is written the way migration six writes one — only where it is
    ABSENT, so a `secret.json` a person edited stays theirs and a deletion stays
    a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`) — and the box the rows live in, `data/secrets.jsonl`, is born
    when the first secret is sealed and not here: an empty file that names
    nothing is a store a person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=SECRETS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(SECRET_PERMISSIONS)


# The table THIS release introduces — what migration twelve names — and the one
# permission it answers. Both lists are explicit for the reason `SECRETS` is: a
# published migration is never edited, so the next release that brings a system
# table brings its own step and its own names.
#
# The permission is the table's OWN and not one of the engine's six: `audit`
# declares `read` alone, so its listing and its record are `audit:read` and a
# creation, an edition and a deletion are not permissions it has. A role born
# before this swap carries none of it — it was built from the catalogue of its
# own day — and the administrator's is the one that must, exactly as migrations
# seven, eight and eleven handed over theirs.
AUDITS = ("audit",)


AUDIT_PERMISSIONS = ("audit:read",)


def _audits(ask: Ask | None) -> list[Report]:
    """Migration twelve: the `audit` table, and the ceiling over it.

    A folder that already exists is the one this is for: §3 makes every act that
    enters the core one line of a table that has to BE there when the first act
    arrives, and the declaration is written the way migration eleven writes one —
    only where it is ABSENT, so an `audit.json` a person edited stays theirs and
    a deletion stays a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`). The box the lines live in, `data/audits.jsonl`, is born with
    the first act and not here — an empty file that names nothing is a store a
    person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=AUDITS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(AUDIT_PERMISSIONS)


# What THIS release adds to a declaration that is ALREADY on disk — migration
# thirteen, and the same shape migration nine writes: the additions are written
# the way a declaration writes itself, so the merge never has to be told which
# kind of key it is holding.
#
# The addition is the field the audit line grew (§3, §4, item 15): the threshold
# that was in force when a demand ran. The line is born with it — a folder born
# by this release has it in `data/defaults/audit.json` — and a folder that is
# already here catches up on the first start after the swap, which is what makes
# the first act after an update carry the same line as every act after it.
AUDIT_THRESHOLD: dict[str, dict] = {
    "audit": {
        "fields": {
            "threshold": {
                "label": "table.audit.field.threshold",
                "filterable": True,
                "searchable": True,
            }
        }
    },
}


def _audit_threshold(ask: Ask | None) -> list[Report]:
    """Migration thirteen: the threshold the audit line carries.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration). Rows written before it carry no
    threshold and are read as they are stored — the field is not `required`, and
    a log that pretended an old line had one would be a log inventing history.
    """
    return _extend(AUDIT_THRESHOLD)


# The table THIS release introduces — what migration fourteen names — and the
# permissions it answers. Both lists are explicit for the reason `AUDITS` is: a
# published migration is never edited, so the next release that brings a system
# table brings its own step and its own names.
#
# The permissions are the object's OWN and not the engine's six: `job` answers a
# read, a run and the two halves of the approval, and `permissions.NARROWED`
# says so — a creation, an edition and a deletion are not permissions it has. A
# role born before this swap carries none of them, and the administrator's is
# the one that must, exactly as migrations seven, eight, eleven and twelve
# handed over theirs.
#
# **`job:approve` and `job:refuse` reach the administrator and no machine**, and
# that is the same reason §3 gives for `audit:read`: whoever can release a
# demand learns where the bar is, and an `agent` that could release its own
# waiting demand would have opened the door it was held behind.
JOBS = ("job",)


JOB_PERMISSIONS = ("job:read", "job:run", "job:approve", "job:refuse")


def _jobs(ask: Ask | None) -> list[Report]:
    """Migration fourteen: the `job` table, and the ceiling over it.

    A folder that already exists is the one this is for: the table that holds
    the demand that could not run has to BE there when the first demand waits,
    and the declaration is written the way migration twelve writes one — only
    where it is ABSENT, so a `job.json` a person edited stays theirs and a
    deletion stays a deletion that was meant.

    It does not ask: a declaration of the product's own, and the role is AT's
    (`_hand_over`). The box the jobs live in, `data/jobs.jsonl`, is born with
    the first demand that waits and not here — an empty file that names nothing
    is a store a person would read as a table that exists elsewhere.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=JOBS)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    return report + _hand_over(JOB_PERMISSIONS)


# What THIS release adds to declarations that are ALREADY on disk — migration
# fifteen. It is the backlog moving into the tables, read off the declaration:
# the `project` gains the `priority` the queue is ordered by, the `planned`
# status that says "decided and not started", and the default order §4 names
# beside the default fields; the `task` gains the `project` column, which is
# what lets the listing say which item a slice belongs to.
#
# It is written the way migration nine writes one, and for the same reason: the
# additions are spelled as a declaration spells them, so the merge never has to
# be told which kind of key it is holding. `planned` lands at the END of the
# folder's `enum` and not where the bundled declaration puts it — the merge
# only ever ADDS, and a key inserted in the middle would be an edit to the
# person's file. The order the picker lists them in is cosmetic; the closed set
# is the same one either way.
BACKLOG: dict[str, dict] = {
    "project": {
        "columns": ["priority"],
        "sort": {"by": "priority", "direction": "desc", "then": "id"},
        "fields": {
            "priority": {
                "label": "table.project.field.priority",
                "filterable": True,
                "searchable": True,
                "enum": {
                    "low": "table.project.field.priority.low",
                    "medium": "table.project.field.priority.medium",
                    "high": "table.project.field.priority.high",
                    "critical": "table.project.field.priority.critical",
                },
                "default": "medium",
            },
            "status": {
                "enum": {"planned": "table.project.field.status.planned"},
                "show": ["planned"],
            },
        },
    },
    "task": {"columns": ["project"]},
}


def _fill_missing(table: str, field: str) -> list[str]:
    """As linhas que já existiam ganham o valor que a declaração dá ao campo novo.

    O motor JÁ lê um campo ausente como o padrão declarado quando ordena — é o
    que `tables._sort_key` faz —, e esta escrita põe na linha o mesmo valor que
    a leitura vinha supondo. O que se ganha é não haver duas verdades: a
    listagem mostra o que a ordem usa, em vez de uma coluna vazia ao lado de uma
    ordem que já decidiu.

    Nada é sobrescrito. Só a linha que NÃO tem o campo o recebe, e a que a pessoa
    já escreveu fica com o que ela escreveu — uma linha sem `priority` não é uma
    decisão, é uma linha mais velha que o campo. É o outro lado da regra de
    sempre: a migração acrescenta o que falta, e diz o que acrescentou.
    """
    default = schema.field(table, field).get("default")
    if default is None or schema.of(table) is None:
        return []
    filled: list[str] = []
    for row in store.load(table):
        if row.get(field) is not None:
            continue
        number = store.number_of(row)
        if number is None:
            continue
        tables.edit(table, number, {field: default})
        filled.append(tables.format_id(table, number))
    return filled


def _backlog_order(ask: Ask | None) -> list[Report]:
    """Migration fifteen: the fields the backlog needs to be a queue.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration). The rows it writes are the `priority`
    those projects never had the chance to carry — the very value the order was
    already reading off the declaration for them.
    """
    report = _extend(BACKLOG)
    filled = _fill_missing("project", "priority")
    if filled:
        report.append(("boot.migration.backlog.filled", {"names": ", ".join(filled)}))
    return report


# The permission THIS release grows the catalogue by — what migration sixteen
# grants. It is the act the `secret` declares of its OWN (item 51,
# `permissions.NARROWED`): the word reads the folder and says what it found, and
# a role born before this swap carries none of it — it was built from the
# catalogue of its own day —, exactly as migrations seven, eight, eleven, twelve
# and fourteen handed over theirs.
#
# It is the administrator's and nobody else's for now, and that is the same
# answer §3 gives for `audit:read`: the ceiling is written once, and the screens
# that move it (item 11) are the ones that hand it to another role.
SCANNER_PERMISSIONS = ("secret:scan",)


def _scanner(ask: Ask | None) -> list[Report]:
    """Migration sixteen: `secret scan`, and the ceiling over it.

    A folder that already exists is the one this is for: the word that says what
    the folder carries is the administrator's, and the row it wears was written
    from the catalogue of the day it was born — which did not name the act.

    It does not ask: the row is AT's own, and the change only ever ADDS
    (`_hand_over`). Nothing else about the folder changes — the act writes no row
    and needs no declaration of its own, and the `gitleaks` it calls is the
    person's machine's business and not the folder's.
    """
    return _hand_over(SCANNER_PERMISSIONS)


# What THIS release adds to a declaration that is ALREADY on disk — migration
# seventeen, and the same shape migrations nine and fifteen write: the additions
# are spelled as a declaration spells them, so the merge never has to be told
# which kind of key it is holding.
#
# The backlog stops being a project or a subproject and becomes a QUEUE OF TAGS:
# the tag is the FATIA, and the fatia is the set of tasks that carry the same
# one. The `task` gains the `tags` list and the column the listing shows it in.
# It is not `editable`: who writes a tag is the backlog session, and not the
# screen a person types into.
TAGS: dict[str, dict] = {
    "task": {
        "columns": ["tags"],
        "fields": {
            "tags": {
                "label": "table.task.field.tags",
                "type": "list",
                "filterable": True,
                "searchable": True,
                "default": [],
            }
        },
    },
}


def _tags(ask: Ask | None) -> list[Report]:
    """Migration seventeen: a task carries the tag the backlog is sliced by.

    It does not ask: a declaration of the product's own, and nothing outside the
    folder points at it (§3, migration).

    **No row is filled, and that is the decision — `_fill_missing` is NOT called
    here.** The default is an empty list, and a row without the field already
    READS as empty: the listing joins the list it finds, an absent field joins
    nothing, and both read as `—`. Writing `[]` into every task would be a
    migration rewriting the whole file to say what the read already says, and
    there is no second truth to settle — unlike `priority`, which the order was
    already reading off the declaration.
    """
    return _extend(TAGS)
