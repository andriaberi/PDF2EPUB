import hashlib
import math
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from pdf2epub.book import GIVEN_COVER, NO_COVER, PDF_COVER, Book
from pdf2epub.cover import Cover, find_cover, load_cover
from pdf2epub.epub import Metadata, write_epub
from pdf2epub.errors import BookError, ConvertError
from pdf2epub.paragraphs import Paragraph, build_paragraphs
from pdf2epub.pdf import Page, read_pdf
from pdf2epub.structure import (
    Section,
    build_sections,
    drop_front_matter,
    drop_printed_contents,
    extract_notes,
    link_footnotes,
    printed_contents,
    title_page_spelling,
)

# The steps convert() tells its progress callback, in order; read_book() tells the first three.
STEPS = ("Reading the PDF", "Finding paragraphs", "Finding chapters", "Writing the EPUB")
READING, PARAGRAPHS, CHAPTERS, WRITING = STEPS

# How many of a book's problems an error names.
MAX_PROBLEMS = 5


@dataclass
class Options:
    pdf: str
    pages: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    cover: str | bytes | None = None  # a path or the image itself
    credit: bool = True  # name PDF2EPUB in the EPUB's metadata
    pictures: bool = True  # keep the pictures printed in the book


@dataclass
class Result:
    output: Path | None  # None when written to a file object
    headings: int
    paragraphs: int
    notes: int
    pictures: int
    cover: str  # where the cover came from: PDF_COVER, GIVEN_COVER or NO_COVER


def convert(
    options: Options, output: str | Path, progress: Callable[[str], None] = lambda step: None
) -> Result:
    """Convert the PDF to an EPUB at `output`, telling `progress` each step as it starts."""
    book = read_book(options, progress)
    progress(WRITING)
    return write_book(book, output, options.credit)


def read_book(options: Options, progress: Callable[[str], None] = lambda step: None) -> Book:
    """Find the book in the PDF, telling `progress` each step as it starts."""
    # Check the cover file first, so a typo fails before the slow part.
    fallback_cover = load_cover(options.cover) if options.cover else None
    progress(READING)
    pdf_book = read_pdf(options.pdf, options.pages, options.pictures)

    progress(PARAGRAPHS)
    pages = drop_printed_contents(pdf_book.pages)
    paragraphs = build_paragraphs(pages)
    progress(CHAPTERS)
    sections = build_sections(paragraphs, pages, pdf_book.outline)

    pdf = Path(options.pdf)
    title, author = title_page_spelling(sections, pdf_book.title, pdf_book.author)
    metadata = Metadata(
        title=options.title or title or pdf.stem,
        author=options.author or author,
        language=options.language or pdf_book.language or "und",
        identifier=book_identifier(pdf),
    )
    everything = [(section, list(section.paragraphs)) for section in sections]
    sections = drop_front_matter(sections, metadata.title, metadata.author)
    notes = extract_notes(sections)
    notes += link_footnotes(sections, [f for page in pdf_book.pages for f in page.footnotes])
    sections = with_left_out(everything, sections)
    for paragraph in printed_contents(pdf_book.pages):
        place_by_page(sections, paragraph)
    sections = place_pictures(sections, pdf_book.pages)

    # The book's own cover comes first; the given one is for books without one.
    cover, source = choose_cover(find_cover(options.pdf), fallback_cover)
    return Book.from_sections(metadata, sections, notes, cover, source)


def write_book(book: Book, output: str | Path | IO[bytes], credit: bool = True) -> Result:
    """Write the book as an EPUB at `output`, a path or a binary file object such as
    io.BytesIO, unless it has problems() to fix first. With `credit`, the EPUB's metadata
    names PDF2EPUB as its producer."""
    if problems := book.problems():
        more = f"; and {len(problems) - MAX_PROBLEMS} more" if len(problems) > MAX_PROBLEMS else ""
        raise BookError("; ".join(problems[:MAX_PROBLEMS]) + more)
    target = Path(output) if isinstance(output, str | Path) else output
    sections = book.sections()
    notes = book.written_notes()
    try:
        write_epub(target, sections, book.metadata, book.cover, notes, credit)
    except OSError as e:
        raise ConvertError(f"can't write {output}: {e.strerror}") from None

    headings = sum(1 for section in sections if section.heading)
    texts = [paragraph for section in sections for paragraph in section.paragraphs]
    pictures = sum(1 for paragraph in texts if paragraph.picture)
    path = target if isinstance(target, Path) else None
    return Result(path, headings, len(texts) - pictures, len(notes), pictures, book.cover_source)


def with_left_out(
    everything: list[tuple[Section, list[Paragraph]]], kept: list[Section]
) -> list[Section]:
    """The sections as they were, with the paragraphs left out marked by their role;
    paragraphs taken into the notes are gone for good."""
    written = {id(paragraph) for section in kept for paragraph in section.paragraphs}
    return [
        Section(
            section.heading,
            [p for p in paragraphs if p.role != "body" or id(p) in written],
            section.notes,
        )
        for section, paragraphs in everything
    ]


def place_by_page(sections: list[Section], paragraph: Paragraph) -> None:
    """Put the paragraph before the first heading or paragraph printed after it."""
    for index, section in enumerate(sections):
        if section.heading and section.heading.page > paragraph.page:
            if index == 0:
                sections.insert(0, Section(None, [paragraph]))
            else:
                sections[index - 1].paragraphs.append(paragraph)
            return
        for at, other in enumerate(section.paragraphs):
            if other.page > paragraph.page:
                section.paragraphs.insert(at, paragraph)
                return
    if sections:
        sections[-1].paragraphs.append(paragraph)
    else:
        sections.append(Section(None, [paragraph]))


def place_pictures(sections: list[Section], pages: list[Page]) -> list[Section]:
    """The sections with the pictures among the text printed around them: each before
    the first paragraph printed below it, and after the heading of its page. A picture
    takes the role of the text after it."""
    waiting = deque((page.number, picture) for page in pages for picture in page.pictures)

    def printed_above(page: float, y: float, role: str) -> list[Paragraph]:
        due = []
        while waiting and (waiting[0][0], waiting[0][1].y0) < (page, y):
            number, picture = waiting.popleft()
            due.append(Paragraph("", number, picture=picture, role=role))
        return due

    # Pictures before the first heading start a section of their own.
    placed = [Section(None)]
    for section in sections:
        if heading := section.heading:
            placed[-1].paragraphs += printed_above(heading.page, -math.inf, heading.role)
        paragraphs: list[Paragraph] = []
        for paragraph in section.paragraphs:
            top = paragraph.lines[0].y0 if paragraph.lines else -math.inf
            paragraphs += printed_above(paragraph.page, top, paragraph.role)
            paragraphs.append(paragraph)
        section.paragraphs = paragraphs
        placed.append(section)
    last = next((p.role for s in reversed(placed) for p in reversed(s.paragraphs)), "body")
    placed[-1].paragraphs += printed_above(math.inf, math.inf, last)
    return placed if placed[0].paragraphs else placed[1:]


def choose_cover(own: Cover | None, fallback: Cover | None) -> tuple[Cover | None, str]:
    if own:
        return own, PDF_COVER
    if fallback:
        return fallback, GIVEN_COVER
    return None, NO_COVER


def book_identifier(pdf: Path) -> str:
    """The same PDF always gets the same id, so readers see a new conversion as the same book."""
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, digest)}"
