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
    build_sections,
    drop_front_matter,
    drop_printed_contents,
    extract_notes,
    title_page_spelling,
)


@dataclass
class Options:
    pdf: str
    output: str
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


def convert(options: Options, progress: Callable[[str], None] = lambda step: None) -> Result:
    """Convert the PDF to an EPUB, telling `progress` each step as it starts."""
    try:
        # Check the cover file first, so a typo fails before the slow part.
        fallback_cover = load_cover(options.cover) if options.cover else None
        progress("Reading the PDF")
        book = read_pdf(options.pdf, options.pages)
    except (CoverError, ReadError, ValueError) as e:
        raise ConvertError(str(e)) from None

    progress("Finding paragraphs")
    pages = drop_printed_contents(book.pages)
    paragraphs = build_paragraphs(pages)
    progress("Finding chapters")
    sections = build_sections(paragraphs, pages)

    pdf = Path(options.pdf)
    title, author = title_page_spelling(sections, book.title, book.author)
    metadata = Metadata(
        title=options.title or title or pdf.stem,
        author=options.author or author,
        language=options.language or book.language or "und",
        identifier=book_identifier(pdf),
    )
    sections = drop_front_matter(sections, metadata.title, metadata.author)
    notes = extract_notes(sections)

    # The book's own cover comes first; --cover is for books without one.
    cover, source = choose_cover(find_cover(options.pdf), fallback_cover)

    output = Path(options.output)
    progress("Writing the EPUB")
    try:
        write_epub(output, sections, metadata, cover, notes)
    except OSError as e:
        raise ConvertError(f"can't write {output}: {e.strerror}") from None

    headings = sum(1 for section in sections if section.heading)
    written = sum(len(section.paragraphs) for section in sections)
    return Result(output, headings, written, len(notes), source)


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
