"""The prose layer: the files that are not structured data (§4).

Everything that is not a table row lives under `prose/`, and this module is the
one place that says what a file there IS and what may be done to it. The read
door and the write door ask the SAME questions (`is_text`, the ceiling) — two
rules for one question drift, and the drift shows up as a file the page can read
and cannot save.

**The tree is rooted at the prose folder** — `Arquivos/` in `pt_BR`, `Files/` in
`en_US`, and `paths.prose_dir()` is what knows which — and not at the Working
Folder: the tables' folder is the table engine's and the instance folder is the
configuration's, and neither is "files a person keeps". What the PoC walked was
its whole sandbox, which had no such split to make.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from at.core import files, paths, versioning

# The ceiling, in bytes, for a file a person edits in the page. It binds the
# reader and the writer alike: a file over it is not text anybody edits here.
MAX_FILE_BYTES = 256 * 1024

BUCKETS = ("code", "text", "data", "other")
BUCKET_EXT = {".py": "code", ".md": "text", ".json": "data", ".jsonl": "data"}

# The first hit wins, and the NAME is asked before the extension: a `Dockerfile`
# has no suffix at all, and `.env` is a name rather than a kind of file.
KIND_NAME = {
    "dockerfile": "dockerfile", "containerfile": "dockerfile",
    "makefile": "shell", "caddyfile": "other",
    ".zshrc": "shell", ".zprofile": "shell", ".bashrc": "shell", ".profile": "shell",
}
KIND_EXT = {
    ".md": "markdown", ".markdown": "markdown", ".txt": "text",
    ".py": "python", ".pyi": "python",
    ".js": "text", ".mjs": "text", ".ts": "text", ".vue": "text",
    ".json": "json", ".jsonl": "json", ".ndjson": "json",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "yaml", ".ini": "yaml",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "shell",
    ".css": "text", ".html": "text", ".sql": "text",
}
SHEBANG = (
    ("python", "python"), ("node", "text"), ("deno", "text"),
    ("bash", "shell"), ("zsh", "shell"), ("sh", "shell"), ("fish", "shell"),
)

# ONE writer at a time: the read, the compare and the write are one move, and two
# of them interleaved is a lost edit.
_LOCK = threading.Lock()


def root() -> Path:
    return paths.prose_dir()


def is_text(data: bytes) -> bool:
    """Whether a person may edit this in a page.

    A NUL byte in the head is what a binary looks like from here — the same
    question the writer asks, so a file the reader shows is a file the writer
    takes.
    """
    return len(data) <= MAX_FILE_BYTES and b"\0" not in data[:4096]


def bucket(rel: str) -> str:
    return BUCKET_EXT.get(Path(rel).suffix.lower(), "other")


def kind(rel: str, data: bytes) -> str:
    """What the file IS, for the icon and the word beside it.

    Layered, and the FIRST hit wins: the name, then the suffix, then the first
    line, then the fallback. `file(1)` is not consulted — it is a tool on the
    machine, and the look of a list is not worth a dependency (§3).
    """
    name = Path(rel).name.lower()
    if name in KIND_NAME:
        return KIND_NAME[name]
    if name.startswith(".env"):
        return "text"
    suffix = Path(name).suffix.lower()
    if suffix in KIND_EXT:
        return KIND_EXT[suffix]
    found = _by_first_line(data)
    if found:
        return found
    return "text" if is_text(data) else "binary"


def _by_first_line(data: bytes) -> str | None:
    head = data[:512]
    if not head.startswith(b"#!"):
        return None
    first = head.split(b"\n", 1)[0].decode("utf-8", "replace").lower()
    return next((word for needle, word in SHEBANG if needle in first), None)


def inside(rel: str) -> Path | None:
    """The path `rel` names inside `prose/`, or None when it escapes it.

    Nothing a caller sends is JOINED as a path: a segment that is `..`, or that
    starts with a dot, or an absolute name, is refused before the disk is
    touched. This is the whole of the read and the write permission.
    """
    if not rel or rel.startswith("/") or "\\" in rel:
        return None
    parts = [part for part in rel.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." or part.startswith(".") for part in parts):
        return None
    return root().joinpath(*parts)


def servable(rel: str) -> bool:
    where = inside(rel)
    return where is not None and where.is_file()


def listed() -> list[str]:
    """Every file of `prose/`, as POSIX paths relative to it, in name order.

    A hidden segment is skipped at every level — a file a person has to know the
    exact name of is not one a tree offers.
    """
    base = root()
    if not base.is_dir():
        return []
    out: list[str] = []
    for entry in sorted(base.rglob("*")):
        if not entry.is_file():
            continue
        relative = entry.relative_to(base)
        if any(part.startswith(".") for part in relative.parts):
            continue
        out.append(relative.as_posix())
    return out


def digest(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def read(rel: str) -> dict | None:
    """One file as the page reads it, or None when it is not one it may read."""
    where = inside(rel)
    if where is None or not where.is_file():
        return None
    data = where.read_bytes()
    payable = is_text(data)
    return {
        "path": rel,
        "bucket": bucket(rel),
        "kind": kind(rel, data),
        # The page owns no rule of the write: whether it may is the SERVER's.
        "writable": payable,
        "rev": digest(data),
        "text": data.decode("utf-8", "replace") if payable else None,
        "reason": None if payable else "prose.not_text",
    }


def write(rel: str, text: str, base: str) -> tuple[int, dict]:
    """Write `text` over `rel`, if the disk still holds the `base` the page read.

    The whole point is the ORDER: the size and the kind are asked before the
    lock, and the read, the compare and the write happen inside it — so a save
    from another tab cannot land between the compare and the write and lose an
    edit nobody saw.
    """
    where = inside(rel)
    if where is None or not where.is_file():
        return 404, {"error": "prose.not_served"}
    if not text:
        # An empty write is how a buffer that failed to load saves itself over a
        # file — it is never what somebody meant.
        return 400, {"error": "prose.empty_write"}
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        return 413, {"error": "prose.too_large"}

    with _LOCK:
        try:
            if where.stat().st_size > MAX_FILE_BYTES:
                return 413, {"error": "prose.too_large"}
            current = where.read_bytes()
        except OSError:
            return 404, {"error": "prose.not_served"}
        if not is_text(current):
            return 403, {"error": "prose.not_writable"}
        revision = digest(current)
        if base and revision != base:
            # The answer carries the revision the disk now holds, so the page can
            # show what happened instead of overwriting it.
            return 409, {"error": "prose.changed_on_disk", "rev": revision}
        try:
            files.atomic_write_text(where, text)
        except files.ReadOnly as refused:
            return 403, {"error": "prose.read_only", "where": str(refused.where)}
        except OSError as error:
            return 500, {"error": str(error)}
        # The revision is read BACK from the disk, never computed from what was
        # sent: what the page must compare against next time is the file.
        answer = {"path": rel, "rev": digest(where.read_bytes())}

    # The version, and OUTSIDE the lock: saving a document is one of the actions
    # that change the folder (§4, item 30), and no other writer of this file
    # should wait on a subprocess for it. The name is the path — what whoever
    # reads `git log` would look for.
    versioning.commit_file(rel)
    return 200, answer
