"""The prose layer: the files that are not structured data (§4).

Everything that is not a table row lives under `prose/`, and this module is the
one place that says what a file there IS and what may be done to it. The read
door and the write door ask the SAME question about the KIND (`is_text`: a NUL
byte in the head is what a binary looks like from here) — two rules for one
question drift, and the drift shows up as a file the page can read and cannot
save.

Their CEILINGS are two, and they are not the same: `MAX_FILE_BYTES` is the
door of the EDIT and `MAX_OPEN_BYTES` is the door of the OPEN. A markdown of
300 KB is text that OPENS (readable, not editable), and a file above
`MAX_OPEN_BYTES` does not open in the browser at all — the page says it hit the
limit and offers the download. One ceiling for both was what made a 0,54 MB
note answer "not supported".

**The tree is rooted at the prose folder** — `Arquivos/` in `pt_BR`, `Files/` in
`en_US`, and `paths.prose_dir()` is what knows which — and not at the Working
Folder: the tables' folder is the table engine's and the instance folder is the
configuration's, and neither is "files a person keeps". What the PoC walked was
its whole sandbox, which had no such split to make.
"""

from __future__ import annotations

import hashlib
import shutil
import threading
from pathlib import Path

from at.core import files, paths, versioning

# The ceiling, in bytes, for a file a person edits in the page: above it the
# write door is closed, and it binds the reader too — a file over it opens for
# READING and not for writing.
MAX_FILE_BYTES = 256 * 1024

# The ceiling, in bytes, for a file the page OPENS. It is the rule MAIOR: a
# file above it does not open in the browser at all — `read` answers
# `prose.over_limit` and the page offers the download.
MAX_OPEN_BYTES = 10 * 1024 * 1024

# How much of a file is read to DECIDE what it is. The whole file is never
# read to answer "is it text" — a 1,47 GB `.txt` is a text file, and reading
# it to find out would be the very thing this fatia is about.
HEAD_BYTES = 64 * 1024

# The nine an image VIEWER already knows how to draw (TASK-167) — an image is
# drawn by the page, inside it.
IMAGE_EXT = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".avif",
)
# The formats a browser PLAYS BY ITSELF — the video and the PDF the page opens
# in a NEW TAB (the browser draws them, AT does not). Only what the browser
# really plays: a `.mkv` or a `.wmv` is a download, not a player that fails.
VIDEO_EXT = (".mp4", ".webm", ".ogv", ".ogg", ".mov")
PDF_EXT = (".pdf",)
# What the page OPENS in a new tab, and what it draws as it is.
TAB_EXT = PDF_EXT + VIDEO_EXT

# What the page may DO with a file — the closed set the answer carries, so
# the page never invents a rule of extension of its own.
OPEN_TEXT = "text"
OPEN_IMAGE = "image"
OPEN_TAB = "tab"
OPEN_DOWNLOAD = "download"

BUCKET_EXT = {
    ".py": "code", ".md": "text", ".json": "data", ".jsonl": "data",
    **{ext: "image" for ext in IMAGE_EXT},
}

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
    **{ext: "image" for ext in IMAGE_EXT},
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
    """Whether these bytes are TEXT.

    A NUL byte in the head is what a binary looks like from here — the same
    question the writer asks, so a file the reader shows is a file the writer
    takes.

    **The SIZE is not part of this question.** The ceiling of the EDIT is
    `MAX_FILE_BYTES` and the ceiling of the OPEN is `MAX_OPEN_BYTES`, and they
    are two doors: a markdown of 300 KB is text that opens (and is not text
    anybody edits here). A rule that mixed the two answered "not supported" to
    a note of half a megabyte.
    """
    return b"\0" not in data[:4096]


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


