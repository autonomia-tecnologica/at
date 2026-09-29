"""A Markdown source as a `.pdf`, written by hand against the 14 base fonts
every reader already embeds (TASK-165, §"Decidido") — no font is embedded here,
because none has to be: `/Helvetica` and its three siblings are names a PDF
reader already knows how to draw.

**The one thing that has to be right for that to work is the WIDTH of every
character this writes**, because nothing else can wrap a line or start a new
page at the right place. Those four widths are the standard Adobe AFM metrics
for Helvetica/Helvetica-Bold (Appendix E of the PDF specification, reproduced
in effectively every PDF library that ever shipped) — Oblique and BoldOblique
share their upright sibling's table because a shear transform never changes an
advance width. An accented Latin letter (`á`, `ç`, `õ`…) is not in that table by
itself; its width is its BASE letter's, which is exactly true in Helvetica (the
accent rides on the same advance the bare letter already reserves) — so
`_ACCENT_BASE` is a lookup and not a second table.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import markdown

# Points. A4, the same page `docx.py`'s `w:pgSz` draws, margins included.
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN = 56.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
TOP = PAGE_HEIGHT - MARGIN
BOTTOM = MARGIN

BODY_SIZE = 11.0
# Half the body size per heading level below H1, the same ladder `docx.py`
# draws in half-points — H1 biggest, H6 smallest, never below the body's own.
_HEADING_SIZE = {1: 20.0, 2: 17.0, 3: 15.0, 4: 13.0, 5: 12.0, 6: 11.0}
_LEADING = 1.28  # line height over the size, close enough to a reader's own default

# ---------------------------------------------------------------- widths ---
# Adobe AFM, Helvetica — codes 32 through 126, 1/1000 em.
_HELVETICA = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667,
    "'": 191, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556,
    "7": 556, "8": 556, "9": 556,
    ":": 278, ";": 278, "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556, "`": 333,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556,
    "h": 556, "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556,
    "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278, "u": 556,
    "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "{": 334, "|": 260, "}": 334, "~": 584,
}
# Adobe AFM, Helvetica-Bold — same range.
_HELVETICA_BOLD = {
    " ": 278, "!": 333, '"': 474, "#": 556, "$": 556, "%": 889, "&": 722,
    "'": 238, "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333,
    ".": 278, "/": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556,
    "7": 556, "8": 556, "9": 556,
    ":": 333, ";": 333, "<": 584, "=": 584, ">": 584, "?": 611, "@": 975,
    "A": 722, "B": 722, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778,
    "H": 722, "I": 278, "J": 556, "K": 722, "L": 611, "M": 833, "N": 722,
    "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722,
    "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "[": 333, "\\": 278, "]": 333, "^": 584, "_": 556, "`": 333,
    "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611,
    "h": 611, "i": 278, "j": 278, "k": 556, "l": 278, "m": 889, "n": 611,
    "o": 611, "p": 611, "q": 611, "r": 389, "s": 556, "t": 333, "u": 611,
    "v": 556, "w": 778, "x": 556, "y": 556, "z": 500,
    "{": 389, "|": 280, "}": 389, "~": 584,
}
_ACCENT_BASE = {
    "á": "a", "à": "a", "â": "a", "ã": "a", "ä": "a", "å": "a",
    "Á": "A", "À": "A", "Â": "A", "Ã": "A", "Ä": "A", "Å": "A",
    "ç": "c", "Ç": "C",
    "é": "e", "è": "e", "ê": "e", "ë": "e", "É": "E", "È": "E", "Ê": "E", "Ë": "E",
    "í": "i", "ì": "i", "î": "i", "ï": "i", "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
    "ñ": "n", "Ñ": "N",
    "ó": "o", "ò": "o", "ô": "o", "õ": "o", "ö": "o",
    "Ó": "O", "Ò": "O", "Ô": "O", "Õ": "O", "Ö": "O",
    "ú": "u", "ù": "u", "û": "u", "ü": "u", "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
    "ý": "y", "ÿ": "y", "Ý": "Y",
    "º": "o", "ª": "a",
}
_DEFAULT_WIDTH = 556  # a digit's width — a character neither table names a fallback


def _width(char: str, bold: bool) -> int:
    table = _HELVETICA_BOLD if bold else _HELVETICA
    return table.get(_ACCENT_BASE.get(char, char), _DEFAULT_WIDTH)


def _text_width(text: str, bold: bool, size: float) -> float:
    return sum(_width(c, bold) for c in text) * size / 1000.0


# ---------------------------------------------------------------- layout ---

@dataclass(frozen=True)
class _Segment:
    text: str
    bold: bool
    italic: bool


@dataclass
class _Line:
    segments: list[_Segment]
    size: float
    y: float = 0.0  # set once by `_paginate`, which is the one place that knows it


def _words(runs: list[markdown.Run]) -> list[_Segment]:
    out: list[_Segment] = []
    for run in runs:
        for word in run.text.split(" "):
            if word:
                out.append(_Segment(word, run.bold, run.italic))
    return out


def _wrap(words: list[_Segment], size: float, first_prefix: str, width: float) -> list[_Line]:
    """Greedy word-wrap: a word joins the current line while it still fits
    `width`, and a new line opens the moment it would not — the same rule any
    reader already expects from a paragraph."""
    lines: list[_Line] = []
    current: list[_Segment] = []
    used = 0.0
    prefix = first_prefix
    if prefix:
        current.append(_Segment(prefix, False, False))
        used = _text_width(prefix, False, size)
    for word in words:
        w = _text_width(word.text, word.bold, size)
        gap = _text_width(" ", word.bold, size) if current else 0.0
        if current and used + gap + w > width:
            lines.append(_Line(current, size))
            current = []
            used = 0.0
            gap = 0.0
        current.append(word)
        used += gap + w
    if current:
        lines.append(_Line(current, size))
    if not lines:
        lines.append(_Line([], size))
    return lines


def _block_lines(block: markdown.Block) -> list[_Line]:
    """A block's own lines — a heading bold throughout (§"O que a fatia
    decide": that IS the title/body distinction this fatia draws, the same one
    `docx.py` draws with `<w:b/>`), a list item with its marker as a leading
    plain word."""
    if block.kind == "heading":
        size = _HEADING_SIZE.get(block.level, BODY_SIZE)
        words = [_Segment(w.text, True, w.italic) for w in _words(block.runs)]
        return _wrap(words, size, "", CONTENT_WIDTH)
    prefix = f"{block.number}. " if block.kind == "item" and block.ordered else (
        "• " if block.kind == "item" else ""
    )
    return _wrap(_words(block.runs), BODY_SIZE, prefix, CONTENT_WIDTH)


def _pdf_escape(data: bytes) -> bytes:
    out = bytearray()
    for byte in data:
        if byte in (0x28, 0x29, 0x5C):  # ( ) \
            out.append(0x5C)
        out.append(byte)
    return bytes(out)


def _font_name(bold: bool, italic: bool) -> str:
    if bold and italic:
        return "F4"
    if bold:
        return "F2"
    if italic:
        return "F3"
    return "F1"


def _content_stream(lines: list[_Line]) -> bytes:
    ops = bytearray()
    for line in lines:
        x = MARGIN
        for i, seg in enumerate(line.segments):
            if i:
                x += _text_width(" ", seg.bold, line.size)
            font = _font_name(seg.bold, seg.italic)
            literal = _pdf_escape(seg.text.encode("cp1252", errors="replace"))
            ops += (
                f"BT /{font} {line.size:.2f} Tf 1 0 0 1 {x:.2f} {line.y:.2f} Tm ("
            ).encode("latin-1")
            ops += literal
            ops += b") Tj ET\n"
            x += _text_width(seg.text, seg.bold, line.size)
    return bytes(ops)


def _paginate(blocks: list[markdown.Block]) -> list[list[_Line]]:
    """Every line, with the `y` it draws at, split into pages the moment one
    would run past the bottom margin — the only thing that makes a document
    longer than one page still open correctly."""
    pages: list[list[_Line]] = [[]]
    y = TOP
    leading = BODY_SIZE * _LEADING
    for block in blocks:
        lines = _block_lines(block)
        for line in lines:
            leading = line.size * _LEADING
            if y - leading < BOTTOM:
                pages.append([])
                y = TOP
            line.y = y
            pages[-1].append(line)
            y -= leading
        y -= leading * 0.4  # a blank half-line between blocks, paragraphs included
    return [page for page in pages if page] or [[]]


def generate(text: str) -> bytes:
    """A Markdown source, whole, as the bytes of a `.pdf` — headings,
    paragraphs, bold/italic and lists preserved, page breaks handled, no font
    embedded because the 14 base fonts never need to be."""
    blocks = markdown.parse(text)
    pages = _paginate(blocks)

    objects: list[bytes] = [b""]  # object 0 is never used, per the PDF spec

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects) - 1

    catalog_num = add(b"")  # 1, patched once the Pages object exists
    pages_num = add(b"")    # 2, patched once every page is written

    font_names = ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique")
    font_nums = [
        add(
            f"<< /Type /Font /Subtype /Type1 /BaseFont /{name} "
            f"/Encoding /WinAnsiEncoding >>".encode("ascii")
        )
        for name in font_names
    ]
    font_dict = " ".join(f"/F{i + 1} {num} 0 R" for i, num in enumerate(font_nums))

    page_nums: list[int] = []
    for page_lines in pages:
        stream = _content_stream(page_lines)
        content_num = add(
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"endstream"
        )
        page_num = add(
            (
                f"<< /Type /Page /Parent {pages_num} 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH:.0f} {PAGE_HEIGHT:.0f}] "
                f"/Resources << /Font << {font_dict} >> >> "
                f"/Contents {content_num} 0 R >>"
            ).encode("ascii")
        )
        page_nums.append(page_num)

    objects[catalog_num] = f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode("ascii")
    kids = " ".join(f"{n} 0 R" for n in page_nums)
    objects[pages_num] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_nums)} >>".encode("ascii")
    )

    return _serialize(objects, catalog_num)


def _serialize(objects: list[bytes], catalog_num: int) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0] * len(objects)
    for num in range(1, len(objects)):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode("ascii")
        out += objects[num]
        out += b"\nendobj\n"
    xref_start = len(out)
    out += f"xref\n0 {len(objects)}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for num in range(1, len(objects)):
        out += f"{offsets[num]:010d} 00000 n \n".encode("ascii")
    out += (
        f"trailer\n<< /Size {len(objects)} /Root {catalog_num} 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF"
    ).encode("ascii")
    return bytes(out)
