"""The shared vocabulary of the migrations: the stamp, the answers, and the
shape of one step.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from at.core import (
    files,
    paths,
)

# The stamp, inside the instance folder: the ids this folder has already run.
STAMP = "migrations"


# Both spellings answer the same question — the language of the prompt is the
# active one, and whoever answers is free to type either.
YES = frozenset({"s", "sim", "y", "yes"})


Ask = Callable[[str], str]


Report = tuple[str, dict]


def is_yes(answer: str) -> bool:
    return answer.strip().lower() in YES


@dataclass(frozen=True)
class Migration:
    ident: int
    step: Callable[[Ask | None], list[Report]]


def stamp_file() -> Path:
    return paths.instance_dir() / STAMP


def applied() -> list[int]:
    """The ids this folder has already run, in order. A stamp nobody can read
    reads as none: the migrations that follow would then simply run again, and
    each one is written to leave alone what is already right."""
    try:
        raw = files.read_json(stamp_file(), default=[])
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    return sorted({value for value in raw if isinstance(value, int) and not isinstance(value, bool)})


def _mark(ident: int) -> None:
    done = applied()
    if ident in done:
        return
    done.append(ident)
    body = json.dumps(sorted(done), ensure_ascii=False) + "\n"
    files.atomic_write_text(stamp_file(), body)
