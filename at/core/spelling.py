"""The spelling-checker's motor: ask the service, get findings — or "unavailable".

`spelling-checker` is the canonical service (§4, §7d); LanguageTool is who
fulfils it today. AT spawns it as a process of its own (`services/
spelling_checker.py`) when the WebApp comes up and stops it when the WebApp
goes down. This module is the other half: the small, testable question.

    spelling.available()            -> bool
    spelling.check(text, language)  -> list[Finding] | None

**`None` is "unavailable", and `[]` is "checked, nothing found".** They are
different answers and a caller that writes `if not found:` has merged them.
Unavailable never raises and never takes anything down: a service that is not
up, or that stops answering, is a service the caller goes on without.

Nothing here reaches past the loopback: the address is `127.0.0.1` and the port
is the one the lifecycle remembered in `App/services/spelling-checker/port`.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from at.core import files, paths

FOLDER = "spelling-checker"
PORT = "port"
LOOPBACK = "127.0.0.1"
TIMEOUT = 10.0


@dataclass(frozen=True)
class Finding:
    """One thing the checker found. `offset` and `length` are in Python
    characters of the text that was asked (not in UTF-16 units)."""

    offset: int
    length: int
    rule: str
    suggestions: tuple[str, ...]
    category: str = ""
    issue_type: str = ""
    message: str = ""


def port_file() -> Path:
    return paths.service_dir(FOLDER) / PORT


def remember(port: int) -> None:
    """Called by the lifecycle once the process is spawned."""
    port_file().parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(port_file(), f"{port}\n")


def forget() -> None:
    """Called by the lifecycle when the process goes down."""
    port_file().unlink(missing_ok=True)


def port() -> int | None:
    try:
        return int(port_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def available() -> bool:
    """Whether something answers on the remembered port right now."""
    found = port()
    if found is None:
        return False
    try:
        with socket.create_connection((LOOPBACK, found), timeout=1):
            return True
    except OSError:
        return False


def language_code(language: str) -> str:
    """AT's `pt_BR` / `en_US` in LanguageTool's `pt-BR` / `en-US`."""
    return language.replace("_", "-")


def check(text: str, language: str) -> list[Finding] | None:
    """The checker's findings for `text`, or `None` when it is unavailable."""
    found = port()
    if found is None:
        return None
    body = urllib.parse.urlencode(
        {"text": text, "language": language_code(language)}
    ).encode("utf-8")
    request = urllib.request.Request(f"http://{LOOPBACK}:{found}/v2/check", data=body)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
            data = json.load(reply)
        return _findings(text, data["matches"])
    except urllib.error.HTTPError as error:
        error.close()
        return None
    except (OSError, ValueError, KeyError, TypeError):
        # URLError, timeouts, refused connections, a half-up server, bad JSON.
        return None


def _findings(text: str, matches: list[dict]) -> list[Finding]:
    units = _utf16_to_index(text)
    out: list[Finding] = []
    for match in matches:
        start = units(match["offset"])
        end = units(match["offset"] + match["length"])
        rule = match.get("rule", {})
        out.append(Finding(
            offset=start,
            length=end - start,
            rule=str(rule.get("id", "")),
            suggestions=tuple(str(r["value"]) for r in match.get("replacements", [])),
            category=str(rule.get("category", {}).get("id", "")),
            issue_type=str(rule.get("issueType", "")),
            message=str(match.get("message", "")),
        ))
    return out


def _utf16_to_index(text: str):
    """LanguageTool counts Java chars (UTF-16 units); Python counts code points."""
    if all(ord(c) < 0x10000 for c in text):
        return lambda unit: unit
    table: list[int] = []
    for index, char in enumerate(text):
        table.extend([index] * (2 if ord(char) >= 0x10000 else 1))
    table.append(len(text))
    return lambda unit: table[min(unit, len(table) - 1)]


def utf16_units(text: str, index: int) -> int:
    """The inverse of the table above: a code-point `index` of `text` in the
    UTF-16 units a browser's string indexes (`slice`, `selectionStart`) count."""
    return len(text[:index].encode("utf-16-le")) // 2
