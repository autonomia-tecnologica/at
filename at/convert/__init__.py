"""Converting a Markdown file to DOCX and PDF (TASK-165) — stdlib only.

Two generators, `docx.py` and `pdf.py`, deliberately kept apart (the person's
own instruction, TASK-165 §"Decidido"): nothing is shared between them beyond
what both genuinely repeat, which is reading the Markdown apart into blocks and
runs — `markdown.py`, this package's third module. Each generator walks the
same blocks its own way, into its own binary format.

No third-party dependency enters here or ever will: `fpdf2` drags Pillow and
`python-docx` drags lxml, and both are C extensions the product's
stdlib-only `requirements.txt` (PyNaCl alone) does not carry. A DOCX is a zip of
XML (`zipfile`, `xml` — both stdlib); a PDF of plain text is a format simple
enough to write by hand against the 14 base fonts every reader already embeds.
"""

from __future__ import annotations

from pathlib import Path

from at.core import files, paths

from . import docx, pdf

# The one door the `cli` (fatia 2) and the WebApp (fatia 4) both walk through —
# neither reaches `docx.generate`/`pdf.generate` on its own, so neither has to
# know where `Convertidos/` is or how a name collision there gets resolved.
FORMATS = {"pdf": pdf, "docx": docx}


def convert(source: Path, to: str) -> Path:
    """`source` (a Markdown file), turned into `to` ("pdf" or "docx") and
    written into `Convertidos/` — the path it landed at, name collision
    already resolved.

    The read is the caller's own file, wherever it sits (`Arquivos/`, a
    project's own tree); the write is always `Convertidos/`, and always
    through the counted, atomic door (`files.atomic_write_bytes`) every other
    product write already uses.
    """
    if to not in FORMATS:
        raise ValueError(f"unknown format: {to}")
    # `errors="replace"`, the same policy `prose.read` already reads a file
    # under — a byte that is not valid UTF-8 is not a reason to crash a
    # conversion the caller already checked was text (`prose.read`'s own
    # `is_text`, which both doors call before this one).
    text = source.read_bytes().decode("utf-8", errors="replace")
    data = FORMATS[to].generate(text)
    target = _unique(paths.convert_dir() / (source.stem + "." + to))
    files.atomic_write_bytes(target, data)
    return target


def _unique(path: Path) -> Path:
    """`path`, or the first `nome (n).ext` beside it nothing already holds —
    `Convertidos` already carrying a file of that name is not a refusal, it is
    the ordinary case a second conversion of the same source produces."""
    if not path.exists():
        return path
    n = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1
