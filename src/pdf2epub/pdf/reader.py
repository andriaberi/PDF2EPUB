from pathlib import Path
from typing import Any

import pymupdf

from pdf2epub.errors import ConvertError

from .fonts import has_unknown, restore_letters, type_letters
from .language import book_language
from .models import Book, Line, OutlineEntry, Page
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


class ReadError(ConvertError):
    """The PDF can't be opened or has no text to extract."""


# Names programs put in as the author when nobody set one.
ACCOUNT_NAMES = {"admin", "administrator", "user", "owner", "author", "unknown", "pc"}

# Pieces level with each other but this many line heights apart and in different
# sizes are separate lines.
APART_IN_ROW = 10
SAME_SIZE = 1.2

# A scanned page is an image covering at least this share of the page.
SCAN_AREA = 0.5


def open_pdf(path: str) -> pymupdf.Document:
    """The PDF, ready to read, or a ReadError saying why it isn't."""
    if not Path(path).is_file():
        raise ReadError(f"no such file: {path}")
    try:
        doc = pymupdf.open(path)
    except (pymupdf.FileDataError, RuntimeError) as e:
        raise ReadError(f"not a readable PDF: {path} ({e})") from None
    if doc.needs_pass:
        doc.close()
        raise ReadError(f"the PDF is password-protected: {path}")
    return doc


def read_pdf(path: str, spec: str | None = None) -> Book:
    """Read the text lines of the selected pages, with page furniture and OCR noise removed."""
    with open_pdf(path) as doc:
        try:
            selected = [doc[index] for index in parse_pages(spec, doc.page_count)]
        except ValueError as e:
            raise ReadError(str(e)) from None
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
            outline=[
                OutlineEntry(level, clean_text(title), page)
                for level, title, page in doc.get_toc()
                if page > 0 and clean_text(title)
            ],
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
    if has_unknown(blocks):
        flags = pymupdf.TEXT_MEDIABOX_CLIP | pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
        restore_letters(blocks, page.get_text("rawdict", flags=flags)["blocks"])
    type_letters(blocks)
    lines = []
    for block in blocks:
        block_glyphs = [glyph for line in block.get("lines", []) for glyph in glyphs(line)]
        # Skip vertical or rotated text such as margin notes and spine labels.
        for line in block.get("lines", []):
            if abs(line["dir"][0]) >= 0.9:
                lines.append({**line, "block": block_glyphs})
    return lines


def glyphs(line: dict[str, Any]) -> list[Glyph]:
    found = []
    for span in line["spans"]:
        raised = is_raised_mark(span)
        found += [
            Glyph(
                char["c"],
                char["origin"][0],
                span["size"],
                span["font"],
                char["bbox"][2],
                raised=raised and char["c"].isdigit(),
            )
            for char in span["chars"]
        ]
    return found


def is_raised_mark(span: dict[str, Any]) -> bool:
    """A note mark set as superscript: digits alone, raised above the line."""
    text = "".join(char["c"] for char in span["chars"]).strip()
    return bool(span["flags"] & pymupdf.TEXT_FONT_SUPERSCRIPT) and text.isdigit()


def merge_rows(pieces: list[Line]) -> list[Line]:
    """Join pieces that sit on the same printed line, in reading order.

    OCR text layers often split one printed line into several, one per word group.
    """
    rows: list[list[Line]] = []
    for piece in sorted(pieces, key=middle):
        if rows and same_row(rows[-1], piece):
            rows[-1].append(piece)
        else:
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


def same_row(row: list[Line], piece: Line) -> bool:
    """On the row's printed line, not a line of its own that happens to sit level with
    it, like a heading on the left beside the end of an epigraph on the right."""
    first = row[0]
    if abs(middle(piece) - middle(first)) >= min(piece.height, first.height) / 2:
        return False
    gap = min(max(piece.x0 - other.x1, other.x0 - piece.x1) for other in row)
    heights = max(piece.height, first.height) / min(piece.height, first.height)
    return gap < APART_IN_ROW * piece.height or heights < SAME_SIZE


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
