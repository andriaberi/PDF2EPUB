import hashlib
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rebind.cli.commands import Args
from rebind.cover import Cover, CoverError, find_cover, load_cover
from rebind.epub import Metadata, write_epub
from rebind.paragraphs import build_paragraphs
from rebind.pdf import ReadError, read_pdf
from rebind.structure import (
    build_sections,
    drop_front_matter,
    drop_printed_contents,
    extract_notes,
    title_page_spelling,
)


class ConvertError(Exception):
    """The book can't be converted: a bad PDF, page range or cover, or nowhere to write."""


@dataclass
class Result:
    output: Path
    headings: int
    paragraphs: int
    notes: int
    cover: str  # where the cover came from: "cover from the PDF", ...

    def summary(self) -> str:
        found = f"{self.headings} headings, {self.paragraphs} paragraphs, {self.notes} notes"
        return f"Wrote {self.output}: {found}, {self.cover}"


def run(args: Args) -> int:
    """Convert from the command line: the result on stdout, a failure on stderr."""
    try:
        result = convert(args)
    except ConvertError as e:
        print(f"rebind: {e}", file=sys.stderr)
        return 1
    print(result.summary())
    return 0


def convert(args: Args, progress: Callable[[str], None] = lambda step: None) -> Result:
    """Convert the PDF to an EPUB, telling `progress` each step as it starts."""
    try:
        # Check the cover file first, so a typo fails before the slow part.
        fallback_cover = load_cover(args.cover) if args.cover else None
        progress("Reading the PDF")
        book = read_pdf(args.pdf, args.pages)
    except (CoverError, ReadError, ValueError) as e:
        raise ConvertError(str(e)) from None

    progress("Finding paragraphs")
    pages = drop_printed_contents(book.pages)
    paragraphs = build_paragraphs(pages)
    progress("Finding chapters")
    sections = build_sections(paragraphs, pages)

    pdf = Path(args.pdf)
    title, author = title_page_spelling(sections, book.title, book.author)
    metadata = Metadata(
        title=args.title or title or pdf.stem,
        author=args.author or author,
        language=args.language or book.language or "und",
        identifier=book_identifier(pdf),
    )
    sections = drop_front_matter(sections, metadata.title, metadata.author)
    notes = extract_notes(sections)

    # The book's own cover comes first; --cover is for books without one.
    cover, source = choose_cover(find_cover(args.pdf), fallback_cover)

    output = Path(args.output) if args.output else pdf.with_suffix(".epub")
    progress("Writing the EPUB")
    try:
        write_epub(output, sections, metadata, cover, notes)
    except OSError as e:
        raise ConvertError(f"can't write {output}: {e.strerror}") from None

    headings = sum(1 for section in sections if section.heading)
    return Result(output, headings, len(paragraphs), len(notes), source)


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
