import hashlib
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bookflow.cli.commands import Args
from bookflow.cover import Cover, CoverError, find_cover, load_cover
from bookflow.epub import Metadata, write_epub
from bookflow.paragraphs import build_paragraphs
from bookflow.pdf import ReadError, read_pdf
from bookflow.structure import Section, build_sections, drop_printed_contents, extract_notes


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
        print(f"bookflow: {e}", file=sys.stderr)
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

    pdf = Path(args.pdf)
    metadata = Metadata(
        title=args.title or book.title or pdf.stem,
        author=args.author or book.author,
        language=args.language or book.language or "und",
        identifier=book_identifier(pdf),
    )

    progress("Finding paragraphs")
    pages = drop_printed_contents(book.pages)
    paragraphs = build_paragraphs(pages)
    progress("Finding chapters")
    sections = drop_title_page_reprints(build_sections(paragraphs, pages))
    sections = drop_repeated_title(sections, metadata)
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
        return fallback, "cover from --cover"
    return None, "no cover"


# Front matter this short is a title page, not a preface.
TITLE_PAGE = 3


def drop_title_page_reprints(sections: list[Section]) -> list[Section]:
    """Drop the title page printed again before a new volume, at the end of a section."""
    if not sections or sections[0].heading or len(sections[0].paragraphs) > TITLE_PAGE:
        return sections
    title_page = {p.text.casefold() for p in sections[0].paragraphs}
    for section in sections[1:]:
        while section.paragraphs and section.paragraphs[-1].text.casefold() in title_page:
            section.paragraphs.pop()
    return sections


def drop_repeated_title(sections: list[Section], metadata: Metadata) -> list[Section]:
    """The title page already shows the title and author; don't print them again.

    The PDF often doesn't say what its title is, so the book's own title page goes
    too, however it spells the title ("ალბერ კამიუ - უცხო").
    """
    if not sections or sections[0].heading:
        return sections
    repeated = {metadata.title.casefold(), (metadata.author or "").casefold()}
    front = sections[0]
    front.paragraphs = [p for p in front.paragraphs if p.text.casefold() not in repeated]
    return sections if front.paragraphs and not is_title_page(front) else sections[1:]


def is_title_page(section: Section) -> bool:
    """A few lines on the first page, names rather than sentences: author, title."""
    paragraphs = section.paragraphs
    return (
        len(paragraphs) <= TITLE_PAGE
        and all(p.page == paragraphs[0].page for p in paragraphs)
        and not any(p.text.endswith((".", "!", "?", "…")) for p in paragraphs)
    )


def book_identifier(pdf: Path) -> str:
    """The same PDF always gets the same id, so readers see a new conversion as the same book."""
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, digest)}"
