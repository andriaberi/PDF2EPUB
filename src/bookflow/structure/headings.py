from bookflow.labels import is_section_name, label_level, split_label
from bookflow.paragraphs import Paragraph
from bookflow.paragraphs.layout import TITLE_LINES, Layout
from bookflow.pdf import Line

# A title is a line or a few, never a paragraph of text.
MAX_TITLE_LINES = TITLE_LINES


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


def is_named_section(paragraph: Paragraph, layout: Layout) -> bool:
    """A section named, not numbered, alone on a line: "წინათქმა", "Prologue"."""
    return (
        len(paragraph.lines) == 1
        and not is_full_line(paragraph.lines[0], layout)
        and is_section_name(paragraph.text)
    )


def run_in_label(paragraph: Paragraph, layout: Layout) -> tuple[str, str] | None:
    """A label and its title on one line, short of the right margin: "თავი მეშვიდე ..."."""
    if len(paragraph.lines) != 1 or not is_short(paragraph.lines[0], layout):
        return None
    return split_label(paragraph.text)


def is_title(paragraph: Paragraph, layout: Layout) -> bool:
    """A line or a few, each centred or short, or all in capitals: never running text."""
    if len(paragraph.lines) > MAX_TITLE_LINES:
        return False
    if paragraph.text.isupper():
        return True
    return all(is_centred(line, layout) or is_short(line, layout) for line in paragraph.lines)


def gap_after(paragraph: Paragraph, following: Paragraph | None, layout: Layout) -> bool:
    """A heading is set off from the text after it; a short paragraph of text isn't."""
    if following is None or following.page != paragraph.page:
        return True
    space = following.lines[0].y0 - paragraph.lines[-1].y1
    return space > layout.gap + layout.line_height / 2
