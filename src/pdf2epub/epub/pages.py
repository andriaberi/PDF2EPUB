import re
from html import escape

from pdf2epub.cover import Cover
from pdf2epub.pdf.text import NOTE_MARK
from pdf2epub.structure import Heading, Note, Section
from pdf2epub.styles import styled_html

from .models import Metadata

PAGE = """\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" \
lang="{lang}" xml:lang="{lang}">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<link rel="stylesheet" type="text/css" href="{css}"/>
</head>
<body{body_class}>
{body}
</body>
</html>
"""

ORNAMENT = "⁂"


def page(title: str, body: str, language: str, css: str = "style.css", body_class: str = "") -> str:
    return PAGE.format(
        lang=escape(language),
        title=escape(title),
        css=css,
        body=body,
        body_class=f' class="{body_class}"' if body_class else "",
    )


def cover_page(cover: Cover, metadata: Metadata) -> str:
    body = (
        '<section class="cover" epub:type="cover">\n'
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'version="1.1" width="100%" height="100%" viewBox="0 0 {cover.width} {cover.height}" '
        'preserveAspectRatio="xMidYMid meet">\n'
        f'<image width="{cover.width}" height="{cover.height}" xlink:href="images/cover.jpg"/>\n'
        "</svg>\n</section>"
    )
    return page(metadata.title, body, metadata.language, body_class="cover")


def title_page(metadata: Metadata) -> str:
    body = ['<section class="titlepage" epub:type="titlepage">']
    body.append(f"<h1>{escape(metadata.title)}</h1>")
    if metadata.author:
        body.append(f'<p class="author">{escape(metadata.author)}</p>')
    body.append("</section>")
    return page(metadata.title, "\n".join(body), metadata.language)


def section_page(section: Section, metadata: Metadata, pictures: dict[int, str]) -> str:
    heading = section.heading
    division = heading is not None and not section.paragraphs
    kind = "division" if division else "chapter"

    parts = [f'<section class="{kind}" epub:type="{kind}">']
    if heading:
        parts.append(heading_html(heading))
    if division:
        parts.append(f'<p class="ornament">{ORNAMENT}</p>')
    linked: set[str] = set()
    epigraph: list[str] = []
    for paragraph in section.paragraphs:
        if paragraph.epigraph:
            kind = ' class="attribution"' if paragraph.attribution else ""
            epigraph.append(f"<p{kind}>{paragraph_html(paragraph.text, section.notes, linked)}</p>")
            continue
        if epigraph:
            parts.append(f'<div class="epigraph">{"".join(epigraph)}</div>')
            epigraph = []
        if paragraph.picture:
            src = pictures[id(paragraph)]
            parts.append(f'<figure class="picture"><img src="../{src}" alt=""/></figure>')
        elif paragraph.scene_break:
            parts.append(f'<p class="scene-break">{escape(paragraph.text)}</p>')
        elif paragraph.verse:
            lines = (paragraph_html(line.text, section.notes, linked) for line in paragraph.lines)
            parts.append(f'<div class="verse">{"".join(f"<p>{line}</p>" for line in lines)}</div>')
        else:
            parts.append(f"<p>{paragraph_html(paragraph.text, section.notes, linked)}</p>")
    if epigraph:
        parts.append(f'<div class="epigraph">{"".join(epigraph)}</div>')
    parts.append("</section>")

    title = heading.text if heading else metadata.title
    return page(title, "\n".join(parts), metadata.language, css="../style.css")


def paragraph_html(text: str, notes: dict[str, Note], linked: set[str]) -> str:
    def link(match: re.Match[str]) -> str:
        note = notes.get(match.group(1))
        if note is None:
            return match.group(0)
        anchor = "" if note.id in linked else f' id="ref-{note.id}"'
        linked.add(note.id)
        return (
            f'<a class="noteref" epub:type="noteref" role="doc-noteref"{anchor} '
            f'href="../notes.xhtml#{note.id}">{note.mark}</a>'
        )

    return NOTE_MARK.sub(link, styled_html(escape(text)))


def notes_page(notes: list[Note], sources: dict[str, str], title: str, language: str) -> str:
    parts = [
        '<section class="notes" epub:type="endnotes" role="doc-endnotes">',
        f"<h1>{escape(title)}</h1>",
        "<ol>",
    ]
    for note in notes:
        mark = escape(note.mark)
        if note.id in sources:
            mark = f'<a href="{sources[note.id]}#ref-{note.id}" role="doc-backlink">{mark}</a>'
        shown = f'<span class="mark">{mark}</span> ' if mark else ""
        parts.append(
            f'<li id="{note.id}" epub:type="endnote"><p>{shown}{escape(note.text)}</p></li>'
        )
    parts.append("</ol>\n</section>")
    return page(title, "\n".join(parts), language)


def heading_html(heading: Heading) -> str:
    tag = f"h{min(heading.level, 3)}"
    if not heading.title:
        return f"<{tag}>{escape(heading.label)}</{tag}>"
    label = f'<span class="label">{escape(heading.label)}</span>'
    return f"<{tag}>{label}{escape(heading.title)}</{tag}>"
