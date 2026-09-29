"""A Markdown source as a `.docx` — a zip of XML, `zipfile` and `xml` both
stdlib (TASK-165, §"Decidido"). Three parts, the minimum Word opens: the
content-types declaration, the package's own relationship to the document, and
`word/document.xml` itself.

**Headings and lists carry no named STYLE** (no `styles.xml`, no
`numbering.xml`): a heading is a paragraph whose run properties are bold at a
bigger size, and a list item is a paragraph with a literal `•`/`N.` prefix —
`docx.py`'s own "o que ficar de fora" (TASK-165 §"O que a fatia decide"). Word
opens either without complaint; what a person loses against a "real" numbered
list is the list PANEL recognizing it as one, never the words on the page.
"""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

from . import markdown

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)

# Half-points — Word's own unit for `w:sz`. H1 the biggest, H6 never below the
# body's own 22 (11pt), the same ladder `pdf.py` draws in points.
_HEADING_SIZE = {1: 32, 2: 28, 3: 26, 4: 24, 5: 22, 6: 20}
_BODY_SIZE = 22

# A4 in twentieths of a point (`w:pgSz`/`w:pgMar`), matching `pdf.py`'s own
# page — the same document, opened by two different readers.
_SECT_PR = (
    "<w:sectPr>"
    '<w:pgSz w:w="11906" w:h="16838"/>'
    '<w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417"/>'
    "</w:sectPr>"
)


def _run_xml(run: markdown.Run, force_bold: bool, size: int) -> str:
    props = []
    if run.bold or force_bold:
        props.append("<w:b/>")
    if run.italic:
        props.append("<w:i/>")
    props.append(f'<w:sz w:val="{size}"/>')
    text = escape(run.text)
    return f'<w:r><w:rPr>{"".join(props)}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'


def _paragraph_xml(runs: list[markdown.Run], *, bold: bool, size: int, prefix: str = "") -> str:
    body = "".join(_run_xml(r, bold, size) for r in runs)
    if prefix:
        marker = f'<w:r><w:rPr><w:sz w:val="{size}"/></w:rPr><w:t xml:space="preserve">{escape(prefix)}</w:t></w:r>'
        body = marker + body
    if not body:
        return "<w:p/>"
    return f"<w:p>{body}</w:p>"


def _document_xml(blocks: list[markdown.Block]) -> str:
    parts = []
    for block in blocks:
        if block.kind == "heading":
            size = _HEADING_SIZE.get(block.level, _BODY_SIZE)
            parts.append(_paragraph_xml(block.runs, bold=True, size=size))
        elif block.kind == "item":
            prefix = f"{block.number}. " if block.ordered else "• "
            parts.append(_paragraph_xml(block.runs, bold=False, size=_BODY_SIZE, prefix=prefix))
        else:
            parts.append(_paragraph_xml(block.runs, bold=False, size=_BODY_SIZE))
    body = "".join(parts) if parts else "<w:p/>"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}{_SECT_PR}</w:body></w:document>"
    )


def generate(text: str) -> bytes:
    """A Markdown source, whole, as the bytes of a `.docx` — headings,
    paragraphs, bold/italic and lists preserved; a table, an image or a link
    is not markdown `markdown.py` reads, and reaches this as plain text."""
    blocks = markdown.parse(text)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", _document_xml(blocks))
    return buffer.getvalue()
