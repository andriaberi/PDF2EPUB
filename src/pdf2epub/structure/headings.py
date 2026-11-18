from pdf2epub.labels import is_section_name, label_level, split_label
from pdf2epub.paragraphs import Paragraph
from pdf2epub.paragraphs.layout import SET_APART, TITLE_LINES, Layout, is_short
from pdf2epub.pdf import Line


def is_centred(line: Line, layout: Layout) -> bool:
    margin = layout.line_height
    middle = (layout.left + layout.right) / 2
    return (
        line.x0 > layout.left + margin
        and line.x1 < layout.right - margin
        and abs((line.x0 + line.x1) / 2 - middle) < 2 * layout.line_height
    )


def is_full_line(line: Line, layout: Layout) -> bool:
    return line.x0 < layout.left + 2 * layout.line_height and not is_short(line, layout)


def is_label(paragraph: Paragraph, layout: Layout) -> bool:
    return (
        len(paragraph.lines) == 1
        and not is_full_line(paragraph.lines[0], layout)
        and label_level(paragraph.text) is not None
    )


def is_named_section(paragraph: Paragraph, layout: Layout) -> bool:
    return (
        len(paragraph.lines) == 1
        and not is_full_line(paragraph.lines[0], layout)
        and is_section_name(paragraph.text)
    )


def run_in_label(paragraph: Paragraph, layout: Layout) -> tuple[str, str] | None:
    if len(paragraph.lines) != 1 or not is_short(paragraph.lines[0], layout):
        return None
    return split_label(paragraph.text)


def is_title(paragraph: Paragraph, layout: Layout) -> bool:
    if len(paragraph.lines) > TITLE_LINES:
        return False
    if paragraph.text.isupper():
        return True
    return all(
        is_centred(line, layout) or is_short(line, layout) or is_set_right(line, layout)
        for line in paragraph.lines
    )


def is_set_right(line: Line, layout: Layout) -> bool:
    return line.x0 - layout.left > SET_APART * layout.line_height


def gap_after(paragraph: Paragraph, following: Paragraph | None, layout: Layout) -> bool:
    if following is None or following.page != paragraph.page:
        return True
    space = following.lines[0].y0 - paragraph.lines[-1].y1
    return space > layout.gap + layout.line_height / 2
