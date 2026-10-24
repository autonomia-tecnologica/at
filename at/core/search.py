"""The global search — one question asked of the files and of the tables (B-21).

It scans AT THE MOMENT it is asked, with no index to keep fresh and none to go
stale: the Working Folder is small enough to walk, and a result that is the
folder's own state is worth more than a fast one that might be last minute's.

Two places are searched, and each says what it reads:

- `Arquivos/` — the NAME of every file, and the CONTENT of the ones that are
  TEXT (the same question the editor asks, `prose.listing.is_text`). A file above
  `MAX_CONTENT_BYTES` is found by its name only: reading a gigabyte to find a word
  is the very thing a live search must not do.
- the tables — the fields that declare `searchable: true`, and only those. A
  `hashed` or `sealed` field never answers, whatever it declares: its value does
  not come out of the engine (§4), and a search would be a way around that.

A hit is a dict, the same shape for every surface (the `cli` prints it, the
page's overlay will draw it):

    {"kind": "file" | "row", "where": <path or table>, "id": <path or row id>,
     "field": <"name" | "content" | the field's name>, "line": <int or None>,
     "snippet": <the text around the match>}

The match is a substring, case-insensitive. Nothing here writes.
"""

from __future__ import annotations

from at.core import tables
from at.data import schema, store
from at.prose import listing

# The ceiling, in bytes, for the CONTENT of one file: above it the file is
# searched by name only (B-21, decided by the person).
MAX_CONTENT_BYTES = 1024 * 1024

# What a hit may be, and the two field names a FILE hit carries.
FILE = "file"
ROW = "row"
NAME = "name"
CONTENT = "content"

# The characters kept on each side of a match in a snippet.
CONTEXT = 40


def snippet(text: str, at: int, length: int) -> str:
    """`text` around the match at `at`, flattened to one line and trimmed."""
    start = max(0, at - CONTEXT)
    end = min(len(text), at + length + CONTEXT)
    piece = " ".join(text[start:end].split())
    return ("…" if start > 0 else "") + piece + ("…" if end < len(text) else "")


def _hit(kind: str, where: str, ident: object, field: str, text: str,
         at: int, length: int, line: int | None = None) -> dict:
    return {"kind": kind, "where": where, "id": ident, "field": field,
            "line": line, "snippet": snippet(text, at, length)}


def files(term: str, limit: int | None = None) -> list[dict]:
    """The files of `Arquivos/` whose name or text holds `term`."""
    needle = term.casefold()
    found: list[dict] = []
    for rel in listing.listed():
        if limit is not None and len(found) >= limit:
            break
        at = rel.casefold().find(needle)
        if at >= 0:
            found.append(_hit(FILE, rel, rel, NAME, rel, at, len(needle)))
        for line, text, column in _lines(rel, needle):
            if limit is not None and len(found) >= limit:
                break
            found.append(_hit(FILE, rel, rel, CONTENT, text, column, len(needle), line))
    return found


def _lines(rel: str, needle: str) -> list[tuple[int, str, int]]:
    """(line number, line, column) of each line of a TEXT file that holds `needle`."""
    where = listing.inside(rel)
    if where is None:
        return []
    try:
        if where.stat().st_size > MAX_CONTENT_BYTES:
            return []
        data = where.read_bytes()
    except OSError:
        return []
    if not listing.is_text(data) or listing.kind(rel, data) == "image":
        return []
    out: list[tuple[int, str, int]] = []
    for number, text in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
        column = text.casefold().find(needle)
        if column >= 0:
            out.append((number, text, column))
    return out


def searchable(table: str) -> list[str]:
    """The fields of `table` that answer a search, in declaration order."""
    fields = (schema.of(table) or {}).get("fields")
    if not isinstance(fields, dict):
        return []
    return [
        name for name, declared in fields.items()
        if isinstance(declared, dict) and declared.get("searchable")
        and tables.opaque(table, name) is None
    ]


def rows(term: str, limit: int | None = None) -> list[dict]:
    """The rows, of every table, whose `searchable` fields hold `term`."""
    needle = term.casefold()
    found: list[dict] = []
    for declared in schema.declared():
        table = str(declared["id"])
        names = searchable(table)
        if not names:
            continue
        for row in tables.rows(table, show_all=True):
            for name in names:
                value = row.get(name)
                if value is None or isinstance(value, (dict, list)):
                    continue
                text = str(value)
                at = text.casefold().find(needle)
                if at < 0:
                    continue
                if limit is not None and len(found) >= limit:
                    return found
                number = store.number_of(row)
                ident = tables.format_id(table, number) if number is not None else None
                found.append(_hit(ROW, table, ident, name, text, at, len(needle)))
    return found


def search(term: str, limit: int | None = None) -> list[dict]:
    """Everything that holds `term`: the files first, then the rows.

    An empty term finds nothing — it would match every byte there is.
    """
    term = term.strip()
    if not term:
        return []
    found = files(term, limit)
    if limit is None:
        return found + rows(term)
    return found + rows(term, max(0, limit - len(found)))
