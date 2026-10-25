import hashlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pdf2epub.book import Book
from pdf2epub.cover import Cover, CoverError, find_cover, load_cover
from pdf2epub.epub import Metadata, write_epub
from pdf2epub.paragraphs import Paragraph, build_paragraphs
from pdf2epub.pdf import ReadError, read_pdf
from pdf2epub.structure import (
    Section,
    build_sections,
    drop_front_matter,
    drop_printed_contents,
    extract_notes,
    printed_contents,
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
    everything = [(section, list(section.paragraphs)) for section in sections]
    sections = drop_front_matter(sections, metadata.title, metadata.author)
    notes = extract_notes(sections)
    sections = with_left_out(everything, sections)
    for paragraph in printed_contents(pdf_book.pages):
        place_by_page(sections, paragraph)

    # The book's own cover comes first; the given one is for books without one.
    cover, source = choose_cover(find_cover(options.pdf), fallback_cover)
    return Book.from_sections(metadata, sections, notes, cover, source)


def write_book(book: Book, output: str | Path) -> Result:
    """Write the book as an EPUB at `output`."""
    output = Path(output)
    sections = book.sections()
    try:
        write_epub(output, sections, book.metadata, book.cover, book.written_notes())
    except OSError as e:
        raise ConvertError(f"can't write {output}: {e.strerror}") from None

    headings = sum(1 for section in sections if section.heading)
    paragraphs = sum(len(section.paragraphs) for section in sections)
    notes = len(book.written_notes())
    return Result(output, headings, paragraphs, notes, book.cover_source)


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
