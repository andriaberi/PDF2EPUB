import zipfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from bookflow.structure import Section

from .models import Metadata
from .navigation import entries, nav_document, ncx_document
from .pages import section_page, title_page
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


def write_epub(path: Path, sections: list[Section], metadata: Metadata) -> None:
    """Write the book as an EPUB 3 file, one page per section."""
    files = [f"text/section-{number:04}.xhtml" for number in range(1, len(sections) + 1)]
    toc = entries(sections, files)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as epub:
        # The mimetype must come first and stay uncompressed.
        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        epub.writestr("META-INF/container.xml", CONTAINER)
        epub.writestr("EPUB/content.opf", package_document(files, metadata))
        epub.writestr("EPUB/style.css", STYLESHEET)
        epub.writestr("EPUB/nav.xhtml", nav_document(toc, metadata.language))
        epub.writestr("EPUB/toc.ncx", ncx_document(toc, metadata.title, metadata.identifier))
        epub.writestr("EPUB/title.xhtml", title_page(metadata))
        for section, file in zip(sections, files, strict=True):
            epub.writestr(f"EPUB/{file}", section_page(section, metadata))


def package_document(files: list[str], metadata: Metadata) -> str:
    modified = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    creator = f"<dc:creator>{escape(metadata.author)}</dc:creator>\n" if metadata.author else ""
    items = "\n".join(
        f'<item id="s{number}" href="{file}" media-type="{XHTML}"/>'
        for number, file in enumerate(files, start=1)
    )
    spine = "\n".join(f'<itemref idref="s{number}"/>' for number in range(1, len(files) + 1))

    return f"""\
<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" \
xml:lang="{escape(metadata.language)}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">{escape(metadata.identifier)}</dc:identifier>
<dc:title>{escape(metadata.title)}</dc:title>
<dc:language>{escape(metadata.language)}</dc:language>
{creator}<meta property="dcterms:modified">{modified}</meta>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="{XHTML}" properties="nav"/>
<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
<item id="css" href="style.css" media-type="text/css"/>
<item id="title" href="title.xhtml" media-type="{XHTML}"/>
{items}
</manifest>
<spine toc="ncx">
<itemref idref="title"/>
<itemref idref="nav"/>
{spine}
</spine>
</package>
"""
