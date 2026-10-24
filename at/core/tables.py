"""The table engine — what a row is, and what may be done to one.

Six actions: `list`, `view`, `create`, `edit`, `cancel`, `delete`. They are the
same six the CLI dispatches and the WebApp calls, because there is one engine and
the surfaces are only ways of reaching it (§4).

`cancel` CLOSES WITH HISTORY — the row stays, the status becomes the terminal one
and the reason goes where the table keeps its story — and every part of that comes
from the `lifecycle` the table declares. A table that declares none says so
instead of inventing a closing. `delete` takes the row out and refuses while
anything NAMES it; what names a row is read off the declarations (`ref`), never
off a scan of the folder. And a table may declare that NO row of its own is
erased (`deletable`), which is the one refusal that comes before the row is
looked for — the `audit` is that table (§4).

What this module knows lives in the declaration, never in a list of names: the
fields, their types, their closed vocabularies, their ceilings, their defaults,
their references and their lifecycle all come from `data/schema/<table>.json`. Add
a table and nothing here changes.
"""

from __future__ import annotations

# The engine is split by responsibility into the flat `tables_*` modules; this one
# is the door every caller already knows, and re-exports the whole of it (the
# private names too: the suites reach `_hashed`, `_touch`, `_require`, ...).
from at.core.tables_base import (  # noqa: F401
    _DAY_SHAPE,
    _INSTANT_SHAPE,
    _WHEN,
    ACTIONS,
    LISTED_KEYS,
    OPAQUE,
    READS,
    WRITES,
    TableError,
    _checked,
    _message,
    _refuse_unlisted_keys,
    columns,
    enum_label,
    enum_values,
    format_id,
    hashed,
    label,
    number_of,
    opaque,
    raw_of,
    sealed,
    table_name,
    title,
    utc,
    verify,
    word,
)
from at.core.tables_close import (  # noqa: F401
    _names,
    _reason_field,
    _terminal_field,
    _write_reason,
    cancel,
    deletable,
    delete,
    lifecycle,
    referrers,
)
from at.core.tables_display import (  # noqa: F401
    _LOCALE,
    _as_day,
    _as_instant,
    _item,
    _locale_writer,
    _reference_text,
    _title_of_reference,
    text_of,
)
from at.core.tables_rows import _sort_key, find, ordered, rows, sort_spec  # noqa: F401
from at.core.tables_types import (  # noqa: F401
    _day,
    _hashed,
    _instant,
    _reference_value,
    _scalar,
    _sealed,
    _value,
)
from at.core.tables_write import (  # noqa: F401
    _coerce,
    _in_declared_order,
    _literal,
    _log_status,
    _require,
    _required,
    _stamp,
    _touch,
    create,
    edit,
)
