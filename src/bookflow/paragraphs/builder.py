from bookflow.pdf import Line, Page

from .layout import (
    Layout,
    ends_page_early,
    ends_paragraph,
    has_gap_before,
    is_indented,
    measure,
)
from .models import Paragraph


def build_paragraphs(pages: list[Page]) -> list[Paragraph]:
    """Join the lines of all pages into paragraphs, across page breaks too."""
    paragraphs: list[Paragraph] = []
    previous: tuple[Line, Layout] | None = None

    for page in pages:
        if not page.lines:
            continue
        layout = measure(page)
        for index, line in enumerate(page.lines):
            above = page.lines[index - 1] if index else None
            if not paragraphs or starts_paragraph(line, above, layout, previous):
                paragraphs.append(Paragraph(line.text, page.number, [line]))
            else:
                last = paragraphs[-1]
                last.text = join(last.text, line.text)
                last.lines.append(line)
            previous = (line, layout)

    return paragraphs


def starts_paragraph(
    line: Line, above: Line | None, layout: Layout, previous: tuple[Line, Layout] | None
) -> bool:
    # A word broken at the end of the last line always carries on, whatever the layout.
    if previous is not None and breaks_word(previous[0].text):
        return False
    if is_indented(line, layout):
        return True
    if above is not None and has_gap_before(line, above, layout):
        return True
    if above is None and previous is not None and ends_page_early(*previous):
        return True
    # A short line ending a sentence closes its paragraph even when the next line's
    # indent is lost. It also decides whether a page's first line carries on the last
    # page's paragraph.
    return previous is not None and ends_paragraph(*previous)


def breaks_word(text: str) -> bool:
    return text.endswith("-") and text[-2:-1].isalpha()


def join(text: str, line: str) -> str:
    """Add a line to a paragraph, rejoining a word broken by a hyphen."""
    if breaks_word(text) and line[:1].isalpha():
        return text[:-1] + line
    return f"{text} {line}"
