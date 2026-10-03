from html import escape

from bookflow.structure import Heading, Section

from .pages import page

Entry = tuple[int, Heading, str]  # level, heading, file

CONTENTS = {"ka": "სარჩევი", "en": "Contents"}


def entries(sections: list[Section], files: list[str]) -> list[Entry]:
    """Table of contents entries; front matter has no heading and isn't listed."""
    return [
        (section.heading.level, section.heading, file)
        for section, file in zip(sections, files, strict=True)
        if section.heading
    ]


def contents_title(language: str) -> str:
    return CONTENTS.get(language.split("-")[0], CONTENTS["en"])


def nav_document(toc: list[Entry], language: str) -> str:
    """The table of contents, nested by heading level. It is also a page of the book."""
    title = contents_title(language)
    nested = any(level > 1 for level, _, _ in toc)
    shape = "nested" if nested else "flat"
    lines = [
        f'<nav epub:type="toc" id="toc" class="contents {shape}">',
        f"<h1>{escape(title)}</h1>",
    ]
    depth = 0
    for level, heading, file in toc:
        level = min(level, depth + 1)  # a level can only go one deeper than the last
        if level > depth:
            lines.append("<ol>")
        else:
            lines.append("</li>")
            for _ in range(depth - level):
                lines.append("</ol></li>")
        lines.append(f'<li><a href="{file}">{escape(heading.text)}</a>')
        depth = level
    for _ in range(depth):
        lines.append("</li></ol>")
    lines.append("</nav>")
    return page(title, "\n".join(lines), language)


def ncx_document(toc: list[Entry], title: str, identifier: str) -> str:
    """The EPUB 2 table of contents, for older readers."""
    lines = []
    depth = 0
    for order, (level, heading, file) in enumerate(toc, start=1):
        level = min(level, depth + 1)
        for _ in range(depth - level + 1):
            lines.append("</navPoint>")
        lines.append(
            f'<navPoint id="nav-{order}" playOrder="{order}">'
            f"<navLabel><text>{escape(heading.text)}</text></navLabel>"
            f'<content src="{file}"/>'
        )
        depth = level
    lines.extend("</navPoint>" for _ in range(depth))

    return f"""\
<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head>
<meta name="dtb:uid" content="{escape(identifier)}"/>
<meta name="dtb:depth" content="{max((level for level, _, _ in toc), default=1)}"/>
<meta name="dtb:totalPageCount" content="0"/>
<meta name="dtb:maxPageNumber" content="0"/>
</head>
<docTitle><text>{escape(title)}</text></docTitle>
<navMap>
{chr(10).join(lines)}
</navMap>
</ncx>
"""
