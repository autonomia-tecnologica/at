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

A `list` narrowed by a filter carries the rows the filter kept. `webapp` does not
wait for the end: `{"ok", "code", "message", "url"}` leaves the moment the server
announces its address, and the run says nothing more unless it fails. Without any
word the command opens the Control Panel, as it does without the flag.

The text is captured from stdout while the word runs, so a prompt typed through
`input` lands in `message` too; the no-echo readers write to the terminal and do
not.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from collections.abc import Callable

from at.prose import payload
from at.ui import ask as door

FLAG = "--json"

# What the word being run handed over beside its text (`attach`); `None` outside
# a `--json` run, so the plain run pays nothing for it.
_extra: dict | None = None
# The real standard output, kept while the captured one is in place.
_real = None


def attach(key: str, value: object) -> None:
    """A structured fact the running word knows — kept only under `--json`."""
    if _extra is not None and value is not None:
        _extra[key] = value


def run(words: list[str], dispatch: Callable[[list[str]], int]) -> int:
    """Run `dispatch(words)` and print its outcome as one JSON object."""
    global _extra, _real, _announced
    if not words:
        # The wordless command opens the Control Panel, which has nothing to say
        # as data: it behaves as the `cli` without `--json`.
        return dispatch(words)
    serves = words[0] == "webapp"
    _extra = {}
    _announced = False
    _real = sys.stdout
    out = io.StringIO()
    if serves:
        # The server runs until it is stopped, so its object cannot wait for the
        # end: it leaves the moment the address is announced (`_started`).
        from at.ui.webapp import app

        app.on_serving.append(_started)
    try:
        with contextlib.redirect_stdout(out):
            code = dispatch(words)
        extra = _extra
    finally:
        _extra = None
        if serves:
            app.on_serving.remove(_started)
        started, _real = _announced, None
    message = out.getvalue().rstrip("\n")
    if serves and started and code == 0:
        # Served and stopped by the person: the start was already said.
        return code
    return _say(code, message, _structured(words, code, extra))


_announced = False


def _started(url: str, line: str) -> None:
    """The webapp is up: say so NOW, on the real standard output, and keep serving."""
    global _announced
    _announced = True
    _say(0, line, {"url": url}, to=_real)


def _say(code: int, message: str, extra: dict, to=None) -> int:
    body = {"ok": code == 0, "code": code, "message": message, **extra}
    print(json.dumps(body, ensure_ascii=False), file=to, flush=True)
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
    elif code == 0 and "table" in extra and action == "list" and door.last_rows is not None:
        # The rows are the ones the listing KEPT, filter included: the shape is the
        # page's, the selection is the listing's own.
        found["table"] = payload.table_payload(
            table, show_all="--all" in words, rows=door.last_rows
        )
    if words[:2] == ["secret", "scan"] and door.last_scan is not None:
        found["findings"] = [
            {"rule": f.rule, "where": f.where, "line": f.line, "commit": f.commit}
            for f in door.last_scan.findings
        ]
    return found
