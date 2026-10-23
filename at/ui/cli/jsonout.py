"""`--json`: the same run, said as data (TASK-131).

The flag is GLOBAL and it changes only what is PRINTED: `main` takes it out of
the words, in any position, and the dispatch runs exactly as it always did —
same prompts, same side effects, same exit codes (`0` ok · `1` refused · `2`
usage). What reaches stdout is ONE JSON object, UTF-8:

    {"ok": code == 0, "code": code, "message": "<the text it would have printed>"}

plus what the word knows as structure:

- a table's `list` carries `table` (the WebApp's `table_payload`) and a `view`
  or a write carries `record` (the WebApp's `record`) — the shape is
  `at.prose.payload`'s, the page's own, and not a second one;
- `version` carries `version`; `secret scan` carries `findings`.

The text is captured from stdout while the word runs, so a prompt typed through
`input` lands in `message` too; the no-echo readers write to the terminal and do
not.
"""

from __future__ import annotations

import contextlib
import io
import json
from collections.abc import Callable

from at.i18n import tr
from at.prose import payload
from at.ui import ask as door
from at.ui.ask import USAGE

FLAG = "--json"

# What the word being run handed over beside its text (`attach`); `None` outside
# a `--json` run, so the plain run pays nothing for it.
_extra: dict | None = None


def attach(key: str, value: object) -> None:
    """A structured fact the running word knows — kept only under `--json`."""
    if _extra is not None and value is not None:
        _extra[key] = value


def run(words: list[str], dispatch: Callable[[list[str]], int]) -> int:
    """Run `dispatch(words)` and print its outcome as one JSON object."""
    global _extra
    if not words:
        # The wordless command opens a browser: there is nothing to say as data.
        return _say(USAGE, tr("cli.error.usage"), {})
    _extra = {}
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = dispatch(words)
        extra = _extra
    finally:
        _extra = None
    return _say(code, out.getvalue().rstrip("\n"), _structured(words, code, extra))


def _say(code: int, message: str, extra: dict) -> int:
    body = {"ok": code == 0, "code": code, "message": message, **extra}
    print(json.dumps(body, ensure_ascii=False))
    return code


def _structured(words: list[str], code: int, extra: dict) -> dict:
    """What the word handed over, turned into the page's own shapes."""
    found: dict = {}
    if "version" in extra:
        found["version"] = extra["version"]
    table = words[0]
    action = words[1] if len(words) > 1 else "list"
    if "row" in extra:
        found["record"] = payload.record(table, extra["row"])
    elif code == 0 and "table" in extra and action == "list" and set(words[2:]) <= {"--all"}:
        # A listing narrowed by `--project` is the engine's own filter, which the
        # page's payload does not carry — it keeps the text and no table.
        found["table"] = payload.table_payload(table, show_all="--all" in words)
    if words[:2] == ["secret", "scan"] and door.last_scan is not None:
        found["findings"] = [
            {"rule": f.rule, "where": f.where, "line": f.line, "commit": f.commit}
            for f in door.last_scan.findings
        ]
    return found
