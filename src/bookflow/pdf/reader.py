from pathlib import Path
from typing import Any

import pymupdf

from .language import detect_language
from .models import Book, Line, Page
from .noise import remove_noise
from .pages import parse_pages
from .spacing import Advances, Glyph, lacks_spaces, learn_advances, spaced_text
from .text import clean_text


class ReadError(Exception):
    """The PDF can't be opened or has no text to extract."""


def read_pdf(path: str, spec: str | None = None) -> Book:
    """Read the text lines of the selected pages, with page furniture and OCR noise removed."""
    if not Path(path).is_file():
        raise ReadError(f"no such file: {path}")
    try:
        doc = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError) as e:
        raise ReadError(f"not a readable PDF: {path} ({e})") from None

    with doc:
        if doc.needs_pass:
            raise ReadError(f"the PDF is password-protected: {path}")

        selected = [doc[index] for index in parse_pages(spec, doc.page_count)]
        pages = [read_page(page, text_lines(page)) for page in selected]
        if lacks_spaces(line.text for page in pages for line in page.lines):
            pages = read_unspaced(selected)
        if not any(page.lines for page in pages):
            raise ReadError(f"no text found in {path}; is it a scan without OCR? Try ocrmypdf.")

        pages = remove_noise(pages)
        metadata = doc.metadata or {}
        return Book(
            title=metadata_text(metadata.get("title")),
            author=metadata_text(metadata.get("author")),
            language=declared_language(doc) or detect_language(pages),
            pages=pages,
        )


def read_page(
    page: pymupdf.Page, lines: list[dict[str, Any]], advances: Advances | None = None
) -> Page:
    """The page's lines; with `advances`, spaces are put back between the words."""
    pieces: list[Line] = []
    for line in lines:
        if advances is None:
            text = "".join(span["text"] for span in line["spans"])
        else:
            text = spaced_text(glyphs(line), advances)
        if text.strip():
            pieces.append(Line(text, *line["bbox"]))

    merged = [line for line in merge_rows(pieces) if line.text]
    return Page(page.number + 1, page.rect.width, page.rect.height, merged)


def read_unspaced(pages: list[pymupdf.Page]) -> list[Page]:
    """Read pages whose words are set apart by position alone, without spaces."""
    lines = [text_lines(page, raw=True) for page in pages]
    advances = learn_advances(glyphs(line) for page in lines for line in page)
    return [
        read_page(page, page_lines, advances) for page, page_lines in zip(pages, lines, strict=True)
    ]


def text_lines(page: pymupdf.Page, raw: bool = False) -> list[dict[str, Any]]:
    """PyMuPDF's lines of horizontal text; `raw` gives each letter with its position."""
    blocks = page.get_text("rawdict" if raw else "dict", flags=pymupdf.TEXT_MEDIABOX_CLIP)["blocks"]
    # Skip vertical or rotated text such as margin notes and spine labels.
    return [
        line for block in blocks for line in block.get("lines", []) if abs(line["dir"][0]) >= 0.9
    ]


def glyphs(line: dict[str, Any]) -> list[Glyph]:
    return [
        Glyph(char["c"], char["origin"][0], span["size"], span["font"])
        for span in line["spans"]
        for char in span["chars"]
    ]


def merge_rows(pieces: list[Line]) -> list[Line]:
    """Join pieces that sit on the same printed line, in reading order.

    OCR text layers often split one printed line into several, one per word group.
    """
    rows: list[list[Line]] = []
    for piece in sorted(pieces, key=middle):
        if rows:
            first = rows[-1][0]
            if abs(middle(piece) - middle(first)) < min(piece.height, first.height) / 2:
                rows[-1].append(piece)
                continue
        rows.append([piece])

    merged = []
    for row in rows:
        row.sort(key=lambda p: p.x0)
        merged.append(
            Line(
                text=clean_text(" ".join(p.text for p in row)),
                x0=min(p.x0 for p in row),
                y0=min(p.y0 for p in row),
                x1=max(p.x1 for p in row),
                y1=max(p.y1 for p in row),
            )
        )
    return merged


def middle(line: Line) -> float:
    return (line.y0 + line.y1) / 2


def metadata_text(value: str | None) -> str | None:
    """Metadata fields are often junk like "000427" or "Microsoft Word - draft.doc"."""
    if not value:
        return None
    value = clean_text(value)
    if not any(c.isalpha() for c in value) or value.lower().endswith((".doc", ".docx", ".pdf")):
        return None
    return value


def declared_language(doc: Any) -> str | None:
    """The /Lang entry of the PDF catalog, e.g. "en-US"."""
    kind, value = doc.xref_get_key(doc.pdf_catalog(), "Lang")
    if kind != "string" or not value.strip():
        return None
    return str(value).strip()
