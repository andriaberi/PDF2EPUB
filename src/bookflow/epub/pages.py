from html import escape

from bookflow.cover import Cover
from bookflow.structure import Heading, Section

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

# Between a book's sections, the sign of a new part.
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
    """The cover image scaled to fill the screen, keeping its proportions."""
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


def section_page(section: Section, metadata: Metadata) -> str:
    """One section as a page of its own, so every section starts on a new page."""
    heading = section.heading
    division = heading is not None and not section.paragraphs
    kind = "division" if division else "chapter"

    parts = [f'<section class="{kind}" epub:type="{kind}">']
    if heading:
        parts.append(heading_html(heading))
    if division:
        parts.append(f'<p class="ornament">{ORNAMENT}</p>')
    parts.extend(f"<p>{escape(paragraph.text)}</p>" for paragraph in section.paragraphs)
    parts.append("</section>")

    title = heading.text if heading else metadata.title
    return page(title, "\n".join(parts), metadata.language, css="../style.css")


def heading_html(heading: Heading) -> str:
    """The label as a small line above the title: "თავი პირველი" over "ბატონი მირიელი".

    A heading without a title shows its label as the title.
    """
    tag = f"h{min(heading.level, 3)}"
    if not heading.title:
        return f"<{tag}>{escape(heading.label)}</{tag}>"
    label = f'<span class="label">{escape(heading.label)}</span>'
    return f"<{tag}>{label}{escape(heading.title)}</{tag}>"
