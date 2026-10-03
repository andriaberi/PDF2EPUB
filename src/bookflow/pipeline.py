import hashlib
import sys
import uuid
from pathlib import Path

from bookflow.cli.commands import Args
from bookflow.cover import Cover, CoverError, find_cover, load_cover
from bookflow.epub import Metadata, write_epub
from bookflow.paragraphs import build_paragraphs
from bookflow.pdf import ReadError, read_pdf
from bookflow.structure import Section, build_sections


def run(args: Args) -> int:
    try:
        # Check the cover file first, so a typo fails before the slow part.
        fallback_cover = load_cover(args.cover) if args.cover else None
        book = read_pdf(args.pdf, args.pages)
    except (CoverError, ReadError, ValueError) as e:
        print(f"bookflow: {e}", file=sys.stderr)
        return 1

    pdf = Path(args.pdf)
    metadata = Metadata(
        title=args.title or book.title or pdf.stem,
        author=args.author or book.author,
        language=args.language or book.language or "und",
        identifier=book_identifier(pdf),
    )

    paragraphs = build_paragraphs(book.pages)
    sections = drop_title_page_reprints(build_sections(paragraphs, book.pages))
    sections = drop_repeated_title(sections, metadata)

    # The book's own cover comes first; --cover is for books without one.
    cover, source = choose_cover(find_cover(args.pdf), fallback_cover)

    output = Path(args.output) if args.output else pdf.with_suffix(".epub")
    try:
        write_epub(output, sections, metadata, cover)
    except OSError as e:
        print(f"bookflow: can't write {output}: {e.strerror}", file=sys.stderr)
        return 1

    headings = sum(1 for section in sections if section.heading)
    print(f"Wrote {output}: {headings} headings, {len(paragraphs)} paragraphs, {source}")
    return 0


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
    """The title page already shows the title and author; don't print them again."""
    if not sections or sections[0].heading:
        return sections
    repeated = {metadata.title.casefold(), (metadata.author or "").casefold()}
    front = sections[0]
    front.paragraphs = [p for p in front.paragraphs if p.text.casefold() not in repeated]
    return sections if front.paragraphs else sections[1:]


def book_identifier(pdf: Path) -> str:
    """The same PDF always gets the same id, so readers see a new conversion as the same book."""
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, digest)}"
