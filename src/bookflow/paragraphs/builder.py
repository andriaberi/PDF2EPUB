from bookflow.labels import numeral_value
from bookflow.pdf import Line, Page

from .layout import (
    Layout,
    ends_page_early,
    ends_paragraph,
    fit,
    has_gap_before,
    is_indented,
    is_set_apart,
    is_tall,
    measure,
    text_column,
)
from .models import Paragraph
from .verse import find_verse


def build_paragraphs(pages: list[Page]) -> list[Paragraph]:
    """Join the lines of all pages into paragraphs, across page breaks too."""
    paragraphs: list[Paragraph] = []
    previous: tuple[Line, Layout] | None = None
    if not any(page.lines for page in pages):
        return paragraphs
    column = text_column(pages)

    for page in pages:
        if not page.lines:
            continue
        layout = fit(measure(page), column)
        verse = find_verse(page.lines, layout)
        for index, line in enumerate(page.lines):
            above = page.lines[index - 1] if index else None
            if index in verse:
                # Verse goes on line by line until a stanza ends; text never joins it.
                starts = verse[index] or not paragraphs or not paragraphs[-1].verse
            else:
                starts = (
                    not paragraphs
                    or paragraphs[-1].verse
                    or starts_paragraph(line, above, layout, previous)
                )
            if starts:
                paragraphs.append(Paragraph(line.text, page.number, [line], index in verse))
            else:
                last = paragraphs[-1]
                last.text = f"{last.text} {line.text}" if last.verse else join(last.text, line.text)
                last.lines.append(line)
            previous = (line, layout)

    return paragraphs


def starts_paragraph(
    line: Line, above: Line | None, layout: Layout, previous: tuple[Line, Layout] | None
) -> bool:
    # A word broken at the end of the last line always carries on, whatever the layout.
    if previous is not None and breaks_word(previous[0].text):
        return False
    # A heading in a bigger font stands alone: the gap below a tall line measures
    # small, so the gap rule alone would glue the heading to the text after it.
    if is_tall(line, layout) or (previous is not None and is_tall(*previous)):
        return True
    # So does a chapter number alone on its line ("XII", "7."), whatever its size.
    if numeral_value(line.text) or (previous is not None and numeral_value(previous[0].text)):
        return True
    # A line set apart from the text, like a right-aligned label, stands alone too,
    # even at the foot of a page.
    if previous is not None and is_set_apart(previous[0], line, layout):
        return True
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
