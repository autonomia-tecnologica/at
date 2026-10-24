"""The look and the doors that serve it: the payload paths, the content types,
the theme registry and the hosted typefaces.

Moved out of `app.py` (B-6) without a change of behaviour. Nothing here knows
the `Handler` or the server: it reads the disk next to this module and the
environment's `AT_THEME`, and answers paths and text. `app.py` imports the names
back, so `app.theme_rows` and friends keep answering the same.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote

DEFAULT_THEME = "at"

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
THEMES = ASSETS / "themes"
ICONS = ASSETS / "icons"
VENDOR = HERE / "vendor"
UI_DIR = HERE / "dist"
UI_ASSETS = UI_DIR / "assets"

_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    # The nine `prose.IMAGE_EXT` names (TASK-167) — the bytes route
    # (`_get_file_bytes`) reads this the same way `_file` already does for
    # every static asset.
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".ico": "image/vnd.microsoft.icon",
    ".avif": "image/avif",
    # The formats the browser DRAWS BY ITSELF (the `tab` door): a PDF it
    # renders, a video it plays. They leave as what they are, or the browser
    # downloads them instead of showing them.
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".ogv": "video/ogg",
    ".ogg": "video/ogg",
    ".mov": "video/quicktime",
}


# What the Vault's clear may go out as a DOCUMENT — opened straight in a tab,
# and not only inside an `<img>` this very page already trusts. **It is a
# deliberate SUBSET of `_CONTENT_TYPES`, and the exclusion is the defence**:
# the Vault holds whatever the PERSON dropped in there, never what this
# product wrote, and a file's name proves nothing about what its bytes
# carry. `.svg` is XML and may carry `<script>` — it is OUT here despite
# being an image, because "is it an image" is not the right question; the
# question is "does the browser run something when this opens as a
# document", and the answer for SVG is yes. `.html`, `.js`, `.css` never
# entered. Whatever `_STRONGBOX_INLINE_TYPES` does not name leaves as
# `application/octet-stream` (`_strongbox_content`) — the browser downloads
# instead of opening, and no extension's name can talk it out of that.
_STRONGBOX_INLINE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".ico": "image/vnd.microsoft.icon",
    ".avif": "image/avif",
    ".pdf": "application/pdf",
}


def _strongbox_content(name: str) -> tuple[str, str]:
    """The Content-Type and the Content-Disposition for `name`, the original
    name (with the `.enc` gone) — never read off the extension the `.enc`
    itself carried, because the person wrote it, not this product.

    What `_STRONGBOX_INLINE_TYPES` recognises opens `inline`: the browser
    draws the image or the PDF exactly as it would one opened from anywhere
    else. Everything else is `attachment` over `application/octet-stream` —
    which is the decision and not a forgotten default: an `.html` or `.svg`
    name that opened as what its name says would be a document running in
    THIS origin, with the person's own session inside it. `quote` carries
    the accented name whole in `filename*` (RFC 6266), and the plain
    `filename` copy carries only what ASCII has, for the browser that does
    not read the first.
    """
    ctype = _STRONGBOX_INLINE_TYPES.get(Path(name).suffix.lower())
    kind = "inline" if ctype else "attachment"
    ascii_name = name.encode("ascii", "replace").decode("ascii")
    disposition = (f'{kind}; filename="{ascii_name}"; '
                    f"filename*=UTF-8''{quote(name)}")
    return ctype or "application/octet-stream", disposition


# ------------------------------------------------------------------ look ---

def theme_rows() -> list[dict]:
    """The theme registry — which themes exist, and which side each wears."""
    where = ASSETS / "themes.jsonl"
    if not where.is_file():
        return []
    rows: list[dict] = []
    for line in where.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            rows.append(row)
    return rows


def active_theme(requested: str | None) -> dict | None:
    """The theme the page wears: the asked one, the machine's, the default, and
    then the first declared — never an error."""
    rows = theme_rows()
    for candidate in (requested, os.environ.get("AT_THEME"), DEFAULT_THEME):
        if not candidate:
            continue
        for row in rows:
            if row.get("id") == candidate:
                return row
    return rows[0] if rows else None


def theme_css(requested: str | None, dark: bool) -> str | None:
    """The stylesheet of the active theme; the OTHER side answers when the
    asked one does not exist. Only `at` ships both — every other theme in the
    registry kept the one side it wore by default and dropped its mirror
    (2026-10-04) — so a theme with one file answers the same CSS whichever
    way `dark` reads: it carries no choice for the page to get wrong."""
    row = active_theme(requested)
    if row is None:
        return None
    ident = str(row.get("id"))
    sides = [f"{ident}-dark.css", f"{ident}.css"] if dark else [f"{ident}.css", f"{ident}-dark.css"]
    for name in sides:
        where = THEMES / name
        if where.is_file():
            return where.read_text(encoding="utf-8")
    return None


def theme_sides(ident: str) -> list[str]:
    """Which files a theme actually has — never hand-declared (the old
    `"side"` field drifted from the files it described), always read off
    disk. Only `at` answers both: every other theme in the registry kept
    the one side it wore by default (2026-10-04) and the picker in Settings
    reads this to know whether there is a choice to offer at all."""
    sides = []
    if (THEMES / f"{ident}.css").is_file():
        sides.append("light")
    if (THEMES / f"{ident}-dark.css").is_file():
        sides.append("dark")
    return sides


def base_css_path(requested: str | None) -> Path:
    """Which base the active theme wears. A theme MAY declare one by name
    (`"base"` in the registry row) — a door every row in the registry leaves
    unused today, since `base-shared.css` was retired on 2026-10-03 and every
    theme now walks `base.css`, `at`'s own from-scratch design system and the
    server's default. The name is a bare filename or the door is refused: no
    separator survives to become a path."""
    row = active_theme(requested)
    name = row.get("base") if row and isinstance(row.get("base"), str) else None
    if name and "/" not in name and "\\" not in name and name.endswith(".css"):
        candidate = ASSETS / name
        if candidate.is_file():
            return candidate
    return ASSETS / "base.css"


def theme_label(row: dict) -> str:
    from at.i18n import active_code

    labels = row.get("labels")
    if isinstance(labels, dict):
        return str(labels.get(active_code()) or labels.get("en_US") or row.get("id"))
    return str(row.get("id"))


# ------------------------------------------------------------- the doors ---

def served(directory: Path, name: str) -> Path | None:
    """A file of `directory` resolved by BARE NAME, or None.

    Nothing the caller sends is ever joined as a path: a name carrying a
    separator, or naming the directory itself, is refused before the disk is
    touched. That is the whole reason every file route takes one segment.
    """
    if not name or name.startswith(".") or "/" in name or "\\" in name:
        return None
    where = directory / name
    return where if where.is_file() else None


def hosted(key: str) -> tuple[Path, str] | None:
    """A hosted dependency by its key, with the hash the manifest pinned.

    The manifest is the pin: it names the package, the version and the sha256 of
    every file, so what leaves here can be checked against what was installed
    (§3, Dependência externa).

    The key is the file's NAME and never a path — the same rule the font door
    keeps —, and the file's extension is the one the vendor's own `upstream`
    carries (`.woff2` for the typefaces, `.js` for the renderer `lib/markdown`
    waits for): it is what tells the content type apart without the key spelling
    a second extension the URL would then have to carry.
    """
    if not key or key.startswith(".") or "/" in key or "\\" in key:
        return None
    manifest = VENDOR / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        rows = json.loads(manifest.read_text(encoding="utf-8")).get("files", {})
    except (OSError, json.JSONDecodeError):
        return None
    entry = rows.get(key)
    if not isinstance(entry, dict):
        return None
    upstream = entry.get("upstream")
    suffix = Path(upstream).suffix if isinstance(upstream, str) else ""
    if not suffix:
        return None
    where = VENDOR / f"{key}{suffix}"
    if not where.is_file():
        return None
    if _pinned(key, where) != entry.get("sha256"):
        return None
    return where, str(entry.get("version", ""))


_PINNED: dict[str, str] = {}


def _pinned(key: str, where: Path) -> str:
    """The file's digest, read once per process — a file on this disk does not
    change under a running server, and re-hashing 372 KB per request would be
    work nobody asked for."""
    if key not in _PINNED:
        _PINNED[key] = hashlib.sha256(where.read_bytes()).hexdigest()
    return _PINNED[key]
