from pdf2epub.labels import numeral_value
from pdf2epub.paragraphs import Paragraph
from pdf2epub.paragraphs.builder import join_lines
from pdf2epub.paragraphs.layout import SET_APART, Layout
from pdf2epub.pdf import Line

from .headings import is_label, is_named_section, is_set_right


def take_epigraph(
    paragraphs: list[Paragraph], index: int, page: int, column: Layout
) -> tuple[list[Paragraph], int]:
    """The epigraph under a heading on `page`, and the index after it: lines set far
    right before the chapter's text, each quotation's author further right still."""
    start = index
    while index < len(paragraphs) and is_epigraph_part(paragraphs[index], page, column):
        index += 1
    lines = [line for paragraph in paragraphs[start:index] for line in paragraph.lines]
    return quotations(lines, paragraphs[start].page if lines else page, column), index


def is_epigraph_part(paragraph: Paragraph, page: int, column: Layout) -> bool:
    # A heading at a page's foot has its epigraph on the next page.
    return (
        paragraph.page in (page, page + 1)
        and not paragraph.scene_break
        and all(is_set_right(line, column) for line in paragraph.lines)
        and not is_label(paragraph, column)
        and not is_named_section(paragraph, column)
        and numeral_value(paragraph.text) is None
    )


def quotations(lines: list[Line], page: int, column: Layout) -> list[Paragraph]:
    """The quotations' lines run together, and each name on a line of its own."""
    parts: list[Paragraph] = []
    quote: list[Line] = []
    for line in lines:
        # A name starts well right of its quotation; the next quotation, back at its left.
        if quote and line.x0 - min(q.x0 for q in quote) > SET_APART * column.line_height:
            parts.append(quotation(quote, page))
            parts.append(Paragraph(line.text, page, [line], epigraph=True, attribution=True))
            quote = []
        else:
            quote.append(line)
    if quote:
        parts.append(quotation(quote, page))
    return parts


def quotation(lines: list[Line], page: int) -> Paragraph:
    return Paragraph(join_lines(lines), page, lines, epigraph=True)
