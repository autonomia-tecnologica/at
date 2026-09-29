"""The one thing `docx.py` and `pdf.py` genuinely repeat (TASK-165, §"Decidido"):
reading a Markdown source apart into BLOCKS, and a block's own text apart into
RUNS. Everything past this — how a heading becomes bold text at a bigger size,
how a `w:p` differs from a content-stream line — is each generator's own, and
stays there.

**What is read**, and no more (the fatia's own "o que ficar de fora"): `#`
through `######` headings, paragraphs, `-`/`*` and `1.` list items, and
`**bold**`/`*italic*`/`_italic_` inline emphasis. A table, an image, a link, a
code fence, a block quote — none of it is markdown this module recognizes, and
each falls through as an ordinary paragraph, verbatim marks and all: a
generator that does not know a shape draws the words anyway, never nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UNORDERED = re.compile(r"^[-*]\s+(.*)$")
_ORDERED = re.compile(r"^(\d+)\.\s+(.*)$")
_INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)")


@dataclass(frozen=True)
class Run:
    """A stretch of one block's text that carries the SAME emphasis — the
    smallest piece either generator ever draws on its own."""

    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Block:
    """One paragraph, heading or list item. `level` is the heading's (1-6) and
    unused otherwise; `ordered`/`number` carry a list item's own marker — the
    number markdown wrote, not a recount, so `3. x` after a gap still reads
    `3`."""

    kind: str  # "heading" | "paragraph" | "item"
    runs: list[Run] = field(default_factory=list)
    level: int = 0
    ordered: bool = False
    number: int | None = None


def parse(text: str) -> list[Block]:
    """The source, apart into blocks, in the order they read.

    A blank line ends whatever paragraph was accumulating; a heading or a list
    item is its own block from the line it starts on, never merged into one
    beside it — the one shape markdown itself never merges either.
    """
    blocks: list[Block] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(Block("paragraph", _inline(" ".join(paragraph))))
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            blocks.append(Block("heading", _inline(heading.group(2).strip()), level=level))
            continue
        ordered = _ORDERED.match(line)
        if ordered:
            flush()
            blocks.append(Block(
                "item", _inline(ordered.group(2).strip()),
                ordered=True, number=int(ordered.group(1)),
            ))
            continue
        unordered = _UNORDERED.match(line)
        if unordered:
            flush()
            blocks.append(Block("item", _inline(unordered.group(1).strip())))
            continue
        paragraph.append(line)
    flush()
    return blocks


def _inline(text: str) -> list[Run]:
    """`text`, apart into runs of plain, `**bold**` and `*italic*`/`_italic_` —
    the marker itself never survives into a `Run.text`. Not nested (a `*` inside
    a `**bold**` stays inside it, per the bold alternative trying first) and not
    combined: `***x***` reads as bold with its own leftover `*x*` untouched —
    the fatia's own line for what markdown a first pass does not have to chase.
    """
    runs: list[Run] = []
    for piece in _INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            runs.append(Run(piece[2:-2], bold=True))
        elif piece.startswith("*") and piece.endswith("*"):
            runs.append(Run(piece[1:-1], italic=True))
        elif piece.startswith("_") and piece.endswith("_"):
            runs.append(Run(piece[1:-1], italic=True))
        else:
            runs.append(Run(piece))
    return runs
