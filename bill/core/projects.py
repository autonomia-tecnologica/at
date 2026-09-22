"""The project scope: which tasks belong to a project, and which to none.

**A task names its project, and that is the only direction.** The PoC also kept a
`tasks` list on the project and read BOTH — and two lists that have to agree are
two lists that drift. This side of the port keeps the link where it is written
and derives everything else, so there is nothing to keep in step.

A project is a SCOPE, not a table of its own: the panel shows the tree, a project
opens a page, and the page carries the tasks of the whole subtree — each row
saying which subproject it came from, which is what the `project` field means
there.

**A project the listing does not show does not claim its tasks.** The table
declares which statuses a listing carries (`show`); a task pointing at a project
outside that set falls to the "no project" node, which is honest — its project is
not on screen either.
"""

from __future__ import annotations

from bill.core import tables
from bill.data import schema, store
from bill.i18n import tr

PROJECT = "project"
TASK = "task"


def available() -> bool:
    """Whether the panel can draw the projects branch at all — a branch with no
    table to open is a dead end, and is not offered."""
    return schema.of(PROJECT) is not None and schema.of(TASK) is not None


def _rows(table: str) -> dict[int, dict]:
    return {
        number: row
        for row in store.load(table)
        if (number := store.number_of(row)) is not None
    }


def shown_projects() -> dict[int, dict]:
    """The projects a listing carries.

    `tables.rows` is the slice the table declares (`show`), and it is the SAME
    slice the CLI's `list` obeys — one rule, so the panel and the prompt cannot
    disagree about which projects exist.
    """
    if schema.of(PROJECT) is None:
        return {}
    return {
        number: row
        for row in tables.rows(PROJECT)
        if (number := store.number_of(row)) is not None
    }


def project_of(row: dict) -> int | None:
    """The project a task names, as a number — None when it names none."""
    value = row.get("project")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
        return value[1]
    return None


def _children(projects: dict[int, dict]) -> dict[int, list[int]]:
    """project number → its DIRECT children, each list in numeric order."""
    kids: dict[int, list[int]] = {}
    for number, row in projects.items():
        parent = row.get("parent")
        if isinstance(parent, int) and not isinstance(parent, bool) and parent in projects:
            kids.setdefault(parent, []).append(number)
    for numbers in kids.values():
        numbers.sort()
    return kids


def _subtree(projects: dict[int, dict], root: int) -> list[int]:
    """The project and everything under it, parent before child, siblings in
    numeric order — the order the page reads them in."""
    kids = _children(projects)
    out: list[int] = []
    queue = [root]
    while queue:
        number = queue.pop(0)
        if number in out:
            continue  # a cycle in `parent` would otherwise never end
        out.append(number)
        queue.extend(kids.get(number, ()))
    return out


def _tasks_by_owner(projects: dict[int, dict]) -> dict[int, int]:
    """task number → the project that owns it, for the tasks a shown project
    claims."""
    owners: dict[int, int] = {}
    if schema.of(TASK) is None:
        return owners
    for number, row in _rows(TASK).items():
        owner = project_of(row)
        if owner is not None and owner in projects:
            owners[number] = owner
    return owners


def orphans() -> list[dict]:
    """The tasks no shown project claims, in the store's order."""
    if schema.of(TASK) is None:
        return []
    claimed = set(_tasks_by_owner(shown_projects()))
    return [
        row for number, row in _rows(TASK).items() if number not in claimed
    ]


def tree() -> list[dict]:
    """The panel's branch: one line per project, and the "no project" node last.

    A parent the listing does not show makes the node read as top-level, rather
    than pointing at a line nobody can see — the same rule the tasks follow.
    """
    projects = shown_projects()
    counts = _counts(projects)
    lines = [
        {
            "id": number,
            "title": tables.title(PROJECT, row),
            "status": tables.text_of(PROJECT, "status", row.get("status")),
            "parent": row.get("parent") if row.get("parent") in projects else None,
            "tasks": counts.get(number, 0),
        }
        for number, row in projects.items()
    ]
    unclaimed = orphans()
    if unclaimed:
        lines.append({
            "id": None,
            "title": tr("webapp.no_project"),
            "status": "",
            "parent": None,
            "tasks": len(unclaimed),
            "orphans": True,
        })
    return lines


def _counts(projects: dict[int, dict]) -> dict[int, int]:
    """How many tasks each project names DIRECTLY — the count the panel prints.

    Direct, not the subtree: the line is the project, and the number says how
    much of the day is under that name. What the subtree holds is what the PAGE
    is for.
    """
    counts: dict[int, int] = {}
    for owner in _tasks_by_owner(projects).values():
        counts[owner] = counts.get(owner, 0) + 1
    return counts


def page(number: int) -> dict | None:
    """One project's page: where it sits, what is inside it, and the tasks of
    the whole subtree."""
    projects = shown_projects()
    if number not in projects and schema.of(PROJECT) is None:
        return None
    all_projects = _rows(PROJECT)
    if number not in all_projects:
        return None

    scope = _subtree(all_projects, number)
    owners = _tasks_by_owner(all_projects)
    tasks = _rows(TASK)
    listed = [
        {**tasks[task], "project": owners[task]}
        for task in owners
        if task in tasks and owners[task] in scope
    ]
    listed.sort(key=lambda row: row.get("id") if isinstance(row.get("id"), int) else 0)

    parent = all_projects[number].get("parent")
    parent = parent if isinstance(parent, int) and parent in projects else None
    kids = _children(all_projects).get(number, [])

    return {
        "id": number,
        "title": tables.title(PROJECT, all_projects[number]),
        "status": tables.text_of(PROJECT, "status", all_projects[number].get("status")),
        "parent": {"id": parent, "title": tables.title(PROJECT, projects[parent])}
        if parent is not None else None,
        "children": [
            {
                "id": child,
                "title": tables.title(PROJECT, all_projects[child]),
                "status": tables.text_of(PROJECT, "status", all_projects[child].get("status")),
                "tasks": _counts(all_projects).get(child, 0),
            }
            for child in kids
        ],
        # The rows, not the payload: whoever serves this one knows how a row is
        # spelled on the wire, and `core` does not.
        "rows": listed,
    }
