from pathlib import Path
from typing import Any

import pymupdf

from .language import book_language
from .models import Book, Line, Page
from .noise import remove_noise
from .pages import parse_pages
from .spacing import (
    Advances,
    Glyph,
    lacks_spaces,
    learn_advances,
    letter_spacing,
    spaced_text,
)
from .text import clean_text


class ReadError(Exception):
    """The PDF can't be opened or has no text to extract."""


# Names programs put in as the author when nobody set one.
ACCOUNT_NAMES = {"admin", "administrator", "user", "owner", "author", "unknown", "pc"}

# A scanned page is an image covering at least this share of the page.
SCAN_AREA = 0.5


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
        pages = read_pages(selected)
        if not any(page.lines for page in pages):
            raise ReadError(f"no text found in {path}; is it a scan without OCR? Try ocrmypdf.")

        pages = remove_noise(pages)
        metadata = doc.metadata or {}
        return Book(
            title=metadata_text(metadata.get("title")),
            author=metadata_text(metadata.get("author")),
            language=book_language(declared_language(doc), pages),
            pages=pages,
        )


def read_pages(pages: list[pymupdf.Page]) -> list[Page]:
    """Read the pages' lines, with a space wherever the page shows one."""
    lines = [text_lines(page) for page in pages]
    every_line = [glyphs(line) for page in lines for line in page]
    advances = learn_advances(every_line)
    unspaced = lacks_spaces("".join(g.char for g in line) for line in every_line)
    return [
        read_page(page, page_lines, advances, unspaced)
        for page, page_lines in zip(pages, lines, strict=True)
    ]


def read_page(
    page: pymupdf.Page, lines: list[dict[str, Any]], advances: Advances, unspaced: bool
) -> Page:
    pieces: list[Line] = []
    for line in lines:
        line_glyphs = glyphs(line)
        # A line too short to tell its letter-spacing has its block's.
        tracking = letter_spacing(line_glyphs, advances)
        if tracking is None:
            tracking = letter_spacing(line["block"], advances) or 0.0
        text = spaced_text(line_glyphs, advances, tracking, unspaced)
        if text.strip():
            pieces.append(Line(text, *line["bbox"]))

    merged = [line for line in merge_rows(pieces) if line.text]
    return Page(page.number + 1, page.rect.width, page.rect.height, merged, scanned=is_scan(page))


def is_scan(page: pymupdf.Page) -> bool:
    """An image covering most of the page: a scan, its text an OCR layer on top."""
    area = abs(page.rect)
    return any(
        abs(pymupdf.Rect(image["bbox"]) & page.rect) >= SCAN_AREA * area
        for image in page.get_image_info()
    )


def text_lines(page: pymupdf.Page) -> list[dict[str, Any]]:
    """PyMuPDF's lines of horizontal text, each letter with its position."""
    blocks = page.get_text("rawdict", flags=pymupdf.TEXT_MEDIABOX_CLIP)["blocks"]
    lines = []
    for block in blocks:
        block_glyphs = [glyph for line in block.get("lines", []) for glyph in glyphs(line)]
        # Skip vertical or rotated text such as margin notes and spine labels.
        for line in block.get("lines", []):
            if abs(line["dir"][0]) >= 0.9:
                lines.append({**line, "block": block_glyphs})
    return lines


def glyphs(line: dict[str, Any]) -> list[Glyph]:
    return [
        Glyph(char["c"], char["origin"][0], span["size"], span["font"], char["bbox"][2])
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
    """Metadata fields are often junk like "000427", "Microsoft Word - draft.doc" or the
    name of the computer's account, "Admin"."""
    if not value:
        return None
    value = clean_text(value)
    if (
        not any(c.isalpha() for c in value)
        or value.lower().endswith((".doc", ".docx", ".pdf"))
        or value.casefold() in ACCOUNT_NAMES
    ):
        return None
    return value


def declared_language(doc: Any) -> str | None:
    """The /Lang entry of the PDF catalog, e.g. "en-US"."""
    kind, value = doc.xref_get_key(doc.pdf_catalog(), "Lang")
    if kind != "string" or not value.strip():
        return None
    return str(value).strip()
