import hashlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pdf2epub.cover import Cover, CoverError, find_cover, load_cover
from pdf2epub.epub import Metadata, write_epub
from pdf2epub.paragraphs import build_paragraphs
from pdf2epub.pdf import ReadError, read_pdf
from pdf2epub.structure import (
    Note,
    Section,
    build_sections,
    drop_front_matter,
    drop_printed_contents,
    extract_notes,
    title_page_spelling,
)

# The steps convert() tells its progress callback, in order; read_book() tells the first three.
STEPS = ("Reading the PDF", "Finding paragraphs", "Finding chapters", "Writing the EPUB")


@dataclass
class Options:
    pdf: str
    pages: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    cover: str | None = None


class ConvertError(Exception):
    """The book can't be converted: a bad PDF, page range or cover, or nowhere to write."""


@dataclass
class Book:
    """Everything found in the PDF, ready to be written as an EPUB."""

    metadata: Metadata
    sections: list[Section]
    notes: list[Note]
    cover: Cover | None
    cover_source: str  # "cover from the PDF", "cover from the given image" or "no cover"


@dataclass
class Result:
    output: Path
    headings: int
    paragraphs: int
    notes: int
    cover: str  # where the cover came from: "cover from the PDF", ...


def convert(
    options: Options, output: str | Path, progress: Callable[[str], None] = lambda step: None
) -> Result:
    """Convert the PDF to an EPUB at `output`, telling `progress` each step as it starts."""
    book = read_book(options, progress)
    progress("Writing the EPUB")
    return write_book(book, output)


def read_book(options: Options, progress: Callable[[str], None] = lambda step: None) -> Book:
    """Find the book in the PDF, telling `progress` each step as it starts."""
    try:
        # Check the cover file first, so a typo fails before the slow part.
        fallback_cover = load_cover(options.cover) if options.cover else None
        progress("Reading the PDF")
        pdf_book = read_pdf(options.pdf, options.pages)
    except (CoverError, ReadError, ValueError) as e:
        raise ConvertError(str(e)) from None

    progress("Finding paragraphs")
    pages = drop_printed_contents(pdf_book.pages)
    paragraphs = build_paragraphs(pages)
    progress("Finding chapters")
    sections = build_sections(paragraphs, pages)

    pdf = Path(options.pdf)
    title, author = title_page_spelling(sections, pdf_book.title, pdf_book.author)
    metadata = Metadata(
        title=options.title or title or pdf.stem,
        author=options.author or author,
        language=options.language or pdf_book.language or "und",
        identifier=book_identifier(pdf),
    )
    sections = drop_front_matter(sections, metadata.title, metadata.author)
    notes = extract_notes(sections)

    # The book's own cover comes first; the given one is for books without one.
    cover, source = choose_cover(find_cover(options.pdf), fallback_cover)
    return Book(metadata, sections, notes, cover, source)


def write_book(book: Book, output: str | Path) -> Result:
    """Write the book as an EPUB at `output`."""
    output = Path(output)
    try:
        write_epub(output, book.sections, book.metadata, book.cover, book.notes)
    except OSError as e:
        raise ConvertError(f"can't write {output}: {e.strerror}") from None

    headings = sum(1 for section in book.sections if section.heading)
    paragraphs = sum(len(section.paragraphs) for section in book.sections)
    return Result(output, headings, paragraphs, len(book.notes), book.cover_source)


def choose_cover(own: Cover | None, fallback: Cover | None) -> tuple[Cover | None, str]:
    if own:
        return own, "cover from the PDF"
    if fallback:
        return fallback, "cover from the given image"
    return None, "no cover"


def book_identifier(pdf: Path) -> str:
    """The same PDF always gets the same id, so readers see a new conversion as the same book."""
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, digest)}"
