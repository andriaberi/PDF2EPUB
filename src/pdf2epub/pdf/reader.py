import re
from collections import Counter
from itertools import groupby
from pathlib import Path
from typing import Any

import pymupdf

from pdf2epub.errors import ConvertError

from .fonts import has_unknown, restore_letters, type_letters
from .language import book_language
from .models import BOLD, ITALIC, Book, Line, OutlineEntry, Page
from .noise import remove_noise
from .pages import parse_pages
from .pictures import read_pictures
from .spacing import (
    Advances,
    Glyph,
    lacks_spaces,
    learn_advances,
    letter_spacing,
    spaced_chars,
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

# Some books put a space at the end of a line, or the start of the next, wherever the
# break falls between words, at least this share of their line breaks, and break words
# with no hyphen: there a line ending in a letter with no space after it breaks a word.
SPACED_BREAKS = 0.5
# Such a book breaks words on many lines, at least this share; a book that only seems to,
# on a few, has lost the space at those breaks instead.
MIN_BROKEN = 0.05

# Font names that tell a font's style where its flags don't: "Sylfaen,Bold",
# "LiberationSerif-Italic".
ITALIC_NAME = re.compile("italic|oblique", re.IGNORECASE)
BOLD_NAME = re.compile("bold", re.IGNORECASE)

# A style at least this share of the book's text is set in is its text's own, not
# emphasis: a book printed in italics throughout.
USUAL_STYLE = 0.5


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
    """Read the text lines and pictures of the selected pages, with page furniture and
    OCR noise removed."""
    with open_pdf(path) as doc:
        try:
            selected = [doc[index] for index in parse_pages(spec, doc.page_count)]
        except ValueError as e:
            raise ReadError(str(e)) from None
        pages = read_pages(selected)
        if not any(page.lines for page in pages):
            raise ReadError(f"no text found in {path}; is it a scan without OCR? Try ocrmypdf.")
        read_pictures(selected, pages)

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
    breaks = iter(word_breaks(every_line))
    read = [
        read_page(page, page_lines, advances, unspaced, [next(breaks) for _ in page_lines])
        for page, page_lines in zip(pages, lines, strict=True)
    ]
    drop_usual_style(read)
    return read


def drop_usual_style(pages: list[Page]) -> None:
    """Take out of the lines' runs any style most of the book is set in."""
    lines = [line for page in pages for line in page.lines]
    counts: Counter[str] = Counter()
    for line in lines:
        for text, style in line.runs or [(line.text, "")]:
            size = len(text.strip())
            counts.update(dict.fromkeys(style, size))
            counts["all"] += size
    usual = "".join(kind for kind in (BOLD, ITALIC) if counts[kind] >= USUAL_STYLE * counts["all"])
    if not usual or not counts["all"]:
        return
    for line in lines:
        runs = [(text, "".join(k for k in style if k not in usual)) for text, style in line.runs]
        line.runs = styled_runs(runs)


def word_breaks(lines: list[list[Glyph]]) -> list[bool]:
    """Which lines break a word with no hyphen to show it, in a book that marks the
    breaks between words with a space (SPACED_BREAKS)."""
    if not lines:
        return []
    spaced = [
        ends_spaced(line) or starts_spaced(following)
        for line, following in zip(lines, [*lines[1:], []], strict=True)
    ]
    if sum(spaced) < SPACED_BREAKS * len(lines):
        return [False] * len(lines)
    breaks = [
        not space and bool(line) and line[-1].char.isalpha()
        for line, space in zip(lines, spaced, strict=True)
    ]
    if sum(breaks) < MIN_BROKEN * len(lines):
        return [False] * len(lines)
    return breaks


def ends_spaced(line: list[Glyph]) -> bool:
    return bool(line) and line[-1].char.isspace()


def starts_spaced(line: list[Glyph]) -> bool:
    return bool(line) and line[0].char.isspace()


def read_page(
    page: pymupdf.Page,
    lines: list[dict[str, Any]],
    advances: Advances,
    unspaced: bool,
    breaks: list[bool] | None = None,
) -> Page:
    pieces: list[Line] = []
    for line, breaks_word in zip(lines, breaks or [False] * len(lines), strict=True):
        line_glyphs = glyphs(line)
        # A line too short to tell its letter-spacing has its block's.
        tracking = letter_spacing(line_glyphs, advances)
        if tracking is None:
            tracking = letter_spacing(line["block"], advances) or 0.0
        chars = spaced_chars(line_glyphs, advances, tracking, unspaced)
        text = "".join(char for char, _ in chars)
        if text.strip():
            x0, y0, x1, y1 = line["bbox"]
            runs = styled_runs(chars)
            pieces.append(Line(text, x0, y0, x1, y1, breaks_word=breaks_word, runs=runs))

    merged = [line for line in merge_rows(pieces) if line.text]
    return Page(page.number + 1, page.rect.width, page.rect.height, merged, scanned=is_scan(page))


def styled_runs(chars: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """The text, characters or runs, as runs of one style each; none if it is all plain."""
    runs = [
        ("".join(text for text, _ in group), style)
        for style, group in groupby(chars, key=lambda char: char[1])
    ]
    return runs if any(style for _, style in runs) else []


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
        style = span_style(span)
        found += [
            Glyph(
                char["c"],
                char["origin"][0],
                span["size"],
                span["font"],
                char["bbox"][2],
                raised=raised and char["c"].isdigit(),
                style=style,
            )
            for char in span["chars"]
        ]
    return found


def span_style(span: dict[str, Any]) -> str:
    """The span's style, from its font's flags or its name."""
    flags, font = span["flags"], span["font"]
    bold = flags & pymupdf.TEXT_FONT_BOLD or BOLD_NAME.search(font)
    italic = flags & pymupdf.TEXT_FONT_ITALIC or ITALIC_NAME.search(font)
    return (BOLD if bold else "") + (ITALIC if italic else "")


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
                breaks_word=row[-1].breaks_word,
                runs=row_runs(row),
            )
        )
    return merged


def row_runs(row: list[Line]) -> list[tuple[str, str]]:
    """The runs of the row's pieces, a space between each; none if all are plain."""
    if not any(piece.runs for piece in row):
        return []
    runs: list[tuple[str, str]] = []
    for piece in row:
        if runs:
            runs.append((" ", ""))
        runs += piece.runs or [(piece.text, "")]
    return runs


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
