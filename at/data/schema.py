"""The table declarations — `data/schema/<table>.json`.

One file per table. It says what the table is (`id`), where its rows live
(`store`), the field a person reads as a row's title (`primary`), the position it
takes in the panel (`order`), and the fields it declares.

**It carries no text a person reads.** A label here is a key of `i18n`, never
the words themselves (§4) — so a translation changes nothing in the
declaration, and the declaration changes nothing in a translation.

The schema is DECLARATION, and it ships with the product; the rows are the
instance's. That split is why the id counter does not live here (it counts what
happened in one folder) — the store keeps it.

Two doors write a declaration, and they are told apart by what they do to one
that is already there: `seed` lays down the whole file where it is ABSENT, and
`extend` grows one that exists, key by key, without ever overwriting what a
person put there (§3, migration).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path

from at.core import files, paths

SCHEMA_DIR = "schema"
BUNDLED = "defaults"
SUFFIX = ".json"


def directory() -> Path:
    """Where the declarations of THIS folder live."""
    return paths.data_dir() / SCHEMA_DIR


@dataclass(frozen=True)
class Extended:
    """What one additive write to a declaration found, and what it did.

    `state` is `written` when the declaration was there to grow, `missing` when
    the folder does not carry it and `unreadable` when it is there and does not
    parse. The last two are told apart on purpose: one is a file that is not
    there, the other is a file AT must not touch, and a report that blurred
    them would say the wrong thing about somebody's folder.

    `added` and `collisions` are dotted paths inside the declaration —
    `fields.since.type`, `columns`, `lifecycle` — and they are paths because a
    name is what a person opens the file to find. `added` is what was written;
    `collisions` is where the folder already carried something ELSE, and the
    folder's value is the one that stays.
    """

    table: str
    added: tuple[str, ...] = ()
    collisions: tuple[str, ...] = ()
    state: str = "written"


def extend(table: str, additions: dict) -> Extended:
    """Grow the folder's declaration of `table` by `additions` — never
    overwriting it.

    The additions are written the way the DECLARATION writes itself — a `fields`
    entry, the `enum` of a closed vocabulary, a `columns` entry, the `type` a
    field was born without — and they are merged in recursively:

    - a key the folder does not carry is added whole, subtree and all;
    - a dict meets a dict and the merge goes deeper;
    - a list gains the entries it is missing, in the order they were declared,
      and keeps the ones it has where they are;
    - anything else already there with another value is a COLLISION, and the
      person's edit wins: the path goes back in `collisions` to be said out
      loud, never resolved here (§3, migration).

    Only a write that ADDS something rewrites the file, and it is the atomic
    write (§3). A declaration that already carries everything is left exactly as
    it is, bytes included — the common case for a folder that migrated late, and
    reformatting the file of somebody who did not need migrating would be AT
    editing what it was only supposed to read.

    A declaration the person deleted is NOT recreated, and one that does not
    parse is NOT replaced: both come back in `state`, and neither is touched.
    The first is a deletion that was meant — `seed` makes the same promise for
    the whole file — and the second is a file that exists, whose rewrite would
    destroy whatever the person put there (`files.read_json`).
    """
    target = directory() / f"{table}{SUFFIX}"
    if not target.is_file():
        return Extended(table, state="missing")
    try:
        declared = files.read_json(target, default=None)
    except (OSError, json.JSONDecodeError):
        return Extended(table, state="unreadable")
    if not isinstance(declared, dict):
        # JSON that parses and is not an object is not a declaration either, and
        # it is read as the file it is: present, and not something to rewrite.
        return Extended(table, state="unreadable")

    added: list[str] = []
    collisions: list[str] = []
    _grow(declared, additions, "", added, collisions)
    if added:
        body = json.dumps(declared, ensure_ascii=False, indent=2) + "\n"
        files.atomic_write_text(target, body)
        # The registry was filled before the write, and whoever extends and then
        # reads — the migration — would be told the table declares what it did
        # before. `seed` resets for the same reason.
        reset()
    return Extended(table, tuple(added), tuple(collisions))


def _grow(declared: dict, additions: dict, where: str, added: list, collisions: list) -> None:
    """Merge `additions` into `declared`, in place, recording every path.

    `where` is the dotted path of `declared` inside the table's declaration —
    empty at the root — and it is what makes the report name the place a person
    has to open.
    """
    for key, value in additions.items():
        path = f"{where}.{key}" if where else key
        if key not in declared:
            declared[key] = value
            added.append(path)
            continue
        mine = declared[key]
        if isinstance(mine, dict) and isinstance(value, dict):
            _grow(mine, value, path, added, collisions)
        elif isinstance(mine, list) and isinstance(value, list):
            fresh = [item for item in value if item not in mine]
            if fresh:
                mine.extend(fresh)
                added.append(path)
        elif mine != value:
            collisions.append(path)


def bundled() -> dict[str, dict]:
    """The declarations that ship with the product.

    §4 makes the schema DECLARATION: it is published, and the rows are the
    instance's. So the product carries the system tables inside it, and the first
    run writes them into the folder — "a pasta `./data` é criada automaticamente
    na primeira execução, com as tabelas de sistema vigentes" (§4). After that
    the folder's copy is the one that counts, because a person may edit it.
    """
    found: dict[str, dict] = {}
    root = resources.files(__name__) / BUNDLED
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if not entry.name.endswith(SUFFIX):
            continue
        try:
            declared = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(declared, dict):
            found[str(declared.get("id") or entry.name[: -len(SUFFIX)])] = declared
    return found


def seed(where: Path, only: tuple[str, ...] | None = None) -> list[str]:
    """Write the bundled declarations into `where`, the ones that are absent.

    Only the absent ones: a declaration a person edited is theirs, and the
    product overwriting it on the next run would be the opposite of a file a
    person can own. A system table that was deleted is not silently recreated
    either — "not deletable" belongs to the door that would delete it, not to a
    repair that happens behind the person's back.

    `only` is that promise at work, and the migration is why it exists: a release
    that introduces a table names the tables IT introduces, and never the whole
    directory — a migration that seeded everything would bring back, on the first
    start after the swap, the declaration somebody deleted on purpose.
    """
    written: list[str] = []
    for table, declared in bundled().items():
        if only is not None and table not in only:
            continue
        target = where / f"{table}{SUFFIX}"
        if target.exists():
            continue
        body = json.dumps(declared, ensure_ascii=False, indent=2) + "\n"
        files.atomic_write_text(target, body)
        written.append(table)
    if written:
        # A table that was just born is a table the registry has to learn: the
        # cache above was filled before the file existed, and whoever seeds and
        # then writes — the first run, and the migration — would be told the
        # table declares no field.
        reset()
    return written


@lru_cache(maxsize=None)
def tables() -> dict[str, dict]:
    """Every declared table, keyed by its machine word.

    A malformed declaration is skipped rather than fatal: one broken file must
    not take the whole registry down and leave every surface blank.
    """
    found: dict[str, dict] = {}
    root = directory()
    if not root.is_dir():
        return found
    for entry in sorted(root.glob(f"*{SUFFIX}")):
        try:
            declared = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(declared, dict):
            continue
        table = declared.get("id") or entry.stem
        found[str(table)] = declared
    return found


def of(table: str) -> dict | None:
    return tables().get(table)


def declared() -> list[dict]:
    """Every table, in the panel order the schema declares.

    The order is a declaration, never the alphabet the filesystem happens to
    list — `order` is what the panel follows, and a table without one goes last,
    by name.
    """
    return sorted(
        tables().values(),
        key=lambda declared: (declared.get("order", 1000), declared.get("id", "")),
    )


def store_path(table: str) -> Path | None:
    """Where the table's rows live, relative to the Working Folder.

    The declaration names the folder by its INTERNAL name — `data/tasks.jsonl` —
    and the resolution happens HERE, never in the declaration (§3). A folder
    that changes its name changes a path, and the declaration is published while
    the name on disk is the instance's: writing the localized name into it would
    put one folder's language into every other folder's copy.

    A first segment that is not an internal name is taken as it is written, so a
    table of the instance's own can still point anywhere it likes.
    """
    declared = of(table)
    relative = declared.get("store") if declared else None
    if not isinstance(relative, str) or not relative:
        return None
    head, _, tail = relative.partition("/")
    root = paths.folder(head) if head in paths.NAMES else paths.working_folder() / head
    return root / tail if tail else root


def name_key(table: str, many: bool = False) -> str | None:
    """The i18n key of the table's own name — one home for the convention, so
    the help, the panel and the header all read the same key."""
    declared = of(table)
    names = declared.get("name") if declared else None
    if not isinstance(names, dict):
        return None
    key = names.get("many" if many else "one")
    return key if isinstance(key, str) else None


def columns(table: str) -> list[str]:
    """The fields a listing shows, in the order the table declares them.

    Which columns a list carries is a property of the table (§4, "campos padrão
    na exibição"), not a choice of whoever wrote the surface — that is what makes
    the CLI and the WebApp show the same thing.
    """
    declared = of(table)
    value = declared.get("columns") if declared else None
    if not isinstance(value, list):
        return []
    return [name for name in value if isinstance(name, str)]


def primary(table: str) -> str | None:
    declared = of(table)
    value = declared.get("primary") if declared else None
    return value if isinstance(value, str) and value else None


def field(table: str, name: str) -> dict:
    """The declaration of one field; `{}` for a field nobody declared.

    An undeclared field is not an error: a store written by an older version may
    carry a key the schema no longer names, and the engine renders it as it is.
    """
    declared = of(table)
    fields = declared.get("fields") if declared else None
    if not isinstance(fields, dict):
        return {}
    value = fields.get(name)
    return value if isinstance(value, dict) else {}


def reset() -> None:
    """Drop the cache — for tests, and for a table created while AT runs."""
    tables.cache_clear()
