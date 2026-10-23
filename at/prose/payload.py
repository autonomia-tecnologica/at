"""The table's payload — the shape a table travels in, for every surface that says it as data.

It lives here, and not in the WebApp, because two doors read the SAME shape: the
page draws it and `at-cli --json` prints it. A second spelling would be a second
format; and a module the `cli` imported from `ui/webapp` would make the terminal
depend on the server. Nothing in here knows a surface: it reads the schema, the
store and the engine, and answers dicts.
"""

from __future__ import annotations

from at import i18n
from at.core import permissions, tables
from at.data import schema, store


def declared_fields(table: str) -> dict:
    declared = schema.of(table) or {}
    declared = declared.get("fields")
    return declared if isinstance(declared, dict) else {}


def label_key(table: str, name: str) -> str | None:
    key = schema.field(table, name).get("label")
    return key if isinstance(key, str) else None


def field_payload(table: str, name: str, field: dict) -> dict:
    """One field of the schema, as the page reads it.

    `labels` carries EVERY language, not the active one: the page switches
    language without asking again, and the words stay the server's (§3).
    """
    key = label_key(table, name)
    refs = field.get("ref") or []
    choices = field.get("enum") if isinstance(field.get("enum"), dict) else {}
    return {
        "name": name,
        "labels": i18n.labels(key) if key else None,
        # The closed vocabulary, each value already written out in every
        # language: the picker draws the word, and the write sends the VALUE.
        "enum": {
            value: (i18n.labels(choices[value]) if isinstance(choices.get(value), str) else None)
            for value in choices
        },
        "type": field.get("type"),
        "primary": schema.primary(table) == name,
        "filterable": bool(field.get("filterable")),
        "searchable": bool(field.get("searchable")),
        "narrow": bool(field.get("narrow")),
        "editable": bool(field.get("editable")),
        "required": bool(field.get("required")),
        "max_length": field.get("max_length"),
        "hide": field.get("hide") or [],
        "refs": [
            {"key": target,
             "labels": i18n.labels(schema.name_key(target, many=True)) if schema.name_key(target) else None}
            for target in refs
        ],
    }


def references(table: str, name: str, row: dict) -> list[dict]:
    """The references the VALUE carries, so a cell can draw a link to the thing
    it names instead of to the word — the page never parses an id."""
    field = schema.field(table, name)
    targets = field.get("ref") or []
    value = row.get(name)
    if not targets or value is None:
        return []

    def one(target: str, number: object) -> dict | None:
        found = store.find(target, number) if isinstance(number, int) else None
        if found is None:
            return None
        title = tables.title(target, found)
        return {"key": target, "id": number, "title": title, "shown": title}

    if isinstance(value, list):
        # A field that may point at more than one table stores the PAIR
        # (`["project", 3]`); a list field stores the bare numbers.
        if len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
            return [entry for entry in (one(value[0], value[1]),) if entry]
        return [entry for item in value if (entry := one(targets[0], item))]
    return [entry for entry in (one(targets[0], value),) if entry]


def schema_payload(table: str) -> list[dict]:
    """The table's declared fields, as the page reads them."""
    return [
        field_payload(table, name, field)
        for name, field in declared_fields(table).items()
        if isinstance(field, dict)
    ]


def stored(table: str, name: str, value: object) -> object:
    """The stored value a form starts from — and NOTHING for the field the engine
    does not hand over.

    It asks the ENGINE which fields those are (`tables.opaque`) and not a list of
    types of its own: a credential is only ever compared and a sealed value is
    only ever opened with the key, and the page carries neither — a cell draws
    the mask and a form asks for a new credential. Any other field is handed over
    as it is stored, and the engine's own door is what says so (`raw_of`).
    """
    if tables.opaque(table, name) is not None:
        return None
    return tables.raw_of(table, name, value)


def record(table: str, row: dict) -> dict:
    number = store.number_of(row)
    fields = declared_fields(table)
    return {
        "id": number,
        **says(table, row),
        "shown_id": tables.format_id(table, number) if number is not None else "",
        "title": tables.title(table, row),
        "fields": [
            {
                "name": name,
                "type": field.get("type"),
                # The value as a person reads it; `raw` as it is stored, so a
                # field that is going to be edited starts from the truth — and
                # the hashed field is handed over by nobody, so a credential
                # never reaches the wire (`stored`).
                "value": tables.format_id(table, number) if name == "id"
                         and number is not None
                         else tables.text_of(table, name, row.get(name)),
                "raw": stored(table, name, row.get(name)),
                "refs": references(table, name, row),
            }
            for name, field in fields.items()
            if isinstance(field, dict)
        ],
    }


def says(table: str, row: dict) -> dict:
    """What the row has to be TOLD, over what the fields already say (§4, item 11).

    Two facts of the two system tables do not fit the generic shape, and both are
    read by the screen that shows them:

    - a `role` that names a permission the catalogue does not have **does not take
      AT down**: it says so, and the saying is what gets read. What the record
      carries is the NAMES the catalogue does not know, so the screen lists them —
      a write that dropped them silently, or kept them silently, would be the
      screen deciding what §4 left to the person;
    - an `actor`'s credential is a derivation that NEVER leaves its row, so the
      payload cannot tell "there is one" from "there is none" by its value (the
      cell draws the mask either way, and `stored` hands over nothing). What the
      screen that mints and revokes needs is exactly that boolean, and the engine
      is the one that knows it.

    Anything else carries the generic shape and nothing more.
    """
    if table == "role":
        return {
            "unknown": [
                name
                for name in permissions.carried(row)
                if not permissions.is_known(name)
            ]
        }
    if table == "actor":
        return {"has_credential": bool(row.get("credential"))}
    return {}


def table_payload(table: str, show_all: bool, rows: list[dict] | None = None) -> dict:
    """`rows` is a listing already narrowed (`--project`, a filter); left out, the table's own."""
    chosen = tables.rows(table, show_all=show_all) if rows is None else rows
    return {
        "key": table,
        "name": tables.table_name(table, many=True),
        "filter": None,
        "fields": schema_payload(table),
        # WHICH COLUMNS A LISTING CARRIES IS THE TABLE'S, not whoever wrote the
        # page (§4, "campos padrão na exibição"): the rest steps aside into the
        # pill, where the person can bring it back.
        "columns": schema.columns(table),
        "records": [record(table, row) for row in chosen],
    }