def digest_of(where: Path) -> str:
    """The revision of a file, read in BLOCKS — the digest is of every byte,
    but no byte of the file is ever in memory all at once.
    """
    hasher = hashlib.sha1()
    with where.open("rb") as handle:
        for block in iter(lambda: handle.read(64 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read(rel: str) -> dict | None:
    """One file as the page reads it, or None when it is not one it may read.

    **What the file IS is asked of a HEAD** (`HEAD_BYTES`), never of the whole
    file: a 1,47 GB `.txt` is a text file, and reading it whole to find out
    would be the very thing this fatia is about. The whole file is read only
    when it is TEXT and it fits in `MAX_OPEN_BYTES` — and then it is read
    because the page is going to show it.

    **The answer carries WHAT TO DO with it** (`open`): the page does not
    invent a rule of extension of its own. A PDF and a video the browser plays
    open in a NEW TAB (`"tab"`), an image opens inline (`"image"`), a text
    opens as text (`"text"`), and everything else is a download (`"download"`).
    """
    where = inside(rel)
    if where is None or not where.is_file():
        return None
    try:
        size = where.stat().st_size
        with where.open("rb") as handle:
            head = handle.read(HEAD_BYTES)
    except OSError:
        return None
    file_kind = kind(rel, head)
    suffix = Path(rel).suffix.lower()
    # THE RULE MAIOR: above `MAX_OPEN_BYTES` the file does not open in the
    # browser AT ALL. Nothing of it is read — the answer says it hit the
    # limit, and the page offers the download.
    if size > MAX_OPEN_BYTES:
        return {
            "path": rel,
            "bucket": bucket(rel),
            "kind": file_kind,
            # Nothing is written to a file the page cannot open.
            "writable": False,
            # No revision: the bytes were not read, and a revision of bytes
            # nobody read would be a lie. A file that is not writable is not
            # compared against anything.
            "rev": "",
            "text": None,
            "reason": "prose.over_limit",
            "open": OPEN_DOWNLOAD,
        }
    if file_kind == "image":
        # An IMAGE is viewed, never edited (TASK-167) — and it opens inline.
        open_as = OPEN_IMAGE
    elif suffix in TAB_EXT:
        # The browser draws a PDF and plays a video BY ITSELF — AT opens the
        # door and keeps out of the way.
        open_as = OPEN_TAB
    elif is_text(head):
        open_as = OPEN_TEXT
    else:
        open_as = OPEN_DOWNLOAD
    text = None
    if open_as == OPEN_TEXT:
        data = where.read_bytes()
        text = data.decode("utf-8", "replace")
        revision = digest(data)
    else:
        revision = digest_of(where)
    return {
        "path": rel,
        "bucket": bucket(rel),
        "kind": file_kind,
        # The page owns no rule of the write: whether it may is the SERVER's.
        # The EDIT has its own ceiling — a text that opens and is too big to
        # save opens all the same, and what is not text is not written here.
        "writable": open_as == OPEN_TEXT and size <= MAX_FILE_BYTES,
        "rev": revision,
        "text": text,
        "reason": None if open_as != OPEN_DOWNLOAD else "prose.not_supported",
        "open": open_as,
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


def create(rel: str, is_dir: bool) -> tuple[int, dict]:
    """A new, empty file or folder at `rel` (TASK-120, fatia 5/7).

    Creating is never an overwrite — that is what `write` is for — so a name
    already taken is refused rather than clobbered.
    """
    where = inside(rel)
    if where is None:
        return 400, {"error": "prose.invalid_name"}
    with _LOCK:
        if where.exists():
            return 409, {"error": "prose.exists"}
        try:
            if is_dir:
                files.guard(where)
                where.mkdir(parents=True)
                files.mark_write()
            else:
                files.atomic_write_text(where, "")
        except files.ReadOnly as refused:
            return 403, {"error": "prose.read_only", "where": str(refused.where)}
        except OSError as error:
            return 500, {"error": str(error)}
    versioning.commit_created(rel)
    return 200, {"path": rel}


def rename(rel: str, new_rel: str) -> tuple[int, dict]:
    """`rel` under a new name or place, as long as `new_rel` is free.

    Both ends walk `inside`: a rename is still a write inside `prose/`, never
    a door to move something out of it or in from outside it.
    """
    where = inside(rel)
    dest = inside(new_rel)
    if where is None or dest is None:
        return 400, {"error": "prose.invalid_name"}
    with _LOCK:
        if not where.exists():
            return 404, {"error": "prose.not_served"}
        if dest.exists():
            return 409, {"error": "prose.exists"}
        try:
            files.guard(where)
            dest.parent.mkdir(parents=True, exist_ok=True)
            where.rename(dest)
            files.mark_write()
        except files.ReadOnly as refused:
            return 403, {"error": "prose.read_only", "where": str(refused.where)}
        except OSError as error:
            return 500, {"error": str(error)}
    versioning.commit_renamed(rel, new_rel)
    return 200, {"path": new_rel}


def delete(rel: str) -> tuple[int, dict]:
    """`rel` removed — the whole folder, with what is inside it, when it is one.
    """
    where = inside(rel)
    if where is None:
        return 400, {"error": "prose.invalid_name"}
    with _LOCK:
        if not where.exists():
            return 404, {"error": "prose.not_served"}
        try:
            files.guard(where)
            if where.is_dir():
                shutil.rmtree(where)
            else:
                where.unlink()
            files.mark_write()
        except files.ReadOnly as refused:
            return 403, {"error": "prose.read_only", "where": str(refused.where)}
        except OSError as error:
            return 500, {"error": str(error)}
    versioning.commit_deleted(rel)
    return 200, {"path": rel}
