from bookflow.labels import label_level
from bookflow.paragraphs import Paragraph
from bookflow.paragraphs.layout import Layout
from bookflow.pdf import Line

# A title is a line or a few, never a paragraph of text.
MAX_TITLE_LINES = 3


def is_short(line: Line, layout: Layout) -> bool:
    """Stops well before the right margin, as a heading set flush left does."""
    return line.x1 < layout.right - 2 * layout.line_height


def is_centred(line: Line, layout: Layout) -> bool:
    """Set apart from both margins, around the middle of the text column."""
    margin = layout.line_height
    middle = (layout.left + layout.right) / 2
    return (
        line.x0 > layout.left + margin
        and line.x1 < layout.right - margin
        and abs((line.x0 + line.x1) / 2 - middle) < 2 * layout.line_height
    )


def is_full_line(line: Line, layout: Layout) -> bool:
    """A line of running text: from the left margin (or an indent) to the right edge."""
    return line.x0 < layout.left + 2 * layout.line_height and not is_short(line, layout)


def is_label(paragraph: Paragraph, layout: Layout) -> bool:
    """A label alone on a line set any way but as running text.

    Books set headings centred, flush left or right, so only a full line is ruled out.
    """
    return (
        len(paragraph.lines) == 1
        and not is_full_line(paragraph.lines[0], layout)
        and label_level(paragraph.text) is not None
    )


def is_title(paragraph: Paragraph, layout: Layout) -> bool:
    """A line or a few, each centred or short: never a run of full lines of text."""
    return len(paragraph.lines) <= MAX_TITLE_LINES and all(
        is_centred(line, layout) or is_short(line, layout) for line in paragraph.lines
    )


def gap_after(paragraph: Paragraph, following: Paragraph | None, layout: Layout) -> bool:
    """A heading is set off from the text after it; a short paragraph of text isn't."""
    if following is None or following.page != paragraph.page:
        return True
    space = following.lines[0].y0 - paragraph.lines[-1].y1
    return space > layout.gap + layout.line_height / 2
