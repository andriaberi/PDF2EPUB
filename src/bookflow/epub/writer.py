import zipfile
from datetime import UTC, datetime
from html import escape
from importlib.resources import files as package_files
from pathlib import Path

from bookflow.cover import Cover
from bookflow.structure import Heading, Note, Section

from .models import Metadata
from .navigation import entries, nav_document, ncx_document, notes_title
from .pages import cover_page, notes_page, section_page, title_page
from .style import STYLESHEET

CONTAINER = """\
<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>
"""

XHTML = "application/xhtml+xml"

FONTS = [
    "NotoSerif-Regular.ttf",
    "NotoSerif-Bold.ttf",
    "NotoSerif-Italic.ttf",
    "NotoSerifGeorgian-Regular.ttf",
    "NotoSerifGeorgian-Bold.ttf",
]


NOTES_FILE = "notes.xhtml"


def write_epub(
    path: Path,
    sections: list[Section],
    metadata: Metadata,
    cover: Cover | None = None,
    notes: list[Note] | None = None,
) -> None:
    """Write the book as an EPUB 3 file, one page per section, after the cover if any.

    Notes, if the book has them, get a page of their own at the end.
    """
    files = [f"text/section-{number:04}.xhtml" for number in range(1, len(sections) + 1)]
    toc = entries(sections, files)
    if notes:
        toc.append((1, Heading(1, notes_title(metadata.language)), NOTES_FILE))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as epub:
        # The mimetype must come first and stay uncompressed.
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr("META-INF/container.xml", CONTAINER)
        epub.writestr(
            "EPUB/content.opf", package_document(files, metadata, cover is not None, bool(notes))
        )
        epub.writestr("EPUB/style.css", STYLESHEET)
        epub.writestr("EPUB/nav.xhtml", nav_document(toc, metadata.language))
        fonts = package_files("bookflow.epub") / "fonts"
        for font in FONTS:
            epub.writestr(f"EPUB/fonts/{font}", (fonts / font).read_bytes())
        epub.writestr("EPUB/toc.ncx", ncx_document(toc, metadata.title, metadata.identifier))
        if cover:
            epub.writestr("EPUB/images/cover.jpg", cover.data)
            epub.writestr("EPUB/cover.xhtml", cover_page(cover, metadata))
        epub.writestr("EPUB/title.xhtml", title_page(metadata))
        for section, file in zip(sections, files, strict=True):
            epub.writestr(f"EPUB/{file}", section_page(section, metadata))
        if notes:
            title = notes_title(metadata.language)
            page = notes_page(notes, note_sources(sections, files), title, metadata.language)
            epub.writestr(f"EPUB/{NOTES_FILE}", page)


def note_sources(sections: list[Section], files: list[str]) -> dict[str, str]:
    """The page each note is first referred to from, relative to the notes page."""
    sources: dict[str, str] = {}
    for section, file in zip(sections, files, strict=True):
        for note in section.notes.values():
            sources.setdefault(note.id, file)
    return sources


def package_document(
    files: list[str], metadata: Metadata, has_cover: bool, has_notes: bool = False
) -> str:
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    creator = f"<dc:creator>{escape(metadata.author)}</dc:creator>\n" if metadata.author else ""
    items = "\n".join(
        f'<item id="s{number}" href="{file}" media-type="{XHTML}"/>'
        for number, file in enumerate(files, start=1)
    )
    fonts = "\n".join(
        f'<item id="font{number}" href="fonts/{font}" media-type="font/ttf"/>'
        for number, font in enumerate(FONTS, start=1)
    )
    spine = "\n".join(f'<itemref idref="s{number}"/>' for number in range(1, len(files) + 1))
    # The cover-image property is EPUB 3; the "cover" meta is for older readers.
    cover_meta = '<meta name="cover" content="cover-image"/>\n' if has_cover else ""
    cover_items = (
        '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" '
        'properties="cover-image"/>\n'
        f'<item id="cover" href="cover.xhtml" media-type="{XHTML}" properties="svg"/>\n'
        if has_cover
        else ""
    )
    cover_spine = '<itemref idref="cover"/>\n' if has_cover else ""
    notes_item = (
        f'\n<item id="notes" href="{NOTES_FILE}" media-type="{XHTML}"/>' if has_notes else ""
    )
    notes_spine = '\n<itemref idref="notes"/>' if has_notes else ""

    return f"""\
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" \
xml:lang="{escape(metadata.language)}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">{escape(metadata.identifier)}</dc:identifier>
<dc:title>{escape(metadata.title)}</dc:title>
<dc:language>{escape(metadata.language)}</dc:language>
{creator}{cover_meta}<meta property="dcterms:modified">{modified}</meta>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="{XHTML}" properties="nav"/>
<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="css" href="style.css" media-type="text/css"/>
{cover_items}<item id="title" href="title.xhtml" media-type="{XHTML}"/>
{fonts}
{items}{notes_item}
</manifest>
<spine toc="ncx">
{cover_spine}<itemref idref="title"/>
<itemref idref="nav"/>
{spine}{notes_spine}
</spine>
</package>
"""
