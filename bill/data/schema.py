"""The table declarations — `data/schema/<table>.json`.

One file per table. It says what the table is (`id`), where its rows live
(`store`), the field a person reads as a row's title (`primary`), the position it
takes in the panel (`order`), and the fields it declares.

**It carries no text a person reads.** A label here is a key of `i18n`, never
the words themselves (README §4) — so a translation changes nothing in the
declaration, and the declaration changes nothing in a translation.

The schema is DECLARATION, and it ships with the product; the rows are the
instance's. That split is why the id counter does not live here (it counts what
happened in one folder) — the store keeps it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

from bill.core import files, paths

SCHEMA_DIR = "schema"
BUNDLED = "defaults"
SUFFIX = ".json"


def directory() -> Path:
    """Where the declarations of THIS folder live."""
    return paths.data_dir() / SCHEMA_DIR


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


def seed(where: Path) -> list[str]:
    """Write the bundled declarations into `where`, the ones that are absent.

    Only the absent ones: a declaration a person edited is theirs, and the
    product overwriting it on the next run would be the opposite of a file a
    person can own. A system table that was deleted is not silently recreated
    either — "not deletable" belongs to the door that would delete it, not to a
    repair that happens behind the person's back.
    """
    written: list[str] = []
    for table, declared in bundled().items():
        target = where / f"{table}{SUFFIX}"
        if target.exists():
            continue
        body = json.dumps(declared, ensure_ascii=False, indent=2) + "\n"
        files.atomic_write_text(target, body)
        written.append(table)
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
    """Where the table's rows live, relative to the Working Folder."""
    declared = of(table)
    relative = declared.get("store") if declared else None
    if not isinstance(relative, str) or not relative:
        return None
    return paths.working_folder() / relative


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
    """Drop the cache — for tests, and for a table created while Bill runs."""
    tables.cache_clear()
